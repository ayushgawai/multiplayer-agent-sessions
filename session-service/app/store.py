"""In-memory session store for schema freeze and local smoke tests.

Postgres-backed event log lands in a later commit. This store is enough to
export OpenAPI and exercise route shapes.
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ulid import ULID

from app.schemas import (
    Actor,
    ActorKind,
    Causality,
    EventType,
    ParticipantRole,
    SessionEvent,
    SessionEventCreate,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _join_code(n: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


@dataclass
class Participant:
    participant_id: str
    display_name: str
    role: ParticipantRole


@dataclass
class Session:
    session_id: str
    title: str
    join_code: str
    scenario_id: str | None = None
    participants: dict[str, Participant] = field(default_factory=dict)
    events: list[SessionEvent] = field(default_factory=list)
    next_seq: int = 1


class Store:
    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}

    def create_session(self, title: str, scenario_id: str | None = None) -> Session:
        session_id = f"ses_{ULID()}"
        session = Session(
            session_id=session_id,
            title=title,
            join_code=_join_code(),
            scenario_id=scenario_id,
        )
        self.sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session:
        if session_id not in self.sessions:
            raise KeyError(session_id)
        return self.sessions[session_id]

    def join(
        self,
        session_id: str,
        join_code: str,
        display_name: str,
        role: ParticipantRole,
    ) -> Participant:
        session = self.get(session_id)
        if session.join_code != join_code:
            raise PermissionError("invalid join_code")
        participant_id = f"p_{len(session.participants) + 1}"
        participant = Participant(
            participant_id=participant_id,
            display_name=display_name,
            role=role,
        )
        session.participants[participant_id] = participant
        join_event = SessionEvent(
            event_id=f"evt_{ULID()}",
            session_id=session_id,
            seq=session.next_seq,
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
        session.next_seq += 1
        session.events.append(join_event)
        return participant

    def append_event(self, session_id: str, body: SessionEventCreate) -> SessionEvent:
        session = self.get(session_id)
        event_id = body.event_id or f"evt_{ULID()}"
        event = SessionEvent(
            event_id=event_id,
            session_id=session_id,
            seq=session.next_seq,
            ts=_now(),
            actor=body.actor,
            type=body.type,
            payload=body.payload,
            causality=body.causality,
        )
        session.next_seq += 1
        session.events.append(event)
        return event

    def events_since(self, session_id: str, since: int, limit: int) -> tuple[list[SessionEvent], int]:
        session = self.get(session_id)
        filtered = [e for e in session.events if e.seq is not None and e.seq > since]
        page = filtered[:limit]
        next_seq = page[-1].seq + 1 if page and page[-1].seq is not None else since
        if not page:
            next_seq = session.next_seq
        return page, next_seq

    def rollback(self, session_id: str, to_seq: int) -> tuple[dict[str, Any], list[SessionEvent]]:
        session = self.get(session_id)
        if to_seq < 0:
            raise ValueError("to_seq must be >= 0")
        kept = [e for e in session.events if e.seq is not None and e.seq <= to_seq]
        rolled = [e for e in session.events if e.seq is not None and e.seq > to_seq]
        session.events = kept
        session.next_seq = to_seq + 1
        snapshot = {
            "session_id": session_id,
            "title": session.title,
            "to_seq": to_seq,
            "event_count": len(kept),
        }
        return snapshot, rolled


store = Store()
