"""
ADF and KPSS tests on the actual consumption (training period), in levels and after
seasonal differencing.

    daily:  level, seasonal difference at lag 7
    hourly: level, seasonal difference at lag 24, lag 168

Reading the pair: ADF has a unit root as null, KPSS has stationarity as null.
Stationary = ADF rejects (p < 0.05) and KPSS does not (p >= 0.05). KPSS p-values are
bounded to [0.01, 0.10] by the statsmodels lookup table.

Outputs: results/eda/tables/stationarity_tests.csv and .tex

    uv run python src/analysis/eda/analyze_stationarity.py
"""

from __future__ import annotations

import warnings

import pandas as pd
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss

from eda_common import load_train, save_table

SERIES = {
    "daily": [("Level", 0), ("Seasonal diff. (lag 7)", 7)],
    "hourly": [("Level", 0), ("Seasonal diff. (lag 24)", 24), ("Seasonal diff. (lag 168)", 168)],
}


def verdict(adf_p: float, kpss_p: float) -> str:
    if adf_p < 0.05 and kpss_p >= 0.05:
        return "stationary"
    if adf_p >= 0.05 and kpss_p < 0.05:
        return "non-stationary"
    return "conflicting"


def main() -> None:
    rows = []
    for granularity, transforms in SERIES.items():
        y = load_train(granularity)["actual_consumption"].reset_index(drop=True)
        for label, lag in transforms:
            x = (y.diff(lag) if lag else y).dropna()
            adf_stat, adf_p = adfuller(x, autolag="AIC", result_object=False)[:2]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", InterpolationWarning)
                kpss_stat, kpss_p = kpss(x, regression="c", nlags="auto", result_object=False)[:2]
            rows.append(
                {
                    "granularity": granularity,
                    "transform": label,
                    "n": len(x),
                    "ADF_stat": adf_stat,
                    "ADF_p": adf_p,
                    "KPSS_stat": kpss_stat,
                    "KPSS_p": kpss_p,
                    "verdict": verdict(adf_p, kpss_p),
                }
            )
    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    save_table(table, "stationarity_tests", float_format="%.3f")


if __name__ == "__main__":
    main()
