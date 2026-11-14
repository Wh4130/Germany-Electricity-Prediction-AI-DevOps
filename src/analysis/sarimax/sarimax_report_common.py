"""
Shared helpers for the SARIMAX figures and tables of the report.

Inputs are the files that src/models/sarimax/run_sarimax.py wrote to src/results/sarimax/ (nothing is refitted,
except that the standard errors of the final model are computed at its saved parameters).

Outputs (upload both folders to the LaTeX project):

    src/results/sarimax/report/figures/*.png
    src/results/sarimax/report/tables/*.tex, *.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ANALYSIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ANALYSIS_DIR.parent / "eda"))  # eda_common: style, colours, figure size
sys.path.insert(0, str(ANALYSIS_DIR.parents[1] / "models" / "sarimax"))  # common, features

from eda_common import (  # noqa: E402,F401
    BLACK,
    BLUE,
    FIG_WIDTH,
    ORANGE,
    VERMILION,
    apply_style,
)

SRC_DIR = ANALYSIS_DIR.parent.parent
PROJECT_ROOT = SRC_DIR.parent
DATA_DIR = SRC_DIR / "data" / "final"
SARIMAX_DIR = SRC_DIR / "results" / "sarimax"
FIGURES_DIR = SARIMAX_DIR / "report" / "figures"
TABLES_DIR = SARIMAX_DIR / "report" / "tables"


def load_daily_y() -> pd.Series:
    """Daily actual consumption (MWh), 2019-2024, indexed by the local date."""
    data = pd.read_csv(DATA_DIR / "data_daily.csv", index_col=0, parse_dates=["date_from"])
    return pd.Series(data["actual_consumption"].to_numpy(), index=pd.to_datetime(data["date_from"]).to_numpy()).asfreq("D")


def seasonal_naive(y: pd.Series, target_dates) -> pd.Series:
    """Same weekday one week before. Known at the origin for every step of a horizon of up to 7 days."""
    target_dates = pd.DatetimeIndex(target_dates)
    return pd.Series(y.shift(7).reindex(target_dates).to_numpy(), index=target_dates)


def load_hourly_y() -> pd.Series:
    """Hourly actual consumption (MWh), 2019-2024, on the continuous UTC index (as in the forecast files)."""
    data = pd.read_csv(DATA_DIR / "data_hourly.csv", index_col=0, parse_dates=["date_from_utc"])
    return pd.Series(data["actual_consumption"].to_numpy(), index=pd.to_datetime(data["date_from_utc"]).dt.tz_localize(None)
                     .to_numpy()).asfreq("h")


def seasonal_naive_hourly(y: pd.Series, target_times) -> pd.Series:
    """Same hour one week (168 hours) before. Known at the origin for every step of a 24-hour horizon."""
    target_times = pd.DatetimeIndex(target_times)
    return pd.Series(y.shift(168).reindex(target_times).to_numpy(), index=target_times)


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))


def mape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true)
    return float(np.mean(np.abs((y_true - np.asarray(y_pred)) / y_true)) * 100)


def save_figure(fig, name: str) -> Path:
    import matplotlib.pyplot as plt

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {path.relative_to(PROJECT_ROOT)}")
    return path


def save_tabular(name: str, header: list[str], rows: list[list[str]], align: str, df: pd.DataFrame | None = None) -> None:
    """Write a booktabs tabular (cells are LaTeX, already escaped by the caller) and optionally a CSV."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    lines = [r"\begin{tabular}{" + align + "}", r"\toprule", " & ".join(header) + r" \\", r"\midrule"]
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES_DIR / f"{name}.tex").write_text("\n".join(lines) + "\n")
    if df is not None:
        df.to_csv(TABLES_DIR / f"{name}.csv", index=False)
    print(f"saved {(TABLES_DIR / name).relative_to(PROJECT_ROOT)}.tex")
