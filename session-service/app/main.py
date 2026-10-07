"""Session service FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.db import create_all
from app.routes.sessions import router as sessions_router
from app.schemas import HealthResponse
from app.store import get_store

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    create_all()
    get_store()
    yield


app = FastAPI(
    title="Multiplayer Agent Sessions - Session Service",
    version=VERSION,
    description="Event log, join, rollback, and stream surface for Team 4.",
    lifespan=lifespan,
)

app.include_router(sessions_router)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(ok=True, version=VERSION)
