"""
Run the foundation-model experiments F1, F2, F4, F5 and F6 end to end.

Protocol (MODELS.md, "Shared setup"; FOUNDATION.md, "Experiments"):

1. **Validation year (2023)**: every setting that has to be chosen is run on
   the 2023 origins.
   - F1 / F2 (hourly TimesFM-3): context length 2048, 4096, 8192 h.
   - F4 / F5 (daily TimesFM-3): the whole history, nothing to choose
     (the validation run is still made, as a reference).
   - F6 (TabICL): features ``ours`` / ``default`` x context ``all`` / ``730`` days.
2. **Selection**: per experiment and horizon, the setting with the lowest
   validation MAE (``--select-metric pinball`` for the mean pinball loss).
3. **Test year (2024)**: one run with the selected setting, used once.
4. Seasonal naive files for every resolution, horizon and split, then all
   metrics, a summary table and ``selection.json``.

The weather inputs are the observed values (weather variant A, oracle), so
the results are an upper bound and marked as such in every JSON sidecar.

Examples (from the project root):

    uv run python src/models/foundation/run_experiments.py                     # all five experiments
    uv run python src/models/foundation/run_experiments.py --experiments F4 F5 F6
    uv run python src/models/foundation/run_experiments.py --hourly-contexts 2048 4096   # smaller F1 / F2 grid
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import evaluate
import tabicl_forecaster
import timesfm3_forecast
from data import (DEFAULT_DATA_DIR, DEFAULT_RESULTS_DIR, HORIZONS, covariate_set, load_frame, origin_positions,
                  write_forecasts)


def same_run(path: Path, cov, n_origins: int) -> bool:
    """True if the JSON sidecar of an existing run has the same covariates and origin count.

    The origin count catches files of a --max-origins test run, so a full run
    never reuses them.
    """
    meta_path = path.with_suffix(".json")
    if not meta_path.exists():
        return False
    meta = json.loads(meta_path.read_text())
    past = meta.get("covariates_past_only", meta.get("covariates_past_only_ffill"))
    return (meta.get("covariates_known") == cov.known and past == cov.past_only
            and meta.get("n_origins") == n_origins)


ALL_EXPERIMENTS = ["F1", "F2", "F4", "F5", "F6"]
TIMESFM_EXPERIMENTS = {"F1": ("hourly", False), "F2": ("hourly", True), "F4": ("daily", False), "F5": ("daily", True)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--experiments", nargs="+", choices=ALL_EXPERIMENTS, default=ALL_EXPERIMENTS)
    p.add_argument("--hourly-contexts", type=int, nargs="+", default=[2048, 4096, 8192])
    p.add_argument("--tabicl-contexts", nargs="+", default=["all", "730"])
    p.add_argument("--tabicl-features", nargs="+", default=["ours", "default"])
    p.add_argument("--select-metric", choices=["MAE", "pinball"], default="MAE")
    p.add_argument("--skip-test", action="store_true", help="validation runs and selection only")
    p.add_argument("--batch-size", type=int, default=16, help="TimesFM-3 per_core_batch_size")
    p.add_argument("--device", default=None)
    p.add_argument("--timesfm-checkpoint", default=timesfm3_forecast.CHECKPOINT)
    p.add_argument("--tabicl-model-path", default=None)
    p.add_argument("--tabicl-n-estimators", type=int, default=None)
    p.add_argument("--max-origins", type=int, default=None, help="only the first N origins (smoke test)")
    p.add_argument("--overwrite", action="store_true", help="rerun runs whose forecast file exists")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    args = p.parse_args()

    forecast_dir = args.results_dir / "forecasts"
    metrics_dir = args.results_dir / "metrics"
    frames = {}

    def frame(res):
        if res not in frames:
            frames[res] = load_frame(res, args.data_dir)
        return frames[res]

    model = None

    def timesfm():
        nonlocal model
        if model is None:
            model = timesfm3_forecast.load_model(args.timesfm_checkpoint, args.batch_size, args.device)
        return model

    tabicl_config = {}
    if args.tabicl_model_path:
        tabicl_config["model_path"] = args.tabicl_model_path
    if args.tabicl_n_estimators:
        tabicl_config["n_estimators"] = args.tabicl_n_estimators
    if args.device:
        tabicl_config["device"] = args.device

    produced: list[Path] = []
    candidates: dict[tuple[str, int], list[tuple[dict, Path]]] = {}

    def run(path: Path, make, cov, res, split, h):
        """Run one forecast unless the same run exists already (resumable)."""
        n = len(origin_positions(frame(res), split, h))
        n = n if args.max_origins is None else min(n, args.max_origins)
        if path.exists() and not args.overwrite and same_run(path, cov, n):
            print(f"[run] exists, skipped: {path.name}")
        else:
            if path.exists() and not args.overwrite:
                print(f"[run] inputs or origins changed since {path.name} was written, running it again")
            out, meta = make()
            write_forecasts(out, path, meta)
        produced.append(path)
        return path

    def timesfm_run(exp, h, split, ctx):
        res, cov = TIMESFM_EXPERIMENTS[exp]
        name = timesfm3_forecast.run_name(res, h, split, cov, ctx)
        return run(forecast_dir / f"{name}.csv", lambda: timesfm3_forecast.forecast(
            timesfm(), frame(res), split, h, cov, ctx, max_origins=args.max_origins),
            covariate_set(res, h, include_covariates=cov), res, split, h)

    def tabicl_run(h, split, feats, ctx):
        name = tabicl_forecaster.run_name(h, split, feats, ctx)
        return run(forecast_dir / f"{name}.csv", lambda: tabicl_forecaster.forecast(
            frame("daily"), split, h, feats, ctx, tabicl_config, max_origins=args.max_origins),
            covariate_set("daily", h, calendar=tabicl_forecaster.FEATURE_SETS[feats][0]), "daily", split, h)

    # ---------------------------------------------------------------- 1. validation
    for exp in [e for e in args.experiments if e in TIMESFM_EXPERIMENTS]:
        res, _ = TIMESFM_EXPERIMENTS[exp]
        contexts = args.hourly_contexts if res == "hourly" else [None]
        for h in HORIZONS[res]:
            for ctx in contexts:
                path = timesfm_run(exp, h, "val", ctx)
                candidates.setdefault((exp, h), []).append(({"context_length": ctx}, path))

    if "F6" in args.experiments:
        for h in HORIZONS["daily"]:
            for feats in args.tabicl_features:
                for ctx in map(tabicl_forecaster.parse_context, args.tabicl_contexts):
                    path = tabicl_run(h, "val", feats, ctx)
                    candidates.setdefault(("F6", h), []).append(({"features": feats, "context_days": ctx}, path))

    # ---------------------------------------------------------------- 2. selection
    selection = {}
    for (exp, h), cands in candidates.items():
        scores = evaluate.evaluate_files([pth for _, pth in cands], metrics_dir, data_dir=args.data_dir, frames=frames)
        metric = scores[args.select_metric].to_numpy()
        best = int(metric.argmin())
        selection[f"{exp}_{h}"] = {
            "experiment": exp, "horizon": h, "metric": args.select_metric,
            "chosen": cands[best][0],
            "validation": [{**c, args.select_metric: float(m)} for (c, _), m in zip(cands, metric)],
        }
        print(f"[select] {exp} h={h}: {cands[best][0]} ({args.select_metric}={metric[best]:.1f})")

    # ---------------------------------------------------------------- 3. test
    if not args.skip_test:
        for key, sel in selection.items():
            exp, h, chosen = sel["experiment"], sel["horizon"], sel["chosen"]
            if exp == "F6":
                tabicl_run(h, "test", chosen["features"], chosen["context_days"])
            else:
                timesfm_run(exp, h, "test", chosen["context_length"])

    # ---------------------------------------------------------------- 4. baselines + metrics
    resolutions = sorted({TIMESFM_EXPERIMENTS[e][0] for e in args.experiments if e in TIMESFM_EXPERIMENTS}
                         | ({"daily"} if "F6" in args.experiments else set()))
    splits = ["val"] if args.skip_test else ["val", "test"]
    for res in resolutions:
        for h in HORIZONS[res]:
            for split in splits:
                produced.append(evaluate.naive_forecast_file(frame(res), split, h, forecast_dir))

    summary = evaluate.evaluate_files(sorted(set(produced)), metrics_dir, "summary_foundation.csv",
                                      data_dir=args.data_dir, frames=frames)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    (metrics_dir / "selection_foundation.json").write_text(json.dumps(selection, indent=2, default=str))

    with pd.option_context("display.width", 220, "display.max_columns", 20, "display.float_format", "{:,.3f}".format):
        print(summary.drop(columns=["file", "model"])
              .sort_values(["resolution", "horizon", "split", "experiment", "setting"]).to_string(index=False))
    print(f"\n[run] summary -> {metrics_dir / 'summary_foundation.csv'}")


if __name__ == "__main__":
    main()
