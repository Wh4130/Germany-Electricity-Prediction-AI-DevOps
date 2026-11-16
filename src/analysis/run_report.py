"""
The whole final report in one go, for every model that has results.

1. finds every forecast file ``src/results/<model>/forecasts/*.csv`` of the split,
2. writes the missing seasonal naive files (``src/results/seasonal_naive``) and
   evaluates every forecast file whose metrics are missing or out of date
   (``src/results/<model>/metrics``),
3. writes to ``src/results/final_report/tables``: the weather breakdown, the
   report tables, the business value and the worst days,
4. writes to ``src/results/final_report/figures``: the report figures,
5. adds the model-specific tables and figures of every model family that has
   an analysis module (``MODEL_SPECIFIC``; today: the foundation models).

Usage (from the project root):

    uv run python -m src.analysis.run_report
    uv run python -m src.analysis.run_report --models foundation sarimax tree-based
    uv run python -m src.analysis.run_report --reference "TimesFM-3, no covariates" --formats png svg
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.common.dataset import FrameCache
from src.common.paths import DATA_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR
from src.analysis import business_value, report_figures, report_tables, weather_breakdown, worst_days
from src.analysis.evaluate import ensure_metrics, ensure_naive
from src.analysis.foundation import report_figures as foundation_figures
from src.analysis.foundation import report_tables as foundation_tables
from src.analysis.plotting import Colors
from src.analysis.runs import check_unique_labels, discover_runs

# results folder -> (tables builder, figures builder) of its model-specific analysis
MODEL_SPECIFIC = {
    "foundation": (foundation_tables.build, foundation_figures.build),
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--models", nargs="+", default=None, help="results folders (default: all)")
    p.add_argument("--split", choices=["val", "test"], default="test")
    p.add_argument("--reference", nargs="*", default=[], help="business value: model labels or run ids to "
                                                               "compare against")
    p.add_argument("--top", type=int, default=10, help="worst days per run")
    p.add_argument("--all-days", action="store_true", help="weather breakdown: include holidays etc.")
    p.add_argument("--formats", nargs="+", default=["png"])
    p.add_argument("--skip", nargs="*", default=[],
                   choices=["weather", "tables", "value", "worst", "figures", "specific"])
    p.add_argument("--data-dir", type=Path, default=DATA_DIR)
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--tables-dir", type=Path, default=TABLES_DIR)
    p.add_argument("--figures-dir", type=Path, default=FIGURES_DIR)
    args = p.parse_args()

    frames = FrameCache(args.data_dir)
    runs = discover_runs(args.results_dir, args.models, args.split)
    if not [r for r in runs if not r.is_naive]:
        raise SystemExit(f"[report] no {args.split} forecast files under {args.results_dir}/<model>/forecasts")
    print(f"[report] {len(runs)} runs: " + ", ".join(r.id for r in runs))
    check_unique_labels(runs)

    # Benchmarks and metrics.
    made = ensure_naive(runs, frames, args.results_dir)
    if made:
        runs = discover_runs(args.results_dir, args.models, args.split)
    ensure_metrics(runs, frames, data_dir=args.data_dir)
    model_runs = [r for r in runs if not r.is_naive]
    colors = Colors(r.label for r in runs)

    if "weather" not in args.skip:
        weather_breakdown.run_breakdown(model_runs, frames, args.all_days, args.tables_dir)
    if "tables" not in args.skip:
        report_tables.build(runs, args.split, args.tables_dir)
    if "value" not in args.skip:
        business_value.build(model_runs, frames, args.reference, out_dir=args.tables_dir)
    if "worst" not in args.skip:
        worst_days.build(model_runs, frames, args.top, args.tables_dir)
    if "figures" not in args.skip:
        report_figures.build(runs, split=args.split, tables_dir=args.tables_dir, out_dir=args.figures_dir,
                             formats=args.formats, colors=colors)
    if "specific" not in args.skip:
        present = {r.model_dir for r in model_runs}
        for model, (tables, figures) in MODEL_SPECIFIC.items():
            if model in present:
                tables(args.results_dir, args.split, args.tables_dir)
                figures(args.results_dir, args.split, args.tables_dir, args.figures_dir, args.formats, colors)

    print(f"\n[report] tables  -> {args.tables_dir}\n[report] figures -> {args.figures_dir}")


if __name__ == "__main__":
    main()