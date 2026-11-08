# Neural models (N-HiTS, NBEATSx)

[README](../../README.md) · [FEATURES](../FEATURES.md) · [FEATURE_ENGINEERING](../FEATURE_ENGINEERING.md) · [EDA](../EDA.md) · [MODELS](../MODELS.md)

Models: [SARIMAX](SARIMAX.md) · [TREES](TREES.md) · **NEURAL** · [FOUNDATION](FOUNDATION.md)

## Navigator

- [Overview](#overview)
- [Preprocessing](#preprocessing)
  - [Data format](#data-format)
  - [Inputs per horizon](#inputs-per-horizon)
  - [Derived inputs](#derived-inputs)
- [Normalization](#normalization)
- [Training and evaluation](#training-and-evaluation)
  - [Settings](#settings)
  - [Tuning](#tuning)
  - [Final training and test](#final-training-and-test)
  - [Evaluation](#evaluation)
  - [Experiments](#experiments)
- [Open questions](#open-questions)

## Overview

> Not implemented yet. Code: [src/models/neural/](../../src/models/neural/).

Two neural networks of the same family (stacks of MLP blocks), trained from scratch on our **hourly** data.

| Model | Main use | Horizons | Library |
|---|---|---|---|
| N-HiTS | main neural model, long horizon | 168 h (and 24 h) | [`neuralforecast`](https://github.com/Nixtla/neuralforecast) `NHITS` |
| NBEATSx | 24 h, and the interpretable split into trend / seasonality / covariates | 24 h (and 168 h) | `neuralforecast` `NBEATSx` |

- Split, horizons, forecast origins, input columns, metrics and baselines: [MODELS - Shared setup](../MODELS.md#shared-setup). This document only has what is specific to the neural models.
- **Hourly only.** 2192 daily rows are too few to train these networks. The daily 7 d forecast can be made by summing the hourly 168 h forecast per local day (experiment N8).
- N-HiTS is also the model for the **ablation tests** of the hourly data ([FEATURES - Ablation](../FEATURES.md#ablation)), because one run takes only minutes.
- Hardware: RTX 3090 (24 GB). Rough estimate (not measured): 1 - 5 min per training run, both also train on a CPU (~5 - 20 min).

Planned files in `src/models/neural/`:

| File | Content |
|---|---|
| `data.py` | Load `final/data_hourly.csv`, select and encode the columns, build the `neuralforecast` DataFrames |
| `tune.py` | Hyperparameter search on the validation year (`AutoNHITS`, `AutoNBEATSx`) |
| `train.py` | Final training on 2019 - 2023 with the chosen settings |
| `predict.py` | Forecasts for all origins of the test year, written in the shared forecast file format |


## Model descriptions

### N-HiTS

**Neural Hierarchical Interpolation for Time Series** (Challu et al., AAAI 2023). Main deep learning model for the **hourly** data, especially the 168 h horizon.

**How it works**
- A stack of small MLP blocks, no recurrent layers and no attention.
- Each block first pools the input window to a coarser resolution (multi-rate sampling). One block sees the hourly detail, another one the daily and weekly shape.
- Each block predicts only a few points of the horizon and interpolates between them (hierarchical interpolation). The forecasts of all blocks are added up.
- So the cost grows about linearly with the lookback and the horizon: a 168 h horizon costs hardly more than 24 h.

**Why it fits**
- Built for long horizons, the 168 h forecast is its home ground.
- Every input window is normalised on its own (`scaler_type`), so level shifts (COVID 2020, the demand drop of 2022) hurt less than in a model scaled once over the whole history.
- Takes the three kinds of inputs of the feature table: known future (`futr_exog`), past only (`hist_exog`) and static (`stat_exog`).
- Cheap: about 1 - 5 min per run on an RTX 3090 (rough estimate, not measured), so all ablation tests of [FEATURES](FEATURES.md#ablation) can be run with it. It also trains on a CPU (~5 - 20 min per run).

**Inputs**
- Target history: the last 336 - 504 h (2 - 3 weeks) as a starting point.
- Known future: the calendar columns, `solar_capacity_mw`, the weather columns (forecast, see [Shared setup](#shared-setup)), `day_ahead_price` only for the 24 h horizon.
- Past only: shifted `generation_*`, `gas_price_eu_usd`, `oxcgrt_stringency`, `ipi_ei_level`.
- Everything numeric: `day_of_week_raw` one-hot or as sine / cosine (drop the text column `day_of_week`), booleans as 0 / 1, no audit columns (`ipi_ei_ref_month` etc.).

**Output**: quantiles with `MQLoss` (or a distribution with `DistributionLoss`), adds little training time.

**Library**: [`neuralforecast`](https://github.com/Nixtla/neuralforecast) (`NHITS`).

**Weak points**
- Holidays and other rare days (~10 national holidays a year, bridge days, Christmas) can be smoothed out. Check the residuals on `is_holiday`, `is_bridge_day` and `is_christmas_new_year` days.
- A 2 - 3 week lookback can not see the annual cycle: the season comes from the covariates (`month`, `hdd`, `is_day`). Do not remove them in an ablation without expecting a loss.
- Covariates are flattened into the input of the first layer, so the number of parameters grows with lookback × number of covariates. One series only: use dropout, weight decay and early stopping.
- Interactions (rooftop solar lowers the midday load) are learned better with an explicit feature, e.g. `solar_capacity_mw × shortwave_radiation`.

### NBEATSx

**Neural Basis Expansion Analysis with exogenous variables** (Olivares et al., International Journal of Forecasting 2023). Second neural model for the **hourly** data, mainly for the 24 h horizon and to explain the forecast.

**How it works**
- The same family as N-HiTS: stacks of MLP blocks. Each block removes what it explains from the input (backcast) and adds its part to the forecast.
- Each block projects onto a basis. In the **interpretable** setup the stacks use fixed bases: a polynomial for the trend, a Fourier series for the seasonality, and a stack for the exogenous variables. The forecast can then be split into trend + seasonality + covariate effect.
- The generic setup (learned bases) is usually a bit more accurate, the interpretable one easier to explain.

**Why it fits**
- It was introduced for electricity price forecasting with exogenous variables. The load is a close case: strong daily and weekly cycles, calendar effects, weather-driven deviations.
- Strong at 24 h.
- The split into trend / seasonality / covariates is useful for the report and next to the ablations.

**Inputs and output**: the same as [N-HiTS](#n-hits). **Library**: `neuralforecast` (`NBEATSx`). **Cost**: similar to N-HiTS, a few minutes per run.

**Weak points**: the same as N-HiTS. For long horizons (168 h) N-HiTS is usually better and faster, because NBEATSx predicts every point of the horizon directly.


## Preprocessing

### Data format

`neuralforecast` uses one long DataFrame:

| Column | Content |
|---|---|
| `unique_id` | one constant value, e.g. `DE_LU` (one series) |
| `ds` | `date_from_utc` (continuous in UTC, no DST gaps or doubles) |
| `y` | `actual_consumption` (MWh) |
| other columns | the covariates, numbers only |

Steps:
1. Read `src/data/final/data_hourly.csv`, sort by `date_from_utc`, check that every step is exactly 1 h (52608 rows).
2. Select the columns of the input table in the [shared setup](../MODELS.md#model-inputs) for the horizon.
3. Encode: booleans as 0 / 1, `day_of_week_raw` and `month` as sine / cosine pairs (drop the text column `day_of_week`), no audit or auxiliary columns.
4. Check for missing values (`df.isna().sum()`) and stop if there are any.
5. The covariates are split into two lists in the model:
   - `futr_exog_list`: known for the whole horizon. At prediction time they are passed in `futr_df` (one row per future hour).
   - `hist_exog_list`: known only up to the origin. The model only reads their values inside the lookback window.

### Inputs per horizon

| Group | Columns | List | 24 h | 168 h |
|---|---|---|---|---|
| Calendar | `month` (sin / cos), `day_of_week_raw` (sin / cos), `is_holiday`, `is_weekday`, `weighted_regional_holiday`, `weighted_school_holiday`, `is_bridge_day`, `is_christmas_new_year`, `is_dst`, `is_dst_transition_day` | futr | ✓ | ✓ |
| Hour of day | `hour_sin`, `hour_cos` (see [Derived inputs](#derived-inputs)) | futr | ✓ | ✓ |
| Solar capacity | `solar_capacity_mw` | futr | ✓ | ✓ |
| Sun position | `is_day` | futr | ✓ | ✓ |
| Weather | `hdd`, `shortwave_radiation`, `wind_speed_10m`, `precipitation` | futr (observed or forecast, see the [weather protocol](../MODELS.md#weather-protocol)) | ✓ | ✓ |
| Day-ahead price | `day_ahead_price` | futr | ✓ | ✗ |
| Gas price | `gas_price_eu_usd` | hist | ✓ | ✓ |
| Policy | `oxcgrt_stringency`, `ipi_ei_level` | hist | ✓ | ✓ |
| Generation | `generation_*` | hist, shifted by 24 h | ablation 5 | ablation 5 |

- `generation_*` as a past covariate only uses values before the origin. They are still shifted by 24 h because SMARD publishes the generation with a delay, so the hours just before the origin are not known yet in practice.
- The calendar columns ablated in tests 1 and 2 (`weighted_*`, `is_dst*`) and the others (3, 4, 6 - 8) follow [FEATURES - Ablation](../FEATURES.md#ablation).

### Derived inputs

Made in `data.py` (not in `final/`):

- **Hour of day**: `final/` has no hour-of-day column. The networks can learn the daily shape from the load history, but a known hour feature helps, especially at the start of the horizon. `hour_sin`, `hour_cos` from the **local** hour of `date_from` (the load follows the local clock). If it helps, move it into [calendar_pipeline.py](../../src/feature_engineering/calendar_pipeline.py) so the other models get it too.
- **Solar interaction** (optional): `solar_capacity_mw × shortwave_radiation`, a proxy for the rooftop solar that lowers the measured midday load. Easier for the network than learning the product. Test it like an ablation.

## Normalization
 
Two ways, the first is the default:
 
**A. Global scaling by hand (default)**
- Model: `scaler_type="identity"` (no window scaling).
- In `data.py`: standardise the target and the continuous covariates (weather, prices, `solar_capacity_mw`, policy indexes) with mean / std **fitted on the training rows only** (2019 - 2022 for tuning, 2019 - 2023 for the final training). Binary columns stay 0 / 1, sine / cosine columns stay as they are.
- Transform the forecasts back to MWh by hand (`y * std + mean`, also for every quantile).
- Do not use `local_scaler_type` of `NeuralForecast` together with `cross_validation`: in `neuralforecast` 3.3.0 the no-refit cross-validation fits these scalers on the whole `df`, test rows included.

**B. Window scaling (`scaler_type="robust"` or `"standard"`)**, only as an experiment
- `neuralforecast` scales the target **and all temporal covariates** of a window with the median / MAD (`robust`) or mean / std (`standard`) of the **lookback part only**, then applies them to the horizon too. It scales the forecast back itself.
- Good for the target (level shifts like COVID 2020 and the 2022 drop hurt less), bad for two kinds of covariates (checked in the `neuralforecast` 3.3.0 code, `robust_statistics`):
  - **Rare binary columns** (`is_holiday`, `is_bridge_day`, `is_christmas_new_year`, `is_dst`, `is_dst_transition_day`): with no holiday in the 336 h lookback, the spread is 0, the scale becomes `eps = 1e-6`, and a holiday hour in the horizon enters the network as **1 000 000**. With one holiday day in the lookback it is 5.76, with two 4.24. The same holiday gets a different value in every window.
  - **Slow columns** (`month`, `gas_price_eu_usd`, `solar_capacity_mw`, `ipi_ei_level`, `oxcgrt_stringency`): almost constant in a window, so they become ~0 after removing the median. Their level, the information they carry, is lost.
- Compare A and B once on the validation year (N10). Keep B only if it is clearly better.

Never fit a scaler on validation or test rows.

## Training and evaluation

### Settings

Starting points, to be tuned (see [Tuning](#tuning)):

| Setting | N-HiTS | NBEATSx |
|---|---|---|
| `h` | 168 (and 24) | 24 (and 168) |
| `input_size` (lookback) | 336 h (try 168, 504, 672) | 168 h (try 336) |
| Stacks | 3 stacks, 1 block each | interpretable: `stack_types=["trend", "seasonality", "exogenous"]`; generic: 3 × `"identity"` |
| Layers | `mlp_units = 3 × [512, 512]` | `mlp_units = 3 × [512, 512]` |
| Multi-rate | `n_pool_kernel_size=[16, 8, 1]`, `n_freq_downsample=[24, 12, 1]` (168 h) / `[8, 4, 1]` (24 h) | — (interpretable: `n_harmonics`, `n_polynomials`) |
| `scaler_type` | `robust` | `robust` |
| Loss | `MQLoss(quantiles=[0.1, 0.2, ..., 0.9])` | same |
| `learning_rate` | 1e-3 | 1e-3 |
| `max_steps` | 2000, early stopping on the validation loss | same |
| `dropout_prob_theta` | 0.1 | 0.1 |
| `windows_batch_size` | 256 | 256 |
| `random_seed` | 3 seeds (see below) | same |

The quantiles 0.1 ... 0.9 are the same as the 9 quantiles of TimesFM-3, so the pinball loss can be compared directly.

### Tuning

- `AutoNHITS` / `AutoNBEATSx` (Optuna backend), 20 - 30 trials per model and horizon.
- Training data 2019 - 2022, forecasts at the daily origins of 2023 (validation year), selection by the mean pinball loss.
- Search space: `input_size`, `n_freq_downsample`, `mlp_units`, `learning_rate`, `dropout_prob_theta`, `scaler_type`.
- Note the number of training steps of the best trial (the step where early stopping stopped). It is used for the final training.
- The ablation tests run on the same setup with the best settings, one test = one retraining.
- Rough estimate (not measured): 1 - 3 GPU hours for the whole search of both models and both horizons.


### Final training and test
 
- Train once on **2019 - 2023** with the chosen settings and the **fixed number of steps** from the tuning. There is no validation year left for early stopping, so the step count is taken from the tuning.
- Forecast all origins of 2024 without retraining (rolling origin, see the [shared setup](../MODELS.md#horizons-and-forecast-origins)). For each origin: the history before it, plus `futr_df` with the known covariates of the next `h` hours.
- Two ways to run the rolling origins:
  - `NeuralForecast.cross_validation(df, n_windows=..., step_size=24, test_size=8784, refit=False)`: one call for all origins of 2024. Two limits: the origins stay at a fixed UTC hour (see [Open questions](#open-questions)), and the future covariates are read from `df`, so every hour has one weather value whatever the lead time. That is fine for weather variant A (observed), not for variant B (forecast issued at each origin).
  - A loop over the origins with `nf.predict(df=history, futr_df=...)`: origins exactly at local midnight, and `futr_df` can hold the weather forecast of that origin. Needed for variant B. 366 calls, fast because nothing is trained.
- **3 seeds**: report mean ± std of the metrics. The mean of the 3 forecasts (a small ensemble) can be reported as an extra line.
- Write the forecasts in the [shared forecast file format](../MODELS.md#forecast-files): rename the quantile columns of `neuralforecast` to `q0.1` ... `q0.9` and the median to `y_pred`.

### Evaluation

The protocol and metrics of the [shared setup](../MODELS.md#metrics). Specific to the neural models:

- **Residuals by day type**: holidays, bridge days and Christmas are rare in the training data (~10 national holidays a year), so check the error on these days separately. If they are clearly worse than on normal days, the tree models may be better there.
- **NBEATSx decomposition**: plot the trend, seasonality and exogenous parts of a few forecasts (a normal week, a holiday week, a cold week). The exogenous part shows what the covariates add.
- **Interpretable vs generic NBEATSx**: report both. The generic one is usually a bit more accurate.
- **Covariate gain**: N-HiTS also without covariates (load history only).

### Experiments

| # | Model | Horizon | Variant | Purpose |
|---|---|---|---|---|
| N1 | N-HiTS | 168 h | all inputs | main result, long horizon |
| N2 | N-HiTS | 24 h | all inputs | comparison with NBEATSx |
| N3 | NBEATSx interpretable | 24 h | all inputs | main result, short horizon, decomposition |
| N4 | NBEATSx generic | 24 h | all inputs | accuracy of the generic setup |
| N5 | NBEATSx (best of N3 / N4) | 168 h | all inputs | completeness |
| N6 | N-HiTS | 24 h, 168 h | no covariates | covariate gain |
| N7 | N-HiTS | 168 h | ablation tests 1 - 8, hour of day, solar interaction | feature selection (validation year) |
| N8 | N-HiTS | 168 h summed per local day | all inputs | daily 7 d forecast, compared with TimesFM-3 / TabICL / trees |
| N9 | N-HiTS | 24 h, 168 h | weather variant A vs B | effect of weather forecast errors |
| N10 | N-HiTS | 24 h, 168 h | global scaling vs window scaling (`robust`) | choice of the normalization (validation year) |

- **Origin time and DST**: the shared setup puts the origin at 00:00 local time. In UTC that is 23:00 in winter and 22:00 in summer. `cross_validation(step_size=24)` keeps a fixed UTC hour, so half of the year the origin would be at 01:00 local. Either loop over the origins with `predict()`, or agree for all models on a fixed UTC origin (e.g. 23:00 UTC). For N8 (daily sums) the origin must be at local midnight.
- **Hour of day**: add `hour_sin` / `hour_cos` to the calendar pipeline for all models, or keep it here only?
- **Publication delay of the generation data**: is 24 h enough? (Only matters if ablation 5 keeps the generation columns.)