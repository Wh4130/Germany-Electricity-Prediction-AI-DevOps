"""
ETL: population of the 16 German states -> src/data/intermin/population_by_land.csv

Source
    Destatis table 12411LJ003 "Population, Länder, Reference date", served by DBnomics:
        GET https://api.db.nomics.world/v22/series/DESTATIS/12411LJ003?observations=1
    One series per state, the series code starts with the official Land code ("01.BEVSTD" = Schleswig-Holstein).

What this script does
    1. Extract:   download the 16 series (one request).
    2. Transform: map the official Land code to the state code used by `holidays.Germany(subdiv=...)`
                  ("01" -> "SH"), one row per state and year.
    3. Check:     all 16 states are present, no missing values.
    4. Load:      save as CSV (no row index, this is a lookup table, not a time series).

All available years are saved (from 1958, from 1990 for the eastern states). The pipeline that uses the file picks the year
and turns the population into weights (population share of each state).

Run (from the project root)
    uv run python src/scripts/population_etl.py
    uv run python src/scripts/population_etl.py --output some/other/path.csv
"""
import argparse
import os
from pathlib import Path

import pandas as pd
import requests

URL = "https://api.db.nomics.world/v22/series/DESTATIS/12411LJ003"

# official Land code (Destatis) -> state code of `holidays.Germany(subdiv=...)`
LAND_TO_SUBDIV = {
    "01": "SH", "02": "HH", "03": "NI", "04": "HB",
    "05": "NW", "06": "HE", "07": "RP", "08": "BW",
    "09": "BY", "10": "SL", "11": "BE", "12": "BB",
    "13": "MV", "14": "SN", "15": "ST", "16": "TH",
}


def extract() -> dict:
    res = requests.get(URL, params = {"observations": 1}, timeout = 60)
    res.raise_for_status()
    return res.json()


def transform(raw: dict) -> pd.DataFrame:
    rows = []
    for doc in raw["series"]["docs"]:
        land_code = doc["series_code"].split(".")[0]  # e.g. "01.BEVSTD" -> "01"
        for period, value in zip(doc["period"], doc["value"]):
            rows.append((LAND_TO_SUBDIV[land_code], int(period), value))

    return (
        pd.DataFrame(rows, columns = ["subdiv", "year", "population"])
        .sort_values(["subdiv", "year"])
        .reset_index(drop = True)
    )


def check(df: pd.DataFrame) -> pd.DataFrame:
    if df["subdiv"].nunique() != 16:
        raise ValueError(f"expected 16 states, got {df['subdiv'].nunique()}")
    if df["population"].isna().any():
        raise ValueError("missing population values")
    return df.astype({"population": int})


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Download the population of the 16 states (Destatis via DBnomics) and save it as CSV"
    )
    parser.add_argument(
        "--output",
        "--out",
        type = Path,
        default = ROOT / "src/data/intermin/population_by_land.csv",
        help = "output CSV path"
    )
    args = parser.parse_args()

    df = check(transform(extract()))

    args.output.parent.mkdir(parents = True, exist_ok = True)
    df.to_csv(args.output, index = False)
    print(f"saved {len(df):>6} rows ({df['year'].min()} - {df['year'].max()}) -> {os.path.relpath(args.output)}")


if __name__ == "__main__":
    main()
