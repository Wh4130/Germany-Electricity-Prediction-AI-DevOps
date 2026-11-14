"""
Weekday effect on daily consumption, as the ratio to the centred 7-day mean (training period).

Outputs (results/eda/figures):
    day_type_ratio_boxplot.png    four day types, pooled across years
    weekly_profile_by_year.png    Monday to Sunday by year, holidays excluded (weekly profile)

    uv run python src/analysis/eda/plot_weekday_effect.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from eda_common import (
    DAY_TYPE_ORDER,
    FIG_HEIGHT,
    FIG_WIDTH,
    WEEKDAY_ORDER,
    YEAR_COLORS,
    BLUE,
    add_day_type,
    apply_style,
    legend_below,
    load_train,
    save_figure,
)


def main() -> None:
    apply_style()
    df = load_train("daily")
    df["year"] = df["date_from"].dt.year
    # Remove level and season: ratio to the centred 7-day mean.
    df["ratio_to_week"] = df["actual_consumption"] / df["actual_consumption"].rolling(7, center=True).mean()
    df = add_day_type(df)

    # (a) four day types, pooled across years
    valid = df.dropna(subset=["ratio_to_week"])
    groups = [valid.loc[valid["day_type"] == t, "ratio_to_week"].to_numpy() for t in DAY_TYPE_ORDER]
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    ax.boxplot(groups, tick_labels=DAY_TYPE_ORDER, showfliers=False, widths=0.5)
    for i, g in enumerate(groups, start=1):
        ax.scatter(i + rng.uniform(-0.18, 0.18, len(g)), g, s=4, alpha=0.4, color=BLUE, linewidths=0)
    ax.axhline(1.0, color="#8a8985", lw=0.8, ls="--")
    ax.set_ylabel("Ratio to centred 7-day mean")
    save_figure(fig, "day_type_ratio_boxplot")

    # (b) Monday to Sunday by year, normal days only
    normal = df[df["day_type"].isin(["Weekday", "Weekend"])]
    dow = (
        normal.groupby(["year", "day_of_week"], observed=True)["ratio_to_week"].mean().unstack("day_of_week")
    )[WEEKDAY_ORDER]
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    for color, (year, row) in zip(YEAR_COLORS, dow.iterrows()):
        ax.plot(range(7), row.to_numpy(), marker="o", ms=3, lw=1.2, color=color, label=str(year))
    ax.set_xticks(range(7), [d[:3] for d in WEEKDAY_ORDER])
    ax.set_ylabel("Ratio to centred 7-day mean")
    legend_below(ax, ncol=6)
    save_figure(fig, "weekly_profile_by_year")


if __name__ == "__main__":
    main()
