import argparse
import os
from pathlib import Path

import pandas as pd


class GenerationBuilder:
    """
    Create the realised generation by source for the daily / hourly data.

    The builder does no file I/O and never changes its input: the methods return a new
    DataFrame that only holds the features (same index as the input).

    WARNING: DO NOT USE THESE COLUMNS AS THEY ARE TO PREDICT THE LOAD. They are realised values of the same
    hour / day: the generation of all sources is about the load (the sum of all 12 sources is 1.01 times the
    actual consumption on average, a linear fit on them gives R2 = 0.85), and the values are only known after
    the hour. This is target leakage. To use them in a model, shift them first (e.g. the value of the day
    before) and check it with an ablation.

    Hourly data: `generation_<source>`, MWh of the hour.
    Daily data:  `generation_<source>`, MWh of the day (sum of its hours, a day with 23 / 25 hours has that many).

    The generation file and the data have different time zones: the file is in UTC, the data is local time
    (Europe/Berlin) without a time zone, in the hourly data the 02:00 at the end of DST is there twice
    (summer time first). The rows are matched by the UTC time.
    """

    TIMEZONE = "Europe/Berlin"
    SOURCES = ["wind_onshore", "wind_offshore", "solar", "lignite", "hard_coal", "natural_gas", "nuclear"]

    def __init__(self, generation: pd.DataFrame) -> None:
        """
        `generation`: the file made by src/pipelines/cleansing_generation.py
        (columns datetime_utc and one column per source, MWh per hour)
        """
        generation = generation.assign(datetime_utc = pd.to_datetime(generation["datetime_utc"]))
        self.generation_utc = generation.set_index("datetime_utc")[self.SOURCES]

        # the same generation summed by local day, for the daily features
        local_day = self.generation_utc.index.tz_localize("UTC").tz_convert(self.TIMEZONE).date
        self.daily = self.generation_utc.groupby(local_day).sum()

    def hourly_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """ features of the hourly data """
        local = data["date_from"].dt.tz_localize(
            self.TIMEZONE,
            ambiguous = ~data["date_from"].duplicated(keep = "first").to_numpy(),
        )
        utc_time = local.dt.tz_convert("UTC").dt.tz_localize(None)

        features = pd.DataFrame({
            f"generation_{source}": utc_time.map(self.generation_utc[source])
            for source in self.SOURCES
        })
        if features.isna().any().any():
            raise ValueError(f"no generation for {int(features.isna().any(axis = 1).sum())} hours")
        return features

    def daily_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """ features of the daily data """
        day = data["date_from"].dt.date

        features = pd.DataFrame({
            f"generation_{source}": day.map(self.daily[source])
            for source in self.SOURCES
        })
        if features.isna().any().any():
            raise ValueError(f"no generation for {int(features.isna().any(axis = 1).sum())} days")
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
        description = "Create the realised generation by source for the daily and hourly data (not for predicting the load as they are)"
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
        "--generationInput",
        "--ginp",
        type = Path,
        default = ROOT / "src/data/intermin/generation_by_source.csv",
        help = "input CSV path for the generation (made by src/pipelines/cleansing_generation.py)"
    )
    parser.add_argument(
        "--hourlyOutput",
        "--hout",
        type = Path,
        default = ROOT / "src/data/features/generation/data_hourly.csv",
        help = "output CSV path for hourly data"
    )
    parser.add_argument(
        "--dailyOutput",
        "--dout",
        type = Path,
        default = ROOT / "src/data/features/generation/data_daily.csv",
        help = "output CSV path for daily data"
    )

    args = parser.parse_args()

    builder = GenerationBuilder(pd.read_csv(args.generationInput))

    save_features(builder.daily_features(load_data(args.dailyInput)), args.dailyOutput)
    save_features(builder.hourly_features(load_data(args.hourlyInput)), args.hourlyOutput)


if __name__ == "__main__":
    main()
