"""
ETL: German industrial confidence indicator (monthly) -> src/data/intermin/industrial_confidence.csv

Source
    Eurostat, dataset ei_bssi_m_r2 "Economic sentiment and confidence indicators by sector - monthly data",
    Statistics API (the business and consumer surveys of the European Commission):
        GET https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ei_bssi_m_r2
            ?geo=DE&s_adj=SA&indic=BS-ICI-BAL&sinceTimePeriod=2018-12
    Where it is in the Eurostat data navigation tree:
        Database by themes > General and regional statistics > European and national indicators for
        short-term analysis > Business and consumer surveys > Business and consumer survey - composite
        indicators > Economic sentiment and confidence indicators by sector - monthly data

    The filters: geo = DE (Germany), s_adj = SA (seasonally adjusted), indic = BS-ICI-BAL (industrial
    confidence indicator, a balance in percentage points: the answers of the industry about order books,
    stocks of finished products and the expected production, an average of the three balances).

    When the value is known: the survey is made in the first 2 - 3 weeks of the month and the European
    Commission publishes it on the second-last working day of the same month (Eurostat: the data of
    2026-09 was updated on 2026-09-29). So a day can only use the value of the month before. This is done
    in economic_indicators_pipeline.py, not here. Schedule: Commission action plan for the business and
    consumer surveys, https://ec.europa.eu/dgs/economy_finance/procurement_grants/calls_for_proposals/2014/2014001a4/action_plan_en.pdf

What this script does
    1. Extract:   download the series (one request, a few KB).
    2. Transform: JSON-stat -> one row per month (`month`, `industrial_confidence`), from 2018-12 on
                  (the month before our data, because a day uses the value of the month before).
    3. Check:     no missing month, all values are numbers, the series covers our data (until 2024-12).
    4. Load:      save as CSV (no row index, this is a lookup table, not a time series).

Run (from the project root)
    uv run python src/scripts/industrial_confidence_etl.py
    uv run python src/scripts/industrial_confidence_etl.py --output some/other/path.csv
"""
import argparse
import os
from pathlib import Path

import pandas as pd
import requests

URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ei_bssi_m_r2"
PARAMS = {
    "format": "JSON",
    "lang": "EN",
    "geo": "DE",
    "s_adj": "SA",
    "indic": "BS-ICI-BAL",
    "sinceTimePeriod": "2018-12",
}
FIRST_MONTH = "2018-12"
LAST_MONTH_NEEDED = "2024-11"  # the month before the last month of our data (2024-12)


def extract() -> dict:
    res = requests.get(URL, params = PARAMS, timeout = 60)
    res.raise_for_status()
    return res.json()


def transform(raw: dict) -> pd.DataFrame:
    # JSON-stat: the filters leave only the time dimension with more than one entry
    other_sizes = {name: size for name, size in zip(raw["id"], raw["size"]) if name != "time"}
    if any(size != 1 for size in other_sizes.values()):
        raise ValueError(f"the filters do not give one series, the sizes are {other_sizes}")

    position_of_month = raw["dimension"]["time"]["category"]["index"]  # {"2018-12": 0, "2019-01": 1, ...}
    values = raw["value"]  # {"0": ..., "1": ...}, a month without a value is not in it
    return pd.DataFrame({
        "month": list(position_of_month),
        "industrial_confidence": [values.get(str(position)) for position in position_of_month.values()],
    })


def check(df: pd.DataFrame) -> None:
    if df["industrial_confidence"].isna().any():
        raise ValueError(f"missing values for {df.loc[df['industrial_confidence'].isna(), 'month'].tolist()}")

    expected = pd.period_range(df["month"].iloc[0], df["month"].iloc[-1], freq = "M").astype(str)
    if list(expected) != df["month"].tolist():
        raise ValueError("there is a gap between the first and the last month")

    if df["month"].iloc[0] != FIRST_MONTH or df["month"].iloc[-1] < LAST_MONTH_NEEDED:
        raise ValueError(f"the series ({df['month'].iloc[0]} - {df['month'].iloc[-1]}) does not cover "
                         f"{FIRST_MONTH} - {LAST_MONTH_NEEDED}")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Download the monthly German industrial confidence indicator (Eurostat) and save it as CSV"
    )
    parser.add_argument(
        "--output",
        "--out",
        type = Path,
        default = ROOT / "src/data/intermin/industrial_confidence.csv",
        help = "output CSV path"
    )
    args = parser.parse_args()

    df = transform(extract())
    check(df)

    args.output.parent.mkdir(parents = True, exist_ok = True)
    df.to_csv(args.output, index = False)
    print(f"saved {len(df):>6} months ({df['month'].iloc[0]} - {df['month'].iloc[-1]}) -> {os.path.relpath(args.output)}")


if __name__ == "__main__":
    main()
