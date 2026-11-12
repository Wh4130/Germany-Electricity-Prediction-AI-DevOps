# The 10 worst forecast days per model

## Summary: what the 10 worst days have in common

Tags can overlap, so the shares need not add up to 100 %. Weekend alone does not count as an explanation.

| Model | Horizon | Share of yearly error from the 10 worst days % | Share of the year's days % | With a special-day tag % | With a weather tag % | With a price spike % | Without any explanation % |
|---|---|---|---|---|---|---|---|
| TimesFM-3, covariates | daily 1 d | 11.6 | 2.7 | 60.0 | 60.0 | 0.0 | 30.0 |
| TimesFM-3, covariates | daily 7 d | 9.0 | 2.7 | 60.0 | 70.0 | 0.0 | 30.0 |
| TimesFM-3, covariates | hourly 24 h | 11.4 | 2.7 | 80.0 | 70.0 | 0.0 | 20.0 |
| TimesFM-3, no covariates | daily 1 d | 20.2 | 2.7 | 90.0 | 60.0 | 0.0 | 10.0 |
| TimesFM-3, no covariates | daily 7 d | 16.3 | 2.7 | 90.0 | 60.0 | 0.0 | 10.0 |
| TimesFM-3, no covariates | hourly 24 h | 16.4 | 2.7 | 90.0 | 70.0 | 0.0 | 10.0 |
| TabICL | daily 1 d | 9.6 | 2.7 | 60.0 | 50.0 | 0.0 | 30.0 |
| TabICL | daily 7 d | 9.4 | 2.7 | 50.0 | 80.0 | 0.0 | 20.0 |

## Days among the worst for several models

| Date | Models | Runs |
|---|---|---|
| 2024-03-31 | 8 | TabICL (daily 1 d); TabICL (daily 7 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d); TimesFM-3, covariates (hourly 24 h); TimesFM-3, no covariates (daily 1 d); TimesFM-3, no covariates (daily 7 d); TimesFM-3, no covariates (hourly 24 h) |
| 2024-05-01 | 6 | TabICL (daily 1 d); TabICL (daily 7 d); TimesFM-3, covariates (hourly 24 h); TimesFM-3, no covariates (daily 1 d); TimesFM-3, no covariates (daily 7 d); TimesFM-3, no covariates (hourly 24 h) |
| 2024-01-01 | 4 | TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d); TimesFM-3, no covariates (daily 1 d); TimesFM-3, no covariates (daily 7 d) |
| 2024-01-28 | 4 | TabICL (daily 1 d); TabICL (daily 7 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d) |
| 2024-04-01 | 4 | TimesFM-3, covariates (hourly 24 h); TimesFM-3, no covariates (daily 1 d); TimesFM-3, no covariates (daily 7 d); TimesFM-3, no covariates (hourly 24 h) |
| 2024-05-30 | 4 | TimesFM-3, covariates (hourly 24 h); TimesFM-3, no covariates (daily 1 d); TimesFM-3, no covariates (daily 7 d); TimesFM-3, no covariates (hourly 24 h) |
| 2024-10-03 | 4 | TimesFM-3, covariates (hourly 24 h); TimesFM-3, no covariates (daily 1 d); TimesFM-3, no covariates (daily 7 d); TimesFM-3, no covariates (hourly 24 h) |
| 2024-01-24 | 3 | TabICL (daily 1 d); TabICL (daily 7 d); TimesFM-3, covariates (daily 7 d) |
| 2024-03-29 | 3 | TimesFM-3, no covariates (daily 1 d); TimesFM-3, no covariates (daily 7 d); TimesFM-3, no covariates (hourly 24 h) |
| 2024-05-09 | 3 | TimesFM-3, no covariates (daily 1 d); TimesFM-3, no covariates (daily 7 d); TimesFM-3, no covariates (hourly 24 h) |
| 2024-05-20 | 3 | TimesFM-3, no covariates (daily 1 d); TimesFM-3, no covariates (daily 7 d); TimesFM-3, no covariates (hourly 24 h) |
| 2024-10-04 | 3 | TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d); TimesFM-3, covariates (hourly 24 h) |
| 2024-11-16 | 3 | TabICL (daily 7 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d) |
| 2024-12-28 | 3 | TabICL (daily 1 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d) |
| 2024-12-29 | 3 | TabICL (daily 7 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d) |
| 2024-05-10 | 2 | TimesFM-3, covariates (hourly 24 h); TimesFM-3, no covariates (daily 7 d) |
| 2024-05-28 | 2 | TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d) |
| 2024-12-26 | 2 | TimesFM-3, covariates (hourly 24 h); TimesFM-3, no covariates (hourly 24 h) |

## TimesFM-3, covariates (daily 1 d)

Hourly runs: the 24 hours of the day. Daily 7 d runs: the forecasts of that day from all lead days. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-03-31 | Sun | 151,135 | 17.5 | 151,135 | 272,193 | -7.1 | 55 | Weekend, DST change, Much warmer than last week |
| 2 | 2024-10-04 | Fri | 90,907 | 7.9 | 90,907 | 180,520 | +4.6 | 96 | Bridge day, Much colder than last week |
| 3 | 2024-01-01 | Mon | 89,537 | 8.8 | 89,537 | 38,117 | +3.7 | 16 | Holiday, Christmas / New Year, Much colder than last week |
| 4 | 2024-12-31 | Tue | 87,576 | 7.3 | 87,576 | 73,336 | +1.6 | 62 | Christmas / New Year |
| 5 | 2024-12-28 | Sat | 85,948 | 7.5 | -85,948 | 119,242 | +5.9 | 123 | Christmas / New Year, Weekend, Much colder than last week |
| 6 | 2024-12-29 | Sun | 80,681 | 6.8 | -80,681 | 8,889 | +4.8 | 105 | Christmas / New Year, Weekend, Much colder than last week |
| 7 | 2024-12-21 | Sat | 77,572 | 6.1 | -77,572 | 54,951 | -4.4 | 22 | Weekend, Much warmer than last week |
| 8 | 2024-05-28 | Tue | 71,462 | 5.9 | 71,462 | 52,790 | +2.9 | 91 | none in our inputs |
| 9 | 2024-11-16 | Sat | 70,706 | 5.4 | -70,706 | 103,600 | -0.6 | 94 | Weekend, no other reason in our inputs |
| 10 | 2024-01-28 | Sun | 70,300 | 6.2 | 70,300 | 179,582 | -2.5 | 59 | Weekend, no other reason in our inputs |

## TimesFM-3, covariates (daily 7 d)

Hourly runs: the 24 hours of the day. Daily 7 d runs: the forecasts of that day from all lead days. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-12-29 | Sun | 138,114 | 11.7 | -138,114 | 8,889 | +4.8 | 105 | Christmas / New Year, Weekend, Much colder than last week |
| 2 | 2024-03-31 | Sun | 120,423 | 13.9 | 120,423 | 272,193 | -7.1 | 55 | Weekend, DST change, Much warmer than last week |
| 3 | 2024-01-28 | Sun | 99,472 | 8.7 | 99,472 | 179,582 | -2.5 | 59 | Weekend, no other reason in our inputs |
| 4 | 2024-10-04 | Fri | 97,683 | 8.4 | 97,683 | 180,520 | +4.6 | 96 | Bridge day, Much colder than last week |
| 5 | 2024-01-24 | Wed | 96,818 | 6.4 | 96,818 | 89,990 | -10.7 | 33 | Much warmer than last week |
| 6 | 2024-12-28 | Sat | 96,368 | 8.4 | -96,368 | 119,242 | +5.9 | 123 | Christmas / New Year, Weekend, Much colder than last week |
| 7 | 2024-11-16 | Sat | 88,442 | 6.8 | -88,442 | 103,600 | -0.6 | 94 | Weekend, no other reason in our inputs |
| 8 | 2024-12-19 | Thu | 81,807 | 5.9 | 81,807 | 79,099 | -7.4 | 52 | Holiday week, Much warmer than last week |
| 9 | 2024-05-28 | Tue | 80,428 | 6.7 | 80,428 | 52,790 | +2.9 | 91 | none in our inputs |
| 10 | 2024-01-01 | Mon | 79,917 | 7.8 | 79,917 | 38,117 | +3.7 | 16 | Holiday, Christmas / New Year, Much colder than last week |

## TimesFM-3, covariates (hourly 24 h)

Hourly runs: the 24 hours of the day. Daily 7 d runs: the forecasts of that day from all lead days. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-05-30 | Thu | 6,226 | 13.2 | 6,226 | 5,769 | +0.3 | 97 | none in our inputs |
| 2 | 2024-03-31 | Sun | 5,878 | 15.6 | 5,878 | 9,841 | -7.2 | 55 | Weekend, DST change, Much warmer than last week |
| 3 | 2024-04-01 | Mon | 5,695 | 13.1 | -5,372 | 11,462 | -4.7 | 36 | Holiday, Much warmer than last week |
| 4 | 2024-10-03 | Thu | 4,616 | 9.9 | 4,571 | 9,526 | +5.8 | 73 | Holiday, Much colder than last week |
| 5 | 2024-05-01 | Wed | 4,598 | 11.4 | 4,598 | 16,540 | -11.2 | 4 | Holiday, Much warmer than last week |
| 6 | 2024-05-10 | Fri | 4,488 | 9.4 | 4,488 | 7,908 | +0.4 | 76 | Bridge day |
| 7 | 2024-10-04 | Fri | 3,202 | 6.3 | 3,200 | 7,522 | +4.7 | 96 | Bridge day, Much colder than last week |
| 8 | 2024-12-23 | Mon | 3,122 | 5.8 | 2,424 | 6,902 | +6.0 | 59 | Holiday week, Much colder than last week |
| 9 | 2024-07-29 | Mon | 2,937 | 6.1 | 2,937 | 4,629 | +1.5 | 72 | none in our inputs |
| 10 | 2024-12-26 | Thu | 2,929 | 6.4 | 2,929 | 12,914 | +4.8 | 113 | Holiday, Christmas / New Year, Much colder than last week |

## TimesFM-3, no covariates (daily 1 d)

Hourly runs: the 24 hours of the day. Daily 7 d runs: the forecasts of that day from all lead days. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-05-01 | Wed | 309,136 | 31.6 | 309,136 | 396,971 | -12.8 | 4 | Holiday, Much warmer than last week |
| 2 | 2024-05-20 | Mon | 273,788 | 28.4 | 273,788 | 295,639 | +1.2 | 65 | Holiday |
| 3 | 2024-05-09 | Thu | 267,879 | 26.3 | 267,879 | 231,526 | +5.0 | 62 | Holiday, Much colder than last week |
| 4 | 2024-10-03 | Thu | 229,004 | 20.9 | 229,004 | 225,698 | +6.0 | 73 | Holiday, Much colder than last week |
| 5 | 2024-01-01 | Mon | 201,932 | 19.8 | 201,932 | 38,117 | +3.7 | 16 | Holiday, Christmas / New Year, Much colder than last week |
| 6 | 2024-03-29 | Fri | 195,897 | 17.5 | 195,897 | 246,754 | +0.2 | 38 | Holiday |
| 7 | 2024-04-01 | Mon | 175,987 | 16.9 | 175,987 | 281,394 | -4.7 | 36 | Holiday, Much warmer than last week |
| 8 | 2024-03-31 | Sun | 165,755 | 19.2 | 165,755 | 272,193 | -7.1 | 55 | Weekend, DST change, Much warmer than last week |
| 9 | 2024-05-30 | Thu | 160,714 | 14.6 | 160,714 | 138,461 | +0.7 | 97 | none in our inputs |
| 10 | 2024-01-02 | Tue | 151,385 | 11.9 | -151,385 | 193,935 | +1.6 | 53 | Holiday week |

## TimesFM-3, no covariates (daily 7 d)

Hourly runs: the 24 hours of the day. Daily 7 d runs: the forecasts of that day from all lead days. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-05-01 | Wed | 330,578 | 33.8 | 330,578 | 396,971 | -12.8 | 4 | Holiday, Much warmer than last week |
| 2 | 2024-05-20 | Mon | 278,828 | 28.9 | 278,828 | 295,639 | +1.2 | 65 | Holiday |
| 3 | 2024-05-09 | Thu | 276,326 | 27.2 | 276,326 | 231,526 | +5.0 | 62 | Holiday, Much colder than last week |
| 4 | 2024-04-01 | Mon | 234,586 | 22.5 | 234,586 | 281,394 | -4.7 | 36 | Holiday, Much warmer than last week |
| 5 | 2024-10-03 | Thu | 230,660 | 21.1 | 230,660 | 225,698 | +6.0 | 73 | Holiday, Much colder than last week |
| 6 | 2024-01-01 | Mon | 201,932 | 19.8 | 201,932 | 38,117 | +3.7 | 16 | Holiday, Christmas / New Year, Much colder than last week |
| 7 | 2024-03-31 | Sun | 169,518 | 19.6 | 169,518 | 272,193 | -7.1 | 55 | Weekend, DST change, Much warmer than last week |
| 8 | 2024-03-29 | Fri | 168,338 | 15.0 | 168,338 | 246,754 | +0.2 | 38 | Holiday |
| 9 | 2024-05-10 | Fri | 161,415 | 14.7 | 161,415 | 189,797 | -0.4 | 76 | Bridge day |
| 10 | 2024-05-30 | Thu | 145,922 | 13.3 | 145,922 | 138,461 | +0.7 | 97 | none in our inputs |

## TimesFM-3, no covariates (hourly 24 h)

Hourly runs: the 24 hours of the day. Daily 7 d runs: the forecasts of that day from all lead days. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-05-09 | Thu | 10,799 | 25.2 | 10,799 | 10,173 | +3.7 | 62 | Holiday, Much colder than last week |
| 2 | 2024-05-01 | Wed | 9,264 | 22.8 | 9,264 | 16,540 | -11.2 | 4 | Holiday, Much warmer than last week |
| 3 | 2024-10-03 | Thu | 8,122 | 17.5 | 8,121 | 9,526 | +5.8 | 73 | Holiday, Much colder than last week |
| 4 | 2024-03-29 | Fri | 7,761 | 16.4 | 7,761 | 10,281 | +0.2 | 38 | Holiday |
| 5 | 2024-12-25 | Wed | 7,702 | 16.4 | 7,638 | 13,072 | +4.5 | 99 | Holiday, Christmas / New Year, Much colder than last week |
| 6 | 2024-12-26 | Thu | 6,833 | 14.8 | 6,833 | 12,914 | +4.8 | 113 | Holiday, Christmas / New Year, Much colder than last week |
| 7 | 2024-05-20 | Mon | 6,795 | 16.5 | 6,795 | 12,318 | +0.4 | 65 | Holiday |
| 8 | 2024-03-31 | Sun | 6,715 | 17.8 | 6,715 | 9,841 | -7.2 | 55 | Weekend, DST change, Much warmer than last week |
| 9 | 2024-05-30 | Thu | 6,354 | 13.5 | 6,354 | 5,769 | +0.3 | 97 | none in our inputs |
| 10 | 2024-04-01 | Mon | 5,497 | 12.7 | 3,972 | 11,462 | -4.7 | 36 | Holiday, Much warmer than last week |

## TabICL (daily 1 d)

Hourly runs: the 24 hours of the day. Daily 7 d runs: the forecasts of that day from all lead days. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-03-31 | Sun | 104,859 | 12.1 | 104,859 | 272,193 | -7.1 | 55 | Weekend, DST change, Much warmer than last week |
| 2 | 2024-01-03 | Wed | 71,898 | 5.3 | -71,898 | 196,988 | -3.7 | 45 | Holiday week, Much warmer than last week |
| 3 | 2024-12-28 | Sat | 68,981 | 6.0 | -68,981 | 119,242 | +5.9 | 123 | Christmas / New Year, Weekend, Much colder than last week |
| 4 | 2024-09-27 | Fri | 67,991 | 5.1 | -67,991 | 128,592 | +2.2 | 15 | none in our inputs |
| 5 | 2024-05-01 | Wed | 65,788 | 6.7 | 65,788 | 396,971 | -12.8 | 4 | Holiday, Much warmer than last week |
| 6 | 2024-05-11 | Sat | 60,007 | 5.9 | 60,007 | 62,519 | -1.4 | 54 | Weekend, no other reason in our inputs |
| 7 | 2024-01-28 | Sun | 59,558 | 5.2 | 59,558 | 179,582 | -2.5 | 59 | Weekend, no other reason in our inputs |
| 8 | 2024-01-24 | Wed | 58,015 | 3.9 | 58,015 | 89,990 | -10.7 | 33 | Much warmer than last week |
| 9 | 2024-12-27 | Fri | 57,703 | 5.0 | -57,703 | 225,668 | +1.9 | 122 | Bridge day, Christmas / New Year |
| 10 | 2024-10-27 | Sun | 57,657 | 5.3 | -57,657 | 44,196 | +1.5 | 90 | Weekend, DST change |

## TabICL (daily 7 d)

Hourly runs: the 24 hours of the day. Daily 7 d runs: the forecasts of that day from all lead days. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-03-31 | Sun | 115,220 | 13.3 | 115,220 | 272,193 | -7.1 | 55 | Weekend, DST change, Much warmer than last week |
| 2 | 2024-01-28 | Sun | 91,592 | 8.0 | 91,592 | 179,582 | -2.5 | 59 | Weekend, no other reason in our inputs |
| 3 | 2024-01-25 | Thu | 87,171 | 5.9 | 87,171 | 95,024 | -7.8 | 78 | Much warmer than last week |
| 4 | 2024-12-29 | Sun | 84,117 | 7.1 | -84,117 | 8,889 | +4.8 | 105 | Christmas / New Year, Weekend, Much colder than last week |
| 5 | 2024-05-01 | Wed | 79,929 | 8.2 | 79,929 | 396,971 | -12.8 | 4 | Holiday, Much warmer than last week |
| 6 | 2024-01-26 | Fri | 75,447 | 5.2 | 75,447 | 135,522 | -8.5 | 59 | Much warmer than last week |
| 7 | 2024-11-16 | Sat | 74,871 | 5.7 | -74,871 | 103,600 | -0.6 | 94 | Weekend, no other reason in our inputs |
| 8 | 2024-01-24 | Wed | 74,825 | 5.0 | 74,825 | 89,990 | -10.7 | 33 | Much warmer than last week |
| 9 | 2024-05-02 | Thu | 73,574 | 5.9 | 73,574 | 111,116 | -12.7 | 36 | Holiday week, Much warmer than last week |
| 10 | 2024-12-24 | Tue | 67,925 | 6.0 | 67,925 | 305,451 | +4.7 | 102 | Christmas / New Year, Much colder than last week |
