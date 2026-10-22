# Exploratory data analysis

[README](../README.md) · [FEATURES](FEATURES.md) · [FEATURE_ENGINEERING](FEATURE_ENGINEERING.md) · **EDA** · [MODELS](MODELS.md)

> **Preliminary.** This analysis uses the whole period (2019 - 2024), before the features were finished and before the train / test split. It is expected to be redone on the training set only. It is kept as a reference to compare with the new results.

## Navigator

- [Notebooks](#notebooks)
- [Data quality check](#data-quality-check)
- [Consumption patterns](#consumption-patterns)
  - [Daily trend](#daily-trend)
  - [Mean consumption by month](#mean-consumption-by-month)
  - [Weekday effect](#weekday-effect)
  - [Intra-day pattern by season](#intra-day-pattern-by-season)
  - [STL decomposition](#stl-decomposition)
- [PV and wind vs consumption](#pv-and-wind-vs-consumption)
- [Related notes in other documents](#related-notes-in-other-documents)

## Notebooks

The notebooks in [src/notebooks/](../src/notebooks/) only read the data. They do not clean or write any dataset, that is done by the [feature engineering pipeline](FEATURE_ENGINEERING.md). File names and paths of the notebooks may change.

| Notebook | Content |
|---|---|
| [data_quality_check.ipynb](../src/notebooks/data_quality_check.ipynb) | Column renaming, semantic validation, duplicates, missing values, anomalies, hourly vs daily cross check |
| [explortory_data_analysis.ipynb](../src/notebooks/explortory_data_analysis.ipynb) | Trend, seasonality, weekday effect, intra-day pattern, STL decomposition, PV + wind vs consumption |

The numbers below are the observations written in the notebooks (SMARD "Realisierter Stromverbrauch", 2019-01-01 to 2025-01-01). Check the notebook before quoting a number, it may have been re-run.

## Data quality check

Notebook: [data_quality_check.ipynb](../src/notebooks/data_quality_check.ipynb). The same checks run on the hourly and on the daily data. The cleaning itself lives in [cleansing.py](../src/feature_engineering/cleansing.py).

- **Columns**: renamed to English and described from the SMARD user guide, pages 41 - 44 ([PDF](../smard-user-guide-09-2021-data.pdf)). See the [raw columns](FEATURES.md#raw-columns).
- **Dates**: mapped to `datetime`.
- **Duplicates**: expected in the hourly data because of the autumn DST day (the 02:00 occurs twice). The period has 6 autumns, so at most 6 duplicated timestamps are tolerated.
- **Missing values**: none.
- **Anomalies**: negative values are checked. A negative `residual_load` is possible when renewable generation is higher than the consumption.
- **Cross check**: the daily data equals the sum of the hourly data.

## Consumption patterns

Notebook: [explortory_data_analysis.ipynb](../src/notebooks/explortory_data_analysis.ipynb).

### Daily trend

- The daily series swings between about 0.87M MWh/day (2024-03-31, Easter Sunday) and about 1.68M MWh/day (2021-11-30).
- The 7-day average removes the weekly cycle and leaves a clear annual wave: highs in winter (up to about 1.57M in Feb 2021), lows in summer (down to about 1.10M in May 2023).
- The yearly maxima are lower in 2023 (about 1.57M) and 2024 (about 1.60M) than in 2019 - 2022 (about 1.65 - 1.68M).

### Mean consumption by month

- Winter peaks (about 1.5M MWh/day), summer troughs (about 1.2M).
- 2020 drops in March - May (matches the first lockdown), 2022 drops in the second half (matches the energy crisis: high prices, saving), 2023 is the lowest year overall. Weather is not controlled here.
- Implication: `month` is a strong feature, and year-level shifts are not purely seasonal.

### Weekday effect

- Monday to Friday are about 1.04 - 1.07 times the weekly mean, Saturday about 0.90, Sunday about 0.84. The pattern is almost identical across 2019 - 2024.
- Monday and Friday are slightly lower than the other weekdays.
- Implication: a day type feature (4 classes) is useful. See the [calendar features](FEATURES.md#calendar).

### Intra-day pattern by season

Hourly means, DST switch days excluded.

- Winter weekday: night low of about 49k MWh/h (02:00), then a plateau of about 70k with two peaks at 11:00 and 18:00 and only a slight dip in between (about 67k at 15:00).
- Summer weekday: night low of about 42k (02:00), a single peak at 11:00 (about 64k), then a gradual decline through the evening. No evening peak.
- Weekend: the whole curve is lower and flatter.

### STL decomposition

MSTL on the daily data with periods 7 and 365.

- Trend: about 1.38M MWh/day (Jan 2019), about 1.33M (mid 2020), back to about 1.38M (Aug 2021), a low of about 1.25M (Apr 2023, about -9% from the 2021 peak), about 1.28M (end of 2024). The decline is not monotonic, most of it is one drop in 2022 - 2023.
- Weekly seasonal: about +100k on weekdays and about -200k on weekends, stable over the six years.

## PV and wind vs consumption

`residual_load = actual_consumption - (PV + onshore wind + offshore wind)`, so the PV + wind total can be recovered from the existing columns. `residual_load` is not a usable feature because it contains the target, and the PV + wind values of the same day are not available at prediction time. See the [leakage notes](FEATURES.md#generation-columns).

- PV + wind averages about 0.48M MWh/day (std about 0.21M), against about 1.33M for consumption.
- The same-day correlation with consumption is 0.10, and stays between -0.07 and 0.11 within each season. `residual_load` correlates 0.55 with consumption, not close to 1: PV + wind varies a lot from day to day, which weakens the link.
- After subtracting the month x weekday mean, the same-day correlation is 0.02. The small raw correlation is mostly shared seasonality, not a day-to-day link. Holidays are not removed there, so some noise remains.
- Lagged PV + wind vs consumption: raw correlation 0.10 (lag 0), 0.07 (lag 1), 0.04 (lag 2), 0.02 (lag 7). After removing the month x weekday mean: 0.02, -0.05, -0.11, -0.14.
- Consumption vs its own lag: raw 0.67 (lag 1) and 0.86 (lag 7); calendar-adjusted 0.82 (lag 1) and 0.47 (lag 7).

## Related notes in other documents

- Why the generation columns cannot be used as they are (R² = 0.76 against the same-hour consumption): [Generation columns](FEATURES.md#generation-columns).
- Rosenmontag check and why there is no carnival feature: [Not done / planned](FEATURES.md#not-done--planned).
- Low priority of the DST features, to test with an ablation: [`is_dst`](FEATURES.md#is_dst).
