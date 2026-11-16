"""
Test-year (2024) RMSE and MAPE of the final hourly SARIMAX model against the seasonal naive forecast,
for the 1-hour forecasts (every hour) and the 24-hour forecasts (all 24 steps, from every local midnight).

Seasonal naive = same hour one week before, evaluated on the same target hours as SARIMAX.

Output: results/sarimax/report/tables/sarimax_hourly_test_metrics.tex and .csv

    uv run python src/analysis/sarimax/make_sarimax_hourly_test_metrics_table.py
"""

from __future__ import annotations

import pandas as pd

from sarimax_report_common import (
    SARIMAX_DIR,
    load_hourly_y,
    mape,
    rmse,
    save_tabular,
    seasonal_naive_hourly,
)


def main() -> None:
    y = load_hourly_y()
    result = {}
    for name, file in [("1 h", "sarimax_hourly_1h_test.csv"), ("24 h", "sarimax_hourly_24h_test.csv")]:
        df = pd.read_csv(SARIMAX_DIR / "forecasts" / file, parse_dates=["target_time"])
        naive = seasonal_naive_hourly(y, df["target_time"])
        result[name] = {
            "Seasonal naive": (rmse(df["y_true"], naive), mape(df["y_true"], naive)),
            "SARIMAX": (rmse(df["y_true"], df["y_pred"]), mape(df["y_true"], df["y_pred"])),
        }

    records, rows = [], []
    for model in ["Seasonal naive", "SARIMAX"]:
        (r1, m1), (r24, m24) = result["1 h"][model], result["24 h"][model]
        records.append(dict(model=model, rmse_1h=r1, mape_1h=m1, rmse_24h=r24, mape_24h=m24))
        rows.append([model, f"{r1:,.0f}", f"{m1:.2f}", f"{r24:,.0f}", f"{m24:.2f}"])
    gain1 = 1 - result["1 h"]["SARIMAX"][0] / result["1 h"]["Seasonal naive"][0]
    gain24 = 1 - result["24 h"]["SARIMAX"][0] / result["24 h"]["Seasonal naive"][0]
    rows.append(["RMSE reduction", f"{gain1 * 100:.0f}\\%", "", f"{gain24 * 100:.0f}\\%", ""])

    save_tabular(
        "sarimax_hourly_test_metrics",
        ["Model", "RMSE 1 h", "MAPE 1 h (\\%)", "RMSE 24 h", "MAPE 24 h (\\%)"],
        rows,
        "lrrrr",
        pd.DataFrame(records),
    )
    print(pd.DataFrame(records).round(2).to_string(index=False),
          f"\nRMSE reduction: 1 h {gain1:.1%}, 24 h {gain24:.1%}")


if __name__ == "__main__":
    main()
