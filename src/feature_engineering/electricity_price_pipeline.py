import argparse
import os
from pathlib import Path

import pandas as pd


class ElectricityPriceBuilder:
    """
    Create day-ahead electricity price features for the daily / hourly data.

    The builder does no file I/O and never changes its input: the methods return a new
    DataFrame that only holds the features (same index as the input).

    The day-ahead price of an hour is known around noon of the day before (the auction closes at
    12:00 CET), so the price of the hour itself can be used to predict that hour, if the forecast is made
    after the auction result is out.

    The price file is in UTC. The data has local time (Europe/Berlin) without a time zone, in the hourly data
    the 02:00 at the end of DST is there twice (summer time first). The rows are matched by the UTC time.

    Hourly data:
    - day_ahead_price                                   price of the hour (EUR/MWh)
    Daily data (over the hours of the local day, a day with 23 / 25 hours has that many hours):
    - day_ahead_price_mean, day_ahead_price_min, day_ahead_price_max
    """

    TIMEZONE = "Europe/Berlin"

    def __init__(self, day_ahead_price: pd.DataFrame) -> None:
        """
        `day_ahead_price`: the file made by src/scripts/day_ahead_price_etl.py
        (columns datetime_utc, day_ahead_price)
        """
        price = day_ahead_price.assign(datetime_utc = pd.to_datetime(day_ahead_price["datetime_utc"]))
        self.price_utc = price.set_index("datetime_utc")["day_ahead_price"]

        # the same prices by local day, for the daily features
        local_day = self.price_utc.index.tz_localize("UTC").tz_convert(self.TIMEZONE).date
        self.daily = self.price_utc.groupby(local_day).agg(["mean", "min", "max"])

    def hourly_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """ features of the hourly data """
        local = data["date_from"].dt.tz_localize(
            self.TIMEZONE,
            ambiguous = ~data["date_from"].duplicated(keep = "first").to_numpy(),
        )
        utc_time = local.dt.tz_convert("UTC").dt.tz_localize(None)
        price = utc_time.map(self.price_utc)

        missing = sorted(set(utc_time[price.isna()]))
        if missing:
            raise ValueError(f"no day-ahead price for {len(missing)} hours, e.g. {missing[:3]}")
        return pd.DataFrame({
            "date_from": data["date_from"],  # only to check the rows, merge_all.py drops it
            "day_ahead_price": price,
        })

    def daily_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """ features of the daily data """
        day = data["date_from"].dt.date
        features = pd.DataFrame({
            "date_from": data["date_from"],  # only to check the rows, merge_all.py drops it
            "day_ahead_price_mean": day.map(self.daily["mean"]),
            "day_ahead_price_min": day.map(self.daily["min"]),
            "day_ahead_price_max": day.map(self.daily["max"]),
        })

        if features.isna().any().any():
            missing = sorted(set(day[features.isna().any(axis = 1)]))
            raise ValueError(f"no day-ahead price for the days {missing[:3]} ...")
        return features


def load_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col = 0, parse_dates = ["date_from", "date_to"])


def save_features(features: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents = True, exist_ok = True)
    features.to_csv(path, index = True)  # keep the row index on purpose, it is used to merge features
    print(f"saved {len(features):>6} rows -> {os.path.relpath(path)}")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Create day-ahead electricity price features for the daily and hourly data"
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
        "--dayAheadPriceInput",
        "--dapinp",
        type = Path,
        default = ROOT / "src/data/intermin/day_ahead_price.csv",
        help = "input CSV path for the day-ahead price (made by src/scripts/day_ahead_price_etl.py)"
    )
    parser.add_argument(
        "--hourlyOutput",
        "--hout",
        type = Path,
        default = ROOT / "src/data/features/electricity_price/data_hourly.csv",
        help = "output CSV path for hourly data"
    )
    parser.add_argument(
        "--dailyOutput",
        "--dout",
        type = Path,
        default = ROOT / "src/data/features/electricity_price/data_daily.csv",
        help = "output CSV path for daily data"
    )

    args = parser.parse_args()

    builder = ElectricityPriceBuilder(pd.read_csv(args.dayAheadPriceInput))

    save_features(builder.daily_features(load_data(args.dailyInput)), args.dailyOutput)
    save_features(builder.hourly_features(load_data(args.hourlyInput)), args.hourlyOutput)


if __name__ == "__main__":
    main()
