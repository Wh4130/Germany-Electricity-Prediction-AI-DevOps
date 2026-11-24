"""
Correlation and multicollinearity of the candidate features (daily, training period).

The candidate features are those of the SARIMAX notebook (daily.ipynb, "Analyze all features that might be used
for all models"), including the two that the notebooks make themselves (is_holiday_weekday and
solar_generation_proxy = solar_capacity_mw * shortwave_radiation_sum).

- Correlation matrix of all candidates and the first yearly Fourier pair (sin_y1, cos_y1). The other Fourier pairs
  and the month and weekday dummies are not drawn: pairs of different frequency are nearly uncorrelated, and the
  dummies are another way to code the same cycles, never used together with the Fourier terms.
- VIF of the candidates without any time feature (no Fourier terms, no dummies). is_weekday is left out first: it
  is a linear combination of the weekday dummies (VIF infinite), and it is replaced by is_holiday_weekday.

Outputs:
    results/eda/figures/feature_correlation.png
    results/eda/tables/feature_vif.csv/.tex
    results/eda/tables/feature_correlation_pairs.csv/.tex   (pairs with |r| >= 0.7)

    uv run python src/analysis/eda/analyze_feature_correlation.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant

from eda_common import apply_style, load_train, save_figure, save_table

CALENDAR = [
    "is_holiday",
    "is_weekday",
    "is_holiday_weekday",
    "weighted_regional_holiday",
    "weighted_school_holiday",
    "is_bridge_day",
    "is_christmas_new_year",
    "is_dst",
    "is_dst_transition_day",
]
ECONOMIC = ["industrial_confidence", "gas_price_eu_usd", "ipi_ei_level", "day_ahead_price_mean"]
WEATHER = ["hdd", "daylight_duration", "shortwave_radiation_sum", "wind_speed_10m_mean", "precipitation_sum"]
SOLAR_POLICY = ["solar_capacity_mw", "solar_generation_proxy", "oxcgrt_stringency"]
FOURIER_FIRST = ["sin_y1", "cos_y1"]

NON_TIME = CALENDAR + ECONOMIC + WEATHER + SOLAR_POLICY
R_LABEL = 0.7  # correlations at or above this are written in the figure and listed in the pairs table


def candidate_features(df: pd.DataFrame) -> pd.DataFrame:
    """The candidates as floats, with the two features that are made in the notebooks."""
    out = df.copy()
    out["is_holiday_weekday"] = (out["is_holiday"].astype(bool) & out["is_weekday"].astype(bool)).astype(float)
    out["solar_generation_proxy"] = out["solar_capacity_mw"] * out["shortwave_radiation_sum"]
    return out[NON_TIME + FOURIER_FIRST].astype(float)


def correlation_figure(X: pd.DataFrame) -> pd.DataFrame:
    corr = X.corr()
    mask = np.triu(np.ones_like(corr, dtype=bool))
    labels = corr.map(lambda v: f"{v:.1f}" if abs(v) >= R_LABEL else "")

    import seaborn as sns

    fig, ax = plt.subplots(figsize=(6.3, 6.3))
    sns.heatmap(corr, mask=mask, annot=labels, fmt="", annot_kws={"size": 5}, cmap="coolwarm", vmin=-1, vmax=1,
                center=0, linewidths=0.3, cbar_kws={"shrink": 0.6, "label": "Pearson r"}, ax=ax)
    ax.grid(False)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    save_figure(fig, "feature_correlation")
    return corr


def pairs_table(corr: pd.DataFrame) -> pd.DataFrame:
    below = ~np.triu(np.ones_like(corr, dtype=bool))
    pairs = corr.where(below).stack().rename("r").reset_index()
    pairs.columns = ["Feature A", "Feature B", "r"]
    pairs = pairs[pairs["r"].abs() >= R_LABEL].copy()
    return pairs.reindex(pairs["r"].abs().sort_values(ascending=False).index).reset_index(drop=True)


def vif_table(X: pd.DataFrame) -> pd.DataFrame:
    """VIF of the non-time candidates; is_weekday is dropped first (exactly collinear with the weekday dummies)."""
    Z = add_constant(X[NON_TIME].drop(columns=["is_weekday"]).dropna())
    vif = [variance_inflation_factor(Z.values, i) for i in range(1, Z.shape[1])]
    return pd.DataFrame({"Feature": Z.columns[1:], "VIF": vif}).sort_values("VIF", ascending=False).reset_index(drop=True)


def main() -> None:
    apply_style()
    X = candidate_features(load_train("daily"))
    print(f"{len(X)} days, {X.shape[1]} features")

    corr = correlation_figure(X)
    pairs = pairs_table(corr)
    print(pairs.round(2).to_string(index=False))
    save_table(pairs, "feature_correlation_pairs", float_format="%.2f")

    vif = vif_table(X)
    print(vif.round(1).to_string(index=False))
    save_table(vif, "feature_vif", float_format="%.1f")


if __name__ == "__main__":
    main()
