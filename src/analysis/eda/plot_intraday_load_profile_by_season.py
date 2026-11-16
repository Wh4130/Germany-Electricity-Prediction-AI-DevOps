"""
Average 24-hour load profile by season and day type (hourly training data).

Days with 23 or 25 hours (daylight saving switch) are dropped.

Output: results/eda/figures/intraday_load_profile_by_season.png

    uv run python src/analysis/eda/plot_intraday_load_profile_by_season.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from eda_common import (
    DAY_TYPE_COLORS,
    DAY_TYPE_ORDER,
    FIG_HEIGHT_TALL,
    FIG_WIDTH,
    SEASON_MAP,
    SEASON_ORDER,
    add_day_type,
    apply_style,
    load_train,
    save_figure,
)


def main() -> None:
    apply_style()
    df = load_train("hourly")

    day = df["date_from"].dt.floor("D")
    n_hours = df.groupby(day)["date_from"].transform("size")
    h = df[n_hours == 24].copy()
    h["hour"] = h["date_from"].dt.hour
    h = add_day_type(h)
    h["season"] = h["month"].map(SEASON_MAP)

    profile = h.groupby(["season", "day_type", "hour"], observed=True, as_index=False)["actual_consumption"].mean()

    fig, axes = plt.subplots(2, 2, figsize=(FIG_WIDTH, FIG_HEIGHT_TALL), sharex=True, sharey=True)
    for ax, season in zip(axes.ravel(), SEASON_ORDER):
        for color, day_type in zip(DAY_TYPE_COLORS, DAY_TYPE_ORDER):
            g = profile[(profile["season"] == season) & (profile["day_type"] == day_type)]
            ax.plot(g["hour"], g["actual_consumption"] / 1e3, color=color, lw=1.3, label=day_type)
        ax.set_title(season)
        ax.set_xticks(range(0, 24, 4))
    for ax in axes[1]:
        ax.set_xlabel("Hour of day")
    for ax in axes[:, 0]:
        ax.set_ylabel("Consumption (thousand MWh/h)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save_figure(fig, "intraday_load_profile_by_season")


if __name__ == "__main__":
    main()
