"""
Actual versus forecast of the final hourly SARIMAX model on two weeks of the test year 2024:
the week around Christmas (Mon 23 to Sun 29 December, with 25 and 26 December) and, for comparison,
a summer week (Mon 8 to Sun 14 July).

Lines: actual, the 1-hour forecast (every hour) and the 24-hour forecast (from local midnight, so the forecast
of an hour is made between 1 and 24 hours before) with its 80% interval (q0.1 to q0.9).
The time axis is the local time (Europe/Berlin); the forecast files are in UTC.

Output: results/sarimax/report/figures/sarimax_hourly_forecast_vs_actual_test.png

    uv run python src/analysis/sarimax/plot_sarimax_hourly_forecast_vs_actual.py
"""

from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from sarimax_report_common import (
    BLACK,
    BLUE,
    FIG_WIDTH,
    ORANGE,
    SARIMAX_DIR,
    apply_style,
    mape,
    rmse,
    save_figure,
)

WEEKS = [("Christmas week", "2024-12-23", "2024-12-29"), ("Summer week", "2024-07-08", "2024-07-14")]


def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(SARIMAX_DIR / "forecasts" / name, parse_dates=["target_time"])
    df["time"] = df["target_time"].dt.tz_localize("UTC").dt.tz_convert("Europe/Berlin").dt.tz_localize(None)
    return df.set_index("time").sort_index()


def main() -> None:
    apply_style()
    h1 = load("sarimax_hourly_1h_test.csv")
    h24 = load("sarimax_hourly_24h_test.csv")

    fig, axes = plt.subplots(len(WEEKS), 1, figsize=(FIG_WIDTH, 5.6))
    for ax, (title, start, end) in zip(axes, WEEKS):
        a = h24.loc[start:f"{end} 23:59"]
        b = h1.loc[start:f"{end} 23:59"]
        ax.fill_between(a.index, a["q0.1"] / 1e3, a["q0.9"] / 1e3, color=BLUE, alpha=0.2, lw=0, label="80% interval (24 h)")
        ax.plot(a.index, a["y_true"] / 1e3, color=BLACK, lw=1.0, label="Actual")
        ax.plot(a.index, a["y_pred"] / 1e3, color=BLUE, lw=1.0, label="Forecast, 24 h")
        ax.plot(b.index, b["y_pred"] / 1e3, color=ORANGE, lw=1.0, label="Forecast, 1 h")
        ax.set_title(
            f"{title}: RMSE {rmse(a['y_true'], a['y_pred']):,.0f} MWh (24 h), "
            f"{rmse(b['y_true'], b['y_pred']):,.0f} MWh (1 h); MAPE {mape(a['y_true'], a['y_pred']):.1f}% / "
            f"{mape(b['y_true'], b['y_pred']):.1f}%",
            loc="left", fontsize=8.5,
        )
        ax.set_ylabel("Consumption (GWh/h)")
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%a\n%d %b"))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save_figure(fig, "sarimax_hourly_forecast_vs_actual_test")


if __name__ == "__main__":
    main()
