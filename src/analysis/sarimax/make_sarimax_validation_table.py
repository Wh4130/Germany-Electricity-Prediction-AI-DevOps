"""
Validation table of the daily SARIMAX specifications (fit 2019-2022, forecast 2023, h = 1).

Rows: seasonal naive, SARIMA without X, Model 1 (seasonal difference, month dummies) with four orders,
Model 2 (levels, weekday dummies and yearly Fourier terms with K pairs). The final model is set in bold.
The model is chosen by the RMSE at h = 1; AIC and BIC are only comparable between models with the same
differencing.

Output: results/sarimax/report/tables/sarimax_validation.tex and .csv

    uv run python src/analysis/sarimax/make_sarimax_validation_table.py
"""

from __future__ import annotations

import json

import pandas as pd

from sarimax_report_common import SARIMAX_DIR, load_daily_y, mape, rmse, save_tabular, seasonal_naive

SELECTION = SARIMAX_DIR / "selection" / "daily"
FINAL_FILE = "SARIMAX_2001117.json"

# (folder, file, label of the model, K for Model 2)
ROWS = [
    ("model1", "SARIMA_1000117.json", "SARIMA, no X", None),
    ("model1", "SARIMAX_1000117.json", "Model 1", None),
    ("model1", "SARIMAX_2000117.json", "Model 1", None),
    ("model1", "SARIMAX_1001117.json", "Model 1", None),
    ("model1", "SARIMAX_2001117.json", "Model 1", None),
    ("model2", "SARIMAX_1001007_K1.json", "Model 2", 1),
    ("model2", "SARIMAX_1001007_K5.json", "Model 2", 5),
    ("model2", "SARIMAX_1001007_K10.json", "Model 2", 10),
    ("model2", "SARIMAX_1011007.json", "Model 2", 10),
]


def order_text(order, seasonal) -> str:
    p, d, q = order
    P, D, Q, s = seasonal
    return f"({p},{d},{q})({P},{D},{Q})$_{{{s}}}$"


def main() -> None:
    y = load_daily_y()
    val_days = pd.date_range("2023-01-01", "2023-12-31")
    naive = seasonal_naive(y, val_days)

    records = [
        dict(model="Seasonal naive", spec="same weekday, one week before", K="", aic=None, bic=None,
             rmse=rmse(y[val_days], naive), mape=mape(y[val_days], naive), final=False)
    ]
    for folder, file, label, K in ROWS:
        d = json.load(open(SELECTION / folder / file))
        records.append(dict(model=label, spec=order_text(d["order"], d["seasonal_order"]), K=K if K else "",
                            aic=d["aic"], bic=d["bic"], rmse=d["rmse"], mape=d["mape"], final=file == FINAL_FILE))
    df = pd.DataFrame(records)

    def num(v, fmt):
        return "--" if v is None or pd.isna(v) else fmt.format(v)

    rows = []
    for r in records:
        cells = [r["model"], r["spec"], str(r["K"]), num(r["aic"], "{:,.0f}"), num(r["bic"], "{:,.0f}"),
                 num(r["rmse"], "{:,.1f}"), num(r["mape"], "{:.2f}")]
        if r["final"]:
            cells = [r"\textbf{" + c + "}" for c in cells]
        rows.append(cells)

    save_tabular(
        "sarimax_validation",
        ["Model", "Specification", "K", "AIC", "BIC", "RMSE (MWh)", "MAPE (\\%)"],
        rows,
        "llrrrrr",
        df.drop(columns="final"),
    )
    print(df.drop(columns="final").round(2).to_string(index=False))


if __name__ == "__main__":
    main()
