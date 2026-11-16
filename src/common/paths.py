"""
Folder layout shared by every model and by the analysis.

    src/data/final/data_{hourly,daily}.csv     input data
    src/results/<model>/forecasts/*.csv        forecast files in the shared format (+ JSON sidecar)
    src/results/<model>/metrics/*.json         metrics of each forecast file (written by the evaluation)
    src/results/final_report/tables/           every table of the final report (CSV + Markdown)
    src/results/final_report/figures/          every figure of the final report

``<model>`` is one folder per model family, e.g. ``foundation``, ``sarimax``,
``tree-based``, ``seasonal_naive``. A new model only has to write its forecast
files to ``src/results/<its name>/forecasts`` to be picked up by the analysis.

Run every script as a module from the project root, e.g.
``uv run python -m src.analysis.run_report``.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # src/common/paths.py -> project root
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = SRC_DIR / "data" / "final"
RESULTS_DIR = SRC_DIR / "results"

REPORT_DIR = RESULTS_DIR / "final_report"
TABLES_DIR = REPORT_DIR / "tables"
FIGURES_DIR = REPORT_DIR / "figures"

NAIVE_MODEL = "seasonal_naive"  # results folder of the seasonal naive benchmark
NOT_MODELS = {REPORT_DIR.name}  # folders under results/ that are not models


def model_dir(model: str, results_dir: Path = RESULTS_DIR) -> Path:
    return Path(results_dir) / model


def forecast_dir(model: str, results_dir: Path = RESULTS_DIR) -> Path:
    return model_dir(model, results_dir) / "forecasts"


def metrics_dir(model: str, results_dir: Path = RESULTS_DIR) -> Path:
    return model_dir(model, results_dir) / "metrics"


def metrics_path_of(forecast_path: Path) -> Path:
    """``results/<model>/forecasts/x.csv`` -> ``results/<model>/metrics/x.json``."""
    forecast_path = Path(forecast_path)
    return forecast_path.parent.parent / "metrics" / f"{forecast_path.stem}.json"


def model_of(forecast_path: Path) -> str:
    """Model folder name of a forecast file (``results/<model>/forecasts/x.csv``)."""
    return Path(forecast_path).resolve().parent.parent.name