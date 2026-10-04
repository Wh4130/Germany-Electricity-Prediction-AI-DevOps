# AI Deployment

Exploring and analysing German electricity consumption data from SMARD.

- Source: SMARD (Bundesnetzagentur), "Realisierter Stromverbrauch" (actual consumption)
- Period: 2019-01-01 to 2025-01-01
- Files: daily (`_Tag.csv`) and hourly (`_Stunde.csv`) data in `src/data/raw/`
- Official docs: [`smard-user-guide-09-2021-data.pdf`](./smard-user-guide-09-2021-data.pdf), section 2.1 ~ 2.3.

## Column reference

CSV format: separator `;`, decimal `,`, thousands `.`, dates as `dd.mm.yyyy`.

| Original column name | English column name | Type | Unit | Description |
|---|---|---|---|---|
| Datum von | `date_from` | datetime | | Start of the interval |
| Datum bis | `date_to` | datetime | | End of the interval |
| Netzlast [MWh] Berechnete Auflösungen | `actual_consumption` | float | MWh | Total load incl. network losses, excl. stored energy (hydro pumped storage) |
| Netzlast inkl. Pumpspeicher [MWh] Berechnete Auflösungen | `actual_consumption_incl_pumped` | float | MWh | `actual_consumption` + `hydro_pumped_storage` |
| Pumpspeicher [MWh] Berechnete Auflösungen | `hydro_pumped_storage` | float | MWh | Consumption of hydro pumped storage (subcategory of actual consumption) |
| Residuallast [MWh] Berechnete Auflösungen | `residual_load` | float | MWh | `actual_consumption` minus feed-in from photovoltaic, onshore wind and offshore wind |

Notes:
- `actual_consumption + hydro_pumped_storage = actual_consumption_incl_pumped` was checked on both the daily and hourly data and holds for every row.
- SMARD values get revised after the fact (MaBiS corrections arrive from roughly the 42nd working day), so the same period can differ slightly between downloads.
- The region (e.g. Germany/Luxembourg) isn't in the file, so note the export settings somewhere.
- `Berechnete Auflösungen` is a label added by the export. The official docs don't explain it, so treat it as a label only.

Derived columns (added by us):

| Column | Description |
|---|---|
| `day_of_week_raw` | Weekday number, 0 = Monday ... 6 = Sunday |
| `day_of_week` | Weekday name |
| `month` | Month number |
| `is_holiday` | German nationwide public holiday (`holidays.Germany()`), weekends don't count |

## EDA ideas (rough draft)

Just a loose plan, we'll adjust as we go:

1. **Overall trend**: plot daily consumption with a rolling average. Is it going up or down over the years? Do 2020 (covid) and 2022 (energy crisis) show up?
2. **Day-of-week effect**: how big is the weekday vs weekend gap? Do public holidays look like weekends? When comparing, use "holidays on a weekday" vs "normal weekdays", otherwise weekends water down the result.
3. **Seasonality**: monthly and seasonal averages, a year x month heatmap. Is winter really higher?
4. **Daily pattern** (hourly data): average 24h curve for weekdays vs weekends and summer vs winter. Watch out for the daylight saving days (23 and 25 hours).
5. **Residual load**: look at `residual_load / actual_consumption` as a rough renewable share. Does it change year by year? Is there a midday dip from solar (the "duck curve")?
6. **Pumped storage**: when does it pump, and does that follow residual load? Is the share big enough to matter for modelling?
7. **Correlation and autocorrelation**: relationships between columns, plus how today relates to yesterday and last week (useful for forecasting later). Careful: `actual_consumption_incl_pumped` is just the sum of two other columns, so it's perfectly collinear.

If we move on to forecasting later: split train/test in time order, not randomly.
