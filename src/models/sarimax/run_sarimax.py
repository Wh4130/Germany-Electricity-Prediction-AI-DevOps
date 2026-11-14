"""
Final SARIMAX models: fit, forecast the validation year 2023 and the test year 2024, and write the forecasts in the
shared format, so that the shared evaluation (`src/models/foundation/evaluate.py`) scores them like the other models.

The specifications were chosen in `daily.ipynb` and `hourly.ipynb` on the validation year; this script does not
select anything, it only refits them:
- daily 1 d:  (2,0,0)(1,1,1,7), Model 1 X (baseline + month dummies) with the day-ahead price,
- daily 7 d:  the same specification without the day-ahead price (known only for the next day),
- hourly 1 h and 24 h: (2,0,0)(1,0,1,24) in levels with a constant, X coefficients by OLS, ARMA by MLE.
Past-only X (monthly indicators) keep their value of the step before the origin; the other X are ex-post.

Validation: fit on 2019-2022, forecast 2023. Test: fit once on 2019-2023, forecast 2024. No refits.
The quantiles are normal with the forecast standard error.

Outputs (src/results/sarimax/):
    forecasts/sarimax_{daily_1d,daily_7d,hourly_1h,hourly_24h}_{val,test}.csv   shared format, + a JSON sidecar
    models/sarimax_{daily_1d,daily_7d,hourly}.json                             the test fits (2019-2023), see
                                                                                common.save_model / load_model

Usage (from the project root):

    uv run python src/models/sarimax/run_sarimax.py                       # daily and hourly (about 20-30 min)
    uv run python src/models/sarimax/run_sarimax.py --resolution hourly
    uv run python src/models/foundation/evaluate.py src/results/sarimax/forecasts/*.csv \
        --metrics-dir src/results/sarimax/metrics
"""
import argparse
import json
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning

SARIMAX_DIR = Path(__file__).resolve().parent
if str(SARIMAX_DIR) not in sys.path:
    sys.path.insert(0, str(SARIMAX_DIR))

from common import fit_eval, forecast_frame, make_features, save_model  # noqa: E402
from features import DAILY_PRICE, PAST_ONLY, build_daily_X, build_hourly_X, standardize  # noqa: E402

PROJECT_ROOT = SARIMAX_DIR.parents[2]
DATA_DIR = PROJECT_ROOT / "src" / "data" / "final"
OUT_DIR = PROJECT_ROOT / "src" / "results" / "sarimax"

Y_SCALE = 1000          # fit in GWh (see fit_eval)
MAXITER = 5000

DAILY_ORDER, DAILY_SEASONAL = (2, 0, 0), (1, 1, 1, 7)
HOURLY_ORDER, HOURLY_SEASONAL = (2, 0, 0), (1, 0, 1, 24)
HOURLY_LB_LAGS = (24, 48, 168)

warnings.simplefilter("ignore", ConvergenceWarning)     # convergence is checked and written to the sidecar


# --------------------------------------------------------------------------
# Outputs
# --------------------------------------------------------------------------


def coverage_80(frame: pd.DataFrame) -> float:
    """ share of the actual values inside the 80 % interval (q0.1 to q0.9), in % """
    return float(((frame["y_true"] >= frame["q0.1"]) & (frame["y_true"] <= frame["q0.9"])).mean() * 100)


def write_forecasts(result: dict, y: pd.Series, horizon: int, resolution: str, split: str) -> pd.DataFrame:
    """ the forecast file in the shared format and its JSON sidecar (settings of the fit) """
    label = f"{horizon}{'h' if resolution == 'hourly' else 'd'}"
    frame = forecast_frame(result, y, horizon)
    path = OUT_DIR / "forecasts" / f"sarimax_{resolution}_{label}_{split}.csv"
    path.parent.mkdir(parents = True, exist_ok = True)
    frame.to_csv(path, index = False)

    res = result["res"]
    fitted = res.fittedvalues.index
    meta = {
        "model": "SARIMAX",
        "resolution": resolution, "horizon": horizon, "split": split,
        "n_origins": int(frame["origin"].nunique()),
        "created_at": datetime.now().isoformat(timespec = "seconds"),
        "order": list(result["order"]), "seasonal_order": list(result["seasonal_order"]),
        "trend": result["trend"], "y_scale": result["y_scale"], "exog_fit": result["exog_fit"],
        "fit_start": fitted[0].isoformat(), "fit_end": fitted[-1].isoformat(),
        "x_columns": result["x_columns"], "frozen_cols": result["frozen_cols"],
        "converged": result["first_converged"],
        "iterations": res.mle_retvals.get("iterations"),
        "aic": float(result["aic"]), "bic": float(result["bic"]),
        "quantiles": "normal, with the standard error of the forecast (parameter uncertainty ignored)",
    }
    path.with_suffix(".json").write_text(json.dumps(meta, indent = 2, default = str))

    err = frame["y_pred"] - frame["y_true"]
    print(f"  -> {path.relative_to(PROJECT_ROOT)}: {len(frame)} rows, {meta['n_origins']} origins | "
          f"RMSE {(err ** 2).mean() ** 0.5:,.0f} MWh, bias {err.mean():+,.0f} MWh, "
          f"80% coverage {coverage_80(frame):.1f}%")
    return frame


def write_model(result: dict, name: str, mu: pd.Series, sd: pd.Series) -> None:
    path = save_model(result, OUT_DIR / "models" / f"{name}.json", mu, sd)
    print(f"  -> {path.relative_to(PROJECT_ROOT)}")


def check_converged(result: dict, name: str) -> None:
    if not result["first_converged"]:
        print(f"  !! {name}: the fit did not converge (see the sidecar JSON)")


# --------------------------------------------------------------------------
# Daily
# --------------------------------------------------------------------------


def run_daily() -> None:
    data = pd.read_csv(DATA_DIR / "data_daily.csv", index_col = 0, parse_dates = ["date_from", "date_from_utc"])
    data.index = pd.to_datetime(data["date_from"]).values
    data = make_features(data)

    y_all = data["actual_consumption"].asfreq("D")           # 2019-2024
    X_raw = build_daily_X(data).asfreq("D")
    missing = int(X_raw.isna().sum().sum())
    if missing:
        raise ValueError(f"daily X has {missing} missing values")

    # * validation: fit 2019-2022, forecast 2023
    val_start = "2023-01-01"
    y_val = y_all[:"2023-12-31"]
    X_val, _, _ = standardize(X_raw, "2022-12-31")
    fit_kw = dict(y_scale = Y_SCALE, maxiter = MAXITER)

    # start values as in daily.ipynb: the likelihood is flat (seasonal MA close to -1), so the default start
    # values do not reach the optimum; the smaller specifications that (2,0,0)(1,1,1,7) contains are fitted first
    print("[daily] start values: (1,0,0)(0,1,1,7), then (1,0,0)(1,1,1,7)")
    start = fit_eval(y_val, X_val, (1, 0, 0), (0, 1, 1, 7), val_start, **fit_kw, name = "daily start 1")
    start = fit_eval(y_val, X_val, (1, 0, 0), (1, 1, 1, 7), val_start, **fit_kw,
                     start_params = start["res"].params, name = "daily start 2")

    print("[daily] validation fits (2019-2022)")
    val_1d = fit_eval(y_val, X_val, DAILY_ORDER, DAILY_SEASONAL, val_start, **fit_kw,
                      start_params = start["res"].params, frozen_cols = PAST_ONLY, name = "daily 1d val")
    val_7d = fit_eval(y_val, X_val.drop(columns = [DAILY_PRICE]), DAILY_ORDER, DAILY_SEASONAL, val_start, **fit_kw,
                      start_params = val_1d["res"].params,       # the price coefficient is dropped
                      horizon = 7, frozen_cols = PAST_ONLY, name = "daily 7d val")
    for name, result in (("daily 1d val", val_1d), ("daily 7d val", val_7d)):
        check_converged(result, name)
    write_forecasts(val_1d, y_all, 1, "daily", "val")
    write_forecasts(val_7d, y_all, 7, "daily", "val")

    # * test: fit once on 2019-2023, forecast 2024
    test_start = "2024-01-01"
    X_test, mu, sd = standardize(X_raw, "2023-12-31")
    print("[daily] test fits (2019-2023)")
    test_1d = fit_eval(y_all, X_test, DAILY_ORDER, DAILY_SEASONAL, test_start, **fit_kw,
                       start_params = val_1d["res"].params, frozen_cols = PAST_ONLY, name = "daily 1d test")
    test_7d = fit_eval(y_all, X_test.drop(columns = [DAILY_PRICE]), DAILY_ORDER, DAILY_SEASONAL, test_start, **fit_kw,
                       start_params = val_7d["res"].params,
                       horizon = 7, frozen_cols = PAST_ONLY, name = "daily 7d test")
    for name, result in (("daily 1d test", test_1d), ("daily 7d test", test_7d)):
        check_converged(result, name)
    write_forecasts(test_1d, y_all, 1, "daily", "test")
    write_forecasts(test_7d, y_all, 7, "daily", "test")
    write_model(test_1d, "sarimax_daily_1d", mu, sd)
    write_model(test_7d, "sarimax_daily_7d", mu, sd)


# --------------------------------------------------------------------------
# Hourly
# --------------------------------------------------------------------------


def run_hourly() -> None:
    data = pd.read_csv(DATA_DIR / "data_hourly.csv", index_col = 0, parse_dates = ["date_from", "date_from_utc"])
    # UTC as index: unique and regular (the local 02:00 is missing / there twice on the DST days)
    data.index = pd.to_datetime(data["date_from_utc"]).values
    data = make_features(data)

    # the years are local years, as UTC times
    val_start = data.loc[data["date_from"] >= "2023-01-01", "date_from_utc"].min()
    val_end = data.loc[data["date_from"] < "2024-01-01", "date_from_utc"].max()
    test_start = data.loc[data["date_from"] >= "2024-01-01", "date_from_utc"].min()
    fit_end = val_start - pd.Timedelta(1, "h")
    # the 24-hour forecasts start at every local midnight (as in the shared setup)
    origins = pd.DatetimeIndex(data.loc[data["date_from"].dt.hour == 0, "date_from_utc"])

    y_all = data["actual_consumption"].asfreq("h")
    X_raw = build_hourly_X(data).asfreq("h")
    missing = int(X_raw.isna().sum().sum())
    if missing:
        raise ValueError(f"hourly X has {missing} missing values")

    fit_kw = dict(y_scale = Y_SCALE, maxiter = MAXITER, freq = "h", exog_fit = "ols", lb_lags = HOURLY_LB_LAGS)
    forecast = dict(horizon = 24, origins = origins, frozen_cols = PAST_ONLY)

    # * validation: fit 2019-2022, forecast 2023
    y_val = y_all[:val_end]
    X_val = standardize(X_raw, fit_end)[0].assign(const = 1.0)      # no differencing, so a constant
    print("[hourly] start values: (2,0,0)(1,0,0,24)")
    start = fit_eval(y_val, X_val, (2, 0, 0), (1, 0, 0, 24), val_start, **fit_kw, name = "hourly start")
    print("[hourly] validation fit (2019-2022)")
    val = fit_eval(y_val, X_val, HOURLY_ORDER, HOURLY_SEASONAL, val_start, **fit_kw, **forecast,
                   start_params = start["res"].params, name = "hourly val")
    check_converged(val, "hourly val")
    write_forecasts(val, y_all, 1, "hourly", "val")
    write_forecasts(val, y_all, 24, "hourly", "val")

    # * test: fit once on 2019-2023, forecast 2024
    X_test, mu, sd = standardize(X_raw, val_end)
    X_test = X_test.assign(const = 1.0)
    print("[hourly] test fit (2019-2023)")
    test = fit_eval(y_all, X_test, HOURLY_ORDER, HOURLY_SEASONAL, test_start, **fit_kw, **forecast,
                    start_params = val["res"].params, name = "hourly test")
    check_converged(test, "hourly test")
    write_forecasts(test, y_all, 1, "hourly", "test")
    write_forecasts(test, y_all, 24, "hourly", "test")
    write_model(test, "sarimax_hourly", mu, sd)


def main() -> None:
    p = argparse.ArgumentParser(description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter)
    p.add_argument("--resolution", choices = ("daily", "hourly", "all"), default = "all")
    args = p.parse_args()

    t0 = time.perf_counter()
    if args.resolution in ("daily", "all"):
        run_daily()
    if args.resolution in ("hourly", "all"):
        run_hourly()
    print(f"done in {(time.perf_counter() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
