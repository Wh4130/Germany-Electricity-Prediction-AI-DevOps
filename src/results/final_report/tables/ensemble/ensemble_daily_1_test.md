# Averaging models: daily 1d, test year

## RMSE and MAE of each model on the common forecasts

366 forecasts that every model has (same origin and target time). Sorted by RMSE.

| Model | n | RMSE (MWh) | MAE (MWh) | Bias (MWh) |
|---|---|---|---|---|
| **TabICL** | 366 | 24,700 | 19,091 | -205 |
| TimesFM-3, covariates | 366 | 27,985 | 20,691 | 560 |
| SARIMAX | 366 | 29,852 | 21,600 | -1,138 |
| Tree-based | 366 | 34,207 | 25,212 | -3,386 |

## Correlation of the errors

Errors = forecast minus actual. Below 1 means an average can cancel part of the errors.

| Model | TabICL | TimesFM-3, covariates | SARIMAX | Tree-based |
|---|---|---|---|---|
| TabICL | 1.00 | 0.72 | 0.66 | 0.61 |
| TimesFM-3, covariates | 0.72 | 1.00 | 0.76 | 0.58 |
| SARIMAX | 0.66 | 0.76 | 1.00 | 0.53 |
| Tree-based | 0.61 | 0.58 | 0.53 | 1.00 |

## Pairs of models: does the average beat the better one?

Expected: the correlation of the errors is below the threshold (3 - q^2) / (2 q), q = RMSE of the other model / RMSE of the better one. Result: the RMSE of the average is below that of the better model. Expected and result agree in 6 of 6 pairs. 'RMSE change' is negative when the average is better.

| Better model | Other model | Error correlation | RMSE ratio | Threshold | Expected | Result | RMSE of the better model (MWh) | RMSE of the average (MWh) | RMSE change vs better % |
|---|---|---|---|---|---|---|---|---|---|
| SARIMAX | Tree-based | 0.53 | 1.15 | 0.74 | helps | helps | 29,852 | 27,998 | -6.2 |
| TimesFM-3, covariates | SARIMAX | 0.76 | 1.07 | 0.87 | helps | helps | 27,985 | 27,085 | -3.2 |
| TimesFM-3, covariates | Tree-based | 0.58 | 1.22 | 0.62 | helps | helps | 27,985 | 27,647 | -1.2 |
| TabICL | TimesFM-3, covariates | 0.72 | 1.13 | 0.76 | helps | helps | 24,700 | 24,437 | -1.1 |
| TabICL | SARIMAX | 0.66 | 1.21 | 0.64 | does not help | does not help | 24,700 | 24,860 | +0.6 |
| TabICL | Tree-based | 0.61 | 1.38 | 0.39 | does not help | does not help | 24,700 | 26,459 | +7.1 |

## Equal-weight averages

Sorted by RMSE. Gain = reduction compared with the best single model (lowest RMSE) inside the same combination (negative: the average is worse). No significance test.

| Average of | Models | RMSE (MWh) | RMSE gain vs best single % | MAE (MWh) | MAE gain vs best single % |
|---|---|---|---|---|---|
| **TabICL + TimesFM-3, covariates** | 2 | 24,437 | 1.1 | 18,534 | 2.9 |
| TabICL + TimesFM-3, covariates + SARIMAX | 3 | 24,745 | -0.2 | 18,373 | 3.8 |
| TabICL + TimesFM-3, covariates + SARIMAX + Tree-based | 4 | 24,849 | -0.6 | 18,568 | 2.7 |
| TabICL + SARIMAX | 2 | 24,860 | -0.6 | 18,593 | 2.6 |
| TabICL + TimesFM-3, covariates + Tree-based | 3 | 25,129 | -1.7 | 18,850 | 1.3 |
| TabICL + SARIMAX + Tree-based | 3 | 25,247 | -2.2 | 18,938 | 0.8 |
| TimesFM-3, covariates + SARIMAX + Tree-based | 3 | 26,422 | 5.6 | 19,362 | 6.4 |
| TabICL + Tree-based | 2 | 26,459 | -7.1 | 20,008 | -4.8 |
| TimesFM-3, covariates + SARIMAX | 2 | 27,085 | 3.2 | 19,703 | 4.8 |
| TimesFM-3, covariates + Tree-based | 2 | 27,647 | 1.2 | 20,241 | 2.2 |
| SARIMAX + Tree-based | 2 | 27,998 | 6.2 | 20,415 | 5.5 |
