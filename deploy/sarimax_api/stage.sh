#!/usr/bin/env bash
# Copy what the image needs into deploy/sarimax_api/artifacts/ (the Docker build context is this folder).
# Run from anywhere: deploy/sarimax_api/stage.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/artifacts"

rm -rf "$OUT"
mkdir -p "$OUT"
cp "$ROOT/src/models/sarimax/common.py" "$ROOT/src/models/sarimax/features.py" "$OUT/"
cp "$ROOT/src/results/sarimax/models/sarimax_daily_1d.json" "$OUT/"
cp "$ROOT/src/data/final/data_daily.csv" "$OUT/"
echo "staged into $OUT:"
ls -l "$OUT"
