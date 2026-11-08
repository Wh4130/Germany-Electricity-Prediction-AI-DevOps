"""
TabICLForecaster on the daily data: experiment F6 (challenger, 1 d and 7 d).

Forecasting as tabular regression: one row per day, the target is
``actual_consumption``, the history rows are the "training set" of an
in-context learner (no gradient training). Raw MWh go in, ``TabICLRegressor``
standardises the target on the context rows and transforms back.

Two settings are compared on the validation year (FOUNDATION.md, "TabICLForecaster"):

| Option     | Values                                                                 |
|------------|------------------------------------------------------------------------|
| features   | ``ours``: all our calendar columns + ``temporal_features=["index", "periodic"]`` |
|            | ``default``: TabICL's default time features (index, datetime, periodic) + only our holiday columns |
| context    | ``all`` (every day before the origin) or a number of days, e.g. ``730`` (last 2 years) |

Covariates (both feature sets): solar capacity, daylight, weather (variant A,
observed), and the past-only columns. TabICL has no past-only slot, so the
future rows of a past-only column get the **last value known at the origin**
(forward fill), which does not leak.

Every origin is passed as its own ``item_id`` in one ``predict_df`` call, so
TabICL handles a chunk of origins in one go (one in-context fit per origin).

Examples (from the project root):

    uv run python src/models/foundation/tabicl_forecaster.py --split val --features ours --context all
    uv run python src/models/foundation/tabicl_forecaster.py --split test --features default --context 730
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from data import (
    DEFAULT_DATA_DIR,
    DEFAULT_FORECAST_DIR,
    HORIZONS,
    QUANTILES,
    SeriesFrame,
    covariate_set,
    forecasts_to_frame,
    horizon_label,
    load_frame,
    origin_positions,
    write_forecasts,
)

FEATURE_SETS = {
    # name: (calendar columns, TabICL temporal_features; None = package default)
    "ours": ("full", ["index", "periodic"]),
    "default": ("holidays", None),
}


def parse_context(value: str) -> int | None:
    return None if str(value).lower() == "all" else int(value)


def run_name(horizon: int, split: str, features: str, context_days: int | None) -> str:
    ctx = "all" if context_days is None else str(context_days)
    return f"tabicl_{features}_daily_{horizon_label('daily', horizon)}_ctx{ctx}_{split}"


def build_frames(
    frame: SeriesFrame,
    positions: np.ndarray,
    horizon: int,
    known_cols: list[str],
    past_cols: list[str],
    context_days: int | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Long context / future DataFrames, one ``item_id`` per origin.

    The future DataFrame has no target column at all. Past-only columns are
    forward-filled from the last context row in the future rows.
    """
    ts = frame.timestamp.to_numpy()
    y = frame.y
    known = frame.matrix(known_cols)
    past = frame.matrix(past_cols)

    ctx_parts, fut_parts = [], []
    for pos in positions:
        start = 0 if context_days is None else max(0, pos - context_days)
        ctx = pd.DataFrame(known[start:pos], columns=known_cols)
        ctx[past_cols] = past[start:pos]
        ctx.insert(0, "target", y[start:pos])
        ctx.insert(0, "timestamp", ts[start:pos])
        ctx.insert(0, "item_id", int(pos))
        ctx_parts.append(ctx)

        fut = pd.DataFrame(known[pos : pos + horizon], columns=known_cols)
        fut[past_cols] = np.repeat(past[pos - 1 : pos], horizon, axis=0)  # last value known at the origin
        fut.insert(0, "timestamp", ts[pos : pos + horizon])
        fut.insert(0, "item_id", int(pos))
        fut_parts.append(fut)
    return pd.concat(ctx_parts, ignore_index=True), pd.concat(fut_parts, ignore_index=True)


def forecast(
    frame: SeriesFrame,
    split: str,
    horizon: int,
    features: str = "ours",
    context_days: int | None = None,
    tabicl_config: dict | None = None,
    chunk_size: int = 32,
    max_origins: int | None = None,
):
    """Forecasts for all origins of one split. Returns (forecast DataFrame, meta dict)."""
    from tabicl import TabICLForecaster

    if frame.resolution != "daily":
        raise ValueError("TabICLForecaster is planned for the daily data only")
    calendar, temporal_features = FEATURE_SETS[features]
    cov = covariate_set("daily", horizon, calendar=calendar)
    positions = origin_positions(frame, split, horizon)
    if max_origins is not None:
        positions = positions[:max_origins]

    forecaster = TabICLForecaster(
        max_context_length=4096,  # > 2192 daily rows, so "all" really is all
        temporal_features=temporal_features,
        point_estimate="median",  # y_pred = median, like the other models
        tabicl_config=tabicl_config or {},
    )

    t0 = time.time()
    y_pred = np.empty((len(positions), horizon))
    q_pred = np.empty((len(positions), horizon, len(QUANTILES)))
    for start in range(0, len(positions), chunk_size):
        chunk = positions[start : start + chunk_size]
        ctx_df, fut_df = build_frames(frame, chunk, horizon, cov.known, cov.past_only, context_days)
        pred = forecaster.predict_df(ctx_df, future_df=fut_df, quantiles=list(QUANTILES))
        for i, pos in enumerate(chunk):
            p = pred.loc[int(pos)].sort_index()
            if len(p) != horizon:
                raise RuntimeError(f"origin {pos}: got {len(p)} forecast rows, expected {horizon}")
            y_pred[start + i] = p["target"].to_numpy()
            q_pred[start + i] = p[QUANTILES].to_numpy()
        print(f"[tabicl] daily {horizon_label('daily', horizon)} {split} {features} "
              f"ctx={'all' if context_days is None else context_days}: "
              f"{min(start + chunk_size, len(positions))}/{len(positions)} origins")
    runtime = time.time() - t0

    # Quantiles of an ensemble are not always ordered; sort them like TimesFM-3 does.
    q_pred = np.sort(q_pred, axis=-1)

    out_df = forecasts_to_frame(frame, positions, horizon, y_pred, q_pred)
    meta = {
        "model": "TabICLForecaster",
        "experiment": "F6",
        "variant": "zero-shot (in-context learning)",
        "resolution": "daily",
        "horizon": horizon,
        "split": split,
        "n_origins": int(len(positions)),
        "features": features,
        "temporal_features": temporal_features or ["index", "datetime", "periodic"],
        "context_days": "all" if context_days is None else int(context_days),
        "covariates_known": cov.known,
        "covariates_past_only_ffill": cov.past_only,
        "weather_variant": "A (observed, oracle)",
        "y_pred": "median",
        "tabicl_config": tabicl_config or {},
        "runtime_seconds": round(runtime, 1),
    }
    return out_df, meta


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", choices=["val", "test"], required=True)
    p.add_argument("--horizons", type=int, nargs="+", default=list(HORIZONS["daily"]))
    p.add_argument("--features", choices=list(FEATURE_SETS), default="ours")
    p.add_argument("--context", default="all", help="'all' or a number of days (e.g. 730)")
    p.add_argument("--n-estimators", type=int, default=None, help="TabICLRegressor ensemble size (default 8)")
    p.add_argument("--model-path", default=None, help="local TabICL checkpoint (default: download from HF)")
    p.add_argument("--device", default=None)
    p.add_argument("--max-origins", type=int, default=None, help="only the first N origins (smoke test)")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_FORECAST_DIR)
    args = p.parse_args()

    config = {}
    if args.n_estimators is not None:
        config["n_estimators"] = args.n_estimators
    if args.model_path is not None:
        config["model_path"] = args.model_path
    if args.device is not None:
        config["device"] = args.device

    frame = load_frame("daily", args.data_dir)
    context_days = parse_context(args.context)
    for h in args.horizons:
        out, meta = forecast(frame, args.split, h, args.features, context_days, config, max_origins=args.max_origins)
        write_forecasts(out, args.out_dir / f"{run_name(h, args.split, args.features, context_days)}.csv", meta)


if __name__ == "__main__":
    main()
