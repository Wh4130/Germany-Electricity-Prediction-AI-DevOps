"""
Run the whole data flow, in order, with the default paths of every step.

    1. src/feature_engineering/cleansing.py, cleansing_generation.py     raw -> intermin
    2. one step per feature group (intermin -> features/<group>), see FEATURES below:
         - the feature files exist (and have date_from_utc) -> skip the step (nothing is downloaded or built)
         - they do not, the downloaded files exist    -> run the pipeline
         - they do not, a downloaded file is missing  -> run its download script (src/scripts/*_etl.py)
                                                         first, then the pipeline
    3. src/feature_engineering/merge_all.py               intermin + features -> final

The downloads are big or slow (the weather ~40 MB, the MaStR export 3 GB), so they only run when
there is no other way to get the feature files.

Run (from the project root)
    uv run python src/feature_engineering/main.py
    uv run python src/feature_engineering/main.py --rebuild         # build the features again, even if their files exist
    uv run python src/feature_engineering/main.py --forceDownload   # download again (and build the features again)

With --forceDownload a failed download (e.g. HTTP 429 of ferien-api.de) is not an error as long as
the old file exists: the old file is kept and the run goes on.
Each step is a normal script, so it can still be run alone with its own arguments (--help).
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BEFORE = [
    "src/feature_engineering/cleansing.py",
    "src/feature_engineering/cleansing_generation.py",
]

# merge_all.py is always the last one: it merges intermin and all features
AFTER = [
    "src/feature_engineering/merge_all.py",
]

FEATURES_DIRECTORY = "src/data/features"

# One row per feature group: (name, pipeline, downloads)
# downloads: (name, script, file) the pipeline needs. The script only runs when the file is missing.
FEATURES = [
    (
        "calendar",
        "src/feature_engineering/calendar_pipeline.py",
        [
            ("school holidays", "src/scripts/school_holidays_etl.py", "src/data/intermin/school_holidays.csv"),
            ("population", "src/scripts/population_etl.py", "src/data/intermin/population_by_land.csv"),
        ],
    ),
    (
        "fourier",
        "src/feature_engineering/fourier_pipeline.py",
        [],
    ),
    (
        "economic_indicators",
        "src/feature_engineering/economic_indicators_pipeline.py",
        [
            ("gas price", "src/scripts/gas_price_etl.py", "src/data/intermin/gas_price_eu.csv"),
            (
                "industrial confidence",
                "src/scripts/industrial_confidence_etl.py",
                "src/data/intermin/industrial_confidence.csv",
            ),
        ],
    ),
    (
        "electricity_price",
        "src/feature_engineering/electricity_price_pipeline.py",
        [("day-ahead price", "src/scripts/day_ahead_price_etl.py", "src/data/intermin/day_ahead_price.csv")],
    ),
    (
        "generation",
        "src/feature_engineering/generation_pipeline.py",
        [],
    ),
    (
        "weather",
        "src/feature_engineering/weather_pipeline.py",
        [("weather", "src/scripts/weather_etl.py", "src/data/intermin/weather_daily_by_city.csv")],
    ),
    (
        "mastr",
        "src/feature_engineering/mastr_pipeline.py",
        [("mastr solar", "src/scripts/mastr_etl.py", "src/data/intermin/mastr_solar.csv")],
    ),
    (
        "policy",
        "src/feature_engineering/policy_pipeline.py",
        [],
    ),
]


TOTAL_STEPS = len(BEFORE) + len(FEATURES) + len(AFTER)
LABEL_WIDTH = max(
    [len(name) for name, _, _ in FEATURES]
    + [len(Path(script).stem) for script in BEFORE + AFTER]
)


def header(step: int, label: str, status: str) -> None:
    print(f"[{step}/{TOTAL_STEPS}] {label:<{LABEL_WIDTH}} {status}")


def run(script: str) -> None:
    """ run a script, its output is shown indented below the step line """
    start = time.perf_counter()
    process = subprocess.Popen(
        [sys.executable, str(ROOT / script)],
        cwd = ROOT,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        text = True,
    )
    for line in process.stdout:
        print(f"      {line.rstrip()}")
    if process.wait() != 0:
        raise subprocess.CalledProcessError(process.returncode, process.args)
    print(f"      done in {time.perf_counter() - start:.1f}s")


def feature_files_status(name: str) -> str:
    """
    "missing": no daily file for the feature group (not every group has an hourly file)
    "outdated": the file exists but has no `date_from_utc`, the key merge_all.py needs
    "ok": the file exists and has the key
    """
    path = ROOT / FEATURES_DIRECTORY / name / "data_daily.csv"
    if not path.exists():
        return "missing"
    with path.open() as file:
        columns = file.readline().rstrip("\n").split(",")
    return "ok" if "date_from_utc" in columns else "outdated"


def download(name: str, script: str, output: str, force: bool) -> None:
    """ run the download script, only when the file is missing (or `force`) """
    exists = (ROOT / output).exists()
    if exists and not force:
        print(f"      {name}: use {output}")
        return

    print(f"      {name}: run {script}")
    try:
        run(script)
    except subprocess.CalledProcessError:
        if not exists:
            raise
        print(f"      warning: failed, keep the existing {output}")


def build_feature(
    step: int,
    name: str,
    pipeline: str,
    downloads: list[tuple[str, str, str]],
    rebuild: bool,
    force_download: bool,
) -> None:
    status = feature_files_status(name)
    if status == "ok" and not (rebuild or force_download):
        header(step, name, f"skip ({FEATURES_DIRECTORY}/{name} exists)")
        return

    outdated = " (the feature files have no date_from_utc, build them again)" if status == "outdated" else ""
    header(step, name, f"run{outdated}")
    for download_name, script, output in downloads:
        download(download_name, script, output, force_download)
    run(pipeline)


def main():
    parser = argparse.ArgumentParser(description = "Run the whole data flow: cleansing, features, merge")
    parser.add_argument(
        "--rebuild",
        action = "store_true",
        help = "build the features again, even if their files already exist"
    )
    parser.add_argument(
        "--forceDownload",
        action = "store_true",
        help = "download again, even if the files already exist (the features are built again)"
    )
    args = parser.parse_args()

    try:
        step = 0
        for script in BEFORE:
            step += 1
            header(step, Path(script).stem, "run")
            run(script)

        for name, pipeline, downloads in FEATURES:
            step += 1
            build_feature(step, name, pipeline, downloads, args.rebuild, args.forceDownload)

        for script in AFTER:
            step += 1
            header(step, Path(script).stem, "run")
            run(script)
    except subprocess.CalledProcessError as e:
        sys.exit(f"[fail] {Path(e.cmd[1]).relative_to(ROOT)} exited with code {e.returncode}, stop")


if __name__ == "__main__":
    main()
