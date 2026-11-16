# Adding a model to the final report

To add a model, save its forecasts in `src/results/<model>/forecasts/` in the format below, then run, from the project root:

```
uv run python -m src.analysis.run_report
```

The run scores the new files, creates any missing seasonal naive benchmark, and adds the model to every table (`src/results/final_report/tables/`) and figure (`src/results/final_report/figures/`). Nothing in the analysis code has to change.

```
src/results/<model>/
  forecasts/
    <stem>.csv     forecasts (required)
    <stem>.json    settings sidecar (recommended)
  metrics/         written by the evaluation, do not edit
```

## The forecast CSV

One file per model, resolution, horizon and split, e.g. `mymodel_hourly_24h_test.csv`. One row per forecast origin and step.

| Column | Meaning |
|---|---|
| `origin` | Time of the **first forecasted step** (not the last observed hour). Everything strictly before it is known. |
| `target_time` | Time being forecast. Must equal `origin + (step − 1)` hours (hourly) or days (daily). |
| `step` | 1 … H |
| `y_true` | May be left empty. The evaluation fills it from `src/data/final/` and writes it back into the CSV. |
| `y_pred` | Point forecast in MWh, on the same scale as `actual_consumption` (daily = the day's total). |
| `q0.1` … `q0.9` | 9 quantiles. May be NaN or left out for point forecasts; pinball loss and band coverage then stay empty. |

### Time format

- **Hourly:** UTC, matching `date_from_utc`, e.g. `2024-01-01 23:00:00` (local midnight in winter). Times without a time zone are read as UTC; `+00:00` also works. Do not use local time.
- **Daily:** the local date, e.g. `2024-01-01`.

### Origins

Any origins are allowed. The shared setup uses every local midnight for hourly runs and every day for daily runs; one origin per hour (as in the tree model) also works.

### Example (hourly, 24 h)

```
origin,target_time,step,y_true,y_pred,q0.1,q0.2,q0.3,q0.4,q0.5,q0.6,q0.7,q0.8,q0.9
2023-12-31 23:00:00,2023-12-31 23:00:00,1,,41250.3,40100.0,...,42500.1
2023-12-31 23:00:00,2024-01-01 00:00:00,2,,40310.8,39200.5,...,41600.2
```

## The JSON sidecar (recommended)

Same name as the CSV, ending in `.json` instead, e.g. `mymodel_hourly_24h_test.json`:

```json
{
  "model": "LSTM",
  "label": "LSTM",
  "resolution": "hourly",
  "horizon": 24,
  "split": "test"
}
```

- `resolution` (`hourly` / `daily`), `horizon` (number of steps) and `split` (`val` = 2023, `test` = 2024) tell the pipeline what the run is. Without a sidecar they are guessed from the file name, which must then contain `_hourly_24h_` or `_daily_7d_` (etc.) and end in `_test` or `_val`.
- `label` is the name shown in tables and figures. If it is missing, the name comes from `LABEL_RULES` in `src/analysis/runs.py`, then from `"model"`, then from the folder name.
- Any other settings can go in the sidecar as well. The report ignores them, but they help trace a run.

## Common pitfalls

- **Two runs with the same name:** if two files have the same label, horizon and split (e.g. two LSTM variants), the report shows both under one name and prints a warning. Give each a different `label`.
- **Reserved folder names:** do not use `final_report` or `seasonal_naive` as a model folder.
- **Test year only by default:** `run_report` uses the 2024 runs. Validation runs are skipped unless you pass `--split val`.
- **`origin` is the first forecasted step**, not the time the forecast was made. If `target_time` is not `origin + (step − 1)`, the weather breakdown, business value and worst-days tables stop with an error.

## Useful commands

```
# only some models
uv run python -m src.analysis.run_report --models foundation sarimax <model>

# score forecasts without building the report
uv run python -m src.analysis.evaluate --models <model>

# figures 1 and 5 for a chosen hourly run (<model folder>/<file name without .csv>)
uv run python -m src.analysis.report_figures --figures 1 5 --run <model>/<stem>
```

## Optional: model-specific analysis

Tables or figures that only make sense for one model family (like the foundation ones in `src/analysis/foundation/`) go in `src/analysis/<model>/`, with `build(...)` functions registered in `MODEL_SPECIFIC` in `src/analysis/run_report.py`.