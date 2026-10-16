"""
Merge all features onto the cleaned SMARD data -> src/data/final/data_daily.csv, data_hourly.csv

Base:      src/data/intermin/data_daily.csv, data_hourly.csv
Features:  every src/data/features/<feature>/data_daily.csv (and data_hourly.csv when the feature has one)
           The feature folders are found automatically, a new feature needs no change in this file.
           A feature without a file for a frequency (e.g. a daily-only feature in the hourly data, or a
           folder that only has a .gitkeep) is skipped, the skip is printed.

The files are joined by the row index (it is kept in every file on purpose). The merge stops with an error when
    - the row index of a feature file differs from the base data (rows dropped or reordered), or
    - a column name already exists (two features with the same column name).

Run (from the project root)
    uv run python src/pipelines/merge_all.py
"""
import argparse
import os
from pathlib import Path

import pandas as pd


def merge(base: pd.DataFrame, features_directory: Path, frequency: str) -> pd.DataFrame:
    merged = base
    used, skipped = [], []
    for folder in sorted(p for p in features_directory.iterdir() if p.is_dir()):
        path = folder / f"data_{frequency}.csv"
        if not path.exists():
            skipped.append(folder.name)
            continue

        features = pd.read_csv(path, index_col = 0)

        if not features.index.equals(base.index):
            raise ValueError(f"{path}: the row index differs from the base data")

        overlap = set(features.columns) & set(merged.columns)
        if overlap:
            raise ValueError(f"{path}: column names already exist: {sorted(overlap)}")

        merged = merged.join(features)
        used.append(f"{folder.name} ({len(features.columns)} columns)")

    print(f"{frequency:<7} merged: {', '.join(used) or '-'} | skipped (no {frequency} file): {', '.join(skipped) or '-'}")
    return merged


def main():
    ROOT = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description = "Merge the cleaned SMARD data and all features into the final data"
    )
    parser.add_argument(
        "--hourlyInput",
        "--hinp",
        type = Path,
        default = ROOT / "src/data/intermin/data_hourly.csv",
        help = "base CSV path for hourly data"
    )
    parser.add_argument(
        "--dailyInput",
        "--dinp",
        type = Path,
        default = ROOT / "src/data/intermin/data_daily.csv",
        help = "base CSV path for daily data"
    )
    parser.add_argument(
        "--featuresDirectory",
        "--fdir",
        type = Path,
        default = ROOT / "src/data/features",
        help = "directory with one sub-folder per feature"
    )
    parser.add_argument(
        "--outputDirectory",
        "--odir",
        type = Path,
        default = ROOT / "src/data/final",
        help = "output directory"
    )
    args = parser.parse_args()

    args.outputDirectory.mkdir(parents = True, exist_ok = True)
    for frequency, base_path in [("daily", args.dailyInput), ("hourly", args.hourlyInput)]:
        base = pd.read_csv(base_path, index_col = 0)

        merged = merge(base, args.featuresDirectory, frequency)

        out_path = args.outputDirectory / f"data_{frequency}.csv"
        merged.to_csv(out_path, index = True)  # keep the row index, like every other file
        print(f"{frequency:<7} saved {len(merged):>6} rows x {len(merged.columns)} columns -> {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
