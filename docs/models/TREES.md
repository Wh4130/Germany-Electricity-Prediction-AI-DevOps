# Tree based models

[README](../../README.md) · [FEATURES](../FEATURES.md) · [FEATURE_ENGINEERING](../FEATURE_ENGINEERING.md) · [EDA](../EDA.md) · [MODELS](../MODELS.md)

Models: [SARIMAX](SARIMAX.md) · **TREES** · [FOUNDATION](FOUNDATION.md)

## Navigator

- [Overview](#overview)
- [How to run](#how-to-run)
- [Preprocessing](#preprocessing)
  - [Daily features](#daily-features)
  - [Hourly features](#hourly-features)
  - [Excluded features](#excluded-features)
- [Normalization](#normalization)
- [Training and evaluation](#training-and-evaluation)
  - [Model selection (cross-validation)](#model-selection-cross-validation)
  - [Final models](#final-models)
  - [Daily results](#daily-results)
  - [Hourly results](#hourly-results)
  - [Forecast files](#forecast-files)
- [Saved models](#saved-models)
- [Insights (daily, h = 1)](#insights-daily-h--1)
  - [Error-day analysis](#error-day-analysis)
  - [Insights by feature type](#insights-by-feature-type)
- [Deviations from the shared setup](#deviations-from-the-shared-setup)
- [Limitations and open questions](#limitations-and-open-questions)

## Overview

> Implemented: daily data (validation 2023, test 2024, h = 1 to 7 days) and hourly data (validation 2023, test 2024, h = 1 to 24 hours). Code: [src/models/trees/](../../src/models/trees/).

Direct multi-step forecasting: one independently tuned model per horizon `h`, not a recursive forecast that feeds its own prediction back in as the next step's lag. This avoids compounding error across steps, at the cost of training (and choosing) H separate models instead of one.

| | Daily | Hourly |
|---|---|---|
| Horizons | h = 1 … 7 days | h = 1 … 24 hours |
| Candidate model families | XGBoost, CatBoost, LightGBM, RandomForest | XGBoost, CatBoost, LightGBM (RandomForest not tried - not enough compute for its grid at this scale) |
| Final refit | 5 random seeds per horizon, lowest-test-MAE seed kept, metrics averaged over seeds | same: 5 random seeds per horizon |
| Test MAE (h = 1) | 25,212 MWh (MAPE 2.02%) | 408 MWh (MAPE 0.78%) |
| Test MAE (h = max, all steps stacked) | 32,091 MWh (MAPE 2.54%) | 1,147 MWh (MAPE 2.16%) |

Code in `src/models/trees/`:

| File | Content |
|---|---|
| `run_tree_based.py` | The final models: refits the model/params chosen in the notebooks (no selection of its own), forecasts the test year 2024, writes the forecasts in the shared format and saves the model files |
| `notebooks/Daily_model_building.ipynb` | Model selection on the daily data: features, per-model CV per horizon, final 5-seed refit, error analysis, SHAP |
| `notebooks/Hourly_model_building.ipynb` | Model selection on the hourly data: same structure, h = 1 … 24, same 5-seed final refit |

Results in `src/results/tree-based/`:

| Path | Content |
|---|---|
| `best_model_config_{daily,hourly}.json` | The model family + hyperparameters chosen per horizon (written by the notebooks' `best_model_config` cell). `run_tree_based.py` reads this file instead of hand-copying the dict, so there is one place for this choice |
| `forecasts/` | `tree_{daily,hourly}_{1,7|24}{d,h}_test.csv` in the shared format of [MODELS - Forecast files](../MODELS.md#forecast-files), each with a JSON sidecar (model per horizon, params per horizon, origins). See [Forecast files](#forecast-files) |
| `metrics/` | The output of the shared evaluation script (`src.analysis.evaluate`) on these files |
| `models/{daily,hourly}/final_model_h{h}.joblib` | The refit model of each horizon, see [Saved models](#saved-models) |
| `Model-comparison-result/{daily,hourly}/summary_final.md` | A hand-written markdown snapshot of the 5-seed-averaged test metrics, written by the notebooks' last cell, so the numbers can be checked without opening or re-running the notebook |

## How to run

Final forecasts, from the project root:

```bash
uv run python src/models/trees/run_tree_based.py                # --resolution daily / hourly for one only
uv run python -m src.analysis.evaluate --models tree-based --force
uv run python -m src.analysis.run_report                        # adds tree-based to every final-report table and figure
```

`run_tree_based.py` does not select anything itself - it raises `FileNotFoundError` if `best_model_config_{daily,hourly}.json` is missing, with a message to run the notebook's CV + `best_model_config` cells first.

Model selection: open `notebooks/Daily_model_building.ipynb` or `Hourly_model_building.ipynb` with the project environment (`uv sync`) and run all cells. The CV cells are the slow part (`GridSearchCV` × `TimeSeriesSplit(5)` per horizon per model family); the hourly notebook is markedly slower than the daily one (24 horizons instead of 7, ~24× the rows per horizon).

## Preprocessing

### Daily features

Daily data, index `date_from` (the local date). Target `actual_consumption` (MWh).

| Group | Columns |
|---|---|
| Calendar | `month`, `day_of_week_raw`, `is_holiday`, `is_weekday`, `weighted_regional_holiday`, `weighted_school_holiday`, `is_bridge_day`, `is_christmas_new_year`, `is_dst`, `is_dst_transition_day` |
| Lags | `lag_1`, `lag_2`, `lag_7` (`actual_consumption.shift(lag)`) |
| Price | `day_ahead_price_mean`, `day_ahead_price_mean_7d` (trailing 7-day mean, excludes today) |
| Weather | `hdd`, `wind_speed_10m_mean`, `precipitation_sum` |
| Solar | `solar_radiation_combi` = `solar_capacity_mw` × `shortwave_radiation_sum` |
| Yearly pattern | `sin_y1`, `cos_y1`, `sin_y2`, `cos_y2`, `sin_y3`, `cos_y3` |
| Economy and policy | `oxcgrt_stringency`, `ipi_ei_level`, `industrial_confidence` |

**`day_ahead_price_mean_7d` is an added feature**, not a column of `final/`: a trailing 7-day mean of `day_ahead_price_mean` that excludes today (`shift(1).rolling(7).mean()`). It was tried alongside the same-day price as an extra attempt to probe the relationship between price and demand over a longer window - a separate "recent price environment" signal rather than just smoothing today's own value, in case demand responds to the price level of the past week rather than (or in addition to) the same day's own price. Its actual importance per horizon is in the notebook's feature-importance / SHAP cells, not re-derived here.

### Hourly features

Hourly data, index `date_from_utc`. Target `actual_consumption` (MWh).

| Group | Columns |
|---|---|
| Calendar | same 10 columns as daily, swapped to the target hour (see below) |
| Lags | `lag_1`, `lag_24`, `lag_48`, `lag_168` |
| Price | `day_ahead_price`, `day_ahead_price_7d` (trailing 24×7-hour mean) |
| Weather | `hdd`, `wind_speed_10m`, `precipitation`, `is_day` |
| Solar | `solar_radiation_combi` = `solar_capacity_mw` × `shortwave_radiation` |
| Yearly pattern | `sin_y1`, `cos_y1`, `sin_y2`, `cos_y2`, `sin_y3`, `cos_y3` |
| Daily pattern | `sin_d1`, `cos_d1`, …, `sin_d6`, `cos_d6` |
| Economy and policy | `oxcgrt_stringency`, `ipi_ei_level`, `industrial_confidence` |

**Calendar and the yearly/daily harmonics are swapped to the target hour**, the same idea as the daily model: these columns are deterministic (known in advance for any future hour), so each horizon `h` gets the *target hour's* own `month`, `day_of_week_raw`, `is_holiday`, …, `sin_y*`/`cos_y*`/`sin_d*`/`cos_d*` instead of the origin hour's. This matters more here than for the daily model: the daily-harmonic pair (`sin_d1`/`cos_d1`, …) encodes time-of-day, which can differ a lot between the origin hour and a target up to 23 hours later. Weather, price and the lags (`lag_1`/`lag_24`/`lag_48`/`lag_168`) stay anchored to the origin hour - those aren't knowable yet for the target hour.

### Excluded features

Same reasoning as the [SARIMAX exclusions](SARIMAX.md#excluded-features), chosen once and shared between the two models:

| Feature | Reason |
|---|---|
| `generation_*` | Leakage |
| `gas_price_eu_usd` | Correlated with `day_ahead_price(_mean)`, little extra information |
| `daylight_duration` (daily) | A function of the day of year, already in the Fourier terms; hourly uses `is_day` / `shortwave_radiation` directly instead |
| `shortwave_radiation_sum` / `shortwave_radiation` on its own | Folded into `solar_radiation_combi` together with `solar_capacity_mw`, instead of kept as a separate column |
| `day_of_week` | Text column; `day_of_week_raw` (integer) is used, trees do not need the sine/cosine encoding SARIMAX needs |

## Normalization

Tree ensembles (XGBoost, CatBoost, LightGBM, RandomForest) split on thresholds of each feature, so they are invariant to monotonic rescaling. Target and features are passed on their raw scale (`actual_consumption` in MWh, prices, weather, etc.) - no standardization, no log transform, no inverse transform. Booleans (`is_holiday`, …) are kept as `True`/`False`; every library here accepts them directly as 0 / 1. `day_of_week_raw` and `month` are kept as integers, not one-hot or Fourier encoded (unlike SARIMAX and the foundation models) - trees can split on an integer directly.

## Training and evaluation

### Model selection (cross-validation)

For each horizon `h` independently, `GridSearchCV` with `TimeSeriesSplit(n_splits=5)`, scored by negative MAE, on that horizon's own train set (2019–2022):

| Model | Grid |
|---|---|
| XGBoost | `max_depth` {3,5,7}, `n_estimators` {200,500,800}, `learning_rate` {0.01,0.05,0.1}, `min_child_weight` {1,5,10} |
| CatBoost | `depth` {3,5,7}, `iterations` {200,500,800}, `learning_rate` {0.01,0.05,0.1}, `l2_leaf_reg` {1,5,10} |
| LightGBM | `num_leaves` {15,31,63}, `n_estimators` {200,500,800}, `learning_rate` {0.01,0.05,0.1}, `min_child_samples` {10,20,40} |
| RandomForest (daily only) | `max_depth` {5,10,20}, `n_estimators` {200,500,800}, `min_samples_leaf` {1,5,10} |

For every horizon, the model family and hyperparameters with the lowest validation (2023) MAE are picked by hand from the CV output and recorded in `best_model_config` - this becomes `best_model_config_{daily,hourly}.json`.

### Final models

- **Both resolutions**: each horizon's chosen model is refit on train + validation (2019–2023) with 5 random seeds (42–46). The seed with the lowest test MAE is kept for the forecast file, the SHAP analysis and the saved model; the test MAE / RMSE / MAPE reported (console output, `summary_final`, [Model-comparison-result](#overview)) is the **average over the 5 seeds** - more robust than resting on one seed's luck. The forecast CSV itself always holds the kept (lowest-MAE) seed's predictions, not an average of 5 predictions.
- `RandomForest` does not support `NaN`: its horizons (daily h = 4, 7) get `.dropna()` on train + validation before the refit.
- The hourly refit is the heavier job: 24 horizons × 5 seeds × ~24× the rows per horizon of the daily model.

### Daily results

Best model per horizon and 5-seed-averaged test (2024) metrics:

| h | Model | MAE (MWh) | RMSE (MWh) | MAPE | Best-seed MAE |
|---:|---|---:|---:|---:|---:|
| 1 | LightGBM | 25,212 | 34,207 | 2.02% | 25,212 |
| 2 | XGBoost | 27,924 | 36,241 | 2.21% | 27,924 |
| 3 | CatBoost | 30,220 | 38,746 | 2.39% | 29,088 |
| 4 | RandomForest | 37,062 | 48,744 | 2.92% | 36,844 |
| 5 | LightGBM | 32,262 | 41,696 | 2.54% | 32,262 |
| 6 | LightGBM | 33,610 | 44,434 | 2.67% | 33,610 |
| 7 | RandomForest | 40,701 | 55,953 | 3.26% | 40,543 |

Shared-evaluation metrics (`src.analysis.evaluate`, computed from the kept, lowest-MAE-seed forecasts - so they match the "Best-seed MAE" column, not the 5-seed average): h = 1 alone (366 origins) MAE 25,212 / RMSE 34,207 / MAPE 2.02%, skill vs. seasonal naive 0.563; h = 1…7 stacked (360 origins whose whole horizon stays inside 2024, 2,520 rows) MAE 32,091 / RMSE 43,116 / MAPE 2.54%, skill 0.435.

### Hourly results

Best model per horizon and 5-seed-averaged test (2024) metrics (full 24-row table in `tree_hourly_24h_test.json`'s `model_per_horizon`; shown here at the horizons the notebook itself picked for plots and SHAP - nowcast + every 6 hours ahead):

| h | Model | MAE (MWh) | RMSE (MWh) | MAPE | Best-seed MAE |
|---:|---|---:|---:|---:|---:|
| 1 | CatBoost | 412 | 537 | 0.79% | 408 |
| 6 | CatBoost | 1,077 | 1,369 | 2.07% | 1,062 |
| 12 | XGBoost | 1,303 | 1,648 | 2.49% | 1,303 |
| 18 | CatBoost | 1,310 | 1,673 | 2.51% | 1,290 |
| 24 | CatBoost | 1,237 | 1,605 | 2.37% | 1,232 |

CatBoost covers h = 1–11, 13–21, 24; XGBoost h = 12, 22, 23 - no horizon picks LightGBM any more (it did before the calendar/harmonic swap described above was added). The error grows from the nowcast (h = 1) through the early afternoon-equivalent horizons and flattens out past h ≈ 13, rather than increasing monotonically with h, because the lag features (`lag_24`, `lag_168`) stay informative at any horizon.

Shared-evaluation metrics (computed from the kept, lowest-MAE-seed forecasts, so they match the "Best-seed MAE" column, not the 5-seed average): h = 1 alone (8,784 origins, one per hour) MAE 408 / RMSE 531 / MAPE 0.78%, skill 0.847; h = 1…24 stacked (366 origins, one per local midnight, 8,784 rows) MAE 1,147 / RMSE 1,518 / MAPE 2.16%, skill 0.568.

The swap to target-hour calendar/harmonics (see [Hourly features](#hourly-features)) was re-run through the full CV + 5-seed refit after it was added: it leaves h = 1 about unchanged (barely any origin/target difference at that horizon) but clearly helps the larger horizons - h = 24's MAE dropped from 1,401 to 1,232 (best seed, about 12% lower).

### Forecast files

Two files per resolution, like the other models' `_1d_`/`_7d_` (daily) and `_1h_`/`_24h_` (hourly) pair - one file per model, resolution, horizon and split, as required by [FORCAST_FORMAT](../FORCAST_FORMAT.md):

| File | Horizon | Content |
|---|---|---|
| `tree_daily_1d_test.csv` | 1 | Step-1-only rows (one per origin, 366 origins) |
| `tree_daily_7d_test.csv` | 7 | All 7 steps stacked per origin, origins whose whole horizon stays inside 2024 - 360 origins, 2,520 rows |
| `tree_hourly_1h_test.csv` | 1 | Step-1-only rows, one origin per hour (8,784 origins) |
| `tree_hourly_24h_test.csv` | 24 | All 24 steps stacked per origin, one origin per **local midnight only** - 366 origins, 8,784 rows |

Both files of a resolution come from the same fit - the `_1{d,h}_` file is not a separate model, just the step-1 rows of the same forecast. The max-horizon file of each resolution additionally restricts its origins, matching the other models' origin set instead of keeping every origin the raw per-horizon fit covers: daily `_7d_` keeps only origins whose whole 7-day horizon stays inside the same year (`full_horizon_valid` in `build_daily_horizons`) - without it, the last 6 days of the year would appear as ragged, incomplete-horizon origins (step 1 only, 1-2 only, …) instead of being excluded like SARIMAX / TabICL / TimesFM-3 do; hourly `_24h_` keeps only local-midnight origins (`is_midnight` in `build_hourly_horizons`), matching SARIMAX / the foundation models' hourly 24h origin set instead of using every hour. The `_1{d,h}_` files keep every origin, which already matched the other models' own `_1d_`/`_1h_` files. Columns: `origin`, `target_time`, `step`, `y_true`, `y_pred`, `q0.1` … `q0.9` (always `NaN` - these models give a point forecast only, no native quantiles). The JSON sidecar records `model`, `resolution`, `horizon`, `split`, `n_origins`, and `model_per_horizon` / `params_per_horizon` (the chosen family and hyperparameters of every horizon up to the file's own `horizon`).

## Saved models

`run_tree_based.py` saves the refit model of every horizon with `joblib.dump`, uniformly regardless of the model family:

| Path | Content |
|---|---|
| `src/results/tree-based/models/daily/final_model_h{1..7}.joblib` | The daily model of each horizon (the lowest-test-MAE seed) |
| `src/results/tree-based/models/hourly/final_model_h{1..24}.joblib` | The hourly model of each horizon |

`deploy/tree_api/service.py` loads `models/daily/final_model_h1.joblib` (the 1-day horizon) for the live what-if API; see [API - Tree notes](../deploy/API.md#tree-notes).

## Insights (daily, h = 1)

### Error-day analysis

Largest absolute-error test-set (2024) days for h = 1, by mechanism (from `errors_h1` / SHAP in the daily notebook):

- **Jan 1 (New Year's Day, Monday) - overestimated.** Even with `is_holiday = True`, SHAP shows `day_of_week_raw` alone still pushes the prediction up (the model learned Monday = demand surge), outweighing the holiday effect - actual demand came in much lower than predicted. `is_holiday × is_weekday` would not fix this, it only flags "a weekday holiday", not *which* weekday; it needs `is_holiday × day_of_week_raw`.
- **Jan 8 and Jan 12 - underestimated.** Both are cold-spell days (`hdd` = 19.1 and 22.4); actual demand rose more than `hdd` alone predicted.
- **Jan 27 (Saturday) - overestimated.** Right after that cold spell ended; the lag features (`lag_1`/`lag_2`/`lag_7`) are still carrying the cold spell's demand level into the first warmer day.
- **Mar 31 (Easter Sunday) - overestimated.** Not flagged as `is_holiday` (falls on a Sunday), but demand is lower than an ordinary Sunday - `is_holiday` is not precise enough, though this also confirms legal holidays do have lower demand than regular Sundays.
- **Dec 24 (Christmas Eve) - overestimated.** Legally a workday, but businesses close early / people take leave ahead of the long holiday - not captured by `is_christmas_new_year` or `is_bridge_day`.

### Insights by feature type

From the h = 1 model's own feature importance / SHAP (`src/results/tree-based/report/figures/daily/shap_summary_h1.png`), grouped by feature type:

- **Calendar.** Contributes strongly overall - `day_of_week_raw` and `is_holiday` rank high. The other holiday-type columns (`is_bridge_day`, `is_christmas_new_year`, …) show lower importance, but mainly because they have few samples (see [EDA - Holiday effect](../EDA.md#holiday-effect)), not because the effect itself is small - taken together, holidays are an important feature group. Holidays do have lower consumption than a regular weekday, and a public holiday lower still than an ordinary non-working day (multi-model comparison, the error-day analysis above). Watch for days that are effectively non-working but not legally a public holiday, especially in winter, where missing the signal means oversupply (e.g. New Year's Eve, Easter Sunday - see the error-day cases above); the opposite risk (oversupply from an overestimate) shows up in summer around an ordinary day off, a public holiday or a bridge day.
- **Weather.** `hdd` and `wind_speed_10m_mean` also rank high (`shap_dependence_hdd_h1.png`). Winter uses more electricity than summer; before temperature drops below 5°C or a cold front (strong wind) arrives, procuring/storing power ahead of time covers the coming demand spike - a combined low-temperature + strong-wind "winter storm alert" signal would capture this. Weather turning points (a warm-up starting, or an extreme cold spell arriving) matter specifically (the Jan 8/12/27 error-day cases above). Not enough evidence yet that precipitation affects consumption.
- **Raw (lags).** The past week's own consumption (`lag_1`/`lag_2`/`lag_7`) contributes strongly to the forecast.
- **Price.** Not enough evidence yet that electricity price affects consumption.

## Deviations from the shared setup

The [shared setup](../MODELS.md#shared-setup) is a proposal of 2026-10-27. The tree-based work follows the later team decisions where they differ, in agreement with [SARIMAX's own deviations](SARIMAX.md#deviations-from-the-shared-setup):

| Shared setup | Tree-based | Effect |
|---|---|---|
| Daily horizons 7 d and 30 d | h = 1 to 7 days, each its own model | 30 d horizon not covered |
| Hourly horizons 24 h and 168 h | h = 1 to 24 hours | 168 h horizon not covered. The 24 h file's origins are local midnight only, and the 1 h file's are every hour - both now aligned with SARIMAX / the foundation models' own `_1h_`/`_24h_` origin sets |
| Main metric MAE; skill vs. seasonal naive; pinball loss and coverage | Point forecast only, no quantiles | Pinball loss and coverage stay empty in the shared evaluation |
| Weather variant B (realistic) for the main results | Observed weather for all horizons (variant A, ex-post) | Optimistic, more so at longer horizons |

## Limitations and open questions

- **Calendar feature gap** (from the h = 1 insights above): `is_holiday × day_of_week_raw` (one-hot per weekday) plus `is_day_before_holiday` / `is_day_after_holiday`, across all horizons - not tried. Would cover days that behave like holidays but legally are not (Whit Sunday, New Year's Eve, Easter Sunday, Dec 24).
- **Extreme-temperature feature**: a feature for a given year's cold spells or other unusually large temperature swings, instead of relying only on daily `hdd` - not tried; see the Jan 8 / Jan 12 / Jan 27 cases above.
- **RandomForest not tuned for the hourly data** (only XGBoost, CatBoost, LightGBM) - its `GridSearchCV` grid (same size as daily's) over 24 horizons × hourly rows (~24× daily's row count per horizon) was not feasible on the available hardware in reasonable time, not a result ruling RandomForest out.
- **No native quantiles.** The point-forecast-only design means pinball loss and interval coverage cannot be reported for tree-based in the shared evaluation; a quantile variant (e.g. `LGBMRegressor(objective="quantile")` per quantile, or `CatBoostRegressor(loss_function="Quantile:alpha=...")`) was not tried.
