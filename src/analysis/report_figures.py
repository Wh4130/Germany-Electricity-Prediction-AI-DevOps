"""
The report figures over every model (analysis_plan.md, "Figures and Tables Checklist").

1. Forecast vs actual for a typical week of one hourly run (default: the hourly
   24 h run with the lowest MAE), with the 80 % band when the run has quantiles.
2. Error removed vs the seasonal naive, per model and horizon.
3. Error by day type, per model (one panel per horizon).
4. Bias by temperature change against last week, per model and horizon.
5. Hour x month heatmap of MAE and bias of one hourly run (default as in 1).

Each figure's title states its message, computed from the data. A figure whose
input is missing is skipped with a note. Inputs are the files the other
scripts write (metrics JSONs, ``weather_breakdown.csv``, the hour x month
tables); nothing is rerun. Figures go to ``src/results/final_report/figures``.

Model-specific figures live next to the model's analysis, e.g.
``src.analysis.foundation.report_figures``.

Usage (from the project root):

    uv run python -m src.analysis.report_figures
    uv run python -m src.analysis.report_figures --figures 1 5 --run sarimax/sarimax_hourly_24h_test --week-start 2024-03-11
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Patch

from src.common.dataset import QUANTILE_COLUMNS, SPLITS
from src.common.paths import FIGURES_DIR, RESULTS_DIR, TABLES_DIR
from src.analysis.plotting import (BLUE_RAMP, GRID, INK, INK2, MONTHS, NEUTRAL, RED_RAMP, SURFACE, Colors,
                                   bar_labels, grouped_bars, hatch_of, headline, plt, save, tidy)
from src.analysis.report_tables import DAY_TYPE_LABEL, load_metrics, summary_frame
from src.analysis.runs import Run, discover_runs, sort_horizons, sort_labels
from src.analysis.weather_breakdown import HOUR_MONTH_DIR


def legend_handles(models: list[str], colors: Colors) -> list[Patch]:
    return [Patch(facecolor=colors(m), hatch=hatch_of(m), edgecolor=SURFACE, label=m) for m in models]


def _unit(horizon: str) -> str:
    return "MWh per hour" if horizon.startswith("hourly") else "GWh per day"


def _scale(horizon: str) -> float:
    """Daily values are shown in GWh, so the bar labels stay short."""
    return 1.0 if horizon.startswith("hourly") else 1000.0


def _fmt(horizon: str) -> str:
    return ",.0f" if horizon.startswith("hourly") else ".1f"


def best_run(summary: pd.DataFrame, runs: dict[str, Run], resolution: str = "hourly",
             horizon: int | None = 24) -> Run | None:
    """The non-naive run with the lowest MAE at this resolution (and horizon)."""
    s = summary[(summary["resolution"] == resolution) & ~summary["is_naive"]]
    if horizon is not None and (s["horizon"] == horizon).any():
        s = s[s["horizon"] == horizon]
    return runs[s.sort_values("MAE").iloc[0]["run"]] if len(s) else None


# --------------------------------------------------------------------------
# Figure 1: typical week
# --------------------------------------------------------------------------


def fig_week(run: Run, week_start: str | None, colors: Colors, out_dir: Path, formats: list[str]):
    fc = pd.read_csv(run.forecast_path)
    if fc["y_true"].isna().all():
        raise ValueError(f"{run.id} has no y_true: run `python -m src.analysis.evaluate` on it first")
    fc["t"] = pd.to_datetime(fc["target_time"], utc=True).dt.tz_convert("Europe/Berlin")
    origin = pd.to_datetime(fc["origin"], utc=True).dt.tz_convert("Europe/Berlin")
    # One forecast per hour: the day-ahead forecasts issued at local midnight, else the 1-step forecasts.
    midnight = origin.dt.hour == 0
    fc, origin = (fc[midnight], origin[midnight]) if midnight.any() else (fc[fc["step"] == 1], origin[fc["step"] == 1])
    issued = "day-ahead forecasts issued at midnight" if midnight.any() else "1-step forecasts"
    fc = fc.assign(day=fc["t"].dt.normalize(), ae=(fc["y_pred"] - fc["y_true"]).abs())

    day_mae = fc.groupby("day")["ae"].mean()
    if week_start:
        start = pd.Timestamp(week_start, tz="Europe/Berlin")
    else:
        # The Monday-to-Sunday week whose error is closest to the median week.
        weekly = day_mae.rolling(7).mean().shift(-6).dropna()
        weekly = weekly[weekly.index.dayofweek == 0]
        start = (weekly - weekly.median()).abs().idxmin()
    week = fc[(fc["day"] >= start) & (fc["day"] < start + pd.Timedelta(days=7))].sort_values("t")
    mape = 100 * (week["ae"] / week["y_true"]).mean()

    fig, ax = plt.subplots(figsize=(10, 4.2))
    color = colors(run.label)
    has_band = set(QUANTILE_COLUMNS) <= set(week) and week[QUANTILE_COLUMNS[0]].notna().any()
    if has_band:
        ax.fill_between(week["t"], week[QUANTILE_COLUMNS[0]] / 1000, week[QUANTILE_COLUMNS[-1]] / 1000,
                        color=color, alpha=0.18, linewidth=0, label="80 % band")
    ax.plot(week["t"], week["y_true"] / 1000, color=INK, linewidth=1.6, label="Actual load")
    ax.plot(week["t"], week["y_pred"] / 1000, color=color, linewidth=1.6, label="Forecast")
    days = pd.date_range(start, periods=7, freq="D")
    ax.set_xticks(days + pd.Timedelta(hours=12), [d.strftime("%a %d %b") for d in days])
    for d in days[1:]:
        ax.axvline(d, color=GRID, linewidth=0.6)
    ax.set_xlim(days[0], days[-1] + pd.Timedelta(days=1))
    ax.set_ylabel("Load (GW)")
    tidy(ax)
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.02), ncol=3)
    end = start + pd.Timedelta(days=6)
    headline(fig, f"In a typical week, the hourly forecast is off by {mape:.1f} % on average",
             f"{run.label}, {issued}, {start:%d %b} to {end:%d %b %Y}." + (" Shaded: 80 % band." if has_band else ""))
    fig.subplots_adjust(top=0.82)
    return save(fig, out_dir, "fig1_typical_week", formats)


# --------------------------------------------------------------------------
# Figure 2: skill per model and horizon
# --------------------------------------------------------------------------


def fig_skill(summary: pd.DataFrame, colors: Colors, out_dir: Path, formats: list[str], split: str = "test"):
    s = summary[(summary["split"] == split) & ~summary["is_naive"]].copy()
    s["skill"] = 100 * s["MAE_skill"].astype(float)
    models = sort_labels(s["Model"])
    horizons = sort_horizons(s["Horizon"])
    fig, ax = plt.subplots(figsize=(9, 1.0 + 0.32 * len(s) + 0.4 * len(horizons)))
    y0 = np.arange(len(horizons))[::-1].astype(float)
    group = 0.8
    for yc, hz in zip(y0, horizons):
        present = [m for m in models if ((s["Model"] == m) & (s["Horizon"] == hz)).any()]
        h = min(group / len(present), 0.2)  # bars no thicker than in a group of four
        for i, m in enumerate(present):
            v = s.loc[(s["Model"] == m) & (s["Horizon"] == hz), "skill"].mean()
            ypos = yc + h * (len(present) / 2 - i - 0.5)
            bars = ax.barh([ypos], [v], h * 0.85, color=colors(m), hatch=hatch_of(m), edgecolor=SURFACE,
                           linewidth=0.8)
            bar_labels(ax, bars, ".0f", horizontal=True)
    ax.set_yticks(y0, [hz.capitalize() for hz in horizons])
    lo, hi = s["skill"].min(), s["skill"].max()
    ax.set_xlim(min(0, lo - 10), max(100, hi + 10) if hi > 90 else 100)
    ax.axvline(0, color=INK2, linewidth=0.8)
    ax.set_xlabel("Error removed compared with the seasonal naive benchmark (%)")
    tidy(ax, "x")
    ax.legend(handles=legend_handles(models, colors), loc="lower right")
    title = (f"Every model removes {lo:.0f} to {hi:.0f} % of the benchmark's error" if lo > 0 else
             f"Error removed vs the benchmark ranges from {lo:.0f} to {hi:.0f} %")
    headline(fig, title, f"{split.capitalize()} year {SPLITS[split]}. Benchmark: the same hour or day one week "
                         "before. Hatched: a model variant.")
    fig.subplots_adjust(top=1 - 0.75 / fig.get_figheight())
    return save(fig, out_dir, "fig2_skill_by_model", formats)


# --------------------------------------------------------------------------
# Figure 3: day types
# --------------------------------------------------------------------------


def _wrap(t: str) -> str:
    return DAY_TYPE_LABEL[t].replace(" / ", "/\n").replace("Normal ", "Normal\n").replace("Bridge ", "Bridge\n")


def fig_day_types(metrics: dict, colors: Colors, out_dir: Path, formats: list[str]):
    rows = [(r.horizon_text, r.label, t, d["MAPE_%"]) for r, m in metrics.values() if not r.is_naive
            for t, d in (m.get("by_day_type") or {}).items() if d]
    if not rows:
        raise ValueError("no day-type metrics")
    df = pd.DataFrame(rows, columns=["Horizon", "Model", "type", "MAPE"])
    horizons = sort_horizons(df["Horizon"])
    fig, axes = plt.subplots(1, len(horizons), figsize=(max(5.5, 4.6 * len(horizons)), 4.6), squeeze=False)
    for ax, hz in zip(axes[0], horizons):
        g = df[df["Horizon"] == hz]
        types = [t for t in DAY_TYPE_LABEL if t in set(g["type"])]
        models = sort_labels(g["Model"])
        vals = {(_wrap(t), m): v for _, (_, m, t, v) in g.iterrows()}
        grouped_bars(ax, [_wrap(t) for t in types], models, vals, colors, fmt=".1f")
        ax.set_title(hz.capitalize(), loc="left")
        ax.set_ylabel("Average error (MAPE, %)")
        ax.tick_params(axis="x", labelsize=8)
        tidy(ax)
    models = sort_labels(df["Model"])
    fig.legend(handles=legend_handles(models, colors), loc="lower center", ncol=min(len(models), 4),
               bbox_to_anchor=(0.5, -0.04))

    worst = df.loc[df.groupby(["Horizon", "Model"])["MAPE"].idxmax(), "type"]
    if worst.nunique() == 1:
        title = f"{DAY_TYPE_LABEL[worst.iloc[0]]}s are the hardest days for every model and horizon"
    else:
        top = worst.value_counts().index[0]
        title = (f"{DAY_TYPE_LABEL[top]}s are the hardest days for {worst.value_counts().iloc[0]} of "
                 f"{len(worst)} runs")
    normal = df[df["type"] == "normal_weekday"]["MAPE"].mean()
    headline(fig, title, f"MAPE by day type of the target. Normal weekdays: {normal:.1f} % on average over all runs.")
    fig.subplots_adjust(top=0.80, bottom=0.24, wspace=0.28)
    return save(fig, out_dir, "fig3_error_by_day_type", formats)


# --------------------------------------------------------------------------
# Figure 4: weather change
# --------------------------------------------------------------------------


def fig_weather_change(weather: pd.DataFrame, colors: Colors, out_dir: Path, formats: list[str],
                       split: str = "test"):
    w = weather[(weather["variable"] == "hdd_change_vs_last_week") & (weather["split"] == split)]
    if w.empty:
        raise ValueError("no hdd_change_vs_last_week rows")
    bins = ["much warmer", "similar", "much colder"]
    horizons = sort_horizons(w["Horizon"])
    fig, axes = plt.subplots(1, len(horizons), figsize=(max(5, 4.2 * len(horizons)), 4.4), squeeze=False)
    for ax, hz in zip(axes[0], horizons):
        g = w[w["Horizon"] == hz]
        models = sort_labels(g["Model"])
        vals = {(b.capitalize(), m): g.loc[(g["bin"] == b) & (g["Model"] == m), "bias"].mean() / _scale(hz)
                for b in bins for m in models}
        grouped_bars(ax, [b.capitalize() for b in bins], models, vals, colors, fmt=_fmt(hz))
        ax.axhline(0, color=INK2, linewidth=0.8)
        ax.set_title(hz.capitalize(), loc="left")
        ax.set_ylabel(f"Bias ({_unit(hz)})")
        tidy(ax)
        ax.margins(y=0.15)
    models = sort_labels(w["Model"])
    fig.legend(handles=legend_handles(models, colors), loc="lower center", ncol=min(len(models), 4),
               bbox_to_anchor=(0.5, -0.04))

    by = w.pivot_table(index=["run"], columns="bin", values="bias")
    lag = ((by.get("much colder", pd.Series(dtype=float)) < 0) & (by.get("much warmer", pd.Series(dtype=float)) > 0))
    if len(lag) and lag.all():
        title = "All models lag behind the weather: too low when it turns colder, too high when warmer"
    else:
        title = (f"{int(lag.sum())} of {len(lag)} runs lag behind the weather "
                 "(too low when it turns colder, too high when warmer)")
    headline(fig, title, "Temperature change = heating degrees vs the same time one week before. Bias = forecast "
                         f"minus actual. Ordinary days of {SPLITS[split]}, observed weather as input.")
    fig.subplots_adjust(top=0.80, bottom=0.2, wspace=0.35)
    return save(fig, out_dir, "fig4_bias_by_temperature_change", formats)


# --------------------------------------------------------------------------
# Figure 5: hour x month heatmap
# --------------------------------------------------------------------------


def fig_heatmap(path: Path, run: Run, out_dir: Path, formats: list[str]):
    d = pd.read_csv(path, header=[0, 1], index_col=0)
    d.columns = pd.MultiIndex.from_tuples([(a, int(b)) for a, b in d.columns])
    mae, bias = d["MAE"].sort_index(), d["bias"].sort_index()
    months = [MONTHS[m - 1] for m in mae.columns]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5.4))
    seq = LinearSegmentedColormap.from_list("seq_blue", BLUE_RAMP)
    im1 = a1.imshow(mae.to_numpy(), aspect="auto", cmap=seq, origin="upper")
    lim = np.nanmax(np.abs(bias.to_numpy())) or 1.0
    div = LinearSegmentedColormap.from_list("div", BLUE_RAMP[::-1][:5] + [NEUTRAL] + RED_RAMP)
    im2 = a2.imshow(bias.to_numpy(), aspect="auto", cmap=div, norm=TwoSlopeNorm(0, -lim, lim), origin="upper")
    for ax, title in ((a1, "Average error (MWh per hour)"), (a2, "Bias (MWh per hour): red = too high, blue = too low")):
        ax.set_xticks(range(len(months)), months)
        ax.set_yticks(range(0, 24, 3), [f"{h:02d}:00" for h in range(0, 24, 3)])
        ax.set_title(title, loc="left")
        ax.tick_params(length=0)
        for side in ax.spines.values():
            side.set_visible(False)
    a1.set_ylabel("Hour of the day (local time)")
    for im, ax in ((im1, a1), (im2, a2)):
        cb = fig.colorbar(im, ax=ax, shrink=0.85)
        cb.outline.set_visible(False)
        cb.ax.tick_params(length=0, colors=INK2)

    by_hour = mae.mean(axis=1)
    peak, low = int(by_hour.idxmax()), int(by_hour.idxmin())
    ratio = by_hour.max() / by_hour.min()
    tail = (": midday, when rooftop solar shapes the load, is the hardest time" if 10 <= peak <= 15 else "")
    headline(fig, f"Errors peak around {peak:02d}:00, {ratio:.1f} times the error at {low:02d}:00{tail}",
             f"{run.display}, ordinary days of {SPLITS[run.split]}.")
    fig.subplots_adjust(top=0.84, wspace=0.18)
    return save(fig, out_dir, "fig5_hour_month_heatmap", formats)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def build(runs: list[Run], figures=(1, 2, 3, 4, 5), split: str = "test", run_id: str | None = None,
          week_start: str | None = None, tables_dir: Path = TABLES_DIR, out_dir: Path = FIGURES_DIR,
          formats=("png",), colors: Colors | None = None) -> None:
    formats = list(formats)
    runs = [r for r in runs if r.split == split]
    colors = colors or Colors(r.label for r in runs)
    metrics = load_metrics(runs)
    if not metrics:
        print("[figures] no metrics found: run `python -m src.analysis.evaluate` first")
        return
    summary = summary_frame(metrics)
    by_id = {r.id: r for r, _ in metrics.values()}
    hourly = by_id.get(run_id) if run_id else best_run(summary, by_id)
    if run_id and hourly is None:
        print(f"[figures] note: run {run_id} not found among the {split} runs")
    weather_path = Path(tables_dir) / "weather_breakdown.csv"

    def need(cond, what):
        if not cond:
            print(f"[figures] skipped, missing: {what}")
        return cond

    for n in figures:
        if n == 1 and need(hourly is not None, "an hourly run"):
            fig_week(hourly, week_start, colors, out_dir, formats)
        elif n == 2:
            fig_skill(summary, colors, out_dir, formats, split)
        elif n == 3:
            fig_day_types(metrics, colors, out_dir, formats)
        elif n == 4 and need(weather_path.exists(), str(weather_path)):
            fig_weather_change(pd.read_csv(weather_path), colors, out_dir, formats, split)
        elif n == 5 and need(hourly is not None, "an hourly run"):
            path = Path(tables_dir) / HOUR_MONTH_DIR / f"{hourly.safe_id}.csv"
            if need(path.exists(), str(path)):
                fig_heatmap(path, hourly, out_dir, formats)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--figures", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    p.add_argument("--models", nargs="+", default=None, help="results folders (default: all)")
    p.add_argument("--split", choices=["val", "test"], default="test")
    p.add_argument("--run", default=None, help="hourly run of figures 1 and 5 (<model folder>/<file stem>); "
                                               "default: the hourly 24 h run with the lowest MAE")
    p.add_argument("--week-start", default=None, help="Monday of the week in figure 1 (YYYY-MM-DD); "
                                                     "default: the week closest to the median error")
    p.add_argument("--formats", nargs="+", default=["png"], help="e.g. png svg pdf")
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--tables-dir", type=Path, default=TABLES_DIR)
    p.add_argument("--out-dir", type=Path, default=FIGURES_DIR)
    args = p.parse_args()
    runs = discover_runs(args.results_dir, args.models, args.split)
    build(runs, args.figures, args.split, args.run, args.week_start, args.tables_dir, args.out_dir, args.formats)


if __name__ == "__main__":
    main()