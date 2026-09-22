"""Uniform model serving. Stub adapters until bake-off winners exist."""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from adapters import m1, m2, m3, m4

VERSION = "0.1.0"

app = FastAPI(
    title="Multiplayer Agent Sessions — Model Serving",
    version=VERSION,
)


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    inputs: dict[str, Any]
    params: dict[str, Any] = Field(default_factory=dict)


class PredictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    model_id: str
    version: str
    outputs: dict[str, Any]
    latency_ms: float
    seed: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    version: str


ADAPTERS = {
    "m1": m1.predict,
    "m2": m2.predict,
    "m3": m3.predict,
    "m4": m4.predict,
}


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(ok=True, version=VERSION)


@app.post("/v1/models/{model_id}/predict", response_model=PredictResponse)
def predict(model_id: str, body: PredictRequest) -> PredictResponse:
    if model_id not in ADAPTERS:
        raise HTTPException(status_code=404, detail=f"unknown model_id: {model_id}")
    seed = int(body.params.get("seed", 13))
    started = time.perf_counter()
    outputs = ADAPTERS[model_id](body.inputs, body.params)
    latency_ms = (time.perf_counter() - started) * 1000.0
    return PredictResponse(
        model_id=model_id,
        version=f"{model_id}-stub@local",
        outputs=outputs,
        latency_ms=latency_ms,
        seed=seed,
    )
