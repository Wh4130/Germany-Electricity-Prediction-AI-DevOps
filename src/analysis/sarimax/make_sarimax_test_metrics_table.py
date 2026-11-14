"""
Test-year (2024) RMSE and MAPE of the final daily SARIMAX model against the seasonal naive forecast,
for the 1-day forecasts (h = 1, every day) and the 7-day forecasts (h = 7: all seven steps, from every origin
whose whole horizon lies inside the year), as in the hourly table (all 24 steps).

Seasonal naive = same weekday one week before, evaluated on the same target days as SARIMAX.

Output: results/sarimax/report/tables/sarimax_test_metrics.tex and .csv

    uv run python src/analysis/sarimax/make_sarimax_test_metrics_table.py
"""

from __future__ import annotations

import pandas as pd

from sarimax_report_common import SARIMAX_DIR, load_daily_y, mape, rmse, save_tabular, seasonal_naive


def load(name: str) -> pd.DataFrame:
    """All steps of the forecast file (for the 1-day file there is only step 1)."""
    return pd.read_csv(SARIMAX_DIR / "forecasts" / name, parse_dates=["target_time"])


def main() -> None:
    y = load_daily_y()
    result = {}
    for h, file in [(1, "sarimax_daily_1d_test.csv"), (7, "sarimax_daily_7d_test.csv")]:
        df = load(file)
        naive = seasonal_naive(y, df["target_time"])
        result[h] = {
            "Seasonal naive": (rmse(df["y_true"], naive), mape(df["y_true"], naive)),
            "SARIMAX": (rmse(df["y_true"], df["y_pred"]), mape(df["y_true"], df["y_pred"])),
        }

    records, rows = [], []
    for model in ["Seasonal naive", "SARIMAX"]:
        (r1, m1), (r7, m7) = result[1][model], result[7][model]
        records.append(dict(model=model, rmse_h1=r1, mape_h1=m1, rmse_h7=r7, mape_h7=m7))
        rows.append([model, f"{r1:,.0f}", f"{m1:.2f}", f"{r7:,.0f}", f"{m7:.2f}"])
    gain1 = 1 - result[1]["SARIMAX"][0] / result[1]["Seasonal naive"][0]
    gain7 = 1 - result[7]["SARIMAX"][0] / result[7]["Seasonal naive"][0]
    rows.append(["RMSE reduction", f"{gain1 * 100:.0f}\\%", "", f"{gain7 * 100:.0f}\\%", ""])

    save_tabular(
        "sarimax_test_metrics",
        ["Model", "RMSE h=1", "MAPE h=1 (\\%)", "RMSE h=7", "MAPE h=7 (\\%)"],
        rows,
        "lrrrr",
        pd.DataFrame(records),
    )
    print(pd.DataFrame(records).round(2).to_string(index=False), f"\nRMSE reduction: h=1 {gain1:.1%}, h=7 {gain7:.1%}")


if __name__ == "__main__":
    main()
