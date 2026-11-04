"""
Evaluation of forecast files in the shared format (MODELS.md, "Metrics").

For every forecast file it
1. fills ``y_true`` from ``final/`` (the model scripts leave it empty),
2. builds the seasonal naive forecast for the same origins and steps
   (hourly: same hour one week before, daily: same weekday one week before,
   i.e. the last observed week repeated over the horizon),
3. computes on the MWh scale, over all origins and steps:
   MAE, RMSE, MAPE, MAE skill vs seasonal naive, mean pinball loss over the
   9 quantiles, coverage of the 80 % interval (q0.1 - q0.9),
4. splits MAE / pinball by lead time (daily 7 d: day 1 ... 7; longer horizons,
   if used again: hourly by day, daily 30 d by week 1 ... 4) and by day type
   of the target time.

Day types (the last three overlap with the first two and with each other):
- ``normal_weekday``: Mon - Fri, not a holiday, bridge day or Christmas window,
- ``weekend``: Sat / Sun, not a holiday or Christmas window,
- ``holiday`` (``is_holiday``), ``bridge_day``, ``christmas_new_year``.

Usage (from the project root):

    uv run python src/models/foundation/evaluate.py src/results/forecasts/timesfm3_*.csv
    uv run python src/models/foundation/evaluate.py --naive hourly 24 test   # write a seasonal naive file
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data import (
    DEFAULT_DATA_DIR,
    DEFAULT_FORECAST_DIR,
    DEFAULT_RESULTS_DIR,
    QUANTILE_COLUMNS,
    QUANTILES,
    SEASONAL_PERIOD,
    SeriesFrame,
    TARGET,
    forecasts_to_frame,
    horizon_label,
    load_frame,
    origin_positions,
    write_forecasts,
)

DEFAULT_METRICS_DIR = DEFAULT_RESULTS_DIR / "metrics"


# --------------------------------------------------------------------------
# Seasonal naive
# --------------------------------------------------------------------------


def seasonal_naive(frame: SeriesFrame, positions: np.ndarray, horizon: int) -> np.ndarray:
    """(n_origins, H): the last observed week repeated over the horizon."""
    period = SEASONAL_PERIOD[frame.resolution]
    y = frame.y
    steps = np.arange(horizon)
    idx = positions[:, None] - period + (steps[None, :] % period)
    if (idx < 0).any():
        raise ValueError("an origin has less than one week of history")
    return y[idx]


def naive_forecast_file(frame: SeriesFrame, split: str, horizon: int, out_dir: Path) -> Path:
    positions = origin_positions(frame, split, horizon)
    out = forecasts_to_frame(frame, positions, horizon, seasonal_naive(frame, positions, horizon), None)
    name = f"seasonal_naive_{frame.resolution}_{horizon_label(frame.resolution, horizon)}_{split}"
    meta = {"model": "seasonal naive", "resolution": frame.resolution, "horizon": horizon,
            "split": split, "n_origins": int(len(positions)), "period": SEASONAL_PERIOD[frame.resolution]}
    return write_forecasts(out, out_dir / f"{name}.csv", meta)


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


def _day_types(frame: SeriesFrame, target_time: pd.Series) -> pd.DataFrame:
    """Day-type flags of the target times (joined from final/)."""
    key = frame.timestamp
    if frame.resolution == "daily":
        key = key.dt.strftime("%Y-%m-%d")
    flags = frame.df[["is_holiday", "is_weekday", "is_bridge_day", "is_christmas_new_year"]].astype(bool)
    flags.index = key.to_numpy()
    f = flags.loc[target_time.to_numpy()].reset_index(drop=True)
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
    key = frame.timestamp
    if frame.resolution == "daily":
        key = key.dt.strftime("%Y-%m-%d")
        tt = fc["target_time"].astype(str)
    else:
        tt = pd.to_datetime(fc["target_time"])
    truth = pd.Series(frame.df[TARGET].to_numpy(), index=key.to_numpy())
    fc = fc.copy()
    fc["y_true"] = truth.reindex(tt.to_numpy()).to_numpy()
    if fc["y_true"].isna().any():
        raise ValueError(f"{fc['y_true'].isna().sum()} target times are not in final/")
    return fc


def evaluate_file(path: Path, frames: dict[str, SeriesFrame], data_dir: Path = DEFAULT_DATA_DIR,
                  write_back: bool = True) -> dict:
    """Metrics of one forecast file. Fills y_true in the file when ``write_back``."""
    path = Path(path)
    meta_path = path.with_suffix(".json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    fc = pd.read_csv(path)
    resolution = meta.get("resolution") or ("hourly" if "_hourly_" in path.name else "daily")
    if resolution not in frames:
        frames[resolution] = load_frame(resolution, data_dir)
    frame = frames[resolution]
    horizon = int(fc["step"].max())

    fc = fill_y_true(fc, frame)
    if write_back:
        fc.to_csv(path, index=False)

    # Seasonal naive for exactly the same (origin, step) rows.
    pos_of = pd.Series(np.arange(len(frame.df)), index=frame.timestamp.to_numpy())
    origin_ts = fc["origin"].drop_duplicates()
    origin_ts_parsed = pd.to_datetime(origin_ts)
    positions = pos_of.loc[origin_ts_parsed.to_numpy()].to_numpy()
    naive = pd.DataFrame(seasonal_naive(frame, positions, horizon), index=origin_ts.to_numpy())
    y_naive = naive.to_numpy()[
        pd.Index(origin_ts.to_numpy()).get_indexer(fc["origin"].to_numpy()), fc["step"].to_numpy() - 1
    ]

    y = fc["y_true"].to_numpy(float)
    y_pred = fc["y_pred"].to_numpy(float)
    q_pred = fc[QUANTILE_COLUMNS].to_numpy(float)

    setting = []
    if "features" in meta:
        setting.append(f"features={meta['features']}")
    for key in ("context_length", "context_days"):
        if key in meta:
            setting.append(f"ctx={meta[key]}")
    if meta.get("use_znorm"):
        setting.append("znorm")
    result = {"file": path.name, **{k: meta.get(k) for k in ("model", "experiment", "split")},
              "setting": " ".join(setting), "resolution": resolution, "horizon": horizon,
              "n_origins": int(len(origin_ts)), "weather_variant": meta.get("weather_variant")}
    result["overall"] = {**point_metrics(y, y_pred, y_naive), **quantile_metrics(y, q_pred)}

    lead = _lead_groups(resolution, horizon, fc["step"].to_numpy())
    if lead is not None:
        label, groups = lead
        result[f"by_{label}"] = {
            int(g): {**point_metrics(y[m], y_pred[m], y_naive[m]), **quantile_metrics(y[m], q_pred[m])}
            for g in np.unique(groups)
            for m in [groups == g]
        }

    tt = pd.to_datetime(fc["target_time"]) if resolution == "hourly" else fc["target_time"].astype(str)
    types = _day_types(frame, tt)
    result["by_day_type"] = {
        t: ({**point_metrics(y[m], y_pred[m], y_naive[m]), **quantile_metrics(y[m], q_pred[m])} if m.any() else None)
        for t in types.columns
        for m in [types[t].to_numpy()]
    }
    return result


def summary_row(res: dict) -> dict:
    o = res["overall"]
    return {
        "file": res["file"], "model": res.get("model"), "experiment": res.get("experiment") or "baseline",
        "setting": res.get("setting", ""), "resolution": res["resolution"], "horizon": res["horizon"],
        "split": res.get("split"),
        "n_origins": res["n_origins"], "MAE": o["MAE"], "RMSE": o["RMSE"], "MAPE_%": o["MAPE_%"],
        "MAE_skill": o.get("MAE_skill"), "pinball": o["pinball"], "coverage80_%": o["coverage80_%"],
    }


def evaluate_files(paths, metrics_dir: Path = DEFAULT_METRICS_DIR, summary_name: str | None = None,
                   data_dir: Path = DEFAULT_DATA_DIR, frames: dict | None = None) -> pd.DataFrame:
    frames = {} if frames is None else frames
    metrics_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in paths:
        res = evaluate_file(Path(path), frames, data_dir)
        (metrics_dir / f"{Path(path).stem}.json").write_text(json.dumps(res, indent=2))
        rows.append(summary_row(res))
    summary = pd.DataFrame(rows)
    if summary_name:
        summary.to_csv(metrics_dir / summary_name, index=False)
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="*", type=Path, help="forecast CSV files")
    p.add_argument("--naive", nargs=3, metavar=("RESOLUTION", "HORIZON", "SPLIT"),
                   help="write the seasonal naive forecast file instead")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--forecast-dir", type=Path, default=DEFAULT_FORECAST_DIR)
    p.add_argument("--metrics-dir", type=Path, default=DEFAULT_METRICS_DIR)
    p.add_argument("--summary", default="summary.csv", help="summary CSV name in the metrics folder")
    args = p.parse_args()

    if args.naive:
        res, h, split = args.naive
        naive_forecast_file(load_frame(res, args.data_dir), split, int(h), args.forecast_dir)
        return
    if not args.files:
        p.error("give forecast files or --naive")
    summary = evaluate_files(args.files, args.metrics_dir, args.summary, args.data_dir)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(summary.drop(columns=["file"]).to_string(index=False))


if __name__ == "__main__":
    main()
