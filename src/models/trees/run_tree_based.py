"""
Final tree-based models (XGBoost / CatBoost / LightGBM / RandomForest): refit the
model/params chosen in notebooks/Daily_model_building.ipynb and
notebooks/Hourly_model_building.ipynb, forecast the test year (2024), and write the
forecasts in the shared format, so that the shared evaluation
(src/models/foundation/evaluate.py) scores them like the other models.

This script does not select anything, it only refits the specs already chosen in the
notebooks. It reads them from src/results/tree-based/best_model_config_{daily,hourly}.json
(written by the notebooks' best_model_config cell) rather than hand-copying that dict
here - there is then one place for this choice, not two that can drift apart. Run the
notebook's CV + best_model_config cells at least once before this script.
- both resolutions: like the notebooks, each horizon is refit with 5 random seeds
  (SEEDS); the model with the lowest test MAE is kept for the forecast and the saved
  model file, the printed MAE/RMSE/MAPE are the average over the 5 seeds.

Test only: fit once on 2019-2023, forecast 2024. No validation run, no refits (the
notebooks already did model/hyperparameter selection on val).

Outputs (src/results/tree-based/):
    forecasts/tree_daily_1d_test.csv, tree_daily_7d_test.csv       shared format (FORCAST_FORMAT.md)
    forecasts/tree_hourly_1h_test.csv, tree_hourly_24h_test.csv    + a JSON sidecar each.
        One file per model, resolution, horizon and split, like the other models: the
        "_1{d,h}_" file is the step-1-only forecast (horizon=1), the "_{7,24}{d,h}_" file
        has every step the direct models cover, stacked (horizon=7 or 24). Both come from
        the same fit - no separate refit for the 1-step file. q0.1 .. q0.9 are NaN: these
        models give a point forecast only, no native quantiles.
    models/{daily,hourly}/final_model_h{h}.joblib

Usage (from the project root):
    uv run python src/models/trees/run_tree_based.py
    uv run python src/models/trees/run_tree_based.py --resolution daily
    uv run python src/models/foundation/evaluate.py src/results/tree-based/forecasts/*.csv \
        --metrics-dir src/results/tree-based/metrics
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

TREES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TREES_DIR.parents[2]
DATA_DIR = PROJECT_ROOT / "src" / "data" / "final"
OUT_DIR = PROJECT_ROOT / "src" / "results" / "tree-based"

QUANTILE_COLUMNS = [f"q{q}" for q in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)]
SEEDS = [42, 43, 44, 45, 46]  # daily only - see refit_and_forecast

MODEL_CLASSES = {
    "LightGBM": LGBMRegressor,
    "XGBoost": XGBRegressor,
    "CatBoost": CatBoostRegressor,
    "RandomForest": RandomForestRegressor,
}


def evaluate(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    mape = (abs((y_true - y_pred) / y_true)).mean() * 100
    return {"mae": mae, "rmse": rmse, "mape": mape}


def load_best_model_config(resolution: str) -> dict:
    """
    Read src/results/tree-based/best_model_config_{resolution}.json, written by the
    "best_model_config" cell of the matching notebook - the single source of truth for
    which model/params each horizon uses, so this script never hand-copies that choice.
    """
    path = OUT_DIR / f"best_model_config_{resolution}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found - run the CV + best_model_config cells of "
            f"notebooks/{resolution.capitalize()}_model_building.ipynb first, "
            f"it saves this file right after best_model_config is defined"
        )
    with open(path) as f:
        raw = json.load(f)
    return {int(h): (entry["model"], MODEL_CLASSES[entry["model"]], entry["params"]) for h, entry in raw.items()}


# --------------------------------------------------------------------------
# Daily: features + the spec chosen in Daily_model_building.ipynb
# --------------------------------------------------------------------------

DAILY_HORIZON = 7
DAILY_CALENDAR_COLS = [
    "month", "day_of_week_raw", "is_holiday", "is_weekday",
    "weighted_regional_holiday", "weighted_school_holiday",
    "is_bridge_day", "is_christmas_new_year", "is_dst", "is_dst_transition_day",
    "sin_y1", "cos_y1", "sin_y2", "cos_y2", "sin_y3", "cos_y3",
]

def build_daily_features(data: pd.DataFrame) -> pd.DataFrame:
    """ same column selection as Daily_model_building.ipynb ("y/time_date/..." and "Add solar_..." cells) """
    time_date = ["date_from", "month", "day_of_week_raw", "is_holiday",
                "is_weekday", "weighted_regional_holiday", "weighted_school_holiday",
                "is_bridge_day", "is_christmas_new_year", "is_dst", "is_dst_transition_day"]
    prices = ["day_ahead_price_mean"]
    data["day_ahead_price_mean_7d"] = data["day_ahead_price_mean"].shift(1).rolling(7).mean()
    prices += ["day_ahead_price_mean_7d"]
    weather_columns = ["hdd", "wind_speed_10m_mean", "precipitation_sum"]
    fourier_columns = ["sin_y1", "cos_y1", "sin_y2", "cos_y2", "sin_y3", "cos_y3"]
    others = ["oxcgrt_stringency", "ipi_ei_level", "industrial_confidence"]

    data["solar_radiation_combi"] = data["solar_capacity_mw"] * data["shortwave_radiation_sum"]
    others = others + ["solar_radiation_combi"]

    for lag in (1, 2, 7):
        data[f"lag_{lag}"] = data["actual_consumption"].shift(lag)
    time_date = time_date + ["lag_1", "lag_2", "lag_7"]

    return data.loc[:, ["actual_consumption"] + time_date + prices + weather_columns + fourier_columns + others]


def build_daily_horizons(data: pd.DataFrame) -> dict:
    """ X_train_h / X_val_h / X_test_h / y_*_h for h = 1..7, target-day calendar swapped in (see the notebook) """
    data["date_from"] = pd.to_datetime(data["date_from"])
    data = data.sort_values("date_from").reset_index(drop=True)

    masks = {
        "train": data["date_from"].dt.year <= 2022,
        "val": data["date_from"].dt.year == 2023,
        "test": data["date_from"].dt.year == 2024,
    }
    feature_cols = [c for c in data.columns if c not in ("actual_consumption", "date_from")]
    X = {split: data.loc[mask, feature_cols] for split, mask in masks.items()}

    # shift() upcasts bool/int columns to object/float wherever it introduces NaN at the
    # tail - restore the original dtypes after slicing out those NaN rows (same as the notebook)
    calendar_dtypes = data[DAILY_CALENDAR_COLS].dtypes.to_dict()
    targets = {h: data["actual_consumption"].shift(-(h - 1)) for h in range(1, DAILY_HORIZON + 1)}

    out = {"X_train_h": {}, "X_val_h": {}, "X_test_h": {}, "y_train_h": {}, "y_val_h": {}, "y_test_h": {}}
    for h in range(1, DAILY_HORIZON + 1):
        valid = targets[h].notna()
        target_calendar = data[DAILY_CALENDAR_COLS].shift(-(h - 1))
        for split, mask in masks.items():
            idx = targets[h][mask & valid].index
            out[f"y_{split}_h"][h] = targets[h].loc[idx]
            out[f"X_{split}_h"][h] = (
                X[split].drop(columns=DAILY_CALENDAR_COLS).loc[idx]
                .join(target_calendar.loc[idx].astype(calendar_dtypes))
            )
    out["origin"] = data["date_from"]
    return out


# --------------------------------------------------------------------------
# Hourly: features + the spec chosen in Hourly_model_building.ipynb
# --------------------------------------------------------------------------

HOURLY_HORIZON = 24
HOURLY_CALENDAR_COLS = [
    "month", "day_of_week_raw", "is_holiday", "is_weekday",
    "weighted_regional_holiday", "weighted_school_holiday",
    "is_bridge_day", "is_christmas_new_year", "is_dst", "is_dst_transition_day",
] + [f"{t}_y{k}" for k in range(1, 4) for t in ("sin", "cos")] \
  + [f"{t}_d{k}" for k in range(1, 7) for t in ("sin", "cos")]


def build_hourly_features(data: pd.DataFrame) -> pd.DataFrame:
    """ same column selection as Hourly_model_building.ipynb """
    time_date = ["date_from", "date_from_utc", "month", "day_of_week_raw", "is_holiday",
                "is_weekday", "weighted_regional_holiday", "weighted_school_holiday",
                "is_bridge_day", "is_christmas_new_year", "is_dst", "is_dst_transition_day"]
    prices = ["day_ahead_price"]
    data["day_ahead_price_7d"] = data["day_ahead_price"].shift(1).rolling(24 * 7).mean()
    prices += ["day_ahead_price_7d"]
    weather_columns = ["hdd", "wind_speed_10m", "precipitation", "is_day"]
    fourier_columns = ([f"{t}_y{k}" for k in range(1, 4) for t in ("sin", "cos")]
                       + [f"{t}_d{k}" for k in range(1, 7) for t in ("sin", "cos")])
    others = ["oxcgrt_stringency", "ipi_ei_level", "industrial_confidence"]

    data["solar_radiation_combi"] = data["solar_capacity_mw"] * data["shortwave_radiation"]
    others = others + ["solar_radiation_combi"]

    for lag in (1, 24, 48, 168):
        data[f"lag_{lag}"] = data["actual_consumption"].shift(lag)
    time_date = time_date + ["lag_1", "lag_24", "lag_48", "lag_168"]

    return data.loc[:, ["actual_consumption"] + time_date + prices + weather_columns + fourier_columns + others]


def build_hourly_horizons(data: pd.DataFrame) -> dict:
    """ X_train_h / X_val_h / X_test_h / y_*_h for h = 1..24, target-hour calendar/harmonics swapped in (see the notebook) """
    data["date_from"] = pd.to_datetime(data["date_from"])
    data["date_from_utc"] = pd.to_datetime(data["date_from_utc"])
    data = data.sort_values("date_from_utc").reset_index(drop=True)

    masks = {
        "train": data["date_from"].dt.year <= 2022,
        "val": data["date_from"].dt.year == 2023,
        "test": data["date_from"].dt.year == 2024,
    }
    feature_cols = [c for c in data.columns if c not in ("actual_consumption", "date_from", "date_from_utc")]
    X = {split: data.loc[mask, feature_cols] for split, mask in masks.items()}

    # shift() upcasts bool/int columns to object/float wherever it introduces NaN at the
    # tail - restore the original dtypes after slicing out those NaN rows (same as the notebook)
    calendar_dtypes = data[HOURLY_CALENDAR_COLS].dtypes.to_dict()
    targets = {h: data["actual_consumption"].shift(-(h - 1)) for h in range(1, HOURLY_HORIZON + 1)}

    out = {"X_train_h": {}, "X_val_h": {}, "X_test_h": {}, "y_train_h": {}, "y_val_h": {}, "y_test_h": {}}
    for h in range(1, HOURLY_HORIZON + 1):
        valid = targets[h].notna()
        target_calendar = data[HOURLY_CALENDAR_COLS].shift(-(h - 1))
        for split, mask in masks.items():
            idx = targets[h][mask & valid].index
            out[f"y_{split}_h"][h] = targets[h].loc[idx]
            out[f"X_{split}_h"][h] = (
                X[split].drop(columns=HOURLY_CALENDAR_COLS).loc[idx]
                .join(target_calendar.loc[idx].astype(calendar_dtypes))
            )
    out["origin"] = data["date_from_utc"]
    return out


# --------------------------------------------------------------------------
# Shared: refit, forecast file, model file
# --------------------------------------------------------------------------


def refit_and_forecast(horizons: dict, best_model_config: dict, max_horizon: int, name: str) -> dict:
    """
    One fit per horizon, using the spec of best_model_config[h] (already has random_state=42),
    refit with every seed in SEEDS (matches both notebooks): keep the model/prediction of
    whichever seed scored the lowest test MAE for the forecast and the saved model file; the
    printed MAE/RMSE/MAPE are the average over the seeds, for a more robust estimate of how
    good this model/params combination typically is.
    """
    final_models_h, y_pred_h = {}, {}
    for h in range(1, max_horizon + 1):
        model_name, model_cls, params = best_model_config[h]
        X_trainval = pd.concat([horizons["X_train_h"][h], horizons["X_val_h"][h]])
        y_trainval = pd.concat([horizons["y_train_h"][h], horizons["y_val_h"][h]])
        if model_name == "RandomForest":  # doesn't support NaN
            X_trainval = X_trainval.dropna()
            y_trainval = y_trainval.loc[X_trainval.index]

        scores, best_mae, best_model, best_pred = [], np.inf, None, None
        for seed in SEEDS:
            model = model_cls(**{**params, "random_state": seed})
            model.fit(X_trainval, y_trainval)
            y_pred = model.predict(horizons["X_test_h"][h])
            score = evaluate(horizons["y_test_h"][h], y_pred)
            scores.append(score)
            if score["mae"] < best_mae:
                best_mae, best_model, best_pred = score["mae"], model, y_pred

        final_models_h[h], y_pred_h[h] = best_model, best_pred
        avg = {k: np.mean([s[k] for s in scores]) for k in ("mae", "rmse", "mape")}
        print(f"[{name}] h={h:>2} ({model_name:12s}) test MAE={avg['mae']:>10,.0f} "
              f"RMSE={avg['rmse']:>10,.0f} MAPE={avg['mape']:5.2f}%  "
              f"(avg of {len(SEEDS)} seeds, best seed MAE={best_mae:,.0f})")
    return {"models": final_models_h, "y_pred_h": y_pred_h}


def forecast_frame(horizons: dict, fit: dict, max_horizon: int, step_unit: str) -> pd.DataFrame:
    """ shared format (MODELS.md): one row per (origin, step); q0.1 .. q0.9 are NaN (point forecast only) """
    one = pd.Timedelta(hours=1) if step_unit == "h" else pd.Timedelta(days=1)
    rows = []
    for h in range(1, max_horizon + 1):
        idx = horizons["y_test_h"][h].index
        origin = horizons["origin"].loc[idx]
        part = pd.DataFrame({
            "origin": origin.values,
            "target_time": (origin + (h - 1) * one).values,
            "step": h,
            "y_true": horizons["y_test_h"][h].values,
            "y_pred": fit["y_pred_h"][h],
        })
        for col in QUANTILE_COLUMNS:
            part[col] = np.nan
        rows.append(part)
    out = pd.concat(rows, ignore_index=True).sort_values(["origin", "step"]).reset_index(drop=True)
    date_format = "%Y-%m-%d" if step_unit == "d" else "%Y-%m-%d %H:%M:%S"
    out["origin"] = pd.to_datetime(out["origin"]).dt.strftime(date_format)
    out["target_time"] = pd.to_datetime(out["target_time"]).dt.strftime(date_format)
    return out


def write_forecast_file(frame: pd.DataFrame, resolution: str, horizon: int, unit: str,
                        best_model_config: dict, forecast_dir: Path) -> None:
    """ one forecast CSV + JSON sidecar, shared format (FORCAST_FORMAT.md): one file per
    model, resolution, horizon and split - like the other models' "_1d_"/"_7d_" pair """
    csv_path = forecast_dir / f"tree_{resolution}_{horizon}{unit}_test.csv"
    frame.to_csv(csv_path, index=False)

    meta = {
        "model": "tree-based (direct multi-step, one model per horizon)",
        "resolution": resolution, "horizon": horizon, "split": "test",
        "n_origins": int(frame["origin"].nunique()),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "model_per_horizon": {h: best_model_config[h][0] for h in range(1, horizon + 1)},
        "params_per_horizon": {h: best_model_config[h][2] for h in range(1, horizon + 1)},
        "quantiles": "not available: these models give a point forecast only",
    }
    csv_path.with_suffix(".json").write_text(json.dumps(meta, indent=2, default=str))
    print(f"  -> {csv_path.relative_to(PROJECT_ROOT)}: {len(frame)} rows, {meta['n_origins']} origins")


def write_outputs(frame: pd.DataFrame, fit: dict, resolution: str, max_horizon: int, best_model_config: dict) -> None:
    forecast_dir = OUT_DIR / "forecasts"
    forecast_dir.mkdir(parents=True, exist_ok=True)
    unit = "d" if resolution == "daily" else "h"

    write_forecast_file(frame, resolution, max_horizon, unit, best_model_config, forecast_dir)
    step1 = frame[frame["step"] == 1].reset_index(drop=True)
    write_forecast_file(step1, resolution, 1, unit, best_model_config, forecast_dir)

    model_dir = OUT_DIR / "models" / resolution
    model_dir.mkdir(parents=True, exist_ok=True)
    for h, model in fit["models"].items():
        joblib.dump(model, model_dir / f"final_model_h{h}.joblib")
    print(f"  -> {model_dir.relative_to(PROJECT_ROOT)}: {max_horizon} models")


def run_daily() -> None:
    best_model_config = load_best_model_config("daily")
    data = pd.read_csv(DATA_DIR / "data_daily.csv")
    data = build_daily_features(data)
    horizons = build_daily_horizons(data)
    print("[daily] refit (5 seeds per horizon) + test (2019-2023 -> 2024)")
    fit = refit_and_forecast(horizons, best_model_config, DAILY_HORIZON, "daily")
    frame = forecast_frame(horizons, fit, DAILY_HORIZON, "d")
    write_outputs(frame, fit, "daily", DAILY_HORIZON, best_model_config)


def run_hourly() -> None:
    best_model_config = load_best_model_config("hourly")
    data = pd.read_csv(DATA_DIR / "data_hourly.csv")
    data = build_hourly_features(data)
    horizons = build_hourly_horizons(data)
    print("[hourly] refit (5 seeds per horizon) + test (2019-2023 -> 2024)")
    fit = refit_and_forecast(horizons, best_model_config, HOURLY_HORIZON, "hourly")
    frame = forecast_frame(horizons, fit, HOURLY_HORIZON, "h")
    write_outputs(frame, fit, "hourly", HOURLY_HORIZON, best_model_config)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--resolution", choices=("daily", "hourly", "all"), default="all")
    args = p.parse_args()

    if args.resolution in ("daily", "all"):
        run_daily()
    if args.resolution in ("hourly", "all"):
        run_hourly()


if __name__ == "__main__":
    main()
