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
