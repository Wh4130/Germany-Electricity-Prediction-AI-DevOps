"""
Data handling of the foundation models (TimesFM-3, TabICLForecaster).

The shared setup (paths, target, quantiles, evaluation years, the forecast
file format and the base loader) lives in ``src.common``; this module adds
what only the foundation models need (see docs/models/FOUNDATION.md,
"Preprocessing"):

1. ``load_frame``: the shared loader plus the numeric encoding of the model
   inputs (``month`` and ``day_of_week_raw`` as sine / cosine pairs, the local
   hour for hourly data); stops if an input has NaN.
2. The covariate roles of the shared setup (known / forecast / past only) and
   the switch for the engineered covariates (``hdd_delta_7d``, ``pv_proxy``,
   ``holiday_week``, see ``src.common.dataset.ENGINEERED``). They are always
   computed, but a model gets them only when they are switched on
   (``EXTRA_FEATURES`` or ``covariate_set(..., extra=True)``).
3. The context / future windows of every forecast origin.

Only the columns of the input table of the shared setup are ever selected, so
leakage, audit and auxiliary columns never reach a model.

Forecasts are written to ``src/results/foundation/forecasts`` (one results
folder per model family, see ``src.common.paths``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# Shared setup, re-exported so the foundation scripts import everything from here.
from src.common.dataset import (  # noqa: F401
    BOOL_COLUMNS,
    DAY_AHEAD_PRICE,
    DAY_TYPE_COLUMNS,
    ENGINEERED,
    FORECAST_COLUMNS,
    QUANTILE_COLUMNS,
    QUANTILES,
    SEASONAL_PERIOD,
    SPLITS,
    TARGET,
    SeriesFrame,
    forecasts_to_frame,
    horizon_label,
    origin_positions,
    origin_rule,
    write_forecasts,
)
from src.common.dataset import HORIZONS as SHARED_HORIZONS
from src.common.dataset import load_frame as load_base_frame
from src.common.paths import DATA_DIR, PROJECT_ROOT, model_dir  # noqa: F401

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

MODEL_NAME = "foundation"  # results folder: src/results/foundation/
EXTRA_FEATURES_NAME = "foundation_extra_features"  # results folder of run_extra_features.py
DEFAULT_DATA_DIR = DATA_DIR
DEFAULT_RESULTS_DIR = model_dir(MODEL_NAME)
DEFAULT_FORECAST_DIR = DEFAULT_RESULTS_DIR / "forecasts"

# --------------------------------------------------------------------------
# Horizons
# --------------------------------------------------------------------------

# The shared horizons plus hourly 1 h (added 2026-11-19, TimesFM-3 only; TabICL
# is daily only). Hourly 1 h origins are every hour, 24 h origins every local
# midnight (src.common.dataset.origin_positions).
HORIZONS = {**SHARED_HORIZONS, "hourly": tuple(sorted({1, *SHARED_HORIZONS["hourly"]}))}

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

# Hour of the local day as sine / cosine, derived here (final/ has no plain hour
# column). Hourly only. Same values as the Fourier pair sin_d1 / cos_d1.
HOUR_OF_DAY = ["hour_sin", "hour_cos"]
SOLAR_CAPACITY = ["solar_capacity_mw"]
SUN = {"hourly": ["is_day"], "daily": ["daylight_duration"]}
WEATHER = {
    "hourly": ["hdd", "shortwave_radiation", "wind_speed_10m", "precipitation"],
    "daily": ["hdd", "shortwave_radiation_sum", "wind_speed_10m_mean", "precipitation_sum"],
}
# Past only: known up to the origin, frozen at the last value for the horizon.
# industrial_confidence is the value of the month before; when the horizon
# crosses into the next month, that month's value is published after the origin, so it is
# past only here, not known.
PAST_ONLY = ["gas_price_eu_usd", "oxcgrt_stringency", "ipi_ei_level", "industrial_confidence"]

# Default of covariate_set(extra=None). False keeps the inputs of the existing
# runs; run_extra_features.py sets it to True.
EXTRA_FEATURES = False


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
    extra: bool | None = None,
) -> CovariateSet:
    """Inputs of the shared setup for one resolution and horizon.

    Parameters
    ----------
    resolution : "hourly" or "daily".
    horizon : steps of the forecast (1 / 24 hourly, 1 / 7 daily).
    calendar : "full" (all calendar columns) or "holidays" (only the holiday
        columns, for TabICL's default time features, experiment F6).
    include_covariates : False gives the target history only (F1, F4).
    extra : add the engineered covariates (``ENGINEERED``). None uses the
        module default ``EXTRA_FEATURES``.
    """
    if not include_covariates:
        return CovariateSet()
    if calendar not in ("full", "holidays"):
        raise ValueError(f"calendar must be 'full' or 'holidays', got {calendar!r}")

    known = list(CALENDAR_ENCODED if calendar == "full" else CALENDAR_HOLIDAYS_ONLY)
    if resolution == "hourly":
        known += HOUR_OF_DAY
    known += SOLAR_CAPACITY + SUN[resolution] + WEATHER[resolution]
    # Day-ahead price: all prices of a local day are published around noon of
    # the day before, so at an origin the prices of the origin's own local day
    # are always known, those of the next day only from noon on.
    # - hourly 24 h (origin at local midnight): the whole forecast day is known,
    # - hourly 1 h (origin at any hour): the one target hour is the origin hour,
    #   which lies in the origin's own day, so it is known,
    # - daily 1 d: known; daily 7 d: only day 1 would be known, so not used.
    if (resolution == "hourly" and horizon <= 24) or (resolution == "daily" and horizon == 1):
        known.append(DAY_AHEAD_PRICE[resolution])
    if EXTRA_FEATURES if extra is None else extra:
        known += ENGINEERED
    return CovariateSet(known=known, past_only=list(PAST_ONLY))


# --------------------------------------------------------------------------
# Loading and encoding
# --------------------------------------------------------------------------


def _encode(df: pd.DataFrame, resolution: str) -> pd.DataFrame:
    """Cyclic encoding of the calendar columns (FOUNDATION.md, shared step 5)."""
    out = df.copy()
    out["month_sin"] = np.sin(2 * np.pi * (out["month"] - 1) / 12)
    out["month_cos"] = np.cos(2 * np.pi * (out["month"] - 1) / 12)
    out["dow_sin"] = np.sin(2 * np.pi * out["day_of_week_raw"] / 7)
    out["dow_cos"] = np.cos(2 * np.pi * out["day_of_week_raw"] / 7)
    if resolution == "hourly":
        # Local hour (the load follows the local clock); the double 02:00 at
        # the end of DST gets the same value twice.
        hour = out["date_from"].dt.hour
        out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        out["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    return out


def load_frame(resolution: str, data_dir: Path | str = DEFAULT_DATA_DIR) -> SeriesFrame:
    """The shared frame of ``final/`` with the model inputs encoded and checked."""
    base = load_base_frame(resolution, data_dir)
    df = _encode(base.df, resolution)

    # Stop on missing values in any column a model could get (FOUNDATION.md, step 6).
    candidates = set([TARGET, *DAY_TYPE_COLUMNS])
    for h in HORIZONS[resolution]:
        candidates |= set(covariate_set(resolution, h, extra=True).all)
    missing_cols = sorted(c for c in candidates if c not in df.columns)
    if missing_cols:
        raise KeyError(f"data_{resolution}.csv: columns missing from final/: {missing_cols}")
    na = df[sorted(candidates)].isna().sum()
    na = na[na > 0]
    if len(na):
        raise ValueError(f"data_{resolution}.csv: missing values in model inputs, not filling silently:\n{na}")

    return SeriesFrame(resolution=resolution, df=df, local_date=base.local_date)


# --------------------------------------------------------------------------
# Forecast windows
# --------------------------------------------------------------------------


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