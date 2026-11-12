"""
The six report figures (analysis_plan.md, "Figures and Tables Checklist").

1. Forecast vs actual for a typical week, with the 80 % band (hourly).
2. Error removed vs the seasonal naive, per model and horizon.
3. Error and band coverage by day type, without vs with covariates (hourly).
4. Bias by temperature change against last week, per model and horizon.
5. Hour x month heatmap of MAE and bias (hourly).
6. Bias on "much colder" days before and after the extra features.

Each figure's title states its message, computed from the data. A figure whose
input file is missing is skipped with a note. Inputs are the files the other
scripts write; nothing is rerun.

Colours follow the model, the same in every figure: TimesFM-3 with covariates
blue, TabICL orange, TimesFM-3 without covariates aqua (validated categorical
order, colour-blind safe). Values are labelled on the bars, so colour never
carries meaning alone.

Usage (from the project root):

    uv run python src/analysis/foundation/report_figures.py
    uv run python src/analysis/foundation/report_figures.py --figures 1 5 --week-start 2024-03-11
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
FOUNDATION_DIR = SRC_DIR / "models" / "foundation"
if str(FOUNDATION_DIR) not in sys.path:
    sys.path.insert(0, str(FOUNDATION_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from models.foundation.data import DEFAULT_FORECAST_DIR, DEFAULT_RESULTS_DIR, QUANTILE_COLUMNS  # noqa: E402
from models.foundation.evaluate import DEFAULT_METRICS_DIR  # noqa: E402
from report_tables import DAY_TYPE_LABEL, horizon_text, run_info  # noqa: E402

# --------------------------------------------------------------------------
# Style (reference palette of the dataviz guidance, light mode)
# --------------------------------------------------------------------------

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8985", "#e4e3df"
MODEL_COLOR = {
    "TimesFM-3, covariates": "#2a78d6",
    "TabICL": "#eb6834",
    "TimesFM-3, no covariates": "#1baf7a",
}
MODEL_ORDER = ["TimesFM-3, no covariates", "TimesFM-3, covariates", "TabICL", "TabICL + extra features"]
HORIZON_ORDER = ["hourly 24 h", "daily 1 d", "daily 7 d"]
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
RED_RAMP = ["#fbe0df", "#f3a9a8", "#e34948", "#b02a2a"]  # red arm of the blue <-> red diverging pair
NEUTRAL = "#f0efec"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 9.5, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": GRID, "axes.titlesize": 10, "axes.titlecolor": INK, "axes.titleweight": "bold",
    "legend.frameon": False, "legend.fontsize": 9,
})


def color_of(model: str) -> str:
    base = model.replace(" + extra features", "")
    return MODEL_COLOR.get(base, MUTED)


def tidy(ax, grid_axis: str = "y"):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def headline(fig, title: str, subtitle: str):
    fig.text(0.01, 0.985, title, ha="left", va="top", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.01, 0.935, subtitle, ha="left", va="top", fontsize=9.5, color=INK2)


def save(fig, out_dir: Path, name: str, formats: list[str]) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in formats:
        path = out_dir / f"{name}.{ext}"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        paths.append(path)
    plt.close(fig)
    print(f"[figures] {name} -> {', '.join(p.name for p in paths)}")
    return paths


def bar_labels(ax, bars, fmt: str, horizontal: bool = False, inside_min: float | None = None):
    """Value at the end of each bar, in text ink (never the series colour)."""
    for b in bars:
        v = b.get_width() if horizontal else b.get_height()
        if np.isnan(v):
            continue
        if horizontal:
            ax.annotate(format(v, fmt), (v, b.get_y() + b.get_height() / 2), xytext=(4, 0),
                        textcoords="offset points", va="center", ha="left", fontsize=8.5, color=INK)
        else:
            off = 3 if v >= 0 else -3
            ax.annotate(format(v, fmt), (b.get_x() + b.get_width() / 2, v), xytext=(0, off),
                        textcoords="offset points", ha="center", va="bottom" if v >= 0 else "top",
                        fontsize=8, color=INK)


def grouped_bars(ax, groups: list[str], series: list[str], values: dict, width: float = 0.8,
                 hatch_of=None, alpha_of=None, fmt: str = ".0f"):
    """Vertical grouped bars: values[(group, series)] -> number."""
    n = len(series)
    w = width / n
    x = np.arange(len(groups))
    for i, s in enumerate(series):
        vals = [values.get((g, s), np.nan) for g in groups]
        bars = ax.bar(x - width / 2 + w * (i + 0.5), vals, w * 0.88, color=color_of(s),
                      hatch=hatch_of(s) if hatch_of else None, edgecolor=SURFACE, linewidth=0.8,
                      alpha=alpha_of(s) if alpha_of else 1.0, label=s)
        bar_labels(ax, bars, fmt)
    ax.set_xticks(x, groups)
    return x


# --------------------------------------------------------------------------
# Figure 1: typical week
# --------------------------------------------------------------------------


def fig_week(path: Path, week_start: str | None, out_dir: Path, formats: list[str]):
    fc = pd.read_csv(path)
    if fc["y_true"].isna().all():
        raise ValueError(f"{path.name} has no y_true: run evaluate.py on it first")
    fc["t"] = pd.to_datetime(fc["target_time"], utc=True).dt.tz_convert("Europe/Berlin")
    fc["day"] = pd.to_datetime(fc["origin"], utc=True).dt.tz_convert("Europe/Berlin").dt.normalize()
    fc["ae"] = (fc["y_pred"] - fc["y_true"]).abs()

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
    color = MODEL_COLOR["TimesFM-3, covariates"]
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
             f"TimesFM-3 with covariates, day-ahead forecasts issued at midnight, "
             f"{start:%d %b} to {end:%d %b %Y}. Shaded: 80 % band.")
    fig.subplots_adjust(top=0.82)
    return save(fig, out_dir, "fig1_typical_week", formats)


# --------------------------------------------------------------------------
# Figure 2: skill per model and horizon
# --------------------------------------------------------------------------


def fig_skill(summary_path: Path, extra_path: Path | None, out_dir: Path, formats: list[str]):
    s = pd.read_csv(summary_path)
    s = s[(s["split"] == "test") & (s["experiment"] != "baseline")].copy()
    s["Model"] = [run_info(Path(f).stem)["model"] for f in s["file"]]
    if extra_path and extra_path.exists():
        e = pd.read_csv(extra_path)
        e = e[(e["split"] == "test") & (e["experiment"] == "F6")].copy()
        e["Model"] = "TabICL + extra features"
        s = pd.concat([s, e], ignore_index=True)
    s["Horizon"] = [horizon_text(r, h) for r, h in zip(s["resolution"], s["horizon"])]
    s["skill"] = 100 * s["MAE_skill"]

    models = [m for m in MODEL_ORDER if m in set(s["Model"])]
    horizons = [hz for hz in HORIZON_ORDER if hz in set(s["Horizon"])]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    h = 0.8 / len(models)
    y0 = np.arange(len(horizons))[::-1]
    seen = set()
    for yc, hz in zip(y0, horizons):
        present = [m for m in models if ((s["Model"] == m) & (s["Horizon"] == hz)).any()]
        for i, m in enumerate(present):
            v = s.loc[(s["Model"] == m) & (s["Horizon"] == hz), "skill"].mean()
            ypos = yc + h * (len(present) / 2 - i - 0.5)
            bars = ax.barh([ypos], [v], h * 0.85, color=color_of(m), hatch="////" if "extra" in m else None,
                           edgecolor=SURFACE, linewidth=0.8, label=None if m in seen else m)
            seen.add(m)
            bar_labels(ax, bars, ".0f", horizontal=True)
    ax.set_yticks(y0, [hz.capitalize() for hz in horizons])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Error removed compared with the seasonal naive benchmark (%)")
    tidy(ax, "x")
    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index(m) for m in models if m in labels]
    ax.legend([handles[i] for i in order], [labels[i] for i in order], loc="lower right")
    lo, hi = s["skill"].min(), s["skill"].max()
    headline(fig, f"Every model removes {lo:.0f} to {hi:.0f} % of the benchmark's error, without training",
             "Test year 2024. Benchmark: the same hour or day one week before. Hatched: TabICL with the "
             "extra features.")
    fig.subplots_adjust(top=0.84)
    return save(fig, out_dir, "fig2_skill_by_model", formats)


# --------------------------------------------------------------------------
# Figure 3: day types
# --------------------------------------------------------------------------


def fig_day_types(nocov_path: Path, cov_path: Path, out_dir: Path, formats: list[str]):
    runs = {"TimesFM-3, no covariates": json.loads(nocov_path.read_text()),
            "TimesFM-3, covariates": json.loads(cov_path.read_text())}
    types = [t for t in DAY_TYPE_LABEL if all((r.get("by_day_type") or {}).get(t) for r in runs.values())]
    wrap = lambda t: DAY_TYPE_LABEL[t].replace(" / ", "/\n").replace("Normal ", "Normal\n").replace(  # noqa: E731
        "Bridge ", "Bridge\n")
    labels = [wrap(t) for t in types]
    series = list(runs)
    mape = {(wrap(t), m): r["by_day_type"][t]["MAPE_%"] for m, r in runs.items() for t in types}
    cover = {(wrap(t), m): r["by_day_type"][t]["coverage80_%"] for m, r in runs.items() for t in types}

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
    grouped_bars(a1, labels, series, mape, fmt=".1f")
    a1.set_ylabel("Average error (MAPE, %)")
    a1.set_title("Error", loc="left")
    tidy(a1)
    grouped_bars(a2, labels, series, cover, fmt=".0f")
    a2.axhline(80, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    a2.annotate("target\n80 %", (1.0, 80), xycoords=("axes fraction", "data"), xytext=(4, 0),
                textcoords="offset points", ha="left", va="center", fontsize=8.5, color=INK2)
    a2.set_ylim(0, 105)
    a2.set_ylabel("Actual inside the 80 % band (%)")
    a2.set_title("Band coverage", loc="left")
    tidy(a2)
    handles = [Patch(color=color_of(m), label=m) for m in series]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), bbox_to_anchor=(0.5, -0.02))

    hol = "holiday" if "holiday" in types else types[-1]
    nc, cv = runs["TimesFM-3, no covariates"]["by_day_type"][hol], runs["TimesFM-3, covariates"]["by_day_type"][hol]
    cut = 100 * (1 - cv["MAE"] / nc["MAE"])
    headline(fig, f"Holiday covariates cut the holiday error by {cut:.0f} % and make the band usable",
             f"Hourly 24 h, TimesFM-3, test year 2024. Holiday band coverage rises from "
             f"{nc['coverage80_%']:.0f} % to {cv['coverage80_%']:.0f} %.")
    fig.subplots_adjust(top=0.80, bottom=0.2, wspace=0.28)
    return save(fig, out_dir, "fig3_day_types", formats)


# --------------------------------------------------------------------------
# Figures 4 and 6: weather change
# --------------------------------------------------------------------------


def _weather_frame(path: Path) -> pd.DataFrame:
    w = pd.read_csv(path)
    w["tag"] = w["run"].str.extract(r"\[(.+)\]$")[0]
    base = w["run"].str.replace(r" \[.+\]$", "", regex=True)
    infos = base.map(run_info)
    w["Model"] = infos.map(lambda i: i["model"])
    w["Horizon"] = infos.map(lambda i: horizon_text(i["resolution"], i["horizon"]))
    return w[w["Model"] != "Seasonal naive"]


def _unit(horizon: str) -> str:
    return "MWh per hour" if horizon.startswith("hourly") else "GWh per day"


def _scale(horizon: str) -> float:
    """Daily values are shown in GWh, so the bar labels stay short."""
    return 1.0 if horizon.startswith("hourly") else 1000.0


def _fmt(horizon: str) -> str:
    return ",.0f" if horizon.startswith("hourly") else ".1f"


def fig_weather_change(path: Path, out_dir: Path, formats: list[str]):
    w = _weather_frame(path)
    if w["tag"].notna().any():  # an old-vs-new file: use the original runs
        w = w[w["tag"] == "results"]
    w = w[w["variable"] == "hdd_change_vs_last_week"]
    bins = ["much warmer", "similar", "much colder"]
    horizons = [h for h in HORIZON_ORDER if h in set(w["Horizon"])]
    fig, axes = plt.subplots(1, len(horizons), figsize=(4.2 * len(horizons), 4.4), squeeze=False)
    for ax, hz in zip(axes[0], horizons):
        g = w[w["Horizon"] == hz]
        models = [m for m in MODEL_ORDER if m in set(g["Model"])]
        vals = {(b.capitalize(), m): g.loc[(g["bin"] == b) & (g["Model"] == m), "bias"].mean() / _scale(hz)
                for b in bins for m in models}
        grouped_bars(ax, [b.capitalize() for b in bins], models, vals, fmt=_fmt(hz))
        ax.axhline(0, color=INK2, linewidth=0.8)
        ax.set_title(hz.capitalize(), loc="left")
        ax.set_ylabel(f"Bias ({_unit(hz)})")
        tidy(ax)
        ax.margins(y=0.15)
    handles = [Patch(color=color_of(m), label=m) for m in MODEL_ORDER if m in set(w["Model"])]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), bbox_to_anchor=(0.5, -0.03))
    headline(fig, "All models lag behind the weather: too low when it turns colder, too high when warmer",
             "Temperature change = heating degrees vs the same time one week before. Bias = forecast minus "
             "actual. Ordinary days of 2024, observed weather as input.")
    fig.subplots_adjust(top=0.80, bottom=0.17, wspace=0.35)
    return save(fig, out_dir, "fig4_bias_by_temperature_change", formats)


def fig_before_after(path: Path, out_dir: Path, formats: list[str], bin_name: str = "much colder"):
    w = _weather_frame(path)
    w = w[(w["variable"] == "hdd_change_vs_last_week") & (w["bin"] == bin_name) & w["tag"].notna()]
    if w.empty:
        raise ValueError(f"{path.name} has no runs tagged [results] / [extra_features]")
    horizons = [h for h in HORIZON_ORDER if h in set(w["Horizon"])]
    widths = [max(1, w.loc[w["Horizon"] == h, "Model"].nunique()) + 0.6 for h in horizons]
    fig, axes = plt.subplots(1, len(horizons), figsize=(2.0 * sum(widths), 4.2), squeeze=False,
                             gridspec_kw={"width_ratios": widths})
    best, no_gain = 0.0, []
    for ax, hz in zip(axes[0], horizons):
        g = w[w["Horizon"] == hz]
        models = [m for m in MODEL_ORDER if m in set(g["Model"])]
        x = np.arange(len(models))
        before = [g.loc[(g["Model"] == m) & (g["tag"] == "results"), "bias"].mean() / _scale(hz) for m in models]
        after = [g.loc[(g["Model"] == m) & (g["tag"] == "extra_features"), "bias"].mean() / _scale(hz)
                 for m in models]
        b1 = ax.bar(x - 0.2, before, 0.36, color=[color_of(m) for m in models], alpha=0.35,
                    edgecolor=SURFACE, linewidth=0.8)
        b2 = ax.bar(x + 0.2, after, 0.36, color=[color_of(m) for m in models], edgecolor=SURFACE, linewidth=0.8)
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
             f"Bias on days much colder than the week before (ordinary days of 2024); closer to zero is "
             f"better.{note}")
    fig.subplots_adjust(top=0.80, bottom=0.2, wspace=0.35)
    return save(fig, out_dir, "fig6_before_after_cold_snaps", formats)


# --------------------------------------------------------------------------
# Figure 5: hour x month heatmap
# --------------------------------------------------------------------------


def fig_heatmap(path: Path, out_dir: Path, formats: list[str]):
    d = pd.read_csv(path, header=[0, 1], index_col=0)
    d.columns = pd.MultiIndex.from_tuples([(a, int(b)) for a, b in d.columns])
    mae, bias = d["MAE"].sort_index(), d["bias"].sort_index()
    months = [MONTHS[m - 1] for m in mae.columns]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5.4))
    seq = LinearSegmentedColormap.from_list("seq_blue", BLUE_RAMP)
    im1 = a1.imshow(mae.to_numpy(), aspect="auto", cmap=seq, origin="upper")
    lim = np.nanmax(np.abs(bias.to_numpy()))
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
    headline(fig, f"Errors peak around {peak:02d}:00, {ratio:.1f} times the error at {low:02d}:00: "
                  "midday, when rooftop solar shapes the load, is the hardest time",
             "Hourly 24 h, TimesFM-3 with covariates, ordinary days of 2024. The hour equals the lead time "
             "for a midnight forecast, so the evening decline rules out a pure lead-time effect.")
    fig.subplots_adjust(top=0.84, wspace=0.18)
    return save(fig, out_dir, "fig5_hour_month_heatmap", formats)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> None:
    m, f = DEFAULT_METRICS_DIR, DEFAULT_FORECAST_DIR
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--figures", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6])
    p.add_argument("--hourly-forecast", type=Path, default=f / "timesfm3_zs_cov_hourly_24h_ctx8192_test.csv")
    p.add_argument("--week-start", default=None, help="Monday of the week in figure 1 (YYYY-MM-DD); "
                                                     "default: the week closest to the median error")
    p.add_argument("--summary", type=Path, default=m / "summary_foundation.csv")
    p.add_argument("--extra-summary", type=Path,
                   default=DEFAULT_RESULTS_DIR / "extra_features" / "metrics" / "summary_foundation.csv")
    p.add_argument("--nocov-metrics", type=Path, default=m / "timesfm3_zs_nocov_hourly_24h_ctx8192_test.json")
    p.add_argument("--cov-metrics", type=Path, default=m / "timesfm3_zs_cov_hourly_24h_ctx8192_test.json")
    p.add_argument("--weather", type=Path, default=m / "weather_breakdown.csv")
    p.add_argument("--old-vs-new", type=Path, default=m / "weather_breakdown_old_vs_new.csv")
    p.add_argument("--heatmap", type=Path, default=m / "weather_hour_month_timesfm3_zs_cov_hourly_24h_ctx8192_test.csv")
    p.add_argument("--formats", nargs="+", default=["png"], help="e.g. png svg pdf")
    p.add_argument("--out-dir", type=Path, default=m / "report" / "figures")
    args = p.parse_args()

    jobs = {
        1: ([args.hourly_forecast], lambda: fig_week(args.hourly_forecast, args.week_start, args.out_dir, args.formats)),
        2: ([args.summary], lambda: fig_skill(args.summary, args.extra_summary, args.out_dir, args.formats)),
        3: ([args.nocov_metrics, args.cov_metrics],
            lambda: fig_day_types(args.nocov_metrics, args.cov_metrics, args.out_dir, args.formats)),
        4: ([args.weather], lambda: fig_weather_change(args.weather, args.out_dir, args.formats)),
        5: ([args.heatmap], lambda: fig_heatmap(args.heatmap, args.out_dir, args.formats)),
        6: ([args.old_vs_new], lambda: fig_before_after(args.old_vs_new, args.out_dir, args.formats)),
    }
    for n in args.figures:
        inputs, make = jobs[n]
        missing = [str(pth) for pth in inputs if not pth.exists()]
        if missing:
            print(f"[figures] figure {n} skipped, missing: {', '.join(missing)}")
            continue
        make()


if __name__ == "__main__":
    main()