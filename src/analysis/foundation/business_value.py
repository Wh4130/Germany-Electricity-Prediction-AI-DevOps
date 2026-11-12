"""
Business value of the forecasts (analysis_plan.md, section 5).

For every forecast file (all days of the evaluation year):

1. Yearly forecast error volume: MAE x number of target steps in the year,
   in TWh, for the model and the seasonal naive; the reduction against the
   naive, and against a reference run (``--reference``, e.g. the run without
   covariates) of the same resolution and horizon.
   For daily 7 d runs this is the error of an average lead day.
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

Usage (from the project root):

    uv run python src/analysis/foundation/business_value.py \
        src/results/forecasts/timesfm3_zs_*_test.csv src/results/forecasts/tabicl_default_*_ctxall_test.csv \
        --reference timesfm3_zs_nocov_hourly_24h_ctx8192_test timesfm3_zs_nocov_daily_1d_ctxall_test \
                    timesfm3_zs_nocov_daily_7d_ctxall_test
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
FOUNDATION_DIR = SRC_DIR / "models" / "foundation"
if str(FOUNDATION_DIR) not in sys.path:
    sys.path.insert(0, str(FOUNDATION_DIR))

import numpy as np
import pandas as pd

from models.foundation.data import DAY_AHEAD_PRICE, DEFAULT_DATA_DIR
from models.foundation.evaluate import DEFAULT_METRICS_DIR
from report_tables import Report, horizon_text, run_info
from weather_breakdown import load_rows, run_names

TOP_PRICE_SHARE = 0.10


def value_row(path: Path, frames: dict, data_dir: Path, run: str) -> dict:
    fc, frame, split = load_rows(path, frames, data_dir)
    res = frame.resolution
    info = run_info(run)
    y, yp, yn = (fc[c].to_numpy(float) for c in ("y_true", "y_pred", "y_naive"))
    err, err_naive = yp - y, yn - y
    ae, ae_naive = np.abs(err), np.abs(err_naive)

    # Steps of the year: each target time once (the 7 d runs hold each day up to 7 times).
    n_year = fc["target_time"].nunique()
    price = np.abs(frame.df[DAY_AHEAD_PRICE[res]].to_numpy(float)[fc["tpos"].to_numpy()])
    signed_price = frame.df[DAY_AHEAD_PRICE[res]].to_numpy(float)[fc["tpos"].to_numpy()]
    top = signed_price >= np.quantile(signed_price, 1 - TOP_PRICE_SHARE)
    pw_mae = float((price * ae).sum() / price.sum())
    steps_per_year = n_year / len(fc)  # rescales sums over rows to one value per target time

    return {
        "run": run, "Model": info["model"], "resolution": res, "horizon": info["horizon"],
        "Horizon": horizon_text(res, info["horizon"]), "split": split,
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
    """Reduction against a reference run of the same resolution, horizon and split."""
    out = table.copy()
    out["Reference"] = ""
    out["Reduction vs reference (TWh)"] = np.nan
    out["Value reduction vs reference (EUR m)"] = np.nan
    ref = table[table["run"].isin(references)]
    for _, r in ref.iterrows():
        same = ((out["resolution"] == r["resolution"]) & (out["horizon"] == r["horizon"])
                & (out["split"] == r["split"]) & (out["run"] != r["run"]))
        out.loc[same, "Reference"] = r["Model"]
        out.loc[same, "Reduction vs reference (TWh)"] = r["Yearly error (TWh)"] - out.loc[same, "Yearly error (TWh)"]
        out.loc[same, "Value reduction vs reference (EUR m)"] = (
            r["Error at day-ahead price (EUR m)"] - out.loc[same, "Error at day-ahead price (EUR m)"])
    missing = set(references) - set(table["run"])
    if missing:
        print(f"[value] note: reference runs not among the files: {sorted(missing)}")
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
                row = {"Model": r["Model"], "Against": against, "Market share %": share}
                for cost in costs:
                    row[f"{cost:g} EUR/MWh (EUR m)"] = twh * 1e6 * cost * share / 100 / 1e6
                rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+", type=Path, help="forecast CSV files")
    p.add_argument("--reference", nargs="*", default=[],
                   help="run names to compare against: the file stem, or 'stem [folder]' when the same "
                        "file name is given from two results folders")
    p.add_argument("--costs", type=float, nargs="+", default=[5, 10, 20], help="imbalance cost, EUR/MWh")
    p.add_argument("--shares", type=float, nargs="+", default=[1, 5, 10], help="market share, %%")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_METRICS_DIR / "report")
    args = p.parse_args()

    frames = {}
    names = run_names(args.files)
    table = pd.DataFrame([value_row(f, frames, args.data_dir, names[f]) for f in args.files])
    table = add_reference(table, args.reference)
    table = table.sort_values(["resolution", "horizon", "MAE (MWh)"], ascending=[False, True, True])

    report = Report(args.out_dir, md_name="business_value.md", title="Business value")
    shown = ["Model", "Horizon", "MAE (MWh)", "Yearly error (TWh)", "Naive yearly error (TWh)",
             "Reduction vs naive (TWh)", "Reference", "Reduction vs reference (TWh)"]
    report.add("value_error_volume", "Yearly forecast error volume", table[shown].round(3),
               note="National scale, all days of the year. Daily 7 d: average lead day.")
    shown = ["Model", "Horizon", "MAE (MWh)", "Price-weighted MAE (MWh)", "Price-weighted / plain MAE",
             "MAE top-10 % price (MWh)", "Bias top-10 % price (MWh)", "Error at day-ahead price (EUR m)",
             "Naive error at day-ahead price (EUR m)", "Value reduction vs reference (EUR m)"]
    report.add("value_price_weighted", "Accuracy where power is expensive", table[shown],
               note="Bias < 0 = under-forecast. Error at day-ahead price = sum of |error| x |price|, "
                    "national scale.")
    sens = sensitivity(table, args.costs, args.shares)
    if not sens.empty:
        report.add("table6_value_sensitivity", "Table 6. Yearly value of the hourly forecast (EUR million)", sens,
                   note="Error reduction x imbalance cost x market share. Upper bound: observed weather inputs.")
    path = report.write()
    table.to_csv(args.out_dir / "business_value.csv", index=False)

    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(table[["Model", "Horizon", "MAE (MWh)", "Reduction vs naive (TWh)", "Reduction vs reference (TWh)",
                     "Price-weighted / plain MAE", "Bias top-10 % price (MWh)"]].round(3).to_string(index=False))
    print(f"\n[value] tables -> {path}")


if __name__ == "__main__":
    main()