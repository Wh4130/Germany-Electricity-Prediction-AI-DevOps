"""
HTTP API of the daily 1-day SARIMAX model (see service.py and docs/deploy/API.md).

    uv run --with-requirements deploy/sarimax_api/requirements.txt \
        uvicorn app:app --app-dir deploy/sarimax_api --port 8000

ALLOWED_ORIGINS: the origins that may call the API from a browser (comma-separated, default "*").
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from service import SarimaxService

service: SarimaxService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global service
    service = SarimaxService()          # loads the model once (a few seconds)
    yield


app = FastAPI(title = "SARIMAX daily 1-day forecast", version = "1.0", lifespan = lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")],
    allow_methods = ["GET", "POST"],
    allow_headers = ["*"],
)


class PredictRequest(BaseModel):
    date: str = Field(examples = ["2024-03-15"])
    x: dict[str, float] = Field(default_factory = dict, examples = [{"hdd": 10.0, "day_ahead_price_mean": 120.0}])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/meta")
def meta() -> dict:
    return service.meta()


@app.get("/forecast")
def forecast(start: str | None = None, end: str | None = None) -> list[dict]:
    return service.forecast(start, end)


@app.get("/features")
def features(date: str) -> dict:
    try:
        return service.features(date)
    except (KeyError, ValueError) as e:
        raise HTTPException(404, str(e).strip('"'))


@app.post("/predict")
def predict(request: PredictRequest) -> dict:
    try:
        return service.predict(request.date, request.x)
    except KeyError as e:
        raise HTTPException(404, str(e).strip('"'))
    except ValueError as e:
        raise HTTPException(422, str(e))
