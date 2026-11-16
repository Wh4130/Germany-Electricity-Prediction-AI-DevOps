"""
Evaluate forecast files of any model (command line of ``src.common.evaluation``).

Reads ``src/results/<model>/forecasts/*.csv`` and writes one metrics JSON per
file to ``src/results/<model>/metrics/`` plus a ``summary.csv`` per model
folder. Seasonal naive files go to ``src/results/seasonal_naive/``.

Usage (from the project root):

    uv run python -m src.analysis.evaluate                          # every model; only files without fresh metrics
    uv run python -m src.analysis.evaluate --models sarimax tree-based --force
    uv run python -m src.analysis.evaluate src/results/sarimax/forecasts/sarimax_daily_1d_test.csv
    uv run python -m src.analysis.evaluate --naive                  # seasonal naive files for every horizon in use
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.common import evaluation
from src.common.dataset import HORIZONS, SPLITS, FrameCache
from src.common.paths import DATA_DIR, NAIVE_MODEL, RESULTS_DIR, forecast_dir
from src.analysis.runs import Run, discover_runs, runs_from_paths


def needs_metrics(run: Run) -> bool:
    m = run.metrics_path
    return not m.exists() or m.stat().st_mtime < run.forecast_path.stat().st_mtime


def ensure_metrics(runs: list[Run], frames: dict, force: bool = False, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Evaluate the runs whose metrics are missing or older than the forecast file."""
    todo = [r for r in runs if force or needs_metrics(r)]
    if not todo:
        print("[evaluate] all metrics are up to date")
        return pd.DataFrame()
    print(f"[evaluate] {len(todo)} of {len(runs)} forecast files to evaluate")
    summary = evaluation.evaluate_files([r.forecast_path for r in todo], data_dir=data_dir, frames=frames)
    # One summary.csv per model folder, over all its metrics files (not only the new ones).
    for mdir in sorted({r.metrics_path.parent for r in todo}):
        rows = []
        for path in sorted(mdir.glob("*.json")):
            res = json.loads(path.read_text())
            if "overall" in res:
                rows.append(evaluation.summary_row(res))
        pd.DataFrame(rows).to_csv(mdir / "summary.csv", index=False)
    return summary


def ensure_naive(runs: list[Run], frames: dict, results_dir: Path = RESULTS_DIR, force: bool = False) -> list[Path]:
    """Seasonal naive files for every (resolution, horizon, split) among ``runs`` that has none yet."""
    out_dir = forecast_dir(NAIVE_MODEL, results_dir)
    keys = {(r.resolution, r.horizon, r.split) for r in runs if not r.is_naive}
    have = {(r.resolution, r.horizon, r.split) for r in runs if r.is_naive}
    if out_dir.exists():
        have |= {(r.resolution, r.horizon, r.split) for r in runs_from_paths(out_dir.glob("*.csv"))}
    made = []
    for res, h, split in sorted(keys if force else keys - have):
        made.append(evaluation.naive_forecast_file(frames[res], split, h, out_dir))
    return made


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="*", type=Path, help="forecast CSV files (default: all models)")
    p.add_argument("--models", nargs="+", default=None, help="results folders to evaluate (default: all)")
    p.add_argument("--split", choices=["val", "test", "all"], default="all")
    p.add_argument("--force", action="store_true", help="evaluate again even if the metrics are up to date")
    p.add_argument("--naive", action="store_true",
                   help="write the seasonal naive files (every horizon of the shared setup and of the runs)")
    p.add_argument("--data-dir", type=Path, default=DATA_DIR)
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = p.parse_args()

    frames = FrameCache(args.data_dir)
    split = None if args.split == "all" else args.split
    if args.files:
        runs = runs_from_paths(args.files)
    else:
        runs = discover_runs(args.results_dir, args.models, split, include_naive=args.models is None)

    if args.naive:
        made = ensure_naive(runs, frames, args.results_dir, force=args.force)
        out_dir = forecast_dir(NAIVE_MODEL, args.results_dir)
        for res, horizons in HORIZONS.items():  # the shared setup, even without runs
            for h in horizons:
                for sp in ([split] if split else list(SPLITS)):
                    name = out_dir / f"seasonal_naive_{res}_{h}{'h' if res == 'hourly' else 'd'}_{sp}.csv"
                    if args.force or not name.exists():
                        made.append(evaluation.naive_forecast_file(frames[res], sp, h, out_dir))
        runs += runs_from_paths(made)

    summary = ensure_metrics(runs, frames, force=args.force, data_dir=args.data_dir)
    if not summary.empty:
        with pd.option_context("display.width", 200, "display.max_columns", 20):
            print(summary.drop(columns=["file"]).to_string(index=False))


if __name__ == "__main__":
    main()