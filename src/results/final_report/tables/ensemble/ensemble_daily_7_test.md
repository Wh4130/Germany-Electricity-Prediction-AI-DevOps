# Averaging models: daily 7d, test year

## RMSE and MAE of each model on the common forecasts

2520 forecasts that every model has (same origin and target time). Sorted by RMSE.

| Model | n | RMSE (MWh) | MAE (MWh) | Bias (MWh) |
|---|---|---|---|---|
| **TabICL** | 2520 | 29,839 | 22,911 | 618 |
| TimesFM-3, covariates | 2520 | 32,539 | 24,331 | -830 |
| SARIMAX | 2520 | 39,181 | 29,385 | -5,147 |
| Tree-based | 2520 | 43,116 | 32,091 | -4,821 |

## Correlation of the errors

Errors = forecast minus actual. Below 1 means an average can cancel part of the errors.

| Model | TabICL | TimesFM-3, covariates | SARIMAX | Tree-based |
|---|---|---|---|---|
| TabICL | 1.00 | 0.79 | 0.70 | 0.55 |
| TimesFM-3, covariates | 0.79 | 1.00 | 0.73 | 0.57 |
| SARIMAX | 0.70 | 0.73 | 1.00 | 0.56 |
| Tree-based | 0.55 | 0.57 | 0.56 | 1.00 |

## Pairs of models: does the average beat the better one?

Expected: the correlation of the errors is below the threshold (3 - q^2) / (2 q), q = RMSE of the other model / RMSE of the better one. Result: the RMSE of the average is below that of the better model. Expected and result agree in 6 of 6 pairs. 'RMSE change' is negative when the average is better.

| Better model | Other model | Error correlation | RMSE ratio | Threshold | Expected | Result | RMSE of the better model (MWh) | RMSE of the average (MWh) | RMSE change vs better % |
|---|---|---|---|---|---|---|---|---|---|
| SARIMAX | Tree-based | 0.56 | 1.10 | 0.81 | helps | helps | 39,181 | 36,466 | -6.9 |
| TabICL | TimesFM-3, covariates | 0.79 | 1.09 | 0.83 | helps | helps | 29,839 | 29,475 | -1.2 |
| TimesFM-3, covariates | SARIMAX | 0.73 | 1.20 | 0.64 | does not help | does not help | 32,539 | 33,375 | +2.6 |
| TimesFM-3, covariates | Tree-based | 0.57 | 1.33 | 0.47 | does not help | does not help | 32,539 | 33,645 | +3.4 |
| TabICL | SARIMAX | 0.70 | 1.31 | 0.49 | does not help | does not help | 29,839 | 31,747 | +6.4 |
| TabICL | Tree-based | 0.55 | 1.44 | 0.32 | does not help | does not help | 29,839 | 32,208 | +7.9 |

## Equal-weight averages

Sorted by RMSE. Gain = reduction compared with the best single model (lowest RMSE) inside the same combination (negative: the average is worse). No significance test.

| Average of | Models | RMSE (MWh) | RMSE gain vs best single % | MAE (MWh) | MAE gain vs best single % |
|---|---|---|---|---|---|
| **TabICL + TimesFM-3, covariates** | 2 | 29,475 | 1.2 | 22,422 | 2.1 |
| TabICL + TimesFM-3, covariates + Tree-based | 3 | 30,449 | -2.0 | 22,694 | 0.9 |
| TabICL + TimesFM-3, covariates + SARIMAX | 3 | 30,692 | -2.9 | 23,172 | -1.1 |
| TabICL + TimesFM-3, covariates + SARIMAX + Tree-based | 4 | 30,895 | -3.5 | 23,002 | -0.4 |
| TabICL + SARIMAX | 2 | 31,747 | -6.4 | 24,091 | -5.1 |
| TabICL + SARIMAX + Tree-based | 3 | 32,000 | -7.2 | 23,897 | -4.3 |
| TabICL + Tree-based | 2 | 32,208 | -7.9 | 24,163 | -5.5 |
| TimesFM-3, covariates + SARIMAX + Tree-based | 3 | 33,082 | -1.7 | 24,384 | -0.2 |
| TimesFM-3, covariates + SARIMAX | 2 | 33,375 | -2.6 | 24,949 | -2.5 |
| TimesFM-3, covariates + Tree-based | 2 | 33,645 | -3.4 | 24,795 | -1.9 |
| SARIMAX + Tree-based | 2 | 36,466 | 6.9 | 26,937 | 8.3 |
