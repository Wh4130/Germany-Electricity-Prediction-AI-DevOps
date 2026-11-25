"""
Which model is best in which group of days? One table for the report (daily forecasts, h = 1, test year).

It is built from the group tables that ``run_report`` writes (day types, heating degree days, change of the heating
degree days against the last week): one row per group, the MAE of each model, the number of days and the best model.
Run ``run_report`` first; run this again after it, the table does not update by itself.

    uv run python -m src.analysis.group_summary

Output: src/results/final_report/tables/group_summary.csv/.md/.tex
        src/results/final_report/tables/lead_time_mae.csv/.md/.tex (MAE by lead day of the 7-day forecast)

Small groups (bridge days: 3, holidays: 9) are in the table with their number of days, so the reader can see that a
"best model" there rests on few days.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.analysis.report import Report, latex_escape
from src.common.paths import TABLES_DIR

HORIZON = "daily 1 d"
MODELS = ["SARIMAX", "Tree-based", "TabICL", "TimesFM-3, covariates"]  # TimesFM-3 without covariates: far worse
SHORT = {"TimesFM-3, covariates": "TimesFM-3 cov."}

# (feature, source table, column with the group, column with the number of days)
SOURCES = [
    ("Day type", "table3_day_types", "Day type", "Hours / days"),
    ("Heating degree days", "table_weather_hdd", "Weather", "Days"),
    ("Change vs. last week", "table_weather_hdd_change_vs_last_week", "Weather", "Days"),
]


def group_rows(tables_dir: Path, feature: str, name: str, group_col: str, days_col: str) -> pd.DataFrame:
    path = tables_dir / f"{name}.csv"
    if not path.exists():
        raise SystemExit(f"{path} is missing: run 'uv run python -m src.analysis.run_report' first")
    df = pd.read_csv(path)
    df = df[(df["Horizon"] == HORIZON) & df["Model"].isin(MODELS)]
    if df.empty:
        raise SystemExit(f"{name}: no rows for {HORIZON} and the models {MODELS}")
    order = list(dict.fromkeys(df[group_col]))  # the order of the source table
    mae = df.pivot_table(index=group_col, columns="Model", values="MAE (MWh)").reindex(order)[MODELS]
    missing = [m for m in MODELS if m not in mae.columns or mae[m].isna().any()]
    if missing:
        raise SystemExit(f"{name}: no {HORIZON} MAE of {missing} in every group")
    days = df.groupby(group_col)[days_col].first().reindex(order)
    out = mae.copy()
    out.insert(0, "Days", days.astype(int))
    out.insert(0, "Group", out.index)
    out.insert(0, "Feature", feature)
    out["Best"] = mae.idxmin(axis=1)
    return out.reset_index(drop=True)


def lead_time_mae(tables_dir: Path) -> pd.DataFrame:
    """MAE of each model for every lead day of the 7-day forecast (from the lead time table of run_report)."""
    path = tables_dir / "table_lead_time_daily_7_d.csv"
    if not path.exists():
        raise SystemExit(f"{path} is missing: run 'uv run python -m src.analysis.run_report' first")
    df = pd.read_csv(path)
    cols = {m: f"MAE (MWh) {m}" for m in MODELS}
    missing = [c for c in cols.values() if c not in df.columns]
    if missing:
        raise SystemExit(f"{path.name}: no column {missing}")
    # short headers (the unit is in the caption of the report), so the table fits the page width
    out = df[["Lead day"] + list(cols.values())].rename(columns={v: SHORT.get(k, k) for k, v in cols.items()})
    return out


def latex_grouped(table: pd.DataFrame) -> str:
    """
    The LaTeX table with one heading row per feature (day type, ...) instead of a Feature column, a Group column that
    wraps, and the short TimesFM-3 header on two lines, so that it fits the text width without shrinking.
    """
    models = [SHORT.get(m, m) for m in MODELS]
    head = ["Group", "Days"] + [r"\shortstack{TimesFM-3\\cov.}" if m == SHORT["TimesFM-3, covariates"] else latex_escape(m)
                                for m in models] + ["Best"]
    lines = [r"\setlength{\tabcolsep}{3pt}",
             r"\begin{tabular}{>{\raggedright\arraybackslash\hangindent=1em}p{0.23\textwidth}c" + "c" * len(models)
             + r">{\raggedright\arraybackslash}p{0.15\textwidth}}",
             r"\toprule", " & ".join(head) + r" \\", r"\midrule"]
    for feature, rows in table.groupby("Feature", sort=False):
        lines.append(r"\multicolumn{%d}{@{}l}{\textit{%s}} \\" % (len(head), latex_escape(feature)))
        for _, r in rows.iterrows():
            cells = [r"\hspace{1em}" + latex_escape(r["Group"]), str(int(r["Days"]))]
            best = latex_escape(r["Best"]).replace(" cov.", "")  # only the covariate version is in the table
            cells += [f"{r[m]:,.0f}" for m in models] + [best]
            lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tables-dir", type=Path, default=TABLES_DIR)
    args = p.parse_args()

    lead = lead_time_mae(args.tables_dir)
    lead_report = Report(args.tables_dir, md_name="lead_time_mae.md", prefix="", title="MAE by lead day")
    lead_report.add("lead_time_mae", "MAE of the 7-day forecast by lead day, test year", lead,
                    note="MAE in MWh. Daily forecasts, each lead day on its own (not an average over the days). "
                         "cov. = with covariates.", numeric_align="c")
    lead_report.write()
    print(lead.to_string(index=False))

    table = pd.concat([group_rows(args.tables_dir, *s) for s in SOURCES], ignore_index=True)
    # short names, so the table fits the page width without shrinking (the unit is in the note and the caption)
    table["Best"] = table["Best"].replace(SHORT)
    table = table.rename(columns=SHORT)

    report = Report(args.tables_dir, md_name="group_summary.md", prefix="", title="Best model by group of days")
    report.add("group_summary", f"MAE by group of days, {HORIZON}, test year", table,
               note=("Groups of days of the test year; MAE of the one-day forecast in MWh; cov. = with covariates. "
                     "'Best' is the model with "
                     "the lowest MAE; small groups (few days) rest on little data, and differences of a few hundred "
                     "MWh are not meaningful."), numeric_align="c")
    path = report.write()
    (args.tables_dir / "group_summary.tex").write_text(latex_grouped(table))  # replaces the plain one of Report.add
    print(table.to_string(index=False))
    print(f"[group_summary] -> {path}")


if __name__ == "__main__":
    main()
