"""
Report tables of the foundation-model results (analysis_plan.md, sections 1 - 4).

Reads only files that exist already, nothing is rerun:

- ``summary_foundation.csv`` -> Table 1 (main results on the test year) and the
  validation settings table (what was chosen and why),
- the metrics JSON of every test run -> Table 3 (results by day type), the
  covariate gain by day type, TabICL vs TimesFM-3 by day type, and the lead time
  table of the 7 d runs,
- ``weather_breakdown.csv`` (from weather_breakdown.py) -> Tables 4 and 5
  (temperature change, midday radiation) and the other weather groups.

Optional: ``--classical`` adds summary files of other models (same columns as
summary_foundation.csv, e.g. SARIMAX or tree models) to Table 1.

Every table is written as CSV (raw numbers) and collected, formatted, in one
``report_tables.md``.

Usage (from the project root):

    uv run python src/analysis/foundation/report_tables.py
    uv run python src/analysis/foundation/report_tables.py --classical src/results/metrics/summary_classical.csv
"""

from __future__ import annotations

import argparse
import json
import re
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

from models.foundation.evaluate import DEFAULT_METRICS_DIR

EXPERIMENT_LABEL = {
    "baseline": "Seasonal naive",
    "F1": "TimesFM-3, no covariates",
    "F2": "TimesFM-3, covariates",
    "F4": "TimesFM-3, no covariates",
    "F5": "TimesFM-3, covariates",
    "F6": "TabICL",
}
DAY_TYPE_LABEL = {
    "normal_weekday": "Normal weekday",
    "weekend": "Weekend",
    "holiday": "Holiday",
    "bridge_day": "Bridge day",
    "christmas_new_year": "Christmas / New Year",
}
WEATHER_TITLE = {
    "hdd_change_vs_last_week": "Table 4. Results by temperature change against last week (ordinary days)",
    "radiation_vs_month": "Table 5. Results by radiation within the month (hourly: 10-16 h; ordinary days)",
    "hdd": "Results by heating degree days (ordinary days)",
    "wind": "Results by wind speed (ordinary days)",
    "precipitation": "Results by precipitation (ordinary days)",
    "holiday_week": "Results in holiday weeks vs other ordinary days",
}
WEATHER_ORDER = {
    "all": ["all"],
    "hdd": ["0 (no heating)", "mild", "cool", "cold"],
    "hdd_change_vs_last_week": ["no heating either week", "much warmer", "similar", "much colder"],
    "radiation_vs_month": ["dull", "average", "sunny"],
    "wind": ["calm", "moderate", "windy"],
    "precipitation": ["dry", "wet"],
    "holiday_week": ["holiday week", "weekend", "other weekday"],
}
WEATHER_VARIABLES = ["hdd_change_vs_last_week", "radiation_vs_month", "holiday_week", "hdd", "wind", "precipitation"]

# Formatting of the Markdown tables: column name pattern -> decimals.
MWH_DECIMALS = 0
PCT_DECIMALS = 1


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def horizon_text(resolution: str, horizon: int) -> str:
    return f"{resolution} {horizon} {'h' if resolution == 'hourly' else 'd'}"


def run_info(stem: str) -> dict:
    """Model label, resolution and horizon from a run file name."""
    m = re.search(r"_(hourly|daily)_(\d+)(h|d)_", stem)
    resolution, horizon = (m.group(1), int(m.group(2))) if m else ("?", 0)
    if stem.startswith("seasonal_naive"):
        model = "Seasonal naive"
    elif stem.startswith("timesfm3"):
        model = "TimesFM-3, covariates" if "_cov_" in stem else "TimesFM-3, no covariates"
    elif stem.startswith("tabicl"):
        model = "TabICL"
    else:
        model = stem
    tag = re.search(r"\[(.+)\]$", stem)  # duplicate names from weather_breakdown.run_names
    if tag:
        model = f"{model} [{tag.group(1).replace('_', ' ')}]"
    return {"model": model, "resolution": resolution, "horizon": horizon,
            "label": f"{model} ({horizon_text(resolution, horizon)})"}


def _number_format(name: str) -> str:
    """Format spec of a numeric column, from its name (first matching rule wins)."""
    if "TWh" in name:
        return ",.2f"
    if "EUR" in name and "%" not in name:
        return ",.1f"
    if "(MWh)" in name:
        return f",.{MWH_DECIMALS}f"
    if "/" in name and "MAE" in name:  # ratios
        return ".2f"
    if "change" in name.lower():
        return f"+.{PCT_DECIMALS}f"
    if "%" in name:
        return f".{PCT_DECIMALS}f"
    if name in ("n", "n_days", "Days", "Hours / days", "Lead day", "Horizon"):
        return "d"
    return f",.{MWH_DECIMALS}f"


def fmt(df: pd.DataFrame) -> pd.DataFrame:
    """Numbers as text for Markdown: MWh without decimals, %, TWh and ratios with decimals."""
    out = df.copy()
    for col in out.columns:
        if not pd.api.types.is_numeric_dtype(out[col]):
            continue
        spec = _number_format(str(col))
        out[col] = out[col].map(lambda v, s=spec: "" if pd.isna(v) else format(int(v) if s == "d" else v, s))
    return out


def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join(lines)


class Report:
    """Collects the tables: one CSV each, all of them in one Markdown file."""

    def __init__(self, out_dir: Path, md_name: str = "report_tables.md", title: str = "Report tables"):
        self.out_dir = out_dir
        self.md_name = md_name
        self.parts: list[str] = [f"# {title}\n"]
        out_dir.mkdir(parents=True, exist_ok=True)

    def add(self, name: str, title: str, df: pd.DataFrame, note: str = "", bold_rows=None):
        df.to_csv(self.out_dir / f"{name}.csv", index=False)
        shown = fmt(df)
        if bold_rows is not None:
            first = shown.columns[0]
            shown.loc[bold_rows, first] = "**" + shown.loc[bold_rows, first].astype(str) + "**"
        self.parts.append(f"## {title}\n")
        if note:
            self.parts.append(note + "\n")
        self.parts.append(md_table(shown) + "\n")

    def section(self, title: str):
        self.parts.append(f"\n# {title}\n")

    def write(self) -> Path:
        path = self.out_dir / self.md_name
        path.write_text("\n".join(self.parts))
        return path


# --------------------------------------------------------------------------
# Section 2: model comparison
# --------------------------------------------------------------------------


def label_summary(summary: pd.DataFrame) -> pd.DataFrame:
    s = summary.copy()
    s["experiment"] = s["experiment"].fillna("baseline")
    s["Model"] = s["experiment"].map(EXPERIMENT_LABEL).fillna(s["model"])
    s["setting"] = s["setting"].fillna("")
    return s


def main_results(report: Report, summary: pd.DataFrame, split: str):
    s = summary[summary["split"] == split]
    for (res, h), g in s.groupby(["resolution", "horizon"], sort=False):
        naive = g[g["experiment"] == "baseline"]
        models = g[g["experiment"] != "baseline"].sort_values("MAE")
        g = pd.concat([models, naive])
        table = pd.DataFrame({
            "Model": g["Model"].to_numpy(),
            "Setting": g["setting"].to_numpy(),
            "MAE (MWh)": g["MAE"].to_numpy(),
            "MAPE %": g["MAPE_%"].to_numpy(),
            "Error reduction vs naive %": 100 * g["MAE_skill"].to_numpy(),
            "RMSE (MWh)": g["RMSE"].to_numpy(),
            "Pinball (MWh)": g["pinball"].to_numpy(),
            "80 % band coverage %": g["coverage80_%"].to_numpy(),
        })
        best = [0] if len(models) else None
        report.add(f"table1_main_{res}_{h}", f"Table 1. Main results, {horizon_text(res, h)}, {split} year", table,
                   note="Sorted by MAE; the best model is in bold, the benchmark is the last row.", bold_rows=best)


def chosen_setting(sel: dict) -> str:
    c = sel["chosen"]
    parts = []
    if "features" in c:
        parts.append(f"features={c['features']}")
    for key in ("context_length", "context_days"):
        if key in c:
            parts.append(f"ctx={'all' if c[key] is None else c[key]}")
    return " ".join(parts)


def validation_settings(report: Report, summary: pd.DataFrame, selection_path: Path):
    v = summary[(summary["split"] == "val") & (summary["experiment"] != "baseline")].copy()
    if v.empty:
        return
    chosen = {}
    if selection_path.exists():
        for sel in json.loads(selection_path.read_text()).values():
            chosen[(sel["experiment"], int(sel["horizon"]))] = chosen_setting(sel)
    v["Chosen"] = [("yes" if chosen.get((e, int(h))) == st else "") for e, h, st in
                   zip(v["experiment"], v["horizon"], v["setting"])]
    v = v.sort_values(["resolution", "horizon", "experiment", "MAE"], ascending=[False, True, True, True])
    table = pd.DataFrame({
        "Model": v["Model"].to_numpy(),
        "Horizon": [horizon_text(r, h) for r, h in zip(v["resolution"], v["horizon"])],
        "Setting": v["setting"].to_numpy(),
        "MAE (MWh)": v["MAE"].to_numpy(),
        "Pinball (MWh)": v["pinball"].to_numpy(),
        "80 % band coverage %": v["coverage80_%"].to_numpy(),
        "Chosen": v["Chosen"].to_numpy(),
    })
    report.add("table_validation_settings", "Settings compared on the validation year (2023)", table,
               note="Chosen = lowest validation MAE; only the chosen setting was run on the test year.")


# --------------------------------------------------------------------------
# Section 3: day types and lead time
# --------------------------------------------------------------------------


def load_metrics(metrics_dir: Path, files) -> dict[str, dict]:
    out = {}
    for f in files:
        path = metrics_dir / f"{Path(f).stem}.json"
        if path.exists():
            out[Path(f).stem] = json.loads(path.read_text())
        else:
            print(f"[report] note: no metrics file {path.name}, skipped")
    return out


def day_type_table(report: Report, metrics: dict[str, dict]):
    rows = []
    for stem, m in metrics.items():
        if m.get("experiment") in (None, "baseline") and stem.startswith("seasonal_naive"):
            continue  # every model JSON already holds the naive MAE per day type
        info = run_info(stem)
        total = m["overall"]["n"] * m["overall"]["MAE"]
        for dt, d in (m.get("by_day_type") or {}).items():
            if not d:
                continue
            rows.append({
                "Model": info["model"], "Horizon": horizon_text(info["resolution"], info["horizon"]),
                "Day type": DAY_TYPE_LABEL.get(dt, dt), "Hours / days": d["n"],
                "MAE (MWh)": d["MAE"], "MAPE %": d["MAPE_%"], "Naive MAE (MWh)": d["MAE_naive"],
                "Error reduction vs naive %": 100 * d["MAE_skill"],
                "80 % band coverage %": d["coverage80_%"],
                "Share of all error %": 100 * d["n"] * d["MAE"] / total,
            })
    if rows:
        report.add("table3_day_types", "Table 3. Results by day type, test year", pd.DataFrame(rows),
                   note=("Hours / days: hourly runs count hours, daily runs count forecast rows (7 d runs count "
                         "each day once per lead day). Holiday, bridge day and Christmas can overlap, so the "
                         "shares need not add up to 100 %."))


def compare_by_day_type(report: Report, metrics: dict[str, dict], name: str, title: str,
                        pairs: list[tuple[str, str]], note: str):
    """MAE of model A and B per day type, change in % and B's share of the total gain."""
    rows = []
    for a, b in pairs:
        ma, mb = metrics[a], metrics[b]
        ia, ib = run_info(a), run_info(b)
        gain_total = ma["overall"]["n"] * ma["overall"]["MAE"] - mb["overall"]["n"] * mb["overall"]["MAE"]
        for dt in DAY_TYPE_LABEL:
            da, db = (ma.get("by_day_type") or {}).get(dt), (mb.get("by_day_type") or {}).get(dt)
            if not da or not db:
                continue
            gain = da["n"] * (da["MAE"] - db["MAE"])
            rows.append({
                "Horizon": horizon_text(ia["resolution"], ia["horizon"]),
                "Day type": DAY_TYPE_LABEL[dt], "Hours / days": da["n"],
                f"MAE {ia['model']} (MWh)": da["MAE"], f"MAE {ib['model']} (MWh)": db["MAE"],
                "MAE change %": 100 * (db["MAE"] / da["MAE"] - 1),
                f"Coverage {ia['model']} %": da["coverage80_%"], f"Coverage {ib['model']} %": db["coverage80_%"],
                "Share of total gain %": 100 * gain / gain_total if gain_total else np.nan,
            })
    if rows:
        report.add(name, title, pd.DataFrame(rows), note=note)


def lead_time_table(report: Report, metrics: dict[str, dict]):
    rows = []
    for stem, m in metrics.items():
        if not m.get("by_day") or stem.startswith("seasonal_naive"):
            continue
        info = run_info(stem)
        for lead, d in m["by_day"].items():
            rows.append({"Lead day": int(lead), "Model": info["model"], "MAE (MWh)": d["MAE"],
                         "Error reduction vs naive %": 100 * d["MAE_skill"],
                         "80 % band coverage %": d["coverage80_%"]})
    if not rows:
        return
    long = pd.DataFrame(rows)
    wide = long.pivot_table(index="Lead day", columns="Model",
                            values=["MAE (MWh)", "Error reduction vs naive %"], sort=False)
    wide.columns = [f"{v} {m}" for v, m in wide.columns]
    report.add("table_lead_time", "Error by lead day, daily 7 d, test year", wide.reset_index(),
               note="Weather inputs are observed values, so the real decay with weather forecasts is larger.")


def find_pairs(metrics: dict[str, dict]) -> dict[str, list[tuple[str, str]]]:
    """Run pairs for the comparisons: covariate gain and TabICL vs TimesFM-3."""
    by_key = {}
    for stem in metrics:
        info = run_info(stem)
        by_key[(info["model"], info["resolution"], info["horizon"])] = stem
    cov, tab = [], []
    for (model, res, h), stem in sorted(by_key.items(), key=lambda kv: (kv[0][1] != "hourly", kv[0][2])):
        if model == "TimesFM-3, no covariates" and ("TimesFM-3, covariates", res, h) in by_key:
            cov.append((stem, by_key[("TimesFM-3, covariates", res, h)]))
        if model == "TimesFM-3, covariates" and ("TabICL", res, h) in by_key:
            tab.append((stem, by_key[("TabICL", res, h)]))
    return {"cov": cov, "tab": tab}


# --------------------------------------------------------------------------
# Section 4: weather
# --------------------------------------------------------------------------


def weather_tables(report: Report, weather: pd.DataFrame, split: str):
    w = weather[weather["split"] == split] if "split" in weather else weather
    infos = {r: run_info(r) for r in w["run"].unique()}
    w = w.assign(Model=w["run"].map(lambda r: infos[r]["model"]),
                 Horizon=w["run"].map(lambda r: horizon_text(infos[r]["resolution"], infos[r]["horizon"])))
    for var in WEATHER_VARIABLES:
        g = w[w["variable"] == var]
        if g.empty:
            continue
        order = {b: i for i, b in enumerate(WEATHER_ORDER[var])}
        g = g.assign(_o=g["bin"].map(order)).sort_values(["Horizon", "_o", "Model"])
        table = pd.DataFrame({
            "Horizon": g["Horizon"].to_numpy(), "Weather": g["bin"].to_numpy(), "Model": g["Model"].to_numpy(),
            "Days": g["n_days"].to_numpy(), "MAE (MWh)": g["MAE"].to_numpy(),
            "Bias (MWh)": g["bias"].to_numpy(),
            "Error reduction vs naive %": 100 * g["MAE_skill"].to_numpy(),
            "80 % band coverage %": g["coverage80_%"].to_numpy(),
            "Share of all error %": g["share_abs_error_%"].to_numpy(),
        })
        report.add(f"table_weather_{var}", WEATHER_TITLE[var], table,
                   note="Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. "
                        "Hourly MWh per hour, daily MWh per day.")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--metrics-dir", type=Path, default=DEFAULT_METRICS_DIR)
    p.add_argument("--summary", default="summary_foundation.csv", help="summary CSV in the metrics folder")
    p.add_argument("--selection", default="selection_foundation.json", help="selection JSON in the metrics folder")
    p.add_argument("--weather", default="weather_breakdown.csv", help="weather CSV in the metrics folder")
    p.add_argument("--classical", type=Path, nargs="*", default=[], help="extra summary CSVs (other models)")
    p.add_argument("--split", default="test", choices=["val", "test"])
    p.add_argument("--out-dir", type=Path, default=None, help="default: <metrics-dir>/report")
    args = p.parse_args()

    out_dir = args.out_dir or args.metrics_dir / "report"
    report = Report(out_dir)

    summary = pd.read_csv(args.metrics_dir / args.summary)
    for extra in args.classical:
        summary = pd.concat([summary, pd.read_csv(extra)], ignore_index=True)
    summary = label_summary(summary)

    report.section("Section 2. Model comparison")
    main_results(report, summary, args.split)
    validation_settings(report, summary, args.metrics_dir / args.selection)

    report.section("Section 3. Day types")
    test_files = summary.loc[(summary["split"] == args.split), "file"].dropna()
    metrics = load_metrics(args.metrics_dir, test_files)
    day_type_table(report, metrics)
    pairs = find_pairs(metrics)
    compare_by_day_type(report, metrics, "table_covariate_gain_by_day_type",
                        "Covariate gain by day type (TimesFM-3 without vs with covariates)", pairs["cov"],
                        note="Share of total gain: part of the whole-year error reduction that comes from this "
                             "day type.")
    compare_by_day_type(report, metrics, "table_tabicl_vs_timesfm_by_day_type",
                        "TabICL vs TimesFM-3 with covariates, by day type", pairs["tab"],
                        note="Negative MAE change = TabICL is better.")
    lead_time_table(report, metrics)

    weather_path = args.metrics_dir / args.weather
    if weather_path.exists():
        report.section("Section 4. Weather")
        weather_tables(report, pd.read_csv(weather_path), args.split)
    else:
        print(f"[report] note: {weather_path.name} not found, weather tables skipped")

    path = report.write()
    print(f"[report] tables -> {out_dir}\n[report] all tables in one file -> {path}")


if __name__ == "__main__":
    main()