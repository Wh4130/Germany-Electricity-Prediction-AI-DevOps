# Best model by group of days

## MAE by group of days, daily 1 d, test year

Groups of days of the test year; MAE of the one-day forecast in MWh; cov. = with covariates. 'Best' is the model with the lowest MAE; small groups (few days) rest on little data, and differences of a few hundred MWh are not meaningful.

| Feature | Group | Days | SARIMAX | Tree-based | TabICL | TimesFM-3 cov. | Best |
|---|---|---|---|---|---|---|---|
| Day type | Normal weekday | 247 | 20,080 | 23,555 | 18,855 | 18,689 | TimesFM-3 cov. |
| Day type | Weekend | 102 | 19,249 | 25,263 | 17,234 | 20,428 | TabICL |
| Day type | Holiday | 9 | 55,684 | 49,216 | 26,699 | 34,613 | TabICL |
| Day type | Bridge day | 3 | 22,157 | 54,459 | 28,069 | 64,909 | SARIMAX |
| Day type | Christmas / New Year | 9 | 81,205 | 49,772 | 43,897 | 69,133 | TabICL |
| Heating degree days | 0 (no heating) | 75 | 18,284 | 20,816 | 16,594 | 18,429 | TabICL |
| Heating degree days | mild | 94 | 18,880 | 19,581 | 17,514 | 18,040 | TabICL |
| Heating degree days | cool | 92 | 21,078 | 24,055 | 20,841 | 18,994 | TimesFM-3 cov. |
| Heating degree days | cold | 88 | 20,886 | 31,593 | 18,261 | 21,300 | TabICL |
| Change vs. last week | no heating either week | 56 | 18,027 | 21,093 | 16,244 | 17,308 | TabICL |
| Change vs. last week | much warmer | 60 | 22,008 | 26,528 | 23,629 | 22,469 | SARIMAX |
| Change vs. last week | similar | 180 | 18,655 | 21,825 | 17,080 | 18,220 | TabICL |
| Change vs. last week | much colder | 53 | 23,306 | 31,956 | 19,120 | 20,807 | TabICL |
