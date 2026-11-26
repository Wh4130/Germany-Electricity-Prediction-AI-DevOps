"""
The shared setup that every model and the analysis rely on (MODELS.md, "Shared setup").

- constants: target, quantiles, evaluation years, horizons, seasonal period,
- ``load_frame``: one resolution of ``final/`` on a regular time axis, with
  the boolean flags as 0 / 1 and the engineered calendar / weather columns
  (``ENGINEERED``). No model-specific encoding happens here (see e.g.
  ``src.models.foundation.data`` for the inputs of the foundation models),
- the shared forecast file format (MODELS.md, "Forecast files"):
  ``origin, target_time, step, y_true, y_pred, q0.1 ... q0.9`` + a JSON sidecar.

Conventions of the forecast files:
- ``origin``: the time of the first forecast step. Everything strictly before it
  is known. Hourly: UTC (``date_from_utc``), daily: the local date.
- ``target_time``: ``date_from_utc`` (hourly) or the local date (daily).
- ``step``: 1 ... H.
- ``y_true``: may be left empty, the evaluation fills it from ``final/``.
- quantile columns: NaN for point-forecast models.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.paths import DATA_DIR

# --------------------------------------------------------------------------
# Constants of the shared setup
# --------------------------------------------------------------------------

TARGET = "actual_consumption"
QUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
QUANTILE_COLUMNS = [f"q{q}" for q in QUANTILES]
FORECAST_COLUMNS = ["origin", "target_time", "step", "y_true", "y_pred", *QUANTILE_COLUMNS]

SPLITS = {"val": 2023, "test": 2024}  # evaluation years (local calendar years)
HORIZONS = {"hourly": (24,), "daily": (1, 7)}  # decided 2026-11-04
EXPECTED_ROWS = {"hourly": 52608, "daily": 2192}
SEASONAL_PERIOD = {"hourly": 168, "daily": 7}  # seasonal naive: one week

BOOL_COLUMNS = [
    "is_holiday",
    "is_weekday",
    "is_bridge_day",
    "is_christmas_new_year",
    "is_dst",
    "is_dst_transition_day",
]
# Columns used to split the error by day type (evaluation only).
DAY_TYPE_COLUMNS = ["is_holiday", "is_weekday", "is_bridge_day", "is_christmas_new_year"]

# Day-ahead price: the hourly price in the hourly data, the mean of the local
# day in the daily data (both columns of final/).
DAY_AHEAD_PRICE = {"hourly": "day_ahead_price", "daily": "day_ahead_price_mean"}
RADIATION = {"hourly": "shortwave_radiation", "daily": "shortwave_radiation_sum"}
WIND = {"hourly": "wind_speed_10m", "daily": "wind_speed_10m_mean"}
RAIN = {"hourly": "precipitation", "daily": "precipitation_sum"}

# Engineered columns (added 2026-11-11 after the weather and day-type error
# analysis). All three use only the calendar and the weather inputs:
# - hdd_delta_7d: HDD minus HDD one week before (168 h / 7 d).
# - pv_proxy: solar_capacity_mw x radiation, a proxy of rooftop PV output.
#   Hourly: MW at 1 kW/m2 (radiation W/m2 / 1000); daily: MWh (MJ/m2 / 3.6).
# - holiday_week: 1 on a Mon - Fri that is not itself a holiday, bridge day or
#   Christmas window day, but lies in a week (Mon - Sun) with a public holiday on
#   a weekday, or is 18 - 23 December.
#   Uses the national is_holiday only (regional holidays: weighted_regional_holiday).
ENGINEERED = ["hdd_delta_7d", "pv_proxy", "holiday_week"]
PRE_CHRISTMAS_DAYS = range(18, 24)


def horizon_label(resolution: str, horizon: int) -> str:
    """``24h``, ``7d``: the horizon as it appears in file names."""
    return f"{horizon}{'h' if resolution == 'hourly' else 'd'}"


def horizon_text(resolution: str, horizon: int) -> str:
    """``hourly 24 h``, ``daily 7 d``: the horizon as it appears in tables and figures."""
    return f"{resolution} {horizon} {'h' if resolution == 'hourly' else 'd'}"


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


@dataclass
class SeriesFrame:
    """One resolution of ``final/``, sorted on a regular time axis."""

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
        """(n_rows, n_columns) float64 array of the given columns."""
        if not columns:
            return np.empty((len(self.df), 0), dtype=np.float64)
        return self.df[columns].to_numpy(dtype=np.float64)

    def time_keys(self) -> np.ndarray:
        """Keys that ``time_key`` gives for the forecast files, one per row."""
        return time_key(self.timestamp, self.resolution)


def time_key(values, resolution: str) -> np.ndarray:
    """Comparable keys of time stamps, whatever text format a forecast file used.

    Hourly: UTC without time zone (naive values are taken as UTC). Daily: ``YYYY-MM-DD``.
    """
    s = pd.Series(values)
    if resolution == "daily":
        return pd.to_datetime(s.astype(str).str[:10]).dt.strftime("%Y-%m-%d").to_numpy()
    return pd.to_datetime(s, utc=True).dt.tz_convert(None).to_numpy()


def _encode_bools(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in BOOL_COLUMNS:
        if col in out:
            # CSV booleans come back as bool or as the strings "True" / "False".
            out[col] = out[col].map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0}).astype(float)
    return out


def add_engineered(df: pd.DataFrame, resolution: str) -> pd.DataFrame:
    """The engineered columns of ``ENGINEERED`` (boolean flags as 0 / 1, rows sorted)."""
    out = df.copy()

    # HDD change against one week before; the first week has no earlier week (0).
    period = SEASONAL_PERIOD[resolution]
    hdd = out["hdd"].to_numpy(dtype=np.float64)
    delta = np.zeros(len(out))
    delta[period:] = hdd[period:] - hdd[:-period]
    out["hdd_delta_7d"] = delta

    # Potential PV output of the installed capacity.
    if resolution == "hourly":
        out["pv_proxy"] = out["solar_capacity_mw"] * out["shortwave_radiation"] / 1000.0
    else:
        out["pv_proxy"] = out["solar_capacity_mw"] * out["shortwave_radiation_sum"] / 3.6

    # Holiday week, decided per local date and mapped back to the rows.
    date = out["date_from"].dt.normalize()
    flags = pd.DataFrame(
        {
            "date": date.to_numpy(),
            "hol": out["is_holiday"].to_numpy() > 0.5,
            "bridge": out["is_bridge_day"].to_numpy() > 0.5,
            "xmas": out["is_christmas_new_year"].to_numpy() > 0.5,
        }
    )
    day = flags.groupby("date")[["hol", "bridge", "xmas"]].any()
    d = pd.DatetimeIndex(day.index)
    dow = d.dayofweek.to_numpy()
    week_start = (d - pd.to_timedelta(dow, unit="D")).to_numpy()
    hol = day["hol"].to_numpy()
    week_has_hol = pd.Series(hol & (dow < 5)).groupby(week_start).transform("any").to_numpy()
    pre_xmas = (d.month.to_numpy() == 12) & np.isin(d.day.to_numpy(), list(PRE_CHRISTMAS_DAYS))
    hw = (dow < 5) & ~hol & ~day["bridge"].to_numpy() & ~day["xmas"].to_numpy() & (week_has_hol | pre_xmas)
    out["holiday_week"] = pd.Series(hw.astype(float), index=d).reindex(date.to_numpy()).to_numpy()
    return out


def load_frame(resolution: str, data_dir: Path | str = DATA_DIR) -> SeriesFrame:
    """Read, sort and check one file of ``final/``; flags as 0 / 1, engineered columns added."""
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
        step = pd.Timedelta(hours=1)
    else:
        # A daily row starts at local midnight (22:00 / 23:00 UTC of the day
        # before), so the regular daily axis is the local date.
        ts = df["date_from"].dt.normalize()
        step = pd.Timedelta(days=1)
    diffs = ts.diff().dropna()
    if not (diffs == step).all():
        bad = ts[1:][diffs != step].head().tolist()
        raise ValueError(f"{path}: the time axis is not regular ({step}), first gaps at {bad}")
    df["timestamp"] = ts

    if len(df) != EXPECTED_ROWS[resolution]:
        print(f"[data] note: {path.name} has {len(df)} rows, the docs expect {EXPECTED_ROWS[resolution]}")

    missing = [c for c in [TARGET, *DAY_TYPE_COLUMNS] if c not in df]
    if missing:
        raise KeyError(f"{path}: columns missing from final/: {missing}")

    df = add_engineered(_encode_bools(df), resolution)
    return SeriesFrame(resolution=resolution, df=df, local_date=df["date_from"].dt.normalize())


class FrameCache(dict):
    """``frames[resolution]`` loads ``final/`` once per resolution."""

    def __init__(self, data_dir: Path | str = DATA_DIR, loader=load_frame):
        super().__init__()
        self.data_dir = data_dir
        self.loader = loader

    def __missing__(self, resolution: str) -> SeriesFrame:
        self[resolution] = frame = self.loader(resolution, self.data_dir)
        return frame


# --------------------------------------------------------------------------
# Forecast origins
# --------------------------------------------------------------------------


def origin_rule(resolution: str, horizon: int) -> str:
    """Which rows are forecast origins (written to the JSON sidecars).

    Hourly 1-step forecasts start at every hour, like the 1-hour forecasts of
    the tree and SARIMAX runs; longer hourly horizons start at local midnight.
    """
    if resolution == "daily":
        return "every day"
    return "every hour" if horizon == 1 else "every local midnight"


def origin_positions(frame: SeriesFrame, split: str, horizon: int) -> np.ndarray:
    """Row positions of the forecast origins of one evaluation year (see ``origin_rule``).

    Hourly 1 step: every hour (8760 origins in 2023, 8784 in 2024).
    Hourly, longer horizons: every local midnight (the first row of each local date).
    Daily: every day. Only origins whose whole horizon lies inside the year.
    """
    if split not in SPLITS:
        raise ValueError(f"split must be one of {list(SPLITS)}, got {split!r}")
    year = SPLITS[split]
    in_year = np.flatnonzero((frame.local_date.dt.year == year).to_numpy())
    if len(in_year) == 0:
        raise ValueError(f"no rows of {year} in the {frame.resolution} data")
    last = in_year[-1]

    if origin_rule(frame.resolution, horizon) == "every local midnight":
        new_day = frame.local_date.ne(frame.local_date.shift()).to_numpy()
        cand = in_year[new_day[in_year]]
    else:
        cand = in_year
    return cand[cand + horizon - 1 <= last]


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


def read_meta(forecast_path: Path | str) -> dict:
    """The JSON sidecar of a forecast file ({} if there is none)."""
    meta_path = Path(forecast_path).with_suffix(".json")
    return json.loads(meta_path.read_text()) if meta_path.exists() else {}