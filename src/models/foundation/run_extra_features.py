"""
Rerun the covariate experiments with the engineered covariates
(``hdd_delta_7d``, ``pv_proxy``, ``holiday_week``).

Same protocol and options as run_experiments.py (validation 2023, selection,
test 2024), with two differences:

- ``data.EXTRA_FEATURES`` is switched on, so every covariate model gets the
  three extra inputs (F1 / F4 have no covariates and are left out by default),
- results go to ``src/results/foundation_extra_features/`` unless
  ``--results-dir`` is given, so the existing forecasts, ``summary_foundation.csv``
  and ``selection_foundation.json`` are not touched.

The same as ``run_experiments --extra-features``; kept as a shortcut.

Examples (from the project root):

    # only the settings selected before (fastest):
    uv run python -m src.models.foundation.run_extra_features \\
        --hourly-contexts 8192 --tabicl-features default --tabicl-contexts all

    # full grid, like the original run:
    uv run python -m src.models.foundation.run_extra_features
"""

from __future__ import annotations

from src.models.foundation import run_experiments


def main(argv: list[str] | None = None) -> None:
    run_experiments.main(argv, extra_features=True)


if __name__ == "__main__":
    main()