"""Database engine and session factory."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.tables import Base

_ENGINE: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "sqlite+pysqlite:///:memory:",
    )


def get_engine() -> Engine:
    global _ENGINE, _SessionLocal
    if _ENGINE is not None:
        return _ENGINE
    url = database_url()
    kwargs: dict = {"future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    _ENGINE = create_engine(url, **kwargs)

    if url.startswith("sqlite"):

        @event.listens_for(_ENGINE, "connect")
        def _sqlite_fk(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _SessionLocal = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False, future=True)
    return _ENGINE


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def create_all() -> None:
    Base.metadata.create_all(bind=get_engine())


def reset_engine() -> None:
    """Test helper: drop the cached engine so a new DATABASE_URL takes effect."""
    global _ENGINE, _SessionLocal
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
    _SessionLocal = None


def session_scope() -> Generator[Session, None, None]:
    factory = get_session_factory()
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
