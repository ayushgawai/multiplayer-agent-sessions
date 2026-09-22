"""Schema and route smoke tests owned with the session service package."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Actor, ActorKind, EventType, ParticipantRole, SessionEventCreate

client = TestClient(app)


def test_healthz() -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_session_event_roundtrip() -> None:
    created = client.post("/v1/sessions", json={"title": "demo"})
    assert created.status_code == 200
    body = created.json()
    session_id = body["session_id"]
    join_code = body["join_code"]

    joined = client.post(
        f"/v1/sessions/{session_id}/join",
        json={
            "join_code": join_code,
            "display_name": "Ayush",
            "role": "author",
        },
    )
    assert joined.status_code == 200

    event = SessionEventCreate(
        actor=Actor(
            kind=ActorKind.human,
            id="p_1",
            display_name="Ayush",
            role=ParticipantRole.author,
        ),
        type=EventType.INSTRUCTION,
        payload={
            "text": "summarize what is blocked",
            "target_agent": "agent_researcher",
        },
    )
    appended = client.post(
        f"/v1/sessions/{session_id}/events",
        json=event.model_dump(mode="json"),
    )
    assert appended.status_code == 200
    assert appended.json()["seq"] >= 1

    page = client.get(f"/v1/sessions/{session_id}/events", params={"since": 0})
    assert page.status_code == 200
    assert len(page.json()["events"]) >= 2
