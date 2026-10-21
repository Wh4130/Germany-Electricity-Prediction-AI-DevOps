"""
Create weather features for the daily and hourly data, from the per-city weather downloaded
by src/scripts/weather_etl.py.

What this pipeline does
    1. Population-weight the 15 cities into a single national value per date/time.
    2. Convert temperature to HDD (Heating Degree Days).
    3. Output only the new columns, row index reset to 0, 1, 2, ... matching intermin/'s row
       order (the row index is used by merge_all.py to join features onto intermin/, see the
       project README).

Does not touch the network: src/scripts/weather_etl.py is the one that downloads the raw,
per-city weather into intermin/weather_daily_by_city.csv and weather_hourly_by_city.csv.

Run (from the project root)
    uv run python src/feature_engineering/weather_pipeline.py
"""

import argparse
import os
from pathlib import Path

import pandas as pd

BASE_TEMP = 18  # HDD base temperature, common energy-industry reference

# must match the columns src/scripts/weather_etl.py writes into intermin/weather_*_by_city.csv

DAILY_VARS = [
    "temperature_2m_mean",
    "daylight_duration",
    "shortwave_radiation_sum",
    "wind_speed_10m_max",
    "precipitation_sum",
]
HOURLY_VARS = [
    "temperature_2m",
    "shortwave_radiation",
    "wind_speed_10m",
    "precipitation",
]


def weights_city_by_population(weather_by_city: pd.DataFrame) -> dict[str, float]:
    """ population share of each city (sums to 1), `population` comes with the weather file """
    population = weather_by_city.drop_duplicates("city").set_index("city")["population"]
    return (population / population.sum()).to_dict()


class WeatherFeatureBuilder:
    """
    Create weather features from the per-city weather downloaded by src/scripts/weather_etl.py.

    The builder does no file I/O and never changes its input: `build_daily`/`build_hourly`
    return a new DataFrame, population-weighted across cities into one row per date/time, with
    the row index reset to 0, 1, 2, ... (same order as intermin/, no date/time column left in).
    """

    def __init__(self, city_weights: dict[str, float]) -> None:
        """ `city_weights`: share of each city (subdiv code -> share, sums to 1) """
        self.city_weights = city_weights

    def weighted_average(self, weather_by_city: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """
        population-weighted average of `columns`, one row per date/time, sorted.

        Grouping only by `date` would merge the two rows that share the same label on the
        autumn DST day (two different real hours both called "02:00") into one wrong,
        double-counted row. Grouping also by the per-city occurrence count keeps them apart:
        every city sees the same real-world clock, so the first occurrence (DST, CEST) sorts
        before the second (CET) for every city alike.
        """
        weights = weather_by_city["city"].map(self.city_weights)
        occurrence = weather_by_city.groupby(["city", "date"]).cumcount()

        weighted = weather_by_city[columns].mul(weights, axis = 0)
        weighted["date"] = weather_by_city["date"]
        weighted["occurrence"] = occurrence

        return (
            weighted.groupby(["date", "occurrence"], sort = True)[columns]
            .sum()
            .reset_index(level = "occurrence", drop = True)
        )

    def heating_degree_days(self, temperature: pd.Series) -> pd.Series:
        """ HDD = max(0, base_temp - temperature) """
        return (BASE_TEMP - temperature).clip(lower = 0)

    def build_daily(self, weather_by_city: pd.DataFrame) -> pd.DataFrame:
        features = self.weighted_average(weather_by_city, DAILY_VARS)
        features = features.rename(columns = {"temperature_2m_mean": "hdd"})
        features["hdd"] = self.heating_degree_days(features["hdd"])
        return features.reset_index(drop = True)

    def build_hourly(self, weather_by_city: pd.DataFrame) -> pd.DataFrame:
        features = self.weighted_average(weather_by_city, HOURLY_VARS)
        features = features.rename(columns = {"temperature_2m": "hdd"})
        features["hdd"] = self.heating_degree_days(features["hdd"])
        return features.reset_index(drop = True)


def load_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates = ["date"])


def save_features(features: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents = True, exist_ok = True)
    features.to_csv(path, index = True)  # keep the row index on purpose, it is used to merge features
    print(f"saved {len(features):>6} rows -> {os.path.relpath(path)}")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Create weather features for the daily and hourly data"
    )
    parser.add_argument(
        "--dailyInput", "--dinp",
        type = Path,
        default = ROOT / "src/data/intermin/weather_daily_by_city.csv",
        help = "input CSV path for daily weather by city (made by src/scripts/weather_etl.py)"
    )
    parser.add_argument(
        "--hourlyInput", "--hinp",
        type = Path,
        default = ROOT / "src/data/intermin/weather_hourly_by_city.csv",
        help = "input CSV path for hourly weather by city (made by src/scripts/weather_etl.py)"
    )
    parser.add_argument(
        "--dailyOutput", "--dout",
        type = Path,
        default = ROOT / "src/data/features/weather/data_daily.csv",
        help = "output CSV path for daily data"
    )
    parser.add_argument(
        "--hourlyOutput", "--hout",
        type = Path,
        default = ROOT / "src/data/features/weather/data_hourly.csv",
        help = "output CSV path for hourly data"
    )
    args = parser.parse_args()

    daily_by_city = load_data(args.dailyInput)
    hourly_by_city = load_data(args.hourlyInput)

    builder = WeatherFeatureBuilder(weights_city_by_population(daily_by_city))

    save_features(builder.build_daily(daily_by_city), args.dailyOutput)
    save_features(builder.build_hourly(hourly_by_city), args.hourlyOutput)


if __name__ == "__main__":
    main()
