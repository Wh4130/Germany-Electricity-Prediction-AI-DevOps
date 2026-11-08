# Foundation model

[README](../../README.md) · [FEATURES](../FEATURES.md) · [FEATURE_ENGINEERING](../FEATURE_ENGINEERING.md) · [EDA](../EDA.md) · [MODELS](../MODELS.md)

Models: [SARIMAX](SARIMAX.md) · [TREES](TREES.md) · **FOUNDATION**

## Navigator

- [Overview](#overview)
- [How to run](#how-to-run)
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

> Implemented: F1, F2, F4, F5 (TimesFM-3 zero-shot) and F6 (TabICLForecaster). Not implemented: F3 (fine-tuning), F7 - F9. Code: [src/models/foundation/](../../src/models/foundation/). Tested end to end on synthetic data with the schema of `final/` and randomly initialised models of the same architecture; no results with the pretrained weights yet.

Two pretrained models. They forecast without training on our data (zero-shot), TimesFM-3 can also be fine-tuned. What they are and why they were chosen: [MODELS](../MODELS.md#model-descriptions).

| Model | Resolution | Horizons | Variants | Package |
|---|---|---|---|---|
| TimesFM-3 (Google Research, 330 M parameters) | hourly, daily | 24 h / 1 d, 7 d | zero-shot; fine-tuning optional (no official code for version 3, see [fine-tuning](#timesfm-3-fine-tuning)) | `pip install timesfm[torch]` (checked: 3.0.2), weights `google/timesfm-3.0-pytorch` |
| TabICLForecaster | daily | 1 d, 7 d | zero-shot only (in-context learning) | `pip install tabicl[forecast]` (checked: 2.2.0) |

- Split, horizons, input columns, metrics and baselines are the same for all models: [MODELS - Shared setup](../MODELS.md#shared-setup). This document only has what is specific to the foundation models.
- Hardware: RTX 3090 (24 GB). TimesFM-3 needs the GPU for a reasonable speed, TabICL on the daily data also runs on a CPU.
- Licence: the TimesFM-3 weights are under the TimesFM Non-Commercial License v1.0. Fine for this university project.

Files in `src/models/foundation/`:

| File | Content |
|---|---|
| `data.py` | Load `final/`, select and encode the columns, covariate roles, forecast origins, context and future cuts per origin, forecast file writer (shared by both models) |
| `timesfm3_forecast.py` | Zero-shot forecast with TimesFM-3 (F1, F2, F4, F5). Not called `timesfm3.py`: run as a script, that name would shadow the installed `timesfm3` package |
| `timesfm3_finetune.py` | Optional, not written: LoRA fine-tuning of TimesFM-3 (own training loop) |
| `tabicl_forecaster.py` | Forecast with TabICLForecaster (F6) |
| `evaluate.py` | Fills `y_true`, seasonal naive baseline, all metrics of the shared setup, by lead time and day type |
| `run_experiments.py` | Validation runs, selection of the settings, test runs, baselines and the summary table |

## How to run

From the project root, with the GPU environment (`timesfm[torch]==3.0.2`, `tabicl[forecast]==2.2.0`). The first run downloads the weights from Hugging Face.

```bash
# Everything: validation grid -> selection -> test with the chosen setting -> baselines -> metrics
uv run python src/models/foundation/run_experiments.py

# Only some experiments, or a smaller hourly context grid
uv run python src/models/foundation/run_experiments.py --experiments F4 F5 F6
uv run python src/models/foundation/run_experiments.py --hourly-contexts 2048 4096

# Quick check that everything runs (first 3 origins per run)
uv run python src/models/foundation/run_experiments.py --max-origins 3 --hourly-contexts 2048 --results-dir /tmp/fm_check

# Single runs
uv run python src/models/foundation/timesfm3_forecast.py --resolution hourly --split val --covariates --context-length 4096
uv run python src/models/foundation/tabicl_forecaster.py --split val --features default --context 730
uv run python src/models/foundation/evaluate.py src/results/forecasts/timesfm3_*_val.csv
```

What `run_experiments.py` chooses on the validation year (lowest MAE, `--select-metric pinball` for the pinball loss), per experiment and horizon:

| Experiment | Grid on 2023 | Test 2024 |
|---|---|---|
| F1, F2 | context 2048, 4096, 8192 h | the chosen context |
| F4, F5 | none (whole history) | whole history |
| F6 | features `ours` / `default` × context `all` / `730` days | the chosen pair |

Output:
- `src/results/forecasts/<run>.csv` in the [shared format](../MODELS.md#forecast-files), plus `<run>.json` with the settings (covariates, context, weather variant, run time). Names: `timesfm3_zs_{cov|nocov}_{hourly|daily}_{H}_ctx{L|all}_{val|test}`, `tabicl_{ours|default}_daily_{H}_ctx{all|730}_{split}`, `seasonal_naive_{resolution}_{H}_{split}`.
- `src/results/metrics/<run>.json` (overall, by lead time, by day type), `summary_foundation.csv`, `selection_foundation.json`.
- Runs whose forecast file already exists are skipped (`--overwrite` to redo them), so an interrupted run can be restarted.

Conventions:
- `origin` is the time of the first forecast step; everything strictly before it is known. Hourly in UTC (`date_from_utc`), daily the local date. Hourly origins are at local midnight (22:00 / 23:00 UTC).
- `y_pred` is the median for both models. `y_true` is left empty by the model scripts and filled in by `evaluate.py`.
- Weather is variant A (observed, oracle) for now, marked in every JSON sidecar. Variant B needs the extra ETL step of the shared setup.
- Horizons (decided 2026-11-04): **hourly 24 h, daily 1 d and 7 d**, not the 24 h / 168 h and 7 d / 30 d of the shared setup. Origins in 2024: 366 (hourly 24 h, daily 1 d) and 360 (daily 7 d).
- The covariates differ from the shared-setup table in two places (decided 2026-11-04): `hour_sin` / `hour_cos` are added (hourly) and `industrial_confidence` is added as past only. The day-ahead price is used where the shared setup allows it: `day_ahead_price` for the hourly 24 h horizon, `day_ahead_price_mean` for the daily 1 d horizon. See [Covariate roles](#covariate-roles). Other models that should be compared on the same inputs need the same change.
- A run whose forecast file exists but whose JSON sidecar lists other covariates is run again, so results of an older feature set are never mixed in.

## Preprocessing

### Shared steps

1. **Read** `src/data/final/data_daily.csv` or `data_hourly.csv` (see [FEATURE_ENGINEERING](../FEATURE_ENGINEERING.md#data-folders)).
2. **Sort by `date_from_utc`** and check that there are no gaps: hourly, every step is exactly 1 h in UTC (52608 rows = 2192 days × 24). Do not use the local `date_from` as the time axis for the hourly data (missing 02:00 in spring, double 02:00 in autumn).
3. **Daily time axis**: a daily row starts at local midnight, in UTC that is 23:00 or 22:00 of the day before, so the daily `date_from_utc` is not a regular 1-day series in UTC. For the daily models use the local date of `date_from` as the timestamp (regular, one row per day).
4. **Select the columns** of the input table in [MODELS - Shared setup](../MODELS.md#shared-setup). Leakage columns, audit columns and auxiliary columns are never passed to a model.
5. **Encode** everything as numbers:
   - booleans (`is_holiday`, `is_weekday`, `is_bridge_day`, ...) as 0 / 1,
   - `day_of_week_raw` and `month` as sine / cosine pairs (or one-hot), drop the text column `day_of_week`,
   - TimesFM-3 has no categorical covariates: the API converts every covariate array to `float32` (unlike the `dynamic_categorical_covariates` of TimesFM 2.5 XReg), so everything goes in as numbers.
6. **Missing values**: `final/` should have none. Check it (`df.isna().sum()`) and stop if there are any instead of filling silently.
7. **Cut per forecast origin**: for every origin, the context is all rows before the origin, the future is the next `H` rows. The target of the future rows is never passed to the model, only kept for the evaluation.

### Covariate roles

Each input column has one of three roles. They follow the `known` / `forecast` / past-only marks of [FEATURES](../FEATURES.md#how-to-read-the-table).

| Role | Columns | Context rows | Future rows |
|---|---|---|---|
| Target | `actual_consumption` | observed values | not given (to predict) |
| Known future | calendar columns, `hour_sin` / `hour_cos` (hourly), `solar_capacity_mw`, `is_day` / `daylight_duration`, `day_ahead_price` (hourly 24 h) / `day_ahead_price_mean` (daily 1 d) | values | values |
| Forecast | weather columns | observed values | weather forecast, see the weather protocol in the [shared setup](../MODELS.md#shared-setup) |
| Past only | `gas_price_eu_usd`, `oxcgrt_stringency`, `ipi_ei_level`, `industrial_confidence`, shifted `generation_*` (ablation 5, not used) | values | not known |

In the code (`data.covariate_set`):

| Run | Variates | Known | Past only |
|---|---|---|---|
| hourly 24 h | 26 | 21 (12 calendar, 2 hour, solar capacity, `is_day`, 4 weather, `day_ahead_price`) | 4 |
| daily 1 d | 24 | 19 (12 calendar, solar capacity, `daylight_duration`, 4 weather, `day_ahead_price_mean`) | 4 |
| daily 7 d | 23 | 18 (as 1 d, without the price) | 4 |

Derived in `data.py` or handled specially:
- `hour_sin`, `hour_cos`: from the **local** hour of `date_from` (the load follows the local clock); the double 02:00 at the end of DST gets the same value twice. The same values as the Fourier pair `sin_d1` / `cos_d1`.
- Day-ahead price: all hourly prices of a day are published together around noon of the day before, so with an origin at local midnight they are known for the whole next local day and not beyond. The hourly 24 h horizon uses the hourly `day_ahead_price`, the daily 1 d horizon `day_ahead_price_mean`; the daily 7 d horizon uses neither (only day 1 would be known). Both are columns of `final/`, nothing is derived.
- `industrial_confidence` is the value of the month before (FEATURES), but when the horizon crosses into the next month, that month's value is published after the origin, so it is **past only**: TimesFM-3 gets it as a past covariate, TabICL the last value known at the origin.

<a id="timesfm-3-preprocessing"></a>
### TimesFM-3

API (`timesfm3`, PyTorch backend):

```python
from timesfm3 import TimesFM3Evaluator, ModelConfig

forecaster = TimesFM3Evaluator(ModelConfig(
    checkpoint_path="google/timesfm-3.0-pytorch", per_core_batch_size=32, device="cuda"))

outputs = forecaster.predict_batch(
    contexts=[y_context, ...],                    # one 1-D array per origin
    horizon=H,
    past_only_covariates=[po, ...],               # (n_past_only, context_len)
    past_future_covariates=[pf, ...],             # (n_known, context_len + H)
    return_quantiles=True,                        # forecast (H,), quantiles (H, 9)
)
```

- **Target**: a 1-D array of `actual_consumption` over the context.
- **Past covariates** (`past_only_covariates`): the past-only columns, one row per column, length = context.
- **Past-future covariates** (`past_future_covariates`): the known future and forecast columns, one row per column, length = context + horizon.
- **Context length**: at most **15 360 steps**. Longer contexts are cut to the most recent 15 360 (checked in `timesfm3` 3.0.2, `_MAX_CONTEXT_LENGTH`). The covariates are cut the same way.
  - hourly: start with 2048 h (~12 weeks), then try 4096 h and 8192 h. A longer context shows more of the weekly and seasonal pattern but also older regimes, and costs more. Pick it on the validation year.
  - daily: the whole history before the origin (at most 2192 days, far below the limit). Early origins simply have a shorter context.
- **Horizon**: no fixed maximum. The horizon is rounded up to a multiple of the output patch and predicted in one pass, so any horizon works. A 1-step horizon still costs one full output patch (64 steps).
- The inputs are grouped into patches of 32 time steps. A context that is a multiple of 32 avoids padding.
- **Number of variates**: target + covariates together, at most **32**. `TimesFM3Evaluator.predict_batch` acts on it (`_MAX_VARIATES_PER_FORWARD = 32` in `timesfm3/torch/evaluator.py`): above 32 it **drops covariates at random** (fixed seed) to fit. `timesfm3_forecast.py` stops with an error instead, so this can not happen unnoticed. Our set is 23 - 26. All 12 shifted `generation_*` columns (ablation 5) would go above 32: use a few aggregates (e.g. total renewables of the day before) instead.
- `TimesFM3Evaluator` defaults (kept): symmetric averaging (the series and its negative are both forecast and averaged, doubles the batch internally), `make_positive=True`, sorted quantiles. The point forecast is the median quantile.
- Multiple targets (the multivariate mode) are not used: we have one target. `actual_consumption_incl_pumped` and `residual_load` would be the obvious second targets, but they are leakage.

<a id="tabiclforecaster-preprocessing"></a>
### TabICLForecaster

API (checked in `tabicl` 2.2.0):

```python
from tabicl import TabICLForecaster

forecaster = TabICLForecaster(
    max_context_length=4096,      # default; more than our 2192 daily rows
    point_estimate="median",      # default is "mean"; the median fits MAE and the other models
)
pred = forecaster.predict_df(context_df, future_df=future_df)   # point forecast + 9 quantile columns
```

- **Context DataFrame**: columns `timestamp` (local date), `target` (`actual_consumption`) and one column per covariate. Every extra column is treated as a **known** covariate. The code passes many origins in one call, each origin as its own `item_id` with its own context and future rows (TabICL fits each `item_id` separately).
- **Future DataFrame** (`future_df`): the future timestamps and the covariates of the future rows, no target. Give both DataFrames the same covariate columns: in 2.2.0 a column that is only in the context is **not** dropped (the intersection is only logged), it reaches the model with NaN in the future rows. NaN in the future rows gives a warning. See [time_series_forecasting.py](../time_series_forecasting.py).
- **Past-only covariates**: there is no past-only slot. Fill the future rows with the **last value known at the origin** (forward fill from the origin). That is what a forecaster would know at that time, so it does not leak. The same rule can be used for TimesFM-3 as an alternative to the past-covariate slot (one experiment, see [Experiments](#experiments)).
- **Own time features** (`temporal_features`, default `["index", "datetime", "periodic"]`):
  - `index`: a running row number, for the trend,
  - `datetime`: the year plus sine / cosine pairs of hour, day of week, day of month, day of year, week and month,
  - `periodic`: seasonal features from periods found by FFT.

  `datetime` overlaps with our `month` and `day_of_week_raw`. Compare (F6): `ours` = all our calendar columns + `temporal_features=["index", "periodic"]`, against `default` = the default features with our holiday columns only (`is_holiday`, `weighted_regional_holiday`, `weighted_school_holiday`, `is_bridge_day`, `is_christmas_new_year`; without `month`, weekday, `is_weekday`, `is_dst*`). Keep the better one (on the validation year).
- **Context**: all daily rows before the origin, or only the last 2 years (to weight the current regime). Pick on the validation year.

## Normalization

Both models scale by themselves (checked in the package code). **Pass raw values** (target in MWh), no own scaling and no inverse transform.

- **TimesFM-3**: every variate, the target **and each covariate**, is normalised inside the model (RevIN with running mean / std over the patches seen so far, `timesfm3/torch/model.py`). A standard deviation below 1e-6 is replaced by 1, so constant or rare 0 / 1 columns (`is_holiday`) do not blow up (unlike the window scaling of `neuralforecast`, see [NEURAL](NEURAL.md#normalization)). The forecast comes back in MWh.
  - Option `use_znorm=True` of `predict_batch`: an extra z-normalisation of every row before the model (target over the context, past-future covariates over context + horizon, all values the model is given anyway, so no leakage). Default `False`. Try it once on the validation year (F9, `--use-znorm` in `timesfm3_forecast.py`).
- **TabICLForecaster**: `TabICLRegressor` standardises the target with a `StandardScaler` fitted on the context rows and transforms the forecast back. The features go through an ensemble of normalisations. NaN in the features is allowed.
- **Never** fit an own scaler on validation or test rows.

## Training and evaluation

<a id="timesfm-3-zero-shot"></a>
### TimesFM-3: zero-shot

- No training. For every forecast origin: context + covariates in, point forecast and 9 quantiles (0.1 - 0.9) out.
- The horizon is predicted in one pass (no step-by-step decoding), so the cost depends on the context length, hardly on the horizon.
- Batch the origins: all origins of one test year fit easily on the RTX 3090 in a few batches. Rough estimate: minutes for the whole hourly test year, seconds for the daily one (not measured). The code starts with `per_core_batch_size=16` and halves it on a CUDA out-of-memory error; the batch size at the end and the run time are in the JSON sidecar.

<a id="timesfm-3-fine-tuning"></a>
### TimesFM-3: fine-tuning

> **Optional.** There is no official fine-tuning code for TimesFM-3 (checked: `timesfm` 3.0.2 has no training loop, no loss function and no LoRA code). The LoRA example in the repository (Hugging Face Transformers + PEFT, added in April 2026) is older than TimesFM 3.0 (August 2026) and written for TimesFM 2.5. The blog post only describes zero-shot use.

- **What it would take**: `TimesFM3Torch` is a normal PyTorch `nn.Module`, so an own training loop is possible: LoRA adapters with PEFT on the attention layers, the pinball loss over the 9 quantiles, and the same horizon masking as in pretraining (Contiguous Patch Masking, see `decode` in `timesfm3/torch/model.py`). This is a small research task of its own, not a configuration.
- **Plan**: do the zero-shot runs (F1, F2, F4, F5) first. Start the fine-tuning (F3) only if there is time left, and report it as an extra.
- **Method**: LoRA (PEFT) on top of the frozen pretrained weights.
- **Data**: windows (context + horizon) cut from the **training years** only. Hourly: one window per day as the origin (~1460 windows for 2019 - 2022), more with a shorter stride. Daily: few windows, so fine-tune only the hourly model at first. Try the daily one only if the hourly fine-tuning helps.
- **Selection**: early stopping and the choice of LoRA rank / learning rate on the validation year. Starting point: rank 8 - 16, learning rate ~1e-4, a few epochs.
- **Final model**: fine-tune again on training + validation years with the chosen settings, then forecast the test year. The same rule as for the other trained models.
- **Cost**: not known yet. A LoRA run on ~1500 windows should take minutes to about an hour on the RTX 3090 (rough estimate).
- **Risk**: overfitting a 330 M model on one series. Compare with zero-shot on the validation year; if fine-tuning does not beat zero-shot there, report zero-shot only.

<a id="tabiclforecaster-runs"></a>
### TabICLForecaster

- No training and no fine-tuning: the history rows are the input (in-context learning).
- What is chosen on the validation year: context length (all history / last 2 years) and the covariate set (with / without our calendar columns).
- Daily only. Hourly would be possible, but by default it keeps only the last 4096 rows (`max_context_length`), which is ~170 days of hourly data, less than half a year of the seasonal pattern.
- The point forecast is the mean by default. Set `point_estimate="median"` so that `y_pred` is the median, like the other models.
- The quantiles of the ensemble are sorted per row before they are written (they are not always in order).

### Evaluation

The protocol is the one of the [shared setup](../MODELS.md#shared-setup): the same forecast origins, horizons, metrics and forecast file format as all other models. Specific to the foundation models:

- **Zero-shot vs fine-tuned**: if the optional fine-tuning is done, report both for TimesFM-3. The difference shows what our data adds to the pretraining.
- **Value of the covariates**: also run TimesFM-3 zero-shot **without covariates** (target history only). The gap to the run with covariates is the covariate gain (F1 vs F2, F4 vs F5).
- **Data contamination**: German load data is public and may be in the pretraining data, so 2019 - 2024 can look better than new data. Check on a fresh 2025 period (needs the 2025 SMARD data and the feature pipelines extended to 2025, see the shared setup). If the advantage of the foundation models over N-HiTS and the trees shrinks a lot on 2025, contamination is likely.
- **Error by day type**: report the error on holidays, bridge days and Christmas separately. Pretrained models know weekly patterns well but not German holidays, those come only from the covariates.

`evaluate.py` details:
- Seasonal naive for the same origins and steps: the last observed week repeated (hourly lag 168 h, daily lag 7 d). Also written as its own forecast file, so other models can use it.
- Lead time: daily 7 d by day 1 - 7. Hourly 24 h and daily 1 d have no split. (Code for longer horizons is kept: hourly by day, daily 30 d by week 1 - 4.)
- Day types of the target time: `normal_weekday` (Mon - Fri, not a holiday, bridge day or Christmas window), `weekend` (Sat / Sun, not a holiday or Christmas window), and the overlapping `holiday`, `bridge_day`, `christmas_new_year`.
- The script can evaluate any forecast file in the shared format, not only the foundation models.

### Experiments

| # | Model | Resolution | Horizon | Variant | Purpose | Status |
|---|---|---|---|---|---|---|
| F1 | TimesFM-3 | hourly | 24 h | zero-shot, no covariates | lower bound, covariate gain | implemented |
| F2 | TimesFM-3 | hourly | 24 h | zero-shot, covariates | main zero-shot result | implemented |
| F3 | TimesFM-3 | hourly | 24 h | fine-tuned, covariates (optional, own training loop) | what fine-tuning adds | |
| F4 | TimesFM-3 | daily | 1 d, 7 d | zero-shot, no covariates | lower bound, covariate gain | implemented |
| F5 | TimesFM-3 | daily | 1 d, 7 d | zero-shot, covariates | main daily result | implemented |
| F6 | TabICLForecaster | daily | 1 d, 7 d | covariates; our calendar columns + `temporal_features=["index", "periodic"]` vs the default features | challenger | implemented |
| F7 | TimesFM-3 | hourly | 24 h | past-only covariates as past covariates vs forward-filled known covariates | covariate handling | |
| F8 | best of F2 / F3, F5, F6 | both | all | 2025 test period | contamination check | |
| F9 | TimesFM-3 | hourly, daily | all | `use_znorm=False` vs `True` | input normalisation (validation year) | flag only (`--use-znorm`) |

## Open questions

Checked on 2026-10-27 and 2026-11-04 in the package code (`timesfm` 3.0.2, `tabicl` 2.2.0). Recheck if a newer version is installed.

| Question | Answer | Where it is used |
|---|---|---|
| Maximum context of TimesFM-3? | 15 360 steps, longer contexts are cut to the most recent ones | [TimesFM-3 preprocessing](#timesfm-3-preprocessing) |
| Maximum horizon of TimesFM-3? | No fixed maximum, the horizon is padded to the output patch and predicted in one pass | [TimesFM-3 preprocessing](#timesfm-3-preprocessing) |
| Fine-tuning example for TimesFM-3 with covariates? | No. The package has no training code; the repository's LoRA example is for TimesFM 2.5. Fine-tuning needs an own training loop, so it is optional | [Fine-tuning](#timesfm-3-fine-tuning) |
| Categorical covariates in TimesFM-3? | No, covariates are converted to `float32`. Numbers only | [Shared steps](#shared-steps) |
| Does TimesFM-3 normalise the covariates? | Yes, every variate with running mean / std, std < 1e-6 is replaced by 1 | [Normalization](#normalization) |
| Limit on the number of covariates? | 32 variates. `TimesFM3Evaluator` drops covariates at random above it; our code stops with an error instead | [TimesFM-3 preprocessing](#timesfm-3-preprocessing) |
| Past-only covariates in TabICLForecaster? | No, every extra column is a known covariate. Forward fill from the origin | [TabICLForecaster preprocessing](#tabiclforecaster-preprocessing) |
| Does TabICLRegressor scale the target? | Yes, `StandardScaler` on the context rows, transformed back | [Normalization](#normalization) |
| Does TabICL drop covariates that are only in the context? | No (2.2.0): the intersection is only logged. Give both DataFrames the same columns | [TabICLForecaster preprocessing](#tabiclforecaster-preprocessing) |

Still open:
- How much GPU memory and time TimesFM-3 needs with 25 - 26 variates and an 8192 h context (the first full run reports the batch size that fit and the run time in the JSON sidecars).
- `gas_price_eu_usd` in `final/` is the value of the row's own month. Forward-filled from the origin, the future rows get the value of the origin's month, which may not be published yet at that time. The shared setup says "value of the last published month"; a one-month shift in the economic indicator pipeline would make it strict for all models.
