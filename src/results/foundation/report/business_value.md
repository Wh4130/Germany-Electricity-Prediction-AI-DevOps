# Business value

## Yearly forecast error volume

National scale, all days of the year. Daily 7 d: average lead day.

Yearly forecast error volume: MAE x number of target steps in the year, in TWh, for the model and the seasonal naive; the reduction against the naive, and against a reference run of the same resolution and horizon. For daily 7 d runs this is the error of an average lead day.

| Model | Horizon | MAE (MWh) | Yearly error (TWh) | Naive yearly error (TWh) | Reduction vs naive (TWh) | Reference | Reduction vs reference (TWh) |
|---|---|---|---|---|---|---|---|
| TimesFM-3, covariates | hourly 24 h | 1,045 | 9.18 | 23.34 | 14.16 | TimesFM-3, no covariates | 1.89 |
| TimesFM-3, no covariates | hourly 24 h | 1,260 | 11.07 | 23.34 | 12.27 |  |  |
| TabICL | daily 1 d | 19,091 | 6.99 | 21.12 | 14.14 | TimesFM-3, no covariates | 3.55 |
| TimesFM-3, covariates | daily 1 d | 20,691 | 7.57 | 21.12 | 13.55 | TimesFM-3, no covariates | 2.97 |
| TimesFM-3, no covariates | daily 1 d | 28,796 | 10.54 | 21.12 | 10.59 |  |  |
| TabICL | daily 7 d | 22,911 | 8.38 | 20.80 | 12.42 | TimesFM-3, no covariates | 4.26 |
| TimesFM-3, covariates | daily 7 d | 24,331 | 8.90 | 20.80 | 11.90 | TimesFM-3, no covariates | 3.74 |
| TimesFM-3, no covariates | daily 7 d | 34,562 | 12.65 | 20.80 | 8.15 |  |  |

Insights:
- The models remove 8–14 TWh of yearly forecast error compared with the naive benchmark. The best hourly model leaves 9.2 TWh, about 2 % of German annual consumption, against 23.3 TWh for naive.

## Accuracy where power is expensive

Bias < 0 = under-forecast. Error at day-ahead price = sum of |error| x |price|, national scale.

Price-weighted view, with the day-ahead price of the target time
   (hourly: the hourly price, daily: the mean price of the day):
   - price-weighted MAE (weights |price|); a ratio above 1 means the errors
     are larger in the expensive hours,
   - MAE and bias in the most expensive 10 % of the steps
     (bias < 0 = under-forecast, i.e. short when power is expensive),
   - the error valued at the day-ahead price (sum of |error| x |price|),
     a simple proxy of what the error costs, in EUR million.

| Model | Horizon | MAE (MWh) | Price-weighted MAE (MWh) | Price-weighted / plain MAE | MAE top-10 % price (MWh) | Bias top-10 % price (MWh) | Error at day-ahead price (EUR m) | Naive error at day-ahead price (EUR m) | Value reduction vs reference (EUR m) |
|---|---|---|---|---|---|---|---|---|---|
| TimesFM-3, covariates | hourly 24 h | 1,045 | 1,029 | 0.99 | 1,104 | 186 | 720.5 | 1,848.1 | 130.7 |
| TimesFM-3, no covariates | hourly 24 h | 1,260 | 1,216 | 0.96 | 1,240 | 36 | 851.2 | 1,848.1 |  |
| TabICL | daily 1 d | 19,091 | 19,030 | 1.00 | 22,345 | -6,904 | 546.8 | 1,664.0 | 221.5 |
| TimesFM-3, covariates | daily 1 d | 20,691 | 20,763 | 1.00 | 25,015 | -12,509 | 596.6 | 1,664.0 | 171.6 |
| TimesFM-3, no covariates | daily 1 d | 28,796 | 26,737 | 0.93 | 25,823 | -6,357 | 768.2 | 1,664.0 |  |
| TabICL | daily 7 d | 22,911 | 22,999 | 1.00 | 28,223 | -10,649 | 661.9 | 1,641.3 | 291.7 |
| TimesFM-3, covariates | daily 7 d | 24,331 | 24,716 | 1.02 | 29,740 | -12,145 | 711.3 | 1,641.3 | 242.3 |
| TimesFM-3, no covariates | daily 7 d | 34,562 | 33,135 | 0.96 | 34,802 | -7,336 | 953.6 | 1,641.3 |  |

Insights:
- Price-weighted MAE ≈ plain MAE (ratio 0.93–1.02). On average, errors are neither concentrated in nor avoided in expensive hours. The models are price-neutral.
- Expensive periods are harder, especially at daily resolution. In the 10 % most expensive days, MAE is 17 % higher for TabICL and 21 % higher for TimesFM-3 with covariates. In expensive hours, hourly MAE is only 6 % higher.
- The daily models under-forecast on expensive days. At 1 day ahead the bias is −6.9k MWh for TabICL and −12.5k for TimesFM-3 with covariates; at 7 days it is −10.6k / −12.1k. A supplier using these forecasts would be short exactly when buying is most expensive. TabICL has about half TimesFM-3’s bias at 1 day, which counts in its favor.
- The hourly model leans slightly the other way (+186 MWh/h in expensive hours). Being long is usually the cheaper mistake, so this is less of a concern.
- Error at the day-ahead price:
    - The hourly model’s mis-forecast energy is valued at €720 m, against €1,848 m for naive.
    - Covariates account for €131 m of that difference.
    - For the daily models, TabICL is €50 m below TimesFM-3 with covariates at both horizons.
    - This is not a cost. It values each mis-forecast MWh at the full price (about 78 €/MWh on average). In reality only the imbalance spread is paid, and Table 6 uses that.

## Table 6. Yearly value of the hourly forecast (EUR million)

Error reduction x imbalance cost (what each missed MWh costs) x market share (how large the portfolio is). Upper bound: observed weather inputs.

Value sensitivity (hourly runs only): the yearly error
   reduction x imbalance cost per MWh x market share.
   This assumes a portfolio's error scales with its share of national load.

| Model | Against | Market share % | 5 EUR/MWh (EUR m) | 10 EUR/MWh (EUR m) | 20 EUR/MWh (EUR m) |
|---|---|---|---|---|---|
| TimesFM-3, covariates | vs seasonal naive | 1.0 | 0.7 | 1.4 | 2.8 |
| TimesFM-3, covariates | vs seasonal naive | 5.0 | 3.5 | 7.1 | 14.2 |
| TimesFM-3, covariates | vs seasonal naive | 10.0 | 7.1 | 14.2 | 28.3 |
| TimesFM-3, covariates | vs TimesFM-3, no covariates | 1.0 | 0.1 | 0.2 | 0.4 |
| TimesFM-3, covariates | vs TimesFM-3, no covariates | 5.0 | 0.5 | 0.9 | 1.9 |
| TimesFM-3, covariates | vs TimesFM-3, no covariates | 10.0 | 0.9 | 1.9 | 3.8 |
| TimesFM-3, no covariates | vs seasonal naive | 1.0 | 0.6 | 1.2 | 2.5 |
| TimesFM-3, no covariates | vs seasonal naive | 5.0 | 3.1 | 6.1 | 12.3 |
| TimesFM-3, no covariates | vs seasonal naive | 10.0 | 6.1 | 12.3 | 24.5 |

# Overall
The accuracy gains are large in volume (about 14 TWh against naive) and worth single-digit millions of euros a year for a mid-sized supplier. The most important commercial finding is the under-forecasting on expensive days, because that is the error that costs most. TabICL has the smaller bias there, and a temperature-change correction would target it directly.