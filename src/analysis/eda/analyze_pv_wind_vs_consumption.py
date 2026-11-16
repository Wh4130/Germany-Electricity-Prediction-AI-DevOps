"""
PV + wind versus consumption (daily, training period).

residual_load = actual_consumption - (PV + onshore wind + offshore wind), so the PV + wind
total is recovered from existing columns. Only lagged values could be used as features.

Outputs:
    results/eda/figures/pv_wind_vs_consumption_by_season.png
    results/eda/figures/pv_wind_vs_consumption_deviation.png
    results/eda/tables/pv_wind_lag_correlation.csv/.tex
    results/eda/tables/consumption_own_lag_correlation.csv/.tex
The summary correlations are printed.

    uv run python src/analysis/eda/analyze_pv_wind_vs_consumption.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from eda_common import (
    BLUE,
    FIG_HEIGHT,
    FIG_WIDTH,
    SEASON_COLORS,
    SEASON_MAP,
    SEASON_ORDER,
    apply_style,
    load_train,
    save_figure,
    save_table,
)


def residualize(target: pd.Series, controls: pd.DataFrame) -> np.ndarray:
    A = np.c_[np.ones(len(controls)), controls.values]
    beta = np.linalg.lstsq(A, target.values, rcond=None)[0]
    return target.values - A @ beta


def main() -> None:
    apply_style()
    df = load_train("daily")
    df["renewable_pv_wind"] = df["actual_consumption"] - df["residual_load"]
    df["season"] = df["month"].map(SEASON_MAP)

    print(df[["actual_consumption", "residual_load", "renewable_pv_wind"]].describe().round(0))
    print("corr(consumption, residual_load):", round(df["actual_consumption"].corr(df["residual_load"]), 3))
    print("corr(consumption, renewable):    ", round(df["actual_consumption"].corr(df["renewable_pv_wind"]), 3))

    # Same-day scatter by season
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    for color, season in zip(SEASON_COLORS, SEASON_ORDER):
        g = df[df["season"] == season]
        ax.scatter(g["renewable_pv_wind"] / 1e6, g["actual_consumption"] / 1e6, s=8, alpha=0.6, color=color,
                   linewidths=0, label=season)
    ax.set_xlabel("PV + wind (million MWh/day)")
    ax.set_ylabel("Actual consumption (million MWh/day)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=4, frameon=False)
    save_figure(fig, "pv_wind_vs_consumption_by_season")
    print(
        df.groupby("season")[["actual_consumption", "renewable_pv_wind"]].corr()
        .xs("actual_consumption", level=1)["renewable_pv_wind"].round(3)
    )

    # Remove the calendar effect: subtract the training mean of the same month x weekday
    key = [df["month"], df["day_of_week_raw"]]
    df["cons_dev"] = df["actual_consumption"] - df.groupby(key)["actual_consumption"].transform("mean")
    df["ren_dev"] = df["renewable_pv_wind"] - df.groupby(key)["renewable_pv_wind"].transform("mean")

    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    ax.scatter(df["ren_dev"] / 1e3, df["cons_dev"] / 1e3, s=8, alpha=0.5, color=BLUE, linewidths=0)
    ax.set_xlabel("PV + wind deviation (thousand MWh/day)")
    ax.set_ylabel("Consumption deviation (thousand MWh/day)")
    save_figure(fig, "pv_wind_vs_consumption_deviation")
    print("corr of deviations (same day):", round(df["cons_dev"].corr(df["ren_dev"]), 3))

    # Lagged PV + wind vs consumption
    lag_table = pd.DataFrame(
        [
            {
                "lag_days": lag,
                "raw": df["actual_consumption"].corr(df["renewable_pv_wind"].shift(lag)),
                "calendar_adjusted": df["cons_dev"].corr(df["ren_dev"].shift(lag)),
            }
            for lag in [0, 1, 2, 7]
        ]
    )
    print("\nConsumption vs lagged PV + wind")
    print(lag_table.round(3).to_string(index=False))
    save_table(lag_table, "pv_wind_lag_correlation")

    own = pd.DataFrame(
        {
            "lag_days": [1, 7],
            "raw": [df["actual_consumption"].corr(df["actual_consumption"].shift(lag)) for lag in [1, 7]],
            "calendar_adjusted": [df["cons_dev"].corr(df["cons_dev"].shift(lag)) for lag in [1, 7]],
        }
    )
    print("\nConsumption vs its own lag")
    print(own.round(3).to_string(index=False))
    save_table(own, "consumption_own_lag_correlation")

    # Partial correlation: lagged PV + wind vs consumption, controlling for consumption lag 1 and 7
    X = pd.DataFrame(
        {
            "y": df["cons_dev"],
            "cons_l1": df["cons_dev"].shift(1),
            "cons_l7": df["cons_dev"].shift(7),
            "ren_l1": df["ren_dev"].shift(1),
        }
    ).dropna()
    e_y = residualize(X["y"], X[["cons_l1", "cons_l7"]])
    e_r = residualize(X["ren_l1"], X[["cons_l1", "cons_l7"]])
    print("\npartial corr (PV + wind lag 1 | consumption lag 1, lag 7):", round(np.corrcoef(e_y, e_r)[0, 1], 3))


if __name__ == "__main__":
    main()
