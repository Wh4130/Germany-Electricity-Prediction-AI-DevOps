# SARIMAX

[README](../../README.md) · [FEATURES](../FEATURES.md) · [FEATURE_ENGINEERING](../FEATURE_ENGINEERING.md) · [EDA](../EDA.md) · [MODELS](../MODELS.md)

Models: **SARIMAX** · [TREES](TREES.md) · [FOUNDATION](FOUNDATION.md)

## Navigator

- [Overview](#overview)
- [How to run](#how-to-run)
- [Preprocessing](#preprocessing)
  - [Features](#features)
  - [Excluded features](#excluded-features)
  - [Stationarity](#stationarity)
- [Normalization](#normalization)
- [Training and evaluation](#training-and-evaluation)
  - [Forecast protocol](#forecast-protocol)
  - [Model 1: seasonal difference](#model-1-seasonal-difference)
  - [Model 2: regression in levels](#model-2-regression-in-levels)
  - [Model 1 vs. Model 2](#model-1-vs-model-2)
  - [Final model: validation and test](#final-model-validation-and-test)
- [Deviations from the shared setup](#deviations-from-the-shared-setup)
- [Limitations and open questions](#limitations-and-open-questions)
- [Learning resources](#learning-resources)
  - [1. How to choose the seasonal period](#1-how-to-choose-the-seasonal-period)
  - [2. Why and how to split the data](#2-why-and-how-to-split-the-data)
  - [3. The precondition of time series forecasting (stationarity)](#3-the-precondition-of-time-series-forecasting-stationarity)
  - [4. SARIMAX and the multiple seasonalities of hourly data](#4-sarimax-and-the-multiple-seasonalities-of-hourly-data)
  - [Suggested reading order](#suggested-reading-order)
  - [Questions to keep in mind](#questions-to-keep-in-mind)

## Overview

> Implemented: daily data (validation 2023, test 2024, h = 1 to 7 days). Not implemented: hourly data. Code: [src/models/sarimax/](../../src/models/sarimax/).

SARIMAX is a linear regression on the exogenous variables X with seasonal ARIMA errors. Two ways to handle the weekly seasonality were compared on the daily data:

| | Model 1 | Model 2 |
|---|---|---|
| Weekly pattern | seasonal difference $\Delta_7$ (D = 1, s = 7) | day-of-week dummies, no differencing |
| Yearly pattern | month dummies | yearly Fourier terms (K = 5 pairs) |
| Chosen orders | (2,0,0)(1,1,1,7) | (1,0,0)(1,0,0,7) |
| Validation RMSE, h = 1 (MWh) | **24,680** | 24,710 |

Model 1 has the lower validation RMSE and is the final SARIMAX model. On the test year 2024 it reaches an RMSE of 29,860 MWh (MAPE 1.74%) at h = 1 and 44,482 MWh (MAPE 2.73%) at h = 7.

Files in `src/models/sarimax/`:

| File | Content |
|---|---|
| `common.py` | Shared helpers: `make_features` (features made in the notebook), `fit_eval` (fit, forecast and metrics), `summarize`, saving and loading of the experiments as JSON |
| `daily.ipynb` | The whole daily analysis: target, features, Model 1, Model 2, comparison, validation and test of the final model |
| `results/daily/model1/`, `model2/` | One JSON per experiment on the validation year (settings, metrics, forecasts, residuals) |
| `results/daily/test/` | The test run of the final model (JSON) |
| `results/daily/model1/sarimax_daily_{1d,7d}_val.csv`, `results/daily/test/sarimax_daily_{1d,7d}_test.csv` | Forecasts of the final model in the shared format of [MODELS - Forecast files](../MODELS.md#forecast-files): `origin` (day of the first step), `target_time`, `step`, `y_true`, `y_pred`, `q0.1` to `q0.9` |

## How to run

Open `src/models/sarimax/daily.ipynb` with the project environment (`uv sync`) and run all cells; the notebook imports `common.py` from its own folder. A fit takes from a few seconds to about a minute; the whole notebook runs in a few minutes on a laptop CPU.

Every call of `fit_eval` returns a dict with the metrics, the forecasts (`y_hat`, and `y_hat_h` for h = 1 to 7), the residuals and the settings of the run. `save_results` writes one JSON per experiment, so running a cell again replaces only its own experiments.

## Preprocessing

### Features

Daily data, index `date_from` (the local date). Target `actual_consumption` (MWh).

Two features are made in the notebook (`make_features`), they are not in `final/`:

| Feature | Definition | Why |
|---|---|---|
| `is_holiday_weekday` | `is_holiday` × `is_weekday` | A holiday on a weekday lowers the load much more than a holiday on a weekend. With `is_holiday` it separates the two effects |
| `solar_generation_proxy` | `solar_capacity_mw` × `shortwave_radiation_sum` | Solar generation behind the meter lowers the measured load; the proxy follows both the weather and the growth of the installed capacity |

X used by both models:

| Group | Columns |
|---|---|
| Calendar | `is_holiday`, `is_holiday_weekday`, `weighted_regional_holiday`, `weighted_school_holiday`, `is_bridge_day`, `is_christmas_new_year`, `is_dst_transition_day` |
| Economy and price | `industrial_confidence`, `ipi_ei_level`, `day_ahead_price_mean` |
| Weather and solar | `hdd`, `wind_speed_10m_mean`, `precipitation_sum`, `solar_generation_proxy` |
| Policy | `oxcgrt_stringency` |
| Model 1 only | `is_dst`, month dummies (`month_2` to `month_12`) |
| Model 2 only | day-of-week dummies (`dow_1` to `dow_6`), `sin_y1`, `cos_y1` to `sin_y5`, `cos_y5`, a constant |

The X were chosen once, before any model was fitted, from the correlation matrix and the VIF of all candidate features on 2019 - 2023, and in agreement with the tree-based model. There is no ablation afterwards.

### Excluded features

| Feature | Excluded from | Evidence | Reason |
|---|---|---|---|
| `shortwave_radiation_sum` | all models | VIF 46.4; r = 0.96 with the proxy | Nearly the same information as `solar_generation_proxy`, which is kept |
| `solar_capacity_mw` | all models | VIF 6.2 | Contained in the proxy; on its own a slowly rising trend |
| `daylight_duration` | all models | VIF 12.1; r = 0.92 with radiation | A function of the day of the year, already in the Fourier terms and month dummies. The tree-based model leaves it out as well |
| `gas_price_eu_usd` | all models | r = 0.88 with `day_ahead_price_mean` | Little information beyond the electricity price. The tree-based model leaves it out as well |
| `is_weekday` | all models | exact collinearity | Replaced by `is_holiday_weekday`. A linear combination of the day-of-week dummies (Model 2), zero after $\Delta_7$ (Model 1) |
| `is_dst` | Model 2 | collinear with `cos_y1` | Daylight saving time covers the same half of the year as the first Fourier pair |
| `generation_*` | all models | – | Leakage |

The VIF values are computed without the Fourier terms and dummies.

### Stationarity

- The target in levels: ADF rejects a unit root, but KPSS rejects stationarity (p < 0.01), because of the strong weekly and yearly seasonality. After the seasonal difference $\Delta_7$ both tests agree that it is stationary (ADF p < 0.001, KPSS p ≥ 0.10).
- Five X are not stationary in levels (`industrial_confidence`, `ipi_ei_level`, `day_ahead_price_mean`, `solar_generation_proxy`, `oxcgrt_stringency`) and stationary after $\Delta_7$. This is enough for Model 1, which differences y and X.
- Model 2 is a regression in levels, which is only valid if y and the non-stationary X are co-integrated (FPP3 §10.1). The residuals of the regression without ARMA terms are stationary (ADF p < 0.001, KPSS p = 0.083 with the final X), so the levels model is used without differencing.

## Normalization

- The continuous X (more than two distinct values) are standardized to mean 0 and standard deviation 1 with the mean and standard deviation of the fit period only (2019 - 2022 for validation, 2019 - 2023 for the test). Dummies stay 0 / 1.
- The target is fitted in GWh (`y_scale = 1000`). In MWh the optimizer can stop at its start values without a single step and still report convergence. Forecasts and errors are given back in MWh; AIC and BIC refer to the GWh scale.
- Unscaled X cause the same optimizer problem, which is another reason for the standardization.

## Training and evaluation

### Forecast protocol

- **Fit once, no refit.** Validation: fit on 2019 - 2022, forecast 2023. Test: fit once more on 2019 - 2023 with the chosen specification, forecast 2024. The parameters stay fixed during the forecast year.
- **Rolling origin, h = 1 to 7 days.** Every day is a forecast origin. From an origin the model forecasts the next 7 days with the actual load up to the day before and the actual X of the forecast days (ex-post). From the second step on, the lagged load is the model's own forecast (recursive). As in the shared setup, the 7-day forecasts are only evaluated for origins whose whole horizon lies inside the year (359 origins in 2023, 360 in 2024); the 1-day forecasts for every day.
- **Quantiles.** Normal quantiles from the forecast standard error of the state space model (given the parameters and the X).
- **Model choice by the RMSE at h = 1 on the validation year.** The specification with the lowest RMSE is chosen, without a tie rule. AIC and BIC are reported, but only compared between specifications with the same differencing.
- **Optimizer.** L-BFGS with up to 1,000 iterations and 50,000 likelihood evaluations. The default limit of 15,000 evaluations is used up after about 280 iterations with 45 parameters (the gradient is numerical). A larger specification starts from the estimates of the simpler one that it contains (new terms at 0), so its likelihood cannot end below it.

### Model 1: seasonal difference

Candidate orders from the ACF and PACF of the residuals of the initial specification (1,0,0)(0,1,1,7), which leaves a spike at the seasonal lag 7:

| Specification | AIC | BIC | RMSE | MAPE |
|---|---:|---:|---:|---:|
| **(2,0,0)(1,1,1,7)** | 13,669 | 13,838 | **24,680** | 1.53% |
| (1,0,0)(1,1,1,7) | 13,667 | 13,831 | 24,680 | 1.53% |
| (1,0,0)(0,1,1,7) | 13,718 | 13,877 | 25,228 | 1.54% |
| (2,0,0)(0,1,1,7) | 13,720 | 13,884 | 25,241 | 1.54% |

Baselines on the validation year: seasonal naive RMSE 81,772 (MAPE 4.12%), SARIMA (1,0,0)(0,1,1,7) without X RMSE 49,519 (MAPE 2.50%).

- The seasonal AR term removes the autocorrelation at lag 7 and lowers the RMSE by about 550 MWh. The second AR term of the chosen specification is close to zero (0.009, p = 0.62), so it is practically the same model as (1,0,0)(1,1,1,7).
- The seasonal MA coefficient is −0.957. It nearly cancels the seasonal difference, the typical sign of over-differencing: the weekly pattern is closer to deterministic than to stochastic seasonality. This motivated Model 2. It also makes the likelihood flat and the fit slow.
- Residuals: Ljung-Box does not reject at lag 7 (p = 0.12) but at lags 14 and 28 (small autocorrelations at lags 8 to 11). Heavy tails; 11 of the 15 largest residuals fall between 23 December and 2 January. ADF rejects a unit root; KPSS rejects stationarity at 5% but not at 1% (p = 0.016).

### Model 2: regression in levels

- Orders from the ACF and PACF of the regression residuals (PACF spike at lag 1 and at lag 7): (1,0,0)(1,0,0,7) and (1,0,1)(1,0,0,7) with K = 10. (1,0,0)(1,0,0,7) has the lower RMSE (24,690 vs. 24,693); the MA term of the other is not significant (0.017, p = 0.56).
- K from 1 to 10 with these orders: K = 5 has the lowest RMSE (24,710) and MAPE (1.52%). AIC would choose K = 9, BIC K = 1.
- Residuals: the same remaining autocorrelation at lags 8 to 11 as in Model 1, so it more likely comes from the shared X (holiday periods) than from the orders. The residual mean drops to about −9 GWh in spring 2020 (first COVID lockdown) and to about −10 GWh in autumn 2022 (energy crisis): the X do not fully describe these drops in demand. Without differencing, Model 2 carries such a level shift only through its AR terms.

### Model 1 vs. Model 2

| Model | RMSE (h = 1) | MAPE (h = 1) |
|---|---:|---:|
| **Model 1**: (2,0,0)(1,1,1,7), month dummies | **24,680** | 1.53% |
| Model 2: (1,0,0)(1,0,0,7), day-of-week dummies, K = 5 | 24,710 | 1.52% |

Model 1 is chosen by the rule (lower RMSE). The two models are very close at h = 1. AIC and BIC are not comparable, since the models have different differencing. Only Model 1 is evaluated at h = 2 to 7 and on the test year.

### Final model: validation and test

1-day forecasts, every day of the year:

| | RMSE | MAPE | 80% interval coverage |
|---|---:|---:|---:|
| Validation 2023 | 24,680 | 1.53% | 85.8% |
| Test 2024 | 29,860 | 1.74% | 80.6% |

7-day forecasts by step, over the origins whose whole horizon lies inside the year (359 in 2023, 360 in 2024); bias = mean of actual − forecast (negative: the model overestimates):

| Step | Validation 2023 RMSE | MAPE | Bias | Test 2024 RMSE | MAPE | Bias |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 23,871 | 1.50% | −791 | 28,716 | 1.69% | +1,265 |
| 2 | 31,786 | 2.00% | −1,262 | 36,350 | 2.11% | +2,686 |
| 3 | 34,930 | 2.21% | −1,632 | 37,880 | 2.29% | +4,134 |
| 4 | 36,121 | 2.29% | −1,944 | 39,718 | 2.39% | +5,293 |
| 5 | 37,251 | 2.37% | −2,288 | 42,448 | 2.55% | +6,481 |
| 6 | 38,247 | 2.42% | −2,186 | 43,412 | 2.63% | +7,119 |
| 7 | 39,910 | 2.52% | −2,167 | 44,482 | 2.73% | +7,304 |

80% interval coverage of the 7-day forecasts (all steps): 86.2% (validation), 82.1% (test).

- The largest step is from step 1 to step 2 (+33% validation, +27% test), when the model has to use its own forecast instead of the actual load of the day before.
- The test errors are higher than the validation errors; the validation year was used to choose the model.
- On the test year the model underestimates the load, increasingly with the horizon (at step 7 the bias is about 16% of the RMSE).
- The normal 80% intervals are not too narrow despite the heavy-tailed residuals: the extreme residuals (Christmas, holidays) enlarge the estimated variance, so the intervals are wide enough on ordinary days (on the validation year even somewhat too wide).
- MAE, the skill against the seasonal naive forecast and the pinball loss are computed by the shared evaluation script from the forecast files.

## Deviations from the shared setup

The [shared setup](../MODELS.md#shared-setup) is a proposal of 2026-10-27. The SARIMAX work follows the later team decisions where they differ:

| Shared setup | SARIMAX | Effect |
|---|---|---|
| Daily horizons 7 d and 30 d | h = 1 to 7 days, each reported | The 7 d horizon is covered; 30 d is not |
| Main metric MAE; skill vs. seasonal naive; pinball loss and coverage | Model choice by RMSE (and MAPE, bias) | The forecast files have the shared format with normal quantiles, so the shared evaluation script computes MAE, skill, pinball loss and coverage as for the other models |
| Weather variant B (realistic) for the main results | Observed weather for all horizons (variant A, ex-post) | Optimistic, more so at longer horizons |
| `day_ahead_price_mean` only for the next day | Used at all horizons (ex-post) | Optimistic for h ≥ 2 |
| Policy and economy columns: last value known at the origin | Value of the forecast day | Small effect: they change at most a few times per month |

## Limitations and open questions

- **Hourly data** is not done yet.
- **Holiday periods.** The largest errors fall between Christmas and New Year and on regional holidays; the remaining autocorrelation at lags 8 to 11 probably comes from there as well.
- **Prediction intervals.** Normal intervals from the model; the 80% interval covers 80 - 86% of the actual values, but the residuals are heavy-tailed, so more extreme quantiles (e.g. 1% / 99%) would likely be too narrow. The intervals ignore the uncertainty of the parameters and of the X.
- **Level shifts.** COVID 2020 and the 2022 energy crisis are not fully described by the X; the test-year underestimation may come from the recovery of the demand in 2024 (not checked).
- **Ex-post X.** See the deviations above; a realistic comparison needs the weather and price inputs as known at the origin.

## Learning resources

Collected on 2026-10-25. Every link was checked to open (status 200), but not every article was read in full; the quality is judged from the title and the summary. FPP3, the free online textbook by Hyndman and Athanasopoulos (in English), is the main reference below.

### 1. How to choose the seasonal period

- [FPP3 chapter 9: ARIMA (section Seasonal ARIMA)](https://otexts.com/fpp3/seasonal-arima.html) (English)
- [Identifying seasonality with ACF/PACF plots](https://apxml.com/zh/courses/time-series-analysis-forecasting/chapter-5-seasonal-arima-sarima/identifying-seasonal-components) (Chinese): the period from the ACF peaks at m, 2m, 3m
- [Choosing the order of a SARIMA model](https://apxml.com/zh/courses/time-series-analysis-forecasting/chapter-5-seasonal-arima-sarima/selecting-sarima-order) (Chinese): p, d, q, P, D, Q from the ACF and PACF

### 2. Why and how to split the data

- [FPP3 chapter 5: Evaluating forecast accuracy (training and test sets)](https://otexts.com/fpp3/accuracy.html) (English)
- [FPP3 chapter 5: Time series cross-validation](https://otexts.com/fpp3/tscv.html) (English): the rolling origin
- [scikit-learn: TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) (English, official documentation): note the `gap` parameter
- No good Chinese article on "why the data can not be split at random" was found; the three English sources above cover this topic.

### 3. The precondition of time series forecasting (stationarity)

- [FPP3 chapter 9: Stationarity and differencing](https://otexts.com/fpp3/stationarity.html) (English)
- [Day 14: Time series forecasting – ARIMA and Prophet](https://ithelp.ithome.com.tw/articles/10360722) (Chinese, iThome)
- [#15 ARIMA tutorial](https://ithelp.ithome.com.tw/articles/10274628) (Chinese, iThome)
- [20 basic concepts of time series](https://ithelp.ithome.com.tw/articles/10398745) (Chinese, iThome)
- [The basics of time series analysis (introduction)](https://zenn.dev/t_shi/articles/7bc8787f4477b4) (Japanese, Zenn): from ACF/PACF, differencing and the ADF test to SARIMA

The iThome articles are personal posts from a writing contest and vary in quality; read them together with FPP3.

### 4. SARIMAX and the multiple seasonalities of hourly data

- [statsmodels: SARIMAX Introduction](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_stata.html) (English, official example): includes an example with exogenous variables (`exog`)
- [FPP3 chapter 10: Dynamic regression models](https://otexts.com/fpp3/regarima.html) (English): regression with ARIMA errors, the idea behind SARIMAX
- [FPP3 12.1 Complex seasonality](https://otexts.com/fpp3/complexseasonality.html) (English): the standard approach to multiple seasonalities, with Fourier terms
- [FPP2 9.5 Dynamic harmonic regression](https://otexts.com/fpp2/dhr.html) (English): why seasonal ARIMA suits short periods such as 12 or 4, and long periods need Fourier terms
- [statsmodels: Deterministic Terms in Time Series Models](https://www.statsmodels.org/dev/examples/notebooks/generated/deterministics.html) (English, official example): Fourier terms with `DeterministicProcess`

No Chinese resources on multiple seasonalities were found; this topic is only covered in English.

Hint (inferred from the FPP approach, not read in the statsmodels documentation; rely on what you read): the statsmodels SARIMAX takes only one seasonal period at a time, so for two periods (daily 24, weekly 168) one of them is usually replaced by Fourier terms in `exog`.

### Suggested reading order

1. FPP3 on stationarity and differencing (9.1), then seasonal ARIMA (9.9)
2. FPP3 chapter 5 on the training / test split and cross-validation
3. The statsmodels SARIMAX Introduction (run it once yourself)
4. FPP3 12.1 and the statsmodels Deterministic Terms (multiple seasonalities of the hourly data)

### Questions to keep in mind

- Our hourly `date_from` repeats 02:00 in autumn and skips an hour in spring, so it is not evenly spaced; `date_from_utc` is a continuous hourly series. Time series models and `TimeSeriesSplit` assume even spacing: which column should be the time axis?
- Are the "future" values of the exogenous variables (weather, day-ahead price, ...) available at forecast time? FPP calls this ex-ante vs. ex-post forecasts, discussed in chapter 10.
- The definitions of these columns, and which ones leak the target, are in [FEATURES](../FEATURES.md) (columns Model and Notes).
