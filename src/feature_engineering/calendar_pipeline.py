import argparse
import os
from pathlib import Path
import holidays
import pandas as pd


def weights_land_by_population(
        population: pd.DataFrame,
        year: int = 2023
) -> dict[str, float]:
    """
    Population share of the 16 Länder in `year`.
    `population` is the file made by src/scripts/population_etl.py (columns subdiv, year, population).
    """
    in_year = population[population["year"] == year].set_index("subdiv")["population"]
    if len(in_year) != 16:
        raise ValueError(f"expected 16 Länder in {year}, got {len(in_year)}")

    return (in_year / in_year.sum()).to_dict()


class CalendarFeatureBuilder:
    """
    Create calendar features from the `date_from` column of the daily / hourly data.

    The builder does no file I/O and never changes its input: `build` returns a new
    DataFrame that only holds the features (same index as the input).
    Each feature is one method that returns a Series. A feature that needs another
    one calls that method (e.g. `is_bridge_day` will call `is_holiday`), so there is
    no hidden order between the features.

    Done:
    - month
    - day_of_week_raw
    - day_of_week
    - is_holiday
    - is_weekday
    - weighted_regional_holiday
    - weighted_school_holiday
    - is_bridge_day
    - is_christmas_new_year
    - is_dst
    - is_dst_transition_day

    Not done on purpose: is_carnival (see "Considered, not done" in the README).
    """

    TIMEZONE = "Europe/Berlin"
    # christmas / new year period as month * 100 + day: from 24 Dec until 1 Jan (included)
    CHRISTMAS_NEW_YEAR_FROM = 1224
    CHRISTMAS_NEW_YEAR_TO = 101

    def __init__(
        self,
        start_year: int,
        end_year: int,
        land_weights: dict[str, float],
        school_holidays: pd.DataFrame,
        include_single_days: bool = False,
    ) -> None:
        """
        shared by all holiday related features, so it is built only once
        `land_weights`: weight of each Land (subdiv code -> share, sums to 1)
        `school_holidays`: the file made by src/scripts/school_holidays_etl.py
        `include_single_days`: also count one-day school holidays (e.g. a movable day off), default: only real holiday periods
        """
        self.years = range(start_year, end_year + 1)

        # holidays for entire Germany (one year more on each side, `is_bridge_day` looks at the neighbour days)
        self.holidays_de = holidays.Germany(years = range(start_year - 1, end_year + 2))
        self.holiday_dates = set(self.holidays_de)

        # weights (population share) of each Land
        self.land_weight_map = land_weights

        # holidays by Land
        self.holiday_dates_by_land = {
            subdiv: set(holidays.Germany(
                subdiv = subdiv,
                years = self.years
            ))
            for subdiv in self.land_weight_map.keys()
        }

        # school holiday days by Land: the union of all periods of a Land (they can overlap)
        periods = school_holidays if include_single_days else school_holidays[~school_holidays["is_single_day"]]
        self.school_holiday_dates_by_land = {
            subdiv: {
                day
                for _, p in periods[periods["subdiv"] == subdiv].iterrows()
                for day in pd.date_range(p["start_date"], p["end_date"]).date
            }
            for subdiv in self.land_weight_map.keys()
        }
        no_school_holidays = [s for s, days in self.school_holiday_dates_by_land.items() if not days]
        if no_school_holidays:
            raise ValueError(f"no school holidays for {no_school_holidays}")

        # period that is covered by the school holiday file
        self.school_first_day = pd.to_datetime(school_holidays["start_date"]).min().date()
        self.school_last_day = pd.to_datetime(school_holidays["end_date"]).max().date()



    def build(
        self,
        data: pd.DataFrame
    ) -> pd.DataFrame:
        """ return all calendar features of `data` """
        outside = set(data["date_from"].dt.year) - set(self.years)
        if outside:
            raise ValueError(f"years {sorted(outside)} are outside of the holiday calendar {self.years}")

        dates = data["date_from"].dt.date
        if dates.min() < self.school_first_day or dates.max() > self.school_last_day:
            raise ValueError(
                f"the data ({dates.min()} - {dates.max()}) is not covered by the school holidays "
                f"({self.school_first_day} - {self.school_last_day})"
            )

        return pd.DataFrame({
            "date_from": data["date_from"],  # only to check the rows, merge_all.py drops it
            "month": self.month(data),
            "day_of_week_raw": self.day_of_week_raw(data),
            "day_of_week": self.day_of_week(data),
            "is_holiday": self.is_holiday(data),
            "is_weekday": self.is_weekday(data),
            "weighted_regional_holiday": self.weighted_regional_holiday(data),
            "weighted_school_holiday": self.weighted_school_holiday(data),
            "is_bridge_day": self.is_bridge_day(data),
            "is_christmas_new_year": self.is_christmas_new_year(data),
            "is_dst": self.is_dst(data),
            "is_dst_transition_day": self.is_dst_transition_day(data),
        })


    def month(self, data: pd.DataFrame) -> pd.Series:
        """ month indicator (1 - 12) """
        return data["date_from"].dt.month

    def day_of_week_raw(self, data: pd.DataFrame) -> pd.Series:
        """ weekday number, 0 = Monday ... 6 = Sunday """
        return data["date_from"].dt.dayofweek

    def day_of_week(self, data: pd.DataFrame) -> pd.Series:
        """ weekday name """
        return data["date_from"].dt.day_name()

    def is_holiday(self, data: pd.DataFrame) -> pd.Series:
        """ national public holiday (also True when it falls on a weekend) """
        return data["date_from"].dt.date.isin(self.holiday_dates)

    def is_weekday(self, data: pd.DataFrame) -> pd.Series:
        """ Monday to Friday (public holidays are not taken into account) """
        return self.day_of_week_raw(data) < 5

    def weighted_regional_holiday(self, data: pd.DataFrame) -> pd.Series:
        """
        share of the population (0 - 1) that has a regional public holiday on that day.
        National holidays are not counted (they are in `is_holiday`), so this is 0 on those days.
        """
        dates = data["date_from"].dt.date
        regional_holiday = pd.Series(0.0, index = data.index)
        for subdiv, weight in self.land_weight_map.items():
            regional_only = self.holiday_dates_by_land[subdiv] - self.holiday_dates
            regional_holiday += dates.isin(regional_only) * weight
        return regional_holiday

    def weighted_school_holiday(self, data: pd.DataFrame) -> pd.Series:
        """
        share of the population (0 - 1) of the Länder that are in school holidays on that day.
        School holidays are not part of the public holidays, so nothing is subtracted:
        days that are both (e.g. Easter Monday) count in `is_holiday` and here.
        """
        dates = data["date_from"].dt.date
        school_holiday = pd.Series(0.0, index = data.index)
        for subdiv, weight in self.land_weight_map.items():
            school_holiday += dates.isin(self.school_holiday_dates_by_land[subdiv]) * weight
        return school_holiday

    def is_bridge_day(self, data: pd.DataFrame) -> pd.Series:
        """
        Monday before a Tuesday holiday, or Friday after a Thursday holiday (national holidays).
        A Wednesday holiday has no bridge day, and a day that is a holiday itself is not a bridge day.
        """
        day = data["date_from"]
        weekday = self.day_of_week_raw(data)
        tomorrow_is_holiday = (day + pd.Timedelta(days = 1)).dt.date.isin(self.holiday_dates)
        yesterday_is_holiday = (day - pd.Timedelta(days = 1)).dt.date.isin(self.holiday_dates)

        monday_before_tuesday_holiday = (weekday == 0) & tomorrow_is_holiday
        friday_after_thursday_holiday = (weekday == 4) & yesterday_is_holiday
        return (monday_before_tuesday_holiday | friday_after_thursday_holiday) & ~self.is_holiday(data)

    def is_christmas_new_year(self, data: pd.DataFrame) -> pd.Series:
        """ fixed window from 24 Dec to 1 Jan (the real shutdown days differ from company to company) """
        month_day = data["date_from"].dt.month * 100 + data["date_from"].dt.day
        return (month_day >= self.CHRISTMAS_NEW_YEAR_FROM) | (month_day <= self.CHRISTMAS_NEW_YEAR_TO)

    def is_dst(self, data: pd.DataFrame) -> pd.Series:
        """
        daylight saving time (summer time) is in effect at `date_from`.
        `date_from` is local time without a time zone: in the hourly data the 02:00 at the end of DST is there
        twice, the first one is summer time, the second one is not.
        """
        local = data["date_from"].dt.tz_localize(
            self.TIMEZONE,
            ambiguous = ~data["date_from"].duplicated(keep = "first").to_numpy(),
        )
        utc_offset = local.dt.tz_localize(None) - local.dt.tz_convert("UTC").dt.tz_localize(None)
        return utc_offset == pd.Timedelta(hours = 2)

    def is_dst_transition_day(self, data: pd.DataFrame) -> pd.Series:
        """ day with 23 hours (start of DST) or 25 hours (end of DST) """
        midnight = data["date_from"].dt.normalize()
        start = midnight.dt.tz_localize(self.TIMEZONE)
        end = (midnight + pd.Timedelta(days = 1)).dt.tz_localize(self.TIMEZONE)
        return (end - start) != pd.Timedelta(hours = 24)


def load_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col = 0, parse_dates = ["date_from", "date_to"])


def save_features(features: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents = True, exist_ok = True)
    features.to_csv(path, index = True)  # keep the row index on purpose, it is used to merge features
    print(f"saved {len(features):>6} rows -> {os.path.relpath(path)}")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Create calendar features for the daily and hourly data"
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
        "--populationInput",
        "--pinp",
        type = Path,
        default = ROOT / "src/data/intermin/population_by_land.csv",
        help = "input CSV path for the population of each Land (made by src/scripts/population_etl.py)"
    )
    parser.add_argument(
        "--populationYear",
        type = int,
        default = 2023,
        help = "year of the population that is used for the weights"
    )
    parser.add_argument(
        "--schoolHolidaysInput",
        "--shinp",
        type = Path,
        default = ROOT / "src/data/intermin/school_holidays.csv",
        help = "input CSV path for the school holidays of each Land (made by src/scripts/school_holidays_etl.py)"
    )
    parser.add_argument(
        "--includeSingleDays",
        action = "store_true",
        help = "also count one-day school holidays (e.g. a movable day off), default: only holiday periods"
    )
    parser.add_argument(
        "--hourlyOutput",
        "--hout",
        type = Path,
        default = ROOT / "src/data/features/calendar/data_hourly.csv",
        help = "output CSV path for hourly data"
    )
    parser.add_argument(
        "--dailyOutput",
        "--dout",
        type = Path,
        default = ROOT / "src/data/features/calendar/data_daily.csv",
        help = "output CSV path for daily data"
    )

    args = parser.parse_args()

    daily = load_data(args.dailyInput)
    hourly = load_data(args.hourlyInput)

    years = pd.concat([daily["date_from"], hourly["date_from"]]).dt.year
    land_weights = weights_land_by_population(pd.read_csv(args.populationInput), args.populationYear)
    school_holidays = pd.read_csv(args.schoolHolidaysInput)
    builder = CalendarFeatureBuilder(
        years.min(), years.max(), land_weights, school_holidays, args.includeSingleDays
    )

    save_features(builder.build(daily), args.dailyOutput)
    save_features(builder.build(hourly), args.hourlyOutput)


if __name__ == "__main__":
    main()
