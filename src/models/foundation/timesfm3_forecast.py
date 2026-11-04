"""
TimesFM-3 zero-shot forecasts: experiments F1, F2 (hourly) and F4, F5 (daily).

| #  | Resolution | Horizons    | Covariates                          |
|----|------------|-------------|-------------------------------------|
| F1 | hourly     | 24 h        | none (target history only)          |
| F2 | hourly     | 24 h        | known future + past only            |
| F4 | daily      | 1 d, 7 d    | none                                |
| F5 | daily      | 1 d, 7 d    | known future + past only            |

No training: for every origin the history before it goes in (plus the
covariates), the point forecast (median) and 9 quantiles come out. The model
normalises every variate by itself, so raw MWh values go in and come out
(FOUNDATION.md, "Normalization").

Examples (from the project root):

    uv run python src/models/foundation/timesfm3_forecast.py --resolution hourly --split val --covariates --context-length 2048
    uv run python src/models/foundation/timesfm3_forecast.py --resolution daily --split test --no-covariates
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from data import (
    DEFAULT_DATA_DIR,
    DEFAULT_FORECAST_DIR,
    HORIZONS,
    QUANTILES,
    SeriesFrame,
    covariate_set,
    forecasts_to_frame,
    horizon_label,
    load_frame,
    make_window,
    origin_positions,
    write_forecasts,
)

CHECKPOINT = "google/timesfm-3.0-pytorch"
MAX_VARIATES = 32  # TimesFM3Evaluator drops covariates at random above this
PATCH = 32  # input patch length; contexts that are a multiple of it need no padding


def load_model(checkpoint: str = CHECKPOINT, batch_size: int = 16, device: str | None = None):
    """Load the pretrained TimesFM-3 evaluator once (it is reused for all runs)."""
    from timesfm3 import ModelConfig, TimesFM3Evaluator

    return TimesFM3Evaluator(
        ModelConfig(checkpoint_path=checkpoint, per_core_batch_size=batch_size, device=device)
    )


def experiment_id(resolution: str, covariates: bool) -> str:
    return {("hourly", False): "F1", ("hourly", True): "F2", ("daily", False): "F4", ("daily", True): "F5"}[
        (resolution, covariates)
    ]


def run_name(resolution: str, horizon: int, split: str, covariates: bool, context_length: int | None, use_znorm=False) -> str:
    ctx = "all" if context_length is None else str(context_length)
    cov = "cov" if covariates else "nocov"
    zn = "_znorm" if use_znorm else ""
    return f"timesfm3_zs_{cov}_{resolution}_{horizon_label(resolution, horizon)}_ctx{ctx}{zn}_{split}"


def _predict_chunk(model, contexts, po, pf, horizon, use_znorm):
    """One predict_batch call; halves the batch size and retries on CUDA OOM."""
    import torch

    oom = getattr(torch, "OutOfMemoryError", torch.cuda.OutOfMemoryError)
    while True:
        try:
            outs = list(
                model.predict_batch(
                    contexts=contexts,
                    horizon=horizon,
                    past_only_covariates=po,
                    past_future_covariates=pf,
                    return_quantiles=True,
                    use_znorm=use_znorm,
                )
            )
            return outs
        except oom:
            bs = model.config.per_core_batch_size
            if bs <= 1:
                raise
            torch.cuda.empty_cache()
            model.config.per_core_batch_size = max(1, bs // 2)
            print(f"[timesfm3] CUDA out of memory, batch size {bs} -> {model.config.per_core_batch_size}")


def forecast(
    model,
    frame: SeriesFrame,
    split: str,
    horizon: int,
    covariates: bool,
    context_length: int | None,
    use_znorm: bool = False,
    chunk_size: int = 64,
    max_origins: int | None = None,
):
    """Forecasts for all origins of one split. Returns (forecast DataFrame, meta dict)."""
    cov = covariate_set(frame.resolution, horizon, include_covariates=covariates)
    if cov.n_variates > MAX_VARIATES:
        raise ValueError(
            f"{cov.n_variates} variates > {MAX_VARIATES}: TimesFM3Evaluator would drop covariates at random. "
            "Use fewer covariates (e.g. aggregates of generation_*)."
        )
    positions = origin_positions(frame, split, horizon)
    if max_origins is not None:
        positions = positions[:max_origins]

    y = frame.y
    known = frame.matrix(cov.known)
    past = frame.matrix(cov.past_only)

    t0 = time.time()
    y_pred = np.empty((len(positions), horizon))
    q_pred = np.empty((len(positions), horizon, len(QUANTILES)))
    for start in range(0, len(positions), chunk_size):
        chunk = positions[start : start + chunk_size]
        wins = [make_window(frame, y, known, past, p, horizon, context_length) for p in chunk]
        contexts = [w.y_context for w in wins]
        if covariates:
            # past-only: (n_past, L); past-future: (n_known, L + H)
            po = [w.past_context.T for w in wins] if cov.past_only else None
            pf = [np.concatenate([w.known_context, w.known_future]).T for w in wins] if cov.known else None
        else:
            po = pf = None
        outs = _predict_chunk(model, contexts, po, pf, horizon, use_znorm)
        for i, out in enumerate(outs):
            y_pred[start + i] = out.forecast
            q_pred[start + i] = out.quantiles
        print(f"[timesfm3] {frame.resolution} {horizon_label(frame.resolution, horizon)} {split}: "
              f"{min(start + chunk_size, len(positions))}/{len(positions)} origins")
    runtime = time.time() - t0

    out_df = forecasts_to_frame(frame, positions, horizon, y_pred, q_pred)
    meta = {
        "model": "TimesFM-3",
        "experiment": experiment_id(frame.resolution, covariates),
        "variant": "zero-shot",
        "checkpoint": CHECKPOINT,
        "resolution": frame.resolution,
        "horizon": horizon,
        "split": split,
        "n_origins": int(len(positions)),
        "context_length": "all" if context_length is None else int(context_length),
        "covariates_known": cov.known,
        "covariates_past_only": cov.past_only,
        "n_variates": cov.n_variates,
        "weather_variant": "A (observed, oracle)" if covariates else "n/a",
        "use_znorm": use_znorm,
        "predict_batch_defaults": "TimesFM3Evaluator: symmetric averaging, make_positive, sorted quantiles",
        "y_pred": "median (q0.5)",
        "runtime_seconds": round(runtime, 1),
        "batch_size_end": model.config.per_core_batch_size,
    }
    return out_df, meta


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--resolution", choices=["hourly", "daily"], required=True)
    p.add_argument("--split", choices=["val", "test"], required=True)
    p.add_argument("--horizons", type=int, nargs="+", help="default: 24 (hourly), 1 7 (daily)")
    p.add_argument("--covariates", action=argparse.BooleanOptionalAction, default=True,
                   help="--no-covariates gives F1 / F4, --covariates F2 / F5")
    p.add_argument("--context-length", type=int, default=None,
                   help="context steps; default 2048 hourly, the whole history daily")
    p.add_argument("--use-znorm", action="store_true", help="extra z-normalisation (experiment F9)")
    p.add_argument("--batch-size", type=int, default=16, help="per_core_batch_size (halved on CUDA OOM)")
    p.add_argument("--device", default=None, help="cuda / cpu (default: cuda if available)")
    p.add_argument("--checkpoint", default=CHECKPOINT)
    p.add_argument("--max-origins", type=int, default=None, help="only the first N origins (smoke test)")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_FORECAST_DIR)
    args = p.parse_args()

    context_length = args.context_length
    if context_length is None and args.resolution == "hourly":
        context_length = 2048
    if context_length is not None and context_length % PATCH:
        print(f"[timesfm3] note: context {context_length} is not a multiple of {PATCH}, the model pads it")

    frame = load_frame(args.resolution, args.data_dir)
    model = load_model(args.checkpoint, args.batch_size, args.device)
    for h in args.horizons or HORIZONS[args.resolution]:
        out, meta = forecast(model, frame, args.split, h, args.covariates, context_length,
                             use_znorm=args.use_znorm, max_origins=args.max_origins)
        name = run_name(args.resolution, h, args.split, args.covariates, context_length, args.use_znorm)
        write_forecasts(out, args.out_dir / f"{name}.csv", meta)


if __name__ == "__main__":
    main()
