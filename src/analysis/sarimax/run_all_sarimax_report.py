"""
Build the SARIMAX figure and tables of the report into results/sarimax/report/.

    uv run python src/analysis/sarimax/run_all_sarimax_report.py
"""

from __future__ import annotations

import make_sarimax_coefficients_table
import make_sarimax_hourly_test_metrics_table
import make_sarimax_hourly_validation_table
import make_sarimax_test_metrics_table
import make_sarimax_validation_table
import plot_sarimax_forecast_vs_actual
import plot_sarimax_hourly_forecast_vs_actual


def main() -> None:
    make_sarimax_validation_table.main()
    plot_sarimax_forecast_vs_actual.main()
    make_sarimax_coefficients_table.main()
    make_sarimax_test_metrics_table.main()
    make_sarimax_hourly_validation_table.main()
    plot_sarimax_hourly_forecast_vs_actual.main()
    make_sarimax_hourly_test_metrics_table.main()


if __name__ == "__main__":
    main()
