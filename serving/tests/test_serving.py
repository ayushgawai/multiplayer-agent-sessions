"""Serving smoke test."""

from __future__ import annotations

from fastapi.testclient import TestClient

from serve import app

client = TestClient(app)


def test_healthz() -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_m1_predict_stub() -> None:
    resp = client.post(
        "/v1/models/m1/predict",
        json={
            "inputs": {"query": "what is blocked?", "context_spans": ["a", "b"]},
            "params": {"seed": 13},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_id"] == "m1"
    assert "summary" in body["outputs"]
    assert body["seed"] == 13
