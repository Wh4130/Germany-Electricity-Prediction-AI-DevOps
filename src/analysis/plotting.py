"""
Shared figure style of the report (reference palette of the dataviz guidance, light mode).

Colours follow the model and are the same in every figure: the known models
have a fixed slot of the categorical order, any other model takes the next
free slot (in display order); a model's variant (``"<model> + ..."``) keeps the
model's colour and is drawn hatched. Values are labelled on the bars, so
colour never carries meaning alone.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from src.analysis.runs import sort_labels  # noqa: E402

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8985", "#e4e3df"
# Categorical order: blue, orange, aqua, yellow, magenta, green, violet, red.
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
FIXED_COLOR = {
    "TimesFM-3, covariates": CATEGORICAL[0],
    "TabICL": CATEGORICAL[1],
    "TimesFM-3, no covariates": CATEGORICAL[2],
    "SARIMAX": CATEGORICAL[3],
    "Tree-based": CATEGORICAL[4],
}
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
RED_RAMP = ["#fbe0df", "#f3a9a8", "#e34948", "#b02a2a"]  # red arm of the blue <-> red diverging pair
NEUTRAL = "#f0efec"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 9.5, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": GRID, "axes.titlesize": 10, "axes.titlecolor": INK, "axes.titleweight": "bold",
    "legend.frameon": False, "legend.fontsize": 9,
})


def base_model(label: str) -> str:
    return label.split(" + ")[0]


def is_variant(label: str) -> bool:
    return " + " in label


class Colors:
    """Model label -> colour, fixed for the whole report (call once with every label)."""

    def __init__(self, labels):
        self.map = dict(FIXED_COLOR)
        free = [c for c in CATEGORICAL if c not in self.map.values()]
        for lab in sort_labels(base_model(x) for x in labels):
            if lab not in self.map:
                self.map[lab] = free.pop(0) if free else MUTED  # beyond 8 models: muted, labels carry identity

    def __call__(self, label: str) -> str:
        return self.map.get(base_model(label), MUTED)


def hatch_of(label: str) -> str | None:
    return "////" if is_variant(label) else None


def tidy(ax, grid_axis: str = "y"):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def headline(fig, title: str, subtitle: str):
    fig.text(0.01, 0.985, title, ha="left", va="top", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.01, 0.935, subtitle, ha="left", va="top", fontsize=9.5, color=INK2)


def save(fig, out_dir: Path, name: str, formats: list[str]) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in formats:
        path = out_dir / f"{name}.{ext}"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        paths.append(path)
    plt.close(fig)
    print(f"[figures] {name} -> {', '.join(p.name for p in paths)}")
    return paths


def bar_labels(ax, bars, fmt: str, horizontal: bool = False):
    """Value at the end of each bar, in text ink (never the series colour)."""
    for b in bars:
        v = b.get_width() if horizontal else b.get_height()
        if np.isnan(v):
            continue
        if horizontal:
            ax.annotate(format(v, fmt), (v, b.get_y() + b.get_height() / 2), xytext=(4 if v >= 0 else -4, 0),
                        textcoords="offset points", va="center", ha="left" if v >= 0 else "right",
                        fontsize=8.5, color=INK)
        else:
            off = 3 if v >= 0 else -3
            ax.annotate(format(v, fmt), (b.get_x() + b.get_width() / 2, v), xytext=(0, off),
                        textcoords="offset points", ha="center", va="bottom" if v >= 0 else "top",
                        fontsize=8, color=INK)


def grouped_bars(ax, groups: list[str], series: list[str], values: dict, colors: Colors, width: float = 0.8,
                 fmt: str = ".0f", alpha_of=None):
    """Vertical grouped bars: values[(group, series)] -> number."""
    n = max(len(series), 1)
    w = width / n
    x = np.arange(len(groups))
    for i, s in enumerate(series):
        vals = [values.get((g, s), np.nan) for g in groups]
        bars = ax.bar(x - width / 2 + w * (i + 0.5), vals, w * 0.88, color=colors(s), hatch=hatch_of(s),
                      edgecolor=SURFACE, linewidth=0.8, alpha=alpha_of(s) if alpha_of else 1.0, label=s)
        if n <= 4:  # selective labels: with many series the values are in the tables
            bar_labels(ax, bars, fmt)
    ax.set_xticks(x, groups)
    return x