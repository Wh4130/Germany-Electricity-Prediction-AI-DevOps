# Foundation model

[README](../../README.md) · [FEATURES](../FEATURES.md) · [FEATURE_ENGINEERING](../FEATURE_ENGINEERING.md) · [EDA](../EDA.md) · [MODELS](../MODELS.md)

Models: [SARIMAX](SARIMAX.md) · [TREES](TREES.md) · **FOUNDATION**

## Navigator

- [Overview](#overview)
- [Preprocessing](#preprocessing)
  - [Shared steps](#shared-steps)
  - [Covariate roles](#covariate-roles)
  - [TimesFM-3](#timesfm-3-preprocessing)
  - [TabICLForecaster](#tabiclforecaster-preprocessing)
- [Normalization](#normalization)
- [Training and evaluation](#training-and-evaluation)
  - [TimesFM-3: zero-shot](#timesfm-3-zero-shot)
  - [TimesFM-3: fine-tuning](#timesfm-3-fine-tuning)
  - [TabICLForecaster](#tabiclforecaster-runs)
  - [Evaluation](#evaluation)
  - [Experiments](#experiments)
- [Open questions](#open-questions)

## Overview

> Not implemented yet. Code: [src/models/foundation/](../../src/models/foundation/).

Two pretrained models. They forecast without training on our data (zero-shot), TimesFM-3 can also be fine-tuned. 

| Model | Resolution | Horizons | Variants | Package |
|---|---|---|---|---|
| TimesFM-3 (Google Research, 330 M parameters) | hourly, daily | 24 h, 168 h / 7 d, 30 d | zero-shot, fine-tuned (LoRA) | [google-research/timesfm](https://github.com/google-research/timesfm), weights `google/timesfm-3.0-pytorch` |
| TabICLForecaster | daily | 7 d, 30 d | zero-shot only (in-context learning) | `pip install tabicl[forecast]` |

- Split, horizons, input columns, metrics and baselines are the same for all models: [MODELS - Shared setup](../MODELS.md#shared-setup). This document only has what is specific to the foundation models.
- Hardware: RTX 3090 (24 GB). TimesFM-3 needs the GPU for a reasonable speed, TabICL on the daily data also runs on a CPU.
- Licence: the TimesFM-3 weights are under the TimesFM Non-Commercial License v1.0. Fine for this university project.

Planned files in `src/models/foundation/`:

| File | Content |
|---|---|
| `data.py` | Load `final/`, select and encode the columns, build the context and future arrays per forecast origin (shared by both models) |
| `timesfm3.py` | Zero-shot forecast with TimesFM-3 |
| `timesfm3_finetune.py` | LoRA fine-tuning of TimesFM-3 |
| `tabicl_forecaster.py` | Forecast with TabICLForecaster |
| `evaluate.py` | Metrics from the forecast files (or the shared evaluation script, if there is one) |

## Model descriptions

### TimesFM-3

Time series foundation model of **Google Research**, released on 2026-08-31 (~330 M parameters). Used for the **hourly and the daily** data.

**How it works**
- Pretrained on a very large set of real and synthetic series (more than a trillion time points). It forecasts series it has never seen (zero-shot), no training needed.
- Unlike TimesFM 1.0 - 2.5 (univariate, covariates only through an added regression), version 3 is natively multivariate and takes covariates directly: **past-only** covariates and **past-and-future** (known future) covariates.
- Returns a point forecast and quantiles.

**How we use it**
- **Zero-shot**: the history of `actual_consumption` plus the covariates, no training. The baseline.
- **Fine-tuned**: LoRA fine-tuning (Hugging Face Transformers + PEFT, examples in the TimesFM repository) on the training years. A fairer opponent for N-HiTS, which is trained on the same data. Report both.
- Inputs: the same split into known future / past only as for [N-HiTS](#n-hits). Hourly: a context of several weeks to months; daily: the whole training history fits.

**Why it fits**
- Covariates are native, so the `known` and past-only columns can go in as they are.
- The best option for the daily data, where training from scratch does not work.
- Shows how far a pretrained model gets without (or with little) training.

**Weak points / notes**
- **Licence**: the code is Apache-2.0, the pretrained weights are under the TimesFM Non-Commercial License v1.0. Fine for this university project, not for a commercial use.
- Needs a GPU for a reasonable speed (the RTX 3090 is enough, also for LoRA).

**Weights**: [`google/timesfm-3.0-pytorch`](https://huggingface.co/google/timesfm-3.0-pytorch). **Code**: [google-research/timesfm](https://github.com/google-research/timesfm).

### TabICLForecaster

Forecasting interface of [TabICL](https://github.com/soda-inria/tabicl), inspired by TabPFN-TS. Used for the **daily** data, as a challenger (experimental).

**How it works**
- Turns forecasting into tabular regression: one row per timestamp, the target is `actual_consumption`.
- Adds time features by itself (index, calendar, seasonality).
- `TabICLRegressor` is a pretrained tabular model that learns from the history rows "in context" (in-context learning): no gradient training, the history is the input.
- `predict_df` takes a DataFrame with `timestamp` and `target` (and `item_id` for several series). Known future covariates go in through `future_df`. Returns a point forecast and quantile columns.

**Why it fits**
- One row per day matches our daily data and the feature table directly.
- Works in a different way than TimesFM-3. When the two disagree, that is information.
- Small data is its normal use case (2192 rows).

**Weak points / notes**
- **Experimental**: the TabICL docs say the forecasting interface is new and not yet evaluated on a large public benchmark. Treat it as a challenger, not as the main model.
- **Flat extrapolation**: tabular models tend to continue with values they have seen. After a level shift (like the 2022 demand drop) it can lag behind.
- **Duplicate features**: its own calendar features overlap with our calendar columns. Check if the duplicates hurt (with and without our calendar columns).
- Same contamination question as TimesFM-3 for the pretrained part, less likely for a tabular model.
- Not planned for the hourly data (52608 rows are large for in-context learning).


## Preprocessing

### Shared steps

1. **Read** `src/data/final/data_daily.csv` or `data_hourly.csv` (see [FEATURE_ENGINEERING](../FEATURE_ENGINEERING.md#data-folders)).
2. **Sort by `date_from_utc`** and check that there are no gaps: hourly, every step is exactly 1 h in UTC (52608 rows = 2192 days × 24). Do not use the local `date_from` as the time axis for the hourly data (missing 02:00 in spring, double 02:00 in autumn).
3. **Daily time axis**: a daily row starts at local midnight, in UTC that is 23:00 or 22:00 of the day before, so the daily `date_from_utc` is not a regular 1-day series in UTC. For the daily models use the local date of `date_from` as the timestamp (regular, one row per day).
4. **Select the columns** of the input table in [MODELS - Shared setup](../MODELS.md#shared-setup). Leakage columns, audit columns and auxiliary columns are never passed to a model.
5. **Encode** everything as numbers:
   - booleans (`is_holiday`, `is_weekday`, `is_bridge_day`, ...) as 0 / 1,
   - `day_of_week_raw` and `month` as sine / cosine pairs (or one-hot), drop the text column `day_of_week`,
   - TimesFM-3 has no documented support for categorical covariates, so everything goes in as numbers.
6. **Missing values**: `final/` should have none. Check it (`df.isna().sum()`) and stop if there are any instead of filling silently.
7. **Cut per forecast origin**: for every origin, the context is all rows before the origin, the future is the next `H` rows. The target of the future rows is never passed to the model, only kept for the evaluation.

### Covariate roles

Each input column has one of three roles. They follow the `known` / `forecast` / past-only marks of [FEATURES](../FEATURES.md#how-to-read-the-table).

| Role | Columns | Context rows | Future rows |
|---|---|---|---|
| Target | `actual_consumption` | observed values | not given (to predict) |
| Known future | calendar columns, `solar_capacity_mw`, `day_ahead_price` / `day_ahead_price_mean` (only for the 24 h / 1 d step, see shared setup) | values | values |
| Forecast | weather columns | observed values | weather forecast, see the weather protocol in the [shared setup](../MODELS.md#shared-setup) |
| Past only | `gas_price_eu_usd`, `oxcgrt_stringency`, `ipi_ei_level`, shifted `generation_*` | values | not known |

<a id="timesfm-3-preprocessing"></a>
### TimesFM-3

- **Target**: a 1-D array of `actual_consumption` over the context.
- **Past covariates**: the past-only columns, arrays with the length of the context.
- **Past-future (dynamic) covariates**: the known future and forecast columns, arrays with the length of context + horizon.
- **Context length**:
  - hourly: start with 2048 h (~12 weeks), then try 4096 h and 8192 h. A longer context shows more of the weekly and seasonal pattern but also older regimes. Pick it on the validation year. The maximum context of TimesFM-3 is not stated in the blog post: check it in the repository (TimesFM 2.5 had 16384).
  - daily: the whole history before the origin (at most 2192 days). Early origins simply have a shorter context.
- The inputs are grouped into patches of 32 time steps. A context that is a multiple of 32 avoids padding.
- Multiple targets (the multivariate mode) are not used: we have one target. `actual_consumption_incl_pumped` and `residual_load` would be the obvious second targets, but they are leakage.

<a id="tabiclforecaster-preprocessing"></a>
### TabICLForecaster

- **Context DataFrame**: columns `timestamp` (local date), `target` (`actual_consumption`) and one column per covariate. No `item_id` (one series).
- **Future DataFrame** (`future_df`): the future timestamps and the covariates of the future rows. `predict_df(context_df, future_df=...)`, see [time_series_forecasting.py](../time_series_forecasting.py).
- **Past-only covariates**: a tabular model needs a value in every future row. Fill the future rows with the **last value known at the origin** (forward fill from the origin). That is what a forecaster would know at that time, so it does not leak. The same rule can be used for TimesFM-3 as an alternative to the past-covariate slot (one experiment, see [Experiments](#experiments)).
- **Own time features**: TabICLForecaster adds index, calendar and seasonality features by itself. They overlap with our calendar columns. Run it with and without our calendar columns, keep the better one (on the validation year).
- **Context**: all daily rows before the origin, or only the last 2 years (to weight the current regime). Pick on the validation year.

## Normalization

- **TimesFM-3**: the model normalises every series by itself (per series, like TimesFM 2.5). **Pass the raw target in MWh**, no own scaling and no inverse transform.
- **Covariates of TimesFM-3**: the blog post does not say whether covariates are normalised the same way. Test two variants on the validation year: raw values, and standardised values (mean / std fitted on the training rows only).
- **TabICLForecaster**: the tabular regressor preprocesses the features and the target itself. Pass raw values. Check this in the TabICL docs before relying on it.
- **Never** fit a scaler on validation or test rows. If a scaler is used, fit it once per training period.

## Training and evaluation

<a id="timesfm-3-zero-shot"></a>
### TimesFM-3: zero-shot

- No training. For every forecast origin: context + covariates in, point forecast and 9 quantiles (0.1 - 0.9) out.
- The horizon is predicted in one pass (no step-by-step decoding), so 24 h and 168 h cost about the same.
- Batch the origins: all origins of one test year fit easily on the RTX 3090 in a few batches. Rough estimate: minutes for the whole hourly test year, seconds for the daily one (not measured).

<a id="timesfm-3-fine-tuning"></a>
### TimesFM-3: fine-tuning (Optional)

- **Method**: LoRA (Hugging Face Transformers + PEFT). The TimesFM repository has a fine-tuning example. The TimesFM-3 blog post itself only describes zero-shot use, so **check that the example supports version 3 and covariates** before planning around it.
- **Data**: windows (context + horizon) cut from the **training years** only. Hourly: one window per day as the origin (~1460 windows for 2019 - 2022), more with a shorter stride. Daily: few windows, so fine-tune only the hourly model at first. Try the daily one only if the hourly fine-tuning helps.
- **Selection**: early stopping and the choice of LoRA rank / learning rate on the validation year. Starting point: rank 8 - 16, learning rate ~1e-4, a few epochs.
- **Final model**: fine-tune again on training + validation years with the chosen settings, then forecast the test year. The same rule as for the other trained models.
- **Cost**: not known yet. A LoRA run on ~1500 windows should take minutes to about an hour on the RTX 3090 (rough estimate).
- **Risk**: overfitting a 330 M model on one series. Compare with zero-shot on the validation year; if fine-tuning does not beat zero-shot there, report zero-shot only.

<a id="tabiclforecaster-runs"></a>
### TabICLForecaster

- No training and no fine-tuning: the history rows are the input (in-context learning).
- What is chosen on the validation year: context length (all history / last 2 years) and the covariate set (with / without our calendar columns).
- Daily only. 52608 hourly rows are too many for in-context learning.

### Evaluation

The protocol is the one of the [shared setup](../MODELS.md#shared-setup): the same forecast origins, horizons, metrics and forecast file format as all other models. Specific to the foundation models:

- **Zero-shot vs fine-tuned**: report both for TimesFM-3. The difference shows what our data adds to the pretraining.
- **Value of the covariates**: also run TimesFM-3 zero-shot **without covariates** (target history only). The gap to the run with covariates is the covariate gain.
- **Data contamination**: German load data is public and may be in the pretraining data, so 2019 - 2024 can look better than new data. Check on a fresh 2025 period (needs the 2025 SMARD data and the feature pipelines extended to 2025, see the shared setup). If the advantage of the foundation models over N-HiTS and the trees shrinks a lot on 2025, contamination is likely.
- **Error by day type**: report the error on holidays, bridge days and Christmas separately. Pretrained models know weekly patterns well but not German holidays, those come only from the covariates.

### Experiments

| # | Model | Resolution | Horizon | Variant | Purpose |
|---|---|---|---|---|---|
| F1 | TimesFM-3 | hourly | 24 h, 168 h | zero-shot, no covariates | lower bound, covariate gain |
| F2 | TimesFM-3 | hourly | 24 h, 168 h | zero-shot, covariates | main zero-shot result |
| F3 | TimesFM-3 | hourly | 24 h, 168 h | fine-tuned, covariates | main fine-tuned result (Optional) |
| F4 | TimesFM-3 | daily | 7 d, 30 d | zero-shot, no covariates | lower bound, covariate gain |
| F5 | TimesFM-3 | daily | 7 d, 30 d | zero-shot, covariates | main daily result |
| F6 | TabICLForecaster | daily | 7 d, 30 d | covariates, with / without our calendar columns | challenger |
| F7 | TimesFM-3 | hourly | 24 h, 168 h | past-only covariates as past covariates vs forward-filled known covariates | covariate handling |

## Open questions
 
Checked on 2026-10-27 in the package code (`timesfm` 3.0.2, `tabicl` 2.2.0). Recheck if a newer version is installed.
 
| Question | Answer | Where it is used |
|---|---|---|
| Maximum context of TimesFM-3? | 15 360 steps, longer contexts are cut to the most recent ones | [TimesFM-3 preprocessing](#timesfm-3-preprocessing) |
| Maximum horizon of TimesFM-3? | No fixed maximum, the horizon is padded to the output patch and predicted in one pass | [TimesFM-3 preprocessing](#timesfm-3-preprocessing) |
| Fine-tuning example for TimesFM-3 with covariates? | No. The package has no training code; the repository's LoRA example is for TimesFM 2.5. Fine-tuning needs an own training loop, so it is optional | [Fine-tuning](#timesfm-3-fine-tuning) |
| Categorical covariates in TimesFM-3? | No, covariates are converted to `float32`. Numbers only | [Shared steps](#shared-steps) |
| Does TimesFM-3 normalise the covariates? | Yes, every variate with running mean / std, std < 1e-6 is replaced by 1 | [Normalization](#normalization) |
| Limit on the number of covariates? | `max_variates = 32` in the config, not enforced; stay at or below it | [TimesFM-3 preprocessing](#timesfm-3-preprocessing) |
| Past-only covariates in TabICLForecaster? | No, every extra column is a known covariate. Forward fill from the origin | [TabICLForecaster preprocessing](#tabiclforecaster-preprocessing) |
| Does TabICLRegressor scale the target? | Yes, `StandardScaler` on the context rows, transformed back | [Normalization](#normalization) |
 
Still open:
- How much GPU memory and time TimesFM-3 needs with ~25 variates and an 8192 h context (measure on the RTX 3090 before choosing the context length).
- The `max_variates = 32` limit is read from the config only. If more covariates are needed, test whether more than 32 variates still give sensible forecasts.