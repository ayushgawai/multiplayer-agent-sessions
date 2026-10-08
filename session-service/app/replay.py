"""Rebuild session snapshot state from the event log alone."""

from __future__ import annotations

from typing import Any

from app.schemas import EventType, SessionEvent


def replay_to_seq(events: list[SessionEvent], to_seq: int | None = None) -> dict[str, Any]:
    """Fold events into a simple snapshot. Used by rollback acceptance checks."""
    participants: dict[str, dict[str, str]] = {}
    instructions: list[dict[str, Any]] = []
    applied: list[int] = []

    for event in sorted(events, key=lambda e: e.seq or 0):
        if event.seq is None:
            continue
        if to_seq is not None and event.seq > to_seq:
            break
        applied.append(event.seq)
        if event.type == EventType.JOIN:
            participants[event.actor.id] = {
                "display_name": event.actor.display_name,
                "role": event.actor.role.value,
            }
        elif event.type == EventType.LEAVE:
            participants.pop(event.actor.id, None)
        elif event.type == EventType.INSTRUCTION:
            instructions.append(
                {
                    "event_id": event.event_id,
                    "seq": event.seq,
                    "text": event.payload.get("text"),
                    "actor_id": event.actor.id,
                }
            )
        elif event.type == EventType.REJECTED:
            continue

    return {
        "to_seq": applied[-1] if applied else 0,
        "participant_count": len(participants),
        "participants": participants,
        "instruction_count": len(instructions),
        "instructions": instructions,
        "applied_seqs": applied,
    }
