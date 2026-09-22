"""Session service FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

from app.routes.sessions import router as sessions_router
from app.schemas import HealthResponse

VERSION = "0.1.0"

app = FastAPI(
    title="Multiplayer Agent Sessions - Session Service",
    version=VERSION,
    description="Event log, join, rollback, and stream surface for Team 4.",
)

app.include_router(sessions_router)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(ok=True, version=VERSION)
