"""
Error of forecast files split by the weather at the target time.

Companion to evaluate.py (same y_true, seasonal naive and day types). By default
only ordinary days are used (normal weekdays and weekends), so that holiday and
Christmas errors are not mistaken for weather errors.

Weather groups (bins are fixed per resolution and evaluation year, so every
model is scored on the same groups):

- ``hdd``: 0 (no heating), then terciles of HDD > 0 -> mild / cool / cold.
- ``hdd_change_vs_last_week``: HDD at the target minus HDD one week before
  (the week the seasonal naive repeats). Heating season only:
  bottom 20 % -> much warmer, top 20 % -> much colder, else similar.
- ``radiation_vs_month``: terciles of shortwave radiation *within each month*
  (dull / average / sunny), so "sunny" does not just mean "summer".
  Hourly: only 10:00 - 15:59 local time, where rooftop PV matters most.
- ``wind``: terciles of wind speed (calm / moderate / windy).
- ``precipitation``: dry / wet (hourly >= 0.1 mm, daily >= 1 mm).
- ``holiday_week`` (calendar, needs the data.py with engineered covariates):
  holiday week / weekend / other weekday, see ``data.ENGINEERED``.

Per group: n, n_days, MAE, bias (mean of y_pred - y_true, > 0 = over-forecast),
seasonal naive MAE, MAE skill, coverage of the 80 % interval and the group's
share of all absolute error.

Hourly files also get local hour x month tables of MAE and bias
(``weather_hour_month_<run>.csv``).

The weather inputs are observed values (variant A), the same values the
covariate models received.

Usage (from the project root):

    uv run python src/analysis/foundation/weather_breakdown.py \
        src/results/forecasts/timesfm3_zs_*_test.csv \
        src/results/forecasts/tabicl_default_*_ctxall_test.csv
"""

from __future__ import annotations

import argparse
import json
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

from models.foundation.data import DEFAULT_DATA_DIR, QUANTILE_COLUMNS, SEASONAL_PERIOD, SPLITS, SeriesFrame, load_frame
from models.foundation.evaluate import DEFAULT_METRICS_DIR, _day_types, fill_y_true

RADIATION = {"hourly": "shortwave_radiation", "daily": "shortwave_radiation_sum"}
WIND = {"hourly": "wind_speed_10m", "daily": "wind_speed_10m_mean"}
RAIN = {"hourly": "precipitation", "daily": "precipitation_sum"}
WET_THRESHOLD = {"hourly": 0.1, "daily": 1.0}  # mm
MIDDAY_HOURS = range(10, 16)  # local 10:00 - 15:59

ORDER = {
    "all": ["all"],
    "hdd": ["0 (no heating)", "mild", "cool", "cold"],
    "hdd_change_vs_last_week": ["no heating either week", "much warmer", "similar", "much colder"],
    "radiation_vs_month": ["dull", "average", "sunny"],
    "wind": ["calm", "moderate", "windy"],
    "precipitation": ["dry", "wet"],
    "holiday_week": ["holiday week", "weekend", "other weekday"],
}


# --------------------------------------------------------------------------
# Weather groups
# --------------------------------------------------------------------------


def _terciles(v: np.ndarray, ref: np.ndarray, labels: list[str]) -> np.ndarray:
    lo, hi = np.nanquantile(v[ref], [1 / 3, 2 / 3])
    lab = np.select([v <= lo, v <= hi], labels[:2], labels[2]).astype(object)
    lab[np.isnan(v)] = None
    return lab


def weather_bins(frame: SeriesFrame, split: str) -> pd.DataFrame:
    """Weather group of every row of ``frame``; thresholds from the evaluation year."""
    df, res = frame.df, frame.resolution
    period = SEASONAL_PERIOD[res]
    year = (frame.local_date.dt.year == SPLITS[split]).to_numpy()
    month = df["month"].to_numpy()
    out = pd.DataFrame(index=df.index)
    out["all"] = "all"

    # Heating degree days: level.
    hdd = df["hdd"].to_numpy(float)
    heat = hdd > 0
    lo, hi = np.quantile(hdd[year & heat], [1 / 3, 2 / 3])
    out["hdd"] = np.select([~heat, hdd <= lo, hdd <= hi], ORDER["hdd"][:3], ORDER["hdd"][3])

    # Heating degree days: change against the week the seasonal naive repeats.
    lag = np.r_[np.full(period, np.nan), hdd[:-period]]
    delta = hdd - lag
    season = heat | (lag > 0)
    q20, q80 = np.nanquantile(delta[year & season], [0.2, 0.8])
    o = ORDER["hdd_change_vs_last_week"]
    lab = np.select([~season, delta <= q20, delta >= q80], [o[0], o[1], o[3]], o[2]).astype(object)
    lab[np.isnan(lag)] = None
    out["hdd_change_vs_last_week"] = lab

    # Radiation relative to the month (hourly: midday hours only).
    rad = df[RADIATION[res]].to_numpy(float)
    if res == "hourly":
        mask = df["date_from"].dt.hour.isin(MIDDAY_HOURS).to_numpy()
    else:
        mask = np.ones(len(df), dtype=bool)
    ref = pd.DataFrame({"r": rad, "m": month})[year & mask]
    q = ref.groupby("m")["r"].quantile([1 / 3, 2 / 3]).unstack()
    r_lo = q.iloc[:, 0].reindex(month).to_numpy()
    r_hi = q.iloc[:, 1].reindex(month).to_numpy()
    o = ORDER["radiation_vs_month"]
    lab = np.select([rad <= r_lo, rad <= r_hi], o[:2], o[2]).astype(object)
    lab[~mask | np.isnan(r_lo)] = None
    out["radiation_vs_month"] = lab

    out["wind"] = _terciles(df[WIND[res]].to_numpy(float), year, ORDER["wind"])
    wet = df[RAIN[res]].to_numpy(float) >= WET_THRESHOLD[res]
    out["precipitation"] = np.where(wet, "wet", "dry")

    # Calendar check of the engineered holiday_week covariate (data.py adds the column).
    if "holiday_week" in df:
        weekend = df["day_of_week_raw"].to_numpy() >= 5
        out["holiday_week"] = np.select([df["holiday_week"].to_numpy() > 0.5, weekend],
                                        ORDER["holiday_week"][:2], ORDER["holiday_week"][2])
    return out


# --------------------------------------------------------------------------
# Forecast rows
# --------------------------------------------------------------------------


def load_rows(path: Path, frames: dict, data_dir: Path) -> tuple[pd.DataFrame, SeriesFrame, str]:
    """Forecast rows with y_true, seasonal naive and the target row position."""
    meta_path = path.with_suffix(".json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    resolution = meta.get("resolution") or ("hourly" if "_hourly_" in path.name else "daily")
    split = meta.get("split") or ("test" if path.stem.endswith("_test") else "val")
    if resolution not in frames:
        frames[resolution] = load_frame(resolution, data_dir)
    frame = frames[resolution]

    fc = fill_y_true(pd.read_csv(path), frame)

    # Row positions, the same way evaluate.py finds the origins.
    pos_of = pd.Series(np.arange(len(frame.df)), index=frame.timestamp.to_numpy())
    origins = fc["origin"].drop_duplicates()
    o_pos = pd.Series(pos_of.loc[pd.to_datetime(origins).to_numpy()].to_numpy(), index=origins.to_numpy())
    p = o_pos.loc[fc["origin"].to_numpy()].to_numpy()
    step = fc["step"].to_numpy()
    fc["tpos"] = p + step - 1
    if not np.allclose(frame.y[fc["tpos"]], fc["y_true"].to_numpy(float)):
        raise ValueError(f"{path.name}: target positions do not match y_true")

    period = SEASONAL_PERIOD[resolution]
    fc["y_naive"] = frame.y[p - period + (step - 1) % period]

    tt = pd.to_datetime(fc["target_time"]) if resolution == "hourly" else fc["target_time"].astype(str)
    types = _day_types(frame, tt)
    fc["ordinary"] = (types["normal_weekday"] | types["weekend"]).to_numpy()
    fc["local_date"] = frame.local_date.iloc[fc["tpos"]].to_numpy()
    if resolution == "hourly":
        fc["local_hour"] = frame.df["date_from"].dt.hour.iloc[fc["tpos"]].to_numpy()
        fc["month"] = frame.df["month"].iloc[fc["tpos"]].to_numpy()
    return fc, frame, split


def group_metrics(g: pd.DataFrame, total_abs_error: float) -> dict:
    y, yp, yn = (g[c].to_numpy(float) for c in ("y_true", "y_pred", "y_naive"))
    err = yp - y
    mae, mae_naive = np.abs(err).mean(), np.abs(yn - y).mean()
    q = g[QUANTILE_COLUMNS].to_numpy(float)
    cov = None if np.isnan(q).all() else 100 * np.mean((y >= q[:, 0]) & (y <= q[:, -1]))
    return {
        "n": len(g),
        "n_days": g["local_date"].nunique(),
        "MAE": mae,
        "bias": err.mean(),
        "MAE_naive": mae_naive,
        "MAE_skill": 1 - mae / mae_naive,
        "coverage80_%": cov,
        "share_abs_error_%": 100 * np.abs(err).sum() / total_abs_error,
    }


def run_names(paths: list[Path]) -> dict[Path, str]:
    """File stem as run name; stems that occur twice (e.g. original vs extra-features
    results) get the results folder appended, e.g. ``..._test [extra_features]``."""
    stems = [p.stem for p in paths]
    names = {}
    for p in paths:
        names[p] = p.stem if stems.count(p.stem) == 1 else f"{p.stem} [{p.resolve().parent.parent.name}]"
    return names


def breakdown(path: Path, frames: dict, bins_cache: dict, data_dir: Path, all_days: bool,
              metrics_dir: Path, run: str | None = None) -> list[dict]:
    run = run or path.stem
    fc, frame, split = load_rows(path, frames, data_dir)
    key = (frame.resolution, split)
    if key not in bins_cache:
        bins_cache[key] = weather_bins(frame, split)
    bins = bins_cache[key].iloc[fc["tpos"].to_numpy()].reset_index(drop=True)

    if not all_days:
        keep = fc["ordinary"].to_numpy()
        fc, bins = fc[keep].reset_index(drop=True), bins[keep].reset_index(drop=True)
    total = np.abs(fc["y_pred"] - fc["y_true"]).sum()

    rows = []
    for var, order in ORDER.items():
        if var not in bins:
            continue
        for label in order:
            m = (bins[var] == label).to_numpy()
            if m.any():
                rows.append({"run": run, "split": split, "resolution": frame.resolution,
                             "variable": var, "bin": label, **group_metrics(fc[m], total)})

    if frame.resolution == "hourly":
        err = fc["y_pred"] - fc["y_true"]
        hm = pd.DataFrame({"hour": fc["local_hour"], "month": fc["month"], "ae": err.abs(), "err": err})
        tables = {
            "MAE": hm.pivot_table(index="hour", columns="month", values="ae", aggfunc="mean"),
            "bias": hm.pivot_table(index="hour", columns="month", values="err", aggfunc="mean"),
        }
        out = pd.concat(tables, axis=1).round(0)
        safe = run.replace(" [", "__").replace("]", "")
        out.to_csv(metrics_dir / f"weather_hour_month_{safe}.csv")
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+", type=Path, help="forecast CSV files")
    p.add_argument("--all-days", action="store_true", help="include holidays, bridge days and Christmas")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--metrics-dir", type=Path, default=DEFAULT_METRICS_DIR)
    p.add_argument("--out", default="weather_breakdown.csv", help="CSV name in the metrics folder")
    args = p.parse_args()

    args.metrics_dir.mkdir(parents=True, exist_ok=True)
    frames, bins_cache, rows = {}, {}, []
    names = run_names(args.files)
    for f in args.files:
        rows += breakdown(f, frames, bins_cache, args.data_dir, args.all_days, args.metrics_dir, names[f])

    table = pd.DataFrame(rows)
    table.to_csv(args.metrics_dir / args.out, index=False)
    cols = ["run", "variable", "bin", "n_days", "MAE", "bias", "MAE_skill", "coverage80_%", "share_abs_error_%"]
    with pd.option_context("display.width", 250, "display.max_rows", 500):
        print(table[cols].round({"MAE": 0, "bias": 0, "MAE_skill": 3, "coverage80_%": 1,
                                 "share_abs_error_%": 1}).to_string(index=False))


if __name__ == "__main__":
    main()