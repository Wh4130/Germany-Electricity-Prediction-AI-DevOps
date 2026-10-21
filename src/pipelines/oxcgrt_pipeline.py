"""OxCGRT pipeline: German COVID-19 policy stringency as daily and hourly features.

Source
    Oxford COVID-19 Government Response Tracker (OxCGRT), final dataset
    https://github.com/OxCGRT/covid-policy-dataset  (file: data/raw/OxCGRT_compact_national_v1.csv)
    Licence: CC BY 4.0. Coverage: 2020-01-01 to 2022-12-31, daily.

Outputs (in ``src/data/features/policy``)
    oxcgrt_daily.csv     one row per calendar day,  column ``index`` = 0..N-1 (join key)
    oxcgrt_hourly.csv    one row per local hour,    column ``index`` = 0..N-1 (join key)
    oxcgrt_metadata.json source, checksum, assumptions, row counts

Join-key convention
    ``index`` is the 0-based position in a fixed calendar:
      * daily : every calendar day from START_DATE to END_DATE
      * hourly: every hour from START_DATE 00:00 to END_DATE 23:00 in Europe/Berlin
                local time (23 rows on the spring DST day, 25 on the autumn DST day),
                which matches the row order of the SMARD hourly export.
    Every feature pipeline must use the same calendar so the keys line up.

Assumptions (also written to the metadata file)
    * Before the source coverage (2019) all values are 0: no pandemic, a structural zero.
    * After the source coverage (2023-2024) all values are set to 0 by assumption;
      ``oxcgrt_observed`` = 0 marks these rows.
    * Short gaps inside the coverage are forward-filled up to ``max_ffill_days``.
    * Values are "as known on day d". Shifting to the forecast origin (persistence)
      happens later in the feature pipeline, not here.

Usage (from the project root)
    python src/pipelines/oxcgrt_pipeline.py                # download if missing, then build
    python src/pipelines/oxcgrt_pipeline.py --force-download
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger("oxcgrt_pipeline")

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------
OXCGRT_URL = (
    "https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/"
    "OxCGRT_compact_national_v1.csv"
)
OXCGRT_COMMIT_API = "https://api.github.com/repos/OxCGRT/covid-policy-dataset/commits/main"
RAW_FILENAME = "OxCGRT_compact_national_v1.csv"

DEFAULT_RAW_DIR = Path("src/data/external_raw")
DEFAULT_OUT_DIR = Path("src/data/features/policy")

START_DATE = "2019-01-01"
END_DATE = "2024-12-31"
TIMEZONE = "Europe/Berlin"
JOIN_KEY = "index"

COUNTRY_CODE = "DEU"
JURISDICTION = "NAT_TOTAL"

# source column -> feature column
COLUMN_MAP = {
    "StringencyIndex_Average": "oxcgrt_stringency",
    "C1M_School closing": "oxcgrt_c1_school",
    "C2M_Workplace closing": "oxcgrt_c2_workplace",
    "C6M_Stay at home requirements": "oxcgrt_c6_stay_home",
}
FEATURE_COLUMNS = list(COLUMN_MAP.values())
OBSERVED_COLUMN = "oxcgrt_observed"

# valid ranges from the OxCGRT codebook
VALUE_RANGES = {
    "oxcgrt_stringency": (0.0, 100.0),
    "oxcgrt_c1_school": (0.0, 3.0),
    "oxcgrt_c2_workplace": (0.0, 3.0),
    "oxcgrt_c6_stay_home": (0.0, 3.0),
}

DEFAULT_MAX_FFILL_DAYS = 3


# --------------------------------------------------------------------------------------
# Calendars (shared convention with the other *_pipeline.py files)
# --------------------------------------------------------------------------------------
def build_daily_calendar(start: str = START_DATE, end: str = END_DATE) -> pd.DataFrame:
    """One row per calendar day, 0-based RangeIndex as join key."""
    dates = pd.date_range(start=start, end=end, freq="D")
    cal = pd.DataFrame({"date": dates})
    cal.index = pd.RangeIndex(len(cal), name=JOIN_KEY)
    return cal


def build_hourly_calendar(start: str = START_DATE, end: str = END_DATE) -> pd.DataFrame:
    """One row per local hour (Europe/Berlin), DST-aware, 0-based RangeIndex as join key.

    ``datetime_from`` is tz-aware local time; ``date`` is the local calendar day.
    """
    first = pd.Timestamp(f"{start} 00:00", tz=TIMEZONE)
    last = pd.Timestamp(f"{end} 23:00", tz=TIMEZONE)
    stamps = pd.date_range(start=first, end=last, freq="h")
    cal = pd.DataFrame({"datetime_from": stamps})
    cal["date"] = cal["datetime_from"].dt.tz_localize(None).dt.normalize()
    cal.index = pd.RangeIndex(len(cal), name=JOIN_KEY)
    return cal


# --------------------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch_commit_sha(timeout: int = 15) -> str | None:
    """Best effort: latest commit SHA of the OxCGRT repo (None if unreachable)."""
    try:
        req = urllib.request.Request(OXCGRT_COMMIT_API, headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")).get("sha")
    except Exception as exc:  # noqa: BLE001 - metadata only, never fatal
        logger.warning("Could not fetch OxCGRT commit SHA (%s); recording None.", exc)
        return None


def download_raw(raw_dir: Path = DEFAULT_RAW_DIR, url: str = OXCGRT_URL, force: bool = False) -> Path:
    """Download the national compact file into ``raw_dir`` (skips if present unless ``force``)."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / RAW_FILENAME
    meta_path = raw_dir / f"{RAW_FILENAME}.source.json"

    if target.exists() and not force:
        logger.info("Raw file already present: %s (use --force-download to refresh)", target)
        return target

    tmp = target.with_suffix(".part")
    logger.info("Downloading %s", url)
    with urllib.request.urlopen(url, timeout=120) as resp, tmp.open("wb") as fh:
        while chunk := resp.read(1 << 20):
            fh.write(chunk)
    tmp.replace(target)

    meta = {
        "url": url,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": _sha256(target),
        "repo_commit_sha": _fetch_commit_sha(),
        "licence": "CC BY 4.0",
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Saved %s (%s bytes)", target, target.stat().st_size)
    return target


# --------------------------------------------------------------------------------------
# Load and clean
# --------------------------------------------------------------------------------------
def load_germany(raw_path: Path) -> pd.DataFrame:
    """Read the raw file and return Germany's national series: ``date`` + feature columns."""
    raw = pd.read_csv(raw_path, dtype=str, low_memory=False)

    required = ["CountryCode", "Jurisdiction", "Date", *COLUMN_MAP]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise KeyError(f"OxCGRT file is missing expected columns: {missing}")

    de = raw[(raw["CountryCode"] == COUNTRY_CODE) & (raw["Jurisdiction"] == JURISDICTION)].copy()
    if de.empty:
        raise ValueError(f"No rows for CountryCode={COUNTRY_CODE}, Jurisdiction={JURISDICTION}")

    de["date"] = pd.to_datetime(de["Date"], format="%Y%m%d")
    out = de[["date", *COLUMN_MAP]].rename(columns=COLUMN_MAP)
    for col in FEATURE_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    dupes = out["date"].duplicated()
    if dupes.any():
        raise ValueError(f"Duplicate dates in OxCGRT Germany data: {out.loc[dupes, 'date'].tolist()[:5]}")

    out = out.sort_values("date").reset_index(drop=True)
    logger.info("Germany rows: %d (%s to %s)", len(out), out["date"].min().date(), out["date"].max().date())
    return out


# --------------------------------------------------------------------------------------
# Build daily / hourly
# --------------------------------------------------------------------------------------
def build_daily(
    germany: pd.DataFrame,
    start: str = START_DATE,
    end: str = END_DATE,
    max_ffill_days: int = DEFAULT_MAX_FFILL_DAYS,
) -> pd.DataFrame:
    """Reindex to the daily calendar and apply the documented fill rules."""
    cal = build_daily_calendar(start, end)
    src_first, src_last = germany["date"].min(), germany["date"].max()

    daily = cal.reset_index().merge(germany, on="date", how="left").set_index(JOIN_KEY)

    observed = daily[FEATURE_COLUMNS].notna().all(axis=1)
    daily[OBSERVED_COLUMN] = observed.astype("int8")

    before = daily["date"] < src_first
    after = daily["date"] > src_last
    inside = ~before & ~after

    # gaps inside the coverage: limited forward fill, otherwise fail loudly
    n_gaps = int((inside & ~observed).sum())
    if n_gaps:
        logger.warning("%d day(s) with missing values inside the coverage; forward-filling (limit=%d)",
                       n_gaps, max_ffill_days)
        daily.loc[inside, FEATURE_COLUMNS] = daily.loc[inside, FEATURE_COLUMNS].ffill(limit=max_ffill_days)
        still = inside & daily[FEATURE_COLUMNS].isna().any(axis=1)
        if still.any():
            raise ValueError(
                "Gap longer than max_ffill_days inside OxCGRT coverage on: "
                f"{daily.loc[still, 'date'].dt.date.tolist()[:10]}"
            )

    # outside the coverage: structural zero (before) / assumed zero (after)
    daily.loc[before | after, FEATURE_COLUMNS] = 0.0
    logger.info("Days set to 0 before coverage: %d, after coverage: %d", int(before.sum()), int(after.sum()))

    return daily[["date", *FEATURE_COLUMNS, OBSERVED_COLUMN]]


def build_hourly(daily: pd.DataFrame, start: str = START_DATE, end: str = END_DATE) -> pd.DataFrame:
    """Broadcast daily values to every local hour of the same calendar day."""
    cal = build_hourly_calendar(start, end)
    feats = daily[["date", *FEATURE_COLUMNS, OBSERVED_COLUMN]]
    hourly = cal.reset_index().merge(feats, on="date", how="left").set_index(JOIN_KEY)
    return hourly[["datetime_from", "date", *FEATURE_COLUMNS, OBSERVED_COLUMN]]


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------
def _check_join_key(df: pd.DataFrame, name: str) -> None:
    expected = pd.RangeIndex(len(df), name=JOIN_KEY)
    if not df.index.equals(expected):
        raise AssertionError(f"{name}: index is not a 0-based consecutive join key")


def _check_values(df: pd.DataFrame, name: str) -> None:
    if df[FEATURE_COLUMNS + [OBSERVED_COLUMN]].isna().any().any():
        raise AssertionError(f"{name}: NaN values in feature columns")
    for col, (lo, hi) in VALUE_RANGES.items():
        bad = (df[col] < lo) | (df[col] > hi)
        if bad.any():
            raise AssertionError(f"{name}: {col} outside [{lo}, {hi}] in {int(bad.sum())} rows")


def validate_daily(daily: pd.DataFrame, start: str = START_DATE, end: str = END_DATE) -> None:
    _check_join_key(daily, "daily")
    expected_dates = pd.date_range(start, end, freq="D")
    if not pd.DatetimeIndex(daily["date"]).equals(expected_dates):
        raise AssertionError("daily: dates are not the complete consecutive calendar")
    _check_values(daily, "daily")


def validate_hourly(hourly: pd.DataFrame, daily: pd.DataFrame,
                    start: str = START_DATE, end: str = END_DATE) -> None:
    _check_join_key(hourly, "hourly")
    expected = build_hourly_calendar(start, end)["datetime_from"]
    if not hourly["datetime_from"].reset_index(drop=True).equals(expected.reset_index(drop=True)):
        raise AssertionError("hourly: timestamps differ from the reference hourly calendar")
    _check_values(hourly, "hourly")
    per_day = hourly.groupby("date")[FEATURE_COLUMNS].nunique()
    if (per_day > 1).any().any():
        raise AssertionError("hourly: a feature varies within a day")


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------
def _format_for_csv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    if "datetime_from" in out.columns:
        out["datetime_from"] = out["datetime_from"].map(lambda t: t.isoformat())
    return out


def write_outputs(daily: pd.DataFrame, hourly: pd.DataFrame, out_dir: Path,
                  metadata: dict | None = None) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "daily": out_dir / "oxcgrt_daily.csv",
        "hourly": out_dir / "oxcgrt_hourly.csv",
        "metadata": out_dir / "oxcgrt_metadata.json",
    }
    _format_for_csv(daily).to_csv(paths["daily"], index=True, index_label=JOIN_KEY)
    _format_for_csv(hourly).to_csv(paths["hourly"], index=True, index_label=JOIN_KEY)
    paths["metadata"].write_text(json.dumps(metadata or {}, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote %s (%d rows) and %s (%d rows)", paths["daily"], len(daily), paths["hourly"], len(hourly))
    return paths


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------
def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    out_dir: Path = DEFAULT_OUT_DIR,
    start: str = START_DATE,
    end: str = END_DATE,
    download: bool = True,
    force_download: bool = False,
    max_ffill_days: int = DEFAULT_MAX_FFILL_DAYS,
) -> dict[str, Path]:
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    raw_path = raw_dir / RAW_FILENAME
    if download or force_download:
        raw_path = download_raw(raw_dir, force=force_download)
    if not raw_path.exists():
        raise FileNotFoundError(f"{raw_path} not found; run without --no-download or place the file there.")

    germany = load_germany(raw_path)
    daily = build_daily(germany, start, end, max_ffill_days)
    validate_daily(daily, start, end)
    hourly = build_hourly(daily, start, end)
    validate_hourly(hourly, daily, start, end)

    source_meta_path = raw_dir / f"{RAW_FILENAME}.source.json"
    metadata = {
        "pipeline": "oxcgrt_pipeline",
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file": str(raw_path),
        "source_sha256": _sha256(raw_path),
        "source_download": json.loads(source_meta_path.read_text()) if source_meta_path.exists() else None,
        "filter": {"CountryCode": COUNTRY_CODE, "Jurisdiction": JURISDICTION},
        "column_map": COLUMN_MAP,
        "calendar": {"start": start, "end": end, "timezone": TIMEZONE, "join_key": JOIN_KEY},
        "source_coverage": [str(germany["date"].min().date()), str(germany["date"].max().date())],
        "assumptions": [
            "Before source coverage: 0 (no pandemic).",
            "After source coverage: 0 by assumption; oxcgrt_observed = 0.",
            f"Gaps inside coverage forward-filled up to {max_ffill_days} days.",
            "Values are as known on day d; shift to forecast origin in the feature pipeline.",
        ],
        "rows": {"daily": len(daily), "hourly": len(hourly)},
        "observed_days": int(daily[OBSERVED_COLUMN].sum()),
    }
    return write_outputs(daily, hourly, out_dir, metadata)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    parser.add_argument("--no-download", action="store_true", help="only use the local raw file")
    parser.add_argument("--force-download", action="store_true", help="re-download even if present")
    parser.add_argument("--max-ffill-days", type=int, default=DEFAULT_MAX_FFILL_DAYS)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run(
        raw_dir=args.raw_dir,
        out_dir=args.out_dir,
        start=args.start,
        end=args.end,
        download=not args.no_download,
        force_download=args.force_download,
        max_ffill_days=args.max_ffill_days,
    )


if __name__ == "__main__":
    main()