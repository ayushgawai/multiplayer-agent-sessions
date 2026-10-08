"""Session store backed by SQLAlchemy (Postgres or SQLite).

Append-only event log: events are INSERTed only. Rollback DELETEs rows with
seq greater than to_seq. Monotonic seq is allocated inside a transaction with
a row lock on the session.
"""

from __future__ import annotations

import secrets
import string
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from ulid import ULID

from app.bus import publish_event
from app.db import create_all, get_session_factory, reset_engine
from app.models.tables import EventRow, ParticipantRow, SessionRow
from app.schemas import (
    Actor,
    ActorKind,
    Causality,
    EventType,
    Labels,
    ParticipantRole,
    SessionEvent,
    SessionEventCreate,
)

_WRITE_ROLES = {ParticipantRole.author, ParticipantRole.reviewer}

# SQLite does not honor FOR UPDATE across threads; serialize writers in-process.
# Postgres still uses row locks for multi-process safety.
_write_lock = threading.RLock()

_store: Store | None = None


@dataclass
class Participant:
    participant_id: str
    display_name: str
    role: ParticipantRole


@dataclass
class SessionInfo:
    session_id: str
    title: str
    join_code: str
    scenario_id: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _join_code(n: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _row_to_event(row: EventRow) -> SessionEvent:
    labels = Labels.model_validate(row.labels_json) if row.labels_json else None
    return SessionEvent(
        event_id=row.event_id,
        session_id=row.session_id,
        seq=row.seq,
        ts=row.ts,
        actor=Actor(
            kind=ActorKind(row.actor_kind),
            id=row.actor_id,
            display_name=row.actor_display_name,
            role=ParticipantRole(row.actor_role),
        ),
        type=EventType(row.type),
        payload=row.payload,
        causality=Causality(
            parent_event=row.parent_event,
            root_instruction=row.root_instruction,
        ),
        labels=labels,
    )


def _insert_event(db: Session, session: SessionRow, event: SessionEvent) -> EventRow:
    assert event.seq is not None
    row = EventRow(
        event_id=event.event_id,
        session_id=session.session_id,
        seq=event.seq,
        ts=event.ts,
        actor_kind=event.actor.kind.value,
        actor_id=event.actor.id,
        actor_display_name=event.actor.display_name,
        actor_role=event.actor.role.value,
        type=event.type.value,
        payload=event.payload,
        parent_event=event.causality.parent_event,
        root_instruction=event.causality.root_instruction,
        labels_json=event.labels.model_dump() if event.labels else None,
    )
    db.add(row)
    return row


class Store:
    def __init__(self) -> None:
        create_all()
        self._factory = get_session_factory()

    def create_session(self, title: str, scenario_id: str | None = None) -> SessionInfo:
        session_id = f"ses_{ULID()}"
        info = SessionInfo(
            session_id=session_id,
            title=title,
            join_code=_join_code(),
            scenario_id=scenario_id,
        )
        with self._factory() as db:
            db.add(
                SessionRow(
                    session_id=info.session_id,
                    title=info.title,
                    join_code=info.join_code,
                    scenario_id=info.scenario_id,
                    next_seq=1,
                    created_at=_now(),
                )
            )
            db.commit()
        return info

    def get(self, session_id: str) -> SessionInfo:
        with self._factory() as db:
            row = db.get(SessionRow, session_id)
            if row is None:
                raise KeyError(session_id)
            return SessionInfo(
                session_id=row.session_id,
                title=row.title,
                join_code=row.join_code,
                scenario_id=row.scenario_id,
            )

    def join(
        self,
        session_id: str,
        join_code: str,
        display_name: str,
        role: ParticipantRole,
    ) -> Participant:
        with _write_lock, self._factory() as db:
            session = db.execute(
                select(SessionRow).where(SessionRow.session_id == session_id).with_for_update()
            ).scalar_one_or_none()
            if session is None:
                raise KeyError(session_id)
            if session.join_code != join_code:
                raise PermissionError("invalid join_code")
            count = db.execute(
                select(func.count())
                .select_from(ParticipantRow)
                .where(ParticipantRow.session_id == session_id)
            ).scalar_one()
            participant_id = f"p_{count + 1}"
            participant = Participant(
                participant_id=participant_id,
                display_name=display_name,
                role=role,
            )
            db.add(
                ParticipantRow(
                    session_id=session_id,
                    participant_id=participant_id,
                    display_name=display_name,
                    role=role.value,
                )
            )
            seq = session.next_seq
            session.next_seq = seq + 1
            event = SessionEvent(
                event_id=f"evt_{ULID()}",
                session_id=session_id,
                seq=seq,
                ts=_now(),
                actor=Actor(
                    kind=ActorKind.human,
                    id=participant_id,
                    display_name=display_name,
                    role=role,
                ),
                type=EventType.JOIN,
                payload={"display_name": display_name, "role": role.value},
                causality=Causality(),
            )
            _insert_event(db, session, event)
            db.commit()
        publish_event(session_id, event)
        return participant

    def append_event(self, session_id: str, body: SessionEventCreate) -> SessionEvent:
        with _write_lock, self._factory() as db:
            session = db.execute(
                select(SessionRow).where(SessionRow.session_id == session_id).with_for_update()
            ).scalar_one_or_none()
            if session is None:
                raise KeyError(session_id)

            participant = db.execute(
                select(ParticipantRow).where(
                    ParticipantRow.session_id == session_id,
                    ParticipantRow.participant_id == body.actor.id,
                )
            ).scalar_one_or_none()

            allowed = True
            reject_reason = ""
            if body.actor.kind == ActorKind.human:
                if participant is None:
                    allowed = False
                    reject_reason = "unknown participant"
                elif ParticipantRole(participant.role) not in _WRITE_ROLES:
                    allowed = False
                    reject_reason = f"role {participant.role} cannot append {body.type.value}"

            seq = session.next_seq
            session.next_seq = seq + 1
            event_id = body.event_id or f"evt_{ULID()}"

            if not allowed:
                event = SessionEvent(
                    event_id=event_id,
                    session_id=session_id,
                    seq=seq,
                    ts=_now(),
                    actor=body.actor,
                    type=EventType.REJECTED,
                    payload={
                        "attempted_type": body.type.value,
                        "reason": reject_reason,
                        "attempted_payload": body.payload,
                    },
                    causality=body.causality,
                )
            else:
                event = SessionEvent(
                    event_id=event_id,
                    session_id=session_id,
                    seq=seq,
                    ts=_now(),
                    actor=body.actor,
                    type=body.type,
                    payload=body.payload,
                    causality=body.causality,
                )
            _insert_event(db, session, event)
            db.commit()
        publish_event(session_id, event)
        return event

    def events_since(
        self, session_id: str, since: int, limit: int
    ) -> tuple[list[SessionEvent], int]:
        with self._factory() as db:
            session = db.get(SessionRow, session_id)
            if session is None:
                raise KeyError(session_id)
            rows = (
                db.execute(
                    select(EventRow)
                    .where(EventRow.session_id == session_id, EventRow.seq > since)
                    .order_by(EventRow.seq.asc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            events = [_row_to_event(r) for r in rows]
            if events and events[-1].seq is not None:
                next_seq = events[-1].seq + 1
            else:
                next_seq = session.next_seq
            return events, next_seq

    def rollback(self, session_id: str, to_seq: int) -> tuple[dict[str, Any], list[SessionEvent]]:
        if to_seq < 0:
            raise ValueError("to_seq must be >= 0")
        with _write_lock, self._factory() as db:
            session = db.execute(
                select(SessionRow).where(SessionRow.session_id == session_id).with_for_update()
            ).scalar_one_or_none()
            if session is None:
                raise KeyError(session_id)
            rolled_rows = (
                db.execute(
                    select(EventRow)
                    .where(EventRow.session_id == session_id, EventRow.seq > to_seq)
                    .order_by(EventRow.seq.asc())
                )
                .scalars()
                .all()
            )
            rolled = [_row_to_event(r) for r in rolled_rows]
            db.execute(
                delete(EventRow).where(EventRow.session_id == session_id, EventRow.seq > to_seq)
            )
            session.next_seq = to_seq + 1
            kept_count = (
                db.execute(
                    select(EventRow).where(
                        EventRow.session_id == session_id, EventRow.seq <= to_seq
                    )
                )
                .scalars()
                .all()
            )
            snapshot = {
                "session_id": session_id,
                "title": session.title,
                "to_seq": to_seq,
                "event_count": len(kept_count),
            }
            db.commit()
        return snapshot, rolled

    def all_events(self, session_id: str) -> list[SessionEvent]:
        events, _ = self.events_since(session_id, since=0, limit=100_000)
        return events


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def reset_store() -> None:
    """Test helper."""
    global _store
    reset_engine()
    _store = None
