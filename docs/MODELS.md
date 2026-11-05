# Models

[README](../README.md) · [FEATURES](FEATURES.md) · [FEATURE_ENGINEERING](FEATURE_ENGINEERING.md) · [EDA](EDA.md) · **MODELS**

## Navigator

- [Overview](#overview)
- [Shared setup](#shared-setup)
- [Comparison](#comparison)

## Overview

> Placeholder. The models are not implemented yet.

Target: `actual_consumption` (daily and hourly). Input: `src/data/final/data_daily.csv` and `data_hourly.csv` (see [FEATURE_ENGINEERING](FEATURE_ENGINEERING.md)), with the columns described in [FEATURES](FEATURES.md).

Each model has its own document (preprocessing, normalization, training and evaluation), so they can be edited without conflicts.

| Model | Document | Code | Status |
|---|---|---|---|
| SARIMAX | [models/SARIMAX.md](models/SARIMAX.md) | [src/models/sarimax/](../src/models/sarimax/) | placeholder |
| Tree based | [models/TREES.md](models/TREES.md) | [src/models/trees/](../src/models/trees/) | placeholder |
| Neural (N-HiTS, NBEATSx) | [models/NEURAL.md](models/NEURAL.md) | [src/models/neural/](../src/models/neural/) | planned |
| Foundation model | [models/FOUNDATION.md](models/FOUNDATION.md) | [src/models/foundation/](../src/models/foundation/) | placeholder |

## Shared setup

> Proposal of 2026-10-27, to be confirmed by the team. Every model (SARIMAX, trees, N-HiTS / NBEATSx, foundation models) uses this setup, so the results in [Comparison](#comparison) can be compared.

### Time index

- Hourly: `date_from_utc`, continuous in UTC (52608 rows, no DST gaps or doubles). Horizons are counted in UTC hours, so a 24 h forecast is always 24 steps, also on the days with 23 or 25 local hours.
- Daily: the local date of `date_from` (one row per local day). The daily `date_from_utc` is not a regular 1-day series (local midnight is 23:00 or 22:00 UTC).
- Calendar features stay in local time, they are already in `final/`.

### Horizons and forecast origins

| Resolution | Horizons | Forecast origin | Origins in the test year |
|---|---|---|---|
| Hourly | 24 h, 168 h | every day at 00:00 local time | 366 (24 h), 360 (168 h) |
| Daily | 7 d, 30 d | every day | 360 (7 d), 337 (30 d) |

At the origin, everything before it is known (target and covariates). A forecast is only evaluated when its whole horizon is inside the evaluation period.

### Train / validation / test split

| Part | Period | Use |
|---|---|---|
| Train | 2019-01-01 - 2022-12-31 | fit the models (incl. COVID 2020 and the 2022 energy crisis) |
| Validation | 2023-01-01 - 2023-12-31 | tuning, early stopping, ablations, choice of context length |
| Test | 2024-01-01 - 2024-12-31 | final results, used once |

- Rolling origin: the origins move through the validation or test year day by day. The context of a forecast may reach back into the earlier parts.
- Trained models: tuned with training on 2019 - 2022 and origins in 2023. Then trained **once more on 2019 - 2023** with the chosen settings and evaluated on all 2024 origins, without refitting during 2024.
- Zero-shot models (TimesFM-3, TabICLForecaster) are not trained, they only get the history before each origin.

### Model inputs

Roles: **known** = known for the whole horizon, **forecast** = needs a forecast at prediction time, **past only** = known only up to the origin. ✓ = input, ✗ = not an input for that horizon.

| Group | Columns | Role | 24 h | 168 h | 7 d | 30 d |
|---|---|---|---|---|---|---|
| Target history | `actual_consumption` | past only | ✓ | ✓ | ✓ | ✓ |
| Calendar | `month`, `day_of_week_raw`, `is_holiday`, `is_weekday`, `weighted_regional_holiday`, `weighted_school_holiday`, `is_bridge_day`, `is_christmas_new_year`, `is_dst`, `is_dst_transition_day` | known | ✓ | ✓ | ✓ | ✓ |
| Solar capacity | `solar_capacity_mw` | known | ✓ | ✓ | ✓ | ✓ |
| Sun position | `is_day` (H), `daylight_duration` (D) | known (astronomical, no forecast needed) | ✓ | ✓ | ✓ | ✓ |
| Weather | `hdd`, `shortwave_radiation(_sum)`, `wind_speed_10m(_mean)`, `precipitation(_sum)` | forecast | ✓ | ✓ | ✓ | ✓ (see weather protocol) |
| Day-ahead price | `day_ahead_price` (H), `day_ahead_price_mean` (D) | known for the next day only (published around noon of the day before) | ✓ | ✗ | ✗ | ✗ |
| Gas price | `gas_price_eu_usd` | past only (value of the last published month) | ✓ | ✓ | ✓ | ✓ |
| Policy | `oxcgrt_stringency`, `ipi_ei_level` | past only (last value known at the origin) | ✓ | ✓ | ✓ | ✓ |
| Generation | `generation_*` | past only, never the same hour / day (leakage) | ablation 5 | ablation 5 | ablation 5 | ablation 5 |

#### Never a model input
 
Some columns of `final/` are never given to a model, for one of three reasons:
 
1. **Leakage**: the column contains the target or is measured at the same time as the target. At the forecast origin it is not known for the horizon. A model that gets it would look very good in the evaluation and could not be used for a real forecast.
2. **Duplicate**: the same information is already in another input. A second copy adds no information, but more inputs to fit (more risk of overfitting, less clear ablations).
3. **Not about the load**: keys, the time axis and columns that describe the data itself (where a value comes from, when it was published). They say nothing about the demand, and a model can find false patterns in them.

| Columns | Reason | Why |
|---|---|---|
| `actual_consumption_incl_pumped` | leakage | `actual_consumption + hydro_pumped_storage`, so it contains the target of the same hour / day |
| `hydro_pumped_storage` | leakage | Measured in the same hour as the target and only known after it. Together with `actual_consumption_incl_pumped` it gives the target exactly |
| `residual_load` | leakage | `actual_consumption` minus wind and solar feed-in: built from the target |
| `day_ahead_price_min`, `day_ahead_price_max` | duplicate | The daily data uses `day_ahead_price_mean` (ablation 4 in [FEATURES](FEATURES.md#ablation)). Min and max of the same day move with the mean and add little. Like the mean, they are only known for the next day |
| `oxcgrt_c1_school`, `oxcgrt_c2_workplace`, `oxcgrt_c6_stay_home` | duplicate (auxiliary) | Parts of the measures that `oxcgrt_stringency` sums up. Non-zero only in 2020 - 2022, so three more columns for a short period are an overfitting risk |
| `oxcgrt_observed` | not about the load (audit) | Says whether an OxCGRT value is a source value or filled. It is 1 almost only in 2020 - 2022, so as an input it would be a hidden "pandemic years" flag, not a measure of the restrictions |
| `ipi_ei_mom`, `ipi_ei_yoy` | duplicate (auxiliary) | Percent changes computed from `ipi_ei_level`. Can be tested later if the level helps (ablation 8) |
| `ipi_ei_staleness_days` | not about the load (auxiliary) | Days since the end of the reference month: a saw-tooth that follows the publication dates, not the demand |
| `ipi_ei_ref_month`, `ipi_ei_release_date`, `ipi_ei_release_source` | not about the load (audit) | Text columns to check the release alignment ("as known on day d") |
| `day_of_week` | duplicate | The weekday name as text. Use the number `day_of_week_raw`, encoded as described below |
| `date_from`, `date_to`, `date_from_utc` | not about the load (keys) | The time axis and merge key, one unique value per row. As a feature a model could only learn "a later date", and tree models can not extrapolate it beyond the training years. Time information goes in through the calendar columns (and the models' own time features, e.g. the index feature of TabICLForecaster) |
 
`generation_*` is not in this list: the same-hour values are leakage too, but a shifted version (e.g. the day before) is tested in ablation 5.
 
How a model uses a past-only column depends on the model: sequence models (N-HiTS, NBEATSx, TimesFM-3) take it as a past covariate, tabular models (trees, TabICLForecaster) get the last value known at the origin in every future row. Lags of the target as features (trees, SARIMAX) must be at least the horizon, or the model forecasts step by step.
 
Encoding (every model): booleans as 0 / 1, `day_of_week_raw` and `month` as sine / cosine pairs or one-hot (tree models can use the integers). Scaling is part of each model document.

### Weather protocol

The weather columns in `final/` are observed values. A real forecast only has weather forecasts. Two variants:

| Variant | Future weather | Use |
|---|---|---|
| A: observed (oracle) | the observed values of `final/` | upper bound, easy to run |
| B: realistic | archived weather forecasts as of the origin where they exist for our period, otherwise observed values + noise that grows with the lead time. Daily 30 d: after day 10 the climatological normal (mean of the same calendar day over the training years) | **main results** |

- Variant B needs an extra ETL step that does not exist yet. Until it exists, results are reported with variant A and marked as such.
- `is_day` and `daylight_duration` are astronomical and get no noise.

### Metrics

Computed on the original scale (MWh), over all origins and all steps of the horizon:

| Metric | What it shows |
|---|---|
| **MAE** (MWh) | main metric for the point forecast |
| RMSE (MWh) | weights large errors more |
| MAPE (%) | comparable with other studies (the load is never close to 0) |
| MAE skill vs seasonal naive | `1 - MAE_model / MAE_naive`, > 0 means better than the baseline |
| **Mean pinball loss** over the quantiles 0.1, 0.2, ..., 0.9 | main metric for the probabilistic forecast |
| Coverage of the 80% interval (q0.1 - q0.9) | should be close to 80% |

Also reported:
- by lead time (hourly 168 h: days 1, 2, ..., 7; daily 30 d: weeks 1 - 4),
- by day type: normal weekday, weekend, `is_holiday`, `is_bridge_day`, `is_christmas_new_year`.

### Baselines

- **Seasonal naive**: the last observed week repeated over the horizon (hourly: same hour one week before; daily: same weekday one week before). Every model has to beat it.
- SARIMAX and the tree models are the classical baselines for the neural and foundation models.

### Ablations

The tests of [FEATURES - Ablation](FEATURES.md#ablation) run on the validation year with the fast models: N-HiTS for the hourly data, the tree models for the daily data. The feature set that comes out is used by all models for the test year.

### Forecast files

Every model writes its forecasts in the same format, so one evaluation script computes all metrics:

- one CSV per model, resolution and horizon, e.g. `src/results/forecasts/nhits_hourly_168h.csv`,
- columns: `origin`, `target_time` (`date_from_utc` hourly, local date daily), `step` (1 ... H), `y_true`, `y_pred`, `q0.1`, ..., `q0.9` (quantile columns empty for models without quantiles),
- `y_true` is filled in by the evaluation, not by the model.

### Reproducibility

- Fixed random seeds. Neural models are trained with 3 seeds, reported as mean ± std.

## Comparison

> TBD. Results of the three models on the same split and metrics.

## References

- Challu, C., Olivares, K. G., Oreshkin, B. N., Garza, F., Mergenthaler-Canseco, M., Dubrawski, A. (2023). *N-HiTS: Neural Hierarchical Interpolation for Time Series Forecasting.* AAAI 2023. [arXiv:2201.12886](https://arxiv.org/abs/2201.12886)
- Olivares, K. G., Challu, C., Marcjasz, G., Weron, R., Dubrawski, A. (2023). *Neural basis expansion analysis with exogenous variables: Forecasting electricity prices with NBEATSx.* International Journal of Forecasting 39(2). [arXiv:2104.05522](https://arxiv.org/abs/2104.05522)
- Google Research (2026). *TimesFM-3: A zero-shot foundation model for multivariate forecasting.* Blog post, 2026-08-31. Code: [github.com/google-research/timesfm](https://github.com/google-research/timesfm)
- TabPFN-TS, the model TabICLForecaster is inspired by: [arXiv:2501.02945](https://arxiv.org/abs/2501.02945)
- TabICL: [github.com/soda-inria/tabicl](https://github.com/soda-inria/tabicl)
- Nixtla `neuralforecast`: [github.com/Nixtla/neuralforecast](https://github.com/Nixtla/neuralforecast)