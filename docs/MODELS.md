# Models

[README](../README.md) · [FEATURES](FEATURES.md) · [FEATURE_ENGINEERING](FEATURE_ENGINEERING.md) · [EDA](EDA.md) · **MODELS**

## Navigator

- [Overview](#overview)
- [Shared setup](#shared-setup)
- [Comparison](#comparison)

## Overview

> Placeholder. The models are not implemented yet.

Target: `actual_consumption` (daily and hourly). Input: `src/data/final/data_daily.csv` and `data_hourly.csv` (see [FEATURE_ENGINEERING](FEATURE_ENGINEERING.md)), with the columns described in [FEATURES](FEATURES.md).

Each model has its own document (preprocessing, normalization, training and evaluation), so they can be edited without conflicts.

| Model | Document | Code | Status |
|---|---|---|---|
| SARIMAX | [models/SARIMAX.md](models/SARIMAX.md) | [src/models/sarimax/](../src/models/sarimax/) | placeholder |
| Tree based | [models/TREES.md](models/TREES.md) | [src/models/trees/](../src/models/trees/) | placeholder |
| Foundation model | [models/FOUNDATION.md](models/FOUNDATION.md) | [src/models/foundation/](../src/models/foundation/) | placeholder |

## Shared setup

> TBD. To be filled in once decided:
> - which columns are model inputs (see the `leakage` and `forecast` marks in [FEATURES](FEATURES.md#how-to-read-the-table))
> - train / validation / test split
> - forecast horizon
> - metrics

## Comparison

> TBD. Results of the three models on the same split and metrics.
