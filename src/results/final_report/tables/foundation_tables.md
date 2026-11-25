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
