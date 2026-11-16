"""
Mean daily consumption by calendar month, one line per year (training period).

Output: results/eda/figures/monthly_mean_consumption_by_year.png

    uv run python src/analysis/eda/plot_monthly_mean_consumption_by_year.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from eda_common import FIG_HEIGHT, FIG_WIDTH, YEAR_COLORS, apply_style, legend_below, load_train, save_figure


def main() -> None:
    apply_style()
    df = load_train("daily")
    df["year"] = df["date_from"].dt.year
    monthly = df.groupby(["year", "month"], as_index=False)["actual_consumption"].mean()

    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    for color, (year, g) in zip(YEAR_COLORS, monthly.groupby("year")):
        ax.plot(g["month"], g["actual_consumption"] / 1e6, marker="o", ms=3, lw=1.2, color=color, label=str(year))
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("Month")
    ax.set_ylabel("Mean consumption (million MWh/day)")
    legend_below(ax, ncol=6)
    save_figure(fig, "monthly_mean_consumption_by_year")


if __name__ == "__main__":
    main()
