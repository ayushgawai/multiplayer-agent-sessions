"""Schema, permissions, rollback, concurrency, and replay tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app
from app.replay import replay_to_seq
from app.schemas import Actor, ActorKind, EventType, ParticipantRole, SessionEventCreate
from app.store import get_store

client = TestClient(app)


def _create_and_join(role: str = "author", name: str = "Ayush") -> tuple[str, str, str]:
    created = client.post("/v1/sessions", json={"title": "demo"})
    assert created.status_code == 200
    body = created.json()
    session_id = body["session_id"]
    join_code = body["join_code"]
    joined = client.post(
        f"/v1/sessions/{session_id}/join",
        json={"join_code": join_code, "display_name": name, "role": role},
    )
    assert joined.status_code == 200
    return session_id, join_code, joined.json()["participant_id"]


def test_healthz() -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_session_event_roundtrip() -> None:
    session_id, _, participant_id = _create_and_join()
    event = SessionEventCreate(
        actor=Actor(
            kind=ActorKind.human,
            id=participant_id,
            display_name="Ayush",
            role=ParticipantRole.author,
        ),
        type=EventType.INSTRUCTION,
        payload={"text": "summarize what is blocked", "target_agent": "agent_researcher"},
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


def test_observer_append_is_rejected_and_logged() -> None:
    session_id, _, participant_id = _create_and_join(role="observer", name="Watcher")
    event = SessionEventCreate(
        actor=Actor(
            kind=ActorKind.human,
            id=participant_id,
            display_name="Watcher",
            role=ParticipantRole.observer,
        ),
        type=EventType.INSTRUCTION,
        payload={"text": "should fail"},
    )
    resp = client.post(
        f"/v1/sessions/{session_id}/events",
        json=event.model_dump(mode="json"),
    )
    assert resp.status_code == 200
    page = client.get(f"/v1/sessions/{session_id}/events", params={"since": 0})
    types = [e["type"] for e in page.json()["events"]]
    assert "rejected" in types
    assert types[-1] == "rejected"


def test_rollback_matches_replay() -> None:
    session_id, _, participant_id = _create_and_join()
    for text in ("one", "two", "three"):
        client.post(
            f"/v1/sessions/{session_id}/events",
            json=SessionEventCreate(
                actor=Actor(
                    kind=ActorKind.human,
                    id=participant_id,
                    display_name="Ayush",
                    role=ParticipantRole.author,
                ),
                type=EventType.INSTRUCTION,
                payload={"text": text},
            ).model_dump(mode="json"),
        )
    events_before = get_store().all_events(session_id)
    # join=1, three instructions => seq 4; roll back to after first instruction (seq 2)
    expected = replay_to_seq(events_before, to_seq=2)
    rolled = client.post(
        f"/v1/sessions/{session_id}/rollback",
        json={"to_seq": 2},
    )
    assert rolled.status_code == 200
    body = rolled.json()
    assert len(body["rolled_back_events"]) == 2
    live = replay_to_seq(get_store().all_events(session_id))
    assert live["instruction_count"] == expected["instruction_count"]
    assert live["applied_seqs"] == expected["applied_seqs"]


def test_concurrent_appends_gapless_seq() -> None:
    session_id, join_code, _ = _create_and_join(name="A")
    # second and third writers
    pids = []
    for name in ("B", "C"):
        joined = client.post(
            f"/v1/sessions/{session_id}/join",
            json={"join_code": join_code, "display_name": name, "role": "author"},
        )
        pids.append(joined.json()["participant_id"])
    # include first participant
    page = client.get(f"/v1/sessions/{session_id}/events", params={"since": 0})
    first_pid = page.json()["events"][0]["actor"]["id"]
    writers = [first_pid, *pids]

    def _write(i: int) -> int:
        pid = writers[i % 3]
        resp = client.post(
            f"/v1/sessions/{session_id}/events",
            json={
                "actor": {
                    "kind": "human",
                    "id": pid,
                    "display_name": "w",
                    "role": "author",
                },
                "type": "instruction",
                "payload": {"text": f"op-{i}"},
            },
        )
        assert resp.status_code == 200
        return int(resp.json()["seq"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        seqs = list(pool.map(_write, range(200)))

    assert len(seqs) == 200
    assert len(set(seqs)) == 200
    # join events occupy 1..3; instructions continue gapless
    events = get_store().all_events(session_id)
    all_seqs = [e.seq for e in events if e.seq is not None]
    assert all_seqs == list(range(1, len(all_seqs) + 1))
