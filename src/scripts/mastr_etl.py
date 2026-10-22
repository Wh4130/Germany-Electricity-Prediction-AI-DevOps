"""
ETL: German installed solar (PV) capacity commissioned per day -> src/data/intermin/mastr_solar.csv

Source
    Marktstammdatenregister (MaStR), via the `open-mastr` package
    (https://github.com/OpenEnergyPlatform/open-MaStR). It downloads the official bulk
    XML export for the "solar" category and loads it into a local SQLite database
    (default location: ~/.open-MaStR/data/sqlite/open-mastr.db, not part of this repo).

Why `AnlagenEegSolar`, not `EinheitenSolar`
    `EinheitenSolar` is normally the right table (it is the actual unit registry: one row
    per solar installation, with its net capacity and commissioning date). It is unusable
    right now: `open-mastr==1.0.0` fails to parse every `EinheitenSolar_*.xml` shard of the
    current (2026-10) MaStR release and writes 0 rows, logging e.g.
        Error processing file 'EinheitenSolar_1.xml': 'invalid literal for int() with base
        10: '712 812''
        Error processing file 'EinheitenSolar_11.xml': 'no element found: line 9, ...'
    (see ~/.open-MaStR/logs/open_mastr.log). This traces back to a schema mismatch: the
    package falls back to its bundled, outdated XSD (dated 2026-07-12) because fetching
    the current one fails first, and MaStR's schema changes at every twice-yearly release
    (next: April/October). `AnlagenEegSolar` (the EEG-subsidy registration table, a
    different table in the same bulk download) parses fine and has the same two fields we
    need (commissioning date, capacity), so it is used as a substitute. Re-check this once
    `open-mastr` ships a fix or MaStR's schema stabilizes - `EinheitenSolar` is the more
    complete table.

Known limitations of `AnlagenEegSolar` as a substitute (also documented, with their
consequence for the feature, in src/feature_engineering/mastr_pipeline.py)
    - EEG-registration scope: covers solar units registered for EEG support (feed-in
      tariff or market premium), which is the great majority of German PV but not,
      strictly, every single panel.
    - No decommission date: only a current status (`AnlageBetriebsstatus`). A unit that
      is `Endgültig stillgelegt` (permanently decommissioned) cannot be dated, so this
      script keeps every unit with a plausible commissioning date and never removes one -
      the pipeline's cumulative capacity only ever goes up. ~1.4% of units are currently
      decommissioned (89,735 / 6,587,139 as of the 2026-10-20 download); given how long PV
      systems typically stay in service, the resulting overestimate should be small, but
      it is a real approximation, not an exact figure.
    - Duplicate records: the same unit (by `EegMastrNummer`) can appear more than once
      (re-registrations, corrections). Kept: the most recently updated row per unit.
    - A handful of rows (677 out of 6.59M) have an implausible commissioning date before
      1991 (Germany's first renewable feed-in law), almost certainly a placeholder/default
      value rather than a real date - these are dropped.
    - A smaller handful (~24 out of 6.59M) have a missing or non-positive capacity value -
      dropped for the same reason: clearly bad data, not real 0 kW installations.

What this script does
    1. Extract:  db.download(data = ["solar"]) downloads the MaStR bulk export (one zip of about
                 3.2 GB, 20 - 60 minutes, it starts again from zero if the connection breaks),
                 loads the solar tables into the local SQLite database, then `AnlagenEegSolar`
                 is read into pandas.
    2. Transform: keep one row per unit (latest update wins), keep only plausible
                 commissioning dates (>= 1991-01-01), convert capacity kW -> MW.
    3. Check:    no duplicated unit IDs, no null commissioning dates or capacities, no
                 negative or zero capacities.
    4. Aggregate: add up the capacity of the units by commissioning date (`capacity_mw`, and
                 `n_units` as the number of units). The pipeline only needs this, and the file is
                 small (one row per day, not one per unit), so it is committed to git.
    5. Load:     save as CSV (no row index, a lookup table like population_by_land.csv).
                 One row per commissioning date. The pipeline adds them up over time (cumulative sum).

    The download is the full MaStR export and can break half way (connection reset by the
    server). Run the script again; every machine needs it only once if the CSV is in git.

Run (from the project root)
    uv run python src/scripts/mastr_etl.py
    uv run python src/scripts/mastr_etl.py --output some/path.csv
"""
import argparse
import os
from pathlib import Path

import pandas as pd

MIN_PLAUSIBLE_COMMISSION_DATE = "1991-01-01"  # Stromeinspeisungsgesetz, Germany's first renewable feed-in law

TABLE = "AnlagenEegSolar"
UNIT_ID_COL = "EegMastrNummer"
COMMISSION_COL = "EegInbetriebnahmedatum"
CAPACITY_COL = "InstallierteLeistung"  # kW
LAST_UPDATED_COL = "DatumLetzteAktualisierung"


def extract() -> pd.DataFrame:
    from open_mastr import Mastr  # imported lazily: heavy optional dependency

    db = Mastr()
    db.download(data = ["solar"])

    return pd.read_sql(
        f"SELECT {UNIT_ID_COL}, {COMMISSION_COL}, {CAPACITY_COL}, {LAST_UPDATED_COL} FROM {TABLE}",
        con = db.engine,
    )


def transform(units: pd.DataFrame) -> pd.DataFrame:
    units = units.sort_values(LAST_UPDATED_COL).drop_duplicates(UNIT_ID_COL, keep = "last")

    commission_date = pd.to_datetime(units[COMMISSION_COL], errors = "coerce")
    capacity_mw = units[CAPACITY_COL] / 1000.0
    valid = (
        commission_date.notna()
        & (commission_date >= MIN_PLAUSIBLE_COMMISSION_DATE)
        & capacity_mw.notna()
        & (capacity_mw > 0)
    )

    return pd.DataFrame({
        "mastr_nummer": units.loc[valid, UNIT_ID_COL],
        "commission_date": commission_date[valid],
        "capacity_mw": capacity_mw[valid],
    }).reset_index(drop = True)


def check(solar_units: pd.DataFrame) -> None:
    if solar_units["mastr_nummer"].duplicated().any():
        raise ValueError("duplicated mastr_nummer after dedup")
    if solar_units[["commission_date", "capacity_mw"]].isna().any().any():
        raise ValueError("null commission_date or capacity_mw")
    if (solar_units["capacity_mw"] <= 0).any():
        raise ValueError("non-positive capacity_mw")


def aggregate(solar_units: pd.DataFrame) -> pd.DataFrame:
    """ the capacity that was commissioned on each day (the pipeline only needs this, not every unit) """
    return (
        solar_units.groupby("commission_date")
        .agg(capacity_mw = ("capacity_mw", "sum"), n_units = ("mastr_nummer", "count"))
        .reset_index()
    )


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Download MaStR solar (PV) units and save the capacity commissioned on each day"
    )
    parser.add_argument(
        "--output", "--out",
        type = Path,
        default = ROOT / "src/data/intermin/mastr_solar.csv",
        help = "output CSV path"
    )
    args = parser.parse_args()

    solar_units = transform(extract())
    check(solar_units)
    per_day = aggregate(solar_units)

    args.output.parent.mkdir(parents = True, exist_ok = True)
    per_day.to_csv(args.output, index = False)
    print(f"saved {len(per_day):>8} days ({len(solar_units)} units) -> {os.path.relpath(args.output)}")


if __name__ == "__main__":
    main()
