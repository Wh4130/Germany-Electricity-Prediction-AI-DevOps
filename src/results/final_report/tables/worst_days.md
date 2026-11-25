# The 10 worst forecast days per model

## Summary: what the 10 worst days have in common

Tags can overlap, so the shares need not add up to 100 %. Weekend alone does not count as an explanation.

| Model | Horizon | Share of yearly error from the 10 worst days % | Share of the year's days % | With a special-day tag % | With a weather tag % | With a price spike % | Without any explanation % |
|---|---|---|---|---|---|---|---|
| TabICL | daily 1 d | 9.6 | 2.7 | 60.0 | 50.0 | 0.0 | 30.0 |
| TabICL | daily 7 d | 9.4 | 2.7 | 50.0 | 80.0 | 0.0 | 20.0 |
| TimesFM-3, covariates | daily 1 d | 11.6 | 2.7 | 60.0 | 60.0 | 0.0 | 30.0 |
| TimesFM-3, covariates | daily 7 d | 9.0 | 2.7 | 60.0 | 70.0 | 0.0 | 30.0 |
| TimesFM-3, covariates | hourly 1 h | 5.4 | 2.7 | 80.0 | 50.0 | 0.0 | 10.0 |
| TimesFM-3, covariates | hourly 24 h | 11.4 | 2.7 | 80.0 | 70.0 | 0.0 | 20.0 |
| SARIMAX | daily 1 d | 13.2 | 2.7 | 100.0 | 70.0 | 0.0 | 0.0 |
| SARIMAX | daily 7 d | 7.9 | 2.7 | 80.0 | 80.0 | 0.0 | 10.0 |
| SARIMAX | hourly 1 h | 5.3 | 2.7 | 70.0 | 40.0 | 0.0 | 20.0 |
| SARIMAX | hourly 24 h | 9.9 | 2.7 | 80.0 | 70.0 | 0.0 | 10.0 |
| Tree-based | daily 1 d | 11.9 | 2.7 | 50.0 | 70.0 | 0.0 | 20.0 |
| Tree-based | daily 7 d | 8.6 | 2.7 | 50.0 | 70.0 | 0.0 | 20.0 |
| Tree-based | hourly 1 h | 4.8 | 2.7 | 40.0 | 50.0 | 0.0 | 30.0 |
| Tree-based | hourly 24 h | 6.3 | 2.7 | 30.0 | 30.0 | 0.0 | 70.0 |

## Days among the worst for several models

| Date | Models | Runs |
|---|---|---|
| 2024-03-31 | 14 | SARIMAX (daily 1 d); SARIMAX (daily 7 d); SARIMAX (hourly 1 h); SARIMAX (hourly 24 h); TabICL (daily 1 d); TabICL (daily 7 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d); TimesFM-3, covariates (hourly 1 h); TimesFM-3, covariates (hourly 24 h); Tree-based (daily 1 d); Tree-based (daily 7 d); Tree-based (hourly 1 h); Tree-based (hourly 24 h) |
| 2024-05-01 | 7 | TabICL (daily 1 d); TabICL (daily 7 d); TimesFM-3, covariates (hourly 1 h); TimesFM-3, covariates (hourly 24 h); Tree-based (daily 1 d); Tree-based (daily 7 d); Tree-based (hourly 1 h) |
| 2024-12-24 | 7 | SARIMAX (daily 1 d); SARIMAX (daily 7 d); SARIMAX (hourly 1 h); SARIMAX (hourly 24 h); TabICL (daily 7 d); Tree-based (daily 1 d); Tree-based (hourly 24 h) |
| 2024-12-29 | 7 | SARIMAX (daily 1 d); SARIMAX (daily 7 d); SARIMAX (hourly 24 h); TabICL (daily 7 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d); Tree-based (hourly 24 h) |
| 2024-01-01 | 6 | SARIMAX (daily 1 d); SARIMAX (daily 7 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d); Tree-based (daily 1 d); Tree-based (daily 7 d) |
| 2024-01-28 | 6 | TabICL (daily 1 d); TabICL (daily 7 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d); Tree-based (daily 1 d); Tree-based (daily 7 d) |
| 2024-11-16 | 5 | SARIMAX (daily 7 d); TabICL (daily 7 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d); Tree-based (hourly 24 h) |
| 2024-12-28 | 5 | SARIMAX (daily 7 d); SARIMAX (hourly 1 h); TabICL (daily 1 d); TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d) |
| 2024-12-31 | 5 | SARIMAX (daily 1 d); SARIMAX (hourly 1 h); SARIMAX (hourly 24 h); TimesFM-3, covariates (daily 1 d); Tree-based (hourly 1 h) |
| 2024-01-02 | 4 | SARIMAX (daily 1 d); SARIMAX (daily 7 d); SARIMAX (hourly 1 h); SARIMAX (hourly 24 h) |
| 2024-10-04 | 4 | TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d); TimesFM-3, covariates (hourly 24 h); Tree-based (daily 7 d) |
| 2024-01-24 | 3 | TabICL (daily 1 d); TabICL (daily 7 d); TimesFM-3, covariates (daily 7 d) |
| 2024-05-10 | 3 | TimesFM-3, covariates (hourly 1 h); TimesFM-3, covariates (hourly 24 h); Tree-based (daily 7 d) |
| 2024-07-29 | 3 | TimesFM-3, covariates (hourly 24 h); Tree-based (daily 7 d); Tree-based (hourly 24 h) |
| 2024-09-27 | 3 | TabICL (daily 1 d); TimesFM-3, covariates (hourly 1 h); Tree-based (hourly 1 h) |
| 2024-11-25 | 3 | SARIMAX (hourly 1 h); TimesFM-3, covariates (hourly 1 h); Tree-based (hourly 1 h) |
| 2024-12-23 | 3 | SARIMAX (daily 1 d); SARIMAX (hourly 24 h); TimesFM-3, covariates (hourly 24 h) |
| 2024-12-25 | 3 | SARIMAX (daily 1 d); SARIMAX (daily 7 d); SARIMAX (hourly 24 h) |
| 2024-12-26 | 3 | SARIMAX (daily 7 d); SARIMAX (hourly 24 h); TimesFM-3, covariates (hourly 24 h) |
| 2024-01-03 | 2 | SARIMAX (daily 1 d); TabICL (daily 1 d) |
| 2024-01-08 | 2 | Tree-based (daily 1 d); Tree-based (daily 7 d) |
| 2024-01-12 | 2 | Tree-based (daily 1 d); Tree-based (daily 7 d) |
| 2024-04-01 | 2 | TimesFM-3, covariates (hourly 1 h); TimesFM-3, covariates (hourly 24 h) |
| 2024-05-28 | 2 | TimesFM-3, covariates (daily 1 d); TimesFM-3, covariates (daily 7 d) |
| 2024-05-30 | 2 | SARIMAX (hourly 1 h); TimesFM-3, covariates (hourly 24 h) |
| 2024-10-03 | 2 | TimesFM-3, covariates (hourly 1 h); TimesFM-3, covariates (hourly 24 h) |
| 2024-10-27 | 2 | TabICL (daily 1 d); Tree-based (daily 1 d) |
| 2024-11-01 | 2 | SARIMAX (hourly 1 h); Tree-based (hourly 1 h) |
| 2024-12-27 | 2 | SARIMAX (hourly 1 h); TabICL (daily 1 d) |
| 2024-12-30 | 2 | SARIMAX (daily 1 d); SARIMAX (hourly 1 h) |

## TabICL (daily 1 d)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

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

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

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

## TimesFM-3, covariates (daily 1 d)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

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

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

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

## TimesFM-3, covariates (hourly 1 h)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-03-31 | Sun | 1,051 | 2.8 | 534 | 9,841 | -7.2 | 55 | Weekend, DST change, Much warmer than last week |
| 2 | 2024-04-01 | Mon | 880 | 2.1 | -153 | 11,563 | -4.7 | 36 | Holiday, Much warmer than last week |
| 3 | 2024-05-01 | Wed | 829 | 2.1 | 407 | 16,540 | -11.2 | 4 | Holiday, Much warmer than last week |
| 4 | 2024-11-25 | Mon | 795 | 1.3 | -139 | 1,983 | -7.3 | 55 | Much warmer than last week |
| 5 | 2024-05-10 | Fri | 757 | 1.7 | 600 | 7,908 | +0.4 | 76 | Bridge day |
| 6 | 2024-09-27 | Fri | 741 | 1.3 | -521 | 5,358 | +1.1 | 15 | none in our inputs |
| 7 | 2024-10-03 | Thu | 707 | 1.6 | 325 | 9,526 | +5.8 | 73 | Holiday, Much colder than last week |
| 8 | 2024-04-02 | Tue | 654 | 1.2 | -67 | 2,552 | -2.3 | 33 | Holiday week |
| 9 | 2024-03-29 | Fri | 640 | 1.4 | 83 | 10,281 | +0.2 | 38 | Holiday |
| 10 | 2024-03-28 | Thu | 634 | 1.1 | 88 | 1,237 | +1.6 | 51 | Holiday week |

## TimesFM-3, covariates (hourly 24 h)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

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

## SARIMAX (daily 1 d)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-12-25 | Wed | 177,948 | 16.4 | -177,948 | 313,738 | +4.5 | 99 | Holiday, Christmas / New Year, Much colder than last week |
| 2 | 2024-03-31 | Sun | 136,263 | 15.8 | 136,263 | 272,193 | -7.1 | 55 | Weekend, DST change, Much warmer than last week |
| 3 | 2024-01-01 | Mon | 111,672 | 10.9 | 111,672 | 38,117 | +3.7 | 16 | Holiday, Christmas / New Year, Much colder than last week |
| 4 | 2024-12-30 | Mon | 110,532 | 8.6 | 110,532 | 2,063 | +1.3 | 78 | Christmas / New Year |
| 5 | 2024-01-02 | Tue | 97,433 | 7.7 | 97,433 | 193,935 | +1.6 | 53 | Holiday week |
| 6 | 2024-12-29 | Sun | 93,687 | 7.9 | -93,687 | 8,889 | +4.8 | 105 | Christmas / New Year, Weekend, Much colder than last week |
| 7 | 2024-12-24 | Tue | 85,872 | 7.6 | 85,872 | 305,451 | +4.7 | 102 | Christmas / New Year, Much colder than last week |
| 8 | 2024-12-23 | Mon | 83,793 | 6.6 | 83,793 | 165,648 | +6.0 | 59 | Holiday week, Much colder than last week |
| 9 | 2024-12-31 | Tue | 74,877 | 6.2 | 74,877 | 73,336 | +1.6 | 62 | Christmas / New Year |
| 10 | 2024-01-03 | Wed | 74,771 | 5.5 | -74,771 | 196,988 | -3.7 | 45 | Holiday week, Much warmer than last week |

## SARIMAX (daily 7 d)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-12-29 | Sun | 193,698 | 16.4 | -193,698 | 8,889 | +4.8 | 105 | Christmas / New Year, Weekend, Much colder than last week |
| 2 | 2024-03-31 | Sun | 159,902 | 18.5 | 159,902 | 272,193 | -7.1 | 55 | Weekend, DST change, Much warmer than last week |
| 3 | 2024-01-02 | Tue | 138,780 | 10.9 | 138,780 | 193,935 | +1.6 | 53 | Holiday week |
| 4 | 2024-12-24 | Tue | 134,628 | 11.9 | 134,628 | 305,451 | +4.7 | 102 | Christmas / New Year, Much colder than last week |
| 5 | 2024-12-28 | Sat | 108,761 | 9.5 | -108,761 | 119,242 | +5.9 | 123 | Christmas / New Year, Weekend, Much colder than last week |
| 6 | 2024-01-01 | Mon | 101,262 | 9.9 | 101,262 | 38,117 | +3.7 | 16 | Holiday, Christmas / New Year, Much colder than last week |
| 7 | 2024-01-09 | Tue | 97,901 | 6.4 | -97,901 | 264,626 | +12.8 | 109 | Much colder than last week |
| 8 | 2024-12-26 | Thu | 88,130 | 8.2 | -88,130 | 309,926 | +4.8 | 113 | Holiday, Christmas / New Year, Much colder than last week |
| 9 | 2024-11-16 | Sat | 86,161 | 6.6 | -86,161 | 103,600 | -0.6 | 94 | Weekend, no other reason in our inputs |
| 10 | 2024-12-25 | Wed | 82,762 | 7.6 | -82,762 | 313,738 | +4.5 | 99 | Holiday, Christmas / New Year, Much colder than last week |

## SARIMAX (hourly 1 h)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-12-24 | Tue | 1,224 | 2.7 | 172 | 12,727 | +4.7 | 102 | Christmas / New Year, Much colder than last week |
| 2 | 2024-05-30 | Thu | 1,200 | 2.7 | -212 | 5,769 | +0.3 | 97 | none in our inputs |
| 3 | 2024-12-31 | Tue | 1,063 | 2.2 | 449 | 3,056 | +1.6 | 62 | Christmas / New Year |
| 4 | 2024-12-27 | Fri | 958 | 2.1 | -436 | 9,403 | +1.9 | 122 | Bridge day, Christmas / New Year |
| 5 | 2024-11-01 | Fri | 896 | 1.9 | -153 | 3,839 | +1.8 | 75 | none in our inputs |
| 6 | 2024-03-31 | Sun | 888 | 2.4 | 525 | 9,841 | -7.2 | 55 | Weekend, DST change, Much warmer than last week |
| 7 | 2024-01-02 | Tue | 872 | 2.0 | 677 | 8,142 | +1.6 | 53 | Holiday week |
| 8 | 2024-11-25 | Mon | 859 | 1.5 | -69 | 1,983 | -7.3 | 55 | Much warmer than last week |
| 9 | 2024-12-28 | Sat | 823 | 1.8 | -347 | 4,968 | +5.9 | 123 | Christmas / New Year, Weekend, Much colder than last week |
| 10 | 2024-12-30 | Mon | 799 | 1.6 | 188 | 999 | +1.3 | 78 | Christmas / New Year |

## SARIMAX (hourly 24 h)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-01-02 | Tue | 6,905 | 14.2 | 6,905 | 8,142 | +1.6 | 53 | Holiday week |
| 2 | 2024-12-25 | Wed | 6,163 | 13.7 | -6,163 | 13,072 | +4.5 | 99 | Holiday, Christmas / New Year, Much colder than last week |
| 3 | 2024-12-29 | Sun | 6,095 | 12.0 | -6,095 | 698 | +4.9 | 105 | Christmas / New Year, Weekend, Much colder than last week |
| 4 | 2024-12-31 | Tue | 5,664 | 11.1 | 5,651 | 3,056 | +1.6 | 62 | Christmas / New Year |
| 5 | 2024-05-31 | Fri | 4,434 | 9.4 | 4,434 | 2,074 | +0.4 | 89 | none in our inputs |
| 6 | 2024-12-24 | Tue | 4,254 | 8.9 | 2,745 | 12,727 | +4.7 | 102 | Christmas / New Year, Much colder than last week |
| 7 | 2024-01-06 | Sat | 3,819 | 7.3 | -3,819 | 5,998 | +5.0 | 89 | Weekend, Much colder than last week |
| 8 | 2024-12-23 | Mon | 3,790 | 6.8 | 3,661 | 6,902 | +6.0 | 59 | Holiday week, Much colder than last week |
| 9 | 2024-12-26 | Thu | 3,717 | 8.2 | -3,648 | 12,914 | +4.8 | 113 | Holiday, Christmas / New Year, Much colder than last week |
| 10 | 2024-03-31 | Sun | 3,696 | 9.9 | 3,649 | 9,841 | -7.2 | 55 | Weekend, DST change, Much warmer than last week |

## Tree-based (daily 1 d)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-01-08 | Mon | 137,798 | 9.2 | -137,798 | 479,638 | +10.3 | 102 | Much colder than last week |
| 2 | 2024-01-01 | Mon | 137,137 | 13.4 | 137,137 | 38,117 | +3.7 | 16 | Holiday, Christmas / New Year, Much colder than last week |
| 3 | 2024-01-12 | Fri | 118,262 | 7.7 | -118,262 | 171,114 | +4.6 | 106 | Much colder than last week |
| 4 | 2024-01-27 | Sat | 115,807 | 9.0 | 115,807 | 110,747 | -5.0 | 68 | Weekend, Much warmer than last week |
| 5 | 2024-12-24 | Tue | 104,762 | 9.3 | 104,762 | 305,451 | +4.7 | 102 | Christmas / New Year, Much colder than last week |
| 6 | 2024-03-31 | Sun | 103,220 | 11.9 | 103,220 | 272,193 | -7.1 | 55 | Weekend, DST change, Much warmer than last week |
| 7 | 2024-05-01 | Wed | 103,009 | 10.5 | 103,009 | 396,971 | -12.8 | 4 | Holiday, Much warmer than last week |
| 8 | 2024-11-11 | Mon | 96,379 | 6.7 | -96,379 | 94,834 | +1.2 | 122 | none in our inputs |
| 9 | 2024-01-28 | Sun | 91,723 | 8.1 | 91,723 | 179,582 | -2.5 | 59 | Weekend, no other reason in our inputs |
| 10 | 2024-10-27 | Sun | 87,247 | 8.0 | -87,247 | 44,196 | +1.5 | 90 | Weekend, DST change |

## Tree-based (daily 7 d)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-03-31 | Sun | 164,130 | 19.0 | 164,130 | 272,193 | -7.1 | 55 | Weekend, DST change, Much warmer than last week |
| 2 | 2024-05-10 | Fri | 143,767 | 13.1 | 143,767 | 189,797 | -0.4 | 76 | Bridge day |
| 3 | 2024-01-01 | Mon | 137,137 | 13.4 | 137,137 | 38,117 | +3.7 | 16 | Holiday, Christmas / New Year, Much colder than last week |
| 4 | 2024-10-04 | Fri | 108,736 | 9.4 | 108,736 | 180,520 | +4.6 | 96 | Bridge day, Much colder than last week |
| 5 | 2024-01-07 | Sun | 98,067 | 8.0 | -98,067 | 177,278 | +7.5 | 86 | Weekend, Much colder than last week |
| 6 | 2024-07-29 | Mon | 97,427 | 8.6 | 97,427 | 111,096 | +0.0 | 72 | none in our inputs |
| 7 | 2024-01-28 | Sun | 94,816 | 8.3 | 94,816 | 179,582 | -2.5 | 59 | Weekend, no other reason in our inputs |
| 8 | 2024-01-12 | Fri | 93,434 | 6.1 | -93,434 | 171,114 | +4.6 | 106 | Much colder than last week |
| 9 | 2024-01-08 | Mon | 89,608 | 6.0 | -89,608 | 479,638 | +10.3 | 102 | Much colder than last week |
| 10 | 2024-05-01 | Wed | 89,334 | 9.1 | 89,334 | 396,971 | -12.8 | 4 | Holiday, Much warmer than last week |

## Tree-based (hourly 1 h)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-03-31 | Sun | 999 | 2.7 | 713 | 9,841 | -7.2 | 55 | Weekend, DST change, Much warmer than last week |
| 2 | 2024-05-01 | Wed | 823 | 2.0 | 276 | 16,540 | -11.2 | 4 | Holiday, Much warmer than last week |
| 3 | 2024-12-31 | Tue | 789 | 1.6 | -270 | 3,056 | +1.6 | 62 | Christmas / New Year |
| 4 | 2024-01-29 | Mon | 699 | 1.2 | 438 | 5,862 | +1.8 | 81 | none in our inputs |
| 5 | 2024-11-25 | Mon | 686 | 1.1 | -16 | 1,983 | -7.3 | 55 | Much warmer than last week |
| 6 | 2024-05-15 | Wed | 678 | 1.2 | 6 | 1,749 | -4.5 | 43 | Much warmer than last week |
| 7 | 2024-09-27 | Fri | 647 | 1.2 | -328 | 5,358 | +1.1 | 15 | none in our inputs |
| 8 | 2024-09-22 | Sun | 645 | 1.7 | 462 | 3,165 | -3.0 | 76 | Weekend, Much warmer than last week |
| 9 | 2024-11-01 | Fri | 640 | 1.3 | -326 | 3,839 | +1.8 | 75 | none in our inputs |
| 10 | 2024-03-27 | Wed | 634 | 1.1 | -168 | 679 | -0.0 | 76 | Holiday week |

## Tree-based (hourly 24 h)

All forecast rows whose target falls on that day. Bias < 0 = under-forecast.

| Rank | Date | Weekday | MAE (MWh) | MAPE % | Bias (MWh) | Naive MAE (MWh) | HDD change vs last week | Mean price (EUR/MWh) | Likely reason |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-03-31 | Sun | 3,500 | 9.4 | 3,463 | 9,841 | -7.2 | 55 | Weekend, DST change, Much warmer than last week |
| 2 | 2024-12-09 | Mon | 2,915 | 4.4 | -2,905 | 2,555 | +0.8 | 100 | none in our inputs |
| 3 | 2024-12-29 | Sun | 2,753 | 5.5 | -2,741 | 698 | +4.9 | 105 | Christmas / New Year, Weekend, Much colder than last week |
| 4 | 2024-11-16 | Sat | 2,684 | 5.0 | -2,654 | 4,317 | -0.6 | 94 | Weekend, no other reason in our inputs |
| 5 | 2024-01-13 | Sat | 2,608 | 4.3 | -2,583 | 5,744 | +1.2 | 75 | Weekend, no other reason in our inputs |
| 6 | 2024-12-24 | Tue | 2,566 | 5.4 | 2,335 | 12,727 | +4.7 | 102 | Christmas / New Year, Much colder than last week |
| 7 | 2024-07-29 | Mon | 2,547 | 5.1 | 2,511 | 4,629 | +1.5 | 72 | none in our inputs |
| 8 | 2024-01-19 | Fri | 2,436 | 3.8 | -2,419 | 2,170 | +0.8 | 79 | none in our inputs |
| 9 | 2024-11-17 | Sun | 2,335 | 4.4 | -2,271 | 4,072 | -1.2 | 63 | Weekend, no other reason in our inputs |
| 10 | 2024-01-21 | Sun | 2,227 | 4.0 | -2,174 | 1,161 | +0.4 | 50 | Weekend, no other reason in our inputs |
