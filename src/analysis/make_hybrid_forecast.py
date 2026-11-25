"""
The forecast file of the hybrid model for the dashboard: the equal-weight average of TabICL and TimesFM-3 with
covariates, daily forecasts for the next day (h = 1), test year 2024.

The point forecast and every quantile (q0.1 ... q0.9) are averaged over the two models, row by row (same origin and
target time). The average of quantiles is a simple choice; its coverage of the 80% interval is not checked here.

The two models were chosen with the forecasts of the test year (see src/analysis/ensemble_check.py), so the hybrid is
exploratory: it is not an unbiased test result.

    uv run python -m src.analysis.make_hybrid_forecast

Output (shared forecast format, step 1 only), next to the other forecasts of the dashboard:
    deploy/dashboard/public/forecasts/hybrid_daily_1d_test.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.common.paths import RESULTS_DIR, SRC_DIR

ROOT = SRC_DIR.parent
MODELS = {
    "TabICL": "foundation/forecasts/tabicl_default_daily_1d_ctxall_test.csv",
    "TimesFM-3, covariates": "foundation/forecasts/timesfm3_zs_cov_daily_1d_ctxall_test.csv",
}
OUT_DIR = ROOT / "deploy" / "dashboard" / "public" / "forecasts"
OUT_NAME = "hybrid_daily_1d_test"
KEYS = ["origin", "target_time", "step"]
QUANTILES = [f"q0.{i}" for i in range(1, 10)]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = p.parse_args()

    frames = []
    for rel in MODELS.values():
        path = args.results_dir / rel
        if not path.exists():
            raise SystemExit(f"{path} is missing")
        df = pd.read_csv(path)
        missing = [c for c in KEYS + ["y_true", "y_pred"] + QUANTILES if c not in df.columns]
        if missing:
            raise SystemExit(f"{path.name}: no column {missing}")
        if (df["step"] != 1).any():
            raise SystemExit(f"{path.name}: step 1 only, please")
        frames.append(df.set_index(KEYS))

    common = frames[0].index
    for f in frames[1:]:
        common = common.intersection(f.index)
    if not all(len(common) == len(f) for f in frames):
        raise SystemExit("the forecast files do not have the same origins and target times")
    frames = [f.loc[common] for f in frames]
    if not all(frames[0]["y_true"].equals(f["y_true"]) for f in frames[1:]):
        raise SystemExit("y_true differs between the files")

    cols = ["y_pred"] + QUANTILES
    out = frames[0][["y_true"]].copy()
    for c in cols:
        out[c] = sum(f[c] for f in frames) / len(frames)
    out = out[["y_true"] + cols].reset_index().sort_values(["origin", "target_time"])
    if not (out[QUANTILES].diff(axis=1).iloc[:, 1:].fillna(0) >= -1e-6).all().all():
        raise SystemExit("the averaged quantiles are not ordered")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_dir / f"{OUT_NAME}.csv"
    out.to_csv(csv_path, index=False)

    mae = (out["y_pred"] - out["y_true"]).abs().mean()
    rmse = ((out["y_pred"] - out["y_true"]) ** 2).mean() ** 0.5
    cover = ((out["y_true"] >= out["q0.1"]) & (out["y_true"] <= out["q0.9"])).mean() * 100
    print(f"[hybrid] {len(out)} days -> {csv_path}")
    print(f"[hybrid] RMSE {rmse:,.0f}  MAE {mae:,.0f}  80% interval covers {cover:.1f}%")


if __name__ == "__main__":
    main()
