"""
Scoring of forecast files in the shared format (MODELS.md, "Metrics"), for any model.

For every forecast file it
1. fills ``y_true`` from ``final/`` (some model scripts leave it empty),
2. builds the seasonal naive forecast for the same origins and steps
   (hourly: same hour one week before, daily: same weekday one week before,
   i.e. the last observed week repeated over the horizon),
3. computes on the MWh scale, over all origins and steps:
   MAE, RMSE, MAPE, MAE skill vs seasonal naive, mean pinball loss over the
   9 quantiles, coverage of the 80 % interval (q0.1 - q0.9); the last two are
   None for point-forecast models (quantile columns all NaN),
4. splits MAE / pinball by lead time (daily 7 d: day 1 ... 7; longer horizons:
   hourly by day, daily 30 d by week 1 ... 4) and by day type of the target time.

Day types (the last three overlap with the first two and with each other):
- ``normal_weekday``: Mon - Fri, not a holiday, bridge day or Christmas window,
- ``weekend``: Sat / Sun, not a holiday or Christmas window,
- ``holiday`` (``is_holiday``), ``bridge_day``, ``christmas_new_year``.

This module is a library: the model scripts use it (e.g. validation-based
selection) and ``src.analysis.evaluate`` is its command line.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.dataset import (
    QUANTILE_COLUMNS,
    QUANTILES,
    SEASONAL_PERIOD,
    TARGET,
    SeriesFrame,
    forecasts_to_frame,
    horizon_label,
    load_frame,
    origin_positions,
    read_meta,
    time_key,
    write_forecasts,
)
from src.common.paths import DATA_DIR, metrics_path_of, model_of

NAIVE_MODEL_NAME = "seasonal naive"  # "model" in the sidecar of a seasonal naive file


# --------------------------------------------------------------------------
# Seasonal naive
# --------------------------------------------------------------------------


def seasonal_naive(frame: SeriesFrame, positions: np.ndarray, horizon: int) -> np.ndarray:
    """(n_origins, H): the last observed week repeated over the horizon."""
    period = SEASONAL_PERIOD[frame.resolution]
    steps = np.arange(horizon)
    idx = positions[:, None] - period + (steps[None, :] % period)
    if (idx < 0).any():
        raise ValueError("an origin has less than one week of history")
    return frame.y[idx]


def naive_forecast_file(frame: SeriesFrame, split: str, horizon: int, out_dir: Path) -> Path:
    """Write the seasonal naive forecast file of one resolution, horizon and split."""
    positions = origin_positions(frame, split, horizon)
    out = forecasts_to_frame(frame, positions, horizon, seasonal_naive(frame, positions, horizon), None)
    name = f"seasonal_naive_{frame.resolution}_{horizon_label(frame.resolution, horizon)}_{split}"
    meta = {"model": NAIVE_MODEL_NAME, "label": "Seasonal naive", "resolution": frame.resolution,
            "horizon": horizon, "split": split, "n_origins": int(len(positions)),
            "period": SEASONAL_PERIOD[frame.resolution]}
    return write_forecasts(out, Path(out_dir) / f"{name}.csv", meta)


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def pinball(y: np.ndarray, q_pred: np.ndarray) -> np.ndarray:
    """Pinball loss per row and quantile, (n, 9)."""
    diff = y[:, None] - q_pred
    qs = np.asarray(QUANTILES)[None, :]
    return np.maximum(qs * diff, (qs - 1) * diff)


def point_metrics(y: np.ndarray, y_pred: np.ndarray, y_naive: np.ndarray | None = None) -> dict:
    err = y - y_pred
    out = {
        "n": int(len(y)),
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err**2))),
        "MAPE_%": float(100 * np.mean(np.abs(err) / np.abs(y))),
        "bias": float(np.mean(-err)),  # forecast minus actual: > 0 = over-forecast
    }
    if y_naive is not None:
        mae_naive = float(np.mean(np.abs(y - y_naive)))
        out["MAE_naive"] = mae_naive
        out["MAE_skill"] = 1 - out["MAE"] / mae_naive
    return out


def quantile_metrics(y: np.ndarray, q_pred: np.ndarray) -> dict:
    if np.isnan(q_pred).all():
        return {"pinball": None, "coverage80_%": None}
    return {
        "pinball": float(pinball(y, q_pred).mean()),
        "coverage80_%": float(100 * np.mean((y >= q_pred[:, 0]) & (y <= q_pred[:, -1]))),
    }


def day_types(frame: SeriesFrame, target_keys: np.ndarray) -> pd.DataFrame:
    """Day-type flags of the target times (``time_key`` values), joined from final/."""
    flags = frame.df[["is_holiday", "is_weekday", "is_bridge_day", "is_christmas_new_year"]].astype(bool)
    flags.index = frame.time_keys()
    f = flags.loc[target_keys].reset_index(drop=True)
    special = f["is_holiday"] | f["is_bridge_day"] | f["is_christmas_new_year"]
    return pd.DataFrame(
        {
            "normal_weekday": f["is_weekday"] & ~special,
            "weekend": ~f["is_weekday"] & ~f["is_holiday"] & ~f["is_christmas_new_year"],
            "holiday": f["is_holiday"],
            "bridge_day": f["is_bridge_day"],
            "christmas_new_year": f["is_christmas_new_year"],
        }
    )


def _lead_groups(resolution: str, horizon: int, step: np.ndarray) -> tuple[str, np.ndarray] | None:
    if resolution == "hourly" and horizon > 24:
        return "day", np.ceil(step / 24).astype(int)
    if resolution == "daily" and horizon > 7:
        return "week", np.minimum(np.ceil(step / 7), 4).astype(int)
    if resolution == "daily" and horizon > 1:
        return "day", step.astype(int)
    return None


def fill_y_true(fc: pd.DataFrame, frame: SeriesFrame) -> pd.DataFrame:
    """``y_true`` of every row from final/ (whatever the file held before)."""
    truth = pd.Series(frame.df[TARGET].to_numpy(), index=frame.time_keys())
    fc = fc.copy()
    fc["y_true"] = truth.reindex(time_key(fc["target_time"], frame.resolution)).to_numpy()
    if fc["y_true"].isna().any():
        raise ValueError(f"{fc['y_true'].isna().sum()} target times are not in final/")
    return fc


def origin_rows(fc: pd.DataFrame, frame: SeriesFrame) -> np.ndarray:
    """Row position in ``frame`` of the origin of every forecast row."""
    pos_of = pd.Series(np.arange(len(frame.df)), index=frame.time_keys())
    keys = time_key(fc["origin"], frame.resolution)
    pos = pos_of.reindex(keys).to_numpy()
    if np.isnan(pos).any():
        raise ValueError(f"{int(np.isnan(pos).sum())} origins are not in final/")
    return pos.astype(int)


def naive_rows(fc: pd.DataFrame, frame: SeriesFrame) -> np.ndarray:
    """Seasonal naive forecast of every (origin, step) row of a forecast file."""
    p = origin_rows(fc, frame)
    step = fc["step"].to_numpy()
    period = SEASONAL_PERIOD[frame.resolution]
    idx = p - period + (step - 1) % period
    if (idx < 0).any():
        raise ValueError("an origin has less than one week of history")
    return frame.y[idx]


def resolution_of(path: Path, meta: dict) -> str:
    return meta.get("resolution") or ("hourly" if "_hourly_" in Path(path).name else "daily")


def _frame(frames: dict, resolution: str, data_dir: Path) -> SeriesFrame:
    if resolution not in frames:
        frames[resolution] = load_frame(resolution, data_dir)
    return frames[resolution]


def _setting(meta: dict) -> str:
    setting = []
    if "features" in meta:
        setting.append(f"features={meta['features']}")
    for key in ("context_length", "context_days"):
        if key in meta:
            setting.append(f"ctx={meta[key]}")
    if meta.get("use_znorm"):
        setting.append("znorm")
    return " ".join(setting)


def evaluate_file(path: Path, frames: dict | None = None, data_dir: Path = DATA_DIR,
                  write_back: bool = True) -> dict:
    """Metrics of one forecast file. Fills y_true in the file when ``write_back``."""
    frames = {} if frames is None else frames
    path = Path(path)
    meta = read_meta(path)
    fc = pd.read_csv(path)
    resolution = resolution_of(path, meta)
    frame = _frame(frames, resolution, data_dir)
    horizon = int(meta.get("horizon") or fc["step"].max())

    fc = fill_y_true(fc, frame)
    if write_back:
        fc.to_csv(path, index=False)

    y_naive = naive_rows(fc, frame)
    y = fc["y_true"].to_numpy(float)
    y_pred = fc["y_pred"].to_numpy(float)
    q_pred = fc[QUANTILE_COLUMNS].to_numpy(float) if set(QUANTILE_COLUMNS) <= set(fc) else \
        np.full((len(fc), len(QUANTILES)), np.nan)

    is_naive = meta.get("model") == NAIVE_MODEL_NAME or path.stem.startswith("seasonal_naive")
    result = {
        "file": path.name, "model_dir": model_of(path),
        **{k: meta.get(k) for k in ("model", "label", "experiment", "split")},
        "is_naive": is_naive, "setting": _setting(meta), "resolution": resolution, "horizon": horizon,
        "n_origins": int(fc["origin"].nunique()), "weather_variant": meta.get("weather_variant"),
    }
    result["overall"] = {**point_metrics(y, y_pred, y_naive), **quantile_metrics(y, q_pred)}

    lead = _lead_groups(resolution, horizon, fc["step"].to_numpy())
    if lead is not None:
        label, groups = lead
        result[f"by_{label}"] = {
            int(g): {**point_metrics(y[m], y_pred[m], y_naive[m]), **quantile_metrics(y[m], q_pred[m])}
            for g in np.unique(groups)
            for m in [groups == g]
        }

    types = day_types(frame, time_key(fc["target_time"], resolution))
    result["by_day_type"] = {
        t: ({**point_metrics(y[m], y_pred[m], y_naive[m]), **quantile_metrics(y[m], q_pred[m])} if m.any() else None)
        for t in types.columns
        for m in [types[t].to_numpy()]
    }
    return result


def summary_row(res: dict) -> dict:
    o = res["overall"]
    experiment = res.get("experiment") or ("baseline" if res.get("is_naive") else "")
    return {
        "file": res["file"], "model_dir": res.get("model_dir"), "model": res.get("model"),
        "experiment": experiment, "setting": res.get("setting", ""), "resolution": res["resolution"],
        "horizon": res["horizon"], "split": res.get("split"),
        "n_origins": res["n_origins"], "MAE": o["MAE"], "RMSE": o["RMSE"], "MAPE_%": o["MAPE_%"],
        "bias": o.get("bias"), "MAE_skill": o.get("MAE_skill"), "pinball": o["pinball"],
        "coverage80_%": o["coverage80_%"],
    }


def evaluate_files(paths, metrics_dir: Path | None = None, summary_name: str | None = None,
                   data_dir: Path = DATA_DIR, frames: dict | None = None) -> pd.DataFrame:
    """Evaluate forecast files and write one metrics JSON each.

    ``metrics_dir`` None: next to the forecasts, ``results/<model>/metrics/``.
    ``summary_name``: also write the summary table (in ``metrics_dir``, or the
    metrics folder of the first file).
    """
    frames = {} if frames is None else frames
    paths = [Path(p) for p in paths]
    rows = []
    for path in paths:
        path = Path(path)
        res = evaluate_file(path, frames, data_dir)
        out = (Path(metrics_dir) / f"{path.stem}.json") if metrics_dir else metrics_path_of(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=2))
        rows.append(summary_row(res))
    summary = pd.DataFrame(rows)
    if summary_name and rows:
        target = Path(metrics_dir) if metrics_dir else metrics_path_of(Path(paths[0])).parent
        target.mkdir(parents=True, exist_ok=True)
        summary.to_csv(target / summary_name, index=False)
    return summary