"""
Validation table of the hourly SARIMAX specifications (fit 2019-2022, forecast 2023).

Rows: seasonal naive (same hour one week before) and the two candidates (2,0,0)(1,0,0)_24 and
(2,0,0)(1,0,1)_24, both in levels with daily and yearly Fourier terms and day-of-week dummies, X coefficients by
OLS and ARMA parameters by maximum likelihood. The model is chosen by the RMSE over all steps of the 24-hour
forecasts (from every local midnight); the 1-hour RMSE is shown as well. The final model is set in bold.

Output: results/sarimax/report/tables/sarimax_hourly_validation.tex and .csv

    uv run python src/analysis/sarimax/make_sarimax_hourly_validation_table.py
"""

from __future__ import annotations

import json

import pandas as pd

from sarimax_report_common import (
    SARIMAX_DIR,
    load_hourly_y,
    mape,
    rmse,
    save_tabular,
    seasonal_naive_hourly,
)

SELECTION = SARIMAX_DIR / "selection" / "hourly"
FINAL_FILE = "SARIMAX_200101_24.json"
ROWS = ["SARIMAX_200100_24.json", "SARIMAX_200101_24.json"]


def order_text(order, seasonal) -> str:
    p, d, q = order
    P, D, Q, s = seasonal
    return f"({p},{d},{q})({P},{D},{Q})$_{{{s}}}$"


def main() -> None:
    y = load_hourly_y()
    val = pd.read_csv(SARIMAX_DIR / "forecasts" / "sarimax_hourly_24h_val.csv", parse_dates=["target_time"])
    val1 = pd.read_csv(SARIMAX_DIR / "forecasts" / "sarimax_hourly_1h_val.csv", parse_dates=["target_time"])
    naive24 = seasonal_naive_hourly(y, val["target_time"])
    naive1 = seasonal_naive_hourly(y, val1["target_time"])

    records = [dict(spec="Seasonal naive", aic=None,
                    rmse_1h=rmse(val1["y_true"], naive1), rmse_24h=rmse(val["y_true"], naive24),
                    mape_24h=mape(val["y_true"], naive24), final=False)]
    for file in ROWS:
        d = json.load(open(SELECTION / file))
        records.append(dict(spec=order_text(d["order"], d["seasonal_order"]), aic=d["aic"], rmse_1h=d["rmse"],
                            rmse_24h=d["rmse_all"], mape_24h=d["mape_all"], final=file == FINAL_FILE))
    df = pd.DataFrame(records)

    rows = []
    for r in records:
        cells = [r["spec"], "--" if r["aic"] is None else f"{r['aic']:,.0f}", f"{r['rmse_1h']:,.0f}",
                 f"{r['rmse_24h']:,.0f}", f"{r['mape_24h']:.2f}"]
        if r["final"]:
            cells = [r"\textbf{" + c + "}" for c in cells]
        rows.append(cells)

    save_tabular(
        "sarimax_hourly_validation",
        ["Specification", "AIC", "RMSE 1 h (MWh)", "RMSE 24 h (MWh)", "MAPE 24 h (\\%)"],
        rows,
        "lrrrr",
        df.drop(columns="final"),
    )
    print(df.drop(columns="final").round(2).to_string(index=False))


if __name__ == "__main__":
    main()
