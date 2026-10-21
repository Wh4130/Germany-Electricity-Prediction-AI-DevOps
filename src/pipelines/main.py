"""
Run the whole data flow, in order, with the default paths of every step.

    1. download the data that does not come from SMARD (src/scripts/*_etl.py)
       -> skipped when its output file already exists, they only need to run once
    2. src/pipelines/cleansing.py          raw -> intermin
    3. src/pipelines/calendar_pipeline.py            intermin -> features/calendar
       src/pipelines/economic_indicators_pipeline.py intermin -> features/economic_indicators
       src/pipelines/electricity_price_pipeline.py   intermin -> features/electricity_price
       src/pipelines/generation_pipeline.py          intermin -> features/generation
       src/pipelines/weather_pipeline.py             intermin -> features/weather
       src/pipelines/mastr_pipeline.py               intermin -> features/mastr


Run (from the project root)
    uv run python src/pipelines/main.py
    uv run python src/pipelines/main.py --forceDownload   # download again, even if the files exist

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

# (name, script, output file: when it exists the download is skipped)
DOWNLOADS = [
    ("school holidays", "src/scripts/school_holidays_etl.py", "src/data/intermin/school_holidays.csv"),
    ("population", "src/scripts/population_etl.py", "src/data/intermin/population_by_land.csv"),
    ("industrial production", "src/scripts/industrial_production_etl.py", "src/data/intermin/industrial_production.csv"),
    ("gas price", "src/scripts/gas_price_etl.py", "src/data/intermin/gas_price_eu.csv"),
    ("day-ahead price", "src/scripts/day_ahead_price_etl.py", "src/data/intermin/day_ahead_price.csv"),
    ("weather", "src/scripts/weather_etl.py", "src/data/intermin/weather_daily_by_city.csv"),
    ("mastr solar", "src/scripts/mastr_etl.py", "src/data/intermin/mastr_solar.csv"),
]

PIPELINES = [
    "src/pipelines/cleansing.py",
    "src/pipelines/cleansing_generation.py",
    "src/pipelines/calendar_pipeline.py",
    "src/pipelines/economic_indicators_pipeline.py",
    "src/pipelines/electricity_price_pipeline.py",
    "src/pipelines/generation_pipeline.py",
    "src/pipelines/weather_pipeline.py",
    "src/pipelines/mastr_pipeline.py",
    "src/pipelines/merge_all.py",  # always the last one: merges intermin and all features
]


TOTAL_STEPS = len(DOWNLOADS) + len(PIPELINES)
LABEL_WIDTH = max([len(name) for name, _, _ in DOWNLOADS] + [len(Path(script).stem) for script in PIPELINES])


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


def download(step: int, name: str, script: str, output: str, force: bool) -> None:
    exists = (ROOT / output).exists()
    if exists and not force:
        header(step, name, f"skip ({output} exists)")
        return

    header(step, name, "run")
    try:
        run(script)
    except subprocess.CalledProcessError:
        if not exists:
            raise
        print(f"      warning: failed, keep the existing {output}")


def main():
    parser = argparse.ArgumentParser(description = "Run the whole data flow: downloads, cleansing, features")
    parser.add_argument(
        "--forceDownload",
        action = "store_true",
        help = "download again, even if the files already exist"
    )
    args = parser.parse_args()

    try:
        for step, (name, script, output) in enumerate(DOWNLOADS, start = 1):
            download(step, name, script, output, args.forceDownload)

        for step, script in enumerate(PIPELINES, start = len(DOWNLOADS) + 1):
            header(step, Path(script).stem, "run")
            run(script)
    except subprocess.CalledProcessError as e:
        sys.exit(f"[fail] {Path(e.cmd[1]).relative_to(ROOT)} exited with code {e.returncode}, stop")


if __name__ == "__main__":
    main()
