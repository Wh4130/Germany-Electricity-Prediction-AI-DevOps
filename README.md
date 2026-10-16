# AI Deployment

Exploring and analysing German electricity consumption data from SMARD.

- Source: SMARD (Bundesnetzagentur), "Realisierter Stromverbrauch" (actual consumption)
- Period: 2019-01-01 to 2025-01-01
- Files: daily (`_Tag.csv`) and hourly (`_Stunde.csv`) data in `src/data/raw/`
- Official docs: [`smard-user-guide-09-2021-data.pdf`](./smard-user-guide-09-2021-data.pdf), section 2.1 ~ 2.3.

## Data folder structure

```
src/data/
├── raw/        # SMARD downloads, untouched
├── intermin/   # cleaned raw data: renamed columns, parsed dates (the folder name is spelled "intermin")
├── features/   # output of the feature pipelines, one sub-folder per feature group
│   ├── calendar/
│   ├── electricity_price/
│   └── weather/
└── final/      # intermin + all features merged, the data for modelling
```

| Folder | File | Rows | Content |
|---|---|---|---|
| `raw/` | `Realisierter_Stromverbrauch_..._Tag.csv` | 2192 | SMARD daily export as downloaded (`;` separated, German number format) |
| `raw/` | `Realisierter_Stromverbrauch_..._Stunde.csv` | 52608 | SMARD hourly export as downloaded |
| `intermin/` | `data_daily.csv` | 2192 | Renamed columns and parsed dates, standard CSV (`,` separated, `.` decimal) |
| `intermin/` | `data_hourly.csv` | 52608 | Same as above, hourly |
| `intermin/` | `population_by_land.csv` | 928 | Population of the 16 states per year (lookup table, no row index), made by `src/scripts/population_etl.py`, used as weights |
| `intermin/` | `school_holidays.csv` | 670 | School holiday periods of the 16 states (lookup table: one row per period, no row index), made by `src/scripts/school_holidays_etl.py` |
| `features/<name>/` | `data_daily.csv` | 2192 | Daily output of the pipeline for that feature group |
| `features/<name>/` | `data_hourly.csv` | 52608 | Hourly output, only if the feature exists at hourly resolution |
| `final/` | `data_daily.csv`, `data_hourly.csv` | 2192 / 52608 | `intermin/` data + the columns of all features, made by `src/pipelines/merge_all.py` |

Notes:
- `raw/` is never edited. Everything else is produced by the pipelines in `src/pipelines/` (see below) and can be rebuilt from it.
- Every CSV in `intermin/` and `features/` keeps the row index as an unnamed first column, on purpose: it is meant for merging a feature file onto `intermin/` row by row. Read with `pd.read_csv(path, index_col=0)`. This also sidesteps the duplicated 02:00 timestamp of the autumn DST day in the hourly data. It only works if every pipeline keeps all rows in the original order.
- Hourly timestamps are naive local time (Europe/Berlin). SMARD has no 02:00 on the spring DST day and a duplicated 02:00 on the autumn one; keep this in mind when joining external hourly data.

Notebooks in `src/notebooks/` (data quality check, EDA) only read the data. They do not clean or write any dataset, that is done by the pipelines. File names and paths of the notebooks may change.

## Run everything (`src/pipelines/main.py`)

```
uv run python src/pipelines/main.py                   # whole data flow
uv run python src/pipelines/main.py --forceDownload   # download the lookup files again
```

```mermaid
flowchart LR
    A["scripts<br/>(downloads)"] --> B["cleansing<br/>raw → intermin"] --> C["feature pipelines<br/>→ features/*"] --> D["merge_all<br/>→ final"]
```

Downloads are skipped when their file exists, a failed step stops the run. To add a data source, append it to `DOWNLOADS` / `PIPELINES` in `src/pipelines/main.py` (see "Adding a feature pipeline").

## Scripts

One-off ETL scripts in `src/scripts/` download the data that does not come from SMARD and save it in `intermin/`. Run them from the project root with `uv run python src/scripts/<name>.py`. Each script has its source, steps and run command in its docstring.

| Script | Source | Writes | Note |
|---|---|---|---|
| `src/scripts/school_holidays_etl.py` | [ferien-api.de](https://ferien-api.de) (one request, all states and years) | `intermin/school_holidays.csv` | Re-running may hit HTTP 429 (rate limit). That is fine: the pipeline does not break and the data is already on GitHub. |
| `src/scripts/population_etl.py` | Destatis 12411LJ003 via [DBnomics](https://db.nomics.world) (one request) | `intermin/population_by_land.csv` | |

They only need to run once (the data does not change).

## Pipelines

The pipelines in `src/pipelines/` turn the data in `src/data/` into the next stage. Run them from the project root with `uv run python src/pipelines/<name>.py`, and use `--help` to list the options (input / output paths have defaults).

| Pipeline | Reads | Writes |
|---|---|---|
| `src/pipelines/cleansing.py` | `raw/` | `intermin/data_daily.csv`, `intermin/data_hourly.csv` |
| `src/pipelines/calendar_pipeline.py` | `intermin/` (incl. `population_by_land.csv`, `school_holidays.csv`) | `features/calendar/data_daily.csv`, `features/calendar/data_hourly.csv` (all calendar columns) |
| `src/pipelines/merge_all.py` | `intermin/data_*.csv` + every `features/*/data_*.csv` | `final/data_daily.csv`, `final/data_hourly.csv` |

### Adding a feature pipeline

Each feature group has one pipeline, `src/pipelines/<feature>_pipeline.py`, and one folder, `src/data/features/<feature>/` (e.g. `calendar_pipeline.py` -> `features/calendar/`). Use `calendar_pipeline.py` as the template.

1. **Design pattern: builder class + thin I/O.** Keep three parts apart:
   - A builder class (`CalendarFeatureBuilder`) that only computes. `build(data)` returns a new DataFrame with the same row index as the input and only the new columns. It does no file or network I/O and never changes its input. One method per feature, returning a Series; a feature that needs another one calls that method (no hidden order).
   - `load_data` / `save_features`: read with `index_col=0`, write with `index=True`.
   - `main()`: `argparse` with a default for every path (input from `intermin/`, output `features/<feature>/data_daily.csv` and `data_hourly.csv`), so the pipeline runs without arguments.
2. **Output rules.**
   - Same rows, same order and same row index as `intermin/data_*.csv`. `merge_all.py` joins by the row index and stops with an error if it differs.
   - Only the new columns (no copy of the `intermin/` columns), and column names that no other feature uses (add a prefix if needed, e.g. `price_`). A duplicate name stops `merge_all.py`.
   - `data_hourly.csv` only if the feature exists at hourly resolution, otherwise skip it: `merge_all.py` skips that file for the hourly data and prints it.
3. **Data from outside SMARD** is downloaded by a script `src/scripts/<name>_etl.py` into `intermin/<name>.csv` (a lookup table, no row index). The pipeline only reads that file, there is no network call inside a pipeline.
4. **Hook it up.** `merge_all.py` finds new feature folders by itself, nothing to change there. In `src/pipelines/main.py`, add the ETL script to `DOWNLOADS` (if there is one) and the pipeline to `PIPELINES`, before `merge_all.py`.
5. **Document it**: new columns in "Column reference", status in "Features".

A folder with only a `.gitkeep` is a placeholder, its pipeline does not exist or has not been run yet.

## Column reference

Columns by group. The raw columns are in `intermin/`, every other group is produced by its own pipeline into `features/<group>/`.

### Raw columns (`intermin/`)

CSV format of the raw files: separator `;`, decimal `,`, thousands `.`, dates as `dd.mm.yyyy`. The files in `intermin/` and `features/` are standard CSV with the row index as the first column.

| Original column name | English column name | Type | Unit | Description |
|---|---|---|---|---|
| Datum von | `date_from` | datetime | | Start of the interval |
| Datum bis | `date_to` | datetime | | End of the interval |
| Netzlast [MWh] Berechnete Auflösungen | `actual_consumption` | float | MWh | Total load incl. network losses, excl. stored energy (hydro pumped storage) |
| Netzlast inkl. Pumpspeicher [MWh] Berechnete Auflösungen | `actual_consumption_incl_pumped` | float | MWh | `actual_consumption` + `hydro_pumped_storage` |
| Pumpspeicher [MWh] Berechnete Auflösungen | `hydro_pumped_storage` | float | MWh | Consumption of hydro pumped storage (subcategory of actual consumption) |
| Residuallast [MWh] Berechnete Auflösungen | `residual_load` | float | MWh | `actual_consumption` minus feed-in from photovoltaic, onshore wind and offshore wind |

Notes:
- `actual_consumption + hydro_pumped_storage = actual_consumption_incl_pumped` was checked on both the daily and hourly data and holds for every row.
- SMARD values get revised after the fact (MaBiS corrections arrive from roughly the 42nd working day), so the same period can differ slightly between downloads.
- The region (e.g. Germany/Luxembourg) isn't in the file, so note the export settings somewhere.
- `Berechnete Auflösungen` is a label added by the export. The official docs don't explain it, so treat it as a label only.

### Calendar (`features/calendar/`)

Produced by `calendar_pipeline.py`, not part of `intermin/`. All columns below are implemented. The files hold only these columns (plus the row index), no copy of the `intermin/` columns: join them onto `intermin/` by the row index.

| Column | Description |
|---|---|
| `day_of_week_raw` | Weekday number, 0 = Monday ... 6 = Sunday |
| `day_of_week` | Weekday name |
| `month` | Month number |
| `is_holiday` | German nationwide public holiday (`holidays.Germany()`); also True when the holiday falls on a weekend |
| `is_weekday` | Monday to Friday (public holidays are not taken into account) |
| `weighted_regional_holiday` | Share of the population (0 - 1) that has a **regional** public holiday on that day: `holidays.Germany(subdiv=...)` for the 16 states, minus the national holidays, weighted by state population (Destatis 12411LJ003 via DBnomics, 2023). 0 on national holidays, they are in `is_holiday` |
| `weighted_school_holiday` | Share of the population (0 - 1) that is in school holidays on that day, same population weights, school holiday periods from `intermin/school_holidays.csv` (ferien-api.de). Overlapping periods of a state are merged, one-day items (e.g. a movable day off) are not counted unless `--includeSingleDays` is set. School holidays are not part of the public holidays, so nothing is subtracted: Easter Monday etc. are in `is_holiday` and here |
| `is_bridge_day` | Monday before a Tuesday national holiday, or Friday after a Thursday national holiday (industry often shuts down on these days). A Wednesday holiday has no bridge day, a day that is a holiday itself is not one |
| `is_christmas_new_year` | Fixed window from 24 Dec to 1 Jan. Dec 24 and 31 are not legal holidays but behave like half-holidays, and many plants run reduced operations for the whole period. The real shutdown days differ from company to company |
| `is_dst` | Summer time is in effect at `date_from` (hourly data: the repeated 02:00 at the end of DST is True the first time, False the second time). Low priority: in the daily data it is almost the same as the season (`month`), in the hourly data the shift of the sun against the clock is mostly covered by the hourly sunshine of the weather data. Check it with an ablation before keeping it in a model |
| `is_dst_transition_day` | The two days a year with 23 hours (start of DST) or 25 hours (end of DST) |

### Weather (`features/weather/`)

Not documented yet.

### Electricity price (`features/electricity_price/`)

Not documented yet.

## Features

Overview of what is available for modelling. Target: `actual_consumption`.

| Feature | Where | Status | Usable at prediction time? |
|---|---|---|---|
| Calendar: weekday, month, holidays, bridge days, ... (see the calendar columns above) | `features/calendar/` | in progress (`calendar_pipeline.py`) | yes, known in advance |
| `residual_load`, `hydro_pumped_storage`, `actual_consumption_incl_pumped` | `intermin/` | available, but **not features** | no, `residual_load` is built from the target, the other two are measured at the same time as it |
| Lags of `actual_consumption` (e.g. 1 / 7 days, 24 / 168 hours) | derive from the target | to do | yes if the lag is at least the forecast horizon |
| Weather (temperature, sunshine, ...) | | in progress (teammate) | use forecasts, not observations |

### Considered, not done

- **Carnival (`is_carnival`)**: not a legal holiday and regional, so there is no data on who is off on which day and a weighted version would need an assumed region x day matrix. Only 6 Rosenmontag days in our data, and a rough check (no weather control) shows about -2% on Rosenmontag against about +-7% normal Monday noise. Add it back (one 0/1 flag per day, no weights) only if the model residuals show these days.
