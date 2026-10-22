"""
Merge the outputs of oxcgrt_pipeline.py and production_index_pipeline.py into one feature file.

    features/policy/oxcgrt_{daily,hourly}.csv
    features/policy/ipi_energy_intensive_{daily,hourly}.csv
        -> features/policy/data_daily.csv, features/policy/data_hourly.csv

Those two pipelines are not changed. Their files have `date` (daily) or `datetime_from` (hourly, with
time zone) and `date` instead of `date_from_utc`, so this step makes `date_from_utc` from them and
writes the files in the format of the other features.
The production index of the main variant is used (aligned to the release date), not the `refmonth` files:
they are an ablation that uses figures before they were published.

Run (from the project root)
    uv run python src/feature_engineering/policy_pipeline.py
"""
import argparse
import os
from pathlib import Path

import pandas as pd

SOURCES = ("oxcgrt", "ipi_energy_intensive")
TIMEZONE = "Europe/Berlin"


class PolicyFeatureBuilder:
    """
    Put the policy files into one DataFrame with `date_from_utc` and all their feature columns.

    The builder does no file I/O and never changes its input.
    """

    @staticmethod
    def date_from_utc(part: pd.DataFrame) -> pd.Series:
        """ `date_from_utc` like in intermin/: UTC, written without a time zone """
        if "datetime_from" in part.columns:
            # hourly: "2019-01-01T00:00:00+01:00" has the offset, so also the repeated 02:00 is exact
            return pd.to_datetime(part["datetime_from"], utc = True).dt.tz_localize(None)
        # daily: the date is the local midnight
        local = pd.to_datetime(part["date"])
        return local.dt.tz_localize(TIMEZONE).dt.tz_convert("UTC").dt.tz_localize(None)

    def build(self, parts: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """ all columns of `parts` next to each other, an error if the parts do not fit together """
        first_name = next(iter(parts))
        first = parts[first_name]
        date_from_utc = self.date_from_utc(first)

        features = []
        for name, part in parts.items():
            if not part.index.equals(first.index):
                raise ValueError(f"{name}: the row index differs from {first_name}")
            if not self.date_from_utc(part).equals(date_from_utc):
                raise ValueError(f"{name}: the dates differ from {first_name}")
            features.append(part.drop(columns = ["date", "datetime_from"], errors = "ignore"))

        merged = pd.concat(features, axis = 1)
        duplicated = sorted(set(merged.columns[merged.columns.duplicated()]))
        if duplicated:
            raise ValueError(f"column names used twice: {duplicated}")

        merged.insert(0, "date_from_utc", date_from_utc)
        return merged


def load_part(directory: Path, source: str, frequency: str) -> pd.DataFrame:
    return pd.read_csv(directory / f"{source}_{frequency}.csv", index_col = 0)


def save_features(features: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents = True, exist_ok = True)
    features.to_csv(path, index = True)  # keep the row index on purpose, it is used to merge features
    print(f"saved {len(features):>6} rows -> {os.path.relpath(path)}")


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Merge the OxCGRT and production index files into one policy feature file"
    )
    parser.add_argument(
        "--inputDirectory",
        "--idir",
        type = Path,
        default = ROOT / "src/data/features/policy",
        help = "directory with the files of oxcgrt_pipeline.py and production_index_pipeline.py"
    )
    parser.add_argument(
        "--hourlyOutput",
        "--hout",
        type = Path,
        default = ROOT / "src/data/features/policy/data_hourly.csv",
        help = "output CSV path for hourly data"
    )
    parser.add_argument(
        "--dailyOutput",
        "--dout",
        type = Path,
        default = ROOT / "src/data/features/policy/data_daily.csv",
        help = "output CSV path for daily data"
    )

    args = parser.parse_args()

    builder = PolicyFeatureBuilder()
    for frequency, output in [("daily", args.dailyOutput), ("hourly", args.hourlyOutput)]:
        parts = {source: load_part(args.inputDirectory, source, frequency) for source in SOURCES}
        save_features(builder.build(parts), output)


if __name__ == "__main__":
    main()
