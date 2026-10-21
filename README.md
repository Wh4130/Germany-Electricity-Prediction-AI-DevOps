# AI Deployment

Exploring and analysing German electricity consumption data from SMARD.

- Target: SMARD (Bundesnetzagentur) "Realisierter Stromverbrauch" (actual consumption), `actual_consumption`
- Period: 2019-01-01 to 2025-01-01
- Resolution: daily (`_Tag.csv`) and hourly (`_Stunde.csv`)
- Official docs: [`smard-user-guide-09-2021-data.pdf`](./smard-user-guide-09-2021-data.pdf), section 2.1 ~ 2.3.

## Navigator

- [Sources](#sources)
- [Project structure](#project-structure)
- [Components](#components)
- [Documentation](#documentation)
- [How to run](#how-to-run)
  - [Feature engineering pipeline](#feature-engineering-pipeline)
  - [Model pipeline](#model-pipeline)

## Sources

Every data source we download from, with its API or URL. Details per source (script, output, licence): [FEATURE_ENGINEERING](docs/FEATURE_ENGINEERING.md#scripts-downloads).

- SMARD download center, manual download (consumption, realised generation): https://www.smard.de/home/downloadcenter/download-marktdaten
- SMARD chart data, day-ahead price DE-LU (JSON, not a documented API): https://www.smard.de/app/chart_data/4169/DE-LU/index_hour.json
- ferien-api.de, school holidays of the 16 states: https://ferien-api.de/api/v1/holidays
- DBnomics, Destatis population by state (12411LJ003): https://api.db.nomics.world/v22/series/DESTATIS/12411LJ003
- DBnomics, IMF European natural gas price (PCPS): https://api.db.nomics.world/v22/series/IMF/PCPS/M.W00.PNGASEU.USD
- Open-Meteo, historical weather archive: https://archive-api.open-meteo.com/v1/archive
- Marktstammdatenregister (MaStR), solar units, via the `open-mastr` package: https://www.marktstammdatenregister.de and https://github.com/OpenEnergyPlatform/open-MaStR
- OxCGRT, COVID-19 policy tracker (national file): https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/OxCGRT_compact_national_v1.csv
- Destatis GENESIS-Online, production index (table 42153-0001), manual download: https://www-genesis.destatis.de/

## Project structure

```
.
├── README.md
├── docs/                       # detailed documentation
│   ├── FEATURES.md
│   ├── FEATURE_ENGINEERING.md
│   ├── EDA.md
│   ├── MODELS.md
│   ├── models/                 # one document per model
│   └── meeting/                # meeting decisions and notes
├── smard-user-guide-09-2021-data.pdf
├── pyproject.toml, uv.lock     # dependencies (uv)
└── src/
    ├── data/                   # raw → intermin → features → final
    ├── scripts/                # download scripts (ETL)
    ├── feature_engineering/    # cleansing, feature pipelines, merge, main.py
    ├── models/                 # SARIMAX, tree based, foundation model
    │   ├── sarimax/
    │   ├── trees/
    │   └── foundation/
    ├── notebooks/              # data quality check, EDA
    └── test/                   # tests of the pipelines
```

## Components

| Component | Purpose |
|---|---|
| `src/data/` | All data. `raw/` is the untouched download, `intermin/` the cleaned data and lookup tables, `features/` one folder per feature group, `final/` everything merged for modelling |
| `src/scripts/` | One-off scripts that download the data that does not come from the SMARD download center and save it in `intermin/` |
| `src/feature_engineering/` | The feature engineering pipeline: cleansing of the raw data, one pipeline per feature group, `merge_all.py` and `main.py` that runs the whole flow |
| `src/models/` | The three models (SARIMAX, tree based, foundation model). Not implemented yet |
| `src/notebooks/` | Data quality check and EDA. They only read the data |
| `src/test/` | Tests of the pipelines |
| `docs/` | Detailed documentation, see below |

## Documentation

| Document | Content |
|---|---|
| [docs/FEATURES.md](docs/FEATURES.md) | All features in one table (name, description, datatype, source, producing file) and details per feature group |
| [docs/FEATURE_ENGINEERING.md](docs/FEATURE_ENGINEERING.md) | Data folders, download scripts, manual downloads, every pipeline, how to add a feature pipeline |
| [docs/EDA.md](docs/EDA.md) | Data quality check and exploratory analysis (preliminary) |
| [docs/MODELS.md](docs/MODELS.md) | Overview of the three models, shared setup, comparison (placeholder) |
| [docs/models/](docs/models/SARIMAX.md) | One document per model: [SARIMAX](docs/models/SARIMAX.md), [TREES](docs/models/TREES.md), [FOUNDATION](docs/models/FOUNDATION.md) (preprocessing, normalization, training; placeholders) |
| [docs/meeting/](docs/meeting/README.md) | Decisions and notes of each meeting |

## How to run

All commands run from the project root. The project uses [uv](https://docs.astral.sh/uv/).

### Feature engineering pipeline

Builds `src/data/final/data_daily.csv` and `data_hourly.csv` from the raw SMARD files.

1. Put the SMARD files in `src/data/raw/` (manual download, see [FEATURE_ENGINEERING](docs/FEATURE_ENGINEERING.md#manual-downloads)).
2. Run the whole flow (downloads, cleansing, feature pipelines, merge):

   ```
   uv run python src/feature_engineering/main.py                   # whole data flow
   uv run python src/feature_engineering/main.py --forceDownload   # download the lookup files again
   ```

   Downloads are skipped when their file already exists, a failed step stops the run.

3. Each step is a normal script and can be run alone, use `--help` for its options:

   ```
   uv run python src/feature_engineering/<name>.py
   ```

The policy features (OxCGRT, production index) need files in `src/data/external_raw/` and are not part of `main.py`. Their outputs are in git, `main.py` only merges them. How to rebuild them: [FEATURE_ENGINEERING](docs/FEATURE_ENGINEERING.md#feature-engineering-pipelines).

Tests: `uv run pytest src/test`

### Model pipeline

> Not implemented yet. See [MODELS](docs/MODELS.md).
