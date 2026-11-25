"""
Does averaging models help? For one resolution, horizon and split, on the forecasts that all models have in common
(same origin and target time). The main metric is the RMSE, as in the validation protocol of the report; the MAE is
given next to it.

1. RMSE, MAE and bias of every model,
2. the correlation of their errors,
3. for every pair: does the equal-weight average of the two beat the better one? An average of two models has
   MSE = (s1^2 + s2^2 + 2 r s1 s2) / 4 (s: RMSE, r: correlation of the errors). With q = s_worse / s_better, it is
   below the MSE of the better model if and only if  r < (3 - q^2) / (2 q). The table gives that threshold, the
   prediction, and what happened,
4. every combination of two or more models: RMSE and MAE of the equal-weight average and the gain over the best
   single model of that combination. There is no significance test: a gain of about one percent on one year of
   data is not shown to be more than chance.

An average has no fitted parameter; only the choice of the models in it comes from the data. Choose that on the
validation year (--split val) and report the test year (--split test) once. If the choice is made on the test
year, call the result exploratory: it is not an unbiased test result.

Usage (from the project root):

    uv run python -m src.analysis.ensemble_check --split test --resolution daily --horizon 1
    uv run python -m src.analysis.ensemble_check --split test --resolution daily --horizon 7
    uv run python -m src.analysis.ensemble_check --split test --labels TabICL SARIMAX "Tree-based"
    uv run python -m src.analysis.ensemble_check --split val --stems tabicl_default_daily_1d_ctxall_val \\
        timesfm3_zs_cov_daily_1d_ctxall_val sarimax_daily_1d_val

Without --labels the four models of the report are used: TabICL, TimesFM-3 with covariates, SARIMAX, Tree-based
(those of them that have forecasts for the chosen resolution, horizon and split).

The tables go to src/results/final_report/tables/ensemble/ (CSV, Markdown, LaTeX). The LaTeX files ending in
_pairs_slim.tex and _averages_slim.tex are the narrow versions of the pairs and the averages for the report.
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.report import Report, latex_escape
from src.analysis.runs import discover_runs
from src.common.paths import RESULTS_DIR, TABLES_DIR

MAX_MODELS = 8  # 2^8 combinations
DEFAULT_LABELS = ["TabICL", "TimesFM-3, covariates", "SARIMAX", "Tree-based"]


def load_common(runs, labels: list[str] | None, stems: list[str] | None) -> tuple[pd.DataFrame, pd.Series]:
    """Predictions of the runs side by side on the rows that all of them have; y_true of those rows."""
    preds, truth = {}, []
    for run in runs:
        if labels is not None and run.label not in labels:
            continue
        if stems is not None and run.stem not in stems:
            continue
        df = pd.read_csv(run.forecast_path, usecols=lambda c: c in ("origin", "target_time", "y_true", "y_pred"))
        df["origin"] = df["origin"].astype(str)
        df["target_time"] = df["target_time"].astype(str)
        df = df.drop_duplicates(["origin", "target_time"]).set_index(["origin", "target_time"])
        if run.label in preds:
            raise SystemExit(f"two runs are called '{run.label}': pick one with --labels or give them different labels")
        preds[run.label] = df["y_pred"]
        truth.append(df["y_true"])
    if len(preds) < 2:
        raise SystemExit("need at least two models with forecasts of this resolution, horizon and split")
    if len(preds) > MAX_MODELS:
        raise SystemExit(f"{len(preds)} models: pick at most {MAX_MODELS} with --labels")
    P = pd.DataFrame(preds)
    y = pd.concat(truth, axis=1).bfill(axis=1).iloc[:, 0].reindex(P.index)  # y_true of any file that has it
    ok = P.notna().all(axis=1) & y.notna()
    return P[ok].sort_index(), y[ok].sort_index()


def rmse(e: pd.DataFrame | pd.Series):
    return np.sqrt((e ** 2).mean())


def threshold(q: float) -> float:
    """The error correlation below which the average of two models beats the better one (q = RMSE worse / better)."""
    return (3 - q ** 2) / (2 * q)


def two(v: float) -> str:
    return f"{v:.2f}"


SHORT = {"TimesFM-3, covariates": "TimesFM-3 cov."}


def short(text: str) -> str:
    """Model names as in the narrow tables of the report (TimesFM-3 cov. = with covariates)."""
    for long_name, short_name in SHORT.items():
        text = text.replace(long_name, short_name)
    return text


def signed(v: float) -> str:
    return f"{v:+.1f}".replace("-", "$-$")


def slim_pairs_tex(pairs: pd.DataFrame) -> str:
    """Pair, correlation, threshold, RMSE of the better model and of the average, change; numbers centred."""
    lines = [r"\setlength{\tabcolsep}{3pt}",
             r"\begin{tabular}{lccccc}",
             r"\toprule",
             r"Pair & Correlation & Threshold & \shortstack{RMSE of\\better model} & "
             r"\shortstack{RMSE of\\average} & \shortstack{RMSE\\change \%} \\",
             r"\midrule"]
    for _, r in pairs.iterrows():
        label = latex_escape(short(f"{r['Better model']} + {r['Other model']}"))
        lines.append(" & ".join([label, r["Error correlation"], r["Threshold"],
                                 f"{r['RMSE of the better model (MWh)']:,.0f}",
                                 f"{r['RMSE of the average (MWh)']:,.0f}",
                                 signed(r["RMSE change vs better %"])]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def slim_averages_tex(avg: pd.DataFrame) -> str:
    """All averages: the models of the average wrap, RMSE and MAE with their gain, numbers centred."""
    lines = [r"\setlength{\tabcolsep}{4pt}",
             r"\begin{tabular}{lcccc}",
             r"\toprule",
             r"Average of & RMSE & \shortstack{RMSE\\gain \%} & MAE & \shortstack{MAE\\gain \%} \\",
             r"\midrule"]
    for i, r in avg.iterrows():
        label = latex_escape(short(r["Average of"]))
        if i == 0:
            label = r"\textbf{" + label + "}"
        lines.append(" & ".join([label, f"{r['RMSE (MWh)']:,.0f}", signed(r["RMSE gain vs best single %"]),
                                 f"{r['MAE (MWh)']:,.0f}", signed(r["MAE gain vs best single %"])]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", choices=["val", "test"], default="test")
    p.add_argument("--resolution", choices=["daily", "hourly"], default="daily")
    p.add_argument("--horizon", type=int, default=1)
    p.add_argument("--labels", nargs="+", default=None,
                   help=f"model labels to use (default: {', '.join(DEFAULT_LABELS)})")
    p.add_argument("--stems", nargs="+", default=None,
                   help="forecast file names (without .csv) to use, when a label has several runs (e.g. the "
                        "settings compared on val)")
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--out-dir", type=Path, default=TABLES_DIR / "ensemble")
    args = p.parse_args()
    labels = args.labels if args.labels is not None or args.stems is not None else DEFAULT_LABELS

    runs = [r for r in discover_runs(args.results_dir, None, args.split, include_naive=False)
            if r.resolution == args.resolution and r.horizon == args.horizon]
    if not runs:
        raise SystemExit(f"no {args.split} forecast files for {args.resolution} {args.horizon}")
    P, y = load_common(runs, labels, args.stems)
    models = list(P.columns)
    err = P.sub(y, axis=0)
    name = f"{args.resolution}_{args.horizon}_{args.split}"
    unit = "d" if args.resolution == "daily" else "h"
    print(f"[ensemble] {args.resolution} {args.horizon}{unit}, {args.split}: {len(P)} common forecasts, "
          f"models: {', '.join(models)}")

    report = Report(args.out_dir, md_name=f"ensemble_{name}.md", prefix=f"ensemble_{name}_",
                    title=f"Averaging models: {args.resolution} {args.horizon}{unit}, {args.split} year")

    s_rmse, s_mae = rmse(err), err.abs().mean()
    single = pd.DataFrame({"Model": models, "n": len(P), "RMSE (MWh)": s_rmse.to_numpy(),
                           "MAE (MWh)": s_mae.to_numpy(), "Bias (MWh)": err.mean().to_numpy()}
                          ).sort_values("RMSE (MWh)")
    report.add("metrics", "RMSE and MAE of each model on the common forecasts", single, bold_rows=[0],
               note=f"{len(P)} forecasts that every model has (same origin and target time). Sorted by RMSE.")

    corr = err.corr()
    corr_text = corr.astype(object).map(lambda v: f"{v:.2f}")
    corr_text.insert(0, "Model", corr_text.index)
    report.add("error_correlation", "Correlation of the errors", corr_text.reset_index(drop=True),
               note="Errors = forecast minus actual. Below 1 means an average can cancel part of the errors.")

    pair_rows = []
    for a, b in itertools.combinations(models, 2):
        better, worse = (a, b) if s_rmse[a] <= s_rmse[b] else (b, a)
        q = s_rmse[worse] / s_rmse[better]
        r = float(corr.loc[a, b])
        thr = threshold(q)
        avg = rmse(P[[a, b]].mean(axis=1) - y)
        helps = avg < s_rmse[better]
        pair_rows.append({"Better model": better, "Other model": worse, "Error correlation": two(r),
                          "RMSE ratio": two(q), "Threshold": two(thr),
                          "Expected": "helps" if r < thr else "does not help",
                          "Result": "helps" if helps else "does not help",
                          "RMSE of the better model (MWh)": float(s_rmse[better]),
                          "RMSE of the average (MWh)": float(avg),
                          "RMSE change vs better %": 100 * (avg - s_rmse[better]) / s_rmse[better]})
    pairs = pd.DataFrame(pair_rows).sort_values("RMSE change vs better %")
    agree = int((pairs["Expected"] == pairs["Result"]).sum())
    report.add("pairs", "Pairs of models: does the average beat the better one?", pairs,
               note=(f"Expected: the correlation of the errors is below the threshold (3 - q^2) / (2 q), q = RMSE of "
                     f"the other model / RMSE of the better one. Result: the RMSE of the average is below that of "
                     f"the better model. Expected and result agree in {agree} of {len(pairs)} pairs. "
                     f"'RMSE change' is negative when the average is better."))

    rows = []
    for k in range(2, len(models) + 1):
        for combo in itertools.combinations(models, k):
            combo = list(combo)
            e_avg = P[combo].mean(axis=1) - y
            best_rmse_model = s_rmse[combo].idxmin()
            best_mae = float(s_mae[combo].min())
            rows.append({"Average of": " + ".join(combo), "Models": k, "RMSE (MWh)": float(rmse(e_avg)),
                         "RMSE gain vs best single %": 100 * (s_rmse[best_rmse_model] - rmse(e_avg)) / s_rmse[best_rmse_model],
                         "MAE (MWh)": float(e_avg.abs().mean()),
                         "MAE gain vs best single %": 100 * (best_mae - float(e_avg.abs().mean())) / best_mae})
    avg_table = pd.DataFrame(rows).sort_values("RMSE (MWh)").reset_index(drop=True)
    report.add("averages", "Equal-weight averages", avg_table, bold_rows=[0],
               note=("Sorted by RMSE. Gain = reduction compared with the best single model (lowest RMSE) inside the "
                     "same combination (negative: the average is worse). No significance test."))
    path = report.write()
    # narrow versions for the report (the CSV and the Markdown above keep all columns)
    (args.out_dir / f"ensemble_{name}_pairs_slim.tex").write_text(slim_pairs_tex(pairs))
    (args.out_dir / f"ensemble_{name}_averages_slim.tex").write_text(slim_averages_tex(avg_table))

    best_single = single.iloc[0]
    best_avg = avg_table.iloc[0]
    print(f"[ensemble] best single: {best_single['Model']} RMSE {best_single['RMSE (MWh)']:,.0f}")
    print(f"[ensemble] best average: {best_avg['Average of']} RMSE {best_avg['RMSE (MWh)']:,.0f} "
          f"({best_avg['RMSE gain vs best single %']:.1f}% below the best single of its models)")
    print(f"[ensemble] pairs: expected and result agree in {agree} of {len(pairs)}")
    print(f"[ensemble] tables -> {args.out_dir}, all in one file -> {path}")


if __name__ == "__main__":
    main()
