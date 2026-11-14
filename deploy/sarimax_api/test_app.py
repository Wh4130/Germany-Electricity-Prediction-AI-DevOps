"""
    uv run --with-requirements deploy/sarimax_api/requirements.txt --with httpx --with pytest \
        pytest deploy/sarimax_api
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import app  # noqa: E402
from service import PROJECT_ROOT  # noqa: E402

FORECASTS = PROJECT_ROOT / "src" / "results" / "sarimax" / "forecasts" / "sarimax_daily_1d_test.csv"


@pytest.fixture(scope = "module")
def client():
    with TestClient(app) as c:
        yield c


def test_forecast_matches_run_sarimax(client):
    if not FORECASTS.exists():
        pytest.skip("run run_sarimax.py first")
    api = pd.DataFrame(client.get("/forecast").json())
    saved = pd.read_csv(FORECASTS)
    assert list(api["date"]) == list(saved["target_time"])
    for col in ("y_true", "y_pred", "q0.1", "q0.5", "q0.9"):
        assert np.allclose(api[col], saved[col], atol = 1e-6)


def test_predict_without_changes_is_the_forecast(client):
    base = client.get("/forecast", params = {"start": "2024-03-15", "end": "2024-03-15"}).json()[0]
    out = client.post("/predict", json = {"date": "2024-03-15"}).json()
    assert out["y_pred"] == pytest.approx(base["y_pred"])
    assert out["q0.1"] == pytest.approx(base["q0.1"])


def test_predict_is_linear_in_x(client):
    value = client.get("/features", params = {"date": "2024-03-15"}).json()["sliders"]["hdd"]["value"]
    d1 = client.post("/predict", json = {"date": "2024-03-15", "x": {"hdd": value + 1}}).json()
    d2 = client.post("/predict", json = {"date": "2024-03-15", "x": {"hdd": value + 2}}).json()
    step1, step2 = d1["y_pred"] - d1["y_pred_baseline"], d2["y_pred"] - d2["y_pred_baseline"]
    assert step1 > 0                    # colder -> more load
    assert step2 == pytest.approx(2 * step1)
    assert d1["q0.9"] - d1["q0.1"] == pytest.approx(d2["q0.9"] - d2["q0.1"])     # same width


def test_errors(client):
    assert client.get("/features", params = {"date": "2023-06-01"}).status_code == 404
    assert client.post("/predict", json = {"date": "2024-12-25", "x": {"is_holiday": 0}}).status_code == 422
