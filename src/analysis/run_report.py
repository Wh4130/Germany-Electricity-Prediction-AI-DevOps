"""
The whole final report in one go, for every model that has results.

1. finds every forecast file ``src/results/<model>/forecasts/*.csv`` of the split
   and keeps the models selected with ``--models`` (default: all),
2. writes the missing seasonal naive files (``src/results/seasonal_naive``) and
   evaluates every forecast file whose metrics are missing or out of date
   (``src/results/<model>/metrics``),
3. writes to ``src/results/final_report/tables``: the weather breakdown, the
   report tables, the business value and the worst days,
4. writes to ``src/results/final_report/figures``: the report figures,
5. adds the model-specific tables and figures of every model family that has
   an analysis module (``MODEL_SPECIFIC``; today: the foundation models).

``--models`` takes display names (``Run.label``, e.g. "TimesFM-3, covariates"),
run ids (``<model folder>/<file stem>``) or results folders (e.g. ``sarimax``),
mixed freely. Only the selected models are compared, in every table and figure,
the model-specific ones included. The seasonal naive is always kept as the
benchmark. ``--list-models`` prints the names that can be selected.

Usage (from the project root):

    uv run python -m src.analysis.run_report
    uv run python -m src.analysis.run_report --list-models
    uv run python -m src.analysis.run_report --models "TimesFM-3, covariates" TabICL SARIMAX Tree-based
    uv run python -m src.analysis.run_report --models foundation sarimax tree-based
    uv run python -m src.analysis.run_report --reference SARIMAX --formats png svg
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path

from src.common.dataset import FrameCache
from src.common.paths import DATA_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR
from src.analysis import business_value, report_figures, report_tables, weather_breakdown, worst_days
from src.analysis import runs as runs_module
from src.analysis.evaluate import ensure_metrics, ensure_naive
from src.analysis.foundation import report_figures as foundation_figures
from src.analysis.foundation import report_tables as foundation_tables
from src.analysis.plotting import Colors
from src.analysis.runs import check_unique_labels, sort_horizons, sort_labels

# results folder -> (tables builder, figures builder) of its model-specific analysis
MODEL_SPECIFIC = {
    "foundation": (foundation_tables.build, foundation_figures.build),
}
# modules of the model-specific analysis that look up their runs themselves
MODEL_SPECIFIC_MODULES = [foundation_tables, foundation_figures]


def is_selected(run, selected: list[str] | None) -> bool:
    """True if ``run`` is the seasonal naive or matches a label, run id or results folder in ``selected``."""
    if not selected or run.is_naive:
        return True
    keep = set(selected)
    return run.label in keep or run.id in keep or run.model_dir in keep


def select_runs(runs: list, selected: list[str] | None) -> list:
    return [r for r in runs if is_selected(r, selected)]


def discover(args) -> list:
    """All runs of the split, then only the selected models (the naive benchmark is always kept)."""
    return select_runs(runs_module.discover_runs(args.results_dir, None, args.split), args.models)


def check_selection(all_runs: list, selected: list[str] | None) -> None:
    """Stop if a name in ``--models`` matches no run (a typo would otherwise drop a model silently)."""
    if not selected:
        return
    known = {r.label for r in all_runs} | {r.id for r in all_runs} | {r.model_dir for r in all_runs}
    unknown = [s for s in selected if s not in known]
    if unknown:
        labels = sort_labels(r.label for r in all_runs if not r.is_naive)
        raise SystemExit(f"[report] --models: no run matches {unknown}.\n"
                         f"[report] models with results: {labels}\n"
                         "[report] (results folders and run ids work too; see --list-models)")


def list_models(all_runs: list, split: str) -> None:
    """Print every model that can be selected, with its horizons and results folder."""
    models = [r for r in all_runs if not r.is_naive]
    if not models:
        print(f"[report] no {split} forecast files found")
        return
    print(f"Models with {split} results (pass the name in quotes to --models):\n")
    for label in sort_labels(r.label for r in models):
        mine = [r for r in models if r.label == label]
        horizons = ", ".join(sort_horizons(r.horizon_text for r in mine))
        folders = ", ".join(sorted({r.model_dir for r in mine}))
        print(f"  {label!r:45s} {horizons:45s} folder: {folders}")


@contextmanager
def selected_only(selected: list[str] | None):
    """Let the model-specific builders see only the selected runs.

    They call ``discover_runs`` themselves, so it is swapped, for the duration,
    for a version that applies the same selection as the rest of the report.
    """
    if not selected:
        yield
        return

    def filtered(*args, **kwargs):
        return select_runs(runs_module.discover_runs(*args, **kwargs), selected)

    originals = {m: m.discover_runs for m in MODEL_SPECIFIC_MODULES}
    try:
        for m in MODEL_SPECIFIC_MODULES:
            m.discover_runs = filtered
        yield
    finally:
        for m, original in originals.items():
            m.discover_runs = original


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--models", nargs="+", default=None,
                   help="models to compare: display names (e.g. \"TimesFM-3, covariates\"), run ids or "
                        "results folders (default: all; the seasonal naive is always kept)")
    p.add_argument("--list-models", action="store_true", help="print the models that have results and exit")
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

    all_runs = runs_module.discover_runs(args.results_dir, None, args.split)
    if args.list_models:
        list_models(all_runs, args.split)
        return
    check_selection(all_runs, args.models)

    frames = FrameCache(args.data_dir)
    runs = select_runs(all_runs, args.models)
    if not [r for r in runs if not r.is_naive]:
        raise SystemExit(f"[report] no {args.split} forecast files under {args.results_dir}/<model>/forecasts")
    print(f"[report] {len(runs)} runs: " + ", ".join(r.id for r in runs))
    if args.models:
        print("[report] models compared: " + ", ".join(sort_labels(r.label for r in runs if not r.is_naive)))
    check_unique_labels(runs)
    missing_refs = [ref for ref in args.reference if not any(ref in (r.label, r.id) for r in runs)]
    if missing_refs:
        print(f"[report] note: --reference {missing_refs} is not among the selected models, "
              "so the business value has no reference columns for it")

    # Benchmarks and metrics.
    made = ensure_naive(runs, frames, args.results_dir)
    if made:
        runs = discover(args)
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
        with selected_only(args.models):
            for model, (tables, figures) in MODEL_SPECIFIC.items():
                if model in present:
                    tables(args.results_dir, args.split, args.tables_dir)
                    figures(args.results_dir, args.split, args.tables_dir, args.figures_dir, args.formats,
                            colors)

    print(f"\n[report] tables  -> {args.tables_dir}\n[report] figures -> {args.figures_dir}")


if __name__ == "__main__":
    main()