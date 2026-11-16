"""
Report tables over every model (analysis_plan.md, sections 2 - 4).

Reads only files that exist already, nothing is rerun:

- the metrics JSON of every run (``src/results/<model>/metrics``) -> Table 1
  (main results per horizon), Table 3 (results by day type) and the lead time
  tables,
- ``weather_breakdown.csv`` (from ``src.analysis.weather_breakdown``) ->
  Tables 4 and 5 (temperature change, midday radiation) and the other weather groups.

Model-specific tables (e.g. the validation settings of the foundation models)
live next to the model's analysis, e.g. ``src.analysis.foundation.report_tables``.

Every table is written as CSV (raw numbers) and collected, formatted, in one
``report_tables.md`` in ``src/results/final_report/tables``.

Usage (from the project root):

    uv run python -m src.analysis.report_tables
    uv run python -m src.analysis.report_tables --models foundation sarimax tree-based --split test
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.paths import RESULTS_DIR, TABLES_DIR
from src.analysis.report import Report
from src.analysis.runs import Run, discover_runs, sort_horizons, sort_labels
from src.analysis.weather_breakdown import ORDER as WEATHER_ORDER

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
WEATHER_VARIABLES = ["hdd_change_vs_last_week", "radiation_vs_month", "holiday_week", "hdd", "wind", "precipitation"]


def _pct(v):
    return np.nan if v is None else 100 * v


def load_metrics(runs: list[Run]) -> dict[str, tuple[Run, dict]]:
    """run id -> (run, metrics); runs without a metrics file are skipped with a note."""
    out = {}
    for r in runs:
        m = r.metrics()
        if m is None:
            print(f"[report] note: no metrics for {r.id} (run src.analysis.evaluate), skipped")
            continue
        out[r.id] = (r, m)
    return out


def summary_frame(metrics: dict[str, tuple[Run, dict]]) -> pd.DataFrame:
    """One row per run: identity + overall metrics."""
    rows = []
    for r, m in metrics.values():
        o = m["overall"]
        rows.append({**r.info(), "is_naive": r.is_naive, "Setting": m.get("setting") or "",
                     "Origins": m.get("n_origins"), "MAE": o["MAE"], "RMSE": o["RMSE"], "MAPE_%": o["MAPE_%"],
                     "bias": o.get("bias"), "MAE_skill": o.get("MAE_skill"), "pinball": o.get("pinball"),
                     "coverage80_%": o.get("coverage80_%")})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Section 2: model comparison
# --------------------------------------------------------------------------


def main_results(report: Report, summary: pd.DataFrame, split: str):
    s = summary[summary["split"] == split]
    for hz in sort_horizons(s["Horizon"]):
        g = s[s["Horizon"] == hz]
        naive = g[g["is_naive"]]
        models = g[~g["is_naive"]].sort_values("MAE")
        g = pd.concat([models, naive])
        table = pd.DataFrame({
            "Model": g["Model"].to_numpy(),
            "Results folder": g["model_dir"].to_numpy(),
            "Setting": g["Setting"].to_numpy(),
            "Origins": g["Origins"].to_numpy(),
            "MAE (MWh)": g["MAE"].to_numpy(),
            "MAPE %": g["MAPE_%"].to_numpy(),
            "Error reduction vs naive %": [_pct(v) for v in g["MAE_skill"]],
            "RMSE (MWh)": g["RMSE"].to_numpy(),
            "Bias (MWh)": g["bias"].to_numpy(),
            "Pinball (MWh)": g["pinball"].to_numpy(dtype=float),
            "80 % band coverage %": g["coverage80_%"].to_numpy(dtype=float),
        })
        res, h = g.iloc[0]["resolution"], int(g.iloc[0]["horizon"])
        best = [0] if len(models) else None
        report.add(f"table1_main_{res}_{h}", f"Table 1. Main results, {hz}, {split} year", table,
                   note=("Sorted by MAE; the best model is in bold, the benchmark is the last row. Error reduction "
                         "vs naive is computed on each model's own forecast rows (origins can differ between "
                         "models). Pinball and coverage are empty for point forecasts."), bold_rows=best)


# --------------------------------------------------------------------------
# Section 3: day types and lead time
# --------------------------------------------------------------------------


def day_type_table(report: Report, metrics: dict[str, tuple[Run, dict]]):
    rows = []
    for r, m in metrics.values():
        if r.is_naive:
            continue  # every model JSON already holds the naive MAE per day type
        total = m["overall"]["n"] * m["overall"]["MAE"]
        for dt, d in (m.get("by_day_type") or {}).items():
            if not d:
                continue
            rows.append({
                "Model": r.label, "Horizon": r.horizon_text,
                "Day type": DAY_TYPE_LABEL.get(dt, dt), "Hours / days": d["n"],
                "MAE (MWh)": d["MAE"], "MAPE %": d["MAPE_%"], "Naive MAE (MWh)": d["MAE_naive"],
                "Error reduction vs naive %": _pct(d["MAE_skill"]),
                "80 % band coverage %": d.get("coverage80_%"),
                "Share of all error %": 100 * d["n"] * d["MAE"] / total,
            })
    if rows:
        report.add("table3_day_types", "Table 3. Results by day type", pd.DataFrame(rows),
                   note=("Hours / days: forecast rows whose target falls on that day type (multi-step runs count "
                         "a target once per step). Holiday, bridge day and Christmas can overlap, so the shares "
                         "need not add up to 100 %."))


def compare_by_day_type(report: Report, metrics: dict[str, tuple[Run, dict]], name: str, title: str,
                        pairs: list[tuple[str, str]], note: str):
    """MAE of run A and B per day type, change in % and the share of the total gain (any two runs)."""
    rows = []
    for a, b in pairs:
        (ra, ma), (rb, mb) = metrics[a], metrics[b]
        gain_total = ma["overall"]["n"] * ma["overall"]["MAE"] - mb["overall"]["n"] * mb["overall"]["MAE"]
        for dt in DAY_TYPE_LABEL:
            da, db = (ma.get("by_day_type") or {}).get(dt), (mb.get("by_day_type") or {}).get(dt)
            if not da or not db:
                continue
            gain = da["n"] * (da["MAE"] - db["MAE"])
            rows.append({
                "Horizon": ra.horizon_text,
                "Day type": DAY_TYPE_LABEL[dt], "Hours / days": da["n"],
                f"MAE {ra.label} (MWh)": da["MAE"], f"MAE {rb.label} (MWh)": db["MAE"],
                "MAE change %": 100 * (db["MAE"] / da["MAE"] - 1),
                f"Coverage {ra.label} %": da.get("coverage80_%"), f"Coverage {rb.label} %": db.get("coverage80_%"),
                "Share of total gain %": 100 * gain / gain_total if gain_total else np.nan,
            })
    if rows:
        report.add(name, title, pd.DataFrame(rows), note=note)


def lead_time_tables(report: Report, metrics: dict[str, tuple[Run, dict]]):
    rows = []
    for r, m in metrics.values():
        if r.is_naive:
            continue
        for unit in ("day", "week"):
            for lead, d in (m.get(f"by_{unit}") or {}).items():
                rows.append({"Horizon": r.horizon_text, "unit": unit, "Lead": int(lead), "Model": r.label,
                             "MAE (MWh)": d["MAE"], "Error reduction vs naive %": _pct(d["MAE_skill"])})
    if not rows:
        return
    long = pd.DataFrame(rows)
    for hz in sort_horizons(long["Horizon"]):
        g = long[long["Horizon"] == hz]
        unit = g["unit"].iloc[0]
        models = sort_labels(g["Model"])
        wide = g.pivot_table(index="Lead", columns="Model", values=["MAE (MWh)", "Error reduction vs naive %"])
        wide = wide[[(v, m) for v in ("MAE (MWh)", "Error reduction vs naive %") for m in models]]
        wide.columns = [f"{v} {m}" for v, m in wide.columns]
        wide = wide.reset_index().rename(columns={"Lead": f"Lead {unit}"})
        report.add(f"table_lead_time_{hz.replace(' ', '_')}", f"Error by lead {unit}, {hz}", wide,
                   note="Weather inputs are observed values, so the real decay with weather forecasts is larger.")


# --------------------------------------------------------------------------
# Section 4: weather
# --------------------------------------------------------------------------


def weather_tables(report: Report, weather: pd.DataFrame, split: str):
    w = weather[weather["split"] == split] if "split" in weather else weather
    for var in WEATHER_VARIABLES:
        g = w[w["variable"] == var]
        if g.empty:
            continue
        order = {b: i for i, b in enumerate(WEATHER_ORDER[var])}
        hz_order = {h: i for i, h in enumerate(sort_horizons(g["Horizon"]))}
        m_order = {m: i for i, m in enumerate(sort_labels(g["Model"]))}
        g = g.assign(_h=g["Horizon"].map(hz_order), _o=g["bin"].map(order), _m=g["Model"].map(m_order))
        g = g.sort_values(["_h", "_o", "_m"])
        table = pd.DataFrame({
            "Horizon": g["Horizon"].to_numpy(), "Weather": g["bin"].to_numpy(), "Model": g["Model"].to_numpy(),
            "Days": g["n_days"].to_numpy(), "MAE (MWh)": g["MAE"].to_numpy(),
            "Bias (MWh)": g["bias"].to_numpy(),
            "Error reduction vs naive %": 100 * g["MAE_skill"].to_numpy(),
            "80 % band coverage %": g["coverage80_%"].to_numpy(dtype=float),
            "Share of all error %": g["share_abs_error_%"].to_numpy(),
        })
        report.add(f"table_weather_{var}", WEATHER_TITLE[var], table,
                   note="Bias = forecast minus actual: positive = over-forecast, negative = under-forecast. "
                        "Hourly MWh per hour, daily MWh per day.")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def build(runs: list[Run], split: str = "test", out_dir: Path = TABLES_DIR,
          weather_name: str = "weather_breakdown.csv") -> Path:
    report = Report(out_dir, title=f"Report tables ({split} year)")
    metrics = load_metrics([r for r in runs if r.split == split])
    if not metrics:
        raise SystemExit(f"[report] no metrics for any {split} run: run `python -m src.analysis.evaluate` first")

    report.section("Section 2. Model comparison")
    main_results(report, summary_frame(metrics), split)

    report.section("Section 3. Day types and lead time")
    day_type_table(report, metrics)
    lead_time_tables(report, metrics)

    weather_path = Path(out_dir) / weather_name
    if weather_path.exists():
        report.section("Section 4. Weather")
        weather_tables(report, pd.read_csv(weather_path), split)
    else:
        print(f"[report] note: {weather_path.name} not found, weather tables skipped "
              "(run `python -m src.analysis.weather_breakdown`)")

    path = report.write()
    print(f"[report] {report.n_tables} tables -> {out_dir}\n[report] all tables in one file -> {path}")
    return path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--models", nargs="+", default=None, help="results folders (default: all)")
    p.add_argument("--split", default="test", choices=["val", "test"])
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--out-dir", type=Path, default=TABLES_DIR)
    p.add_argument("--weather", default="weather_breakdown.csv", help="weather CSV in the output folder")
    args = p.parse_args()
    build(discover_runs(args.results_dir, args.models, args.split), args.split, args.out_dir, args.weather)


if __name__ == "__main__":
    main()