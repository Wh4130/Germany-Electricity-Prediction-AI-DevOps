"""
Actual versus forecast of the final daily SARIMAX model on the test year 2024, for h = 1 and h = 7,
with the 80% interval (q0.1 to q0.9).

h = 1: the 1-day forecasts (every day). h = 7: step 7 of the 7-day forecasts (origins whose whole horizon
lies inside the year), so the forecast of a day is made 7 days before.

Output: results/sarimax/report/figures/sarimax_forecast_vs_actual_test.png

    uv run python src/analysis/sarimax/plot_sarimax_forecast_vs_actual.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from sarimax_report_common import (
    BLACK,
    BLUE,
    FIG_WIDTH,
    SARIMAX_DIR,
    apply_style,
    mape,
    rmse,
    save_figure,
)


def load(name: str, step: int) -> pd.DataFrame:
    df = pd.read_csv(SARIMAX_DIR / "forecasts" / name, parse_dates=["origin", "target_time"])
    return df[df["step"] == step].sort_values("target_time")


def main() -> None:
    apply_style()
    panels = [(1, load("sarimax_daily_1d_test.csv", 1)), (7, load("sarimax_daily_7d_test.csv", 7))]

    fig, axes = plt.subplots(2, 1, figsize=(FIG_WIDTH, 5.4), sharex=True, sharey=True)
    for ax, (h, df) in zip(axes, panels):
        t = df["target_time"]
        ax.fill_between(t, df["q0.1"] / 1e6, df["q0.9"] / 1e6, color=BLUE, alpha=0.2, lw=0, label="80% interval")
        ax.plot(t, df["y_true"] / 1e6, color=BLACK, lw=0.8, label="Actual")
        ax.plot(t, df["y_pred"] / 1e6, color=BLUE, lw=0.8, label="Forecast")
        label = "1-day forecast" if h == 1 else "day 7 of the 7-day forecast"
        ax.set_title(
            f"{label}: RMSE {rmse(df['y_true'], df['y_pred']):,.0f} MWh, MAPE {mape(df['y_true'], df['y_pred']):.2f}%",
            loc="left",
        )
        ax.set_ylabel("Consumption (million MWh/day)")
    axes[-1].set_xlabel("2024")
    axes[-1].xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b"))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save_figure(fig, "sarimax_forecast_vs_actual_test")


if __name__ == "__main__":
    main()
