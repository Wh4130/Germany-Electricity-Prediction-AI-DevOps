"""
ETL: German weather (temperature, radiation, wind, precipitation, daylight) ->
    src/data/intermin/weather_daily_by_city.csv
    src/data/intermin/weather_hourly_by_city.csv

Source
    Open-Meteo Historical Weather (Archive) API, one request per city per resolution:
        GET https://archive-api.open-meteo.com/v1/archive
    Population of the 15 largest German cities: worldpopulationreview.com/cities/germany.

What this script does
    1. Extract:   fetch daily and hourly weather for each of the 15 cities, with retry.
                   Daily is requested in Europe/Berlin (no DST row-count issue at that
                   resolution). Hourly is requested in UTC and converted to Europe/Berlin
                   ourselves (pandas tz database), instead of trusting the API's own
                   fixed-offset-per-day timezone conversion - this reproduces the real German
                   civil time, including the 23-hour spring DST day and the 25-hour autumn one
                   (same as SMARD's data in intermin/data_hourly.csv).
    2. Transform: stack all cities into two long tables (city, date/time, weather columns).
    3. Check:     all 15 cities present, expected row counts, no missing values.
    4. Load:      save as CSV (no row index, lookup tables, not time series).

Not done here (left to the pipeline that uses these files)
    - Population weighting across cities.
    - HDD conversion.

Run (from the project root)
    uv run python src/scripts/weather_etl.py
    uv run python src/scripts/weather_etl.py --dailyOutput some/path.csv --hourlyOutput some/other/path.csv

Takes a few minutes: 15 cities x 2 resolutions = 30 requests, with a polite delay between them.
"""
import argparse
import os
import time
from pathlib import Path

import pandas as pd
import requests

URL = "https://archive-api.open-meteo.com/v1/archive"

START_DATE = "2019-01-01"
END_DATE = "2024-12-31"

DAILY_VARS = [
    "temperature_2m_mean",
    "daylight_duration",
    "shortwave_radiation_sum",
    "wind_speed_10m_mean",
    "precipitation_sum",
]
HOURLY_VARS = [
    "temperature_2m",
    "shortwave_radiation",
    "wind_speed_10m",
    "precipitation",
    "is_day",
]

# top 15 populated German cities (worldpopulationreview.com, 2026 estimate)
CITIES = pd.DataFrame([
    {"city": "Berlin",     "population": 3_775_697, "lat": 52.5244, "lon": 13.4105},
    {"city": "Hamburg",    "population": 1_917_879, "lat": 53.5507, "lon": 9.993},
    {"city": "Munich",     "population": 1_531_842, "lat": 48.1374, "lon": 11.5755},
    {"city": "Cologne",    "population": 1_031_939, "lat": 50.9333, "lon": 6.95},
    {"city": "Frankfurt",  "population": 768_993,   "lat": 50.1155, "lon": 8.6842},
    {"city": "Dusseldorf", "population": 626_202,   "lat": 51.2232, "lon": 6.7793},
    {"city": "Leipzig",    "population": 625_081,   "lat": 51.3396, "lon": 12.3713},
    {"city": "Stuttgart",  "population": 614_876,   "lat": 48.7823, "lon": 9.177},
    {"city": "Dortmund",   "population": 608_723,   "lat": 51.5149, "lon": 7.466},
    {"city": "Bremen",     "population": 597_689,   "lat": 53.0758, "lon": 8.8072},
    {"city": "Essen",      "population": 578_348,   "lat": 51.4566, "lon": 7.0123},
    {"city": "Dresden",    "population": 572_117,   "lat": 51.0509, "lon": 13.7383},
    {"city": "Nuremberg",  "population": 536_555,   "lat": 49.4542, "lon": 11.0775},
    {"city": "Hannover",   "population": 531_123,   "lat": 52.3705, "lon": 9.7332},
    {"city": "Duisburg",   "population": 503_126,   "lat": 51.4325, "lon": 6.7652},
])

# fetch one extra UTC day on each side for hourly: the German-time boundary (00:00 on the
# first day, 23:00 on the last) can fall on the UTC day before (start) or after (end),
# depending on whether that date is in CET (+1) or CEST (+2)

HOURLY_FETCH_START = (pd.Timestamp(START_DATE) - pd.Timedelta(days = 1)).strftime("%Y-%m-%d")
HOURLY_FETCH_END = (pd.Timestamp(END_DATE) + pd.Timedelta(days = 1)).strftime("%Y-%m-%d")

EXPECTED_DAILY_ROWS_PER_CITY = len(pd.date_range(START_DATE, END_DATE, freq = "D"))
EXPECTED_HOURLY_ROWS_PER_CITY = EXPECTED_DAILY_ROWS_PER_CITY * 24


def fetch(params: dict, retries: int = 6) -> dict:
    """ GET the archive API, retry on failure (network error or non-200 response) """
    last_err = None
    for attempt in range(retries):
        try:
            response = requests.get(URL, params = params, timeout = 100)
            if response.status_code == 200 and response.text.strip():
                return response.json()
            last_err = f"HTTP {response.status_code}: {response.text[:200]}"
        except requests.exceptions.RequestException as e:
            last_err = e
        time.sleep(5)
    raise RuntimeError(f"fetch failed after {retries} retries ({params}): {last_err}")


def fetch_daily(lat: float, lon: float) -> pd.DataFrame:
    data = fetch({
        "latitude": lat,
        "longitude": lon,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": ",".join(DAILY_VARS),
        "timezone": "Europe/Berlin",  # no DST row-count issue at daily resolution
    })["daily"]

    df = pd.DataFrame(data).rename(columns = {"time": "date"})
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch_hourly(lat: float, lon: float) -> pd.DataFrame:
    data = fetch({
        "latitude": lat,
        "longitude": lon,
        "start_date": HOURLY_FETCH_START,
        "end_date": HOURLY_FETCH_END,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "UTC",  # convert to Europe/Berlin ourselves below, see module docstring
    })["hourly"]

    df = pd.DataFrame(data).rename(columns = {"time": "date"})
    df["date"] = pd.to_datetime(df["date"], utc = True)
    df["date"] = df["date"].dt.tz_convert("Europe/Berlin")
    df["date"] = df["date"].dt.tz_localize(None)  # drop tz info, back to naive

    # trim the buffer days back down to the exact requested German-time range
    return df[(df["date"] >= START_DATE) & (df["date"] <= f"{END_DATE} 23:00:00")]


def extract() -> tuple[pd.DataFrame, pd.DataFrame]:
    daily_rows, hourly_rows = [], []
    for _, city in CITIES.iterrows():
        daily = fetch_daily(city["lat"], city["lon"])
        daily.insert(0, "population", city["population"])
        daily.insert(0, "city", city["city"])
        daily_rows.append(daily)

        hourly = fetch_hourly(city["lat"], city["lon"])
        hourly.insert(0, "population", city["population"])
        hourly.insert(0, "city", city["city"])
        hourly_rows.append(hourly)

        print(f"{city['city']} done")
        time.sleep(10)

    return (
        pd.concat(daily_rows, ignore_index = True),
        pd.concat(hourly_rows, ignore_index = True),
    )


def check(daily: pd.DataFrame, hourly: pd.DataFrame) -> None:
    cities = set(CITIES["city"])

    missing_daily = cities - set(daily["city"])
    if missing_daily:
        raise ValueError(f"no daily weather for: {sorted(missing_daily)}")
    missing_hourly = cities - set(hourly["city"])
    if missing_hourly:
        raise ValueError(f"no hourly weather for: {sorted(missing_hourly)}")

    bad_daily = daily.groupby("city").size()[lambda s: s != EXPECTED_DAILY_ROWS_PER_CITY]
    if len(bad_daily):
        raise ValueError(f"expected {EXPECTED_DAILY_ROWS_PER_CITY} daily rows per city, got:\n{bad_daily}")
    bad_hourly = hourly.groupby("city").size()[lambda s: s != EXPECTED_HOURLY_ROWS_PER_CITY]
    if len(bad_hourly):
        raise ValueError(f"expected {EXPECTED_HOURLY_ROWS_PER_CITY} hourly rows per city, got:\n{bad_hourly}")

    if daily[DAILY_VARS].isna().any().any():
        raise ValueError("missing values in daily weather")
    if hourly[HOURLY_VARS].isna().any().any():
        raise ValueError("missing values in hourly weather")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Download daily and hourly weather (Open-Meteo archive) for the 15 largest German cities"
    )
    parser.add_argument(
        "--dailyOutput", "--dout",
        type = Path,
        default = ROOT / "src/data/intermin/weather_daily_by_city.csv",
        help = "output CSV path for daily data"
    )
    parser.add_argument(
        "--hourlyOutput", "--hout",
        type = Path,
        default = ROOT / "src/data/intermin/weather_hourly_by_city.csv",
        help = "output CSV path for hourly data"
    )
    args = parser.parse_args()

    daily, hourly = extract()
    check(daily, hourly)

    for df, path in [(daily, args.dailyOutput), (hourly, args.hourlyOutput)]:
        path.parent.mkdir(parents = True, exist_ok = True)
        df.to_csv(path, index = False)
        print(f"saved {len(df):>6} rows -> {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
