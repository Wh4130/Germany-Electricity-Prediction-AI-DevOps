"""Production index pipeline: energy-intensive industry output, aligned to its release dates.

Source
    Destatis GENESIS-Online, table 42153-0001 "Indizes der Produktion",
    series "Produktionsindex energieintensive Industriezweige" (2021 = 100, from 2005).
    Licence: Datenlizenz Deutschland - Namensnennung - Version 2.0 (DL-DE BY 2.0).

    Download it manually from GENESIS-Online as "Flat File CSV" (all months from 2015 on)
    and save it as ``src/data/external_raw/42153-0001_flat.csv``. The parser accepts both
    the German (Zeit / Auspraegung) and English (time / variable_attribute) header styles,
    long or wide value layout. Alternatively provide a simple CSV (see ``read_simple``).

Release calendar
    ``src/data/external_raw/ipi_release_calendar.csv`` with columns
    ``ref_month`` (YYYY-MM), ``release_date`` (YYYY-MM-DD), ``source_url``.
    Curated dates from the Destatis press releases "Produktion im <Monat>" take priority.
    Months without a curated date get the fallback rule: day ``RULE_DAY`` of month t+2,
    moved to the next working day in Hesse (Destatis sits in Wiesbaden).

Release alignment ("as known on day d")
    daily : value of the latest reference month whose release_date <= d
            (``include_release_day=False`` makes it available only from d+1)
    hourly: value of the latest reference month released at or before the hour, with the
            release at ``RELEASE_HOUR``:00 Europe/Berlin
    The value itself is the latest revised figure from GENESIS ("pseudo-real-time"):
    publication timing is respected, revisions are not.

Reference-month alignment (``--alignment reference_month``, ABLATION ONLY)
    Every day/hour of month m gets month m's value, ~5-6 weeks before it was published.
    This leaks information a real forecast could not have; use it only as an oracle
    upper bound to measure how much the release lag costs. Written to separate files
    (``ipi_energy_intensive_refmonth_*``) so it cannot be mixed up with the main variant.

Outputs (in ``src/data/intermin``), <stem> = ipi_energy_intensive | ipi_energy_intensive_refmonth
    <stem>_daily.csv    column ``index`` = 0..N-1 (join key)
    <stem>_hourly.csv   column ``index`` = 0..N-1 (join key)
    <stem>_monthly.csv  monthly audit table (no join key)
    <stem>_metadata.json

    Same calendars and join-key convention as oxcgrt_pipeline.py.

Usage (from the project root)
    python src/pipelines/production_index_pipeline.py
    python src/pipelines/production_index_pipeline.py --alignment reference_month
    python src/pipelines/production_index_pipeline.py --input-format simple
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import holidays
import numpy as np
import pandas as pd

logger = logging.getLogger("production_index_pipeline")

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------
GENESIS_TABLE = "42153-0001"
DEFAULT_GENESIS_FILE = "42153-0001_flat.csv"
DEFAULT_SIMPLE_FILE = "ipi_monthly_simple.csv"
RELEASE_CALENDAR_FILE = "ipi_release_calendar.csv"

DEFAULT_RAW_DIR = Path("src/data/external_raw")
DEFAULT_OUT_DIR = Path("src/data/features/policy")
OUTPUT_STEM = "ipi_energy_intensive"

# "release": as known on day d (main variant). "reference_month": month m's value on the days of
# month m itself - uses figures before they were published, so ABLATION / oracle upper bound only.
ALIGNMENTS = ("release", "reference_month")
DEFAULT_ALIGNMENT = "release"
OUTPUT_STEMS = {"release": OUTPUT_STEM, "reference_month": f"{OUTPUT_STEM}_refmonth"}

START_DATE = "2019-01-01"
END_DATE = "2024-12-31"
TIMEZONE = "Europe/Berlin"
JOIN_KEY = "index"
PREFIX = "ipi_ei"

# Series selection on the concatenated GENESIS labels (case-insensitive regexes).
# Every "include" must match, no "exclude" may match; "prefer" breaks ties.
# Exact aggregate label in 42153-0001 is "Energieintensive Industriezweige". Anchoring on the
# full phrase keeps out "Prod. Gew. (oh.Energie,Baugew.,energieintens.Ind.)" (= WITHOUT them).
SERIES_INCLUDE = [r"energieintensive industriezweige|energy.intensive industr"]
SA_INCLUDE = [r"saison|season"]                       # calendar + seasonally adjusted
SA_EXCLUDE: list[str] = []
CA_INCLUDE = [r"kalenderbereinigt|calendar.adjusted"]  # calendar adjusted only
CA_EXCLUDE = [r"saison|season"]
VARIANT_PREFER = [r"x13"]

RULE_DAY = 10            # fallback release: day 10 of month t+2, next working day
HOLIDAY_SUBDIV = "HE"    # Hesse
RELEASE_HOUR = 8         # Destatis press releases go out at 08:00 local time
INCLUDE_RELEASE_DAY = True

MISSING_MARKERS = {"", "-", "–", "—", "...", "…", ".", "x", "/", "nan", "none"}

FEATURE_COLUMNS = [f"{PREFIX}_level", f"{PREFIX}_mom", f"{PREFIX}_yoy", f"{PREFIX}_staleness_days"]
AUDIT_COLUMNS = [f"{PREFIX}_ref_month", f"{PREFIX}_release_date", f"{PREFIX}_release_source"]


# --------------------------------------------------------------------------------------
# Calendars (identical convention to oxcgrt_pipeline.py)
# --------------------------------------------------------------------------------------
def build_daily_calendar(start: str = START_DATE, end: str = END_DATE) -> pd.DataFrame:
    dates = pd.date_range(start=start, end=end, freq="D")
    cal = pd.DataFrame({"date": dates})
    cal.index = pd.RangeIndex(len(cal), name=JOIN_KEY)
    return cal


def build_hourly_calendar(start: str = START_DATE, end: str = END_DATE) -> pd.DataFrame:
    first = pd.Timestamp(f"{start} 00:00", tz=TIMEZONE)
    last = pd.Timestamp(f"{end} 23:00", tz=TIMEZONE)
    stamps = pd.date_range(start=first, end=last, freq="h")
    cal = pd.DataFrame({"datetime_from": stamps})
    cal["date"] = cal["datetime_from"].dt.tz_localize(None).dt.normalize()
    cal.index = pd.RangeIndex(len(cal), name=JOIN_KEY)
    return cal


# --------------------------------------------------------------------------------------
# Reading the monthly series
# --------------------------------------------------------------------------------------
_FLAGGED_NUMBER = re.compile(r"^([+-]?[\d.,]+)\s*[A-Za-z]{1,2}$")


def parse_number(raw: object) -> float:
    """Parse a GENESIS value: decimal comma or point, special markers -> NaN.

    Trailing quality flags ("83,2p" provisional, "79,7r" revised, "e", "s", ...) are dropped.
    """
    s = str(raw).strip()
    if s.lower() in MISSING_MARKERS:
        return np.nan
    flagged = _FLAGGED_NUMBER.match(s)
    if flagged:
        s = flagged.group(1)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        logger.warning("Unparseable value %r -> NaN", raw)
        return np.nan


def _read_text(path: Path) -> str:
    data = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def read_genesis_flatfile(path: Path) -> pd.DataFrame:
    """Read a GENESIS "Flat File CSV" into a long table: ``ref_month``, ``text``, ``value``.

    ``text`` joins every attribute label of the row except the month (plus the value
    variable label), so one distinct ``text`` identifies one monthly series.
    """
    text = _read_text(path)
    lines = text.splitlines()
    header_row = next(
        (i for i, line in enumerate(lines[:30]) if re.search(r"statistics_code|statistik_code", line, re.I)), 0
    )
    df = pd.read_csv(io.StringIO(text), sep=";", dtype=str, keep_default_na=False, skiprows=header_row)
    df.columns = [c.strip() for c in df.columns]
    lower = {c.lower(): c for c in df.columns}

    time_col = lower.get("time") or lower.get("zeit")
    if time_col is None:
        raise KeyError(f"No time/Zeit column found. Columns: {list(df.columns)[:15]}")

    pair_re = re.compile(r"^(\d+)_(?:variable_attribute|auspraegung)_(code|label)$", re.I)
    pairs: dict[str, dict[str, str]] = {}
    for c in df.columns:
        m = pair_re.match(c)
        if m:
            pairs.setdefault(m.group(1), {})[m.group(2).lower()] = c

    # month dimension: the attribute code column holding MONAT01..MONAT12
    month_key = None
    for k, cols in pairs.items():
        if "code" in cols and df[cols["code"]].str.match(r"^MONAT\d{2}$", case=False).mean() > 0.5:
            month_key = k
            break

    if month_key is not None:
        month = df[pairs[month_key]["code"]].str.extract(r"(\d{2})$")[0]
        year = df[time_col].str.extract(r"(\d{4})")[0]
        ref = year + "-" + month
    elif df[time_col].str.match(r"^\d{4}-\d{2}").all():
        ref = df[time_col].str.slice(0, 7)
    else:
        raise ValueError("No month dimension (MONATxx) found - is this the monthly table 42153-0001?")

    label_cols = [cols["label"] for k, cols in sorted(pairs.items(), key=lambda kv: int(kv[0]))
                  if k != month_key and "label" in cols]

    if "value" in lower:  # long layout
        long = pd.DataFrame({
            "ref": ref,
            "labels": df[label_cols].agg(" | ".join, axis=1) if label_cols else "",
            "value_label": df[lower["value_variable_label"]] if "value_variable_label" in lower else "",
            "value_raw": df[lower["value"]],
        })
    else:  # wide layout: one column per value variable
        meta_re = re.compile(r"^(statistics_|statistik_|time|zeit|\d+_)", re.I)
        value_cols = [c for c in df.columns if not meta_re.match(c) and not re.search(r"_q$", c, re.I)]
        if not value_cols:
            raise ValueError("No value columns found in GENESIS file.")
        base = pd.DataFrame({
            "ref": ref,
            "labels": df[label_cols].agg(" | ".join, axis=1) if label_cols else "",
        })
        long = pd.concat(
            [base.assign(value_label=c, value_raw=df[c].values) for c in value_cols], ignore_index=True
        )

    long = long.dropna(subset=["ref"])
    out = pd.DataFrame({
        "ref_month": pd.PeriodIndex(long["ref"], freq="M"),
        "text": (long["labels"].astype(str) + " | " + long["value_label"].astype(str)).str.strip(" |"),
        "value": long["value_raw"].map(parse_number),
    })
    logger.info("GENESIS file: %d rows, %d distinct series, %s to %s",
                len(out), out["text"].nunique(), out["ref_month"].min(), out["ref_month"].max())
    return out


def select_series(long: pd.DataFrame, include: list[str], exclude: list[str] | None = None,
                  prefer: list[str] | None = None, name: str = "series") -> pd.Series:
    """Pick exactly one monthly series by label patterns; raise with diagnostics otherwise."""
    t = long["text"].str.lower()
    mask = pd.Series(True, index=long.index)
    for p in include:
        mask &= t.str.contains(p, regex=True)
    for p in exclude or []:
        mask &= ~t.str.contains(p, regex=True)

    distinct = list(dict.fromkeys(long.loc[mask, "text"]))
    if not distinct:
        sample = "\n  ".join(list(dict.fromkeys(long["text"]))[:25])
        raise ValueError(f"No {name} matched include={include} exclude={exclude}. Available series:\n  {sample}")
    if len(distinct) > 1 and prefer:
        narrowed = [d for d in distinct if all(re.search(p, d, re.I) for p in prefer)]
        if len(narrowed) == 1:
            distinct = narrowed
    if len(distinct) > 1:
        listing = "\n  ".join(distinct[:25])
        raise ValueError(f"{name}: {len(distinct)} series match, refine the patterns:\n  {listing}")

    chosen = long[long["text"] == distinct[0]]
    if chosen["ref_month"].duplicated().any():
        raise ValueError(f"{name}: duplicate months for series {distinct[0]!r}")
    logger.info("%s -> %s", name, distinct[0])
    s = chosen.set_index("ref_month")["value"].sort_index()
    s.attrs["label"] = distinct[0]
    return s


def read_simple(path: Path) -> tuple[pd.Series, pd.Series | None]:
    """Simple input: columns ``ref_month`` (YYYY-MM), ``value_sa``, optional ``value_ca``."""
    df = pd.read_csv(path, dtype=str)
    if not {"ref_month", "value_sa"} <= set(df.columns):
        raise KeyError("Simple file needs columns ref_month, value_sa (optional value_ca)")
    idx = pd.PeriodIndex(df["ref_month"].str.slice(0, 7), freq="M")
    sa = pd.Series(df["value_sa"].map(parse_number).values, index=idx).sort_index()
    ca = None
    if "value_ca" in df.columns:
        ca = pd.Series(df["value_ca"].map(parse_number).values, index=idx).sort_index()
    if sa.index.duplicated().any():
        raise ValueError("Simple file: duplicate ref_month values")
    return sa, ca


def build_monthly(sa: pd.Series, ca: pd.Series | None = None) -> pd.DataFrame:
    """Monthly table with level, month-on-month and year-on-year change (in %)."""
    sa = sa.dropna()
    full = pd.period_range(sa.index.min(), sa.index.max(), freq="M")
    missing = full.difference(sa.index)
    if len(missing):
        raise ValueError(f"Missing months inside the series: {[str(m) for m in missing[:10]]}")

    monthly = pd.DataFrame(index=pd.PeriodIndex(full, name="ref_month"))
    monthly["level"] = sa.reindex(full).values
    yoy_base = monthly["level"]
    if ca is not None:
        monthly["level_ca"] = ca.reindex(full).values
        yoy_base = monthly["level_ca"]
    monthly["mom"] = monthly["level"].pct_change(fill_method=None) * 100
    monthly["yoy"] = (yoy_base / yoy_base.shift(12) - 1) * 100
    monthly[["mom", "yoy"]] = monthly[["mom", "yoy"]].round(4)
    return monthly


# --------------------------------------------------------------------------------------
# Release calendar
# --------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _holidays(year: int, subdiv: str) -> holidays.HolidayBase:
    return holidays.Germany(years=year, subdiv=subdiv)


def rule_release_date(ref_month: pd.Period, day: int = RULE_DAY, subdiv: str = HOLIDAY_SUBDIV) -> pd.Timestamp:
    """Fallback rule: ``day`` of month t+2, rolled forward to the next working day."""
    d = (ref_month + 2).start_time.normalize() + pd.Timedelta(days=day - 1)
    while d.weekday() >= 5 or d.date() in _holidays(d.year, subdiv):
        d += pd.Timedelta(days=1)
    return d


def load_release_calendar(path: Path) -> pd.DataFrame:
    cal = pd.read_csv(path, dtype=str, comment="#")
    if not {"ref_month", "release_date"} <= set(cal.columns):
        raise KeyError("Release calendar needs columns ref_month, release_date")
    cal = cal.dropna(subset=["ref_month", "release_date"])
    out = pd.DataFrame({
        "ref_month": pd.PeriodIndex(cal["ref_month"].str.strip(), freq="M"),
        "release_date": pd.to_datetime(cal["release_date"].str.strip(), format="%Y-%m-%d"),
    })
    if out["ref_month"].duplicated().any():
        raise ValueError("Release calendar has duplicate ref_month entries")
    too_early = out["release_date"] <= out["ref_month"].dt.end_time.dt.normalize()
    if too_early.any():
        raise ValueError(f"Release date not after its reference month: {out[too_early].to_dict('records')}")
    return out.set_index("ref_month").sort_index()


def assign_release_dates(months: pd.PeriodIndex, curated: pd.DataFrame | None,
                         rule_day: int = RULE_DAY) -> pd.DataFrame:
    """Curated date where available, rule otherwise. Release dates must strictly increase."""
    rel = pd.DataFrame(index=pd.PeriodIndex(months, name="ref_month"))
    rel["release_date"] = [rule_release_date(m, rule_day) for m in rel.index]
    rel["release_source"] = "rule"
    if curated is not None and len(curated):
        hit = rel.index.intersection(curated.index)
        rel.loc[hit, "release_date"] = curated.loc[hit, "release_date"].values
        rel.loc[hit, "release_source"] = "curated"
    rel["release_date"] = pd.to_datetime(rel["release_date"])
    if not rel["release_date"].is_monotonic_increasing or rel["release_date"].duplicated().any():
        raise ValueError("Release dates are not strictly increasing across reference months")
    return rel


def compare_rule_with_curated(curated: pd.DataFrame, rule_day: int = RULE_DAY) -> pd.DataFrame:
    """Days between rule and curated date (>= 0 means the rule is conservative)."""
    cmp = curated.copy()
    cmp["rule_date"] = [rule_release_date(m, rule_day) for m in cmp.index]
    cmp["rule_minus_curated_days"] = (cmp["rule_date"] - cmp["release_date"]).dt.days
    leaky = cmp[cmp["rule_minus_curated_days"] < 0]
    if len(leaky):
        logger.warning("Fallback rule is EARLIER than the real release for %d curated month(s): %s. "
                       "Raise RULE_DAY or curate those months.", len(leaky), [str(m) for m in leaky.index])
    return cmp


# --------------------------------------------------------------------------------------
# As-of alignment
# --------------------------------------------------------------------------------------
def _monthly_for_merge(monthly: pd.DataFrame, releases: pd.DataFrame) -> pd.DataFrame:
    m = monthly.join(releases, how="inner").reset_index()
    return m.rename(columns={
        "level": f"{PREFIX}_level", "mom": f"{PREFIX}_mom", "yoy": f"{PREFIX}_yoy",
        "ref_month": f"{PREFIX}_ref_month", "release_date": f"{PREFIX}_release_date",
        "release_source": f"{PREFIX}_release_source",
    })


def _finish(aligned: pd.DataFrame, cal: pd.DataFrame, extra: list[str],
            missing_hint: str = "download earlier months") -> pd.DataFrame:
    ref = aligned[f"{PREFIX}_ref_month"]
    if ref.isna().any():
        first_bad = aligned.loc[ref.isna(), "date"].min()
        raise ValueError(f"No monthly value available on {first_bad.date()}; {missing_hint}.")
    ref_end = ref.dt.end_time.dt.normalize()
    aligned[f"{PREFIX}_staleness_days"] = (aligned["date"] - ref_end).dt.days.astype("int64")
    aligned.index = cal.index
    return aligned[[*extra, *FEATURE_COLUMNS, *AUDIT_COLUMNS]]


def align_daily(monthly: pd.DataFrame, releases: pd.DataFrame, start: str = START_DATE,
                end: str = END_DATE, include_release_day: bool = INCLUDE_RELEASE_DAY) -> pd.DataFrame:
    cal = build_daily_calendar(start, end)
    m = _monthly_for_merge(monthly, releases)
    m["available_from"] = m[f"{PREFIX}_release_date"] + pd.Timedelta(days=0 if include_release_day else 1)
    aligned = pd.merge_asof(cal.reset_index(), m.sort_values("available_from"),
                            left_on="date", right_on="available_from", direction="backward")
    out = _finish(aligned, cal, ["date"])
    out.attrs["available_from_offset_days"] = 0 if include_release_day else 1
    return out


def align_hourly(monthly: pd.DataFrame, releases: pd.DataFrame, start: str = START_DATE,
                 end: str = END_DATE, release_hour: int = RELEASE_HOUR) -> pd.DataFrame:
    cal = build_hourly_calendar(start, end)
    m = _monthly_for_merge(monthly, releases)
    m["available_from"] = (m[f"{PREFIX}_release_date"] + pd.Timedelta(hours=release_hour)).dt.tz_localize(TIMEZONE)
    aligned = pd.merge_asof(cal.reset_index(), m.sort_values("available_from"),
                            left_on="datetime_from", right_on="available_from", direction="backward")
    return _finish(aligned, cal, ["datetime_from", "date"])


# --------------------------------------------------------------------------------------
# Reference-month alignment (ABLATION ONLY - leaks unpublished information)
# --------------------------------------------------------------------------------------
def _align_reference_month(monthly: pd.DataFrame, releases: pd.DataFrame, cal: pd.DataFrame,
                           extra: list[str]) -> pd.DataFrame:
    """Every day/hour of month m gets month m's value, regardless of when it was published.

    ``ipi_ei_release_date`` still holds the (rule/curated) publication date, so the size of
    the look-ahead is visible; ``ipi_ei_staleness_days`` is <= 0 (days to the month end).
    """
    m = _monthly_for_merge(monthly, releases)
    left = cal.reset_index()
    left["_ref_key"] = left["date"].dt.to_period("M")
    aligned = left.merge(m, left_on="_ref_key", right_on=f"{PREFIX}_ref_month", how="left")
    return _finish(aligned, cal, extra, missing_hint="the monthly data does not cover this month")


def align_daily_reference_month(monthly: pd.DataFrame, releases: pd.DataFrame,
                                start: str = START_DATE, end: str = END_DATE) -> pd.DataFrame:
    return _align_reference_month(monthly, releases, build_daily_calendar(start, end), ["date"])


def align_hourly_reference_month(monthly: pd.DataFrame, releases: pd.DataFrame,
                                 start: str = START_DATE, end: str = END_DATE) -> pd.DataFrame:
    return _align_reference_month(monthly, releases, build_hourly_calendar(start, end),
                                  ["datetime_from", "date"])


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------
def _check_join_key(df: pd.DataFrame, name: str) -> None:
    if not df.index.equals(pd.RangeIndex(len(df), name=JOIN_KEY)):
        raise AssertionError(f"{name}: index is not a 0-based consecutive join key")


def _check_reference_month(df: pd.DataFrame, name: str) -> None:
    mismatch = df[f"{PREFIX}_ref_month"] != df["date"].dt.to_period("M")
    if mismatch.any():
        raise AssertionError(f"{name}: {int(mismatch.sum())} rows not mapped to their own calendar month")


def validate_daily(daily: pd.DataFrame, include_release_day: bool = INCLUDE_RELEASE_DAY,
                   start: str = START_DATE, end: str = END_DATE, alignment: str = "release") -> None:
    _check_join_key(daily, "daily")
    if not pd.DatetimeIndex(daily["date"]).equals(pd.date_range(start, end, freq="D")):
        raise AssertionError("daily: dates are not the complete consecutive calendar")
    if daily[FEATURE_COLUMNS].isna().any().any():
        raise AssertionError("daily: NaN in feature columns")
    if alignment == "reference_month":
        _check_reference_month(daily, "daily")
        return
    rel = daily[f"{PREFIX}_release_date"]
    leak = rel > daily["date"] if include_release_day else rel >= daily["date"]
    if leak.any():
        raise AssertionError(f"daily: {int(leak.sum())} rows use a month released after that day")


def validate_hourly(hourly: pd.DataFrame, release_hour: int = RELEASE_HOUR,
                    start: str = START_DATE, end: str = END_DATE, alignment: str = "release") -> None:
    _check_join_key(hourly, "hourly")
    expected = build_hourly_calendar(start, end)["datetime_from"].reset_index(drop=True)
    if not hourly["datetime_from"].reset_index(drop=True).equals(expected):
        raise AssertionError("hourly: timestamps differ from the reference hourly calendar")
    if hourly[FEATURE_COLUMNS].isna().any().any():
        raise AssertionError("hourly: NaN in feature columns")
    if alignment == "reference_month":
        _check_reference_month(hourly, "hourly")
        return
    avail = (hourly[f"{PREFIX}_release_date"] + pd.Timedelta(hours=release_hour)).dt.tz_localize(TIMEZONE)
    leak = avail > hourly["datetime_from"]
    if leak.any():
        raise AssertionError(f"hourly: {int(leak.sum())} rows use a month released after that hour")


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------
def _format_for_csv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    if "datetime_from" in out.columns:
        out["datetime_from"] = out["datetime_from"].map(lambda t: t.isoformat())
    out[f"{PREFIX}_ref_month"] = out[f"{PREFIX}_ref_month"].astype(str)
    out[f"{PREFIX}_release_date"] = out[f"{PREFIX}_release_date"].dt.strftime("%Y-%m-%d")
    return out


def write_outputs(daily: pd.DataFrame, hourly: pd.DataFrame, monthly: pd.DataFrame,
                  releases: pd.DataFrame, out_dir: Path, metadata: dict | None = None,
                  alignment: str = "release") -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = OUTPUT_STEMS[alignment]
    paths = {
        "daily": out_dir / f"{stem}_daily.csv",
        "hourly": out_dir / f"{stem}_hourly.csv",
        # "monthly": out_dir / f"{stem}_monthly.csv",
        "metadata": out_dir / f"{stem}_metadata.json",
    }
    _format_for_csv(daily).to_csv(paths["daily"], index=True, index_label=JOIN_KEY)
    _format_for_csv(hourly).to_csv(paths["hourly"], index=True, index_label=JOIN_KEY)

    audit = monthly.join(releases, how="left").reset_index()
    audit["ref_month"] = audit["ref_month"].astype(str)
    audit["release_date"] = audit["release_date"].dt.strftime("%Y-%m-%d")
    # audit.to_csv(paths["monthly"], index=False)

    paths["metadata"].write_text(json.dumps(metadata or {}, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote %s (%d rows) and %s (%d rows)", paths["daily"], len(daily), paths["hourly"], len(hourly))
    return paths


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_monthly_input(raw_dir: Path, input_format: str, genesis_file: str,
                       simple_file: str) -> tuple[pd.DataFrame, dict]:
    if input_format == "genesis":
        path = Path(raw_dir) / genesis_file
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Download table {GENESIS_TABLE} from GENESIS-Online as 'Flat File CSV'.")
        long = read_genesis_flatfile(path)
        sa = select_series(long, SERIES_INCLUDE + SA_INCLUDE, SA_EXCLUDE, VARIANT_PREFER, "seasonally adjusted")
        try:
            ca = select_series(long, SERIES_INCLUDE + CA_INCLUDE, CA_EXCLUDE, VARIANT_PREFER, "calendar adjusted")
        except ValueError as exc:
            logger.warning("Calendar-adjusted series not found, yoy uses the SA series: %s", str(exc)[:200])
            ca = None
        info = {"input_file": str(path), "sha256": _sha256(path),
                "series_sa": sa.attrs.get("label"), "series_ca": ca.attrs.get("label") if ca is not None else None}
    elif input_format == "simple":
        path = Path(raw_dir) / simple_file
        if not path.exists():
            raise FileNotFoundError(f"{path} not found.")
        sa, ca = read_simple(path)
        info = {"input_file": str(path), "sha256": _sha256(path)}
    else:
        raise ValueError(f"Unknown input_format {input_format!r}")
    return build_monthly(sa, ca), info


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    out_dir: Path = DEFAULT_OUT_DIR,
    start: str = START_DATE,
    end: str = END_DATE,
    input_format: str = "genesis",
    genesis_file: str = DEFAULT_GENESIS_FILE,
    simple_file: str = DEFAULT_SIMPLE_FILE,
    calendar_file: str = RELEASE_CALENDAR_FILE,
    rule_day: int = RULE_DAY,
    include_release_day: bool = INCLUDE_RELEASE_DAY,
    release_hour: int = RELEASE_HOUR,
    alignment: str = DEFAULT_ALIGNMENT,
) -> dict[str, Path]:
    if alignment not in ALIGNMENTS:
        raise ValueError(f"alignment must be one of {ALIGNMENTS}, got {alignment!r}")
    raw_dir = Path(raw_dir)
    monthly, input_info = load_monthly_input(raw_dir, input_format, genesis_file, simple_file)

    cal_path = raw_dir / calendar_file
    curated = load_release_calendar(cal_path) if cal_path.exists() else None
    if curated is None:
        logger.warning("No release calendar at %s; using the fallback rule for every month.", cal_path)
    else:
        compare_rule_with_curated(curated, rule_day)
    releases = assign_release_dates(monthly.index, curated, rule_day)

    if alignment == "release":
        daily = align_daily(monthly, releases, start, end, include_release_day)
        hourly = align_hourly(monthly, releases, start, end, release_hour)
        alignment_note = "Release-aligned: each value is used only from its (rule/curated) release date."
    else:
        logger.warning("alignment=reference_month: values are used BEFORE they were published "
                       "(look-ahead). Use these files for ablation only, never for reported results.")
        daily = align_daily_reference_month(monthly, releases, start, end)
        hourly = align_hourly_reference_month(monthly, releases, start, end)
        alignment_note = ("LEAKY ABLATION: month m's value is placed on the days of month m, about "
                          "5-6 weeks before Destatis published it. Oracle upper bound only.")
    validate_daily(daily, include_release_day, start, end, alignment)
    validate_hourly(hourly, release_hour, start, end, alignment)

    metadata = {
        "pipeline": "production_index_pipeline",
        "alignment": alignment,
        "alignment_note": alignment_note,
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": f"Destatis GENESIS-Online {GENESIS_TABLE}, energy-intensive industrial branches, 2021=100",
        "licence": "DL-DE BY 2.0",
        "input": input_info,
        "calendar": {"start": start, "end": end, "timezone": TIMEZONE, "join_key": JOIN_KEY},
        "release_rule": {"day_of_month_t_plus_2": rule_day, "holiday_subdiv": HOLIDAY_SUBDIV,
                         "release_hour_local": release_hour, "include_release_day_daily": include_release_day},
        "release_sources": releases["release_source"].value_counts().to_dict(),
        "monthly_range": [str(monthly.index.min()), str(monthly.index.max())],
        "assumptions": [
            "Values are the latest revised GENESIS figures (pseudo-real-time).",
            ("Daily: month available on its release day; hourly: from the release hour."
             if alignment == "release" else
             "Month m's value on all days/hours of month m (look-ahead; ablation only)."),
            "Values are as known on day d; shift to forecast origin in the feature pipeline.",
            "Audit columns (ref_month, release_date, release_source) are not model features.",
        ],
        "rows": {"daily": len(daily), "hourly": len(hourly), "monthly": len(monthly)},
    }
    return write_outputs(daily, hourly, monthly, releases, Path(out_dir), metadata, alignment)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    parser.add_argument("--input-format", choices=["genesis", "simple"], default="genesis")
    parser.add_argument("--genesis-file", default=DEFAULT_GENESIS_FILE)
    parser.add_argument("--simple-file", default=DEFAULT_SIMPLE_FILE)
    parser.add_argument("--calendar-file", default=RELEASE_CALENDAR_FILE)
    parser.add_argument("--rule-day", type=int, default=RULE_DAY)
    parser.add_argument("--release-next-day", action="store_true",
                        help="daily: make a month available only from the day after its release")
    parser.add_argument("--release-hour", type=int, default=RELEASE_HOUR)
    parser.add_argument("--alignment", choices=ALIGNMENTS, default=DEFAULT_ALIGNMENT,
                        help="release: as known on day d (default). reference_month: month m on the "
                             "days of month m - leaks unpublished data, ablation only; writes "
                             f"{OUTPUT_STEMS['reference_month']}_*.csv")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run(
        raw_dir=args.raw_dir,
        out_dir=args.out_dir,
        start=args.start,
        end=args.end,
        input_format=args.input_format,
        genesis_file=args.genesis_file,
        simple_file=args.simple_file,
        calendar_file=args.calendar_file,
        rule_day=args.rule_day,
        include_release_day=not args.release_next_day,
        release_hour=args.release_hour,
        alignment=args.alignment,
    )


if __name__ == "__main__":
    main()