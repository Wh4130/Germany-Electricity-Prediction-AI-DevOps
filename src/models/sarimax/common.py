"""
Shared helpers of the SARIMAX notebooks (daily data), so that Model 1 and Model 2 use the same code.

The notebooks import this file (they run in this folder):
    from common import make_features, evaluate, fit_eval, summarize, save_result, save_results, load_results

Nothing here changes a global variable: `fit_eval` returns its result and the notebook stores it
(e.g. `results["A"] = fit_eval(...)`), so a cell only depends on what it passes in.

Every experiment is saved to its own file, <directory>/<name>.json: saving an experiment again replaces
only its own file, the other experiments in the folder stay. The file also holds the settings of the run
(X columns, trend, mean and standard deviation of every X column on the first fit), so a number can
always be traced back to what produced it.
"""
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """ features that are made in the notebooks only (they are not in the feature pipeline) """
    out = df.copy()

    # * interaction term for is_holiday and is_weekday
    out["is_holiday_weekday"] = (out["is_holiday"] & out["is_weekday"]).astype(float)

    # * computed solar generation proxy: capacity * radiation
    out["solar_generation_proxy"] = out["solar_capacity_mw"] * out["shortwave_radiation_sum"]
    return out


def evaluate(y_true: pd.Series, y_pred: pd.Series, verbose: bool = True) -> dict:
    err = y_true - y_pred
    rmse = np.sqrt((err ** 2).mean())
    mape = (err.abs() / y_true).mean() * 100
    if verbose:
        print(f"🔹 rmse = {rmse:.2f}")
        print(f"🔹 mape = {mape:.2f}%")
    return {"rmse": rmse, "mape": mape}


def fit_eval(
    y: pd.Series,
    X: pd.DataFrame | None,
    order: tuple,
    seasonal_order: tuple,
    val_start: str,
    trend: str | None = None,
    refit_freq: str | None = None,
    y_scale: float = 1.0,
    maxiter: int = 1000,
    refit_maxiter: int = 50,
    maxfun: int = 50000,
    start_params: pd.Series | None = None,
    horizon: int = 1,
    name: str = "",
) -> dict:
    """
    `refit_freq = None` (the default, the team's protocol): fit once on all the data before `val_start`, then
    predict every day from `val_start` on one step ahead with these parameters (the day before is the actual y).
    Expanding window with refits: `refit_freq` "7D" (every 7 days) or "MS" (at the start of every month):
    for each block from `val_start` on, fit on all the data before the block, then predict every day of the
    block one step ahead (the parameters are fixed within the block).

    `y` has to end with the last day to evaluate (the test period is not in it).
    AIC, BIC and the residuals come from the first fit (the data before `val_start`).
    Returns a dict: the metrics, `y_hat` (the forecasts), `res` (the first fit), `resid`, and `n_not_converged`.

    `y_scale`: the model is fitted on y / y_scale (e.g. 1000: MWh -> GWh). With y in the millions the optimizer
    can stop at its start values without a single step (and still report "converged"), so sigma2, AIC and BIC
    are wrong. `y_hat`, `resid`, RMSE and MAPE are given back in the unit of `y`; AIC, BIC and `res` are in the
    scaled unit, so compare AIC and BIC only between fits with the same `y_scale`.
    `first_stuck`: the first fit stopped at its start values without a single iteration.

    `maxiter`: the iteration limit of the first fit (statsmodels' default of 50 is often too few here); AIC, BIC
    and the residuals come from this fit. `refit_maxiter`: the limit of the refits. They start from the
    estimates of the block before (warm start), so they are already close to the optimum and only make the
    forecasts. Near a flat likelihood (e.g. a seasonal MA close to -1) the optimizer reports "not converged"
    although the estimates hardly change, so refits that reach their limit are expected and only counted
    (`n_not_converged`); a message is printed only if the first fit does not converge (`first_converged`).

    `maxfun`: the limit of likelihood evaluations per fit (scipy's L-BFGS default is 15000). The gradient is
    computed numerically, about one evaluation per parameter, so with many X (e.g. 45 parameters) the default
    is used up after about 280 iterations, long before `maxiter`.

    `start_params`: the start values of the first fit, as a Series indexed by parameter name, usually the
    estimates of a simpler model that this one contains, e.g. `results["SARIMAX_1000117"]["res"].params` for
    (2,0,0)(0,1,1,7). Parameters that are not in it (the new terms) start at 0, so the first fit starts at the
    likelihood of the simpler model and cannot end below it. This helps when the likelihood is flat (seasonal MA
    close to -1) and the default start values do not reach the optimum. The simpler model has to be fitted with
    the same X and `y_scale`, otherwise its estimates are on another scale.

    `horizon`: forecasts for h = 1 .. horizon days (only without refits). Every day from the day before
    `val_start` to the second last day is a forecast origin: the actual y up to the origin, the actual X of the
    forecast days (ex-post), and from the second step on the model's own forecasts of y. Forecasts after the last
    day of `y` are left out, so horizon h is evaluated on the days from val_start + (h - 1) days to the last day.
    Returns `y_hat_h` (index: the forecast day, columns "h1" .. "hH") and per horizon `rmse_hH`, `mape_hH` and
    `bias_hH` (mean of actual - forecast: negative = the model overestimates). `rmse`, `mape` and `y_hat` are h = 1.
    """
    if horizon > 1 and refit_freq is not None:
        raise ValueError("horizon > 1 is only supported without refits (refit_freq = None): with refits, a forecast "
                         "from an origin before a refit would use parameters estimated on data after the origin")

    y = y.asfreq("D")
    y_model = y / y_scale
    if X is not None:
        X = X.astype(float).asfreq("D")

    # the refit dates: val_start, then every refit_freq (none without refits); a block ends the day before the next refit
    if refit_freq is None:
        block_starts = pd.DatetimeIndex([val_start])
    else:
        block_starts = pd.date_range(val_start, y.index[-1], freq = refit_freq)
        if len(block_starts) == 0 or block_starts[0] != pd.Timestamp(val_start):
            block_starts = block_starts.insert(0, pd.Timestamp(val_start))
    block_ends = list(block_starts[1:] - pd.Timedelta(days = 1)) + [y.index[-1]]

    first_res, prev_res, parts, not_converged = None, None, [], 0
    t0 = time.perf_counter()

    for i, (start, end) in enumerate(zip(block_starts, block_ends), start = 1):
        y_train = y_model[:start - pd.Timedelta(days = 1)]
        exog_train = None if X is None else X.loc[y_train.index]

        model = SARIMAX(
            y_train,
            order = order,
            seasonal_order = seasonal_order,
            exog = exog_train,
            trend = trend,
        )
        if prev_res is not None:
            init = prev_res.params          # warm start: the estimates of the block before (only one block more data)
        elif start_params is not None:
            init = start_params.reindex(model.param_names).fillna(0.0)     # new terms start at 0
        else:
            init = None
        res = model.fit(
            disp = False,
            maxiter = maxiter if prev_res is None else refit_maxiter,
            maxfun = maxfun,
            start_params = init,
        )
        prev_res = res
        not_converged += not res.mle_retvals["converged"]
        if first_res is None:
            first_res = res         # the first fit = the data before val_start

        res_block = res.apply(y_model[:end], exog = None if X is None else X[:end])
        parts.append(res_block.get_prediction(start = start, dynamic = False).predicted_mean)

        if i % 10 == 1:
            elapsed = time.perf_counter() - t0
            remaining = len(block_starts) - i
            print(f"[{name}] refit {i}/{len(block_starts)} (block from {start.date()}), "
                  f"{remaining} left, elapsed {elapsed:.0f}s, ETA {elapsed / i * remaining:.0f}s")

    y_hat = pd.concat(parts) * y_scale
    score = evaluate(y[val_start:], y_hat, verbose = False)

    # forecasts for h = 1 .. horizon (without refits there is one block, so res_block holds all the data)
    if horizon == 1:
        y_hat_h = y_hat.to_frame("h1")
    else:
        t1 = time.perf_counter()
        y_hat_h = _forecast_horizons(res_block, val_start, y.index[-1], horizon) * y_scale
        print(f"[{name}] forecasts for h = 1..{horizon}: {time.perf_counter() - t1:.0f}s")
    by_horizon = {}
    for column in y_hat_h.columns:
        pred = y_hat_h[column].dropna()
        score_h = evaluate(y[pred.index], pred, verbose = False)
        by_horizon[f"rmse_{column}"] = score_h["rmse"]
        by_horizon[f"mape_{column}"] = score_h["mape"]
        by_horizon[f"bias_{column}"] = (y[pred.index] - pred).mean()

    lb =acorr_ljungbox(first_res.resid.iloc[28:], lags = [7, 14, 28])
    first_converged = bool(first_res.mle_retvals["converged"])
    first_stuck = first_res.mle_retvals.get("iterations", 1) == 0
    if not first_converged:
        retvals = first_res.mle_retvals
        print(f"[{name}] the first fit did not converge ({retvals.get('iterations')} iterations, "
              f"{retvals.get('fcalls')} function calls; limits {maxiter} / {maxfun})")
    if first_stuck:
        print(f"[{name}] the first fit stopped at its start values (0 iterations), try a larger y_scale")

    return {
        "order": order, "seasonal_order": seasonal_order,
        "aic": first_res.aic, "bic": first_res.bic,
        "rmse": score["rmse"], "mape": score["mape"],
        "lb_p7": lb.loc[7, "lb_pvalue"], "lb_p14": lb.loc[14, "lb_pvalue"], "lb_p28": lb.loc[28, "lb_pvalue"],
        "first_converged": first_converged, "first_stuck": first_stuck,
        "n_not_converged": not_converged, "n_refits": len(block_starts), "val_start": val_start,
        "refit_freq": refit_freq,
        "y_scale": y_scale, "maxiter": maxiter, "refit_maxiter": refit_maxiter, "maxfun": maxfun,
        "start_params": None if start_params is None else start_params.to_dict(),
        **_config_from_res(first_res),
        "horizon": horizon, **by_horizon,
        "y_hat": y_hat, "y_hat_h": y_hat_h, "res": first_res, "resid": first_res.resid * y_scale,
    }


def _forecast_horizons(res, val_start: str, last: pd.Timestamp, horizon: int) -> pd.DataFrame:
    """ forecasts for h = 1 .. horizon from every origin (the day before val_start to the second last day), in the scale of `res` """
    columns = {f"h{k}": {} for k in range(1, horizon + 1)}
    for origin in pd.date_range(pd.Timestamp(val_start) - pd.Timedelta(days = 1), last - pd.Timedelta(days = 1), freq = "D"):
        end = min(origin + pd.Timedelta(days = horizon), last)
        # dynamic: the actual y up to the origin, then the model's own forecasts
        pred = res.get_prediction(start = origin + pd.Timedelta(days = 1), end = end, dynamic = True).predicted_mean
        for k, (day, value) in enumerate(pred.items(), start = 1):
            columns[f"h{k}"][day] = value
    return pd.DataFrame(columns).sort_index()


def _config_from_res(res) -> dict:
    """ settings of a fit: the X columns, the trend, and the mean / standard deviation of every X column on the fitted data """
    model = res.model
    if model.exog is None:
        return {"x_columns": [], "trend": model.trend, "x_fit_mean": {}, "x_fit_std": {}}
    columns = list(model.exog_names)
    return {
        "x_columns": columns,
        "trend": model.trend,
        "x_fit_mean": dict(zip(columns, model.exog.mean(axis = 0).tolist())),
        "x_fit_std": dict(zip(columns, model.exog.std(axis = 0, ddof = 1).tolist())),
    }


def summarize(results: dict, names: list | None = None, columns: tuple = ("aic", "bic", "rmse", "mape")) -> pd.DataFrame:
    """ one row per result. A name that is not in `results` is a KeyError, so a missing dependency is visible. """
    names = list(results) if names is None else names
    return pd.DataFrame({name: {c: results[name][c] for c in columns} for name in names}).T


def _to_json(value):
    if isinstance(value, pd.DataFrame):
        return {"dates": [d.isoformat() for d in value.index],
                "columns": {c: value[c].astype(float).tolist() for c in value.columns}}
    if isinstance(value, pd.Series):
        return {"dates": [d.isoformat() for d in value.index], "values": value.astype(float).tolist()}
    if isinstance(value, dict):
        return {k: _to_json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_to_json(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def save_result(name: str, result: dict, directory: str | Path) -> Path:
    """
    Write one experiment to <directory>/<name>.json (an earlier file of the same name is replaced).
    The fitted model object is not saved (it is big), so diagnostic plots that need it need a new fit.
    """
    if "x_columns" not in result and "res" in result:     # made by an older fit_eval: take the settings from the fit
        result = {**result, **_config_from_res(result["res"])}

    data = {
        "name": name,
        "saved_at": datetime.now().isoformat(timespec = "seconds"),
        **{k: _to_json(v) for k, v in result.items() if k != "res"},
    }
    path = Path(directory) / f"{name}.json"
    path.parent.mkdir(parents = True, exist_ok = True)
    with open(path, "w") as file:
        json.dump(data, file, indent = 1)
    return path


def save_results(results: dict, directory: str | Path) -> None:
    """ save every experiment of `results` to its own file; files of experiments that are not in `results` stay """
    for name, result in results.items():
        save_result(name, result, directory)


def load_results(directory: str | Path) -> dict:
    """ all experiments in the folder, in the format of fit_eval (without the fitted model object) """
    results = {}
    for path in sorted(Path(directory).glob("*.json")):
        with open(path) as file:
            data = json.load(file)
        for key in ("y_hat", "resid"):
            if isinstance(data.get(key), dict):
                data[key] = pd.Series(data[key]["values"], index = pd.to_datetime(data[key]["dates"]))
        if isinstance(data.get("y_hat_h"), dict):
            data["y_hat_h"] = pd.DataFrame(data["y_hat_h"]["columns"], index = pd.to_datetime(data["y_hat_h"]["dates"]))
        for key in ("order", "seasonal_order"):
            if key in data:
                data[key] = tuple(data[key])
        results[data.pop("name", path.stem)] = data
    return results
