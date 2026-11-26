"""
Finding and naming the runs that the analysis works on.

A *run* is one forecast file ``src/results/<model>/forecasts/<stem>.csv`` (+ its
JSON sidecar); its metrics are ``src/results/<model>/metrics/<stem>.json``
(written by ``src.analysis.evaluate``). Every model that writes its forecasts
there in the shared format is picked up, nothing here is model-specific
except the display names below.

Display name (``Run.label``), first match wins:
1. ``"label"`` in the JSON sidecar (a new model can name itself this way),
2. ``LABEL_RULES``: a regular expression on the file name,
3. ``"model"`` in the sidecar, else the results folder name.
A results folder in ``MODEL_DIR_SUFFIX`` appends a suffix (e.g. the reruns
with the extra features), so a label stays unique across folders.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.common.dataset import horizon_text, read_meta
from src.common.paths import NAIVE_MODEL, NOT_MODELS, RESULTS_DIR, metrics_path_of, model_of

NAIVE_LABEL = "Seasonal naive"

LABEL_RULES: list[tuple[str, str]] = [
    (r"^seasonal_naive", NAIVE_LABEL),
    (r"^timesfm3_.*_nocov_", "TimesFM-3, no covariates"),
    (r"^timesfm3_", "TimesFM-3, covariates"),
    (r"^tabicl", "TabICL"),
    (r"^sarimax", "SARIMAX"),
    (r"^tree", "Tree-based"),
]
MODEL_DIR_SUFFIX = {"foundation_extra_features": " + extra features"}

# Fixed display order of the known models (others follow alphabetically).
MODEL_ORDER = ["TimesFM-3, covariates", "TimesFM-3, no covariates", "TabICL", "SARIMAX", "Tree-based"]
HORIZON_ORDER = ["hourly 1 h", "hourly 24 h", "daily 1 d", "daily 7 d"]


def label_of(stem: str, meta: dict, model_dir: str) -> str:
    label = meta.get("label")
    if not label:
        label = next((lab for pattern, lab in LABEL_RULES if re.search(pattern, stem)), None)
    if not label:
        label = meta.get("model") or model_dir
    return label + MODEL_DIR_SUFFIX.get(model_dir, "")


def sort_labels(labels) -> list[str]:
    """Known models in ``MODEL_ORDER`` (each followed by its variants), then the rest alphabetically."""
    def key(lab: str):
        base = next((i for i, m in enumerate(MODEL_ORDER) if lab == m or lab.startswith(m + " +")), len(MODEL_ORDER))
        return (base, lab)
    return sorted(set(labels), key=key)


def sort_horizons(horizons) -> list[str]:
    hs = set(horizons)
    return [h for h in HORIZON_ORDER if h in hs] + sorted(hs - set(HORIZON_ORDER))


@dataclass
class Run:
    forecast_path: Path
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        self.forecast_path = Path(self.forecast_path)
        if not self.meta:
            self.meta = read_meta(self.forecast_path)
        stem = self.stem
        m = re.search(r"_(hourly|daily)_(\d+)(h|d)_", f"_{stem}_")
        self.resolution = self.meta.get("resolution") or (m.group(1) if m else
                                                          "hourly" if "_hourly_" in stem else "daily")
        horizon = self.meta.get("horizon") or (int(m.group(2)) if m else None)
        if horizon is None:  # last resort: the largest step in the file
            horizon = int(pd.read_csv(self.forecast_path, usecols=["step"])["step"].max())
        self.horizon = int(horizon)
        self.split = self.meta.get("split") or ("test" if stem.endswith("_test") else
                                                "val" if stem.endswith("_val") else "test")
        self.model_dir = model_of(self.forecast_path)
        self.label = label_of(stem, self.meta, self.model_dir)

    @property
    def stem(self) -> str:
        return self.forecast_path.stem

    @property
    def id(self) -> str:
        """Unique name of the run: ``<model folder>/<file stem>``."""
        return f"{self.model_dir}/{self.stem}"

    @property
    def safe_id(self) -> str:
        """``id`` usable in a file name."""
        return self.id.replace("/", "__")

    @property
    def horizon_text(self) -> str:
        return horizon_text(self.resolution, self.horizon)

    @property
    def display(self) -> str:
        return f"{self.label} ({self.horizon_text})"

    @property
    def is_naive(self) -> bool:
        return self.label == NAIVE_LABEL

    @property
    def metrics_path(self) -> Path:
        return metrics_path_of(self.forecast_path)

    def metrics(self) -> dict | None:
        p = self.metrics_path
        return json.loads(p.read_text()) if p.exists() else None

    def info(self) -> dict:
        """The columns that identify a run in every analysis table."""
        return {"run": self.id, "model_dir": self.model_dir, "Model": self.label, "resolution": self.resolution,
                "horizon": self.horizon, "Horizon": self.horizon_text, "split": self.split}


def _is_forecast_file(path: Path) -> bool:
    try:
        cols = set(pd.read_csv(path, nrows=0).columns)
    except Exception:  # noqa: BLE001 - unreadable file: not a forecast file
        return False
    return {"origin", "target_time", "step", "y_pred"} <= cols


def discover_runs(results_dir: Path = RESULTS_DIR, models: list[str] | None = None,
                  split: str | None = "test", include_naive: bool = True) -> list[Run]:
    """Every forecast file under ``results/<model>/forecasts`` (sorted by model folder and name).

    models : only these results folders (default: all except ``final_report``).
    split : only runs of this split ("val" / "test"); None for all.
    """
    results_dir = Path(results_dir)
    runs = []
    for mdir in sorted(p for p in results_dir.iterdir() if p.is_dir() and p.name not in NOT_MODELS):
        if models is not None and mdir.name not in models and not (include_naive and mdir.name == NAIVE_MODEL):
            continue
        for path in sorted((mdir / "forecasts").glob("*.csv")):
            if not _is_forecast_file(path):
                print(f"[runs] note: {path} is not in the forecast format, skipped")
                continue
            run = Run(path)
            if split is not None and run.split != split:
                continue
            if run.is_naive and not include_naive:
                continue
            runs.append(run)
    return runs


def runs_from_paths(paths) -> list[Run]:
    return [Run(Path(p)) for p in paths]


def check_unique_labels(runs: list[Run]) -> None:
    """Warn when two runs of the same horizon and split share a display name."""
    seen: dict[tuple, str] = {}
    for r in runs:
        key = (r.label, r.resolution, r.horizon, r.split)
        if key in seen:
            print(f"[runs] note: {r.id} and {seen[key]} are both shown as '{r.display}'; "
                  "set 'label' in a JSON sidecar or MODEL_DIR_SUFFIX to tell them apart")
        seen[key] = r.id