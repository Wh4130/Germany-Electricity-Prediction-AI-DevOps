"""
Shared helpers of the SARIMAX notebooks (daily and hourly data), so that the models use the same code.

The notebooks import this file (they run in this folder):
    from common import make_features, evaluate, fit_eval, forecast_frame, summarize, save_result, save_results, load_results
    from common import save_model, load_model      # the fitted model (parameters), to forecast again without a new fit

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
from scipy.stats import norm
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """ features that are made in the notebooks only (they are not in the feature pipeline) """
    out = df.copy()

    # * interaction term for is_holiday and is_weekday
    out["is_holiday_weekday"] = (out["is_holiday"] & out["is_weekday"]).astype(float)

    # * computed solar generation proxy: capacity * radiation (daily: daily sum, hourly: hourly value)
    radiation = "shortwave_radiation_sum" if "shortwave_radiation_sum" in out else "shortwave_radiation"
    out["solar_generation_proxy"] = out["solar_capacity_mw"] * out[radiation]
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
    freq: str = "D",
    origins: pd.DatetimeIndex | None = None,
    frozen_cols: list | None = None,
    exog_fit: str = "mle",
    lb_lags: tuple = (7, 14, 28),
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

    `horizon`: forecasts for h = 1 .. horizon days (only without refits). A forecast uses the actual y up to the
    day before its first step, the actual X of the forecast days (ex-post), and from the second step on the model's
    own forecasts of y. As in the shared setup (MODELS.md), only origins whose whole horizon lies inside the
    evaluation period are used: first steps from val_start to the last day - (horizon - 1) days.
    Returns `y_hat_h` (index: the forecast day, columns "h1" .. "hH"), its standard errors `y_hat_h_se`, and per
    horizon `rmse_hH`, `mape_hH` and `bias_hH` (mean of actual - forecast: negative = the model overestimates),
    all over these origins. `rmse`, `mape`, `y_hat` and `y_hat_se` are h = 1 for every day of the period.
    The standard errors give normal prediction intervals (see `forecast_frame`). `rmse_all`, `mape_all` and
    `bias_all` pool all steps of all these origins.

    `freq`: the frequency of the data, "D" (daily) or "h" (hourly); "day" above means one step of this frequency.
    `origins`: the first forecast steps for horizon > 1 (e.g. hourly: the UTC times of every local midnight);
    default: every step. Origins whose horizon leaves the period are dropped.
    `frozen_cols`: X columns that are only known up to the origin (past-only in the shared setup, e.g. monthly
    indicators). All forecasts from an origin (h = 1 included) use their value of the step before the first
    forecast step instead of the actual value of the forecast step; the other X stay ex-post. The X enter the
    model as a regression (y = X beta + SARIMA errors), so this only shifts the forecast by
    (X frozen - X actual) @ beta; the standard errors stay the same. Default None: all X ex-post.
    `exog_fit`: how the coefficients of X are estimated. "mle" (default): together with the ARMA parameters by
    maximum likelihood. "ols": two steps, for many X on long data (hourly): the X coefficients by OLS of y on X
    over the fit data, then the ARMA parameters (and sigma2, trend) by maximum likelihood with the X coefficients
    fixed (`fit_constrained`). The optimizer then has only a few parameters instead of all X coefficients, which
    is much faster with a numerical gradient. OLS is consistent but not efficient under autocorrelated errors, the
    X coefficients have no standard errors (p-values NaN), and the prediction intervals ignore their uncertainty.
    AIC and BIC count only the free parameters, so compare them only between fits with the same `exog_fit`.
    `lb_lags`: the lags of the Ljung-Box test on the residuals of the first fit (hourly e.g. (24, 48, 168)); the
    first 4 weeks of residuals are left out (start-up of the filter).
    """
    if horizon > 1 and refit_freq is not None:
        raise ValueError("horizon > 1 is only supported without refits (refit_freq = None): with refits, a forecast "
                         "from an origin before a refit would use parameters estimated on data after the origin")

    one = pd.Timedelta(1, freq)         # one step
    y = y.asfreq(freq)
    y_model = y / y_scale
    if X is not None:
        X = X.astype(float).asfreq(freq)
    frozen_cols = list(frozen_cols or [])
    missing = [c for c in frozen_cols if X is None or c not in X.columns]
    if missing:
        raise ValueError(f"frozen_cols not in X: {missing}")
    if exog_fit not in ("mle", "ols"):
        raise ValueError(f"exog_fit has to be 'mle' or 'ols', not {exog_fit!r}")

    # the refit dates: val_start, then every refit_freq (none without refits); a block ends the day before the next refit
    if refit_freq is None:
        block_starts = pd.DatetimeIndex([val_start])
    else:
        block_starts = pd.date_range(val_start, y.index[-1], freq = refit_freq)
        if len(block_starts) == 0 or block_starts[0] != pd.Timestamp(val_start):
            block_starts = block_starts.insert(0, pd.Timestamp(val_start))
    block_ends = list(block_starts[1:] - one) + [y.index[-1]]

    first_res, prev_res, parts, se_parts, not_converged = None, None, [], [], 0
    t0 = time.perf_counter()

    for i, (start, end) in enumerate(zip(block_starts, block_ends), start = 1):
        y_train = y_model[:start - one]
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
        fit_kwargs = dict(disp = False, maxiter = maxiter if prev_res is None else refit_maxiter, maxfun = maxfun)
        if exog_fit == "ols" and exog_train is not None:
            # step 1: the X coefficients by OLS; step 2: the other parameters by MLE with these fixed
            beta = np.linalg.lstsq(exog_train.to_numpy(), y_train.to_numpy(), rcond = None)[0]
            fixed = dict(zip(model.exog_names, beta))
            free_init = None if init is None else pd.Series(init, index = model.param_names).drop(list(fixed)).to_numpy()
            res = model.fit_constrained(fixed, start_params = free_init, **fit_kwargs)
        else:
            res = model.fit(start_params = init, **fit_kwargs)
        prev_res = res
        not_converged += not res.mle_retvals["converged"]
        if first_res is None:
            first_res = res         # the first fit = the data before val_start

        res_block = res.apply(y_model[:end], exog = None if X is None else X[:end])
        pred_block = res_block.get_prediction(start = start, dynamic = False)
        parts.append(pred_block.predicted_mean + _frozen_shift(X, frozen_cols, res.params, pred_block.predicted_mean.index, 1, one))
        se_parts.append(pred_block.se_mean)

        if i % 10 == 1:
            elapsed = time.perf_counter() - t0
            remaining = len(block_starts) - i
            print(f"[{name}] refit {i}/{len(block_starts)} (block from {start.date()}), "
                  f"{remaining} left, elapsed {elapsed:.0f}s, ETA {elapsed / i * remaining:.0f}s")

    y_hat = pd.concat(parts) * y_scale
    y_hat_se = pd.concat(se_parts) * y_scale
    score = evaluate(y[val_start:], y_hat, verbose = False)

    # forecasts for h = 1 .. horizon (without refits there is one block, so res_block holds all the data)
    if horizon == 1:
        y_hat_h, y_hat_h_se = y_hat.to_frame("h1"), y_hat_se.to_frame("h1")
    else:
        t1 = time.perf_counter()
        y_hat_h, y_hat_h_se = _forecast_horizons(res_block, val_start, y.index[-1], horizon, one, origins)
        for k in range(1, horizon + 1):
            y_hat_h[f"h{k}"] += _frozen_shift(X, frozen_cols, res_block.params, y_hat_h.index, k, one)
        y_hat_h, y_hat_h_se = y_hat_h * y_scale, y_hat_h_se * y_scale
        print(f"[{name}] forecasts for h = 1..{horizon}: {time.perf_counter() - t1:.0f}s")
    by_horizon = {}
    for column in y_hat_h.columns:
        pred = y_hat_h[column].dropna()
        score_h = evaluate(y[pred.index], pred, verbose = False)
        by_horizon[f"rmse_{column}"] = score_h["rmse"]
        by_horizon[f"mape_{column}"] = score_h["mape"]
        by_horizon[f"bias_{column}"] = (y[pred.index] - pred).mean()
    # all steps together (a target time can belong to several steps, so stack the columns)
    pred_all = y_hat_h.stack().dropna()
    actual_all = y.reindex(pred_all.index.get_level_values(0)).to_numpy()
    by_horizon["rmse_all"] = np.sqrt(((actual_all - pred_all.to_numpy()) ** 2).mean())
    by_horizon["mape_all"] = (np.abs(actual_all - pred_all.to_numpy()) / actual_all).mean() * 100
    by_horizon["bias_all"] = (actual_all - pred_all.to_numpy()).mean()

    burn = int(pd.Timedelta(weeks = 4) / one)          # the first 4 weeks: start-up of the filter
    lb = acorr_ljungbox(first_res.resid.iloc[burn:], lags = list(lb_lags))
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
        **{f"lb_p{lag}": lb.loc[lag, "lb_pvalue"] for lag in lb_lags},
        "first_converged": first_converged, "first_stuck": first_stuck,
        "n_not_converged": not_converged, "n_refits": len(block_starts), "val_start": val_start,
        "refit_freq": refit_freq,
        "y_scale": y_scale, "maxiter": maxiter, "refit_maxiter": refit_maxiter, "maxfun": maxfun,
        "start_params": None if start_params is None else start_params.to_dict(),
        **_config_from_res(first_res),
        "freq": freq, "horizon": horizon, "frozen_cols": frozen_cols, "exog_fit": exog_fit, **by_horizon,
        "y_hat": y_hat, "y_hat_se": y_hat_se, "y_hat_h": y_hat_h, "y_hat_h_se": y_hat_h_se,
        "res": first_res, "resid": first_res.resid * y_scale,
    }


def _frozen_shift(X: pd.DataFrame | None, cols: list, params: pd.Series, index: pd.DatetimeIndex, k: int,
                  one: pd.Timedelta) -> pd.Series | float:
    """
    Change of the step-k forecasts at the target times `index` (in the scale of `params`) when the columns `cols`
    keep their value of the step before the origin (origin = target - (k - 1) steps, so the value at target - k
    steps) instead of the actual value at the target: (X before - X target) @ beta. 0 without `cols`.
    """
    if not cols:
        return 0.0
    beta = params[cols].to_numpy()
    before = X[cols].reindex(index - k * one).to_numpy()
    target = X[cols].reindex(index).to_numpy()
    return pd.Series((before - target) @ beta, index = index)


def _forecast_horizons(res, val_start: str, last: pd.Timestamp, horizon: int, one: pd.Timedelta,
                       origins: pd.DatetimeIndex | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Forecasts and their standard errors for h = 1 .. horizon, in the scale of `res`. `origins` are the first steps
    (default: every step); only those whose whole horizon lies inside the period (val_start to last) are used.
    """
    if origins is None:
        origins = pd.date_range(val_start, last, freq = one)
    origins = pd.DatetimeIndex(origins)
    origins = origins[(origins >= pd.Timestamp(val_start)) & (origins + (horizon - 1) * one <= last)]
    means = {f"h{k}": {} for k in range(1, horizon + 1)}
    ses = {f"h{k}": {} for k in range(1, horizon + 1)}
    for first in origins:
        # dynamic: the actual y up to the step before the first step, then the model's own forecasts
        pred = res.get_prediction(start = first, end = first + (horizon - 1) * one, dynamic = True)
        for k, (day, value, se) in enumerate(zip(pred.predicted_mean.index, pred.predicted_mean, pred.se_mean), start = 1):
            means[f"h{k}"][day] = value
            ses[f"h{k}"][day] = se
    return pd.DataFrame(means).sort_index(), pd.DataFrame(ses).sort_index()


QUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def forecast_frame(result: dict, y: pd.Series, horizon: int) -> pd.DataFrame:
    """
    The forecasts of a `fit_eval` result in the shared format of MODELS.md (Forecast files): one row per origin and
    step, columns origin, target_time, step, y_true, y_pred, q0.1 .. q0.9. `origin` is the day of the first forecast
    step; daily as YYYY-MM-DD, hourly as YYYY-MM-DD HH:MM:SS (the UTC time of `date_from_utc`). horizon = 1: every
    step of the period; horizon > 1: the origins of `fit_eval` whose whole horizon lies inside the period (the
    result needs `fit_eval(..., horizon = horizon)` or larger).
    The quantiles come from a normal distribution with the forecast standard error; they ignore the uncertainty of
    the parameters and of the X. The residuals are heavy-tailed, so check the coverage before trusting quantiles
    further out than 0.1 / 0.9.
    """
    freq = result.get("freq", "D")      # results saved before hourly support are daily
    one = pd.Timedelta(1, freq)
    if horizon == 1:
        means, ses = result["y_hat"].to_frame("h1"), result["y_hat_se"].to_frame("h1")
    else:
        if result["horizon"] < horizon:
            raise ValueError(f"the result has forecasts up to h = {result['horizon']}, not {horizon}")
        means, ses = result["y_hat_h"], result["y_hat_h_se"]
    first_steps = means["h1"].dropna().index      # the origins of the result
    rows = []
    for k in range(1, horizon + 1):
        mean, se = means[f"h{k}"].dropna(), ses[f"h{k}"].dropna()
        origin = mean.index - (k - 1) * one
        part = pd.DataFrame({"origin": origin, "target_time": mean.index, "step": k,
                             "y_true": y.reindex(mean.index).to_numpy(), "y_pred": mean.to_numpy()})
        for q in QUANTILES:
            part[f"q{q}"] = mean.to_numpy() + norm.ppf(q) * se.reindex(mean.index).to_numpy()
        rows.append(part[part["origin"].isin(first_steps)])
    out = pd.concat(rows).sort_values(["origin", "step"]).reset_index(drop = True)
    date_format = "%Y-%m-%d" if freq == "D" else "%Y-%m-%d %H:%M:%S"
    out["origin"] = out["origin"].dt.strftime(date_format)
    out["target_time"] = out["target_time"].dt.strftime(date_format)
    return out


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
    if isinstance(value, pd.Timestamp):      # e.g. val_start of the hourly data (a UTC time)
        return value.isoformat()
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


def save_model(result: dict, path: str | Path, x_mean: pd.Series | None = None, x_std: pd.Series | None = None) -> Path:
    """
    Write the fitted model of a `fit_eval` result to a JSON file, so that it can forecast again without a new fit
    (`load_model`): the specification, the estimated parameters, the X columns, `frozen_cols`, and the mean and
    standard deviation that standardized the raw X before the fit (`x_mean`, `x_std`, e.g. from the notebook's
    `standardize`; the columns that are not in them, the dummies, stay unscaled). Not the data: `load_model` takes
    y and the raw X again. The result needs the fitted model (`res`), so a result loaded with `load_results` does
    not work.
    """
    import statsmodels
    res = result["res"]
    model = res.model
    x_columns = [] if model.exog is None else list(model.exog_names)
    scaled = [] if x_mean is None else [c for c in x_columns if c in x_mean.index]
    missing = [c for c in scaled if x_std is None or c not in x_std.index]
    if missing:
        raise ValueError(f"x_std is missing columns of x_mean: {missing}")
    fitted = res.fittedvalues.index
    data = {
        "saved_at": datetime.now().isoformat(timespec = "seconds"),
        "statsmodels_version": statsmodels.__version__,
        "order": list(result["order"]), "seasonal_order": list(result["seasonal_order"]),
        "trend": model.trend, "y_scale": result["y_scale"], "freq": result.get("freq", "D"),
        "fit_start": fitted[0].isoformat(), "fit_end": fitted[-1].isoformat(),
        "converged": bool(res.mle_retvals["converged"]),
        "params": {k: float(v) for k, v in res.params.items()},
        "x_columns": x_columns,
        "frozen_cols": list(result.get("frozen_cols", [])),
        "x_mean": {c: float(x_mean[c]) for c in scaled},
        "x_std": {c: float(x_std[c]) for c in scaled},
    }
    path = Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)
    with open(path, "w") as file:
        json.dump(data, file, indent = 1)
    return path


def load_model(path: str | Path, y: pd.Series | None = None, X: pd.DataFrame | None = None) -> dict:
    """
    Read a model written by `save_model`. With y (in its original unit) and the raw X (unscaled, at least the saved
    X columns), the dict also holds `res`: the model on these data with the saved parameters (no new estimation),
    in the unit y / y_scale, e.g. `res.get_forecast(steps, exog = ...)` (multiply by `y_scale`), and `X`: the X
    standardized as in the fit. Past-only X (`frozen_cols`) have to be frozen by the caller when it forecasts.
    """
    with open(path) as file:
        spec = json.load(file)
    spec["order"], spec["seasonal_order"] = tuple(spec["order"]), tuple(spec["seasonal_order"])
    if y is None:
        return spec

    freq = spec["freq"]
    y = y.asfreq(freq)
    exog = None
    if spec["x_columns"]:
        missing = [c for c in spec["x_columns"] if X is None or c not in X.columns]
        if missing:
            raise ValueError(f"X is missing columns of the model: {missing}")
        exog = X[spec["x_columns"]].astype(float).asfreq(freq).copy()
        for c, mean in spec["x_mean"].items():
            exog[c] = (exog[c] - mean) / spec["x_std"][c]
    model = SARIMAX(y / spec["y_scale"], order = spec["order"], seasonal_order = spec["seasonal_order"],
                    exog = exog, trend = spec["trend"])
    params = pd.Series(spec["params"])[model.param_names]
    return {**spec, "res": model.filter(params), "X": exog}


def load_results(directory: str | Path) -> dict:
    """ all experiments in the folder, in the format of fit_eval (without the fitted model object) """
    results = {}
    for path in sorted(Path(directory).glob("*.json")):
        with open(path) as file:
            data = json.load(file)
        for key in ("y_hat", "y_hat_se", "resid"):
            if isinstance(data.get(key), dict):
                data[key] = pd.Series(data[key]["values"], index = pd.to_datetime(data[key]["dates"]))
        for key in ("y_hat_h", "y_hat_h_se"):
            if isinstance(data.get(key), dict):
                data[key] = pd.DataFrame(data[key]["columns"], index = pd.to_datetime(data[key]["dates"]))
        for key in ("order", "seasonal_order"):
            if key in data:
                data[key] = tuple(data[key])
        results[data.pop("name", path.stem)] = data
    return results
