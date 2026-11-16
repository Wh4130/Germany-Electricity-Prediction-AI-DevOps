"""
The daily 1-day tree model behind the API: the 2024 forecasts and what-if forecasts with changed X.

The model is `final_model_h1.joblib` of src/models/trees/run_tree_based.py (fit on 2019-2023, one model for the
1-day horizon; it is a LightGBM, the training script picks the best library per horizon). Nothing is trained here.
A forecast for day d uses the actual load of d - 1, d - 2 and d - 7 (lags) and the X of day d, as in the shared
evaluation: `/forecast` equals the step-1 rows of src/results/tree-based/forecasts/tree_daily_test.csv.

What-if: the model is a set of trees, so it is NOT linear in the X. A what-if forecast is the model applied to the
features of the day with the changed X (the others stay as they are). Small changes can leave the forecast
unchanged (the trees split at fixed values) and then jump when a split is crossed. The model gives a point
forecast only, so there are no quantiles and no interval.

Files (`TREE_ARTIFACTS`, default: the project folders): data_daily.csv, final_model_h1.joblib.
"""
import os
from pathlib import Path

import joblib
import pandas as pd

from features import build_daily_features

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent     # in the image (/app) this is just "/"
ARTIFACTS = os.environ.get("TREE_ARTIFACTS")
if ARTIFACTS:
    DATA_PATH, MODEL_PATH = Path(ARTIFACTS) / "data_daily.csv", Path(ARTIFACTS) / "final_model_h1.joblib"
else:
    DATA_PATH = PROJECT_ROOT / "src" / "data" / "final" / "data_daily.csv"
    MODEL_PATH = PROJECT_ROOT / "src" / "results" / "tree-based" / "Models" / "daily" / "final_model_h1.joblib"

TEST_START = pd.Timestamp("2024-01-01")
SLIDER_SDS = 2          # slider range: the value of the day +- 2 standard deviations of 2019-2023

# the X that the dashboard can change: label, unit, and the physical bounds of the slider (same as the SARIMAX API)
SLIDERS = {
    "hdd":                    {"label": "Heating degree days", "unit": "°C·d", "lower": 0.0,
                               "note": "≈ 18 °C − mean temperature (0 above 18 °C)"},
    "wind_speed_10m_mean":    {"label": "Wind speed (10 m, daily mean)", "unit": "km/h", "lower": 0.0},
    "precipitation_sum":      {"label": "Precipitation", "unit": "mm", "lower": 0.0},
    "solar_generation_proxy": {"label": "Solar generation proxy", "unit": "MW·MJ/m²", "lower": 0.0},
    "day_ahead_price_mean":   {"label": "Day-ahead price (daily mean)", "unit": "EUR/MWh"},
    "industrial_confidence":  {"label": "Industrial confidence", "unit": "balance"},
    "ipi_ei_level":           {"label": "Industrial production index", "unit": "index"},
    "oxcgrt_stringency":      {"label": "COVID stringency (OxCGRT)", "unit": "0-100", "lower": 0.0, "upper": 100.0},
}
# slider name -> feature column of the model, where they differ (capacity x radiation, same quantity)
FEATURE = {"solar_generation_proxy": "solar_radiation_combi"}

# the X that follow from the date (shown, not changeable)
CALENDAR = ["is_holiday", "is_weekday", "weighted_regional_holiday", "weighted_school_holiday",
            "is_bridge_day", "is_christmas_new_year", "is_dst", "is_dst_transition_day"]

LIBRARIES = {"LGBMRegressor": "LightGBM", "XGBRegressor": "XGBoost", "CatBoostRegressor": "CatBoost",
             "RandomForestRegressor": "RandomForest"}


class TreeService:
    def __init__(self, data_path: Path = DATA_PATH, model_path: Path = MODEL_PATH):
        data = pd.read_csv(data_path)
        data["date_from"] = pd.to_datetime(data["date_from"])
        data = data.sort_values("date_from").reset_index(drop=True)
        features = build_daily_features(data)
        features.index = pd.DatetimeIndex(features.pop("date_from"))

        self.model = joblib.load(model_path)
        self.library = LIBRARIES.get(type(self.model).__name__, type(self.model).__name__)
        self.columns = [str(c) for c in self.model.feature_names_in_]    # the model's own order

        self.X_used = features.loc[TEST_START:, self.columns]            # the features each forecast uses
        self.y = features.loc[TEST_START:, "actual_consumption"]
        self.sd = features.loc[:"2023-12-31", self.columns].std()        # for the slider ranges
        self.calendar_data = features.loc[TEST_START:]
        self.y_pred = pd.Series(self.model.predict(self.X_used), index=self.X_used.index)

    def _day(self, date: str) -> pd.Timestamp:
        day = pd.Timestamp(date)
        if day not in self.y_pred.index:
            raise KeyError(f"no forecast for {date}: dates from {self.y_pred.index[0].date()} "
                           f"to {self.y_pred.index[-1].date()}")
        return day

    def meta(self) -> dict:
        return {
            "model": self.library, "resolution": "daily", "horizon": 1,
            "first_date": str(self.y_pred.index[0].date()), "last_date": str(self.y_pred.index[-1].date()),
            "sliders": {c: {k: v for k, v in s.items() if k in ("label", "unit")} for c, s in SLIDERS.items()},
            "calendar": CALENDAR,
        }

    def forecast(self, start: str | None = None, end: str | None = None) -> list[dict]:
        """ the one-step forecasts with the actual X, in the shared format (one row per day, no quantiles) """
        pred, y = self.y_pred[start:end], self.y[start:end]
        return [{"date": str(day.date()), "y_true": float(y[day]), "y_pred": float(pred[day])} for day in pred.index]

    def features(self, date: str) -> dict:
        """ the X of the day: the slider values (the X the forecast uses) with their ranges, and the calendar """
        day = self._day(date)
        sliders = {}
        for c, s in SLIDERS.items():
            column = FEATURE.get(c, c)
            value, sd = float(self.X_used.at[day, column]), float(self.sd[column])
            low, high = value - SLIDER_SDS * sd, value + SLIDER_SDS * sd
            if "lower" in s:
                low = max(low, s["lower"])
            if "upper" in s:
                high = min(high, s["upper"])
            # past_only: the tree model uses the monthly indicators as they are on the day, it does not freeze them
            sliders[c] = {**s, "value": value, "min": low, "max": high, "step": sd / 50, "past_only": False}
        calendar = {c: float(self.calendar_data.at[day, c]) for c in CALENDAR}
        calendar |= {"month": int(self.calendar_data.at[day, "month"]), "day_of_week": day.day_name()}
        return {"date": str(day.date()), "y_true": float(self.y[day]), "sliders": sliders, "calendar": calendar}

    def predict(self, date: str, x: dict[str, float]) -> dict:
        """ the forecast of the day with the given X (the others stay as in `features`) """
        day = self._day(date)
        unknown = [c for c in x if c not in SLIDERS]
        if unknown:
            raise ValueError(f"these X cannot be changed: {unknown} (only {list(SLIDERS)})")
        new = self.X_used.loc[[day]].copy()
        for c, value in x.items():
            new[FEATURE.get(c, c)] = float(value)
        return {"date": str(day.date()), "y_pred": float(self.model.predict(new)[0]),
                "y_pred_baseline": float(self.y_pred[day]), "y_true": float(self.y[day]),
                "x": {c: float(new.at[day, FEATURE.get(c, c)]) for c in SLIDERS}}
