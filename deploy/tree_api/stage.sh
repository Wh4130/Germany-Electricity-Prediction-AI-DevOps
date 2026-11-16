#!/usr/bin/env bash
# Copy what the image needs into deploy/tree_api/artifacts/ (the Docker build context is this folder).
# Run from anywhere: deploy/tree_api/stage.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/artifacts"

rm -rf "$OUT"
mkdir -p "$OUT"
cp "$ROOT/src/results/tree-based/Models/daily/final_model_h1.joblib" "$OUT/"
cp "$ROOT/src/data/final/data_daily.csv" "$OUT/"
echo "staged into $OUT:"
ls -l "$OUT"
