# Report tables (test year)


# Section 2. Model comparison

## Table 1. Main results, hourly 1 h, test year

Sorted by MAE; the best model is in bold, the benchmark is the last row. Error reduction vs naive is computed on each model's own forecast rows (origins can differ between models). Pinball and coverage are empty for point forecasts.

| Model | Results folder | Setting | Origins | MAE (MWh) | MAPE % | Error reduction vs naive % | RMSE (MWh) | Bias (MWh) | Pinball (MWh) | 80 % band coverage % |
|---|---|---|---|---|---|---|---|---|---|---|
| **Tree-based** | tree-based |  | 8784 | 408 | 0.8 | 84.7 | 531 | -46 |  |  |
| SARIMAX | sarimax |  | 8784 | 489 | 1.0 | 81.6 | 706 |  | 196 | 84.7 |
| Seasonal naive | seasonal_naive |  | 366 | 2,154 | 4.8 | 0.0 | 2,931 | -9 |  |  |

## Table 1. Main results, hourly 24 h, test year

Sorted by MAE; the best model is in bold, the benchmark is the last row. Error reduction vs naive is computed on each model's own forecast rows (origins can differ between models). Pinball and coverage are empty for point forecasts.

| Model | Results folder | Setting | Origins | MAE (MWh) | MAPE % | Error reduction vs naive % | RMSE (MWh) | Bias (MWh) | Pinball (MWh) | 80 % band coverage % |
|---|---|---|---|---|---|---|---|---|---|---|
| **TimesFM-3, covariates** | foundation | ctx=8192 | 366 | 1,045 | 2.0 | 60.7 | 1,491 |  | 408 | 81.6 |
| Tree-based | tree-based |  | 8784 | 1,153 | 2.2 | 56.6 | 1,508 | -238 |  |  |
| TimesFM-3, no covariates | foundation | ctx=8192 | 366 | 1,260 | 2.4 | 52.6 | 2,038 |  | 504 | 78.7 |
| SARIMAX | sarimax |  | 366 | 1,330 | 2.6 | 49.9 | 1,798 |  | 530 | 76.5 |
| Seasonal naive | seasonal_naive |  | 366 | 2,657 | 5.1 | 0.0 | 4,102 | -32 |  |  |

## Table 1. Main results, daily 1 d, test year

Sorted by MAE; the best model is in bold, the benchmark is the last row. Error reduction vs naive is computed on each model's own forecast rows (origins can differ between models). Pinball and coverage are empty for point forecasts.

| Model | Results folder | Setting | Origins | MAE (MWh) | MAPE % | Error reduction vs naive % | RMSE (MWh) | Bias (MWh) | Pinball (MWh) | 80 % band coverage % |
|---|---|---|---|---|---|---|---|---|---|---|
| **TabICL** | foundation | features=default ctx=all | 366 | 19,091 | 1.5 | 66.9 | 24,700 |  | 7,448 | 76.5 |
| TimesFM-3, covariates | foundation | ctx=all | 366 | 20,691 | 1.7 | 64.2 | 27,985 |  | 8,186 | 85.2 |
| SARIMAX | sarimax |  | 366 | 21,600 | 1.7 | 62.6 | 29,852 |  | 8,520 | 80.6 |
| Tree-based | tree-based |  | 366 | 25,212 | 2.0 | 56.3 | 34,207 | -3,386 |  |  |
| TimesFM-3, no covariates | foundation | ctx=all | 366 | 28,796 | 2.4 | 50.1 | 46,954 |  | 11,572 | 80.3 |
| Seasonal naive | seasonal_naive |  | 366 | 57,716 | 4.7 | 0.0 | 89,644 | -785 |  |  |

## Table 1. Main results, daily 7 d, test year

Sorted by MAE; the best model is in bold, the benchmark is the last row. Error reduction vs naive is computed on each model's own forecast rows (origins can differ between models). Pinball and coverage are empty for point forecasts.

| Model | Results folder | Setting | Origins | MAE (MWh) | MAPE % | Error reduction vs naive % | RMSE (MWh) | Bias (MWh) | Pinball (MWh) | 80 % band coverage % |
|---|---|---|---|---|---|---|---|---|---|---|
| **TabICL** | foundation | features=default ctx=all | 360 | 22,911 | 1.8 | 59.7 | 29,839 |  | 9,033 | 75.0 |
| TimesFM-3, covariates | foundation | ctx=all | 360 | 24,331 | 1.9 | 57.2 | 32,539 |  | 9,645 | 78.6 |
| SARIMAX | sarimax |  | 360 | 29,385 | 2.3 | 48.3 | 39,181 |  | 11,590 | 82.3 |
| Tree-based | tree-based |  | 366 | 32,188 | 2.6 | 43.5 | 43,203 | -4,994 |  |  |
| TimesFM-3, no covariates | foundation | ctx=all | 360 | 34,562 | 2.8 | 39.2 | 52,545 |  | 13,833 | 78.9 |
| Seasonal naive | seasonal_naive |  | 360 | 56,842 | 4.6 | 0.0 | 88,603 | -60 |  |  |


# Section 3. Day types and lead time

## Table 3. Results by day type

Hours / days: forecast rows whose target falls on that day type (multi-step runs count a target once per step). Holiday, bridge day and Christmas can overlap, so the shares need not add up to 100 %.

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
| SARIMAX | daily 1 d | Normal weekday | 247 | 20,080 | 1.5 | 52,564 | 61.8 | 82.6 | 62.7 |
| SARIMAX | daily 1 d | Weekend | 102 | 19,249 | 1.8 | 46,037 | 58.2 | 81.4 | 24.8 |
| SARIMAX | daily 1 d | Holiday | 9 | 55,684 | 5.3 | 259,974 | 78.6 | 55.6 | 6.3 |
| SARIMAX | daily 1 d | Bridge day | 3 | 22,157 | 2.0 | 198,662 | 88.8 | 100.0 | 0.8 |
| SARIMAX | daily 1 d | Christmas / New Year | 9 | 81,205 | 7.2 | 155,159 | 47.7 | 22.2 | 9.2 |
| SARIMAX | daily 7 d | Normal weekday | 1715 | 28,067 | 2.1 | 51,449 | 45.4 | 83.0 | 65.0 |
| SARIMAX | daily 7 d | Weekend | 713 | 27,280 | 2.5 | 45,900 | 40.6 | 86.1 | 26.3 |
| SARIMAX | daily 7 d | Holiday | 56 | 57,875 | 5.6 | 282,852 | 79.5 | 44.6 | 4.4 |
| SARIMAX | daily 7 d | Bridge day | 19 | 59,295 | 5.2 | 195,819 | 69.7 | 47.4 | 1.5 |
| SARIMAX | daily 7 d | Christmas / New Year | 36 | 101,202 | 9.0 | 220,595 | 54.1 | 22.2 | 4.9 |
| SARIMAX | hourly 1 h | Normal weekday | 5928 | 462 | 0.9 | 2,461 | 81.2 | 87.0 | 63.7 |
| SARIMAX | hourly 1 h | Weekend | 2448 | 511 | 1.1 | 2,145 | 76.2 | 81.9 | 29.1 |
| SARIMAX | hourly 1 h | Holiday | 216 | 638 | 1.5 | 10,914 | 94.2 | 73.6 | 3.2 |
| SARIMAX | hourly 1 h | Bridge day | 72 | 795 | 1.8 | 8,278 | 90.4 | 63.9 | 1.3 |
| SARIMAX | hourly 1 h | Christmas / New Year | 216 | 837 | 1.8 | 6,631 | 87.4 | 64.8 | 4.2 |
| SARIMAX | hourly 24 h | Normal weekday | 5928 | 1,238 | 2.3 | 2,461 | 49.7 | 78.5 | 62.8 |
| SARIMAX | hourly 24 h | Weekend | 2447 | 1,260 | 2.7 | 2,146 | 41.3 | 78.0 | 26.4 |
| SARIMAX | hourly 24 h | Holiday | 217 | 2,597 | 5.9 | 10,905 | 76.2 | 42.4 | 4.8 |
| SARIMAX | hourly 24 h | Bridge day | 72 | 2,162 | 4.8 | 8,278 | 73.9 | 55.6 | 1.3 |
| SARIMAX | hourly 24 h | Christmas / New Year | 216 | 4,102 | 8.5 | 6,631 | 38.1 | 23.1 | 7.6 |
| Tree-based | daily 1 d | Normal weekday | 247 | 23,555 | 1.7 | 52,564 | 55.2 |  | 63.1 |
| Tree-based | daily 1 d | Weekend | 102 | 25,263 | 2.3 | 46,037 | 45.1 |  | 27.9 |
| Tree-based | daily 1 d | Holiday | 9 | 49,216 | 4.8 | 259,974 | 81.1 |  | 4.8 |
| Tree-based | daily 1 d | Bridge day | 3 | 54,459 | 4.8 | 198,662 | 72.6 |  | 1.8 |
| Tree-based | daily 1 d | Christmas / New Year | 9 | 49,772 | 4.5 | 155,159 | 67.9 |  | 4.9 |
| Tree-based | daily 7 d | Normal weekday | 1715 | 30,785 | 2.3 | 51,449 | 40.2 |  | 64.6 |
| Tree-based | daily 7 d | Weekend | 713 | 31,976 | 2.9 | 45,900 | 30.3 |  | 27.9 |
| Tree-based | daily 7 d | Holiday | 57 | 37,850 | 3.7 | 283,327 | 86.6 |  | 2.6 |
| Tree-based | daily 7 d | Bridge day | 21 | 102,509 | 9.1 | 198,662 | 48.4 |  | 2.6 |
| Tree-based | daily 7 d | Christmas / New Year | 57 | 48,033 | 4.2 | 167,479 | 71.3 |  | 3.3 |
| Tree-based | hourly 1 h | Normal weekday | 5928 | 405 | 0.7 | 2,461 | 83.6 |  | 67.0 |
| Tree-based | hourly 1 h | Weekend | 2448 | 401 | 0.9 | 2,145 | 81.3 |  | 27.4 |
| Tree-based | hourly 1 h | Holiday | 216 | 482 | 1.1 | 10,914 | 95.6 |  | 2.9 |
| Tree-based | hourly 1 h | Bridge day | 72 | 390 | 0.8 | 8,278 | 95.3 |  | 0.8 |
| Tree-based | hourly 1 h | Christmas / New Year | 216 | 494 | 1.0 | 6,631 | 92.6 |  | 3.0 |
| Tree-based | hourly 24 h | Normal weekday | 142272 | 1,109 | 2.0 | 2,461 | 54.9 |  | 65.0 |
| Tree-based | hourly 24 h | Weekend | 58752 | 1,186 | 2.5 | 2,145 | 44.7 |  | 28.7 |
| Tree-based | hourly 24 h | Holiday | 4908 | 1,398 | 3.2 | 11,414 | 87.8 |  | 2.8 |
| Tree-based | hourly 24 h | Bridge day | 1728 | 1,411 | 2.9 | 8,278 | 83.0 |  | 1.0 |
| Tree-based | hourly 24 h | Christmas / New Year | 4908 | 1,721 | 3.6 | 6,889 | 75.0 |  | 3.5 |

## Error by lead day, daily 7 d

Weather inputs are observed values, so the real decay with weather forecasts is larger.

| Lead day | MAE (MWh) TimesFM-3, no covariates | MAE (MWh) TimesFM-3, covariates | MAE (MWh) TabICL | MAE (MWh) SARIMAX | MAE (MWh) Tree-based | Error reduction vs naive % TimesFM-3, no covariates | Error reduction vs naive % TimesFM-3, covariates | Error reduction vs naive % TabICL | Error reduction vs naive % SARIMAX | Error reduction vs naive % Tree-based |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 28,430 | 18,557 | 19,060 | 20,996 | 25,212 | 49.8 | 67.2 | 66.3 | 62.9 | 56.3 |
| 2 | 32,887 | 22,299 | 21,974 | 26,499 | 27,924 | 42.7 | 61.1 | 61.7 | 53.8 | 51.7 |
| 3 | 34,566 | 24,158 | 23,169 | 28,790 | 29,088 | 39.9 | 58.0 | 59.7 | 49.9 | 49.3 |
| 4 | 35,209 | 24,924 | 23,747 | 29,967 | 36,844 | 38.5 | 56.5 | 58.5 | 47.7 | 35.4 |
| 5 | 36,151 | 26,568 | 24,066 | 31,932 | 32,262 | 36.3 | 53.2 | 57.6 | 43.8 | 43.1 |
| 6 | 37,065 | 27,066 | 24,263 | 33,134 | 33,610 | 34.2 | 51.9 | 56.9 | 41.1 | 40.3 |
| 7 | 37,622 | 26,744 | 24,099 | 34,377 | 40,543 | 32.9 | 52.3 | 57.0 | 38.7 | 27.7 |


# Section 4. Weather

## Table 4. Results by temperature change against last week (ordinary days)

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| hourly 1 h | no heating either week | SARIMAX | 107 | 451 | -14 | 77.1 | 86.3 | 13.5 |
| hourly 1 h | no heating either week | Tree-based | 107 | 445 | -87 | 77.5 |  | 15.7 |
| hourly 1 h | much warmer | SARIMAX | 111 | 492 | 8 | 81.8 | 83.8 | 18.2 |
| hourly 1 h | much warmer | Tree-based | 111 | 437 | 28 | 83.8 |  | 19.0 |
| hourly 1 h | similar | SARIMAX | 293 | 479 | -17 | 76.9 | 85.5 | 52.3 |
| hourly 1 h | similar | Tree-based | 293 | 393 | -52 | 81.0 |  | 50.8 |
| hourly 1 h | much colder | SARIMAX | 106 | 472 | 17 | 85.7 | 86.5 | 16.0 |
| hourly 1 h | much colder | Tree-based | 106 | 363 | -75 | 89.0 |  | 14.5 |
| hourly 24 h | no heating either week | TimesFM-3, no covariates | 107 | 1,179 | -9 | 40.3 | 79.4 | 15.3 |
| hourly 24 h | no heating either week | TimesFM-3, covariates | 107 | 1,058 | 117 | 46.4 | 81.9 | 15.4 |
| hourly 24 h | no heating either week | SARIMAX | 107 | 1,187 | -175 | 39.9 | 85.8 | 13.6 |
| hourly 24 h | no heating either week | Tree-based | 107 | 1,248 | 165 | 36.8 |  | 15.7 |
| hourly 24 h | much warmer | TimesFM-3, no covariates | 111 | 1,206 | 224 | 55.3 | 77.5 | 19.3 |
| hourly 24 h | much warmer | TimesFM-3, covariates | 111 | 1,058 | 169 | 60.8 | 79.0 | 19.0 |
| hourly 24 h | much warmer | SARIMAX | 111 | 1,340 | 85 | 50.4 | 74.1 | 18.9 |
| hourly 24 h | much warmer | Tree-based | 111 | 1,183 | -206 | 56.2 |  | 18.4 |
| hourly 24 h | similar | TimesFM-3, no covariates | 293 | 1,031 | -32 | 50.2 | 81.7 | 48.9 |
| hourly 24 h | similar | TimesFM-3, covariates | 293 | 934 | 33 | 54.9 | 83.3 | 49.6 |
| hourly 24 h | similar | SARIMAX | 293 | 1,227 | -119 | 40.8 | 78.0 | 51.3 |
| hourly 24 h | similar | Tree-based | 293 | 1,114 | -323 | 46.2 |  | 51.2 |
| hourly 24 h | much colder | TimesFM-3, no covariates | 105 | 1,125 | -487 | 66.0 | 77.9 | 16.5 |
| hourly 24 h | much colder | TimesFM-3, covariates | 105 | 974 | -284 | 70.6 | 80.6 | 16.0 |
| hourly 24 h | much colder | SARIMAX | 105 | 1,249 | 62 | 62.3 | 77.6 | 16.2 |
| hourly 24 h | much colder | Tree-based | 106 | 1,031 | -399 | 68.8 |  | 14.7 |
| daily 1 d | no heating either week | TimesFM-3, no covariates | 56 | 18,994 | -8,092 | 35.9 | 78.6 | 12.7 |
| daily 1 d | no heating either week | TimesFM-3, covariates | 56 | 17,308 | 4,231 | 41.6 | 82.1 | 14.5 |
| daily 1 d | no heating either week | TabICL | 56 | 16,244 | -1,197 | 45.2 | 76.8 | 14.2 |
| daily 1 d | no heating either week | SARIMAX | 56 | 18,027 | -792 | 39.1 | 82.1 | 14.6 |
| daily 1 d | no heating either week | Tree-based | 56 | 21,093 | 3,297 | 28.8 |  | 14.1 |
| daily 1 d | much warmer | TimesFM-3, no covariates | 60 | 27,511 | 6,611 | 59.7 | 80.0 | 19.7 |
| daily 1 d | much warmer | TimesFM-3, covariates | 60 | 22,469 | 9,345 | 67.1 | 85.0 | 20.1 |
| daily 1 d | much warmer | TabICL | 60 | 23,629 | 8,328 | 65.4 | 65.0 | 22.1 |
| daily 1 d | much warmer | SARIMAX | 60 | 22,008 | 3,181 | 67.8 | 80.0 | 19.1 |
| daily 1 d | much warmer | Tree-based | 60 | 26,528 | 7,450 | 61.1 |  | 19.0 |
| daily 1 d | similar | TimesFM-3, no covariates | 180 | 24,687 | -4,186 | 42.0 | 85.6 | 53.1 |
| daily 1 d | similar | TimesFM-3, covariates | 180 | 18,220 | -1,775 | 57.2 | 90.6 | 49.0 |
| daily 1 d | similar | TabICL | 180 | 17,080 | -326 | 59.9 | 82.2 | 47.9 |
| daily 1 d | similar | SARIMAX | 180 | 18,655 | -1,785 | 56.2 | 85.6 | 48.5 |
| daily 1 d | similar | Tree-based | 180 | 21,825 | -6,375 | 48.7 |  | 46.8 |
| daily 1 d | much colder | TimesFM-3, no covariates | 53 | 22,769 | -10,626 | 71.7 | 79.2 | 14.4 |
| daily 1 d | much colder | TimesFM-3, covariates | 53 | 20,807 | -8,618 | 74.1 | 77.4 | 16.5 |
| daily 1 d | much colder | TabICL | 53 | 19,120 | -8,333 | 76.2 | 73.6 | 15.8 |
| daily 1 d | much colder | SARIMAX | 53 | 23,306 | -7,127 | 71.0 | 73.6 | 17.8 |
| daily 1 d | much colder | Tree-based | 53 | 31,956 | -24,487 | 60.2 |  | 20.2 |
| daily 7 d | no heating either week | TimesFM-3, no covariates | 56 | 24,563 | -13,520 | 17.1 | 76.0 | 13.3 |
| daily 7 d | no heating either week | TimesFM-3, covariates | 56 | 20,603 | -3,298 | 30.4 | 73.5 | 14.2 |
| daily 7 d | no heating either week | TabICL | 56 | 19,481 | -4,338 | 34.2 | 71.2 | 13.9 |
| daily 7 d | no heating either week | SARIMAX | 56 | 21,796 | -5,160 | 26.4 | 93.1 | 12.6 |
| daily 7 d | no heating either week | Tree-based | 56 | 24,455 | 4,668 | 17.4 |  | 12.7 |
| daily 7 d | much warmer | TimesFM-3, no covariates | 60 | 33,865 | 12,144 | 49.5 | 76.9 | 19.5 |
| daily 7 d | much warmer | TimesFM-3, covariates | 60 | 29,729 | 16,394 | 55.7 | 73.3 | 21.7 |
| daily 7 d | much warmer | TabICL | 60 | 27,247 | 13,703 | 59.4 | 73.6 | 20.7 |
| daily 7 d | much warmer | SARIMAX | 60 | 29,157 | 2,919 | 56.5 | 83.2 | 17.9 |
| daily 7 d | much warmer | Tree-based | 60 | 33,610 | 7,664 | 49.9 |  | 18.5 |
| daily 7 d | similar | TimesFM-3, no covariates | 180 | 29,435 | -5,721 | 29.9 | 82.2 | 51.2 |
| daily 7 d | similar | TimesFM-3, covariates | 180 | 21,408 | -2,611 | 49.0 | 83.6 | 47.2 |
| daily 7 d | similar | TabICL | 180 | 20,963 | 472 | 50.1 | 77.8 | 47.9 |
| daily 7 d | similar | SARIMAX | 180 | 25,821 | -6,247 | 38.5 | 86.1 | 47.9 |
| daily 7 d | similar | Tree-based | 180 | 30,374 | -8,030 | 27.6 |  | 50.4 |
| daily 7 d | much colder | TimesFM-3, no covariates | 53 | 31,578 | -21,017 | 60.0 | 84.4 | 16.0 |
| daily 7 d | much colder | TimesFM-3, covariates | 53 | 26,239 | -11,636 | 66.7 | 76.4 | 16.8 |
| daily 7 d | much colder | TabICL | 53 | 26,289 | -9,193 | 66.7 | 70.1 | 17.5 |
| daily 7 d | much colder | SARIMAX | 53 | 39,747 | -14,261 | 49.6 | 67.1 | 21.5 |
| daily 7 d | much colder | Tree-based | 53 | 38,102 | -29,035 | 51.7 |  | 18.4 |

## Table 5. Results by radiation within the month (hourly: 10-16 h; ordinary days)

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| hourly 1 h | dull | SARIMAX | 283 | 476 | 12 | 82.5 | 82.4 | 8.4 |
| hourly 1 h | dull | Tree-based | 283 | 448 | -13 | 83.5 |  | 9.4 |
| hourly 1 h | average | SARIMAX | 303 | 466 | 8 | 82.7 | 84.0 | 8.2 |
| hourly 1 h | average | Tree-based | 303 | 473 | 23 | 82.4 |  | 9.8 |
| hourly 1 h | sunny | SARIMAX | 214 | 480 | -21 | 83.6 | 84.8 | 8.3 |
| hourly 1 h | sunny | Tree-based | 214 | 468 | 37 | 84.0 |  | 9.6 |
| hourly 24 h | dull | TimesFM-3, no covariates | 283 | 1,411 | -612 | 48.0 | 74.6 | 10.8 |
| hourly 24 h | dull | TimesFM-3, covariates | 283 | 1,194 | -242 | 56.0 | 78.2 | 10.3 |
| hourly 24 h | dull | SARIMAX | 283 | 1,409 | -6 | 48.1 | 78.2 | 9.5 |
| hourly 24 h | dull | Tree-based | 283 | 1,261 | -426 | 53.6 |  | 9.4 |
| hourly 24 h | average | TimesFM-3, no covariates | 303 | 1,362 | -87 | 49.4 | 79.5 | 10.3 |
| hourly 24 h | average | TimesFM-3, covariates | 303 | 1,149 | 2 | 57.3 | 84.0 | 9.8 |
| hourly 24 h | average | SARIMAX | 303 | 1,193 | -77 | 55.7 | 85.5 | 8.0 |
| hourly 24 h | average | Tree-based | 303 | 1,205 | 107 | 55.2 |  | 8.9 |
| hourly 24 h | sunny | TimesFM-3, no covariates | 214 | 1,452 | 607 | 50.4 | 79.7 | 10.9 |
| hourly 24 h | sunny | TimesFM-3, covariates | 214 | 1,226 | 294 | 58.1 | 81.3 | 10.3 |
| hourly 24 h | sunny | SARIMAX | 214 | 1,327 | -47 | 54.6 | 78.7 | 8.8 |
| hourly 24 h | sunny | Tree-based | 214 | 1,461 | 821 | 50.0 |  | 10.6 |
| daily 1 d | dull | TimesFM-3, no covariates | 125 | 23,819 | -10,327 | 50.9 | 81.6 | 35.6 |
| daily 1 d | dull | TimesFM-3, covariates | 125 | 20,280 | 1,190 | 58.2 | 83.2 | 37.8 |
| daily 1 d | dull | TabICL | 125 | 18,959 | -1,458 | 60.9 | 74.4 | 36.9 |
| daily 1 d | dull | SARIMAX | 125 | 20,834 | 422 | 57.0 | 80.8 | 37.6 |
| daily 1 d | dull | Tree-based | 125 | 23,693 | -12,338 | 51.2 |  | 35.3 |
| daily 1 d | average | TimesFM-3, no covariates | 111 | 22,068 | 1,538 | 51.8 | 83.8 | 29.3 |
| daily 1 d | average | TimesFM-3, covariates | 111 | 16,565 | 1,964 | 63.8 | 90.1 | 27.4 |
| daily 1 d | average | TabICL | 111 | 16,932 | 1,491 | 63.0 | 79.3 | 29.3 |
| daily 1 d | average | SARIMAX | 111 | 16,794 | 480 | 63.3 | 86.5 | 26.9 |
| daily 1 d | average | Tree-based | 111 | 22,184 | 676 | 51.5 |  | 29.3 |
| daily 1 d | sunny | TimesFM-3, no covariates | 113 | 25,998 | -2,239 | 55.0 | 82.3 | 35.1 |
| daily 1 d | sunny | TimesFM-3, covariates | 113 | 20,584 | -3,057 | 64.4 | 85.8 | 34.7 |
| daily 1 d | sunny | TabICL | 113 | 19,167 | -450 | 66.9 | 77.9 | 33.8 |
| daily 1 d | sunny | SARIMAX | 113 | 21,724 | -5,828 | 62.4 | 79.6 | 35.5 |
| daily 1 d | sunny | Tree-based | 113 | 26,292 | -3,066 | 54.5 |  | 35.4 |
| daily 7 d | dull | TimesFM-3, no covariates | 125 | 27,387 | -13,423 | 40.6 | 82.7 | 32.6 |
| daily 7 d | dull | TimesFM-3, covariates | 125 | 24,125 | -1,486 | 47.7 | 79.4 | 36.5 |
| daily 7 d | dull | TabICL | 125 | 23,199 | -673 | 49.7 | 75.7 | 36.4 |
| daily 7 d | dull | SARIMAX | 125 | 28,486 | -5,544 | 38.2 | 82.0 | 36.2 |
| daily 7 d | dull | Tree-based | 125 | 30,864 | -16,017 | 33.1 |  | 35.1 |
| daily 7 d | average | TimesFM-3, no covariates | 111 | 29,982 | -3,620 | 34.5 | 80.8 | 32.3 |
| daily 7 d | average | TimesFM-3, covariates | 111 | 21,877 | 1,530 | 52.2 | 80.8 | 29.9 |
| daily 7 d | average | TabICL | 111 | 20,644 | 1,483 | 54.9 | 73.6 | 29.2 |
| daily 7 d | average | SARIMAX | 111 | 25,861 | -3,874 | 43.5 | 86.5 | 29.7 |
| daily 7 d | average | Tree-based | 111 | 29,117 | -4,571 | 36.4 |  | 29.9 |
| daily 7 d | sunny | TimesFM-3, no covariates | 113 | 32,030 | -939 | 44.6 | 78.3 | 35.1 |
| daily 7 d | sunny | TimesFM-3, covariates | 113 | 24,200 | -2,412 | 58.2 | 77.1 | 33.6 |
| daily 7 d | sunny | TabICL | 113 | 23,873 | 838 | 58.7 | 75.1 | 34.4 |
| daily 7 d | sunny | SARIMAX | 113 | 29,069 | -7,682 | 49.7 | 83.4 | 34.0 |
| daily 7 d | sunny | Tree-based | 113 | 33,410 | 2,110 | 42.2 |  | 35.0 |

## Results in holiday weeks vs other ordinary days

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| hourly 1 h | holiday week | SARIMAX | 30 | 519 | 55 | 86.7 | 83.5 | 9.4 |
| hourly 1 h | holiday week | Tree-based | 30 | 417 | -16 | 89.3 |  | 8.9 |
| hourly 1 h | weekend | SARIMAX | 102 | 511 | -63 | 76.2 | 81.9 | 31.4 |
| hourly 1 h | weekend | Tree-based | 102 | 401 | -68 | 81.3 |  | 29.0 |
| hourly 1 h | other weekday | SARIMAX | 217 | 454 | 12 | 80.0 | 87.5 | 59.3 |
| hourly 1 h | other weekday | Tree-based | 217 | 403 | -41 | 82.2 |  | 62.1 |
| hourly 24 h | holiday week | TimesFM-3, no covariates | 30 | 1,383 | -202 | 64.5 | 78.2 | 10.8 |
| hourly 24 h | holiday week | TimesFM-3, covariates | 30 | 1,172 | 186 | 69.9 | 78.3 | 10.3 |
| hourly 24 h | holiday week | SARIMAX | 30 | 1,601 | 645 | 58.9 | 70.0 | 11.1 |
| hourly 24 h | holiday week | Tree-based | 30 | 1,167 | -218 | 70.0 |  | 8.9 |
| hourly 24 h | weekend | TimesFM-3, no covariates | 102 | 1,056 | 36 | 50.8 | 80.6 | 28.1 |
| hourly 24 h | weekend | TimesFM-3, covariates | 102 | 945 | 4 | 56.0 | 83.0 | 28.2 |
| hourly 24 h | weekend | SARIMAX | 102 | 1,260 | -721 | 41.3 | 78.0 | 29.6 |
| hourly 24 h | weekend | Tree-based | 102 | 1,186 | -405 | 44.7 |  | 30.6 |
| hourly 24 h | other weekday | TimesFM-3, no covariates | 217 | 1,078 | -81 | 52.3 | 80.0 | 61.1 |
| hourly 24 h | other weekday | TimesFM-3, covariates | 217 | 970 | 2 | 57.1 | 81.9 | 61.6 |
| hourly 24 h | other weekday | SARIMAX | 217 | 1,188 | 150 | 47.5 | 79.7 | 59.4 |
| hourly 24 h | other weekday | Tree-based | 217 | 1,102 | -174 | 51.3 |  | 60.5 |
| daily 1 d | holiday week | TimesFM-3, no covariates | 30 | 31,147 | -11,232 | 64.7 | 90.0 | 11.2 |
| daily 1 d | holiday week | TimesFM-3, covariates | 30 | 22,310 | 14,505 | 74.7 | 86.7 | 10.0 |
| daily 1 d | holiday week | TabICL | 30 | 23,718 | 886 | 73.1 | 73.3 | 11.1 |
| daily 1 d | holiday week | SARIMAX | 30 | 29,916 | 3,155 | 66.1 | 66.7 | 13.0 |
| daily 1 d | holiday week | Tree-based | 30 | 23,419 | -1,573 | 73.4 |  | 8.4 |
| daily 1 d | weekend | TimesFM-3, no covariates | 102 | 25,490 | -6,905 | 44.6 | 83.3 | 31.1 |
| daily 1 d | weekend | TimesFM-3, covariates | 102 | 20,428 | -10,750 | 55.6 | 86.3 | 31.1 |
| daily 1 d | weekend | TabICL | 102 | 17,234 | -746 | 62.6 | 79.4 | 27.4 |
| daily 1 d | weekend | SARIMAX | 102 | 19,249 | -1,796 | 58.2 | 81.4 | 28.4 |
| daily 1 d | weekend | Tree-based | 102 | 25,263 | -4,652 | 45.1 |  | 30.7 |
| daily 1 d | other weekday | TimesFM-3, no covariates | 217 | 22,260 | -1,529 | 53.3 | 81.1 | 57.7 |
| daily 1 d | other weekday | TimesFM-3, covariates | 217 | 18,188 | 3,146 | 61.8 | 86.2 | 58.9 |
| daily 1 d | other weekday | TabICL | 217 | 18,183 | -84 | 61.8 | 76.5 | 61.5 |
| daily 1 d | other weekday | SARIMAX | 217 | 18,720 | -2,139 | 60.7 | 84.8 | 58.7 |
| daily 1 d | other weekday | Tree-based | 217 | 23,574 | -5,954 | 50.5 |  | 60.9 |
| daily 7 d | holiday week | TimesFM-3, no covariates | 30 | 29,011 | -6,971 | 64.2 | 93.4 | 7.9 |
| daily 7 d | holiday week | TimesFM-3, covariates | 30 | 25,156 | 9,265 | 68.9 | 85.2 | 8.7 |
| daily 7 d | holiday week | TabICL | 30 | 26,952 | 2,285 | 66.7 | 81.6 | 9.6 |
| daily 7 d | holiday week | SARIMAX | 30 | 35,320 | 10,161 | 56.4 | 76.0 | 10.2 |
| daily 7 d | holiday week | Tree-based | 30 | 35,451 | -4,721 | 56.2 |  | 9.2 |
| daily 7 d | weekend | TimesFM-3, no covariates | 102 | 31,830 | -9,340 | 30.7 | 79.8 | 31.4 |
| daily 7 d | weekend | TimesFM-3, covariates | 102 | 23,817 | -10,984 | 48.1 | 80.6 | 29.9 |
| daily 7 d | weekend | TabICL | 102 | 22,246 | -1,363 | 51.5 | 76.9 | 28.9 |
| daily 7 d | weekend | SARIMAX | 102 | 27,280 | -4,671 | 40.6 | 86.1 | 28.8 |
| daily 7 d | weekend | Tree-based | 102 | 31,976 | -5,828 | 30.3 |  | 30.2 |
| daily 7 d | other weekday | TimesFM-3, no covariates | 217 | 28,837 | -4,657 | 39.5 | 79.4 | 60.7 |
| daily 7 d | other weekday | TimesFM-3, covariates | 217 | 23,026 | 2,645 | 51.7 | 77.6 | 61.5 |
| daily 7 d | other weekday | TabICL | 217 | 22,206 | 1,159 | 53.4 | 73.0 | 61.5 |
| daily 7 d | other weekday | SARIMAX | 217 | 27,131 | -8,239 | 43.0 | 83.9 | 61.0 |
| daily 7 d | other weekday | Tree-based | 217 | 30,183 | -6,963 | 36.6 |  | 60.6 |

## Results by heating degree days (ordinary days)

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| hourly 1 h | 0 (no heating) | SARIMAX | 137 | 463 | -41 | 77.5 | 85.3 | 20.8 |
| hourly 1 h | 0 (no heating) | Tree-based | 137 | 452 | -69 | 78.1 |  | 23.9 |
| hourly 1 h | mild | SARIMAX | 202 | 503 | 24 | 76.4 | 83.3 | 28.5 |
| hourly 1 h | mild | Tree-based | 202 | 394 | 3 | 81.5 |  | 26.3 |
| hourly 1 h | cool | SARIMAX | 195 | 472 | 17 | 80.1 | 86.4 | 26.3 |
| hourly 1 h | cool | Tree-based | 195 | 407 | -64 | 82.9 |  | 26.7 |
| hourly 1 h | cold | SARIMAX | 138 | 462 | -35 | 83.9 | 87.0 | 24.4 |
| hourly 1 h | cold | Tree-based | 138 | 369 | -64 | 87.2 |  | 23.0 |
| hourly 24 h | 0 (no heating) | TimesFM-3, no covariates | 137 | 1,134 | 25 | 45.0 | 80.7 | 22.1 |
| hourly 24 h | 0 (no heating) | TimesFM-3, covariates | 137 | 1,000 | 29 | 51.5 | 82.4 | 21.8 |
| hourly 24 h | 0 (no heating) | SARIMAX | 137 | 1,200 | -278 | 41.8 | 83.0 | 20.6 |
| hourly 24 h | 0 (no heating) | Tree-based | 137 | 1,268 | 80 | 38.5 |  | 23.9 |
| hourly 24 h | mild | TimesFM-3, no covariates | 202 | 1,048 | 68 | 50.8 | 80.3 | 25.7 |
| hourly 24 h | mild | TimesFM-3, covariates | 202 | 932 | 80 | 56.3 | 82.1 | 25.6 |
| hourly 24 h | mild | SARIMAX | 202 | 1,276 | 113 | 40.2 | 77.2 | 27.6 |
| hourly 24 h | mild | Tree-based | 202 | 991 | -18 | 53.5 |  | 23.6 |
| hourly 24 h | cool | TimesFM-3, no covariates | 195 | 1,170 | -54 | 50.7 | 79.3 | 28.2 |
| hourly 24 h | cool | TimesFM-3, covariates | 195 | 1,039 | 76 | 56.3 | 80.1 | 28.1 |
| hourly 24 h | cool | SARIMAX | 195 | 1,244 | 153 | 47.6 | 77.6 | 26.5 |
| hourly 24 h | cool | Tree-based | 195 | 1,054 | -266 | 55.6 |  | 24.7 |
| hourly 24 h | cold | TimesFM-3, no covariates | 138 | 1,045 | -263 | 63.7 | 79.9 | 24.0 |
| hourly 24 h | cold | TimesFM-3, covariates | 138 | 952 | -119 | 66.9 | 83.2 | 24.4 |
| hourly 24 h | cold | SARIMAX | 138 | 1,250 | -292 | 56.6 | 76.6 | 25.3 |
| hourly 24 h | cold | Tree-based | 138 | 1,248 | -742 | 56.6 |  | 27.8 |
| daily 1 d | 0 (no heating) | TimesFM-3, no covariates | 75 | 20,356 | -9,330 | 37.5 | 78.7 | 18.3 |
| daily 1 d | 0 (no heating) | TimesFM-3, covariates | 75 | 18,429 | 1,306 | 43.4 | 81.3 | 20.6 |
| daily 1 d | 0 (no heating) | TabICL | 75 | 16,594 | -2,284 | 49.1 | 78.7 | 19.4 |
| daily 1 d | 0 (no heating) | SARIMAX | 75 | 18,284 | -3,654 | 43.9 | 84.0 | 19.8 |
| daily 1 d | 0 (no heating) | Tree-based | 75 | 20,816 | 1,232 | 36.1 |  | 18.6 |
| daily 1 d | mild | TimesFM-3, no covariates | 94 | 23,257 | -298 | 54.7 | 89.4 | 26.1 |
| daily 1 d | mild | TimesFM-3, covariates | 94 | 18,040 | 2,522 | 64.8 | 90.4 | 25.3 |
| daily 1 d | mild | TabICL | 94 | 17,514 | 4,401 | 65.9 | 76.6 | 25.7 |
| daily 1 d | mild | SARIMAX | 94 | 18,880 | 2,742 | 63.2 | 85.1 | 25.6 |
| daily 1 d | mild | Tree-based | 94 | 19,581 | 1,687 | 61.8 |  | 21.9 |
| daily 1 d | cool | TimesFM-3, no covariates | 92 | 26,402 | 1,365 | 48.1 | 80.4 | 29.0 |
| daily 1 d | cool | TimesFM-3, covariates | 92 | 18,994 | 4,511 | 62.7 | 91.3 | 26.1 |
| daily 1 d | cool | TabICL | 92 | 20,841 | 1,521 | 59.0 | 75.0 | 29.9 |
| daily 1 d | cool | SARIMAX | 92 | 21,078 | 4,402 | 58.6 | 82.6 | 28.0 |
| daily 1 d | cool | Tree-based | 92 | 24,055 | -6,133 | 52.7 |  | 26.4 |
| daily 1 d | cold | TimesFM-3, no covariates | 88 | 25,261 | -8,761 | 61.2 | 80.7 | 26.6 |
| daily 1 d | cold | TimesFM-3, covariates | 88 | 21,300 | -8,280 | 67.3 | 80.7 | 28.0 |
| daily 1 d | cold | TabICL | 88 | 18,261 | -5,113 | 72.0 | 78.4 | 25.0 |
| daily 1 d | cold | SARIMAX | 88 | 20,886 | -10,696 | 68.0 | 77.3 | 26.5 |
| daily 1 d | cold | Tree-based | 88 | 31,593 | -17,050 | 51.5 |  | 33.1 |
| daily 7 d | 0 (no heating) | TimesFM-3, no covariates | 75 | 24,864 | -12,927 | 23.7 | 76.2 | 18.1 |
| daily 7 d | 0 (no heating) | TimesFM-3, covariates | 75 | 20,563 | -4,624 | 36.9 | 73.0 | 19.0 |
| daily 7 d | 0 (no heating) | TabICL | 75 | 19,558 | -4,747 | 40.0 | 72.4 | 18.7 |
| daily 7 d | 0 (no heating) | SARIMAX | 75 | 22,283 | -8,459 | 31.6 | 92.6 | 17.3 |
| daily 7 d | 0 (no heating) | Tree-based | 75 | 23,997 | 3,501 | 26.4 |  | 16.7 |
| daily 7 d | mild | TimesFM-3, no covariates | 94 | 26,203 | 1,683 | 48.9 | 87.4 | 23.9 |
| daily 7 d | mild | TimesFM-3, covariates | 94 | 20,361 | 6,595 | 60.3 | 85.6 | 23.6 |
| daily 7 d | mild | TabICL | 94 | 20,907 | 9,092 | 59.2 | 77.7 | 25.1 |
| daily 7 d | mild | SARIMAX | 94 | 22,894 | 8,030 | 55.4 | 91.3 | 22.3 |
| daily 7 d | mild | Tree-based | 94 | 25,368 | 6,597 | 50.5 |  | 22.1 |
| daily 7 d | cool | TimesFM-3, no covariates | 92 | 30,841 | 3,471 | 36.8 | 83.5 | 27.1 |
| daily 7 d | cool | TimesFM-3, covariates | 92 | 24,512 | 5,039 | 49.8 | 80.8 | 27.4 |
| daily 7 d | cool | TabICL | 92 | 25,170 | 3,471 | 48.4 | 75.0 | 29.1 |
| daily 7 d | cool | SARIMAX | 92 | 28,387 | 3,478 | 41.8 | 82.5 | 26.7 |
| daily 7 d | cool | Tree-based | 92 | 31,724 | -5,061 | 35.0 |  | 26.6 |
| daily 7 d | cold | TimesFM-3, no covariates | 88 | 36,565 | -19,056 | 43.0 | 74.3 | 30.9 |
| daily 7 d | cold | TimesFM-3, covariates | 88 | 28,082 | -11,655 | 56.2 | 75.7 | 30.1 |
| daily 7 d | cold | TabICL | 88 | 24,372 | -7,308 | 62.0 | 73.8 | 27.1 |
| daily 7 d | cold | SARIMAX | 88 | 37,373 | -27,713 | 41.7 | 69.8 | 33.7 |
| daily 7 d | cold | Tree-based | 88 | 42,885 | -30,529 | 33.1 |  | 34.6 |

## Results by wind speed (ordinary days)

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| hourly 1 h | calm | SARIMAX | 234 | 463 | -40 | 79.5 | 86.7 | 31.7 |
| hourly 1 h | calm | Tree-based | 234 | 374 | -39 | 83.4 |  | 30.2 |
| hourly 1 h | moderate | SARIMAX | 289 | 470 | -3 | 77.4 | 86.0 | 33.1 |
| hourly 1 h | moderate | Tree-based | 289 | 395 | -39 | 81.0 |  | 32.9 |
| hourly 1 h | windy | SARIMAX | 214 | 494 | 22 | 82.1 | 83.9 | 35.2 |
| hourly 1 h | windy | Tree-based | 214 | 440 | -62 | 84.1 |  | 36.9 |
| hourly 24 h | calm | TimesFM-3, no covariates | 234 | 1,020 | 297 | 54.8 | 81.4 | 30.3 |
| hourly 24 h | calm | TimesFM-3, covariates | 234 | 936 | 86 | 58.5 | 81.8 | 31.1 |
| hourly 24 h | calm | SARIMAX | 234 | 1,226 | -157 | 45.7 | 77.6 | 32.1 |
| hourly 24 h | calm | Tree-based | 234 | 1,022 | 55 | 54.7 |  | 29.4 |
| hourly 24 h | moderate | TimesFM-3, no covariates | 289 | 1,031 | -26 | 50.5 | 82.9 | 31.5 |
| hourly 24 h | moderate | TimesFM-3, covariates | 289 | 914 | 31 | 56.1 | 84.2 | 31.3 |
| hourly 24 h | moderate | SARIMAX | 289 | 1,159 | -156 | 44.3 | 81.0 | 31.2 |
| hourly 24 h | moderate | Tree-based | 289 | 1,113 | -185 | 46.5 |  | 33.0 |
| hourly 24 h | windy | TimesFM-3, no covariates | 214 | 1,240 | -428 | 55.1 | 75.9 | 38.2 |
| hourly 24 h | windy | TimesFM-3, covariates | 214 | 1,088 | -60 | 60.6 | 79.7 | 37.6 |
| hourly 24 h | windy | SARIMAX | 214 | 1,348 | 122 | 51.2 | 76.5 | 36.7 |
| hourly 24 h | windy | Tree-based | 214 | 1,255 | -594 | 54.5 |  | 37.6 |
| daily 1 d | calm | TimesFM-3, no covariates | 114 | 24,506 | 3,489 | 52.3 | 82.5 | 33.4 |
| daily 1 d | calm | TimesFM-3, covariates | 114 | 20,472 | -3,516 | 60.2 | 82.5 | 34.8 |
| daily 1 d | calm | TabICL | 114 | 20,332 | -1,582 | 60.5 | 72.8 | 36.1 |
| daily 1 d | calm | SARIMAX | 114 | 20,278 | -3,893 | 60.6 | 78.9 | 33.4 |
| daily 1 d | calm | Tree-based | 114 | 26,266 | -3,619 | 48.9 |  | 35.7 |
| daily 1 d | moderate | TimesFM-3, no covariates | 117 | 21,108 | -443 | 47.2 | 85.5 | 29.5 |
| daily 1 d | moderate | TimesFM-3, covariates | 117 | 17,134 | 500 | 57.1 | 91.5 | 29.9 |
| daily 1 d | moderate | TabICL | 117 | 15,920 | 929 | 60.2 | 79.5 | 29.0 |
| daily 1 d | moderate | SARIMAX | 117 | 18,735 | -1,448 | 53.1 | 86.3 | 31.7 |
| daily 1 d | moderate | Tree-based | 117 | 20,376 | -4,783 | 49.0 |  | 28.4 |
| daily 1 d | windy | TimesFM-3, no covariates | 118 | 26,284 | -14,569 | 56.6 | 79.7 | 37.1 |
| daily 1 d | windy | TimesFM-3, covariates | 118 | 20,011 | 3,082 | 66.9 | 84.7 | 35.2 |
| daily 1 d | windy | TabICL | 118 | 18,938 | 35 | 68.7 | 78.8 | 34.8 |
| daily 1 d | windy | SARIMAX | 118 | 20,504 | 515 | 66.1 | 81.4 | 34.9 |
| daily 1 d | windy | Tree-based | 118 | 25,565 | -7,131 | 57.8 |  | 35.9 |
| daily 7 d | calm | TimesFM-3, no covariates | 114 | 29,521 | 876 | 42.6 | 80.6 | 32.6 |
| daily 7 d | calm | TimesFM-3, covariates | 114 | 23,950 | -5,954 | 53.4 | 74.7 | 33.6 |
| daily 7 d | calm | TabICL | 114 | 23,642 | -3,519 | 54.0 | 68.8 | 34.4 |
| daily 7 d | calm | SARIMAX | 114 | 29,304 | -10,877 | 43.0 | 82.6 | 34.6 |
| daily 7 d | calm | Tree-based | 114 | 31,471 | 5,357 | 38.8 |  | 33.2 |
| daily 7 d | moderate | TimesFM-3, no covariates | 117 | 26,400 | -1,260 | 33.7 | 85.3 | 29.9 |
| daily 7 d | moderate | TimesFM-3, covariates | 117 | 20,361 | 372 | 48.9 | 83.7 | 29.3 |
| daily 7 d | moderate | TabICL | 117 | 20,615 | 2,518 | 48.3 | 77.3 | 30.7 |
| daily 7 d | moderate | SARIMAX | 117 | 25,028 | -3,837 | 37.2 | 88.1 | 30.3 |
| daily 7 d | moderate | Tree-based | 117 | 26,624 | -3,243 | 33.2 |  | 28.8 |
| daily 7 d | windy | TimesFM-3, no covariates | 118 | 33,289 | -18,187 | 42.9 | 76.0 | 37.4 |
| daily 7 d | windy | TimesFM-3, covariates | 118 | 26,011 | 3,017 | 55.4 | 78.8 | 37.1 |
| daily 7 d | windy | TabICL | 118 | 23,577 | 2,444 | 59.6 | 78.3 | 34.9 |
| daily 7 d | windy | SARIMAX | 118 | 29,223 | -2,507 | 49.9 | 80.9 | 35.1 |
| daily 7 d | windy | Tree-based | 118 | 35,347 | -21,280 | 39.4 |  | 38.0 |

## Results by precipitation (ordinary days)

Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. Hourly MWh per hour, daily MWh per day.

| Horizon | Weather | Model | Days | MAE (MWh) | Bias (MWh) | Error reduction vs naive % | 80 % band coverage % | Share of all error % |
|---|---|---|---|---|---|---|---|---|
| hourly 1 h | dry | SARIMAX | 346 | 470 | -18 | 80.2 | 86.2 | 68.1 |
| hourly 1 h | dry | Tree-based | 346 | 405 | -38 | 82.9 |  | 69.4 |
| hourly 1 h | wet | SARIMAX | 254 | 491 | 20 | 79.2 | 84.1 | 31.9 |
| hourly 1 h | wet | Tree-based | 254 | 399 | -65 | 83.1 |  | 30.6 |
| hourly 24 h | dry | TimesFM-3, no covariates | 346 | 1,077 | 71 | 54.7 | 81.3 | 67.6 |
| hourly 24 h | dry | TimesFM-3, covariates | 346 | 970 | 40 | 59.2 | 82.3 | 68.3 |
| hourly 24 h | dry | SARIMAX | 346 | 1,205 | -87 | 49.3 | 78.8 | 66.8 |
| hourly 24 h | dry | Tree-based | 346 | 1,132 | -138 | 52.3 |  | 69.0 |
| hourly 24 h | wet | TimesFM-3, no covariates | 254 | 1,146 | -342 | 51.3 | 77.3 | 32.4 |
| hourly 24 h | wet | TimesFM-3, covariates | 254 | 1,003 | -31 | 57.4 | 81.1 | 31.7 |
| hourly 24 h | wet | SARIMAX | 254 | 1,332 | -7 | 43.4 | 77.4 | 33.2 |
| hourly 24 h | wet | Tree-based | 254 | 1,132 | -485 | 51.9 |  | 31.0 |
| daily 1 d | dry | TimesFM-3, no covariates | 134 | 23,449 | 2,220 | 55.5 | 81.3 | 37.6 |
| daily 1 d | dry | TimesFM-3, covariates | 134 | 18,643 | -2,545 | 64.6 | 85.8 | 37.3 |
| daily 1 d | dry | TabICL | 134 | 18,877 | -499 | 64.2 | 76.9 | 39.4 |
| daily 1 d | dry | SARIMAX | 134 | 18,683 | -5,642 | 64.5 | 81.3 | 36.2 |
| daily 1 d | dry | Tree-based | 134 | 27,843 | -3,530 | 47.1 |  | 44.4 |
| daily 1 d | wet | TimesFM-3, no covariates | 215 | 24,291 | -7,770 | 50.8 | 83.3 | 62.4 |
| daily 1 d | wet | TimesFM-3, covariates | 215 | 19,542 | 1,685 | 60.4 | 86.5 | 62.7 |
| daily 1 d | wet | TabICL | 215 | 18,073 | -3 | 63.4 | 77.2 | 60.6 |
| daily 1 d | wet | SARIMAX | 215 | 20,557 | 947 | 58.4 | 82.8 | 63.8 |
| daily 1 d | wet | Tree-based | 215 | 21,693 | -6,235 | 56.1 |  | 55.6 |
| daily 7 d | dry | TimesFM-3, no covariates | 134 | 28,974 | 2,925 | 45.0 | 82.3 | 37.6 |
| daily 7 d | dry | TimesFM-3, covariates | 134 | 24,557 | -1,191 | 53.4 | 76.1 | 40.5 |
| daily 7 d | dry | TabICL | 134 | 22,768 | 180 | 56.8 | 75.3 | 38.9 |
| daily 7 d | dry | SARIMAX | 134 | 28,585 | -9,996 | 45.7 | 82.7 | 39.7 |
| daily 7 d | dry | Tree-based | 134 | 33,063 | 1,102 | 37.2 |  | 41.0 |
| daily 7 d | wet | TimesFM-3, no covariates | 215 | 30,206 | -11,975 | 37.1 | 79.6 | 62.4 |
| daily 7 d | wet | TimesFM-3, covariates | 215 | 22,721 | -590 | 52.7 | 81.0 | 59.5 |
| daily 7 d | wet | TabICL | 215 | 22,495 | 717 | 53.2 | 74.6 | 61.1 |
| daily 7 d | wet | SARIMAX | 215 | 27,364 | -3,005 | 43.0 | 84.6 | 60.3 |
| daily 7 d | wet | Tree-based | 215 | 29,921 | -11,202 | 37.7 |  | 59.0 |
