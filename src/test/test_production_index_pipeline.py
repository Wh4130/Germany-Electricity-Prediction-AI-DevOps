"""Tests for production_index_pipeline.py (synthetic GENESIS files, no network needed)."""

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_engineering import production_index_pipeline as ipi

SEED_CALENDAR = PROJECT_ROOT / "src" / "data" / "external_raw" / ipi.RELEASE_CALENDAR_FILE

MONTHS = pd.period_range("2017-01", "2024-12", freq="M")
# Labels as shown in GENESIS-Online table 42153-0001 (checked 2026-10-21).
SERIES = [
    ("WZ08-EI", "Energieintensive Industriezweige"),
    ("WZ08-OEI", "Prod. Gew. (oh.Energie,Baugew.,energieintens.Ind.)"),  # distractor: WITHOUT them
    ("WZ08-C", "Verarbeitendes Gewerbe"),
]
VARIANTS = [
    ("ORIG", "Originalwerte", 0.3),
    ("X13KB", "X13 JDemetra+ kalenderbereinigt", 0.2),
    ("X13KSB", "X13 JDemetra+ kalender- und saisonbereinigt", 0.1),
    ("BVKSB", "BV4.1 kalender- und saisonbereinigt", 0.5),
    ("BVTREND", "BV4.1 Trend", 0.4),
]


def expected_value(i: int, step: float, series_code: str) -> float:
    base = {"WZ08-EI": 100.0, "WZ08-OEI": 150.0}.get(series_code, 200.0)
    return round(base + i * step, 1)


def _flag(i: int, n: int) -> str:
    """Last 12 months provisional ('p'), the 12 before revised ('r'), like the GENESIS view."""
    return "p" if i >= n - 12 else ("r" if i >= n - 24 else "")


def _de(x: float, flag: str = "") -> str:
    """German number format; optional quality flag as GENESIS shows it (e.g. '83,2p')."""
    return f"{x:.1f}".replace(".", ",") + flag


# --------------------------------------------------------------------------------------
# Synthetic GENESIS files
# --------------------------------------------------------------------------------------
def write_genesis_long(path: Path, variants=VARIANTS, months=MONTHS) -> Path:
    header = ("statistics_code;statistics_label;time_code;time_label;time;"
              "1_variable_code;1_variable_label;1_variable_attribute_code;1_variable_attribute_label;"
              "2_variable_code;2_variable_label;2_variable_attribute_code;2_variable_attribute_label;"
              "3_variable_code;3_variable_label;3_variable_attribute_code;3_variable_attribute_label;"
              "value;value_unit;value_variable_code;value_variable_label")
    lines = [header]
    for i, m in enumerate(months):
        for s_code, s_label in SERIES:
            for v_code, v_label, step in variants:
                lines.append(";".join([
                    "42153", "Indizes der Produktion", "JAHR", "Jahr", str(m.year),
                    "DINSG", "Deutschland insgesamt", "DG", "Deutschland",
                    "MONAT", "Monate", f"MONAT{m.month:02d}", m.strftime("%B"),
                    "WZ08X", "WZ2008", s_code, s_label,
                    _de(expected_value(i, step, s_code), _flag(i, len(months))),
                    "2021=100", f"PRO101_{v_code}", f"Produktionsindex, {v_label}",
                ]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_genesis_wide_german(path: Path, months=MONTHS) -> Path:
    """Old German layout: variant as a dimension, one value column."""
    header = ("Statistik_Code;Statistik_Label;Zeit_Code;Zeit_Label;Zeit;"
              "1_Merkmal_Code;1_Merkmal_Label;1_Auspraegung_Code;1_Auspraegung_Label;"
              "2_Merkmal_Code;2_Merkmal_Label;2_Auspraegung_Code;2_Auspraegung_Label;"
              "3_Merkmal_Code;3_Merkmal_Label;3_Auspraegung_Code;3_Auspraegung_Label;"
              "PRO101__Produktionsindex__2021=100;PRO101__Produktionsindex__q")
    lines = [header]
    for i, m in enumerate(months):
        for s_code, s_label in SERIES:
            for v_code, v_label, step in VARIANTS:
                lines.append(";".join([
                    "42153", "Indizes der Produktion", "JAHR", "Jahr", str(m.year),
                    "MONAT", "Monate", f"MONAT{m.month:02d}", "Monat",
                    "WZ08X", "WZ2008", s_code, s_label,
                    "WERTE4", "Bereinigung", v_code, v_label,
                    _de(expected_value(i, step, s_code)), "e",
                ]))
    path.write_text("\n".join(lines) + "\n", encoding="cp1252")
    return path


@pytest.fixture
def genesis_long(tmp_path) -> Path:
    return write_genesis_long(tmp_path / ipi.DEFAULT_GENESIS_FILE)


@pytest.fixture
def monthly_sa_ca(genesis_long):
    long = ipi.read_genesis_flatfile(genesis_long)
    sa = ipi.select_series(long, ipi.SERIES_INCLUDE + ipi.SA_INCLUDE, ipi.SA_EXCLUDE, ipi.VARIANT_PREFER)
    ca = ipi.select_series(long, ipi.SERIES_INCLUDE + ipi.CA_INCLUDE, ipi.CA_EXCLUDE, ipi.VARIANT_PREFER)
    return sa, ca


# --------------------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("raw, expected", [
    ("98,7", 98.7), ("1.234,5", 1234.5), ("101.3", 101.3), ("...", np.nan),
    ("-", np.nan), ("x", np.nan), (".", np.nan), ("", np.nan),
    ("83,2p", 83.2), ("79,7r", 79.7), ("100,0 e", 100.0),
])
def test_parse_number(raw, expected):
    result = ipi.parse_number(raw)
    assert (np.isnan(result) and np.isnan(expected)) or result == pytest.approx(expected)


def test_read_long_and_select_sa(monthly_sa_ca):
    sa, ca = monthly_sa_ca
    assert len(sa) == len(MONTHS)
    assert sa.index[0] == pd.Period("2017-01", "M")
    assert sa.iloc[0] == pytest.approx(100.0)
    assert sa.iloc[12] == pytest.approx(101.2)       # step 0.1 per month
    assert ca.iloc[12] == pytest.approx(102.4)       # step 0.2 per month
    assert "saisonbereinigt" in sa.attrs["label"]


def test_read_wide_german_layout_matches_long(tmp_path, monthly_sa_ca):
    wide = ipi.read_genesis_flatfile(write_genesis_wide_german(tmp_path / "wide.csv"))
    sa_wide = ipi.select_series(wide, ipi.SERIES_INCLUDE + ipi.SA_INCLUDE, ipi.SA_EXCLUDE, ipi.VARIANT_PREFER)
    pd.testing.assert_series_equal(sa_wide, monthly_sa_ca[0], check_names=False)


def test_select_without_variant_is_ambiguous(genesis_long):
    long = ipi.read_genesis_flatfile(genesis_long)
    with pytest.raises(ValueError, match="series match"):
        ipi.select_series(long, ipi.SERIES_INCLUDE)


def test_select_no_match_lists_available(genesis_long):
    long = ipi.read_genesis_flatfile(genesis_long)
    with pytest.raises(ValueError, match="Available series"):
        ipi.select_series(long, [r"does-not-exist"])


def test_prefer_x13_resolves_x13_vs_bv41(genesis_long):
    long = ipi.read_genesis_flatfile(genesis_long)
    sa = ipi.select_series(long, ipi.SERIES_INCLUDE + ipi.SA_INCLUDE, prefer=ipi.VARIANT_PREFER)
    assert "X13" in sa.attrs["label"]
    with pytest.raises(ValueError, match="series match"):
        ipi.select_series(long, ipi.SERIES_INCLUDE + ipi.SA_INCLUDE, prefer=None)


def test_distractor_aggregate_is_not_selected(monthly_sa_ca):
    sa, ca = monthly_sa_ca
    assert "Energieintensive Industriezweige" in sa.attrs["label"]
    assert "oh.Energie" not in sa.attrs["label"] and "oh.Energie" not in ca.attrs["label"]
    assert "BV4.1" not in ca.attrs["label"]


def test_flagged_recent_values_are_parsed(monthly_sa_ca):
    sa, _ = monthly_sa_ca
    n = len(MONTHS)
    assert sa.notna().all()
    assert sa.iloc[-1] == pytest.approx(expected_value(n - 1, 0.1, "WZ08-EI"))  # was '...p'
    assert sa.iloc[-13] == pytest.approx(expected_value(n - 13, 0.1, "WZ08-EI"))  # was '...r'


def test_read_simple(tmp_path):
    path = tmp_path / "simple.csv"
    pd.DataFrame({"ref_month": ["2020-01", "2020-02"], "value_sa": ["99,5", "100.5"]}).to_csv(path, index=False)
    sa, ca = ipi.read_simple(path)
    assert sa.tolist() == [99.5, 100.5] and ca is None


# --------------------------------------------------------------------------------------
# Monthly derived values
# --------------------------------------------------------------------------------------
def test_build_monthly_mom_yoy():
    idx = pd.period_range("2020-01", periods=14, freq="M")
    sa = pd.Series([100.0] * 12 + [110.0, 99.0], index=idx)
    monthly = ipi.build_monthly(sa)
    assert np.isnan(monthly["mom"].iloc[0])
    assert monthly.loc[pd.Period("2021-01", "M"), "mom"] == pytest.approx(10.0)
    assert monthly.loc[pd.Period("2021-02", "M"), "mom"] == pytest.approx(-10.0)
    assert monthly.loc[pd.Period("2021-01", "M"), "yoy"] == pytest.approx(10.0)


def test_build_monthly_missing_month_raises():
    idx = pd.PeriodIndex(["2020-01", "2020-03"], freq="M")
    with pytest.raises(ValueError, match="Missing months"):
        ipi.build_monthly(pd.Series([1.0, 2.0], index=idx))


# --------------------------------------------------------------------------------------
# Release calendar
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("ref, expected", [
    ("2022-10", "2022-12-12"),  # 10 Dec 2022 is a Saturday
    ("2023-02", "2023-04-11"),  # 10 Apr 2023 is Easter Monday
    ("2024-03", "2024-05-10"),  # regular Friday
])
def test_rule_release_date(ref, expected):
    assert ipi.rule_release_date(pd.Period(ref, "M")) == pd.Timestamp(expected)


def test_curated_dates_override_rule(tmp_path):
    path = tmp_path / "cal.csv"
    path.write_text("ref_month,release_date\n2022-11,2023-01-09\n", encoding="utf-8")
    curated = ipi.load_release_calendar(path)
    rel = ipi.assign_release_dates(pd.period_range("2022-10", "2022-12", freq="M"), curated)
    assert rel.loc[pd.Period("2022-11", "M"), "release_date"] == pd.Timestamp("2023-01-09")
    assert rel.loc[pd.Period("2022-11", "M"), "release_source"] == "curated"
    assert rel.loc[pd.Period("2022-10", "M"), "release_source"] == "rule"


def test_non_monotone_release_dates_raise(tmp_path):
    path = tmp_path / "cal.csv"
    path.write_text("ref_month,release_date\n2022-11,2023-03-20\n", encoding="utf-8")  # after Dec's rule date
    with pytest.raises(ValueError, match="strictly increasing"):
        ipi.assign_release_dates(pd.period_range("2022-10", "2022-12", freq="M"), ipi.load_release_calendar(path))


def test_release_before_month_end_raises(tmp_path):
    path = tmp_path / "cal.csv"
    path.write_text("ref_month,release_date\n2022-11,2022-11-20\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not after"):
        ipi.load_release_calendar(path)


@pytest.mark.skipif(not SEED_CALENDAR.exists(), reason="seed release calendar not present")
def test_seed_calendar_rule_is_conservative():
    cmp = ipi.compare_rule_with_curated(ipi.load_release_calendar(SEED_CALENDAR))
    assert (cmp["rule_minus_curated_days"] >= 0).all()


# --------------------------------------------------------------------------------------
# As-of alignment
# --------------------------------------------------------------------------------------
@pytest.fixture
def aligned_inputs(monthly_sa_ca, tmp_path):
    sa, ca = monthly_sa_ca
    monthly = ipi.build_monthly(sa, ca)
    path = tmp_path / "cal.csv"
    path.write_text("ref_month,release_date\n2022-11,2023-01-09\n", encoding="utf-8")
    releases = ipi.assign_release_dates(monthly.index, ipi.load_release_calendar(path))
    return monthly, releases


def test_daily_switches_on_release_day(aligned_inputs):
    monthly, releases = aligned_inputs
    daily = ipi.align_daily(monthly, releases, "2023-01-01", "2023-01-31")
    by_date = daily.set_index("date")
    assert by_date.loc["2023-01-08", "ipi_ei_ref_month"] == pd.Period("2022-10", "M")
    assert by_date.loc["2023-01-09", "ipi_ei_ref_month"] == pd.Period("2022-11", "M")
    assert by_date.loc["2023-01-09", "ipi_ei_staleness_days"] == 40  # 2023-01-09 minus 2022-11-30
    ipi.validate_daily(daily, True, "2023-01-01", "2023-01-31")


def test_daily_next_day_option(aligned_inputs):
    monthly, releases = aligned_inputs
    daily = ipi.align_daily(monthly, releases, "2023-01-01", "2023-01-31", include_release_day=False)
    by_date = daily.set_index("date")
    assert by_date.loc["2023-01-09", "ipi_ei_ref_month"] == pd.Period("2022-10", "M")
    assert by_date.loc["2023-01-10", "ipi_ei_ref_month"] == pd.Period("2022-11", "M")
    ipi.validate_daily(daily, False, "2023-01-01", "2023-01-31")


def test_daily_values_match_monthly(aligned_inputs):
    monthly, releases = aligned_inputs
    daily = ipi.align_daily(monthly, releases, "2023-01-01", "2023-01-31")
    row = daily.set_index("date").loc["2023-01-20"]
    assert row["ipi_ei_level"] == pytest.approx(monthly.loc[pd.Period("2022-11", "M"), "level"])
    assert row["ipi_ei_yoy"] == pytest.approx(monthly.loc[pd.Period("2022-11", "M"), "yoy"])


def test_hourly_switches_at_release_hour(aligned_inputs):
    monthly, releases = aligned_inputs
    hourly = ipi.align_hourly(monthly, releases, "2023-01-01", "2023-01-31")
    at = hourly.set_index("datetime_from")
    assert at.loc[pd.Timestamp("2023-01-09 07:00", tz="Europe/Berlin"), "ipi_ei_ref_month"] == pd.Period("2022-10", "M")
    assert at.loc[pd.Timestamp("2023-01-09 08:00", tz="Europe/Berlin"), "ipi_ei_ref_month"] == pd.Period("2022-11", "M")
    ipi.validate_hourly(hourly, ipi.RELEASE_HOUR, "2023-01-01", "2023-01-31")


def test_missing_early_months_raise(monthly_sa_ca):
    sa, _ = monthly_sa_ca
    late = sa[sa.index >= pd.Period("2019-06", "M")]
    monthly = ipi.build_monthly(late)
    releases = ipi.assign_release_dates(monthly.index, None)
    with pytest.raises(ValueError, match="download earlier months"):
        ipi.align_daily(monthly, releases, "2019-01-01", "2019-12-31")


def test_validate_detects_leakage(aligned_inputs):
    monthly, releases = aligned_inputs
    daily = ipi.align_daily(monthly, releases, "2023-01-01", "2023-01-31")
    daily.loc[0, "ipi_ei_release_date"] = pd.Timestamp("2023-02-01")
    with pytest.raises(AssertionError, match="released after"):
        ipi.validate_daily(daily, True, "2023-01-01", "2023-01-31")


def test_calendars_match_oxcgrt_pipeline():
    from src.feature_engineering import oxcgrt_pipeline as ox
    pd.testing.assert_frame_equal(ipi.build_daily_calendar(), ox.build_daily_calendar())
    pd.testing.assert_frame_equal(ipi.build_hourly_calendar(), ox.build_hourly_calendar())


# --------------------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------------------
def test_run_genesis_full_period(tmp_path, genesis_long):
    raw_dir = genesis_long.parent
    (raw_dir / ipi.RELEASE_CALENDAR_FILE).write_text("ref_month,release_date\n2022-11,2023-01-09\n", encoding="utf-8")
    paths = ipi.run(raw_dir=raw_dir, out_dir=tmp_path / "intermin")

    daily = pd.read_csv(paths["daily"])
    hourly = pd.read_csv(paths["hourly"])
    assert len(daily) == 2192 and len(hourly) == 2192 * 24
    assert daily.columns[0] == "index" and hourly.columns[0] == "index"
    assert daily["index"].tolist() == list(range(len(daily)))
    assert hourly["index"].tolist() == list(range(len(hourly)))
    assert daily[ipi.FEATURE_COLUMNS].notna().all().all()
    assert daily["date"].iloc[0] == "2019-01-01"
    assert (pd.to_datetime(daily["ipi_ei_release_date"]) <= pd.to_datetime(daily["date"])).all()
    assert paths["monthly"].exists() and paths["metadata"].exists()


def test_run_simple_format(tmp_path, monthly_sa_ca):
    sa, _ = monthly_sa_ca
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    pd.DataFrame({"ref_month": sa.index.astype(str), "value_sa": sa.values}).to_csv(
        raw_dir / ipi.DEFAULT_SIMPLE_FILE, index=False)
    paths = ipi.run(raw_dir=raw_dir, out_dir=tmp_path / "out", input_format="simple",
                    start="2022-01-01", end="2022-12-31")
    daily = pd.read_csv(paths["daily"])
    assert len(daily) == 365 and daily["index"].iloc[0] == 0


def test_run_missing_input_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="Flat File CSV"):
        ipi.run(raw_dir=tmp_path, out_dir=tmp_path / "out")


# --------------------------------------------------------------------------------------
# --alignment reference_month (ablation)
# --------------------------------------------------------------------------------------
def test_reference_month_daily_uses_own_month(aligned_inputs):
    monthly, releases = aligned_inputs
    daily = ipi.align_daily_reference_month(monthly, releases, "2022-11-01", "2022-12-31")
    row = daily.set_index("date").loc["2022-11-15"]
    assert row["ipi_ei_ref_month"] == pd.Period("2022-11", "M")
    assert row["ipi_ei_level"] == pytest.approx(monthly.loc[pd.Period("2022-11", "M"), "level"])
    assert row["ipi_ei_staleness_days"] == -15  # 15 Nov minus 30 Nov
    assert row["ipi_ei_release_date"] == pd.Timestamp("2023-01-09")  # still recorded for audit
    ipi.validate_daily(daily, start="2022-11-01", end="2022-12-31", alignment="reference_month")


def test_reference_month_differs_from_release(aligned_inputs):
    monthly, releases = aligned_inputs
    ref = ipi.align_daily_reference_month(monthly, releases, "2022-11-01", "2022-11-30")
    rel = ipi.align_daily(monthly, releases, "2022-11-01", "2022-11-30")
    assert (ref["ipi_ei_ref_month"] == pd.Period("2022-11", "M")).all()
    assert (rel["ipi_ei_ref_month"] <= pd.Period("2022-09", "M")).all()


def test_reference_month_hourly_switches_at_month_boundary(aligned_inputs):
    monthly, releases = aligned_inputs
    hourly = ipi.align_hourly_reference_month(monthly, releases, "2022-11-01", "2022-12-31")
    at = hourly.set_index("datetime_from")
    assert at.loc[pd.Timestamp("2022-11-30 23:00", tz="Europe/Berlin"), "ipi_ei_ref_month"] == pd.Period("2022-11", "M")
    assert at.loc[pd.Timestamp("2022-12-01 00:00", tz="Europe/Berlin"), "ipi_ei_ref_month"] == pd.Period("2022-12", "M")
    ipi.validate_hourly(hourly, start="2022-11-01", end="2022-12-31", alignment="reference_month")


def test_reference_month_needs_data_to_period_end(monthly_sa_ca):
    sa, _ = monthly_sa_ca
    monthly = ipi.build_monthly(sa[sa.index <= pd.Period("2024-06", "M")])
    releases = ipi.assign_release_dates(monthly.index, None)
    with pytest.raises(ValueError, match="does not cover"):
        ipi.align_daily_reference_month(monthly, releases, "2024-01-01", "2024-12-31")


def test_reference_month_validation_detects_wrong_month(aligned_inputs):
    monthly, releases = aligned_inputs
    daily = ipi.align_daily_reference_month(monthly, releases, "2022-11-01", "2022-11-30")
    daily.loc[0, "ipi_ei_ref_month"] = pd.Period("2022-10", "M")
    with pytest.raises(AssertionError, match="own calendar month"):
        ipi.validate_daily(daily, start="2022-11-01", end="2022-11-30", alignment="reference_month")


def test_run_both_alignments_write_separate_files(tmp_path, genesis_long):
    raw_dir, out_dir = genesis_long.parent, tmp_path / "intermin"
    main_paths = ipi.run(raw_dir=raw_dir, out_dir=out_dir)
    ref_paths = ipi.run(raw_dir=raw_dir, out_dir=out_dir, alignment="reference_month")

    assert main_paths["daily"].name == "ipi_energy_intensive_daily.csv"
    assert ref_paths["daily"].name == "ipi_energy_intensive_refmonth_daily.csv"
    assert ref_paths["hourly"].name == "ipi_energy_intensive_refmonth_hourly.csv"
    for p in [*main_paths.values(), *ref_paths.values()]:
        assert p.exists()

    main_daily, ref_daily = pd.read_csv(main_paths["daily"]), pd.read_csv(ref_paths["daily"])
    assert main_daily["index"].equals(ref_daily["index"])  # same join key
    assert (ref_daily["ipi_ei_ref_month"] == ref_daily["date"].str.slice(0, 7)).all()
    meta = json.loads(ref_paths["metadata"].read_text())
    assert meta["alignment"] == "reference_month" and "LEAKY" in meta["alignment_note"]


def test_invalid_alignment_raises(tmp_path, genesis_long):
    with pytest.raises(ValueError, match="alignment must be one of"):
        ipi.run(raw_dir=genesis_long.parent, out_dir=tmp_path / "o", alignment="oracle")


def test_cli_alignment_flag(tmp_path, genesis_long):
    out_dir = tmp_path / "cli_out"
    ipi.main(["--raw-dir", str(genesis_long.parent), "--out-dir", str(out_dir),
              "--alignment", "reference_month", "--start", "2023-01-01", "--end", "2023-03-31"])
    assert (out_dir / "ipi_energy_intensive_refmonth_daily.csv").exists()
    assert not (out_dir / "ipi_energy_intensive_daily.csv").exists()