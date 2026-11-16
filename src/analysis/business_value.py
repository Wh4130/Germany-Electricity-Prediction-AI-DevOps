"""
Business value of the forecasts of any model (analysis_plan.md, section 5).

For every run (all days of the evaluation year):

1. Yearly forecast error volume: MAE x number of target steps in the year,
   in TWh, for the model and the seasonal naive; the reduction against the
   naive, and against a reference model (``--reference``, e.g. the TimesFM-3
   run without covariates) of the same resolution, horizon and split.
   For multi-step runs this is the error of an average lead step.
2. Price-weighted view, with the day-ahead price of the target time
   (hourly: the hourly price, daily: the mean price of the day):
   - price-weighted MAE (weights |price|); a ratio above 1 means the errors
     are larger in the expensive hours,
   - MAE and bias in the most expensive 10 % of the steps
     (bias < 0 = under-forecast, i.e. short when power is expensive),
   - the error valued at the day-ahead price (sum of |error| x |price|),
     a simple proxy of what the error costs, in EUR million.
3. Value sensitivity (hourly runs only, because imbalance is settled on short
   intervals and daily errors partly cancel within the day): the yearly error
   reduction x imbalance cost per MWh x market share.
   This assumes a portfolio's error scales with its share of national load;
   a small portfolio is usually less smooth, so the estimate is conservative.

The weather inputs are observed values (variant A), so the value is an upper bound.

Outputs (``src/results/final_report/tables``): business_value.csv, value_*.csv,
table6_value_sensitivity.csv and business_value.md.

Usage (from the project root):

    uv run python -m src.analysis.business_value
    uv run python -m src.analysis.business_value --reference "TimesFM-3, no covariates"
    uv run python -m src.analysis.business_value --reference sarimax/sarimax_hourly_24h_test
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.dataset import DAY_AHEAD_PRICE, FrameCache
from src.common.paths import DATA_DIR, RESULTS_DIR, TABLES_DIR
from src.analysis.report import Report
from src.analysis.runs import Run, discover_runs
from src.analysis.weather_breakdown import load_rows

TOP_PRICE_SHARE = 0.10


def value_row(run: Run, frames: dict) -> dict:
    fc, frame = load_rows(run, frames)
    res = frame.resolution
    y, yp, yn = (fc[c].to_numpy(float) for c in ("y_true", "y_pred", "y_naive"))
    err, err_naive = yp - y, yn - y
    ae, ae_naive = np.abs(err), np.abs(err_naive)

    # Steps of the year: each target time once (multi-step runs hold a target several times).
    n_year = fc["target_time"].nunique()
    signed_price = frame.df[DAY_AHEAD_PRICE[res]].to_numpy(float)[fc["tpos"].to_numpy()]
    price = np.abs(signed_price)
    top = signed_price >= np.quantile(signed_price, 1 - TOP_PRICE_SHARE)
    pw_mae = float((price * ae).sum() / price.sum())
    steps_per_year = n_year / len(fc)  # rescales sums over rows to one value per target time

    return {
        **run.info(),
        "MAE (MWh)": ae.mean(), "Naive MAE (MWh)": ae_naive.mean(),
        "Yearly error (TWh)": ae.mean() * n_year / 1e6,
        "Naive yearly error (TWh)": ae_naive.mean() * n_year / 1e6,
        "Reduction vs naive (TWh)": (ae_naive.mean() - ae.mean()) * n_year / 1e6,
        "Price-weighted MAE (MWh)": pw_mae,
        "Price-weighted / plain MAE": pw_mae / ae.mean(),
        "MAE top-10 % price (MWh)": ae[top].mean(),
        "Bias top-10 % price (MWh)": err[top].mean(),
        "Error at day-ahead price (EUR m)": (price * ae).sum() * steps_per_year / 1e6,
        "Naive error at day-ahead price (EUR m)": (price * ae_naive).sum() * steps_per_year / 1e6,
    }


def add_reference(table: pd.DataFrame, references: list[str]) -> pd.DataFrame:
    """Reduction against a reference run of the same resolution, horizon and split.

    A reference is a run id (``<model folder>/<file stem>``) or a model label
    (then every horizon of that model is a reference for its horizon).
    """
    out = table.copy()
    out["Reference"] = ""
    out["Reduction vs reference (TWh)"] = np.nan
    out["Value reduction vs reference (EUR m)"] = np.nan
    ref = table[table["run"].isin(references) | table["Model"].isin(references)]
    for _, r in ref.iterrows():
        same = ((out["resolution"] == r["resolution"]) & (out["horizon"] == r["horizon"])
                & (out["split"] == r["split"]) & (out["run"] != r["run"]))
        out.loc[same, "Reference"] = r["Model"]
        out.loc[same, "Reduction vs reference (TWh)"] = r["Yearly error (TWh)"] - out.loc[same, "Yearly error (TWh)"]
        out.loc[same, "Value reduction vs reference (EUR m)"] = (
            r["Error at day-ahead price (EUR m)"] - out.loc[same, "Error at day-ahead price (EUR m)"])
    missing = set(references) - set(table["run"]) - set(table["Model"])
    if missing:
        print(f"[value] note: references not among the runs: {sorted(missing)}")
    return out


def sensitivity(table: pd.DataFrame, costs: list[float], shares: list[float]) -> pd.DataFrame:
    """Yearly value in EUR million for each imbalance cost and market share (hourly runs)."""
    rows = []
    for _, r in table[table["resolution"] == "hourly"].iterrows():
        bases = [("vs seasonal naive", r["Reduction vs naive (TWh)"])]
        if r.get("Reference"):
            bases.append((f"vs {r['Reference']}", r["Reduction vs reference (TWh)"]))
        for against, twh in bases:
            for share in shares:
                row = {"Model": r["Model"], "Horizon": r["Horizon"], "Against": against, "Market share %": share}
                for cost in costs:
                    row[f"{cost:g} EUR/MWh (EUR m)"] = twh * 1e6 * cost * share / 100 / 1e6
                rows.append(row)
    return pd.DataFrame(rows)


def build(runs: list[Run], frames: dict, references: list[str] | None = None, costs=(5, 10, 20),
          shares=(1, 5, 10), out_dir: Path = TABLES_DIR) -> pd.DataFrame:
    runs = [r for r in runs if not r.is_naive]
    table = pd.DataFrame([value_row(r, frames) for r in runs])
    table = add_reference(table, list(references or []))
    table = table.sort_values(["resolution", "horizon", "MAE (MWh)"], ascending=[False, True, True])

    report = Report(out_dir, md_name="business_value.md", title="Business value")
    shown = ["Model", "Horizon", "MAE (MWh)", "Yearly error (TWh)", "Naive yearly error (TWh)",
             "Reduction vs naive (TWh)", "Reference", "Reduction vs reference (TWh)"]
    report.add("value_error_volume", "Yearly forecast error volume", table[shown].round(3),
               note="National scale, all days of the year. Multi-step runs: average lead step.")
    shown = ["Model", "Horizon", "MAE (MWh)", "Price-weighted MAE (MWh)", "Price-weighted / plain MAE",
             "MAE top-10 % price (MWh)", "Bias top-10 % price (MWh)", "Error at day-ahead price (EUR m)",
             "Naive error at day-ahead price (EUR m)", "Value reduction vs reference (EUR m)"]
    report.add("value_price_weighted", "Accuracy where power is expensive", table[shown],
               note="Bias < 0 = under-forecast. Error at day-ahead price = sum of |error| x |price|, "
                    "national scale.")
    sens = sensitivity(table, list(costs), list(shares))
    if not sens.empty:
        report.add("table6_value_sensitivity", "Table 6. Yearly value of the hourly forecasts (EUR million)", sens,
                   note="Error reduction x imbalance cost x market share. Upper bound: observed weather inputs.")
    path = report.write()
    table.to_csv(Path(out_dir) / "business_value.csv", index=False)
    print(f"[value] tables -> {path}")
    return table


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--models", nargs="+", default=None, help="results folders (default: all)")
    p.add_argument("--split", choices=["val", "test"], default="test")
    p.add_argument("--reference", nargs="*", default=[],
                   help="model labels or run ids (<model folder>/<file stem>) to compare against")
    p.add_argument("--costs", type=float, nargs="+", default=[5, 10, 20], help="imbalance cost, EUR/MWh")
    p.add_argument("--shares", type=float, nargs="+", default=[1, 5, 10], help="market share, %%")
    p.add_argument("--data-dir", type=Path, default=DATA_DIR)
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--out-dir", type=Path, default=TABLES_DIR)
    args = p.parse_args()

    runs = discover_runs(args.results_dir, args.models, args.split, include_naive=False)
    table = build(runs, FrameCache(args.data_dir), args.reference, args.costs, args.shares, args.out_dir)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(table[["Model", "Horizon", "MAE (MWh)", "Reduction vs naive (TWh)", "Reduction vs reference (TWh)",
                     "Price-weighted / plain MAE", "Bias top-10 % price (MWh)"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()