"""
ETL: European natural gas price (monthly) -> src/data/intermin/gas_price_eu.csv

Source
    IMF Primary Commodity Price System (PCPS), served by DBnomics (no registration needed):
        GET https://api.db.nomics.world/v22/series/IMF/PCPS/M.W00.PNGASEU.USD?observations=1
    Series M.W00.PNGASEU.USD = monthly, world, commodity PNGASEU "Natural gas, EU", unit USD
    (US dollars per million British thermal units, MMBtu).

    The price LEVEL is used on purpose, not the percent change: the year-over-year change has a moving
    base (the same month of the last year), so after the price spike of 2022 the change of 2023 is about
    -85% although the price is still higher than before the crisis.
    The price is not converted to euro: the gas price moves much more than the exchange rate, and a
    conversion would need the rate of every month, not the current one.

    DBnomics is a copy of the IMF data, it is some months behind the IMF. Cite it as "IMF PCPS via DBnomics".
    DBnomics documentation: https://docs.db.nomics.world/web-api/

What this script does
    1. Extract:   download the series (one request).
    2. Transform: one row per month (`month`, `gas_price_eu_usd`), from 2019-01 on.
    3. Check:     no missing month, all prices are numbers, the series covers our data (until 2024-12).
    4. Load:      save as CSV (no row index, this is a lookup table, not a time series).

The last month of the series is not the current month, that is fine as long as it
covers the period of our data.

Run (from the project root)
    uv run python src/scripts/gas_price_etl.py
    uv run python src/scripts/gas_price_etl.py --output some/other/path.csv
"""
import argparse
import os
from pathlib import Path

import pandas as pd
import requests

URL = "https://api.db.nomics.world/v22/series/IMF/PCPS/M.W00.PNGASEU.USD"
FIRST_MONTH = "2019-01"
LAST_MONTH_NEEDED = "2024-12"  # the last month of our data


def extract() -> dict:
    res = requests.get(URL, params = {"observations": 1}, timeout = 60)
    res.raise_for_status()
    return res.json()


def transform(raw: dict) -> pd.DataFrame:
    series = raw["series"]["docs"][0]
    return (
        pd.DataFrame({
            "month": series["period"],
            "gas_price_eu_usd": pd.to_numeric(pd.Series(series["value"]), errors = "coerce"),
        })
        .query("month >= @FIRST_MONTH")
        .reset_index(drop = True)
    )


def check(df: pd.DataFrame) -> None:
    if df["gas_price_eu_usd"].isna().any():
        raise ValueError(f"missing values for {df.loc[df['gas_price_eu_usd'].isna(), 'month'].tolist()}")

    expected = pd.period_range(df["month"].iloc[0], df["month"].iloc[-1], freq = "M").astype(str)
    if list(expected) != df["month"].tolist():
        raise ValueError("there is a gap between the first and the last month")

    if df["month"].iloc[0] != FIRST_MONTH or df["month"].iloc[-1] < LAST_MONTH_NEEDED:
        raise ValueError(f"the series ({df['month'].iloc[0]} - {df['month'].iloc[-1]}) does not cover "
                         f"{FIRST_MONTH} - {LAST_MONTH_NEEDED}")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Download the monthly European natural gas price (IMF via DBnomics) and save it as CSV"
    )
    parser.add_argument(
        "--output",
        "--out",
        type = Path,
        default = ROOT / "src/data/intermin/gas_price_eu.csv",
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
