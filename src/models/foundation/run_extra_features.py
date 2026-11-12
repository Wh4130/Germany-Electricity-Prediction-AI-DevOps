"""
Rerun the covariate experiments with the engineered covariates of data.py
(``hdd_delta_7d``, ``pv_proxy``, ``holiday_week``).

Same protocol and options as run_experiments.py (validation 2023, selection,
test 2024), with two differences:

- ``data.EXTRA_FEATURES`` is switched on, so every covariate model gets the
  three extra inputs (F1 / F4 have no covariates and are left out by default),
- results go to ``src/results/extra_features/`` unless ``--results-dir`` is
  given, so the existing forecasts, ``summary_foundation.csv`` and
  ``selection_foundation.json`` are not touched.

Examples (from the project root):

    # only the settings selected before (fastest):
    uv run python src/models/foundation/run_extra_features.py \
        --hourly-contexts 8192 --tabicl-features default --tabicl-contexts all

    # full grid, like the original run:
    uv run python src/models/foundation/run_extra_features.py
"""

from __future__ import annotations

import sys

import data

data.EXTRA_FEATURES = True

import run_experiments  # noqa: E402  (imported after the switch on purpose)


def main() -> None:
    argv = sys.argv[1:]
    if "--experiments" not in argv:
        argv += ["--experiments", "F2", "F5", "F6"]
    if "--results-dir" not in argv:
        argv += ["--results-dir", str(data.DEFAULT_RESULTS_DIR / "extra_features")]
    sys.argv = [sys.argv[0], *argv]
    print(f"[extra] engineered covariates: {data.ENGINEERED}")
    run_experiments.main()


if __name__ == "__main__":
    main()