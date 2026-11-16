"""
Coefficients of the final daily SARIMAX model (Model 1, (2,0,0)(1,1,1)_7, fit on 2019-2023) with p-values.

The saved model has only the parameters, so the standard errors are computed at these parameters (no new
estimation, `model.smooth(params)`), from the outer product of gradients (statsmodels default). The p-values
are therefore approximate. The target is in GWh/day. Continuous X are standardized (the coefficient is the
effect of +1 standard deviation), dummies are 0/1, the month dummies are relative to January.

Outputs (results/sarimax/report/tables):
    sarimax_coefficients.tex/.csv   covariates and ARMA terms
    sarimax_month_dummies.tex       month dummies (for the appendix)

    uv run python src/analysis/sarimax/make_sarimax_coefficients_table.py
"""

from __future__ import annotations

import warnings

import pandas as pd

from sarimax_report_common import DATA_DIR, SARIMAX_DIR, save_tabular  # first: puts src/models/sarimax on sys.path

from common import load_model, make_features  # noqa: E402  (src/models/sarimax)
from features import build_daily_X  # noqa: E402

warnings.filterwarnings("ignore")

LABELS = {
    "is_holiday": "Public holiday",
    "is_holiday_weekday": "Public holiday on a weekday",
    "weighted_regional_holiday": "Regional public holiday (population share)",
    "weighted_school_holiday": "School holiday (population share)",
    "is_bridge_day": "Bridge day",
    "is_christmas_new_year": "Christmas / New Year",
    "is_dst": "Daylight saving time",
    "is_dst_transition_day": "DST transition day",
    "industrial_confidence": "Industrial confidence",
    "ipi_ei_level": "Production index, energy-intensive industries",
    "day_ahead_price_mean": "Day-ahead price (mean)",
    "hdd": "Heating degree days",
    "wind_speed_10m_mean": "Wind speed",
    "precipitation_sum": "Precipitation",
    "solar_generation_proxy": "Solar generation proxy",
    "oxcgrt_stringency": "COVID-19 stringency index",
    "ar.L1": "AR(1)",
    "ar.L2": "AR(2)",
    "ar.S.L7": "Seasonal AR(1), lag 7",
    "ma.S.L7": "Seasonal MA(1), lag 7",
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SCALED_NOTE = {"weighted_regional_holiday", "weighted_school_holiday", "industrial_confidence", "ipi_ei_level",
               "day_ahead_price_mean", "hdd", "wind_speed_10m_mean", "precipitation_sum", "solar_generation_proxy",
               "oxcgrt_stringency"}


def num(x: float) -> str:
    """Two decimals with a proper minus sign for LaTeX."""
    return f"{x:.2f}".replace("-", "$-$")


def stars(p: float) -> str:
    """Superscript stars, padded with invisible stars so that the p-values stay aligned."""
    s = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    return r"\textsuperscript{" + s + r"\phantom{" + "*" * (3 - len(s)) + "}}" if len(s) < 3 else \
        r"\textsuperscript{" + s + "}"


def p_text(p: float) -> str:
    return "$<$0.001" if p < 0.001 else f"{p:.3f}"


def main() -> None:
    data = pd.read_csv(DATA_DIR / "data_daily.csv", index_col=0, parse_dates=["date_from", "date_from_utc"])
    data.index = pd.to_datetime(data["date_from"]).values
    data = make_features(data)
    y = data["actual_consumption"].asfreq("D")[:"2023-12-31"]
    X = build_daily_X(data).asfreq("D")[:"2023-12-31"]

    res = load_model(SARIMAX_DIR / "models" / "sarimax_daily_1d.json", y, X)["res"]
    fit = res.model.smooth(res.params)
    table = pd.DataFrame({"coef": fit.params, "se": fit.bse, "p": fit.pvalues})
    table.index.name = "term"

    def rows_for(names):
        out = []
        for n in names:
            r = table.loc[n]
            label = LABELS.get(n, n)
            unit = r"per SD" if n in SCALED_NOTE else ("" if n.startswith(("ar.", "ma.")) else "0/1")
            out.append([label, unit, num(r["coef"]), num(r["se"]), p_text(r["p"]) + stars(r["p"])])
        return out

    covariates = [n for n in table.index if n in LABELS and not n.startswith(("ar.", "ma."))]
    arma = [n for n in table.index if n.startswith(("ar.", "ma."))]
    header = ["Term", "Unit", "Coefficient (GWh)", "Std. error", "$p$-value"]
    save_tabular("sarimax_coefficients", header, rows_for(covariates + arma), "llrrr",
                 table.reset_index().rename(columns={"index": "term"}))

    month_rows = []
    for n in table.index:
        if n.startswith("month_"):
            m = int(n.split("_")[1])
            r = table.loc[n]
            month_rows.append([MONTHS[m - 1], num(r["coef"]), num(r["se"]), p_text(r["p"]) + stars(r["p"])])
    save_tabular("sarimax_month_dummies", ["Month (vs.\\ January)", "Coefficient (GWh)", "Std. error", "$p$-value"],
                 month_rows, "lrrr")

    print(table.round(4).to_string())


if __name__ == "__main__":
    main()
