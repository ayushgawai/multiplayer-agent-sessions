"""SessionEvent emission for the agent runtime.

Linear: DAT-18. Owner: Shriram Dundigalla.

Every transition the loop makes becomes exactly one SessionEvent, built
against the frozen contract in session-service/app/schemas.py (ADR-001). The
runtime does not write to the event log itself: it hands finished events to a
sink, so the loop can be exercised against an in-memory sink in tests and
against the session service in a live session without changing the loop.

`seq` is deliberately left unset. It is allocated server side on append.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any, Protocol

from ulid import ULID

AGENT_STEP = "agent_step"
TOOL_CALL = "tool_call"
TOOL_RESULT = "tool_result"
INTERRUPT = "interrupt"

# Mirrors ParticipantRole in the frozen schema. An agent acts as an author.
AGENT_ROLE = "author"


_id_lock = threading.Lock()
_last_ulid_int = 0


def new_event_id() -> str:
    """ULID, lexicographically sortable, matching the contract's evt_ shape.

    A plain ULID only sorts by its millisecond prefix, and the loop emits
    several events inside one millisecond, where the random tail makes order
    arbitrary. The contract calls these sortable, so generation is made
    monotonic: within the same millisecond the previous value is incremented
    instead of redrawn.
    """
    global _last_ulid_int
    with _id_lock:
        candidate = int(ULID())
        if candidate <= _last_ulid_int:
            candidate = _last_ulid_int + 1
        _last_ulid_int = candidate
    return f"evt_{ULID.from_int(candidate)}"


def utc_now_iso() -> str:
    """Server time, UTC, millisecond precision, as the contract specifies."""
    return (
        datetime.now(UTC)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


class EventSink(Protocol):
    """Where finished events go. The session service is one implementation."""

    def emit(self, event: dict[str, Any]) -> None: ...


class ListSink:
    """Collects events in memory. Used by tests and the fixture harness."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)

    def of_type(self, event_type: str) -> list[dict[str, Any]]:
        return [e for e in self.events if e["type"] == event_type]


class EventEmitter:
    """Builds contract shaped events for one agent in one session."""

    def __init__(
        self,
        sink: EventSink,
        *,
        session_id: str,
        agent_id: str,
        display_name: str,
        root_instruction: str | None = None,
    ) -> None:
        self.sink = sink
        self.session_id = session_id
        self.agent_id = agent_id
        self.display_name = display_name
        self.root_instruction = root_instruction

    def _actor(self) -> dict[str, Any]:
        return {
            "kind": "agent",
            "id": self.agent_id,
            "display_name": self.display_name,
            "role": AGENT_ROLE,
        }

    def emit(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        parent_event: str | None = None,
    ) -> dict[str, Any]:
        """Build one event, hand it to the sink, and return it."""
        event: dict[str, Any] = {
            "event_id": new_event_id(),
            "session_id": self.session_id,
            "seq": None,
            "ts": utc_now_iso(),
            "actor": self._actor(),
            "type": event_type,
            "payload": payload,
            "causality": {
                "parent_event": parent_event,
                "root_instruction": self.root_instruction,
            },
            "labels": None,
        }
        self.sink.emit(event)
        return event

    def agent_step(
        self,
        *,
        index: int,
        phase: str,
        thought: str = "",
        tool: str | None = None,
        args: dict[str, Any] | None = None,
        ok: bool | None = None,
        output: Any = None,
        error: str | None = None,
        parent_event: str | None = None,
    ) -> dict[str, Any]:
        """One transition of the plan, act, observe loop."""
        payload: dict[str, Any] = {
            "step_index": index,
            "phase": phase,
            "thought": thought,
        }
        if tool is not None:
            payload["tool"] = tool
        if args is not None:
            payload["args"] = args
        if ok is not None:
            payload["ok"] = ok
        if output is not None:
            payload["output"] = output
        if error is not None:
            payload["error"] = error
        return self.emit(AGENT_STEP, payload, parent_event=parent_event)
