"""
Create the solar (PV) installed-capacity feature for the daily data, from the per-unit
MaStR data downloaded by src/scripts/mastr_etl.py.

What this pipeline does
    For every day, sum the net capacity of every unit whose commissioning date is on or
    before that day -> `solar_capacity_mw`, a single running total (MW) for all of Germany.
    Units are never removed once commissioned (see "Known limitations" below), so the
    series is non-decreasing by construction. Output is the new column only, same row
    index as intermin/data_daily.csv (the row index is used by merge_all.py to join
    features onto intermin/, see the project README).

Does not touch the network: src/scripts/mastr_etl.py is the one that downloads the raw,
per-unit MaStR data into intermin/mastr_solar.csv.

Hourly file is a same-day broadcast, not real hourly resolution
    Installed capacity is a registry fact (when a unit was commissioned), not something
    that changes within a day. `data_hourly.csv` repeats each day's `solar_capacity_mw`
    across all 24 of its hours (same value, looked up via the same `build`, since it only
    keys off the date). It exists so the column is available to an hourly model (e.g.
    multiplied by the hourly weather feature's `shortwave_radiation` as a generation
    proxy, which does carry real intra-day shape) - on its own this column carries no
    intra-day information.

Feature characteristics and known limitations (carried over from src/scripts/mastr_etl.py,
restated here because they shape what this column does and does not mean)
    - This is installed capacity, not generation. It says how much PV *could* produce at
      full sun, not how much it actually produced on a given day - combine it with a solar
      irradiance variable (e.g. the weather feature's `shortwave_radiation_sum`, not
      `daylight_duration` which ignores cloud cover) for a generation proxy.
    - Monotonically non-decreasing by construction: `intermin/mastr_solar.csv` has no
      decommissioning date (MaStR's `AnlagenEegSolar` table only has a current status, not
      a date), so a unit's capacity is added at commissioning and never removed. About
      1.4% of units are currently decommissioned (as of the 2026-10-20 download) - given
      how long PV systems typically stay in service, this should make the later years of
      the series a slight overestimate, not a large one, but it is an approximation.
    - Source coverage: `AnlagenEegSolar` is MaStR's EEG-subsidy registration table, which
      covers the great majority of German PV (feed-in tariff or market premium) but not,
      strictly, every single panel in the country.
    - Known-good substitute for a broken table: the actual MaStR unit registry
      (`EinheitenSolar`) fails to parse under `open-mastr==1.0.0` against the current
      (2026-10) MaStR release (schema mismatch, see src/scripts/mastr_etl.py docstring for
      the exact error and root cause). If a future `open-mastr` version fixes this,
      `EinheitenSolar` would be the more complete and more accurate source.
    - As an exogenous variable: unlike weather, this does not need a real forecast to be
      usable at prediction time - the series is slow-moving and close to monotonic, so the
      last known value or a simple trend extrapolation is a reasonable stand-in for the
      near future. It does need to be refreshed periodically from MaStR to stay current
      as new capacity comes online.

Run (from the project root)
    uv run python src/feature_engineering/mastr_pipeline.py
"""
import argparse
import os
from pathlib import Path

import pandas as pd


class SolarCapacityFeatureBuilder:
    """
    Create the cumulative installed solar capacity feature from the per-unit MaStR data
    downloaded by src/scripts/mastr_etl.py.

    The builder does no file I/O and never changes its input: `build` returns a new
    DataFrame with the same row index as `data`, holding only the new column.
    """

    def __init__(self, solar_units: pd.DataFrame) -> None:
        """ `solar_units`: the file made by src/scripts/mastr_etl.py (one row per unit) """
        additions = solar_units.groupby("commission_date")["capacity_mw"].sum()
        self.cumulative_capacity = additions.sort_index().cumsum()

    def build(self, data: pd.DataFrame) -> pd.DataFrame:
        """ return the `solar_capacity_mw` feature, aligned to the row index of `data` """
        dates = data["date_from"].dt.normalize()

        first_commissioned = self.cumulative_capacity.index.min()
        if dates.min() < first_commissioned:
            raise ValueError(
                f"data starts {dates.min().date()}, before the first commissioned unit "
                f"{first_commissioned.date()}"
            )

        capacity = self.cumulative_capacity.reindex(dates, method = "ffill")
        return pd.DataFrame({"solar_capacity_mw": capacity.to_numpy()}, index = data.index)


def load_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col = 0, parse_dates = ["date_from", "date_to"])


def load_solar_units(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates = ["commission_date"])


def save_features(features: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents = True, exist_ok = True)
    features.to_csv(path, index = True)  # keep the row index on purpose, it is used to merge features
    print(f"saved {len(features):>6} rows -> {os.path.relpath(path)}")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Create the solar installed-capacity feature for the daily data"
    )
    parser.add_argument(
        "--dailyInput", "--dinp",
        type = Path,
        default = ROOT / "src/data/intermin/data_daily.csv",
        help = "input CSV path for daily data"
    )
    parser.add_argument(
        "--hourlyInput", "--hinp",
        type = Path,
        default = ROOT / "src/data/intermin/data_hourly.csv",
        help = "input CSV path for hourly data"
    )
    parser.add_argument(
        "--solarInput", "--sinp",
        type = Path,
        default = ROOT / "src/data/intermin/mastr_solar.csv",
        help = "input CSV path for per-unit solar data (made by src/scripts/mastr_etl.py)"
    )
    parser.add_argument(
        "--dailyOutput", "--dout",
        type = Path,
        default = ROOT / "src/data/features/mastr/data_daily.csv",
        help = "output CSV path for daily data"
    )
    parser.add_argument(
        "--hourlyOutput", "--hout",
        type = Path,
        default = ROOT / "src/data/features/mastr/data_hourly.csv",
        help = "output CSV path for hourly data (same-day broadcast, see module docstring)"
    )
    args = parser.parse_args()

    daily = load_data(args.dailyInput)
    hourly = load_data(args.hourlyInput)
    solar_units = load_solar_units(args.solarInput)

    builder = SolarCapacityFeatureBuilder(solar_units)
    save_features(builder.build(daily), args.dailyOutput)
    save_features(builder.build(hourly), args.hourlyOutput)


if __name__ == "__main__":
    main()
