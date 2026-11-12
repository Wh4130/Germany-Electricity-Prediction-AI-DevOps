"""
The worst forecast days of the evaluation year, with the likely reason.

For every forecast file the error is grouped by the local date of the target:

- hourly runs: the 24 hours of the day,
- daily runs: the day itself (7 d runs: the up-to-7 forecasts of that day,
  one per lead day, averaged).

The N days with the largest MAE are listed with their calendar and weather
context and rule-based tags:

- calendar: Holiday, Bridge day, Christmas / New Year, Holiday week, DST change,
  and Weekend (context only, not counted as an explanation),
- weather: Much colder / Much warmer than last week (daily mean HDD minus the
  same day one week before; top / bottom 20 % of the heating-season days of
  the year),
- market: Price spike (daily mean day-ahead price in the top 5 % of the year).

A day without any tag has no obvious explanation in our inputs, which is a
finding in itself.

Also written: how much of the yearly error the N worst days cause, how many of
them carry a calendar or weather tag, and the dates that are among the worst
for several models.

Usage (from the project root):

    uv run python src/analysis/foundation/worst_days.py \
        src/results/forecasts/timesfm3_zs_*_test.csv src/results/forecasts/tabicl_default_*_ctxall_test.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
FOUNDATION_DIR = SRC_DIR / "models" / "foundation"
if str(FOUNDATION_DIR) not in sys.path:
    sys.path.insert(0, str(FOUNDATION_DIR))

import numpy as np
import pandas as pd

from models.foundation.data import DAY_AHEAD_PRICE, DEFAULT_DATA_DIR, QUANTILE_COLUMNS, SPLITS
from models.foundation.evaluate import DEFAULT_METRICS_DIR
from report_tables import Report, horizon_text, run_info
from weather_breakdown import load_rows, run_names

RADIATION = {"hourly": "shortwave_radiation", "daily": "shortwave_radiation_sum"}
SPECIAL_TAGS = ["Holiday", "Bridge day", "Christmas / New Year", "Holiday week", "DST change"]
WEATHER_TAGS = ["Much colder than last week", "Much warmer than last week"]
MARKET_TAGS = ["Price spike"]


def day_context(frame, split: str) -> pd.DataFrame:
    """Calendar, weather and price of every local date, with the tags."""
    df, res = frame.df, frame.resolution
    date = frame.local_date.to_numpy()
    flags = {c: df[c].to_numpy() > 0.5 for c in
             ("is_holiday", "is_bridge_day", "is_christmas_new_year", "is_dst_transition_day") if c in df}
    if "holiday_week" in df:
        flags["holiday_week"] = df["holiday_week"].to_numpy() > 0.5
    g = pd.DataFrame({"date": date, "hdd": df["hdd"].to_numpy(float),
                      "price": df[DAY_AHEAD_PRICE[res]].to_numpy(float),
                      "radiation": df[RADIATION[res]].to_numpy(float), **flags}).groupby("date")
    ctx = g[["hdd", "price", "radiation"]].mean()
    ctx = ctx.join(g[list(flags)].any())
    ctx.index = pd.DatetimeIndex(ctx.index)
    ctx["weekday"] = ctx.index.day_name().str[:3]

    # Weather change against the same day one week before (dates are consecutive).
    ctx["hdd_change"] = ctx["hdd"] - ctx["hdd"].shift(7)
    year = ctx.index.year == SPLITS[split]
    season = year & ((ctx["hdd"] > 0) | (ctx["hdd"].shift(7) > 0)).to_numpy()
    q20, q80 = np.nanquantile(ctx.loc[season, "hdd_change"], [0.2, 0.8])
    p95 = np.nanquantile(ctx.loc[year, "price"], 0.95)

    rules = {
        "Holiday": ctx.get("is_holiday"),
        "Bridge day": ctx.get("is_bridge_day"),
        "Christmas / New Year": ctx.get("is_christmas_new_year"),
        "Holiday week": ctx.get("holiday_week"),
        "Weekend": pd.Series(ctx.index.dayofweek >= 5, index=ctx.index),
        "DST change": ctx.get("is_dst_transition_day"),
        "Much colder than last week": season & (ctx["hdd_change"] >= q80),
        "Much warmer than last week": season & (ctx["hdd_change"] <= q20),
        "Price spike": ctx["price"] >= p95,
    }
    tags = pd.Series([[] for _ in range(len(ctx))], index=ctx.index)
    for tag, mask in rules.items():
        if mask is None:
            continue
        for d in ctx.index[np.asarray(mask, dtype=bool)]:
            tags[d].append(tag)
    ctx["tags"] = tags
    return ctx


def daily_errors(fc: pd.DataFrame) -> pd.DataFrame:
    y, yp, yn = (fc[c].to_numpy(float) for c in ("y_true", "y_pred", "y_naive"))
    q = fc[QUANTILE_COLUMNS].to_numpy(float)
    rows = pd.DataFrame({
        "date": pd.DatetimeIndex(fc["local_date"]),
        "ae": np.abs(yp - y), "err": yp - y, "ape": 100 * np.abs(yp - y) / np.abs(y),
        "ae_naive": np.abs(yn - y),
        "inside": (y >= q[:, 0]) & (y <= q[:, -1]) if not np.isnan(q).all() else np.nan,
    })
    return rows.groupby("date").agg(MAE=("ae", "mean"), bias=("err", "mean"), MAPE=("ape", "mean"),
                                    naive=("ae_naive", "mean"), coverage=("inside", "mean"),
                                    total=("ae", "sum"))


def worst_for_run(path: Path, run: str, frames: dict, ctx_cache: dict, data_dir: Path, top: int):
    fc, frame, split = load_rows(path, frames, data_dir)
    key = (frame.resolution, split)
    if key not in ctx_cache:
        ctx_cache[key] = day_context(frame, split)
    ctx = ctx_cache[key]
    days = daily_errors(fc).join(ctx, how="left")
    days = days[days.index.year == SPLITS[split]]
    worst = days.sort_values("MAE", ascending=False).head(top)

    info = run_info(run)
    table = pd.DataFrame({
        "Rank": np.arange(1, len(worst) + 1),
        "Date": worst.index.strftime("%Y-%m-%d"),
        "Weekday": worst["weekday"].to_numpy(),
        "MAE (MWh)": worst["MAE"].to_numpy(),
        "MAPE %": worst["MAPE"].to_numpy(),
        "Bias (MWh)": worst["bias"].to_numpy(),
        "Naive MAE (MWh)": worst["naive"].to_numpy(),
        "HDD change vs last week": worst["hdd_change"].map(lambda v: "" if pd.isna(v) else f"{v:+.1f}").to_numpy(),
        "Mean price (EUR/MWh)": worst["price"].map(lambda v: "" if pd.isna(v) else f"{v:.0f}").to_numpy(),
        "Likely reason": [", ".join(t) if [x for x in t if x != "Weekend"] else
                          ", ".join(t + ["no other reason in our inputs"]) if t else "none in our inputs"
                          for t in worst["tags"]],
    })
    has = lambda group: np.mean([any(t in group for t in tags) for tags in worst["tags"]])  # noqa: E731
    summary = {
        "Model": info["model"], "Horizon": horizon_text(info["resolution"], info["horizon"]),
        f"Share of yearly error from the {top} worst days %": 100 * worst["total"].sum() / days["total"].sum(),
        f"Share of the year's days %": 100 * len(worst) / len(days),
        "With a special-day tag %": 100 * has(SPECIAL_TAGS),
        "With a weather tag %": 100 * has(WEATHER_TAGS),
        "With a price spike %": 100 * has(MARKET_TAGS),
        "Without any explanation %": 100 * np.mean([not [x for x in t if x != "Weekend"] for t in worst["tags"]]),
    }
    return info, table, summary, set(table["Date"])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+", type=Path, help="forecast CSV files")
    p.add_argument("--top", type=int, default=10, help="number of worst days per run")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_METRICS_DIR / "report")
    args = p.parse_args()

    report = Report(args.out_dir, md_name="worst_days.md", title=f"The {args.top} worst forecast days per model")
    frames, ctx_cache, summaries, dates, tables = {}, {}, [], {}, []
    names = run_names(args.files)
    for f in args.files:
        if f.stem.startswith("seasonal_naive"):
            continue
        info, table, summary, top_dates = worst_for_run(f, names[f], frames, ctx_cache, args.data_dir, args.top)
        summaries.append(summary)
        tables.append((names[f], info, table))
        for d in top_dates:
            dates.setdefault(d, []).append(info["label"])

    summary = pd.DataFrame(summaries)
    report.add("worst_days_summary", f"Summary: what the {args.top} worst days have in common", summary,
               note="Tags can overlap, so the shares need not add up to 100 %. Weekend alone does not count "
                    "as an explanation.")
    common = pd.DataFrame([{"Date": d, "Models": len(r), "Runs": "; ".join(sorted(r))}
                           for d, r in dates.items() if len(r) > 1])
    if not common.empty:
        common = common.sort_values(["Models", "Date"], ascending=[False, True])
        report.add("worst_days_common", "Days among the worst for several models", common)
    for name, info, table in tables:
        safe = name.replace(" [", "__").replace("]", "")
        report.add(f"worst_days_{safe}", info["label"], table,
                   note="Hourly runs: the 24 hours of the day. Daily 7 d runs: the forecasts of that day from "
                        "all lead days. Bias < 0 = under-forecast.")
    path = report.write()

    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print(summary.round(1).to_string(index=False))
    print(f"\n[worst] tables -> {path}")


if __name__ == "__main__":
    main()