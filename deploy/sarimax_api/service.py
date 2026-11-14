"""
The daily 1-day SARIMAX model behind the API: the 2024 forecasts and what-if forecasts with changed X.

The model is the test fit of `run_sarimax.py` (2019-2023, `sarimax_daily_1d.json`); it is not estimated again,
only filtered over 2019-2024 with the saved parameters. A forecast for day d uses the actual load up to d - 1
and the X of day d, as in the shared evaluation (past-only X keep their value of d - 1).

What-if: the X enter the model as a regression (y = X beta + SARIMA errors), so the one-step forecast of day d
is linear in the X of day d. Changing them shifts the forecast by (X new - X used) @ beta (in standardized
units); the forecast standard error, and so the width of the interval, stays the same. Only the continuous
X can be changed (`SLIDERS`); the calendar X follow from the date.

Files (`SARIMAX_ARTIFACTS`, default: the project folders): common.py, features.py, sarimax_daily_1d.json,
data_daily.csv.
"""
import os
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import norm

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent     # in the image (/app) this is just "/"
ARTIFACTS = os.environ.get("SARIMAX_ARTIFACTS")
if ARTIFACTS:
    CODE_DIR = Path(ARTIFACTS)
    DATA_PATH, MODEL_PATH = CODE_DIR / "data_daily.csv", CODE_DIR / "sarimax_daily_1d.json"
else:
    CODE_DIR = PROJECT_ROOT / "src" / "models" / "sarimax"
    DATA_PATH = PROJECT_ROOT / "src" / "data" / "final" / "data_daily.csv"
    MODEL_PATH = PROJECT_ROOT / "src" / "results" / "sarimax" / "models" / "sarimax_daily_1d.json"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from common import QUANTILES, load_model, make_features  # noqa: E402
from features import build_daily_X  # noqa: E402

TEST_START = pd.Timestamp("2024-01-01")
SLIDER_SDS = 2          # slider range: the value of the day +- 2 standard deviations of 2019-2023

# the X that the dashboard can change: label, unit, and the physical bounds of the slider
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

# the X that follow from the date (shown, not changeable)
CALENDAR = ["is_holiday", "is_holiday_weekday", "weighted_regional_holiday", "weighted_school_holiday",
            "is_bridge_day", "is_christmas_new_year", "is_dst", "is_dst_transition_day"]


class SarimaxService:
    def __init__(self, data_path: Path = DATA_PATH, model_path: Path = MODEL_PATH):
        data = pd.read_csv(data_path, index_col = 0, parse_dates = ["date_from", "date_from_utc"])
        data.index = pd.to_datetime(data["date_from"]).values
        data = make_features(data)
        y = data["actual_consumption"].asfreq("D")
        X_raw = build_daily_X(data).asfreq("D")

        model = load_model(model_path, y, X_raw)
        self.spec = {k: v for k, v in model.items() if k not in ("res", "X", "params")}
        self.y_scale = model["y_scale"]
        self.x_columns = model["x_columns"]
        self.x_mean, self.x_std = pd.Series(model["x_mean"]), pd.Series(model["x_std"])
        self.frozen = model["frozen_cols"]
        res = model["res"]
        self.beta = res.params[self.x_columns]

        # the raw X that each forecast uses: the actual X of the day, past-only X of the day before
        X_used = X_raw[self.x_columns].copy()
        X_used[self.frozen] = X_raw[self.frozen].shift(1)
        self.X_used = X_used[TEST_START:]
        self.data = data.loc[TEST_START:]
        self.y = y[TEST_START:]

        # one-step forecasts with the actual X (statsmodels), then the past-only X frozen
        pred = res.get_prediction(start = TEST_START, dynamic = False)
        shift = (self._standardize(self.X_used) - model["X"].loc[TEST_START:, self.x_columns]) @ self.beta
        self.y_pred = (pred.predicted_mean + shift) * self.y_scale
        self.se = pred.se_mean * self.y_scale

    def _standardize(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        cont = [c for c in X.columns if c in self.x_mean.index]
        X[cont] = (X[cont] - self.x_mean[cont]) / self.x_std[cont]
        return X

    def _day(self, date: str) -> pd.Timestamp:
        day = pd.Timestamp(date)
        if day not in self.y_pred.index:
            raise KeyError(f"no forecast for {date}: dates from {self.y_pred.index[0].date()} "
                           f"to {self.y_pred.index[-1].date()}")
        return day

    def _quantiles(self, mean: float, se: float) -> dict:
        return {f"q{q}": float(mean + norm.ppf(q) * se) for q in QUANTILES}

    def meta(self) -> dict:
        return {
            "model": "SARIMAX", "resolution": "daily", "horizon": 1,
            "order": self.spec["order"], "seasonal_order": self.spec["seasonal_order"],
            "fit_start": self.spec["fit_start"], "fit_end": self.spec["fit_end"],
            "first_date": str(self.y_pred.index[0].date()), "last_date": str(self.y_pred.index[-1].date()),
            "sliders": {c: {k: v for k, v in s.items() if k in ("label", "unit")} for c, s in SLIDERS.items()},
            "calendar": CALENDAR,
        }

    def forecast(self, start: str | None = None, end: str | None = None) -> list[dict]:
        """ the one-step forecasts with the actual X, in the shared format (one row per day) """
        mean, se, y = self.y_pred[start:end], self.se[start:end], self.y[start:end]
        rows = []
        for day in mean.index:
            rows.append({"date": str(day.date()), "y_true": float(y[day]), "y_pred": float(mean[day]),
                         **self._quantiles(mean[day], se[day])})
        return rows

    def features(self, date: str) -> dict:
        """ the X of the day: the slider values (the X the forecast uses) with their ranges, and the calendar """
        day = self._day(date)
        sliders = {}
        for c, s in SLIDERS.items():
            value, sd = float(self.X_used.at[day, c]), float(self.x_std[c])
            low, high = value - SLIDER_SDS * sd, value + SLIDER_SDS * sd
            if "lower" in s:
                low = max(low, s["lower"])
            if "upper" in s:
                high = min(high, s["upper"])
            sliders[c] = {**s, "value": value, "min": low, "max": high, "step": sd / 50,
                          "past_only": c in self.frozen}
        calendar = {c: float(self.data.at[day, c]) for c in CALENDAR}
        calendar |= {"month": int(self.data.at[day, "month"]), "day_of_week": day.day_name()}
        return {"date": str(day.date()), "y_true": float(self.y[day]), "sliders": sliders, "calendar": calendar}

    def predict(self, date: str, x: dict[str, float]) -> dict:
        """ the forecast of the day with the given X (the others stay as in `features`) """
        day = self._day(date)
        unknown = [c for c in x if c not in SLIDERS]
        if unknown:
            raise ValueError(f"these X cannot be changed: {unknown} (only {list(SLIDERS)})")
        used = self.X_used.loc[[day]]
        new = used.copy()
        for c, value in x.items():
            new[c] = float(value)
        delta = float(((self._standardize(new) - self._standardize(used)) @ self.beta).iloc[0])
        mean = float(self.y_pred[day]) + delta * self.y_scale
        return {"date": str(day.date()), "y_pred": mean, "y_pred_baseline": float(self.y_pred[day]),
                "y_true": float(self.y[day]), "x": {c: float(new.at[day, c]) for c in SLIDERS},
                **self._quantiles(mean, float(self.se[day]))}
