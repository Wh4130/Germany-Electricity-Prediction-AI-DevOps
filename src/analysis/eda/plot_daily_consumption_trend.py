"""
Daily actual consumption with its 7-day moving average (training period).

Output: results/eda/figures/daily_consumption_trend.png

    uv run python src/analysis/eda/plot_daily_consumption_trend.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from eda_common import BLUE, FIG_HEIGHT, FIG_WIDTH, ORANGE, apply_style, legend_below, load_train, save_figure


def main() -> None:
    apply_style()
    df = load_train("daily")
    ma7 = df["actual_consumption"].rolling(window=7).mean()

    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    ax.plot(df["date_from"], df["actual_consumption"] / 1e6, color=BLUE, lw=0.6, label="Daily consumption")
    ax.plot(df["date_from"], ma7 / 1e6, color=ORANGE, lw=1.2, label="7-day moving average")
    ax.set_xlabel("Year")
    ax.set_ylabel("Consumption (million MWh/day)")
    legend_below(ax, ncol=2)
    save_figure(fig, "daily_consumption_trend")


if __name__ == "__main__":
    main()
