# Features

[README](../README.md) · **FEATURES** · [FEATURE_ENGINEERING](FEATURE_ENGINEERING.md) · [EDA](EDA.md) · [MODELS](MODELS.md)

## Navigator

- [How to read the table](#how-to-read-the-table)
- [Feature table](#feature-table)
- [Details](#details)
  - [Raw columns](#raw-columns)
  - [Calendar](#calendar)
  - [Economic indicators](#economic-indicators)
  - [Electricity price](#electricity-price)
  - [Generation](#generation)
  - [Weather](#weather)
  - [MaStR solar capacity](#mastr-solar-capacity)
  - [Policy](#policy)
- [Ablation](#ablation)
- [Not done / planned](#not-done--planned)

## How to read the table

- Target: `actual_consumption` (MWh), daily and hourly.
- **Name** links to the details below when there is something more to say.
- **Produced by** is the file that writes the column. The `intermin/` columns come from [cleansing.py](../src/feature_engineering/cleansing.py), every other group from its own pipeline into `src/data/features/<group>/`. [merge_all.py](../src/feature_engineering/merge_all.py) joins everything into `src/data/final/`.
- **Datatype** is the type of the column in `final/` (`str` = text, `bool` = True / False). **D** = daily file only, **H** = hourly file only, no mark = both.
- **Model**: `x` = model input, or a possible input; `y` = target; empty = not a model input (keys, audit and auxiliary columns, and the columns that leak the target).
- **Ablation**: the number of the ablation test, see [Ablation](#ablation). Columns with the same number are added or removed together. Empty = not tested.
- **Notes**: `leakage` = measured at the same time as the target or built from it, do **not** use as a model input as it is. `forecast` = known only as an observation, at prediction time a forecast is needed. `known` = known in advance. `auxiliary` = a detail of another column. `audit column` = there to check the data, not for the model.
- Every file in `features/` also has `date_from` as its first column, only to read the file. It is not merged (`final/` has one `date_from`).

## Feature table

| Category | Name | Description | Datatype | Model | Ablation | Source | Produced by | Notes |
|---|---|---|---|---|---|---|---|---|
| Raw | [`date_from`](#raw-columns) | Start of the interval (local time, no time zone) | datetime (`str` in CSV) | | | [SMARD download center](https://www.smard.de/home/downloadcenter/download-marktdaten) | [cleansing.py](../src/feature_engineering/cleansing.py) | row key together with the row index |
| Raw | [`date_to`](#raw-columns) | End of the interval | datetime (`str` in CSV) | | | SMARD download center | cleansing.py | |
| Raw | [`actual_consumption`](#raw-columns) | Total load incl. network losses, excl. pumped storage, MWh | float | y | | SMARD download center | cleansing.py | **target** |
| Raw | [`actual_consumption_incl_pumped`](#raw-columns) | `actual_consumption` + `hydro_pumped_storage`, MWh | float | | | SMARD download center | cleansing.py | leakage |
| Raw | [`hydro_pumped_storage`](#raw-columns) | Consumption of hydro pumped storage, MWh | float | | | SMARD download center | cleansing.py | leakage |
| Raw | [`residual_load`](#raw-columns) | `actual_consumption` minus wind and solar feed-in, MWh | float | | | SMARD download center | cleansing.py | leakage (built from the target) |
| Calendar | `month` | Month number 1 - 12 | int | x | | derived from `date_from` | [calendar_pipeline.py](../src/feature_engineering/calendar_pipeline.py) | known |
| Calendar | `day_of_week_raw` | Weekday number, 0 = Monday ... 6 = Sunday | int | x | | derived from `date_from` | calendar_pipeline.py | known |
| Calendar | `day_of_week` | Weekday name | str | x | | derived from `date_from` | calendar_pipeline.py | known |
| Calendar | `is_holiday` | German nationwide public holiday | bool | x | | [`holidays`](https://pypi.org/project/holidays/) package | calendar_pipeline.py | known; True also on weekends |
| Calendar | `is_weekday` | Monday to Friday | bool | x | | derived from `date_from` | calendar_pipeline.py | known; holidays not excluded |
| Calendar | [`weighted_regional_holiday`](#weighted_regional_holiday) | Share of the population (0 - 1) with a regional public holiday | float | x | 1 | `holidays` package, [Destatis 12411LJ003 via DBnomics](https://api.db.nomics.world/v22/series/DESTATIS/12411LJ003) | calendar_pipeline.py | known |
| Calendar | [`weighted_school_holiday`](#weighted_school_holiday) | Share of the population (0 - 1) in school holidays | float | x | 1 | [ferien-api.de](https://ferien-api.de/api/v1/holidays), Destatis 12411LJ003 | calendar_pipeline.py | known |
| Calendar | [`is_bridge_day`](#is_bridge_day) | Bridge day next to a Tuesday / Thursday holiday | bool | x | | derived from `is_holiday` | calendar_pipeline.py | known |
| Calendar | [`is_christmas_new_year`](#is_christmas_new_year) | 24 Dec to 1 Jan | bool | x | | fixed window | calendar_pipeline.py | known |
| Calendar | [`is_dst`](#is_dst) | Summer time is in effect | bool | x | 2 | derived from `date_from` | calendar_pipeline.py | known |
| Calendar | [`is_dst_transition_day`](#is_dst) | Day with 23 or 25 hours | bool | x | 2 | derived from `date_from` | calendar_pipeline.py | known |
| Economic | [`gas_price_eu_usd`](#gas_price_eu_usd) | European natural gas price of the month, USD per MMBtu | float | x | 3 | [IMF PCPS via DBnomics](https://api.db.nomics.world/v22/series/IMF/PCPS/M.W00.PNGASEU.USD) | [economic_indicators_pipeline.py](../src/feature_engineering/economic_indicators_pipeline.py) | monthly value on every row |
| Electricity price | [`day_ahead_price`](#day-ahead-price) | Day-ahead price of the hour, EUR/MWh | float | x | 4 | [SMARD chart data](https://www.smard.de/app/chart_data/4169/DE-LU/index_hour.json) (DE-LU) | [electricity_price_pipeline.py](../src/feature_engineering/electricity_price_pipeline.py) | **H**; known around noon of the day before |
| Electricity price | [`day_ahead_price_mean`](#day-ahead-price) | Mean of the day-ahead prices of the day | float | x | 4 | SMARD chart data | electricity_price_pipeline.py | **D**; same as above |
| Electricity price | [`day_ahead_price_min`](#day-ahead-price) | Minimum of the day | float | | | SMARD chart data | electricity_price_pipeline.py | **D**; not used, the daily data uses the mean |
| Electricity price | [`day_ahead_price_max`](#day-ahead-price) | Maximum of the day | float | | | SMARD chart data | electricity_price_pipeline.py | **D**; not used, the daily data uses the mean |
| Generation | [`generation_wind_onshore`](#generation-columns) | Realised wind onshore generation, MWh | float | x | 5 | [SMARD download center](https://www.smard.de/home/downloadcenter/download-marktdaten) | [generation_pipeline.py](../src/feature_engineering/generation_pipeline.py) | leakage, only a shifted version can be used |
| Generation | [`generation_wind_offshore`](#generation-columns) | Wind offshore, MWh | float | x | 5 | SMARD download center | generation_pipeline.py | leakage |
| Generation | [`generation_solar`](#generation-columns) | Solar (PV), MWh | float | x | 5 | SMARD download center | generation_pipeline.py | leakage |
| Generation | [`generation_lignite`](#generation-columns) | Lignite, MWh | float | x | 5 | SMARD download center | generation_pipeline.py | leakage |
| Generation | [`generation_hard_coal`](#generation-columns) | Hard coal, MWh | float | x | 5 | SMARD download center | generation_pipeline.py | leakage |
| Generation | [`generation_natural_gas`](#generation-columns) | Natural gas, MWh | float | x | 5 | SMARD download center | generation_pipeline.py | leakage |
| Generation | [`generation_nuclear`](#generation-columns) | Nuclear, MWh (0 after 2023-04-15) | float | x | 5 | SMARD download center | generation_pipeline.py | leakage |
| Weather | [`hdd`](#weather-columns) | Heating degree days: `max(0, 18 - temperature)`, °C | float | x | | [Open-Meteo archive](https://archive-api.open-meteo.com/v1/archive) | [weather_pipeline.py](../src/feature_engineering/weather_pipeline.py) | forecast |
| Weather | [`daylight_duration`](#weather-columns) | Length of daylight, seconds | float | x | | Open-Meteo archive | weather_pipeline.py | **D**; forecast |
| Weather | [`shortwave_radiation_sum`](#weather-columns) | Solar radiation at the surface, MJ/m² | float | x | | Open-Meteo archive | weather_pipeline.py | **D**; forecast |
| Weather | [`shortwave_radiation`](#weather-columns) | Solar radiation at the surface, W/m² | float | x | | Open-Meteo archive | weather_pipeline.py | **H**; forecast |
| Weather | [`wind_speed_10m_max`](#weather-columns) | Wind speed 10 m above ground, daily maximum, km/h | float | x | | Open-Meteo archive | weather_pipeline.py | **D**; forecast |
| Weather | [`wind_speed_10m`](#weather-columns) | Wind speed 10 m above ground, km/h | float | x | | Open-Meteo archive | weather_pipeline.py | **H**; forecast |
| Weather | [`precipitation_sum`](#weather-columns) | Precipitation of the day, mm | float | x | | Open-Meteo archive | weather_pipeline.py | **D**; forecast |
| Weather | [`precipitation`](#weather-columns) | Precipitation of the hour, mm | float | x | | Open-Meteo archive | weather_pipeline.py | **H**; forecast |
| Solar capacity | [`solar_capacity_mw`](#mastr-solar-capacity) | Cumulative installed PV capacity in Germany, MW | float | x | 6 | [Marktstammdatenregister](https://www.marktstammdatenregister.de) via [open-mastr](https://github.com/OpenEnergyPlatform/open-MaStR) | [mastr_pipeline.py](../src/feature_engineering/mastr_pipeline.py) | known (slow-moving); overestimates a little, see details |
| Policy | [`oxcgrt_stringency`](#oxcgrt-columns) | OxCGRT stringency index, 0 - 100 | float | x | 7 | [OxCGRT](https://github.com/OxCGRT/covid-policy-dataset) | [oxcgrt_pipeline.py](../src/feature_engineering/oxcgrt_pipeline.py), then [policy_pipeline.py](../src/feature_engineering/policy_pipeline.py) | 0 outside 2020 - 2022 |
| Policy | [`oxcgrt_c1_school`](#oxcgrt-columns) | School closing level, 0 - 3 | float | | | OxCGRT | oxcgrt_pipeline.py | auxiliary |
| Policy | [`oxcgrt_c2_workplace`](#oxcgrt-columns) | Workplace closing level, 0 - 3 | float | | | OxCGRT | oxcgrt_pipeline.py | auxiliary |
| Policy | [`oxcgrt_c6_stay_home`](#oxcgrt-columns) | Stay-at-home requirements level, 0 - 3 | float | | | OxCGRT | oxcgrt_pipeline.py | auxiliary |
| Policy | [`oxcgrt_observed`](#oxcgrt-columns) | 1 on days with source values, 0 on days outside the coverage or filled | int | | | OxCGRT | oxcgrt_pipeline.py | audit column |
| Policy | [`ipi_ei_level`](#production-index-columns) | Production index of energy-intensive industries (2021 = 100) | float | x | 8 | [Destatis GENESIS 42153-0001](https://www-genesis.destatis.de/) | [production_index_pipeline.py](../src/feature_engineering/production_index_pipeline.py), then policy_pipeline.py | as known on that day |
| Policy | [`ipi_ei_mom`](#production-index-columns) | Change to the previous month, % | float | | | Destatis GENESIS 42153-0001 | production_index_pipeline.py | auxiliary |
| Policy | [`ipi_ei_yoy`](#production-index-columns) | Change to the same month of the year before, % | float | | | Destatis GENESIS 42153-0001 | production_index_pipeline.py | auxiliary |
| Policy | [`ipi_ei_staleness_days`](#production-index-columns) | Days from the end of the reference month to the row | int | | | derived | production_index_pipeline.py | auxiliary |
| Policy | [`ipi_ei_ref_month`](#production-index-columns) | Reference month of the value | str (`YYYY-MM`) | | | Destatis GENESIS 42153-0001 | production_index_pipeline.py | audit column |
| Policy | [`ipi_ei_release_date`](#production-index-columns) | Publication date of the value | str (`YYYY-MM-DD`) | | | Destatis press releases / rule | production_index_pipeline.py | audit column |
| Policy | [`ipi_ei_release_source`](#production-index-columns) | `curated` (real date) or `rule` (estimated date) | str | | | derived | production_index_pipeline.py | audit column |

## Details

### Raw columns

The columns of the SMARD export "Realisierter Stromverbrauch", renamed to English. The raw files use `;` as separator, `,` as decimal and dates as `dd.mm.yyyy`; the files in `intermin/` and `features/` are standard CSV.

| Original column name | English name | Unit |
|---|---|---|
| Datum von | `date_from` | |
| Datum bis | `date_to` | |
| Netzlast [MWh] Berechnete Auflösungen | `actual_consumption` | MWh |
| Netzlast inkl. Pumpspeicher [MWh] Berechnete Auflösungen | `actual_consumption_incl_pumped` | MWh |
| Pumpspeicher [MWh] Berechnete Auflösungen | `hydro_pumped_storage` | MWh |
| Residuallast [MWh] Berechnete Auflösungen | `residual_load` | MWh |

- `actual_consumption + hydro_pumped_storage = actual_consumption_incl_pumped` was checked on the daily and hourly data and holds for every row.
- `residual_load` is `actual_consumption` minus the feed-in of photovoltaic, onshore and offshore wind. It is built from the target, so it cannot be a feature.
- SMARD values get revised after the fact (MaBiS corrections arrive from roughly the 42nd working day), so the same period can differ slightly between downloads.
- The region (Germany / Luxembourg) is not in the file, note the export settings with the download.
- `Berechnete Auflösungen` is a label added by the export, the official docs do not explain it. See [section 2.1 - 2.3 of the SMARD user guide](../smard-user-guide-09-2021-data.pdf).
- Hourly timestamps are naive local time (Europe/Berlin): there is no 02:00 on the spring DST day and the 02:00 is there twice on the autumn one. Keep this in mind when joining external hourly data.

### Calendar

Produced by [calendar_pipeline.py](../src/feature_engineering/calendar_pipeline.py), all from `date_from`. Everything here is known in advance.

#### `weighted_regional_holiday`

Share of the population (0 - 1) that has a **regional** public holiday on that day: `holidays.Germany(subdiv=...)` for the 16 states, minus the national holidays, weighted by state population (Destatis 12411LJ003 via DBnomics, 2023). It is 0 on national holidays, those are in `is_holiday`.

#### `weighted_school_holiday`

Share of the population (0 - 1) that is in school holidays on that day, with the same population weights. The periods come from `intermin/school_holidays.csv` (ferien-api.de). Overlapping periods of a state are merged, one-day items (e.g. a movable day off) are not counted unless `--includeSingleDays` is set. School holidays are not part of the public holidays, so nothing is subtracted: Easter Monday etc. are in `is_holiday` and here.

#### `is_bridge_day`

Monday before a Tuesday national holiday, or Friday after a Thursday national holiday (industry often shuts down on these days). A Wednesday holiday has no bridge day, and a day that is a holiday itself is not one.

#### `is_christmas_new_year`

Fixed window from 24 Dec to 1 Jan. Dec 24 and 31 are not legal holidays but behave like half-holidays, and many plants run reduced operations for the whole period. The real shutdown days differ from company to company.

#### `is_dst`

Summer time is in effect at `date_from`. In the hourly data the repeated 02:00 at the end of DST is True the first time and False the second time. `is_dst_transition_day` marks the two days a year with 23 hours (start of DST) or 25 hours (end of DST).

Low priority: in the daily data `is_dst` is almost the same as the season (`month`), and in the hourly data the shift of the sun against the clock is mostly covered by the hourly sunshine of the weather data. Check it with an ablation before keeping it in a model.

### Economic indicators

Produced by [economic_indicators_pipeline.py](../src/feature_engineering/economic_indicators_pipeline.py). Monthly indicators: every day and every hour gets the value of its month.

#### `gas_price_eu_usd`

European natural gas price (IMF PCPS "Natural gas, EU"), US dollars per MMBtu, price level (not converted to euro, not a percent change). The gas price sets the electricity price when gas plants are the marginal plant, so it affects the load mostly through industry and in the long run.

DBnomics is a copy of the IMF data and some months behind (up to 2025-06), enough for our period. Cite as "IMF PCPS via DBnomics".

### Electricity price

#### Day-ahead price

Produced by [electricity_price_pipeline.py](../src/feature_engineering/electricity_price_pipeline.py). The day-ahead price is the market clearing price of the bidding zone Germany / Luxembourg (one price per hour, set by the last plant needed to meet the demand), EUR/MWh. It is known around noon of the day before, so it can be used to forecast the next day. It is driven by the demand itself (a high demand pushes the price up), so it is a signal of the expected scarcity, not a cause of the load.

- Hourly file: `day_ahead_price`. Daily file: `day_ahead_price_mean`, `day_ahead_price_min`, `day_ahead_price_max` (a day with 23 or 25 hours has that many hours).
- The price file is in UTC, the data is in local time. The rows are matched by the UTC time, including the repeated 02:00 at the end of DST.
- The data are the JSON files behind the charts of the SMARD website, not a documented API, so it can change. SMARD gets the data from ENTSO-E. Cite as "Bundesnetzagentur | SMARD.de" (CC BY 4.0).

### Generation

#### Generation columns

Produced by [generation_pipeline.py](../src/feature_engineering/generation_pipeline.py). Realised generation of the same hour (hourly file) or the same day (daily file, sum of the hours), MWh.

**Do not use these columns as they are to predict the load.** They are the target seen from the supply side: the sum of all 12 sources is 1.01 times the actual consumption on average, and a linear fit of the actual consumption on the 7 sources of the same hour gives R² = 0.76 (0.85 with all 12). The values are also only known after the hour. That is target leakage, like `residual_load`. They are there for analysis (e.g. the supply mix, the effect of the nuclear shutdown). To use them in a model, shift them first (e.g. the value of the day before) and test it with an ablation.

- Onshore + offshore + solar equals `actual_consumption - residual_load` (52538 of 52608 hours within 0.01 MWh, the other 70 hours are 2021-01-04 to 2021-01-06, a small difference inside the SMARD data).
- `generation_nuclear` is 0 after the last three plants were shut down on 2023-04-15.
- The other 5 sources (biomass, hydro, other renewable, pumped storage, other conventional) are in `intermin/generation_by_source.csv`, but not in the features.

### Weather

#### Weather columns

Produced by [weather_pipeline.py](../src/feature_engineering/weather_pipeline.py) from the per-city weather that [weather_etl.py](../src/scripts/weather_etl.py) downloads (Open-Meteo historical archive), population-weighted across the 15 largest German cities.

| Column | Unit | Description |
|---|---|---|
| `hdd` | °C | Heating degree days: `max(0, 18 - temperature)`. Demand-side driver, higher on cold days |
| `daylight_duration` | seconds | Length of daylight (sunrise to sunset). **Daily only** |
| `shortwave_radiation_sum` (daily) / `shortwave_radiation` (hourly) | MJ/m² / W/m² | Solar radiation reaching the surface. Supply-side driver (solar generation) |
| `wind_speed_10m_max` (daily) / `wind_speed_10m` (hourly) | km/h | Wind speed, 10 m above ground. Supply-side driver (wind generation) |
| `precipitation_sum` (daily) / `precipitation` (hourly) | mm | Total precipitation (rain + showers + snowfall water equivalent) |

- Daily columns are aggregated over the day (`_sum` / `_max` suffix), hourly columns are the instantaneous value of that hour.
- `daylight_duration` is daily only: at hourly resolution it would repeat the same value for all 24 hours of a day, which the `month` column already covers.
- The hourly data handles the two DST days: 23 rows on the spring one, 25 on the autumn one (`02:00` occurs twice with different weather values, two distinct real hours), matching `intermin/data_hourly.csv` row for row.
- These are **observed** values. At prediction time use weather **forecasts**, not these.

### MaStR solar capacity

#### `solar_capacity_mw`

Produced by [mastr_pipeline.py](../src/feature_engineering/mastr_pipeline.py) from the per-unit solar data that [mastr_etl.py](../src/scripts/mastr_etl.py) downloads (Marktstammdatenregister bulk export). Cumulative installed solar (PV) capacity in Germany as of that day, in MW. It is capacity, not generation: combine it with a solar radiation variable (e.g. `shortwave_radiation`) for a generation proxy.

- Daily file: the real day-to-day value. Hourly file: the day's value repeated across all 24 hours (capacity does not change within a day), so it carries no intra-day information on its own.
- Built from `AnlagenEegSolar` (the EEG-subsidy registration table), not the real unit registry `EinheitenSolar`, which currently fails to parse under `open-mastr` against MaStR's schema (a package / schema-version bug, not our data). Revisit once that is fixed.
- There is no decommissioning date in the substitute table, so capacity only ever increases. About 1.4% of the units are currently decommissioned, which should be a small overestimate in later years.
- Coverage is the EEG-subsidized units, the large majority of German PV but not strictly every panel.
- It does not need a forecast at prediction time (slow-moving, close to monotonic), but it needs a new extraction from MaStR to stay current beyond 2024.

### Policy

The OxCGRT and production index files are made by two pipelines that need the files in `src/data/external_raw/` and are not part of `main.py`. [policy_pipeline.py](../src/feature_engineering/policy_pipeline.py) puts their outputs into one `features/policy/data_daily.csv` and `data_hourly.csv`. The `refmonth` ablation files are not used.

#### OxCGRT columns

Produced by [oxcgrt_pipeline.py](../src/feature_engineering/oxcgrt_pipeline.py) from the Oxford COVID-19 Government Response Tracker (national, Germany, CC BY 4.0, coverage 2020-01-01 to 2022-12-31).

- Before the coverage (2019) all values are 0 (no pandemic). After it (2023 - 2024) all values are set to 0 by assumption. `oxcgrt_observed` = 0 marks these rows (and the rows filled inside the coverage).
- Short gaps inside the coverage are forward-filled up to 3 days.
- Values are "as known on day d". Shifting to the forecast origin happens later, not in the pipeline.
- Valid ranges from the OxCGRT codebook: stringency 0 - 100, the three levels 0 - 3.

#### Production index columns

Produced by [production_index_pipeline.py](../src/feature_engineering/production_index_pipeline.py) from Destatis GENESIS-Online, table 42153-0001 "Indizes der Produktion", series "Produktionsindex energieintensive Industriezweige" (2021 = 100). It needs the manual download `42153-0001_flat.csv` (Flat File CSV) in `src/data/external_raw/` and optionally `ipi_release_calendar.csv` (real publication dates from the Destatis press releases). Licence: DL-DE BY 2.0.

- **Release alignment ("as known on day d")**: a day gets the value of the latest reference month whose release date is on or before that day. Hourly rows use a release at 08:00 local time. The value itself is the latest revised figure (revisions are not modelled).
- Without `ipi_release_calendar.csv` the release date is estimated: day 10 of month t+2, moved to the next working day in Hesse. `ipi_ei_release_source` says which dates are `curated` and which are `rule`.
- `ipi_ei_ref_month`, `ipi_ei_release_date` and `ipi_ei_release_source` are audit columns, they are text and not meant as model inputs.
- The ablation `--alignment reference_month` (every day gets the value of its own month, weeks before it was published) leaks information and is only an upper bound. It is written to separate files and never reaches `final/`.

## Ablation

An ablation trains the model with and without a feature (or a group of features) on the same split and compares the metrics. The numbers in the Ablation column of the table are the tests. Each row below is one test: the columns of a row are added or removed together. They are the features with a doubt about their value, decided in the [meeting of 2026-10-21](meeting/2026-10-21.md).

| # | Columns | Why |
|---|---|---|
| 1 | `weighted_regional_holiday`, `weighted_school_holiday` | The population weights are an approximation. Compare with simple 0 / 1 flags |
| 2 | `is_dst`, `is_dst_transition_day` | Low priority. In the daily data `is_dst` is almost the same as the season (`month`), and in the hourly data the shift of the sun against the clock is mostly covered by the hourly sunshine of the weather data |
| 3 | `gas_price_eu_usd` | The effect is indirect, mostly through industry and in the long run |
| 4 | `day_ahead_price`, `day_ahead_price_mean` | The price is driven by the demand itself, it is a signal of the expected scarcity and not a cause of the load. For the daily data only the mean is used, not the minimum and the maximum |
| 5 | `generation_*` (all 7, all or nothing) | The same-hour values are the target seen from the supply side (target leakage). Only a shifted version (e.g. the value of the day before) can be tested. If the group helps, test the sources one by one afterwards |
| 6 | `solar_capacity_mw` | Slow-moving and rising, it may only repeat the trend |
| 7 | `oxcgrt_stringency` | Not zero only in 2020 - 2022, so it can only help in the pandemic period. Check whether it helps there at all. The other `oxcgrt_*` columns are auxiliary |
| 8 | `ipi_ei_level` | Compare with and without the production index, and with the other leading economic indicators that are being looked for. The other `ipi_ei_*` columns are auxiliary |

New features that are planned (leading economic indicators, EV data) are tested the same way once they are built, and added to the table above.

## Not done / planned

- **Lags of `actual_consumption`** (e.g. 1 / 7 days, 24 / 168 hours): to derive from the target. Usable if the lag is at least the forecast horizon.
- **Carbon price (EUA)**: no free source found, and the effect on the load is indirect and weak.
- **Carnival (`is_carnival`)**: not a legal holiday and regional, so there is no data on who is off on which day and a weighted version would need an assumed region x day matrix. Only 6 Rosenmontag days in our data, and a rough check (no weather control) shows about -2% on Rosenmontag against about ±7% normal Monday noise. Add it back (one 0/1 flag per day, no weights) only if the model residuals show these days.
