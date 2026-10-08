"""SQLAlchemy tables for the append-only event log."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class SessionRow(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    join_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    scenario_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    next_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    participants: Mapped[list[ParticipantRow]] = relationship(back_populates="session")
    events: Mapped[list[EventRow]] = relationship(back_populates="session")


class ParticipantRow(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("session_id", "participant_id", name="uq_session_participant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False)
    participant_id: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)

    session: Mapped[SessionRow] = relationship(back_populates="participants")


class EventRow(Base):
    """Append-only. Application code never UPDATEs rows; rollback DELETEs seq > to_seq."""

    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("session_id", "seq", name="uq_session_seq"),)

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    parent_event: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    root_instruction: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    labels_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Opaque column reserved so raw dumps stay human-readable in SQL tools
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped[SessionRow] = relationship(back_populates="events")
