"""
MSTL decomposition of the actual consumption (training period).

daily:  periods 7 and 365 (weekly and yearly seasonal), as in the notebook.
hourly: periods 24 and 168 (daily and weekly seasonal). No yearly period, so the
        annual wave stays in the trend. The UTC timestamp is the index because
        local time repeats an hour when the clocks go back.

Outputs (results/eda/figures):
    mstl_decomposition_<granularity>.png   observed, trend and the seasonal components
    mstl_residual_<granularity>.png        residual with +-3 sigma lines

    uv run python src/analysis/eda/plot_mstl_decomposition.py --granularity daily
    uv run python src/analysis/eda/plot_mstl_decomposition.py --granularity hourly
"""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import MSTL

from eda_common import BLUE, FIG_HEIGHT, FIG_WIDTH, VERMILION, apply_style, load_train, save_figure

CONFIG = {
    "daily": dict(time_col="date_from", freq="D", periods=(7, 365), unit="million MWh/day", scale=1e6,
                  names={7: "Weekly seasonal", 365: "Yearly seasonal"}),
    "hourly": dict(time_col="date_from_utc", freq="h", periods=(24, 168), unit="thousand MWh/h", scale=1e3,
                   names={24: "Daily seasonal", 168: "Weekly seasonal"}),
}


def main(granularity: str) -> None:
    apply_style()
    cfg = CONFIG[granularity]
    df = load_train(granularity)
    s = df.set_index(cfg["time_col"])["actual_consumption"].asfreq(cfg["freq"])
    res = MSTL(s, periods=cfg["periods"]).fit()

    panels = [("Observed", res.observed), ("Trend", res.trend)]
    for p in cfg["periods"]:
        panels.append((cfg["names"][p], res.seasonal[f"seasonal_{p}"]))

    fig, axes = plt.subplots(len(panels), 1, figsize=(FIG_WIDTH, 1.3 * len(panels) + 0.6), sharex=True)
    for ax, (title, series) in zip(axes, panels):
        ax.plot(series.index, series / cfg["scale"], color=BLUE, lw=0.5)
        ax.set_ylabel(title, fontsize=8)
    axes[-1].set_xlabel("Year")
    fig.supylabel(f"Consumption ({cfg['unit']})", fontsize=8)
    fig.tight_layout()
    save_figure(fig, f"mstl_decomposition_{granularity}")

    resid = res.resid / cfg["scale"]
    sd = resid.std()
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    ax.plot(resid.index, resid, color=BLUE, lw=0.5)
    for sign in (-3, 3):
        ax.axhline(sign * sd, color=VERMILION, lw=0.8, ls="--")
    ax.set_xlabel("Year")
    ax.set_ylabel(f"Residual ({cfg['unit']})")
    save_figure(fig, f"mstl_residual_{granularity}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--granularity", choices=["daily", "hourly"], default="daily")
    main(parser.parse_args().granularity)
