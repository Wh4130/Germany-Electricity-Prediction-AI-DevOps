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
├── intermin/   # cleaned data + calendar columns (the folder name is spelled "intermin")
└── features/   # output of the feature pipelines, one sub-folder per feature group
    ├── calendar/
    ├── electricity_price/
    └── weather/
```

| Folder | File | Rows | Content |
|---|---|---|---|
| `raw/` | `Realisierter_Stromverbrauch_..._Tag.csv` | 2192 | SMARD daily export as downloaded (`;` separated, German number format) |
| `raw/` | `Realisierter_Stromverbrauch_..._Stunde.csv` | 52608 | SMARD hourly export as downloaded |
| `intermin/` | `data_daily.csv` | 2192 | Renamed and cleaned columns + calendar columns, standard CSV (`,` separated, `.` decimal) |
| `intermin/` | `data_hourly.csv` | 52608 | Same as above, hourly |
| `features/<name>/` | `data_daily.csv` | | Daily output of the pipeline for that feature group |
| `features/<name>/` | `data_hourly.csv` | | Hourly output, only if the feature exists at hourly resolution |

Notes:
- `raw/` is never edited. Everything else can be rebuilt from it (and from the notebooks listed below).
- Hourly timestamps are naive local time (Europe/Berlin). SMARD has no 02:00 on the spring DST day and a duplicated 02:00 on the autumn one; keep this in mind when joining external hourly data.

| Notebook | What it does |
|---|---|
| `src/notebooks/data_quality_check_and_cleansing.ipynb` | `raw/` -> `intermin/` |
| `src/notebooks/explortory_data_analysis.ipynb` | EDA on `intermin/` |

## Feature pipelines

Each feature group has one pipeline script in `src/pipelines/`, named after its folder in `src/data/features/` (e.g. `src/pipelines/calendar.py` -> `src/data/features/calendar/`).

- The result of a pipeline is saved in the matching folder under `src/data/features/`, named `data_daily.csv`.
- If the feature also exists at hourly resolution, it is saved as `data_hourly.csv` in the same folder. If there is no hourly version, skip it.
- Folders with only a `.gitkeep` are placeholders: the pipeline has not been run yet.

## Column reference

CSV format of the raw files: separator `;`, decimal `,`, thousands `.`, dates as `dd.mm.yyyy`. The files in `intermin/` are standard CSV.

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

Derived columns (added by us):

| Column | Description |
|---|---|
| `day_of_week_raw` | Weekday number, 0 = Monday ... 6 = Sunday |
| `day_of_week` | Weekday name |
| `month` | Month number |
| `is_holiday` | German nationwide public holiday (`holidays.Germany()`); also True when the holiday falls on a weekend |

## Features

Overview of what is available for modelling. Target: `actual_consumption`.

| Feature | Where | Status | Usable at prediction time? |
|---|---|---|---|
| Calendar: `day_of_week_raw`, `day_of_week`, `month`, `is_holiday` | `intermin/` | available | yes, known in advance |
| `residual_load`, `hydro_pumped_storage`, `actual_consumption_incl_pumped` | `intermin/` | available, but **not features** | no, `residual_load` is built from the target, the other two are measured at the same time as it |
| Lags of `actual_consumption` (e.g. 1 / 7 days, 24 / 168 hours) | derive from the target | to do | yes if the lag is at least the forecast horizon |
| Weather (temperature, sunshine, ...) | | in progress (teammate) | use forecasts, not observations |

## EDA ideas (rough draft)

Just a loose plan, we'll adjust as we go:

1. **Overall trend**: plot daily consumption with a rolling average. Is it going up or down over the years? Do 2020 (covid) and 2022 (energy crisis) show up?
2. **Day-of-week effect**: how big is the weekday vs weekend gap? Do public holidays look like weekends? When comparing, use "holidays on a weekday" vs "normal weekdays", otherwise weekends water down the result.
3. **Seasonality**: monthly and seasonal averages, a year x month heatmap. Is winter really higher?
4. **Daily pattern** (hourly data): average 24h curve for weekdays vs weekends and summer vs winter. Watch out for the daylight saving days (23 and 25 hours).
5. **Residual load**: look at `residual_load / actual_consumption` as a rough renewable share. Does it change year by year? Is there a midday dip from solar (the "duck curve")?
6. **Pumped storage**: when does it pump, and does that follow residual load? Is the share big enough to matter for modelling?
7. **Correlation and autocorrelation**: relationships between columns, plus how today relates to yesterday and last week (useful for forecasting later). Careful: `actual_consumption_incl_pumped` is just the sum of two other columns, so it's perfectly collinear.

If we move on to forecasting later: split train/test in time order, not randomly.
