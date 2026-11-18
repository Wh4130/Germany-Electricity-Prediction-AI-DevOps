"""
Holiday effect on daily consumption: mean consumption per day type (training period), as
percent change from the Weekday mean - no detrending, raw averages (unlike
plot_weekday_effect.py's ratio to the centred 7-day mean).

Seven mutually exclusive day types, Christmas/New Year has first priority (fixed window,
regardless of weekday/weekend/holiday), then public holiday (split into weekend and
weekday), then bridge day, then weekend split into Saturday/Sunday, then plain weekday.

Outputs (results/eda/figures):
    holiday_type_pct_bar.png    % change vs Weekday mean per type, sample size (n) on each bar

    uv run python src/analysis/eda/plot_holiday_effect.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from eda_common import (
    BLUE,
    FIG_HEIGHT,
    FIG_WIDTH,
    VERMILION,
    apply_style,
    load_train,
    save_figure,
)

HOLIDAY_TYPE_ORDER = [
    "Weekday", "Saturday", "Sunday",
    "Public holiday (weekday)", "Public holiday (weekend)",
    "Bridge day", "Christmas/New Year",
]


def add_holiday_type(df):
    """Seven mutually exclusive day types - see the module docstring for the priority order."""
    sat = df["day_of_week_raw"] == 5
    sun = df["day_of_week_raw"] == 6
    weekend = sat | sun
    holiday = df["is_holiday"].astype(bool)
    bridge = df["is_bridge_day"].astype(bool)
    christmas = df["is_christmas_new_year"].astype(bool)

    label = np.select(
        [christmas, holiday & weekend, holiday & ~weekend, bridge, sat, sun],
        ["Christmas/New Year", "Public holiday (weekend)", "Public holiday (weekday)",
         "Bridge day", "Saturday", "Sunday"],
        default="Weekday",
    )
    out = df.copy()
    out["holiday_type"] = label
    return out


def main() -> None:
    apply_style()
    df = load_train("daily")
    df = add_holiday_type(df)

    stats = df.groupby("holiday_type")["actual_consumption"].agg(["mean", "count"]).reindex(HOLIDAY_TYPE_ORDER)
    weekday_mean = stats.loc["Weekday", "mean"]
    stats["pct_vs_weekday"] = (stats["mean"] / weekday_mean - 1) * 100

    colors = [BLUE if t in ("Weekday", "Saturday", "Sunday") else VERMILION for t in HOLIDAY_TYPE_ORDER]
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    bars = ax.bar(range(len(stats)), stats["pct_vs_weekday"], color=colors, width=0.6)
    ax.axhline(0.0, color="#8a8985", lw=0.8, ls="--")
    for bar, n in zip(bars, stats["count"]):
        va = "bottom" if bar.get_height() >= 0 else "top"
        offset = 2 if bar.get_height() >= 0 else -2
        ax.annotate(f"n={int(n)}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va=va, fontsize=7, xytext=(0, offset), textcoords="offset points")
    ax.set_xticks(range(len(stats)), stats.index, rotation=20, ha="right")
    ax.set_ylabel("% change in mean consumption vs Weekday")
    save_figure(fig, "holiday_type_pct_bar")

    print(stats)


if __name__ == "__main__":
    main()
