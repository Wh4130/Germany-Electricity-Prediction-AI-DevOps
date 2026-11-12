# Report tables


# Section 2. Model comparison

## Table 1. Main results, daily 1 d, test year

Sorted by MAE; the best model is in bold, the benchmark is the last row.

| Model | Setting | MAE (MWh) | MAPE % | Error reduction vs naive % | RMSE (MWh) | Pinball (MWh) | 80 % band coverage % |
|---|---|---|---|---|---|---|---|
| **TabICL** | features=default ctx=all | 19,091 | 1.5 | 66.9 | 24,700 | 7,448 | 76.5 |
| TimesFM-3, covariates | ctx=all | 20,691 | 1.7 | 64.2 | 27,985 | 8,186 | 85.2 |
| TimesFM-3, no covariates | ctx=all | 28,796 | 2.4 | 50.1 | 46,954 | 11,572 | 80.3 |
| Seasonal naive |  | 57,716 | 4.7 | 0.0 | 89,644 |  |  |

Insights:
- TabICL is the best daily model: 19,091 MWh MAE (1.5 %), 67 % better than the naive benchmark.
- TimesFM-3 with covariates is close behind at 20,691. Adding covariates cuts TimesFM-3’s error by 28 %.
- TabICL’s 80 % bands are slightly too narrow (76.5 %), while TimesFM-3’s are too wide (85.2 %).


## Table 1. Main results, daily 7 d, test year

Sorted by MAE; the best model is in bold, the benchmark is the last row.

| Model | Setting | MAE (MWh) | MAPE % | Error reduction vs naive % | RMSE (MWh) | Pinball (MWh) | 80 % band coverage % |
|---|---|---|---|---|---|---|---|
| **TabICL** | features=default ctx=all | 22,911 | 1.8 | 59.7 | 29,839 | 9,033 | 75.0 |
| TimesFM-3, covariates | ctx=all | 24,331 | 1.9 | 57.2 | 32,539 | 9,645 | 78.6 |
| TimesFM-3, no covariates | ctx=all | 34,562 | 2.8 | 39.2 | 52,545 | 13,833 | 78.9 |
| Seasonal naive |  | 56,842 | 4.6 | 0.0 | 88,603 |  |  |

Insights:
- The ranking stays the same. Error grows about 20 % compared with the 1-day horizon (TabICL 22.9k, 1.8 %).
- TimesFM-3 without covariates degrades most, keeping only 39 % skill. Covariates matter more the further ahead you forecast.


## Table 1. Main results, hourly 24 h, test year

Sorted by MAE; the best model is in bold, the benchmark is the last row.

| Model | Setting | MAE (MWh) | MAPE % | Error reduction vs naive % | RMSE (MWh) | Pinball (MWh) | 80 % band coverage % |
|---|---|---|---|---|---|---|---|
| **TimesFM-3, covariates** | ctx=8192 | 1,045 | 2.0 | 60.7 | 1,491 | 408 | 81.6 |
| TimesFM-3, no covariates | ctx=8192 | 1,260 | 2.4 | 52.6 | 2,038 | 504 | 78.7 |
| Seasonal naive |  | 2,657 | 5.1 | 0.0 | 4,102 |  |  |

Insights:
- TimesFM-3 with covariates reaches 1,045 MWh/h (2.0 %), 61 % better than naive, with well-calibrated bands (81.6 %).


## Settings compared on the validation year (2023)

Chosen = lowest validation MAE; only the chosen setting was run on the test year.

| Model | Horizon | Setting | MAE (MWh) | Pinball (MWh) | 80 % band coverage % | Chosen |
|---|---|---|---|---|---|---|
| TimesFM-3, no covariates | hourly 24 h | ctx=8192 | 1,130 | 453 | 80.1 | yes |
| TimesFM-3, no covariates | hourly 24 h | ctx=4096 | 1,156 | 463 | 80.0 |  |
| TimesFM-3, no covariates | hourly 24 h | ctx=2048 | 1,186 | 476 | 78.9 |  |
| TimesFM-3, covariates | hourly 24 h | ctx=8192 | 946 | 371 | 82.5 | yes |
| TimesFM-3, covariates | hourly 24 h | ctx=4096 | 965 | 382 | 83.4 |  |
| TimesFM-3, covariates | hourly 24 h | ctx=2048 | 992 | 395 | 82.5 |  |
| TimesFM-3, no covariates | daily 1 d | ctx=all | 24,456 | 10,021 | 87.7 | yes |
| TimesFM-3, covariates | daily 1 d | ctx=all | 17,642 | 6,958 | 89.9 | yes |
| TabICL | daily 1 d | features=default ctx=all | 15,792 | 6,160 | 82.2 | yes |
| TabICL | daily 1 d | features=ours ctx=all | 16,154 | 6,218 | 82.5 |  |
| TabICL | daily 1 d | features=ours ctx=730 | 16,476 | 6,407 | 80.8 |  |
| TabICL | daily 1 d | features=default ctx=730 | 16,558 | 6,427 | 80.0 |  |
| TimesFM-3, no covariates | daily 7 d | ctx=all | 29,823 | 11,981 | 84.8 | yes |
| TimesFM-3, covariates | daily 7 d | ctx=all | 21,959 | 8,505 | 84.6 | yes |
| TabICL | daily 7 d | features=default ctx=all | 19,996 | 7,870 | 76.6 | yes |
| TabICL | daily 7 d | features=ours ctx=all | 20,310 | 7,837 | 76.6 |  |
| TabICL | daily 7 d | features=default ctx=730 | 21,138 | 8,216 | 76.1 |  |
| TabICL | daily 7 d | features=ours ctx=730 | 21,364 | 8,259 | 75.0 |  |

Insights:
- For hourly TimesFM-3, longer context is always better (8,192 h).
- For TabICL, the default features beat our own feature set by about 2 %, and full history beats 730 days.
- All 2023 errors are lower than 2024 errors, so 2024 was a harder year. 


# Section 3. Day types

## Table 3. Results by day type, test year

Hours / days: hourly runs count hours, daily runs count forecast rows (7 d runs count each day once per lead day). Holiday, bridge day and Christmas can overlap, so the shares need not add up to 100 %.

| Model | Horizon | Day type | Hours / days | MAE (MWh) | MAPE % | Naive MAE (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|---|
| TabICL | daily 1 d | Normal weekday | 247 | 18,855 | 1.4 | 52,564 | 64.1 | 76.1 | 66.7 |
| TabICL | daily 1 d | Weekend | 102 | 17,234 | 1.6 | 46,037 | 62.6 | 79.4 | 25.2 |
| TabICL | daily 1 d | Holiday | 9 | 26,699 | 2.6 | 259,974 | 89.7 | 77.8 | 3.4 |
| TabICL | daily 1 d | Bridge day | 3 | 28,069 | 2.4 | 198,662 | 85.9 | 66.7 | 1.2 |
| TabICL | daily 1 d | Christmas / New Year | 9 | 43,897 | 3.8 | 155,159 | 71.7 | 44.4 | 5.7 |
| TabICL | daily 7 d | Normal weekday | 1715 | 22,748 | 1.7 | 51,449 | 55.8 | 74.0 | 67.6 |
| TabICL | daily 7 d | Weekend | 713 | 22,246 | 2.0 | 45,900 | 51.5 | 76.9 | 27.5 |
| TabICL | daily 7 d | Holiday | 56 | 25,792 | 2.5 | 282,852 | 90.9 | 85.7 | 2.5 |
| TabICL | daily 7 d | Bridge day | 19 | 20,536 | 1.8 | 195,819 | 89.5 | 94.7 | 0.7 |
| TabICL | daily 7 d | Christmas / New Year | 36 | 42,536 | 3.7 | 220,595 | 80.7 | 63.9 | 2.7 |
| TimesFM-3, covariates | daily 1 d | Normal weekday | 247 | 18,689 | 1.4 | 52,564 | 64.4 | 86.2 | 61.0 |
| TimesFM-3, covariates | daily 1 d | Weekend | 102 | 20,428 | 1.9 | 46,037 | 55.6 | 86.3 | 27.5 |
| TimesFM-3, covariates | daily 1 d | Holiday | 9 | 34,613 | 3.3 | 259,974 | 86.7 | 77.8 | 4.1 |
| TimesFM-3, covariates | daily 1 d | Bridge day | 3 | 64,909 | 5.7 | 198,662 | 67.3 | 66.7 | 2.6 |
| TimesFM-3, covariates | daily 1 d | Christmas / New Year | 9 | 69,133 | 6.1 | 155,159 | 55.4 | 44.4 | 8.2 |
| TimesFM-3, covariates | daily 7 d | Normal weekday | 1715 | 23,269 | 1.7 | 51,449 | 54.8 | 78.5 | 65.1 |
| TimesFM-3, covariates | daily 7 d | Weekend | 713 | 23,817 | 2.1 | 45,900 | 48.1 | 80.6 | 27.7 |
| TimesFM-3, covariates | daily 7 d | Holiday | 56 | 33,331 | 3.2 | 282,852 | 88.2 | 80.4 | 3.0 |
| TimesFM-3, covariates | daily 7 d | Bridge day | 19 | 70,339 | 6.2 | 195,819 | 64.1 | 26.3 | 2.2 |
| TimesFM-3, covariates | daily 7 d | Christmas / New Year | 36 | 55,316 | 4.9 | 220,595 | 74.9 | 75.0 | 3.2 |
| TimesFM-3, covariates | hourly 24 h | Normal weekday | 5928 | 995 | 1.8 | 2,461 | 59.6 | 81.4 | 64.2 |
| TimesFM-3, covariates | hourly 24 h | Weekend | 2447 | 945 | 2.0 | 2,146 | 56.0 | 83.0 | 25.2 |
| TimesFM-3, covariates | hourly 24 h | Holiday | 217 | 2,785 | 6.4 | 10,905 | 74.5 | 77.0 | 6.6 |
| TimesFM-3, covariates | hourly 24 h | Bridge day | 72 | 2,945 | 6.0 | 8,278 | 64.4 | 45.8 | 2.3 |
| TimesFM-3, covariates | hourly 24 h | Christmas / New Year | 216 | 1,426 | 3.0 | 6,631 | 78.5 | 85.6 | 3.4 |
| TimesFM-3, no covariates | daily 1 d | Normal weekday | 247 | 23,339 | 1.8 | 52,564 | 55.6 | 82.2 | 54.7 |
| TimesFM-3, no covariates | daily 1 d | Weekend | 102 | 25,490 | 2.3 | 46,037 | 44.6 | 83.3 | 24.7 |
| TimesFM-3, no covariates | daily 1 d | Holiday | 9 | 185,886 | 18.1 | 259,974 | 28.5 | 22.2 | 15.9 |
| TimesFM-3, no covariates | daily 1 d | Bridge day | 3 | 72,472 | 6.4 | 198,662 | 63.5 | 33.3 | 2.1 |
| TimesFM-3, no covariates | daily 1 d | Christmas / New Year | 9 | 60,321 | 5.4 | 155,159 | 61.1 | 66.7 | 5.2 |
| TimesFM-3, no covariates | daily 7 d | Normal weekday | 1715 | 28,856 | 2.2 | 51,449 | 43.9 | 81.0 | 56.8 |
| TimesFM-3, no covariates | daily 7 d | Weekend | 713 | 31,830 | 2.9 | 45,900 | 30.7 | 79.8 | 26.1 |
| TimesFM-3, no covariates | daily 7 d | Holiday | 56 | 208,100 | 20.3 | 282,852 | 26.4 | 19.6 | 13.4 |
| TimesFM-3, no covariates | daily 7 d | Bridge day | 19 | 128,486 | 11.4 | 195,819 | 34.4 | 26.3 | 2.8 |
| TimesFM-3, no covariates | daily 7 d | Christmas / New Year | 36 | 60,090 | 5.4 | 220,595 | 72.8 | 83.3 | 2.5 |
| TimesFM-3, no covariates | hourly 24 h | Normal weekday | 5928 | 1,115 | 2.0 | 2,461 | 54.7 | 79.8 | 59.7 |
| TimesFM-3, no covariates | hourly 24 h | Weekend | 2447 | 1,056 | 2.3 | 2,146 | 50.8 | 80.6 | 23.3 |
| TimesFM-3, no covariates | hourly 24 h | Holiday | 217 | 7,259 | 16.5 | 10,905 | 33.4 | 22.6 | 14.2 |
| TimesFM-3, no covariates | hourly 24 h | Bridge day | 72 | 2,411 | 4.9 | 8,278 | 70.9 | 73.6 | 1.6 |
| TimesFM-3, no covariates | hourly 24 h | Christmas / New Year | 216 | 2,551 | 5.5 | 6,631 | 61.5 | 72.2 | 5.0 |

Insights:
- Normal weekdays and weekends cause 85–90 % of all error, simply because there are so many of them.
- Special days are where the models differ:
    - TimesFM-3 without covariates fails on holidays (MAPE 16–20 %, coverage about 20 %).
    - Christmas/New Year is the hardest period for every model.
    - Bridge days are TimesFM-3’s weak spot.
- Samples are tiny: 9 holidays and 3 bridge days.


## Covariate gain by day type (TimesFM-3 without vs with covariates)

Share of total gain: part of the whole-year error reduction that comes from this day type.

| Horizon | Day type | Hours / days | MAE TimesFM-3, no covariates (MWh) | MAE TimesFM-3, covariates (MWh) | MAE change % | Coverage TimesFM-3, no covariates % | Coverage TimesFM-3, covariates % | Share of total gain % |
|---|---|---|---|---|---|---|---|---|
| hourly 24 h | Normal weekday | 5928 | 1,115 | 995 | -10.8 | 79.8 | 81.4 | 37.9 |
| hourly 24 h | Weekend | 2447 | 1,056 | 945 | -10.5 | 80.6 | 83.0 | 14.4 |
| hourly 24 h | Holiday | 217 | 7,259 | 2,785 | -61.6 | 22.6 | 77.0 | 51.3 |
| hourly 24 h | Bridge day | 72 | 2,411 | 2,945 | +22.2 | 73.6 | 45.8 | -2.0 |
| hourly 24 h | Christmas / New Year | 216 | 2,551 | 1,426 | -44.1 | 72.2 | 85.6 | 12.8 |
| daily 1 d | Normal weekday | 247 | 23,339 | 18,689 | -19.9 | 82.2 | 86.2 | 38.7 |
| daily 1 d | Weekend | 102 | 25,490 | 20,428 | -19.9 | 83.3 | 86.3 | 17.4 |
| daily 1 d | Holiday | 9 | 185,886 | 34,613 | -81.4 | 22.2 | 77.8 | 45.9 |
| daily 1 d | Bridge day | 3 | 72,472 | 64,909 | -10.4 | 33.3 | 66.7 | 0.8 |
| daily 1 d | Christmas / New Year | 9 | 60,321 | 69,133 | +14.6 | 66.7 | 44.4 | -2.7 |
| daily 7 d | Normal weekday | 1715 | 28,856 | 23,269 | -19.4 | 81.0 | 78.5 | 37.2 |
| daily 7 d | Weekend | 713 | 31,830 | 23,817 | -25.2 | 79.8 | 80.6 | 22.2 |
| daily 7 d | Holiday | 56 | 208,100 | 33,331 | -84.0 | 19.6 | 80.4 | 38.0 |
| daily 7 d | Bridge day | 19 | 128,486 | 70,339 | -45.3 | 26.3 | 26.3 | 4.3 |
| daily 7 d | Christmas / New Year | 36 | 60,090 | 55,316 | -7.9 | 83.3 | 75.0 | 0.7 |

Insights:
- Holidays are only 2.5 % of the year but supply 38–51 % of the total covariate gain
- The holiday flags are the most valuable covariate.
- On ordinary days covariates still cut error by 10–25 %.
- Covariates make two cases worse: hourly bridge days (+22 %, coverage falls to 46 %) and Christmas at 1 day ahead (+15 %).

## TabICL vs TimesFM-3 with covariates, by day type

Negative MAE change = TabICL is better.

| Horizon | Day type | Hours / days | MAE TimesFM-3, covariates (MWh) | MAE TabICL (MWh) | MAE change % | Coverage TimesFM-3, covariates % | Coverage TabICL % | Share of total gain % |
|---|---|---|---|---|---|---|---|---|
| daily 1 d | Normal weekday | 247 | 18,689 | 18,855 | +0.9 | 86.2 | 76.1 | -7.0 |
| daily 1 d | Weekend | 102 | 20,428 | 17,234 | -15.6 | 86.3 | 79.4 | 55.6 |
| daily 1 d | Holiday | 9 | 34,613 | 26,699 | -22.9 | 77.8 | 77.8 | 12.2 |
| daily 1 d | Bridge day | 3 | 64,909 | 28,069 | -56.8 | 66.7 | 66.7 | 18.9 |
| daily 1 d | Christmas / New Year | 9 | 69,133 | 43,897 | -36.5 | 44.4 | 44.4 | 38.8 |
| daily 7 d | Normal weekday | 1715 | 23,269 | 22,748 | -2.2 | 78.5 | 74.0 | 25.0 |
| daily 7 d | Weekend | 713 | 23,817 | 22,246 | -6.6 | 80.6 | 76.9 | 31.3 |
| daily 7 d | Holiday | 56 | 33,331 | 25,792 | -22.6 | 80.4 | 85.7 | 11.8 |
| daily 7 d | Bridge day | 19 | 70,339 | 20,536 | -70.8 | 26.3 | 94.7 | 26.4 |
| daily 7 d | Christmas / New Year | 36 | 55,316 | 42,536 | -23.1 | 75.0 | 63.9 | 12.9 |

Insights:
- On normal weekdays the two are tied (±2 %).
- TabICL’s lead comes from weekends, Christmas and especially bridge days. At 7 days ahead it has 71 % less bridge-day error, with 95 % coverage against 26 %.
- This supports using TabICL for the daily total and TimesFM-3 for the hourly shape.


## Error by lead day, daily 7 d, test year

Weather inputs are observed values, so the real decay with weather forecasts is larger.

| Lead day | MAE (MWh) TabICL | MAE (MWh) TimesFM-3, covariates | MAE (MWh) TimesFM-3, no covariates | Error reduction vs naive % TabICL | Error reduction vs naive % TimesFM-3, covariates | Error reduction vs naive % TimesFM-3, no covariates |
|---|---|---|---|---|---|---|
| 1 | 19,060 | 18,557 | 28,430 | 66.3 | 67.2 | 49.8 |
| 2 | 21,974 | 22,299 | 32,887 | 61.7 | 61.1 | 42.7 |
| 3 | 23,169 | 24,158 | 34,566 | 59.7 | 58.0 | 39.9 |
| 4 | 23,747 | 24,924 | 35,209 | 58.5 | 56.5 | 38.5 |
| 5 | 24,066 | 26,568 | 36,151 | 57.6 | 53.2 | 36.3 |
| 6 | 24,263 | 27,066 | 37,065 | 56.9 | 51.9 | 34.2 |
| 7 | 24,099 | 26,744 | 37,622 | 57.0 | 52.3 | 32.9 |

Insights:
- TimesFM-3 is marginally better on day 1.
- TabICL wins from day 2 onward and degrades less: +26 % from day 1 to day 7, against +44 % for TimesFM-3.
- Both flatten after about day 4. With real weather forecasts instead of observed weather, the decay would be steeper.


# Section 4. Weather

## Table 4. Results by temperature change against last week (ordinary days)

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

HDD at the target minus HDD one week before (the week the seasonal naive repeats). Heating season only: bottom 20 % -> much warmer, top 20 % -> much colder, else similar.

Much colder / Much warmer than last week (daily mean HDD minus the same day one week before; top / bottom 20 % of the heating-season days of the year)

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| daily 1 d | no heating either week | TabICL | 56 | 15,937 | -1,805 | 46.2 | 75.0 | 14.2 |
| daily 1 d | no heating either week | TimesFM-3, covariates | 56 | 16,724 | 3,000 | 43.5 | 82.1 | 13.5 |
| daily 1 d | much warmer | TabICL | 60 | 22,950 | 8,448 | 66.4 | 76.7 | 21.9 |
| daily 1 d | much warmer | TimesFM-3, covariates | 60 | 24,695 | 8,031 | 63.8 | 81.7 | 21.4 |
| daily 1 d | similar | TabICL | 180 | 16,951 | -227 | 60.2 | 82.2 | 48.4 |
| daily 1 d | similar | TimesFM-3, covariates | 180 | 19,055 | -2,304 | 55.2 | 86.7 | 49.5 |
| daily 1 d | much colder | TabICL | 53 | 18,471 | -8,463 | 77.0 | 75.5 | 15.5 |
| daily 1 d | much colder | TimesFM-3, covariates | 53 | 20,483 | -6,934 | 74.5 | 79.2 | 15.7 |
| daily 7 d | no heating either week | TabICL | 56 | 19,131 | -4,198 | 35.4 | 68.9 | 13.9 |
| daily 7 d | no heating either week | TimesFM-3, covariates | 56 | 20,621 | -3,204 | 30.4 | 73.0 | 13.9 |
| daily 7 d | much warmer | TabICL | 60 | 27,459 | 14,193 | 59.0 | 72.8 | 21.2 |
| daily 7 d | much warmer | TimesFM-3, covariates | 60 | 31,622 | 14,504 | 52.8 | 71.6 | 22.6 |
| daily 7 d | similar | TabICL | 180 | 20,574 | 1,243 | 51.0 | 78.0 | 48.0 |
| daily 7 d | similar | TimesFM-3, covariates | 180 | 22,110 | -2,784 | 47.3 | 82.3 | 47.7 |
| daily 7 d | much colder | TabICL | 53 | 24,873 | -6,986 | 68.5 | 71.2 | 16.9 |
| daily 7 d | much colder | TimesFM-3, covariates | 53 | 25,302 | -7,754 | 67.9 | 80.5 | 15.9 |
| hourly 24 h | no heating either week | TimesFM-3, covariates | 107 | 1,060 | 101 | 46.3 | 81.9 | 15.4 |
| hourly 24 h | much warmer | TimesFM-3, covariates | 111 | 1,058 | 161 | 60.8 | 78.8 | 19.0 |
| hourly 24 h | similar | TimesFM-3, covariates | 293 | 933 | 20 | 55.0 | 83.3 | 49.5 |
| hourly 24 h | much colder | TimesFM-3, covariates | 105 | 978 | -309 | 70.5 | 80.8 | 16.1 |

Insights:
- This table shows the clearest weakness: every model under-reacts to temperature change.
- After warming, the models over-forecast: +8k MWh/day at 1 day ahead, +14k at 7 days.
- After cooling, they under-forecast: −7k to −8k.
- “Much warmer” days are 17 % of days but cause 22 % of the error.
- Under-forecasting in cold snaps is costly: a balancing group would be short exactly when imbalance prices are high.

## Table 5. Results by radiation within the month (hourly: 10-15 h; ordinary days)

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

Used columns:
- Hourly: shortwave_radiation
- Daily: shortwave_radiation_sum

Definition:
- Dull: Radiation is in the lowest third for that calendar month.
- Average: Radiation is in the middle third for that month.
- Sunny: Radiation is in the highest third for that month.

For hourly data, these categories apply only to local hours 10:00–15:59.

Note: share of all-hours error; the midday window holds 30.4 %

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| daily 1 d | dull | TabICL | 125 | 18,300 | -255 | 62.3 | 77.6 | 36.3 |
| daily 1 d | dull | TimesFM-3, covariates | 125 | 21,014 | 765 | 56.7 | 81.6 | 37.9 |
| daily 1 d | average | TabICL | 111 | 16,450 | 1,012 | 64.1 | 80.2 | 29.0 |
| daily 1 d | average | TimesFM-3, covariates | 111 | 16,647 | 979 | 63.6 | 88.3 | 26.6 |
| daily 1 d | sunny | TabICL | 113 | 19,346 | -1,452 | 66.5 | 79.6 | 34.7 |
| daily 1 d | sunny | TimesFM-3, covariates | 113 | 21,763 | -2,981 | 62.4 | 82.3 | 35.5 |
| daily 7 d | dull | TabICL | 125 | 22,489 | 808 | 51.2 | 74.5 | 35.9 |
| daily 7 d | dull | TimesFM-3, covariates | 125 | 24,337 | -1,538 | 47.2 | 79.1 | 35.9 |
| daily 7 d | average | TabICL | 111 | 20,388 | 1,741 | 55.5 | 73.6 | 29.4 |
| daily 7 d | average | TimesFM-3, covariates | 111 | 21,889 | 1,241 | 52.2 | 81.7 | 29.2 |
| daily 7 d | sunny | TabICL | 113 | 23,564 | 1,544 | 59.3 | 75.7 | 34.6 |
| daily 7 d | sunny | TimesFM-3, covariates | 113 | 25,644 | -1,502 | 55.7 | 75.3 | 34.8 |
| hourly 24 h | dull | TimesFM-3, covariates | 283 | 1,193 | -250 | 56.1 | 78.8 | 10.3 |
| hourly 24 h | average | TimesFM-3, covariates | 303 | 1,148 | -13 | 57.4 | 83.8 | 9.8 |
| hourly 24 h | sunny | TimesFM-3, covariates | 214 | 1,224 | 262 | 58.1 | 81.3 | 10.3 |

Insights:
- The hourly midday bias follows the sun: sunny hours are over-forecast (+262 MWh/h) and dull hours under-forecast (−250). Rooftop solar used on site is not fully captured.
- The daily effect is small.
- Midday hours are 25 % of all hours but cause 30 % of the error.


## Results by heating degree days (ordinary days)

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

The hdd variable is categorized using heating degree days:

- hdd = 0 (no heating): HDD is 0, meaning no heating demand.
- hdd = mild: Positive HDD in the lowest third.
- hdd = cool: Positive HDD in the middle third.
- hdd = cold: Positive HDD in the highest third.

The mild/cool/cold thresholds are calculated separately for each evaluation year using only rows where hdd > 0,

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| daily 1 d | 0 (no heating) | TabICL | 75 | 16,676 | -2,903 | 48.8 | 77.3 | 19.9 |
| daily 1 d | 0 (no heating) | TimesFM-3, covariates | 75 | 18,143 | 87 | 44.3 | 80.0 | 19.6 |
| daily 1 d | mild | TabICL | 94 | 17,151 | 3,818 | 66.6 | 83.0 | 25.6 |
| daily 1 d | mild | TimesFM-3, covariates | 94 | 19,235 | 1,848 | 62.5 | 88.3 | 26.1 |
| daily 1 d | cool | TabICL | 92 | 20,156 | 1,127 | 60.4 | 77.2 | 29.4 |
| daily 1 d | cool | TimesFM-3, covariates | 92 | 19,596 | 5,050 | 61.5 | 85.9 | 26.0 |
| daily 1 d | cold | TabICL | 88 | 17,982 | -3,733 | 72.4 | 78.4 | 25.1 |
| daily 1 d | cold | TimesFM-3, covariates | 88 | 22,297 | -8,833 | 65.8 | 80.7 | 28.3 |
| daily 7 d | 0 (no heating) | TabICL | 75 | 19,602 | -4,861 | 39.8 | 70.3 | 19.1 |
| daily 7 d | 0 (no heating) | TimesFM-3, covariates | 75 | 20,488 | -4,955 | 37.1 | 72.4 | 18.5 |
| daily 7 d | mild | TabICL | 94 | 20,551 | 8,839 | 59.9 | 77.1 | 25.1 |
| daily 7 d | mild | TimesFM-3, covariates | 94 | 22,464 | 6,160 | 56.2 | 82.8 | 25.4 |
| daily 7 d | cool | TabICL | 92 | 24,420 | 4,833 | 50.0 | 76.4 | 28.8 |
| daily 7 d | cool | TimesFM-3, covariates | 92 | 24,417 | 5,721 | 50.0 | 81.1 | 26.6 |
| daily 7 d | cold | TabICL | 88 | 23,772 | -5,023 | 62.9 | 73.9 | 26.9 |
| daily 7 d | cold | TimesFM-3, covariates | 88 | 28,163 | -10,871 | 56.1 | 77.2 | 29.5 |
| hourly 24 h | 0 (no heating) | TimesFM-3, covariates | 137 | 1,002 | 14 | 51.4 | 82.4 | 21.8 |
| hourly 24 h | mild | TimesFM-3, covariates | 202 | 934 | 70 | 56.2 | 82.2 | 25.7 |
| hourly 24 h | cool | TimesFM-3, covariates | 195 | 1,035 | 59 | 56.4 | 80.0 | 28.0 |
| hourly 24 h | cold | TimesFM-3, covariates | 138 | 955 | -136 | 66.8 | 83.2 | 24.5 |

Insights:
- On cold days TimesFM-3 strongly under-forecasts: −8.8k at 1 day, −10.9k at 7 days. TabICL has about half that bias and about 20 % lower MAE.
- Mild days are over-forecast, the same under-reaction seen in Table 4.
- Days with no heating have the lowest skill compared with naive. In summer the naive model already does well, and there is no input for cooling demand.

## Results by wind speed (ordinary days)

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

 ``wind``: terciles of wind speed (calm / moderate / windy)

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| daily 1 d | calm | TabICL | 114 | 19,703 | -2,052 | 61.7 | 74.6 | 35.7 |
| daily 1 d | calm | TimesFM-3, covariates | 114 | 20,702 | -4,487 | 59.7 | 78.9 | 34.0 |
| daily 1 d | moderate | TabICL | 117 | 15,868 | 435 | 60.3 | 82.1 | 29.5 |
| daily 1 d | moderate | TimesFM-3, covariates | 117 | 17,589 | -49 | 56.0 | 88.9 | 29.7 |
| daily 1 d | windy | TabICL | 118 | 18,619 | 842 | 69.2 | 80.5 | 34.9 |
| daily 1 d | windy | TimesFM-3, covariates | 118 | 21,320 | 3,262 | 64.8 | 83.9 | 36.3 |
| daily 7 d | calm | TabICL | 114 | 22,930 | -3,003 | 55.4 | 67.8 | 34.0 |
| daily 7 d | calm | TimesFM-3, covariates | 114 | 24,593 | -5,853 | 52.2 | 73.7 | 33.7 |
| daily 7 d | moderate | TabICL | 117 | 19,942 | 2,760 | 50.0 | 77.5 | 30.3 |
| daily 7 d | moderate | TimesFM-3, covariates | 117 | 21,331 | 810 | 46.5 | 82.4 | 30.0 |
| daily 7 d | windy | TabICL | 118 | 23,658 | 4,196 | 59.4 | 78.4 | 35.7 |
| daily 7 d | windy | TimesFM-3, covariates | 118 | 26,044 | 3,032 | 55.3 | 79.9 | 36.3 |
| hourly 24 h | calm | TimesFM-3, covariates | 234 | 933 | 78 | 58.7 | 81.9 | 31.0 |
| hourly 24 h | moderate | TimesFM-3, covariates | 289 | 917 | 15 | 55.9 | 84.0 | 31.4 |
| hourly 24 h | windy | TimesFM-3, covariates | 214 | 1,088 | -81 | 60.6 | 79.9 | 37.6 |

Insights:
- Windy hours have the highest hourly error (1,088 MWh/h). They are 34 % of hours and cause 38 % of the error.
- The daily differences are modest. 

## Results by precipitation (ordinary days)

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

``precipitation``: dry / wet (hourly >= 0.1 mm, daily >= 1 mm).

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| daily 1 d | dry | TabICL | 134 | 18,289 | -1,209 | 65.3 | 81.3 | 38.9 |
| daily 1 d | dry | TimesFM-3, covariates | 134 | 18,923 | -2,749 | 64.1 | 82.8 | 36.6 |
| daily 1 d | wet | TabICL | 215 | 17,902 | 365 | 63.8 | 77.7 | 61.1 |
| daily 1 d | wet | TimesFM-3, covariates | 215 | 20,456 | 1,097 | 58.6 | 84.7 | 63.4 |
| daily 7 d | dry | TabICL | 134 | 22,572 | 1,426 | 57.2 | 74.1 | 39.3 |
| daily 7 d | dry | TimesFM-3, covariates | 134 | 24,900 | -229 | 52.7 | 76.7 | 40.1 |
| daily 7 d | wet | TabICL | 215 | 21,912 | 1,296 | 54.4 | 75.0 | 60.7 |
| daily 7 d | wet | TimesFM-3, covariates | 215 | 23,400 | -894 | 51.3 | 80.0 | 59.9 |
| hourly 24 h | dry | TimesFM-3, covariates | 346 | 971 | 24 | 59.1 | 82.3 | 68.3 |
| hourly 24 h | wet | TimesFM-3, covariates | 254 | 1,002 | -43 | 57.4 | 81.1 | 31.7 |

Insights:
- Dry and wet days have almost the same error and little bias. Precipitation carries no usable signal and can be dropped.

# Section 5. Overall 
- Model choice: TabICL for daily totals, TimesFM-3 with covariates for hourly.
- Calendar effects: the covariates mostly earn their value on holidays.
- Remaining weaknesses: the models respond too weakly to temperature changes and don’t fully capture midday solar. Both point to a bias-correction step or better temperature features rather than more inputs.
- Caveat: all weather results used observed weather, so treat them as an upper bound on real-world accuracy.
