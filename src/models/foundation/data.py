"""
Shared data handling for the foundation models (TimesFM-3, TabICLForecaster).

What this module does (see docs/models/FOUNDATION.md, "Preprocessing"):

1. Reads ``src/data/final/data_hourly.csv`` or ``data_daily.csv``.
2. Builds a regular time axis:
   - hourly: ``date_from_utc`` (continuous in UTC, checked to be exactly 1 h apart),
   - daily: the local date of ``date_from`` (one row per local day).
3. Encodes the model inputs as numbers (booleans 0 / 1, ``month`` and
   ``day_of_week_raw`` as sine / cosine pairs) and stops if an input has NaN.
4. Defines the covariate roles of the shared setup (known / forecast / past only).
5. Finds the forecast origins of the validation (2023) or test (2024) year and
   cuts the context and the future part for every origin.
6. Writes forecasts in the shared forecast file format (MODELS.md, "Forecast files").

Only the columns of the input table of the shared setup are ever selected, so
leakage, audit and auxiliary columns never reach a model.

Conventions of the forecast files written here:
- ``origin``: the time of the first forecast step. Everything strictly before it
  is known. Hourly: UTC (``date_from_utc``), daily: the local date.
- ``target_time``: ``date_from_utc`` (hourly) or the local date (daily).
- ``step``: 1 ... H.
- ``y_true``: left empty, filled in by ``evaluate.py``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Paths and constants
# --------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = PROJECT_ROOT / "src" / "data" / "final"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "src" / "results"
DEFAULT_FORECAST_DIR = DEFAULT_RESULTS_DIR / "forecasts"

TARGET = "actual_consumption"
QUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
QUANTILE_COLUMNS = [f"q{q}" for q in QUANTILES]
FORECAST_COLUMNS = ["origin", "target_time", "step", "y_true", "y_pred", *QUANTILE_COLUMNS]

# Evaluation years of the shared setup (local calendar years).
SPLITS = {"val": 2023, "test": 2024}

HORIZONS = {"hourly": (24,), "daily": (1, 7)}  # decided 2026-11-04
EXPECTED_ROWS = {"hourly": 52608, "daily": 2192}
SEASONAL_PERIOD = {"hourly": 168, "daily": 7}  # seasonal naive: one week

# --------------------------------------------------------------------------
# Covariates (MODELS.md, "Model inputs")
# --------------------------------------------------------------------------

# Calendar columns after encoding (month and weekday as sine / cosine).
CALENDAR_ENCODED = [
    "month_sin",
    "month_cos",
    "dow_sin",
    "dow_cos",
    "is_holiday",
    "is_weekday",
    "weighted_regional_holiday",
    "weighted_school_holiday",
    "is_bridge_day",
    "is_christmas_new_year",
    "is_dst",
    "is_dst_transition_day",
]
# Calendar subset that TabICL's own ``datetime`` features do not cover (F6 "default").
CALENDAR_HOLIDAYS_ONLY = [
    "is_holiday",
    "weighted_regional_holiday",
    "weighted_school_holiday",
    "is_bridge_day",
    "is_christmas_new_year",
]
BOOL_COLUMNS = [
    "is_holiday",
    "is_weekday",
    "is_bridge_day",
    "is_christmas_new_year",
    "is_dst",
    "is_dst_transition_day",
]

# Hour of the local day as sine / cosine, derived here (final/ has no plain hour
# column). Hourly only. Same values as the Fourier pair sin_d1 / cos_d1.
HOUR_OF_DAY = ["hour_sin", "hour_cos"]
SOLAR_CAPACITY = ["solar_capacity_mw"]
SUN = {"hourly": ["is_day"], "daily": ["daylight_duration"]}
WEATHER = {
    "hourly": ["hdd", "shortwave_radiation", "wind_speed_10m", "precipitation"],
    "daily": ["hdd", "shortwave_radiation_sum", "wind_speed_10m_mean", "precipitation_sum"],
}
# Day-ahead price: the hourly price in the hourly data, the mean of the local
# day in the daily data (both columns of final/).
DAY_AHEAD_PRICE = {"hourly": "day_ahead_price", "daily": "day_ahead_price_mean"}
# Past only: known up to the origin, frozen at the last value for the horizon.
# industrial_confidence is the value of the month before; when the horizon
# crosses into the next month, that month's value is published after the origin, so it is
# past only here, not known.
PAST_ONLY = ["gas_price_eu_usd", "oxcgrt_stringency", "ipi_ei_level", "industrial_confidence"]

# Columns used to split the error by day type (evaluation only, not inputs).
DAY_TYPE_COLUMNS = ["is_holiday", "is_weekday", "is_bridge_day", "is_christmas_new_year"]


@dataclass(frozen=True)
class CovariateSet:
    """The model inputs of one run, split by role."""

    known: list[str] = field(default_factory=list)  # known future + forecast (weather)
    past_only: list[str] = field(default_factory=list)

    @property
    def all(self) -> list[str]:
        return [*self.known, *self.past_only]

    @property
    def n_variates(self) -> int:
        """Target + covariates, the number TimesFM-3 sees."""
        return 1 + len(self.known) + len(self.past_only)


def covariate_set(
    resolution: str,
    horizon: int,
    calendar: str = "full",
    include_covariates: bool = True,
) -> CovariateSet:
    """Inputs of the shared setup for one resolution and horizon.

    Parameters
    ----------
    resolution : "hourly" or "daily".
    horizon : steps of the forecast (24 hourly, 1 / 7 daily).
    calendar : "full" (all calendar columns) or "holidays" (only the holiday
        columns, for TabICL's default time features, experiment F6).
    include_covariates : False gives the target history only (F1, F4).
    """
    if not include_covariates:
        return CovariateSet()
    if calendar not in ("full", "holidays"):
        raise ValueError(f"calendar must be 'full' or 'holidays', got {calendar!r}")

    known = list(CALENDAR_ENCODED if calendar == "full" else CALENDAR_HOLIDAYS_ONLY)
    if resolution == "hourly":
        known += HOUR_OF_DAY
    known += SOLAR_CAPACITY + SUN[resolution] + WEATHER[resolution]
    # Day-ahead price: published around noon of the day before, so it is only
    # known for the first local day after a midnight origin: hourly 24 h and
    # daily 1 d may use it, daily 7 d may not.
    if (resolution == "hourly" and horizon <= 24) or (resolution == "daily" and horizon == 1):
        known.append(DAY_AHEAD_PRICE[resolution])
    return CovariateSet(known=known, past_only=list(PAST_ONLY))


# --------------------------------------------------------------------------
# Loading and encoding
# --------------------------------------------------------------------------


@dataclass
class SeriesFrame:
    """One resolution of ``final/``, sorted on a regular time axis and encoded."""

    resolution: str
    df: pd.DataFrame  # one row per step; ``timestamp`` is the regular time axis
    local_date: pd.Series  # local calendar date of every row (for origins / splits)

    @property
    def timestamp(self) -> pd.Series:
        return self.df["timestamp"]

    @property
    def y(self) -> np.ndarray:
        return self.df[TARGET].to_numpy(dtype=np.float64)

    def matrix(self, columns: list[str]) -> np.ndarray:
        """(n_rows, n_columns) float64 array of the given encoded columns."""
        if not columns:
            return np.empty((len(self.df), 0), dtype=np.float64)
        return self.df[columns].to_numpy(dtype=np.float64)


def _encode(df: pd.DataFrame) -> pd.DataFrame:
    """Numeric encoding of the calendar columns (FOUNDATION.md, shared step 5)."""
    out = df.copy()
    for col in BOOL_COLUMNS:
        if col in out:
            # CSV booleans come back as bool or as the strings "True" / "False".
            out[col] = out[col].map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0}).astype(float)
    out["month_sin"] = np.sin(2 * np.pi * (out["month"] - 1) / 12)
    out["month_cos"] = np.cos(2 * np.pi * (out["month"] - 1) / 12)
    out["dow_sin"] = np.sin(2 * np.pi * out["day_of_week_raw"] / 7)
    out["dow_cos"] = np.cos(2 * np.pi * out["day_of_week_raw"] / 7)
    if "day_ahead_price" in out:  # hourly file only
        # Local hour (the load follows the local clock); the double 02:00 at
        # the end of DST gets the same value twice.
        hour = out["date_from"].dt.hour
        out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        out["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    return out


def load_frame(resolution: str, data_dir: Path | str = DEFAULT_DATA_DIR) -> SeriesFrame:
    """Read, sort, check and encode one file of ``final/``."""
    if resolution not in HORIZONS:
        raise ValueError(f"resolution must be 'hourly' or 'daily', got {resolution!r}")
    path = Path(data_dir) / f"data_{resolution}.csv"
    df = pd.read_csv(path, index_col=0)

    df["date_from"] = pd.to_datetime(df["date_from"])
    df["date_from_utc"] = pd.to_datetime(df["date_from_utc"])
    df = df.sort_values("date_from_utc").reset_index(drop=True)

    if resolution == "hourly":
        # The local date_from has a gap / a double hour on the DST days, so the
        # time axis is the UTC column.
        ts = df["date_from_utc"]
        steps = ts.diff().dropna()
        if not (steps == pd.Timedelta(hours=1)).all():
            bad = ts[1:][steps != pd.Timedelta(hours=1)].head().tolist()
            raise ValueError(f"{path}: date_from_utc is not a regular 1 h series, first gaps at {bad}")
        df["timestamp"] = ts
    else:
        # A daily row starts at local midnight (22:00 / 23:00 UTC of the day
        # before), so the regular daily axis is the local date.
        ts = df["date_from"].dt.normalize()
        steps = ts.diff().dropna()
        if not (steps == pd.Timedelta(days=1)).all():
            bad = ts[1:][steps != pd.Timedelta(days=1)].head().tolist()
            raise ValueError(f"{path}: local dates are not a regular daily series, first gaps at {bad}")
        df["timestamp"] = ts

    if len(df) != EXPECTED_ROWS[resolution]:
        print(f"[data] note: {path.name} has {len(df)} rows, the docs expect {EXPECTED_ROWS[resolution]}")

    df = _encode(df)

    # Stop on missing values in any column a model could get (FOUNDATION.md, step 6).
    candidates = set([TARGET, *DAY_TYPE_COLUMNS])
    for h in HORIZONS[resolution]:
        candidates |= set(covariate_set(resolution, h).all)
    missing_cols = sorted(c for c in candidates if c not in df.columns)
    if missing_cols:
        raise KeyError(f"{path}: columns missing from final/: {missing_cols}")
    na = df[sorted(candidates)].isna().sum()
    na = na[na > 0]
    if len(na):
        raise ValueError(f"{path}: missing values in model inputs, not filling silently:\n{na}")

    return SeriesFrame(resolution=resolution, df=df, local_date=df["date_from"].dt.normalize())


# --------------------------------------------------------------------------
# Forecast origins and windows
# --------------------------------------------------------------------------


def origin_positions(frame: SeriesFrame, split: str, horizon: int) -> np.ndarray:
    """Row positions of the forecast origins of one evaluation year.

    Hourly: every local midnight (the first row of each local date).
    Daily: every day. Only origins whose whole horizon lies inside the year.
    """
    if split not in SPLITS:
        raise ValueError(f"split must be one of {list(SPLITS)}, got {split!r}")
    year = SPLITS[split]
    in_year = np.flatnonzero((frame.local_date.dt.year == year).to_numpy())
    if len(in_year) == 0:
        raise ValueError(f"no rows of {year} in the {frame.resolution} data")
    last = in_year[-1]

    if frame.resolution == "hourly":
        new_day = frame.local_date.ne(frame.local_date.shift()).to_numpy()
        cand = in_year[new_day[in_year]]
    else:
        cand = in_year
    return cand[cand + horizon - 1 <= last]


@dataclass
class Window:
    """Inputs of one forecast origin. The future target is never included."""

    pos: int  # row position of the first forecast step
    y_context: np.ndarray  # (L,)
    known_context: np.ndarray  # (L, n_known)
    known_future: np.ndarray  # (H, n_known)
    past_context: np.ndarray  # (L, n_past)


def make_window(
    frame: SeriesFrame,
    y: np.ndarray,
    known: np.ndarray,
    past: np.ndarray,
    pos: int,
    horizon: int,
    context_length: int | None,
) -> Window:
    """Cut the context (rows before ``pos``) and the future (next ``horizon`` rows)."""
    start = 0 if context_length is None else max(0, pos - context_length)
    return Window(
        pos=pos,
        y_context=y[start:pos],
        known_context=known[start:pos],
        known_future=known[pos : pos + horizon],
        past_context=past[start:pos],
    )


# --------------------------------------------------------------------------
# Forecast files
# --------------------------------------------------------------------------


def forecasts_to_frame(
    frame: SeriesFrame,
    positions: np.ndarray,
    horizon: int,
    y_pred: np.ndarray,
    quantiles: np.ndarray | None,
) -> pd.DataFrame:
    """Shared forecast file format, one row per (origin, step).

    y_pred : (n_origins, H); quantiles : (n_origins, H, 9) or None.
    """
    n = len(positions)
    if y_pred.shape != (n, horizon):
        raise ValueError(f"y_pred has shape {y_pred.shape}, expected {(n, horizon)}")
    ts = frame.timestamp.to_numpy()
    rows = (positions[:, None] + np.arange(horizon)[None, :]).ravel()
    out = pd.DataFrame(
        {
            "origin": np.repeat(ts[positions], horizon),
            "target_time": ts[rows],
            "step": np.tile(np.arange(1, horizon + 1), n),
            "y_true": np.nan,
            "y_pred": y_pred.ravel(),
        }
    )
    for i, col in enumerate(QUANTILE_COLUMNS):
        out[col] = quantiles[:, :, i].ravel() if quantiles is not None else np.nan
    if frame.resolution == "daily":
        out["origin"] = pd.to_datetime(out["origin"]).dt.strftime("%Y-%m-%d")
        out["target_time"] = pd.to_datetime(out["target_time"]).dt.strftime("%Y-%m-%d")
    return out[FORECAST_COLUMNS]


def write_forecasts(out: pd.DataFrame, path: Path | str, meta: dict) -> Path:
    """Write the forecast CSV and a JSON sidecar with the run settings."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2, default=str))
    print(f"[data] wrote {len(out)} rows -> {path}")
    return path


def horizon_label(resolution: str, horizon: int) -> str:
    return f"{horizon}{'h' if resolution == 'hourly' else 'd'}"
