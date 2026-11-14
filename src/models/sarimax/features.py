"""
The X of the final SARIMAX models, shared by the notebooks (model selection) and `run_sarimax.py` (final fits),
so that both build exactly the same columns.

    from features import PAST_ONLY, build_daily_X, build_hourly_X, standardize

The functions take the data of `data/final` after `common.make_features` and return the raw X (not standardized).
"""
import pandas as pd

# * X that are only known up to the origin in the shared setup (monthly indicators): `fit_eval(frozen_cols = ...)`
PAST_ONLY = ["industrial_confidence", "ipi_ei_level", "oxcgrt_stringency"]

# * daily Model 1: the baseline X + month dummies (the weekly pattern is in the seasonal difference)
DAILY_BASE_X = [
    "is_holiday", "is_holiday_weekday",
    "weighted_regional_holiday", "weighted_school_holiday",
    "is_bridge_day", "is_christmas_new_year", "is_dst", "is_dst_transition_day",
    "industrial_confidence", "ipi_ei_level", "day_ahead_price_mean",
    "hdd", "wind_speed_10m_mean", "precipitation_sum",
    "solar_generation_proxy", "oxcgrt_stringency",
]
DAILY_PRICE = "day_ahead_price_mean"          # left out of the 7-day model (known only for the next day)

# * hourly model: levels with yearly and daily Fourier terms, day-of-week dummies and the daily profile of
#   Saturdays and of Sundays / holidays
HOURLY_BASE_X = [
    "is_holiday", "is_holiday_weekday", "weighted_regional_holiday", "weighted_school_holiday",
    "is_bridge_day", "is_christmas_new_year", "is_dst_transition_day",
    "industrial_confidence", "ipi_ei_level", "day_ahead_price",
    "hdd", "wind_speed_10m", "precipitation", "solar_generation_proxy",
    "oxcgrt_stringency",
]
K_YEAR, K_DAY = 5, 6
FOURIER_YEAR = [f"{t}_y{k}" for k in range(1, K_YEAR + 1) for t in ("sin", "cos")]
FOURIER_DAY = [f"{t}_d{k}" for k in range(1, K_DAY + 1) for t in ("sin", "cos")]


def build_daily_X(data: pd.DataFrame) -> pd.DataFrame:
    """ the X of daily Model 1, raw: the baseline X and the month dummies (January is the reference) """
    months = pd.get_dummies(data["month"], prefix = "month", drop_first = True)
    return pd.concat([data[DAILY_BASE_X], months], axis = 1).astype(float)


def build_hourly_X(data: pd.DataFrame) -> pd.DataFrame:
    """ the X of the hourly model, raw (without the constant) """
    is_holiday = data["is_holiday"].astype(bool)
    is_saturday = ((data["day_of_week_raw"] == 5) & ~is_holiday).astype(float)
    is_sunday_holiday = ((data["day_of_week_raw"] == 6) | is_holiday).astype(float)
    # the daily profile on Saturdays and on Sundays / holidays: the daily Fourier terms times the type of day
    profiles = pd.concat(
        {f"{c}_sat": data[c] * is_saturday for c in FOURIER_DAY}
        | {f"{c}_sunhol": data[c] * is_sunday_holiday for c in FOURIER_DAY},
        axis = 1)
    dow = pd.get_dummies(data["day_of_week_raw"], prefix = "dow", drop_first = True)
    return pd.concat([data[HOURLY_BASE_X + FOURIER_YEAR + FOURIER_DAY], dow, profiles], axis = 1).astype(float)


def standardize(X: pd.DataFrame, fit_end) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Standardize the continuous columns (more than two values) with the mean and sd of the rows up to `fit_end`;
    the dummies stay 0 / 1. Returns the X and the mean and sd (for `common.save_model`).
    """
    X = X.astype(float).copy()
    cont = [c for c in X.columns if X[c].nunique() > 2]
    mu, sd = X.loc[:fit_end, cont].mean(), X.loc[:fit_end, cont].std()
    X[cont] = (X[cont] - mu) / sd
    return X, mu, sd
