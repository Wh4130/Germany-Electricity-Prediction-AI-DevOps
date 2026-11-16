# Results Analysis Plan: Foundation Models for German Electricity Load Forecasting
 
Goal: show that the models work, where they work best, where they still fail and how we fix it, and what this is worth in business terms.
 
Storyline: it works, it beats the alternatives, we understand its weak spots, we tested fixes for them, and here is the value.
 
Evaluation basis: settings chosen on 2023 (validation), results reported on 2024 (test), compared with the seasonal naive benchmark (last week repeated).
 
Status (11 Nov 2026): original runs done, extra-features run done, weather and day-type analyses done, table, figure, worst-day and business-value scripts written. Open: significance test, running the scripts on the final results.
 
 
## 0. Executive Summary
 
Analysis:
- Summarise the main result in three or four sentences a manager can repeat.
- Write this section last.
Evidence to show:
- Hourly 24 h (TimesFM-3): MAE 1,045 MWh, 2.0 % error, 61 % less error than the benchmark, 80 % band correct 81.6 % of the time.
- Daily (TabICL with the extra features): 1.5 % error for the next day, 1.8 % for the next week, 60 to 68 % less error than the benchmark.
- No training needed; a new forecast setup takes minutes.
- The error analysis found systematic weaknesses, and a targeted fix cut the cold-snap under-forecast at 7 days by a quarter to a third.
- The estimated yearly value in euros from section 5.
- Figure 1: forecast vs actual for a typical 2024 week, with the 80 % band.
## 1. Data and Evaluation Setup
 
Analysis:
- Describe the data, the target, the two resolutions and the horizons, and why each horizon matters (day-ahead market, weekly planning).
- Explain how the evaluation is kept honest: choose on 2023, test once on 2024.
- Explain the benchmark and the metrics in plain words.
Evidence to show:
- Table of resolutions, horizons, number of forecast origins and inputs.
- Table of the settings compared on 2023 and the one chosen (context length, TabICL features).
- Short metric glossary:
  - MAE: average error in MWh, also given as % of load.
  - Skill: share of the benchmark's error that the model removes.
  - Coverage: how often the actual value lies inside the 80 % band.
  - Bias: forecast minus actual; positive = over-forecast, negative = under-forecast.
## 2. Model Comparison
 
Analysis:
- Which model is best for each horizon, and by how much.
- Strengths and weaknesses of each model.
- Which model we recommend for which use.
Evidence to show:
- Table 1: main results on 2024 for seasonal naive, TimesFM-3 without covariates, TimesFM-3 with covariates, TabICL, and TabICL with extra features, per horizon (MAE, MAPE, skill, pinball loss, coverage).
- Figure 2: skill per model and horizon.
- Our classical models (SARIMAX, tree models) on the same origins, if available.
- Statistical test (Diebold-Mariano): TabICL vs TimesFM-3 on daily data, and TabICL with vs without extra features (the gain is only about 2 %).
- Key facts:
  - Hourly: TimesFM-3 with covariates is best (MAE 1,045 MWh, 2.0 %).
  - Daily: TabICL is best, 6 to 8 % lower MAE than TimesFM-3 with covariates.
  - With the extra features, TabICL improves by about 2 % on both 2023 and 2024; TimesFM-3 does not improve (hourly unchanged, daily 0.5 to 2.3 % worse on both years).
- Table 2: strengths and weaknesses:
  - Seasonal naive: free and simple, but large errors and no uncertainty band.
  - TimesFM-3: best hourly, well-calibrated hourly bands, no training; weak on bridge days, does not benefit from extra engineered inputs and uses rare yes/no flags unreliably, weights are non-commercial.
  - TabICL: best daily, strong on all special days, benefits from targeted features; bands too narrow (75 to 79 %), tested on daily data only, licence to check.
Conclusion and business insight:
- All foundation models clearly beat the benchmark without any training.
- Recommended setup: TimesFM-3 with the original inputs for hourly operations, TabICL with the extra features for daily planning.
## 3. Day-Type Influence
 
Analysis:
- Which day types are forecast best and worst.
- How much the holiday covariates help, and on which days.
- What remains weak, what we tested, and what to do next.
Evidence to show:
- Table 3: MAE and coverage per day type (normal weekday, weekend, holiday, bridge day, Christmas), hourly without vs with covariates, and daily TimesFM-3 vs TabICL.
- Figure 3: MAE and coverage by day type, without vs with covariates.
- Key facts:
  - Holiday error falls by 62 % with covariates.
  - Holiday band coverage rises from 23 % to 77 %.
  - 64 % of the covariate gain comes from about 5 % of the hours (holidays and Christmas).
  - Bridge days get worse for hourly TimesFM-3 with covariates (coverage 46 %).
  - TabICL forecasts bridge days well (2.4 % vs 5.7 % error for TimesFM-3 daily).
  - With extra features, TabICL improves most on special days (1 d: holidays -10 %, bridge days -15 %).
  - After covariates, 89 % of the remaining error is on ordinary days.
- Holiday weeks (ordinary weekdays in a week with a holiday, or 18 to 23 December; 30 days in 2024):
  - TimesFM-3 daily over-forecasts them by 14,500 MWh per day.
  - The holiday-week flag we added made this worse for TimesFM-3 (over-forecast roughly doubles, MAE +28 to +38 %).
  - TabICL hardly had the problem (bias +900 MWh per day).
- Caveat: 2024 has only 9 holidays, 3 bridge days and 30 holiday-week days.
Business insight:
- Holiday errors repeat every year and always go in the same direction, so they are expensive to leave unfixed. Holiday covariates are essential.
- Bridge days and holiday weeks are known risks: flag them, widen the bands, or use TabICL's daily total there.
Future work:
- Reconciliation: daily total from TabICL, hourly shape from TimesFM-3.
- A narrower holiday-week definition (only the days next to a holiday, or school-holiday weeks), tested for TabICL only.
- Regional holidays.
## 4. Weather Influence
 
Analysis:
- Under which weather conditions the models do best and worst.
- In which direction the errors go (over- or under-forecast).
- Which fixes we tested and what they achieved.
### 4a. Weaknesses found
 
Evidence to show:
- Table 4: bias and MAE by temperature change vs last week (much warmer, similar, much colder).
- Table 5: bias at midday by radiation level within the month (dull, average, sunny).
- Figure 4: bias by temperature change, for all models.
- Figure 5: hour x month error heatmap (hourly, with covariates).
- Key facts:
  - All models under-forecast when it gets colder and over-forecast when it gets warmer, even with observed weather. They react in the right direction, but not enough.
  - Covariates capture about 55 % of the rooftop-PV effect at midday: sunny middays are over-forecast, dull middays under-forecast.
  - Error peaks at midday and is lowest at night.
  - Hot spots: December evenings, November afternoons, March and May.
  - Wind and rain have no effect of their own once the other inputs are used.
  - Summer has the weakest skill; there is no temperature input for heat.
### 4b. Targeted fixes tested
 
Evidence to show:
- Table 7: bias before and after, for each feature in the group it was designed for.
- Figure 6: before/after bias on "much colder" days, per model.
- Results:
  - Temperature change vs last week (hdd_delta_7d): works partly. Cold-snap under-forecast at 7 days falls by 33 % (TimesFM-3) and 24 % (TabICL); at 1 day by 20 % for TimesFM-3; no change hourly. Most of the under-reaction remains.
  - PV proxy (capacity x radiation): no effect on the midday bias. Dropped.
  - Holiday week: works against TimesFM-3, no clear gain for TabICL. Dropped for TimesFM-3; a narrower version may be retested.
  - TabICL's overall 2 % gain is spread over most weather groups and special days, so it cannot be attributed to one feature. We keep all three features for TabICL, because the gain holds on both years; a feature-by-feature test was not run.
Business insight:
- The cold-snap error is one-sided: a balancing group would be short when imbalance prices are high, so this error costs more than average. The temperature-change feature reduces this risk at the weekly horizon.
- Midday becomes the hardest hour as rooftop PV grows. Adding inputs did not help, so this needs a different method.
- For weather data, focus on radiation and temperature forecasts; wind and rain can be dropped.
Future work:
- Residual correction layer, fitted on 2023: regress the forecast errors on temperature change, radiation and hour of day, and apply the correction to 2024. Adding inputs has reached its limit for TimesFM-3.
- Add a temperature or cooling-degree input for summer.
- Wider uncertainty bands on days with large weather changes.
## 5. Business Value
 
Analysis:
- Translate the accuracy gains into money and operational benefits.
Evidence to show:
- Yearly error reduction in 2024 (national scale): 14.2 TWh less than the benchmark, 1.9 TWh from the covariates alone.
- Table 6: value sensitivity, for an imbalance cost of 5, 10 and 20 EUR/MWh and a market share of 1 %, 5 % and 10 % (hourly).
- Price-weighted MAE and bias in the 10 % most expensive hours: are we accurate, and not short, when power is expensive?
- Error valued at the day-ahead price, in EUR million, model vs benchmark.
- Qualitative benefits:
  - Reliable bands allow risk-based reserves instead of fixed margins.
  - No training pipeline, so low build and maintenance cost.
  - Fast to extend to new areas or updated data.
## 6. Limitations
 
Analysis:
- State the limits ourselves, so the results are trusted.
Evidence to show:
- Observed weather was used, so the results are an upper bound. Run with real weather forecasts (variant B) before the final report if possible.
- SMARD data is public and may be in the pretraining data; the 2025 test (F8) checks this.
- Small samples for holidays, bridge days and holiday weeks. The worst-days table shows which single days drive the averages.
- The extra features were designed after looking at 2024 errors. Mitigation: TabICL improves on 2023 as well, and two of three features were dropped because they did not work.
- The TabICL gain from the extra features is about 2 % and still needs a significance test. It is not known which of the three features causes it.
## 7. Recommendations and Roadmap
 
Analysis:
- Prioritised next steps, each with expected gain and effort.
Evidence to show:
1. Production setup: TimesFM-3 with the original inputs for hourly; TabICL with the extra features for daily.
2. Bridge-day and holiday-week reconciliation with TabICL's daily total (small effort, fixes the worst band problem).
3. Residual correction layer for the remaining temperature and PV bias (medium effort).
4. Recalibrate the uncertainty bands by day type and by size of the weather change.
5. Real weather forecasts (variant B) and the 2025 test before deployment.
## Scripts
 
Done:
- evaluate.py: overall, day-type and lead-time metrics.
- weather_breakdown.py: weather and holiday-week tables, hour x month heatmap data.
- run_extra_features.py: rerun with the engineered features into a separate results folder.
- report_tables.py: all report tables as CSV and one Markdown file.
- business_value.py: error volume, price-weighted accuracy, value sensitivity.
- worst_days.py: the 10 worst forecast days per model, with the likely reason.
- report_figures.py: the six figures, titles computed from the data.
To do:
- dm_test.py: Diebold-Mariano test.
- Optional: reconcile_daily_hourly.py, recalibrate_intervals.py.
## Figures and Tables Checklist
 
Figures:
1. Forecast vs actual week with 80 % band (section 0)
2. Skill per model and horizon (section 2)
3. MAE and coverage by day type, without vs with covariates (section 3)
4. Bias by temperature change (section 4a)
5. Hour x month error heatmap (section 4a)
6. Bias on "much colder" days before and after the temperature-change feature (section 4b)
Tables:
1. Main results on 2024 (section 2)
2. Strengths and weaknesses per model (section 2)
3. Results by day type (section 3)
4. Results by temperature change (section 4a)
5. Midday results by radiation (section 4a)
6. Value sensitivity (section 5)
7. Targeted fixes: bias before and after, per feature (section 4b)
Rule for every figure: the title states the message, for example "Holiday covariates cut holiday error by 62 %", not "MAE by day type".