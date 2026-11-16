"""
    uv run --with-requirements deploy/tree_api/requirements.txt --with httpx --with pytest \
        pytest deploy/tree_api
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import app  # noqa: E402
from service import PROJECT_ROOT, SLIDERS  # noqa: E402

FORECASTS = PROJECT_ROOT / "src" / "results" / "tree-based" / "Forecasts" / "tree_daily_test.csv"


@pytest.fixture(scope = "module")
def client():
    with TestClient(app) as c:
        yield c


def test_forecast_matches_run_tree_based(client):
    """ the API features are a copy of the training script's: this fails when the two drift apart """
    if not FORECASTS.exists():
        pytest.skip("run run_tree_based.py first")
    api = pd.DataFrame(client.get("/forecast").json())
    saved = pd.read_csv(FORECASTS)
    saved = saved[saved["step"] == 1]
    assert list(api["date"]) == list(saved["target_time"])
    for col in ("y_true", "y_pred"):
        assert np.allclose(api[col], saved[col], atol = 1e-6)


def test_forecast_has_no_quantiles(client):
    row = client.get("/forecast", params = {"start": "2024-03-15", "end": "2024-03-15"}).json()[0]
    assert set(row) == {"date", "y_true", "y_pred"}


def test_features_are_the_x_of_the_day(client):
    out = client.get("/features", params = {"date": "2024-03-15"}).json()
    assert set(out["sliders"]) == set(SLIDERS)
    for s in out["sliders"].values():
        assert s["min"] <= s["value"] <= s["max"]
    assert out["calendar"]["day_of_week"] == "Friday"


def test_predict_without_changes_is_the_forecast(client):
    base = client.get("/forecast", params = {"start": "2024-03-15", "end": "2024-03-15"}).json()[0]
    out = client.post("/predict", json = {"date": "2024-03-15"}).json()
    assert out["y_pred"] == pytest.approx(base["y_pred"])
    assert out["y_pred_baseline"] == pytest.approx(base["y_pred"])


def test_predict_follows_the_x(client):
    """ a much colder day gives more load (a tree is not linear, so only the direction is checked) """
    value = client.get("/features", params = {"date": "2024-03-15"}).json()["sliders"]["hdd"]["value"]
    out = client.post("/predict", json = {"date": "2024-03-15", "x": {"hdd": value + 12}}).json()
    assert out["y_pred"] > out["y_pred_baseline"]
    assert out["x"]["hdd"] == pytest.approx(value + 12)


def test_errors(client):
    assert client.get("/features", params = {"date": "2023-06-01"}).status_code == 404
    assert client.post("/predict", json = {"date": "2024-12-25", "x": {"is_holiday": 0}}).status_code == 422
