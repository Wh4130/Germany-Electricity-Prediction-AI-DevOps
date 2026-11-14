# Model API contract

Every model that the dashboard shows runs as its own HTTP service with the same endpoints, so the dashboard
calls all of them the same way. The prototype covers the **daily 1-day forecasts of 2024** only.

The reference implementation is the SARIMAX service in `deploy/sarimax_api/`.

## Conventions

- Dates are local dates, `YYYY-MM-DD`; the forecast range is 2024-01-01 to 2024-12-31.
- Loads are in MWh (`actual_consumption` of `data_daily.csv`).
- A forecast for day d uses the actual load up to d − 1 and the X of day d, as in the shared evaluation.
  Past-only X (the monthly indicators) use their value of d − 1.
- Quantiles are named as in the shared forecast files: `q0.1` … `q0.9`. The dashboard draws `q0.1` to
  `q0.9` (80% interval). A model without quantiles returns only `y_pred`.
- The service must allow browser calls from the dashboard (CORS).

## Endpoints

### `GET /health`

`{"status": "ok"}`. Used by the cloud to check that the service is up.

### `GET /meta`

The model and the X it lets the dashboard change.

```json
{
  "model": "SARIMAX",
  "resolution": "daily",
  "horizon": 1,
  "first_date": "2024-01-01",
  "last_date": "2024-12-31",
  "sliders": {"hdd": {"label": "Heating degree days", "unit": "°C·d"}, "...": {}},
  "calendar": ["is_holiday", "..."]
}
```

### `GET /forecast?start=&end=`

The forecasts with the actual X, one row per day (both parameters optional).

```json
[{"date": "2024-01-01", "y_true": 1180000.0, "y_pred": 1203000.0, "q0.1": 1170000.0, "...": 0, "q0.9": 1236000.0}]
```

### `GET /features?date=2024-03-15`

The X of the day: the slider values (the X that the forecast of that day uses) and their ranges, and the
calendar X, which follow from the date and cannot be changed.

```json
{
  "date": "2024-03-15",
  "y_true": 1382702.75,
  "sliders": {
    "hdd": {"label": "Heating degree days", "unit": "°C·d", "value": 6.44, "min": 0.0, "max": 18.86,
            "step": 0.12, "past_only": false}
  },
  "calendar": {"is_holiday": 0.0, "month": 3, "day_of_week": "Friday"}
}
```

Slider range: the value of the day ± 2 standard deviations of 2019–2023, cut at physical bounds
(e.g. precipitation ≥ 0). A slider can have an optional `note` (shown under its label), e.g. for `hdd`:
"≈ 18 °C − mean temperature (0 above 18 °C)".

### `POST /predict`

The forecast of the day with changed X; X that are left out keep the value of `/features`.

Request:

```json
{"date": "2024-03-15", "x": {"hdd": 10.0, "day_ahead_price_mean": 120.0}}
```

Response:

```json
{"date": "2024-03-15", "y_pred": 1401000.0, "y_pred_baseline": 1385000.0, "y_true": 1382702.75,
 "x": {"hdd": 10.0, "...": 0}, "q0.1": 1368000.0, "...": 0, "q0.9": 1434000.0}
```

Errors: 404 for a date without a forecast, 422 for an X that cannot be changed (e.g. a calendar X).

## Slider X (prototype)

| X | Meaning | Unit |
|---|---|---|
| `hdd` | heating degree days | °C·d |
| `wind_speed_10m_mean` | wind speed at 10 m, daily mean | km/h |
| `precipitation_sum` | precipitation | mm |
| `solar_generation_proxy` | solar capacity × shortwave radiation | MW·MJ/m² |
| `day_ahead_price_mean` | day-ahead price, daily mean | EUR/MWh |
| `industrial_confidence` | industrial confidence (past-only) | balance |
| `ipi_ei_level` | industrial production index (past-only) | index |
| `oxcgrt_stringency` | COVID stringency (past-only) | 0–100 |

A model that does not use one of these X returns it in `/features` with its value and ignores changes to it.

## Dashboard config

`deploy/dashboard/public/config.json` lists the models; it is read at runtime, so changing it needs no rebuild.

```json
{
  "models": [
    { "id": "sarimax", "label": "SARIMAX", "url": "http://localhost:8000" },
    { "id": "tree", "label": "Tree", "url": "http://localhost:8001" },
    { "id": "foundation", "label": "TimesFM", "forecastCsv": "forecasts/timesfm_daily_1d_test.csv" }
  ],
  "featureSource": "sarimax"
}
```

- `url`: a live model with this API (what-if forecasts).
- `forecastCsv`: a static model, no API and no what-if. The file is in the shared forecast format; only its
  step-1 rows are drawn. Put it in `deploy/dashboard/public/` (the path is relative to the page).
- `featureSource`: the live model whose `/features` fills the sliders.
- Colors are fixed per `id`: `sarimax` blue, `tree` orange, `hybrid` aqua, `foundation` yellow.
- The 80% interval is drawn only when one model is shown; the models can be hidden in the chart.

## SARIMAX notes

- The model is the test fit of `run_sarimax.py` (2019–2023), filtered over 2019–2024 with the saved parameters,
  not estimated again. `/forecast` equals `src/results/sarimax/forecasts/sarimax_daily_1d_test.csv`.
- The X enter as a regression (y = Xβ + SARIMA errors), so a what-if forecast moves linearly with the X:
  `y_pred − y_pred_baseline = (X new − X used) @ β`. The interval width does not change.
- Run locally:

```bash
uv run --with-requirements deploy/sarimax_api/requirements.txt \
    uvicorn app:app --app-dir deploy/sarimax_api --port 8000
# http://localhost:8000/docs
```

- Tests: `uv run --with-requirements deploy/sarimax_api/requirements.txt --with httpx --with pytest pytest deploy/sarimax_api`
- Image: `deploy/sarimax_api/stage.sh`, then `docker build -t sarimax-api deploy/sarimax_api`.
