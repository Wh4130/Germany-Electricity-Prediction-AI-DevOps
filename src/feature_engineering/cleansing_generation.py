"""
Cleansing: SMARD realised generation by source (raw) -> src/data/intermin/generation_by_source.csv

Raw file:  src/data/raw/Realisierte_Erzeugung_201812230000_202501080000_Stunde.csv
           Manual download from the SMARD download center (https://www.smard.de/home/downloadcenter/download-marktdaten):
           Oberkategorie Stromerzeugung, Datenkategorie Realisierte Erzeugung, Land Deutschland,
           Auflösung Stunde, CSV, 23.12.2018 - 07.01.2025 (the month before our data is for the lagged features).
           Licence CC BY 4.0, cite as "Bundesnetzagentur | SMARD.de".

What this script does
    1. Read:   `;` separated, German numbers (`3.850,39`), `-` means no value.
    2. Rename: the 12 sources get English column names (MWh per hour).
    3. Time:   `Datum von` is local time (Europe/Berlin) without a time zone, the 02:00 at the end of DST is
               there twice (summer time first). It is converted to UTC (`datetime_utc`), so no hour is missing
               or repeated.
    4. Check:  the only `-` allowed are nuclear after the last plants were shut down (2023-04-15), they become 0.
               No missing hour, no negative value.
    5. Save:   CSV (no row index, this is a lookup table, not a time series).

The values are REALISED values, only known after the hour. As a feature they can only be used with a lag.

Run (from the project root)
    uv run python src/feature_engineering/cleansing_generation.py
"""
import argparse
import os
from pathlib import Path

import pandas as pd

# SMARD (German) column name -> English column name
COLUMN_MAP = {
    "Biomasse": "biomass",
    "Wasserkraft": "hydro",
    "Wind Offshore": "wind_offshore",
    "Wind Onshore": "wind_onshore",
    "Photovoltaik": "solar",
    "Sonstige Erneuerbare": "other_renewable",
    "Kernenergie": "nuclear",
    "Braunkohle": "lignite",
    "Steinkohle": "hard_coal",
    "Erdgas": "natural_gas",
    "Pumpspeicher": "pumped_storage",
    "Sonstige Konventionelle": "other_conventional",
}
TIMEZONE = "Europe/Berlin"
NUCLEAR_SHUTDOWN = pd.Timestamp("2023-04-15")  # the last three plants were shut down on this day


def read_raw(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(
        path,
        sep = ";",
        decimal = ",",
        thousands = ".",
        encoding = "utf-8-sig",
        na_values = ["-"],
        dtype = {"Datum von": str, "Datum bis": str},
    )
    # "Biomasse [MWh] Berechnete Auflösungen" -> "Biomasse"
    raw.columns = [c.split(" [")[0] for c in raw.columns]
    return raw.rename(columns = COLUMN_MAP)


def to_utc(local_start: pd.Series) -> pd.Series:
    """ local time without a time zone -> UTC without a time zone """
    local = local_start.dt.tz_localize(
        TIMEZONE,
        ambiguous = ~local_start.duplicated(keep = "first").to_numpy(),  # the first 02:00 is summer time
    )
    return local.dt.tz_convert("UTC").dt.tz_localize(None)


def transform(raw: pd.DataFrame) -> pd.DataFrame:
    local_start = pd.to_datetime(raw["Datum von"], format = "%d.%m.%Y %H:%M")
    sources = list(COLUMN_MAP.values())

    # "-" is only expected for nuclear, after the shutdown: no generation, not a missing value
    missing = raw[sources].isna()
    unexpected = missing.drop(columns = "nuclear").any(axis = None) or (
        missing["nuclear"] & (local_start < NUCLEAR_SHUTDOWN)
    ).any()
    if unexpected:
        raise ValueError("found '-' (no value) that is not nuclear after the shutdown")

    return (
        raw[sources]
        .fillna(0.0)
        .assign(datetime_utc = to_utc(local_start))
        [["datetime_utc"] + sources]
        .sort_values("datetime_utc")
        .reset_index(drop = True)
    )


def check(df: pd.DataFrame) -> None:
    expected = pd.date_range(df["datetime_utc"].iloc[0], df["datetime_utc"].iloc[-1], freq = "h")
    if list(expected) != df["datetime_utc"].tolist():
        raise ValueError("there is a missing or repeated hour")
    if (df.drop(columns = "datetime_utc") < 0).any(axis = None):
        raise ValueError("found negative generation")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Clean the SMARD realised generation (raw) and save it with UTC time and English column names"
    )
    parser.add_argument(
        "--input",
        "--inp",
        type = Path,
        default = ROOT / "src/data/raw/Realisierte_Erzeugung_201812230000_202501080000_Stunde.csv",
        help = "raw CSV path (SMARD download)"
    )
    parser.add_argument(
        "--output",
        "--out",
        type = Path,
        default = ROOT / "src/data/intermin/generation_by_source.csv",
        help = "output CSV path"
    )
    args = parser.parse_args()

    df = transform(read_raw(args.input))
    check(df)

    args.output.parent.mkdir(parents = True, exist_ok = True)
    df.to_csv(args.output, index = False)
    print(f"saved {len(df):>6} hours ({df['datetime_utc'].iloc[0]} - {df['datetime_utc'].iloc[-1]} UTC) -> {os.path.relpath(args.output)}")


if __name__ == "__main__":
    main()
