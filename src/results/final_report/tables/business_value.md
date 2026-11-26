# Business value

## Yearly forecast error volume

National scale, all days of the year. Multi-step runs: average lead step.

| Model | Horizon | MAE (MWh) | Yearly error (TWh) | Naive yearly error (TWh) | Reduction vs naive (TWh) | Reference | Reduction vs reference (TWh) |
|---|---|---|---|---|---|---|---|
| TimesFM-3, covariates | hourly 1 h | 386 | 3.39 | 23.33 | 19.95 |  |  |
| Tree-based | hourly 1 h | 408 | 3.58 | 23.33 | 19.75 |  |  |
| SARIMAX | hourly 1 h | 489 | 4.29 | 23.33 | 19.04 |  |  |
| TimesFM-3, covariates | hourly 24 h | 1,045 | 9.18 | 23.34 | 14.16 |  |  |
| Tree-based | hourly 24 h | 1,153 | 10.12 | 23.34 | 13.21 |  |  |
| SARIMAX | hourly 24 h | 1,330 | 11.69 | 23.34 | 11.65 |  |  |
| TabICL | daily 1 d | 19,091 | 6.99 | 21.12 | 14.14 |  |  |
| TimesFM-3, covariates | daily 1 d | 20,691 | 7.57 | 21.12 | 13.55 |  |  |
| SARIMAX | daily 1 d | 21,600 | 7.91 | 21.12 | 13.22 |  |  |
| Tree-based | daily 1 d | 25,212 | 9.23 | 21.12 | 11.90 |  |  |
| TabICL | daily 7 d | 22,911 | 8.38 | 20.80 | 12.42 |  |  |
| TimesFM-3, covariates | daily 7 d | 24,331 | 8.90 | 20.80 | 11.90 |  |  |
| SARIMAX | daily 7 d | 29,385 | 10.76 | 20.80 | 10.05 |  |  |
| Tree-based | daily 7 d | 32,091 | 11.74 | 20.80 | 9.06 |  |  |

## Accuracy where power is expensive

Bias < 0 = under-forecast. Error at day-ahead price = sum of |error| x |price|, national scale.

| Model | Horizon | MAE (MWh) | Price-weighted MAE (MWh) | Price-weighted / plain MAE | MAE top-10 % price (MWh) | Bias top-10 % price (MWh) | Error at day-ahead price (EUR m) | Naive error at day-ahead price (EUR m) | Value reduction vs reference (EUR m) |
|---|---|---|---|---|---|---|---|---|---|
| TimesFM-3, covariates | hourly 1 h | 386 | 373 | 0.97 | 361 | 68 | 260.9 | 1,847.9 |  |
| Tree-based | hourly 1 h | 408 | 396 | 0.97 | 403 | -87 | 277.3 | 1,847.9 |  |
| SARIMAX | hourly 1 h | 489 | 481 | 0.98 | 428 | -62 | 337.0 | 1,847.9 |  |
| TimesFM-3, covariates | hourly 24 h | 1,045 | 1,029 | 0.99 | 1,104 | 186 | 720.5 | 1,848.1 |  |
| Tree-based | hourly 24 h | 1,153 | 1,116 | 0.97 | 1,080 | -272 | 782.5 | 1,850.3 |  |
| SARIMAX | hourly 24 h | 1,330 | 1,331 | 1.00 | 1,208 | -271 | 931.8 | 1,848.1 |  |
| TabICL | daily 1 d | 19,091 | 19,030 | 1.00 | 22,345 | -6,904 | 546.8 | 1,664.0 |  |
| TimesFM-3, covariates | daily 1 d | 20,691 | 20,763 | 1.00 | 25,015 | -12,509 | 596.6 | 1,664.0 |  |
| SARIMAX | daily 1 d | 21,600 | 21,437 | 0.99 | 19,942 | -10,815 | 616.0 | 1,664.0 |  |
| Tree-based | daily 1 d | 25,212 | 25,541 | 1.01 | 28,154 | -14,077 | 733.9 | 1,664.0 |  |
| TabICL | daily 7 d | 22,911 | 22,999 | 1.00 | 28,223 | -10,649 | 661.9 | 1,641.3 |  |
| TimesFM-3, covariates | daily 7 d | 24,331 | 24,716 | 1.02 | 29,740 | -12,145 | 711.3 | 1,641.3 |  |
| SARIMAX | daily 7 d | 29,385 | 30,658 | 1.04 | 38,862 | -31,297 | 882.3 | 1,641.3 |  |
| Tree-based | daily 7 d | 32,091 | 32,431 | 1.01 | 34,873 | -16,078 | 933.4 | 1,641.3 |  |

## Table 6. Yearly value of the hourly forecasts (EUR million)

Error reduction x imbalance cost x market share. Upper bound: observed weather inputs.

| Model | Horizon | Against | Market share % | 5 EUR/MWh (EUR m) | 10 EUR/MWh (EUR m) | 20 EUR/MWh (EUR m) |
|---|---|---|---|---|---|---|
| TimesFM-3, covariates | hourly 1 h | vs seasonal naive | 1.0 | 1.0 | 2.0 | 4.0 |
| TimesFM-3, covariates | hourly 1 h | vs seasonal naive | 5.0 | 5.0 | 10.0 | 19.9 |
| TimesFM-3, covariates | hourly 1 h | vs seasonal naive | 10.0 | 10.0 | 19.9 | 39.9 |
| Tree-based | hourly 1 h | vs seasonal naive | 1.0 | 1.0 | 2.0 | 4.0 |
| Tree-based | hourly 1 h | vs seasonal naive | 5.0 | 4.9 | 9.9 | 19.8 |
| Tree-based | hourly 1 h | vs seasonal naive | 10.0 | 9.9 | 19.8 | 39.5 |
| SARIMAX | hourly 1 h | vs seasonal naive | 1.0 | 1.0 | 1.9 | 3.8 |
| SARIMAX | hourly 1 h | vs seasonal naive | 5.0 | 4.8 | 9.5 | 19.0 |
| SARIMAX | hourly 1 h | vs seasonal naive | 10.0 | 9.5 | 19.0 | 38.1 |
| TimesFM-3, covariates | hourly 24 h | vs seasonal naive | 1.0 | 0.7 | 1.4 | 2.8 |
| TimesFM-3, covariates | hourly 24 h | vs seasonal naive | 5.0 | 3.5 | 7.1 | 14.2 |
| TimesFM-3, covariates | hourly 24 h | vs seasonal naive | 10.0 | 7.1 | 14.2 | 28.3 |
| Tree-based | hourly 24 h | vs seasonal naive | 1.0 | 0.7 | 1.3 | 2.6 |
| Tree-based | hourly 24 h | vs seasonal naive | 5.0 | 3.3 | 6.6 | 13.2 |
| Tree-based | hourly 24 h | vs seasonal naive | 10.0 | 6.6 | 13.2 | 26.4 |
| SARIMAX | hourly 24 h | vs seasonal naive | 1.0 | 0.6 | 1.2 | 2.3 |
| SARIMAX | hourly 24 h | vs seasonal naive | 5.0 | 2.9 | 5.8 | 11.7 |
| SARIMAX | hourly 24 h | vs seasonal naive | 10.0 | 5.8 | 11.7 | 23.3 |
