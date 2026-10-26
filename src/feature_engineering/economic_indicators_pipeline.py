import argparse
import os
from pathlib import Path

import pandas as pd


class EconomicIndicatorsBuilder:
    """
    Create economic indicator features for the daily / hourly data.

    The builder does no file I/O and never changes its input: `build` returns a new
    DataFrame that only holds the features (same index as the input).
    Each feature is one method that returns a Series.

    The indicators are monthly: every day and every hour gets the value of its month, except the
    industrial confidence, which gets the value of the month before (the survey of a month is
    published at the end of that month, see src/scripts/industrial_confidence_etl.py).

    Done:
    - gas_price_eu_usd
    - industrial_confidence

    Not done: carbon price (EUA), no free source found and the effect on the load is indirect and weak.
    The industrial production index is not a feature here: the energy-intensive production index
    of production_index_pipeline.py (features/ipi_energy_intensive) covers it.
    """

    def __init__(self, gas_price: pd.DataFrame, industrial_confidence: pd.DataFrame) -> None:
        """
        `gas_price`: the file made by src/scripts/gas_price_etl.py (columns month, gas_price_eu_usd)
        `industrial_confidence`: the file made by src/scripts/industrial_confidence_etl.py
        (columns month, industrial_confidence)
        """
        self.gas_price = gas_price.set_index("month")["gas_price_eu_usd"]
        self.industrial_confidence_by_month = industrial_confidence.set_index("month")["industrial_confidence"]

    def build(
        self,
        data: pd.DataFrame
    ) -> pd.DataFrame:
        """ return all economic indicator features of `data` """
        return pd.DataFrame({
            "date_from_utc": data["date_from_utc"],  # the key to merge the features
            "gas_price_eu_usd": self.gas_price_eu_usd(data),
            "industrial_confidence": self.industrial_confidence(data),
        })

    @staticmethod
    def monthly_value(data: pd.DataFrame, monthly: pd.Series, name: str, lag_months: int = 0) -> pd.Series:
        """
        value of the month of every row (`lag_months` = 1: of the month before),
        an error if a month is missing in `monthly`
        """
        months = (data["date_from"].dt.to_period("M") - lag_months).dt.strftime("%Y-%m")
        values = months.map(monthly)

        missing = sorted(set(months[values.isna()]))
        if missing:
            raise ValueError(f"no {name} for the months {missing}")
        return values

    def gas_price_eu_usd(self, data: pd.DataFrame) -> pd.Series:
        """ European natural gas price (IMF, US dollars per MMBtu) of the month """
        return self.monthly_value(data, self.gas_price, "gas price")

    def industrial_confidence(self, data: pd.DataFrame) -> pd.Series:
        """
        German industrial confidence indicator (Eurostat, balance in percentage points) of the month
        before: the survey of a month is published at the end of that month, so a day does not know
        the value of its own month yet
        """
        return self.monthly_value(
            data, self.industrial_confidence_by_month, "industrial confidence", lag_months = 1
        )


def load_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col = 0, parse_dates = ["date_from", "date_to"])


def save_features(features: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents = True, exist_ok = True)
    features.to_csv(path, index = True)  # keep the row index on purpose, it is used to merge features
    print(f"saved {len(features):>6} rows -> {os.path.relpath(path)}")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Create economic indicator features for the daily and hourly data"
    )
    parser.add_argument(
        "--hourlyInput",
        "--hinp",
        type = Path,
        default = ROOT / "src/data/intermin/data_hourly.csv",
        help = "input CSV path for hourly data"
    )
    parser.add_argument(
        "--dailyInput",
        "--dinp",
        type = Path,
        default = ROOT / "src/data/intermin/data_daily.csv",
        help = "input CSV path for daily data"
    )
    parser.add_argument(
        "--gasPriceInput",
        "--gpinp",
        type = Path,
        default = ROOT / "src/data/intermin/gas_price_eu.csv",
        help = "input CSV path for the gas price (made by src/scripts/gas_price_etl.py)"
    )
    parser.add_argument(
        "--industrialConfidenceInput",
        "--icinp",
        type = Path,
        default = ROOT / "src/data/intermin/industrial_confidence.csv",
        help = "input CSV path for the industrial confidence (made by src/scripts/industrial_confidence_etl.py)"
    )
    parser.add_argument(
        "--hourlyOutput",
        "--hout",
        type = Path,
        default = ROOT / "src/data/features/economic_indicators/data_hourly.csv",
        help = "output CSV path for hourly data"
    )
    parser.add_argument(
        "--dailyOutput",
        "--dout",
        type = Path,
        default = ROOT / "src/data/features/economic_indicators/data_daily.csv",
        help = "output CSV path for daily data"
    )

    args = parser.parse_args()

    builder = EconomicIndicatorsBuilder(
        pd.read_csv(args.gasPriceInput),
        pd.read_csv(args.industrialConfidenceInput),
    )

    save_features(builder.build(load_data(args.dailyInput)), args.dailyOutput)
    save_features(builder.build(load_data(args.hourlyInput)), args.hourlyOutput)


if __name__ == "__main__":
    main()
