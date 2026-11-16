"""
The features of the daily tree model (1 day ahead), as the model was trained.

This is a COPY of `build_daily_features` in src/models/trees/run_tree_based.py (the training script imports
catboost, xgboost, lightgbm and scikit-learn at the top, which the API does not need). If the training features
change, change this file too: `test_app.py` compares the API forecasts with
src/results/tree-based/forecasts/tree_daily_test.csv and fails when the two drift apart.
"""
import pandas as pd

# For h = 1 the row of day d holds everything the forecast of day d uses: the X of day d (calendar, weather, price,
# ...) and the load of d - 1, d - 2 and d - 7 (the lags). For h > 1 the training script swaps in the calendar of the
# target day; that is not needed here.


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
