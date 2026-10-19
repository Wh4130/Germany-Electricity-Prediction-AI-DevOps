"""
ETL: German industrial production index -> src/data/intermin/industrial_production.csv

Source
    Eurostat, dataset sts_inpr_m "Production in industry - monthly data", Statistics API:
        GET https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sts_inpr_m
            ?geo=DE&nace_r2=B-D&s_adj=SCA&unit=I21&sinceTimePeriod=2019-01
    Documentation: https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-detailed-guidelines/api-statistics

    Eurostat website direct download: https://ec.europa.eu/eurostat/web/main/data/database
    - Data Navigation Tree > Industry, trade and services > Short-term business statistics
                      > Industry > Production in industry (sts_inpr_m)

    The filters: geo = DE (Germany), nace_r2 = B-D (mining, manufacturing, electricity, gas, steam and
    air conditioning supply), s_adj = SCA (seasonally and calendar adjusted), unit = I21 (index, 2021 = 100).
    The response is the latest published data (later revisions of past months are included).

What this script does
    1. Extract:   download the series (one request, a few KB).
    2. Transform: JSON-stat -> one row per month (`month`, `industrial_production_index`).
    3. Check:     no missing month between the first and the last month, all values are numbers.
    4. Load:      save as CSV (no row index, this is a lookup table, not a time series).

Run (from the project root)
    uv run python src/scripts/industrial_production_etl.py
    uv run python src/scripts/industrial_production_etl.py --output some/other/path.csv
"""
import argparse
import os
from pathlib import Path

import pandas as pd
import requests

URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sts_inpr_m"
PARAMS = {
    "format": "JSON",
    "lang": "EN",
    "geo": "DE",
    "nace_r2": "B-D",
    "s_adj": "SCA",
    "unit": "I21",
    "sinceTimePeriod": "2019-01",
}


def extract() -> dict:
    res = requests.get(URL, params = PARAMS, timeout = 60)
    res.raise_for_status()
    return res.json()


def transform(raw: dict) -> pd.DataFrame:
    # JSON-stat: `value` maps the position of a month to its value, a missing month has no entry
    months = sorted(raw["dimension"]["time"]["category"]["index"].items(), key = lambda item: item[1])
    values = raw["value"]
    return pd.DataFrame({
        "month": [month for month, _ in months],
        "industrial_production_index": [values.get(str(position)) for _, position in months],
    })


def check(df: pd.DataFrame) -> None:
    if df["industrial_production_index"].isna().any():
        missing = df.loc[df["industrial_production_index"].isna(), "month"].tolist()
        raise ValueError(f"missing values for {missing}")

    expected = pd.period_range(df["month"].iloc[0], df["month"].iloc[-1], freq = "M").astype(str)
    if list(expected) != df["month"].tolist():
        raise ValueError("there is a gap between the first and the last month")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Download the German industrial production index (Eurostat) and save it as CSV"
    )
    parser.add_argument(
        "--output",
        "--out",
        type = Path,
        default = ROOT / "src/data/intermin/industrial_production.csv",
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
