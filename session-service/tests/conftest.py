"""Pytest fixtures: in-memory SQLite event log, no Redis required."""

from __future__ import annotations

import os

import pytest

# Force SQLite before app modules bind an engine.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ.pop("REDIS_URL", None)


@pytest.fixture(autouse=True)
def _fresh_store() -> None:
    from app.store import reset_store

    reset_store()
    yield
    reset_store()
