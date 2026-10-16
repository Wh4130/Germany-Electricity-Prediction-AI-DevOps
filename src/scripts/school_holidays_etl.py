"""
ETL: school holidays of the 16 German states -> src/data/intermin/school_holidays.csv

Source
    ferien-api.de, one request returns the school holidays of all states and all years:
        GET https://ferien-api.de/api/v1/holidays
    Each item is one holiday period, e.g.
        {"start": "2019-04-15", "end": "2019-04-27", "year": 2019, "stateCode": "BW",
         "name": "osterferien baden-württemberg 2019", ...}
    `end` is the last day of the holiday (included).

What this script does
    1. Extract:   download the full list (one request).
    2. Transform: keep the periods that touch our data (2018-12-01 .. 2025-12-31, the Christmas holidays
                  of 2019 start in December 2018), keep the columns we need, derive `holiday_type`
                  (first word of the name, e.g. "osterferien") and `is_single_day` (a one-day "holiday"
                  such as a movable day off, the user of the file decides whether to count it).
    3. Check:     all 16 states are present, end >= start, at least 4 periods per state and year.
    4. Load:      save as CSV (no row index, this is a lookup table, not a time series).

Not done here (left to the pipeline that uses the file)
    - Periods of one state can overlap: take the union of the days.
    - Expanding the periods to single days and weighting the states.

Run (from the project root)
    uv run python src/scripts/school_holidays_etl.py
    uv run python src/scripts/school_holidays_etl.py --output some/other/path.csv

If the server answers with HTTP 429 (rate limit), wait a while and run it again.
"""
import argparse
import os
from pathlib import Path

import pandas as pd
import requests

URL = "https://ferien-api.de/api/v1/holidays"
PERIOD_START = "2018-12-01"
PERIOD_END = "2025-12-31"
STATES = ["BB", "BE", "BW", "BY", "HB", "HE", "HH", "MV", "NI", "NW", "RP", "SH", "SL", "SN", "ST", "TH"]
CHECK_YEARS = range(2019, 2026)
MIN_PERIODS_PER_YEAR = 4  # fewer than this in a year most likely means missing data


def extract() -> pd.DataFrame:
    res = requests.get(URL, headers = {"accept": "application/json"}, timeout = 60)
    if res.status_code == 429:
        raise RuntimeError("HTTP 429: rate limit of ferien-api.de reached, try again later")
    res.raise_for_status()
    return pd.DataFrame(res.json())


def transform(raw: pd.DataFrame) -> pd.DataFrame:
    df = (
        raw.rename(columns = {"stateCode": "subdiv", "start": "start_date", "end": "end_date"})
        # ISO dates (yyyy-mm-dd) compare correctly as strings
        .query("end_date >= @PERIOD_START and start_date <= @PERIOD_END")
        .assign(
            holiday_type = lambda d: d["name"].str.split().str[0],
            is_single_day = lambda d: d["start_date"] == d["end_date"],
        )
        [["subdiv", "start_date", "end_date", "holiday_type", "is_single_day"]]
        .drop_duplicates()
        .sort_values(["subdiv", "start_date", "end_date"])
        .reset_index(drop = True)
    )
    return df


def check(df: pd.DataFrame) -> None:
    unknown = set(df["subdiv"]) - set(STATES)
    if unknown:
        raise ValueError(f"unexpected state codes: {sorted(unknown)}")

    missing = set(STATES) - set(df["subdiv"])
    if missing:
        raise ValueError(f"no school holidays for: {sorted(missing)}")

    if (df["end_date"] < df["start_date"]).any():
        raise ValueError("found periods that end before they start")

    # not errors, but these states / years need a look
    counts = df.groupby(["subdiv", pd.to_datetime(df["start_date"]).dt.year]).size()
    for subdiv in STATES:
        for year in CHECK_YEARS:
            n = int(counts.get((subdiv, year), 0))
            if n < MIN_PERIODS_PER_YEAR:
                print(f"warning: {subdiv} {year} has only {n} school holiday periods")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Download the school holidays (ferien-api.de) and save them as a clean CSV"
    )
    parser.add_argument(
        "--output",
        "--out",
        type = Path,
        default = ROOT / "src/data/intermin/school_holidays.csv",
        help = "output CSV path"
    )
    args = parser.parse_args()

    df = transform(extract())
    check(df)

    args.output.parent.mkdir(parents = True, exist_ok = True)
    df.to_csv(args.output, index = False)
    print(f"saved {len(df):>6} school holiday periods ({df['is_single_day'].sum()} single days) -> {os.path.relpath(args.output)}")


if __name__ == "__main__":
    main()
