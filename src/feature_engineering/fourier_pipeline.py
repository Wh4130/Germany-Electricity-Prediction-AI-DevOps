"""
Fourier terms (sin / cos of the time) for the daily / hourly data -> src/data/features/fourier/

    sin(2 pi k t / P), cos(2 pi k t / P)   for k = 1 ... K

They are a smooth way to describe a seasonal pattern with few columns, e.g. for a model that does not
difference the series (SARIMAX with weekday dummies + yearly Fourier terms). They only depend on the
time, so they are known for the future too.

    yearly   P = 365.25 days    daily and hourly data   sin_y1, cos_y1 ... sin_y10, cos_y10
    daily    P = 24 hours       hourly data only        sin_d1, cos_d1 ... sin_d6, cos_d6

The terms of a lower k are the same whatever K is, so a model can use only the first k it needs.
No weekly terms (P = 7 days / 168 hours) on purpose, see "Not done / planned" in docs/FEATURES.md.

Run (from the project root)
    uv run python src/feature_engineering/fourier_pipeline.py
"""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd


class FourierFeatureBuilder:
    """
    Create the Fourier terms from the `date_from` column of the daily / hourly data.

    The builder does no file I/O and never changes its input: the methods return a new
    DataFrame that only holds the features (same index as the input).

    - yearly: t = days since YEARLY_ORIGIN (a fixed date, not the first row of the data, so the columns do not
      change when the period of the data changes). In the hourly data t has the fraction of the day.
      `date_from` is the local time without a time zone, so the terms follow the local calendar day.
    - daily (hourly data only): t = local hour of the day (0 - 23), because the load follows the local
      clock. On the two days with 23 / 25 hours the hour 02 is missing / twice in the data; the twice
      repeated 02:00 gets the same terms.
    """

    YEARLY_PERIOD = 365.25
    YEARLY_ORIGIN = pd.Timestamp("2019-01-01")
    YEARLY_K = 10
    DAILY_PERIOD = 24
    DAILY_K = 6

    def daily_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """ features of the daily data """
        return self.with_key(data, self.yearly(data))

    def hourly_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """ features of the hourly data """
        return self.with_key(data, self.yearly(data), self.daily(data))

    @staticmethod
    def with_key(data: pd.DataFrame, *terms: pd.DataFrame) -> pd.DataFrame:
        key = pd.DataFrame({"date_from_utc": data["date_from_utc"]})  # the key to merge the features
        return pd.concat([key, *terms], axis = 1)

    def yearly(self, data: pd.DataFrame) -> pd.DataFrame:
        """ sin_y<k>, cos_y<k>: P = 365.25 days """
        t = (data["date_from"] - self.YEARLY_ORIGIN) / pd.Timedelta(days = 1)
        return self.terms(t, self.YEARLY_PERIOD, self.YEARLY_K, "y")

    def daily(self, data: pd.DataFrame) -> pd.DataFrame:
        """ sin_d<k>, cos_d<k>: P = 24 hours """
        return self.terms(data["date_from"].dt.hour, self.DAILY_PERIOD, self.DAILY_K, "d")

    @staticmethod
    def terms(t: pd.Series, period: float, max_k: int, name: str) -> pd.DataFrame:
        columns = {}
        for k in range(1, max_k + 1):
            angle = 2 * np.pi * k * t / period
            columns[f"sin_{name}{k}"] = np.sin(angle)
            columns[f"cos_{name}{k}"] = np.cos(angle)
        return pd.DataFrame(columns)


def load_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col = 0, parse_dates = ["date_from", "date_to"])


def save_features(features: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents = True, exist_ok = True)
    features.to_csv(path, index = True)  # keep the row index on purpose, it is used to merge features
    print(f"saved {len(features):>6} rows -> {os.path.relpath(path)}")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Create Fourier terms (sin / cos) for the daily and hourly data"
    )
    parser.add_argument(
        "--hourlyInput",
        "--hinp",
        type = Path,
        default = ROOT / "src/data/intermin/data_hourly.csv",
        help = "input CSV path for hourly data"
    )
    parser.add_argument(
        "--dailyInput",
        "--dinp",
        type = Path,
        default = ROOT / "src/data/intermin/data_daily.csv",
        help = "input CSV path for daily data"
    )
    parser.add_argument(
        "--hourlyOutput",
        "--hout",
        type = Path,
        default = ROOT / "src/data/features/fourier/data_hourly.csv",
        help = "output CSV path for hourly data"
    )
    parser.add_argument(
        "--dailyOutput",
        "--dout",
        type = Path,
        default = ROOT / "src/data/features/fourier/data_daily.csv",
        help = "output CSV path for daily data"
    )

    args = parser.parse_args()

    builder = FourierFeatureBuilder()
    save_features(builder.daily_features(load_data(args.dailyInput)), args.dailyOutput)
    save_features(builder.hourly_features(load_data(args.hourlyInput)), args.hourlyOutput)


if __name__ == "__main__":
    main()
