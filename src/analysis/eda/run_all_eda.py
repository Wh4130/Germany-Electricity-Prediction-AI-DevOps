"""
Run every EDA script and write all figures and tables to results/eda/.

    uv run python src/analysis/eda/run_all_eda.py
"""

from __future__ import annotations

import analyze_pv_wind_vs_consumption
import analyze_stationarity
import plot_daily_consumption_trend
import plot_intraday_load_profile_by_season
import plot_monthly_mean_consumption_by_year
import plot_mstl_decomposition
import plot_weekday_effect


def main() -> None:
    plot_daily_consumption_trend.main()
    plot_monthly_mean_consumption_by_year.main()
    plot_weekday_effect.main()
    plot_intraday_load_profile_by_season.main()
    plot_mstl_decomposition.main("daily")
    plot_mstl_decomposition.main("hourly")
    analyze_stationarity.main()
    analyze_pv_wind_vs_consumption.main()


if __name__ == "__main__":
    main()
