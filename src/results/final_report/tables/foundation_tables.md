# Foundation models: specific tables

## Settings compared on the validation year (foundation)

Chosen = lowest validation MAE; only the chosen setting was run on the test year.

| Model | Experiment | Horizon | Setting | MAE (MWh) | Pinball (MWh) | 80 % band coverage % | Chosen |
|---|---|---|---|---|---|---|---|
| TimesFM-3, no covariates | F1 | hourly 24 h | ctx=8192 | 1,130 | 453 | 80.1 | yes |
| TimesFM-3, no covariates | F1 | hourly 24 h | ctx=4096 | 1,156 | 463 | 80.0 |  |
| TimesFM-3, no covariates | F1 | hourly 24 h | ctx=2048 | 1,186 | 476 | 78.9 |  |
| TimesFM-3, covariates | F2 | hourly 24 h | ctx=8192 | 946 | 371 | 82.5 | yes |
| TimesFM-3, covariates | F2 | hourly 24 h | ctx=4096 | 965 | 382 | 83.4 |  |
| TimesFM-3, covariates | F2 | hourly 24 h | ctx=2048 | 992 | 395 | 82.5 |  |
| TimesFM-3, no covariates | F4 | daily 1 d | ctx=all | 24,456 | 10,021 | 87.7 | yes |
| TimesFM-3, covariates | F5 | daily 1 d | ctx=all | 17,642 | 6,958 | 89.9 | yes |
| TabICL | F6 | daily 1 d | features=default ctx=all | 15,792 | 6,160 | 82.2 | yes |
| TabICL | F6 | daily 1 d | features=ours ctx=all | 16,154 | 6,218 | 82.5 |  |
| TabICL | F6 | daily 1 d | features=ours ctx=730 | 16,476 | 6,407 | 80.8 |  |
| TabICL | F6 | daily 1 d | features=default ctx=730 | 16,558 | 6,427 | 80.0 |  |
| TimesFM-3, no covariates | F4 | daily 7 d | ctx=all | 29,823 | 11,981 | 84.8 | yes |
| TimesFM-3, covariates | F5 | daily 7 d | ctx=all | 21,959 | 8,505 | 84.6 | yes |
| TabICL | F6 | daily 7 d | features=default ctx=all | 19,996 | 7,870 | 76.6 | yes |
| TabICL | F6 | daily 7 d | features=ours ctx=all | 20,310 | 7,837 | 76.6 |  |
| TabICL | F6 | daily 7 d | features=default ctx=730 | 21,138 | 8,216 | 76.1 |  |
| TabICL | F6 | daily 7 d | features=ours ctx=730 | 21,364 | 8,259 | 75.0 |  |

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
