"""Tests for oxcgrt_pipeline.py (synthetic data; one optional test on the real raw file)."""

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_engineering import oxcgrt_pipeline as ox

REAL_RAW = PROJECT_ROOT / "src" / "data" / "external_raw" / ox.RAW_FILENAME


# --------------------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------------------
def _raw_rows(country: str, dates: pd.DatetimeIndex, stringency: float, c2: float) -> pd.DataFrame:
    return pd.DataFrame({
        "CountryName": country,
        "CountryCode": country,
        "RegionName": "",
        "RegionCode": "",
        "Jurisdiction": "NAT_TOTAL",
        "Date": dates.strftime("%Y%m%d"),
        "C1M_School closing": "2.00",
        "C1M_Flag": "1",
        "C2M_Workplace closing": f"{c2:.2f}",
        "C2M_Flag": "1",
        "C6M_Stay at home requirements": "1.00",
        "C6M_Flag": "1",
        "StringencyIndex_Average": f"{stringency:.2f}",
    })


@pytest.fixture
def raw_file(tmp_path: Path) -> Path:
    de = _raw_rows("DEU", pd.date_range("2020-01-01", "2020-01-10"), stringency=50.0, c2=2.0)
    fr = _raw_rows("FRA", pd.date_range("2020-01-01", "2020-01-10"), stringency=99.0, c2=3.0)
    path = tmp_path / ox.RAW_FILENAME
    pd.concat([de, fr]).to_csv(path, index=False)
    return path


START, END = "2019-12-30", "2020-01-15"


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------
def test_load_germany_filters_country_and_renames(raw_file):
    de = ox.load_germany(raw_file)
    assert list(de.columns) == ["date", *ox.FEATURE_COLUMNS]
    assert len(de) == 10
    assert (de["oxcgrt_stringency"] == 50.0).all()  # FRA rows (99) excluded


def test_load_germany_missing_column_raises(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"CountryCode": ["DEU"], "Jurisdiction": ["NAT_TOTAL"], "Date": ["20200101"]}).to_csv(path, index=False)
    with pytest.raises(KeyError, match="missing expected columns"):
        ox.load_germany(path)


def test_load_germany_duplicate_dates_raise(tmp_path):
    rows = _raw_rows("DEU", pd.DatetimeIndex(["2020-01-01", "2020-01-01"]), 10.0, 1.0)
    path = tmp_path / "dup.csv"
    rows.to_csv(path, index=False)
    with pytest.raises(ValueError, match="Duplicate dates"):
        ox.load_germany(path)


# --------------------------------------------------------------------------------------
# Daily build
# --------------------------------------------------------------------------------------
def test_daily_zero_outside_coverage_and_observed_flag(raw_file):
    daily = ox.build_daily(ox.load_germany(raw_file), START, END)
    before = daily["date"] < "2020-01-01"
    after = daily["date"] > "2020-01-10"
    inside = ~before & ~after

    assert (daily.loc[before | after, ox.FEATURE_COLUMNS] == 0).all().all()
    assert (daily.loc[inside, "oxcgrt_stringency"] == 50.0).all()
    assert (daily.loc[inside, ox.OBSERVED_COLUMN] == 1).all()
    assert (daily.loc[before | after, ox.OBSERVED_COLUMN] == 0).all()


def test_daily_join_key_is_zero_based_and_complete(raw_file):
    daily = ox.build_daily(ox.load_germany(raw_file), START, END)
    assert daily.index.equals(pd.RangeIndex(len(daily), name="index"))
    assert daily["date"].iloc[0] == pd.Timestamp(START)
    assert daily["date"].iloc[-1] == pd.Timestamp(END)
    ox.validate_daily(daily, START, END)


def test_short_gap_is_forward_filled_and_flagged(raw_file):
    de = ox.load_germany(raw_file)
    de = de[de["date"] != "2020-01-05"]  # 1-day gap
    daily = ox.build_daily(de, START, END, max_ffill_days=3)
    row = daily[daily["date"] == "2020-01-05"].iloc[0]
    assert row["oxcgrt_stringency"] == 50.0
    assert row[ox.OBSERVED_COLUMN] == 0


def test_long_gap_raises(raw_file):
    de = ox.load_germany(raw_file)
    de = de[(de["date"] < "2020-01-03") | (de["date"] > "2020-01-08")]  # 6-day gap
    with pytest.raises(ValueError, match="Gap longer"):
        ox.build_daily(de, START, END, max_ffill_days=3)


def test_validate_daily_rejects_out_of_range(raw_file):
    daily = ox.build_daily(ox.load_germany(raw_file), START, END)
    daily.loc[3, "oxcgrt_c2_workplace"] = 7
    with pytest.raises(AssertionError, match="outside"):
        ox.validate_daily(daily, START, END)


# --------------------------------------------------------------------------------------
# Calendars and hourly build
# --------------------------------------------------------------------------------------
def test_full_period_row_counts():
    assert len(ox.build_daily_calendar()) == 2192          # 2019-2024 incl. two leap years
    assert len(ox.build_hourly_calendar()) == 2192 * 24     # DST days cancel out (23 + 25)


@pytest.mark.parametrize("day, n_hours", [("2020-03-29", 23), ("2020-10-25", 25), ("2020-06-01", 24)])
def test_hourly_calendar_handles_dst(day, n_hours):
    cal = ox.build_hourly_calendar("2020-01-01", "2020-12-31")
    assert (cal["date"] == day).sum() == n_hours


def test_hourly_broadcasts_daily_values(raw_file):
    daily = ox.build_daily(ox.load_germany(raw_file), START, END)
    hourly = ox.build_hourly(daily, START, END)
    ox.validate_hourly(hourly, daily, START, END)

    assert hourly.index.equals(pd.RangeIndex(len(hourly), name="index"))
    assert hourly["datetime_from"].iloc[0] == pd.Timestamp(f"{START} 00:00", tz="Europe/Berlin")
    merged = hourly.merge(daily, on="date", suffixes=("_h", "_d"))
    for col in ox.FEATURE_COLUMNS:
        assert (merged[f"{col}_h"] == merged[f"{col}_d"]).all()


# --------------------------------------------------------------------------------------
# Output files
# --------------------------------------------------------------------------------------
def test_run_writes_csvs_with_index_join_key(tmp_path, raw_file):
    raw_dir = raw_file.parent
    out_dir = tmp_path / "intermin"
    paths = ox.run(raw_dir=raw_dir, out_dir=out_dir, start=START, end=END, download=False)

    daily = pd.read_csv(paths["daily"])
    hourly = pd.read_csv(paths["hourly"])
    assert daily.columns[0] == "index" and hourly.columns[0] == "index"
    assert daily["index"].tolist() == list(range(len(daily)))
    assert hourly["index"].tolist() == list(range(len(hourly)))
    assert daily["date"].iloc[0] == START
    assert hourly["datetime_from"].iloc[0] == f"{START}T00:00:00+01:00"
    assert paths["metadata"].exists()


def test_run_without_raw_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ox.run(raw_dir=tmp_path, out_dir=tmp_path / "out", download=False)


# --------------------------------------------------------------------------------------
# Optional: real raw file (skipped if it has not been downloaded)
# --------------------------------------------------------------------------------------
@pytest.mark.skipif(not REAL_RAW.exists(), reason="real OxCGRT raw file not downloaded")
def test_real_file_sanity():
    daily = ox.build_daily(ox.load_germany(REAL_RAW))
    ox.validate_daily(daily)
    by_year = daily.groupby(daily["date"].dt.year)["oxcgrt_stringency"].max()
    assert by_year[2019] == 0 and by_year[2023] == 0 and by_year[2024] == 0
    assert by_year[2020] > 60  # spring 2020 lockdown
    assert daily[ox.OBSERVED_COLUMN].sum() == 1096  # 2020-01-01..2022-12-31