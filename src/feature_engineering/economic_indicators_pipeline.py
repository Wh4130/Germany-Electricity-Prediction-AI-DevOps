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

    The indicators are monthly: every day and every hour gets the value of its month.

    Done:
    - industrial_production_index
    - gas_price_eu_usd

    Not done: carbon price (EUA), no free source found and the effect on the load is indirect and weak.
    """

    def __init__(self, industrial_production: pd.DataFrame, gas_price: pd.DataFrame) -> None:
        """
        `industrial_production`: the file made by src/scripts/industrial_production_etl.py
        (columns month, industrial_production_index)
        `gas_price`: the file made by src/scripts/gas_price_etl.py (columns month, gas_price_eu_usd)
        """
        self.industrial_production = industrial_production.set_index("month")["industrial_production_index"]
        self.gas_price = gas_price.set_index("month")["gas_price_eu_usd"]

    def build(
        self,
        data: pd.DataFrame
    ) -> pd.DataFrame:
        """ return all economic indicator features of `data` """
        return pd.DataFrame({
            "industrial_production_index": self.industrial_production_index(data),
            "gas_price_eu_usd": self.gas_price_eu_usd(data),
        })

    @staticmethod
    def monthly_value(data: pd.DataFrame, monthly: pd.Series, name: str) -> pd.Series:
        """ value of the month of every row, an error if a month is missing in `monthly` """
        months = data["date_from"].dt.strftime("%Y-%m")
        values = months.map(monthly)

        missing = sorted(set(months[values.isna()]))
        if missing:
            raise ValueError(f"no {name} for the months {missing}")
        return values

    def industrial_production_index(self, data: pd.DataFrame) -> pd.Series:
        """ German industrial production index (2021 = 100, seasonally adjusted) of the month """
        return self.monthly_value(data, self.industrial_production, "industrial production index")

    def gas_price_eu_usd(self, data: pd.DataFrame) -> pd.Series:
        """ European natural gas price (IMF, US dollars per MMBtu) of the month """
        return self.monthly_value(data, self.gas_price, "gas price")


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
        "--industrialProductionInput",
        "--ipinp",
        type = Path,
        default = ROOT / "src/data/intermin/industrial_production.csv",
        help = "input CSV path for the industrial production index (made by src/scripts/industrial_production_etl.py)"
    )
    parser.add_argument(
        "--gasPriceInput",
        "--gpinp",
        type = Path,
        default = ROOT / "src/data/intermin/gas_price_eu.csv",
        help = "input CSV path for the gas price (made by src/scripts/gas_price_etl.py)"
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
        pd.read_csv(args.industrialProductionInput),
        pd.read_csv(args.gasPriceInput),
    )

    save_features(builder.build(load_data(args.dailyInput)), args.dailyOutput)
    save_features(builder.build(load_data(args.hourlyInput)), args.hourlyOutput)


if __name__ == "__main__":
    main()
