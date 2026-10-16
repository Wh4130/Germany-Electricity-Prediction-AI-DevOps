import argparse
import os
from pathlib import Path

import pandas as pd

# SMARD (German) column name -> English column name
COLUMN_MAP = {
    "Datum von": "date_from",
    "Datum bis": "date_to",
    "Netzlast [MWh] Berechnete Auflösungen": "actual_consumption",
    "Netzlast inkl. Pumpspeicher [MWh] Berechnete Auflösungen": "actual_consumption_incl_pumped",
    "Pumpspeicher [MWh] Berechnete Auflösungen": "hydro_pumped_storage",
    "Residuallast [MWh] Berechnete Auflösungen": "residual_load",
}


class RawDataCleanser:
    """Rename the SMARD columns and parse the date columns of the raw exports."""

    @staticmethod
    def _clean(file_path: Path) -> pd.DataFrame:
        # load data (SMARD format: `;` separated, `,` decimal, `.` thousands)
        df = pd.read_csv(
            file_path,
            delimiter = ';',
            decimal = ',',
            thousands = '.',
            dtype = {"Datum von": str, "Datum bis": str}
        )

        # rename column
        df = df.rename(columns = COLUMN_MAP)

        # to datetime
        df["date_from"] = pd.to_datetime(df["date_from"], dayfirst = True)
        df["date_to"] = pd.to_datetime(df["date_to"], dayfirst = True)

        return df

    @staticmethod
    def clean_hourly_data(
        filePath: Path
    ) -> pd.DataFrame:
        return RawDataCleanser._clean(filePath)

    @staticmethod
    def clean_daily_data(
        filePath: Path
    ) -> pd.DataFrame:
        return RawDataCleanser._clean(filePath)


def check_consumption_identity(df: pd.DataFrame, name: str) -> None:
    """actual_consumption + hydro_pumped_storage should equal actual_consumption_incl_pumped."""
    gap = (
        df["actual_consumption"] + df["hydro_pumped_storage"] - df["actual_consumption_incl_pumped"]
    ).abs().max()
    if gap > 1e-3:
        print(f"warning [{name}]: actual_consumption + hydro_pumped_storage != actual_consumption_incl_pumped (max gap {gap:.3f})")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Rename columns and transform date format for source datasets"
    )
    parser.add_argument(
        "--hourlyInput",
        "--hinp",
        type = Path,
        default = ROOT / "src/data/raw/Realisierter_Stromverbrauch_201901010000_202501010000_Stunde.csv",
        help = "input CSV path for hourly data"
    )
    parser.add_argument(
        "--dailyInput",
        "--dinp",
        type = Path,
        default = ROOT / "src/data/raw/Realisierter_Stromverbrauch_201901010000_202501010000_Tag.csv",
        help = "input CSV path for daily data"
    )
    parser.add_argument(
        "--outputDirectory",
        "--odir",
        type = Path,
        default = ROOT / "src/data/intermin",
        help = "output directory"
    )
    parser.add_argument(
        "--hourlyOutputFilename",
        "--honame",
        type = str,
        default = "data_hourly.csv",
        help = "output filename for hourly data"
    )
    parser.add_argument(
        "--dailyOutputFilename",
        "--doname",
        type = str,
        default = "data_daily.csv",
        help = "output filename for daily data"
    )

    args = parser.parse_args()

    df_hour = RawDataCleanser.clean_hourly_data(args.hourlyInput)
    df_day = RawDataCleanser.clean_daily_data(args.dailyInput)

    check_consumption_identity(df_hour, "hourly")
    check_consumption_identity(df_day, "daily")

    args.outputDirectory.mkdir(parents = True, exist_ok = True)
    for df, filename in [
        (df_hour, args.hourlyOutputFilename),
        (df_day, args.dailyOutputFilename),
    ]:
        out_path = args.outputDirectory / filename
        df.to_csv(out_path, index = True)  # keep the row index on purpose, it is used later to merge features
        print(f"saved {len(df):>6} rows -> {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
