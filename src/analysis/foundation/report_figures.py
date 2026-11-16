"""
Report figures that only make sense for the foundation models.

- ``foundation_fig_covariates_by_day_type``: error and band coverage by day
  type, TimesFM-3 without vs with covariates (hourly 24 h).
- ``foundation_fig_before_after_cold_snaps``: bias on days much colder than the
  week before, original inputs (``results/foundation``) vs the reruns with the
  extra features (``results/foundation_extra_features``), same file names.

Inputs: the metrics JSONs and ``final_report/tables/weather_breakdown.csv``
(which has to include both results folders). Figures go to
``src/results/final_report/figures``. The figures over all models are made by
``src.analysis.report_figures``.

Usage (from the project root):

    uv run python -m src.analysis.foundation.report_figures
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from src.common.dataset import SPLITS
from src.common.paths import FIGURES_DIR, RESULTS_DIR, TABLES_DIR
from src.analysis.foundation.report_tables import COV, FOUNDATION_MODELS, NOCOV
from src.analysis.plotting import INK2, MUTED, SURFACE, Colors, bar_labels, grouped_bars, headline, plt, save, tidy
from src.analysis.report_figures import _fmt, _scale, _unit
from src.analysis.report_tables import DAY_TYPE_LABEL, load_metrics
from src.analysis.runs import discover_runs, sort_horizons, sort_labels

BEFORE, AFTER = "foundation", "foundation_extra_features"


def fig_covariates_by_day_type(nocov: dict, cov: dict, colors: Colors, out_dir: Path, formats: list[str],
                               horizon: str):
    runs = {NOCOV: nocov, COV: cov}
    types = [t for t in DAY_TYPE_LABEL if all((r.get("by_day_type") or {}).get(t) for r in runs.values())]
    wrap = lambda t: DAY_TYPE_LABEL[t].replace(" / ", "/\n").replace("Normal ", "Normal\n").replace(  # noqa: E731
        "Bridge ", "Bridge\n")
    labels = [wrap(t) for t in types]
    series = list(runs)
    mape = {(wrap(t), m): r["by_day_type"][t]["MAPE_%"] for m, r in runs.items() for t in types}
    cover = {(wrap(t), m): r["by_day_type"][t]["coverage80_%"] for m, r in runs.items() for t in types}

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
    grouped_bars(a1, labels, series, mape, colors, fmt=".1f")
    a1.set_ylabel("Average error (MAPE, %)")
    a1.set_title("Error", loc="left")
    tidy(a1)
    grouped_bars(a2, labels, series, cover, colors, fmt=".0f")
    a2.axhline(80, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    a2.annotate("target\n80 %", (1.0, 80), xycoords=("axes fraction", "data"), xytext=(4, 0),
                textcoords="offset points", ha="left", va="center", fontsize=8.5, color=INK2)
    a2.set_ylim(0, 105)
    a2.set_ylabel("Actual inside the 80 % band (%)")
    a2.set_title("Band coverage", loc="left")
    tidy(a2)
    handles = [Patch(color=colors(m), label=m) for m in series]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), bbox_to_anchor=(0.5, -0.02))

    hol = "holiday" if "holiday" in types else types[-1]
    nc, cv = nocov["by_day_type"][hol], cov["by_day_type"][hol]
    cut = 100 * (1 - cv["MAE"] / nc["MAE"])
    verb = "cut" if cut >= 0 else "raise"
    headline(fig, f"Covariates {verb} the {DAY_TYPE_LABEL[hol].lower()} error by {abs(cut):.0f} %",
             f"{horizon.capitalize()}, TimesFM-3. {DAY_TYPE_LABEL[hol]} band coverage goes from "
             f"{nc['coverage80_%']:.0f} % to {cv['coverage80_%']:.0f} %.")
    fig.subplots_adjust(top=0.80, bottom=0.2, wspace=0.28)
    return save(fig, out_dir, "foundation_fig_covariates_by_day_type", formats)


def fig_before_after(weather: pd.DataFrame, colors: Colors, out_dir: Path, formats: list[str],
                     bin_name: str = "much colder", split: str = "test"):
    w = weather[(weather["variable"] == "hdd_change_vs_last_week") & (weather["bin"] == bin_name)
                & (weather["split"] == split) & weather["model_dir"].isin([BEFORE, AFTER])].copy()
    w["stem"] = w["run"].str.split("/").str[-1]
    both = set(w.loc[w["model_dir"] == BEFORE, "stem"]) & set(w.loc[w["model_dir"] == AFTER, "stem"])
    w = w[w["stem"].isin(both)]
    if w.empty:
        raise ValueError(f"no run is in both results/{BEFORE} and results/{AFTER}")
    w["Base"] = w["Model"].str.split(" + ", regex=False).str[0]
    horizons = sort_horizons(w["Horizon"])
    widths = [max(1, w.loc[w["Horizon"] == h, "Base"].nunique()) + 0.6 for h in horizons]
    fig, axes = plt.subplots(1, len(horizons), figsize=(2.0 * sum(widths), 4.2), squeeze=False,
                             gridspec_kw={"width_ratios": widths})
    best, no_gain = 0.0, []
    for ax, hz in zip(axes[0], horizons):
        g = w[w["Horizon"] == hz]
        models = sort_labels(g["Base"])
        x = np.arange(len(models))
        before = [g.loc[(g["Base"] == m) & (g["model_dir"] == BEFORE), "bias"].mean() / _scale(hz) for m in models]
        after = [g.loc[(g["Base"] == m) & (g["model_dir"] == AFTER), "bias"].mean() / _scale(hz) for m in models]
        b1 = ax.bar(x - 0.2, before, 0.36, color=[colors(m) for m in models], alpha=0.35,
                    edgecolor=SURFACE, linewidth=0.8)
        b2 = ax.bar(x + 0.2, after, 0.36, color=[colors(m) for m in models], edgecolor=SURFACE, linewidth=0.8)
        bar_labels(ax, b1, _fmt(hz))
        bar_labels(ax, b2, _fmt(hz))
        for m, bf, af in zip(models, before, after):
            if bf < 0 and not np.isnan(af):
                best = max(best, 100 * (1 - af / bf))
            if not np.isnan(af) and abs(af) >= abs(bf):
                no_gain.append(f"{m.replace(', covariates', '')} {hz}")
        ax.axhline(0, color=INK2, linewidth=0.8)
        ax.set_xticks(x, [m.replace(", ", ",\n") for m in models])
        ax.set_xlim(-0.8, len(models) - 0.2)  # same bar width in every panel
        ax.set_title(hz.capitalize(), loc="left")
        ax.set_ylabel(f"Bias on '{bin_name}' days ({_unit(hz)})")
        tidy(ax)
        ax.margins(y=0.18)
    handles = [Patch(facecolor=MUTED, alpha=0.35, label="Before (original inputs)"),
               Patch(facecolor=MUTED, label="After (with extra features)")]
    fig.legend(handles=handles, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0))
    note = f" No gain for {', '.join(no_gain)}." if no_gain else ""
    headline(fig, f"The temperature-change feature cuts the cold-snap under-forecast by up to {best:.0f} %",
             f"Bias on days much colder than the week before (ordinary days of {SPLITS[split]}); closer to zero is "
             f"better.{note}")
    fig.subplots_adjust(top=0.80, bottom=0.2, wspace=0.35)
    return save(fig, out_dir, "foundation_fig_before_after_cold_snaps", formats)


def build(results_dir: Path = RESULTS_DIR, split: str = "test", tables_dir: Path = TABLES_DIR,
          out_dir: Path = FIGURES_DIR, formats=("png",), colors: Colors | None = None) -> None:
    formats = list(formats)
    runs = [r for r in discover_runs(results_dir, FOUNDATION_MODELS, split, include_naive=False)
            if r.model_dir in FOUNDATION_MODELS]
    if not runs:
        print("[foundation] no foundation runs found, foundation figures skipped")
        return
    colors = colors or Colors(r.label for r in runs)
    metrics = load_metrics(runs)

    pair = {(r.label, r.horizon_text): m for r, m in metrics.values() if r.model_dir == BEFORE}
    hz = "hourly 24 h"
    if (NOCOV, hz) in pair and (COV, hz) in pair:
        fig_covariates_by_day_type(pair[(NOCOV, hz)], pair[(COV, hz)], colors, out_dir, formats, hz)
    else:
        print(f"[foundation] covariate figure skipped: needs both TimesFM-3 runs at {hz}")

    weather_path = Path(tables_dir) / "weather_breakdown.csv"
    if not weather_path.exists():
        print(f"[foundation] before/after figure skipped, missing: {weather_path}")
        return
    try:
        fig_before_after(pd.read_csv(weather_path), colors, out_dir, formats, split=split)
    except ValueError as err:
        print(f"[foundation] before/after figure skipped: {err}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", choices=["val", "test"], default="test")
    p.add_argument("--formats", nargs="+", default=["png"])
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--tables-dir", type=Path, default=TABLES_DIR)
    p.add_argument("--out-dir", type=Path, default=FIGURES_DIR)
    args = p.parse_args()
    build(args.results_dir, args.split, args.tables_dir, args.out_dir, args.formats)


if __name__ == "__main__":
    main()