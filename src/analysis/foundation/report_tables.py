"""
Report tables that only make sense for the foundation models (TimesFM-3, TabICL).

- the validation settings table (which context length / feature set was
  compared on 2023 and which one was chosen), from
  ``src/results/foundation/metrics/summary_foundation.csv`` and
  ``selection_foundation.json`` (written by ``run_experiments``),
- the covariate gain by day type (TimesFM-3 without vs with covariates),
- TabICL vs TimesFM-3 with covariates, by day type.

Tables go to ``src/results/final_report/tables`` with the prefix ``foundation_``,
collected in ``foundation_tables.md``. The tables over all models are made by
``src.analysis.report_tables``.

Usage (from the project root):

    uv run python -m src.analysis.foundation.report_tables
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.common.dataset import horizon_text
from src.common.paths import RESULTS_DIR, TABLES_DIR, metrics_dir
from src.analysis.report import Report
from src.analysis.report_tables import compare_by_day_type, load_metrics
from src.analysis.runs import Run, discover_runs

FOUNDATION_MODELS = ["foundation", "foundation_extra_features"]
NOCOV, COV, TABICL = "TimesFM-3, no covariates", "TimesFM-3, covariates", "TabICL"
EXPERIMENT_LABEL = {"F1": NOCOV, "F2": COV, "F4": NOCOV, "F5": COV, "F6": TABICL}


def chosen_setting(sel: dict) -> str:
    c = sel["chosen"]
    parts = []
    if "features" in c:
        parts.append(f"features={c['features']}")
    for key in ("context_length", "context_days"):
        if key in c:
            parts.append(f"ctx={'all' if c[key] is None else c[key]}")
    return " ".join(parts)


def validation_settings(report: Report, summary: pd.DataFrame, selection_path: Path, name: str, title: str):
    v = summary[(summary["split"] == "val") & (summary["experiment"].fillna("baseline") != "baseline")].copy()
    if v.empty:
        return
    v["setting"] = v["setting"].fillna("")
    chosen = {}
    if selection_path.exists():
        for sel in json.loads(selection_path.read_text()).values():
            chosen[(sel["experiment"], int(sel["horizon"]))] = chosen_setting(sel)
    v["Chosen"] = [("yes" if chosen.get((e, int(h))) == st else "") for e, h, st in
                   zip(v["experiment"], v["horizon"], v["setting"])]
    v = v.sort_values(["resolution", "horizon", "experiment", "MAE"], ascending=[False, True, True, True])
    table = pd.DataFrame({
        "Model": v["experiment"].map(EXPERIMENT_LABEL).fillna(v["model"]).to_numpy(),
        "Experiment": v["experiment"].to_numpy(),
        "Horizon": [horizon_text(r, int(h)) for r, h in zip(v["resolution"], v["horizon"])],
        "Setting": v["setting"].to_numpy(),
        "MAE (MWh)": v["MAE"].to_numpy(),
        "Pinball (MWh)": v["pinball"].to_numpy(dtype=float),
        "80 % band coverage %": v["coverage80_%"].to_numpy(dtype=float),
        "Chosen": v["Chosen"].to_numpy(),
    })
    report.add(name, title, table,
               note="Chosen = lowest validation MAE; only the chosen setting was run on the test year.")


def find_pairs(metrics: dict[str, tuple[Run, dict]]) -> dict[str, list[tuple[str, str]]]:
    """Run pairs of the same results folder and horizon: covariate gain and TabICL vs TimesFM-3."""
    by_key = {(r.model_dir, r.label.split(" + ")[0], r.resolution, r.horizon): rid for rid, (r, _) in metrics.items()}
    cov, tab = [], []
    for (mdir, model, res, h), rid in sorted(by_key.items(), key=lambda kv: (kv[0][0], kv[0][2] != "hourly", kv[0][3])):
        if model == NOCOV and (mdir, COV, res, h) in by_key:
            cov.append((rid, by_key[(mdir, COV, res, h)]))
        if model == COV and (mdir, TABICL, res, h) in by_key:
            tab.append((rid, by_key[(mdir, TABICL, res, h)]))
    return {"cov": cov, "tab": tab}


def build(results_dir: Path = RESULTS_DIR, split: str = "test", out_dir: Path = TABLES_DIR) -> Path | None:
    runs = [r for r in discover_runs(results_dir, FOUNDATION_MODELS, split, include_naive=False)
            if r.model_dir in FOUNDATION_MODELS]
    if not runs:
        print("[foundation] no foundation runs found, foundation tables skipped")
        return None
    report = Report(out_dir, md_name="foundation_tables.md", title="Foundation models: specific tables",
                    prefix="foundation_")

    for mdir in FOUNDATION_MODELS:
        mdir_metrics = metrics_dir(mdir, results_dir)
        summary_path = mdir_metrics / "summary_foundation.csv"
        if summary_path.exists():
            validation_settings(report, pd.read_csv(summary_path), mdir_metrics / "selection_foundation.json",
                                f"validation_settings_{mdir}",
                                f"Settings compared on the validation year ({mdir})")

    metrics = load_metrics(runs)
    pairs = find_pairs(metrics)
    compare_by_day_type(report, metrics, "covariate_gain_by_day_type",
                        "Covariate gain by day type (TimesFM-3 without vs with covariates)", pairs["cov"],
                        note="Share of total gain: part of the whole-year error reduction that comes from this "
                             "day type.")
    compare_by_day_type(report, metrics, "tabicl_vs_timesfm_by_day_type",
                        "TabICL vs TimesFM-3 with covariates, by day type", pairs["tab"],
                        note="Negative MAE change = TabICL is better.")
    path = report.write()
    print(f"[foundation] {report.n_tables} tables -> {path}")
    return path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", default="test", choices=["val", "test"])
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--out-dir", type=Path, default=TABLES_DIR)
    args = p.parse_args()
    build(args.results_dir, args.split, args.out_dir)


if __name__ == "__main__":
    main()