"""
ETL: German day-ahead electricity price (hourly) -> src/data/intermin/day_ahead_price.csv

Source
    SMARD (Bundesnetzagentur), wholesale price Germany / Luxembourg, day-ahead, hourly, EUR/MWh.
    SMARD gets the data from the ENTSO-E transparency platform, which publishes the results of the
    day-ahead auction (EPEX SPOT). Licence: CC BY 4.0, cite as "Bundesnetzagentur | SMARD.de".

    The script reads the JSON files that the charts of the SMARD website use:
        https://www.smard.de/app/chart_data/4169/DE-LU/index_hour.json                     list of the weeks
        https://www.smard.de/app/chart_data/4169/DE-LU/4169_DE-LU_hour_<week start ms>.json  one week, hourly
    4169 = day-ahead price, DE-LU = bidding zone Germany / Luxembourg (exists since 2018-10-01).
    This is NOT a documented API, it can change without notice. That is why the file is downloaded once and
    committed. The official way is the manual download of the SMARD download center (market data).
    The same data is also published by the Energy-Charts API (Fraunhofer ISE) without changes.

What this script does
    1. Extract:   download one JSON file per week.
    2. Transform: one row per hour, time in UTC (`datetime_utc`) and the price (`day_ahead_price`).
                  UTC has no daylight saving time, so no hour is missing or repeated.
    3. Check:     no missing hour and no missing price in the period of our data
                  (local time 2019-01-01 00:00 - 2024-12-31 23:00). SMARD has had short gaps before.
    4. Load:      save as CSV (no row index, this is a lookup table, not a time series).

The day-ahead price of a day is known around noon of the day before (the auction closes at 12:00 CET).

Run (from the project root)
    uv run python src/scripts/day_ahead_price_etl.py
    uv run python src/scripts/day_ahead_price_etl.py --output some/other/path.csv
"""
import argparse
import os
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://www.smard.de/app/chart_data/4169/DE-LU"
# our data in UTC: local 2019-01-01 00:00 is 2018-12-31 23:00 UTC, local 2024-12-31 23:00 is 2024-12-31 22:00 UTC
START = pd.Timestamp("2018-12-31 23:00", tz = "UTC")
END = pd.Timestamp("2024-12-31 22:00", tz = "UTC")
WEEK_MS = 7 * 24 * 3600 * 1000


def get_json(url: str) -> dict:
    res = requests.get(url, timeout = 60)
    res.raise_for_status()
    return res.json()


def extract() -> list[list]:
    week_starts = get_json(f"{BASE}/index_hour.json")["timestamps"]
    needed = [t for t in week_starts if START.value // 10**6 - WEEK_MS < t <= END.value // 10**6]

    rows = []
    for week_start in needed:
        rows += get_json(f"{BASE}/4169_DE-LU_hour_{week_start}.json")["series"]
        time.sleep(0.05)  # be polite, one request per week
    return rows


def transform(rows: list[list]) -> pd.DataFrame:
    df = (
        pd.DataFrame(rows, columns = ["ms", "day_ahead_price"])
        .assign(datetime_utc = lambda d: pd.to_datetime(d["ms"], unit = "ms", utc = True))
        .drop_duplicates(subset = "datetime_utc", keep = "last")
        .set_index("datetime_utc")
        .loc[START:END, ["day_ahead_price"]]
        .sort_index()
    )
    df.index = df.index.tz_convert(None)  # naive, but in UTC (the column name says it)
    return df.reset_index()


def check(df: pd.DataFrame) -> None:
    expected = pd.date_range(START.tz_convert(None), END.tz_convert(None), freq = "h")
    missing_hours = expected.difference(df["datetime_utc"])
    if len(missing_hours):
        raise ValueError(f"{len(missing_hours)} hours are missing, e.g. {list(missing_hours[:3])}")

    missing_prices = df.loc[df["day_ahead_price"].isna(), "datetime_utc"]
    if len(missing_prices):
        raise ValueError(f"{len(missing_prices)} hours have no price, e.g. {list(missing_prices[:3])}")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Download the hourly day-ahead price Germany / Luxembourg (SMARD) and save it as CSV"
    )
    parser.add_argument(
        "--output",
        "--out",
        type = Path,
        default = ROOT / "src/data/intermin/day_ahead_price.csv",
        help = "output CSV path"
    )
    args = parser.parse_args()

    df = transform(extract())
    check(df)

    args.output.parent.mkdir(parents = True, exist_ok = True)
    df.to_csv(args.output, index = False)
    print(f"saved {len(df):>6} hours ({df['datetime_utc'].iloc[0]} - {df['datetime_utc'].iloc[-1]} UTC) -> {os.path.relpath(args.output)}")


if __name__ == "__main__":
    main()
