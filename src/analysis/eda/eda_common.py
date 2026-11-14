"""
Shared helpers for the EDA figure and table scripts.

Everything here uses the training period only (before CUTOFF), as the EDA
notebook does. Figures have a fixed size so they all scale the same way when
included in LaTeX with \\includegraphics[width=\\textwidth]{...}.

Outputs (upload the whole folder to the LaTeX project):

    src/results/eda/figures/*.png
    src/results/eda/tables/*.csv, *.tex
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SRC_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = SRC_DIR / "data" / "final"
FIGURES_DIR = SRC_DIR / "results" / "eda" / "figures"
TABLES_DIR = SRC_DIR / "results" / "eda" / "tables"

CUTOFF = "2024-01-01"

FIG_WIDTH = 6.3  # inches, about the text width of an A4 page
FIG_HEIGHT = 3.2
FIG_HEIGHT_TALL = 6.0

# Okabe-Ito palette (colour-blind safe), same colours as the notebook.
BLUE, ORANGE, SKY, GREEN, VERMILION, PINK, BLACK = (
    "#0072B2",
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#D55E00",
    "#CC79A7",
    "#000000",
)
YEAR_COLORS = [BLACK, ORANGE, SKY, GREEN, VERMILION, PINK]
SEASON_COLORS = [BLUE, GREEN, ORANGE, VERMILION]

DAY_TYPE_ORDER = ["Weekday", "Weekday holiday", "Weekend", "Weekend holiday"]
DAY_TYPE_COLORS = [BLUE, VERMILION, GREEN, ORANGE]
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SEASON_MAP = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn",
}
SEASON_ORDER = ["Winter", "Spring", "Summer", "Autumn"]


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 100,
            "savefig.dpi": 300,
            "font.size": 9,
            "axes.titlesize": 9,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#e4e3df",
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
        }
    )


def load_train(granularity: str) -> pd.DataFrame:
    """Training rows (before CUTOFF) of the daily or hourly final dataset, sorted by time."""
    if granularity not in ("daily", "hourly"):
        raise ValueError("granularity must be 'daily' or 'hourly'")
    df = pd.read_csv(
        DATA_DIR / f"data_{granularity}.csv",
        index_col=0,
        parse_dates=["date_from", "date_to", "date_from_utc"],
    )
    train = df[df["date_from"] < CUTOFF].sort_values("date_from").copy()
    return train


def add_day_type(df: pd.DataFrame) -> pd.DataFrame:
    """Four day types: holidays are their own group, split into weekday and weekend."""
    weekend = df["day_of_week_raw"] >= 5
    holiday = df["is_holiday"].astype(bool)
    label = np.select(
        [holiday & weekend, holiday & ~weekend, weekend],
        ["Weekend holiday", "Weekday holiday", "Weekend"],
        default="Weekday",
    )
    out = df.copy()
    out["day_type"] = pd.Categorical(label, categories=DAY_TYPE_ORDER, ordered=True)
    return out


def legend_below(fig_or_ax, handles=None, labels=None, ncol: int = 4):
    """Horizontal legend under the plot, as in the notebook."""
    kwargs = dict(loc="upper center", ncol=ncol, frameon=False)
    if hasattr(fig_or_ax, "legend"):
        if handles is None:
            return fig_or_ax.legend(bbox_to_anchor=(0.5, -0.15), **kwargs)
        return fig_or_ax.legend(handles, labels, bbox_to_anchor=(0.5, -0.15), **kwargs)
    raise TypeError("expected a Figure or Axes")


def save_figure(fig, name: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {path.relative_to(SRC_DIR.parent)}")
    return path


def save_table(df: pd.DataFrame, name: str, index: bool = False, float_format: str = "%.3f") -> None:
    """Write a table as CSV and as a booktabs LaTeX tabular (no extra dependency)."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES_DIR / f"{name}.csv", index=index, float_format=float_format)

    frame = df.reset_index() if index else df
    cols = list(frame.columns)

    def cell(v) -> str:
        if isinstance(v, (float, np.floating)):
            return "" if pd.isna(v) else float_format % v
        return str(v).replace("_", r"\_").replace("%", r"\%")

    lines = [r"\begin{tabular}{" + "l" + "r" * (len(cols) - 1) + "}", r"\toprule"]
    lines.append(" & ".join(str(c).replace("_", r"\_") for c in cols) + r" \\")
    lines.append(r"\midrule")
    for row in frame.itertuples(index=False):
        lines.append(" & ".join(cell(v) for v in row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES_DIR / f"{name}.tex").write_text("\n".join(lines) + "\n")
    print(f"saved {(TABLES_DIR / name).relative_to(SRC_DIR.parent)}.csv/.tex")
