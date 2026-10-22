"""Every event the runtime emits must validate against the frozen contract.

Linear: DAT-18. Owner: Shriram Dundigalla.

The models come from session-service/app/schemas.py, frozen under ADR-001.
Importing them here rather than restating the shape is the point: if Ayush
changes the contract, these tests fail instead of the runtime silently
emitting events the session service will reject.
"""

from __future__ import annotations

from typing import Any

import pytest
from app.schemas import ActorKind, EventType, ParticipantRole, SessionEvent

from runtime.events import EventEmitter, ListSink, new_event_id, utc_now_iso
from runtime.loop import AgentLoop
from runtime.state import Observation, Plan, Step


class TwoStepPlanner:
    def __init__(self) -> None:
        self.calls = 0

    def plan(self, instruction: str, steps: list[Step]) -> Plan:
        self.calls += 1
        if self.calls == 1:
            return Plan(kind="act", thought="look it up", tool="echo", args={"q": 1})
        return Plan(kind="finish", thought="got it", answer="done")


class EchoTool:
    name = "echo"

    def run(self, args: dict[str, Any]) -> Observation:
        return Observation(tool="echo", ok=True, output=args)


@pytest.fixture
def emitted() -> list[dict[str, Any]]:
    loop = AgentLoop(TwoStepPlanner(), tools={"echo": EchoTool()})
    loop.run("pull the Q3 numbers into the table")
    return loop.events


def test_every_emitted_event_validates_against_session_event(
    emitted: list[dict[str, Any]],
) -> None:
    assert emitted
    for event in emitted:
        SessionEvent.model_validate(event)


def test_emitted_events_use_a_declared_event_type(
    emitted: list[dict[str, Any]],
) -> None:
    allowed = {e.value for e in EventType}
    assert {e["type"] for e in emitted} <= allowed


def test_the_actor_is_an_agent_in_a_declared_role(
    emitted: list[dict[str, Any]],
) -> None:
    for event in emitted:
        actor = event["actor"]
        assert actor["kind"] == ActorKind.agent.value
        assert actor["role"] in {r.value for r in ParticipantRole}


def test_seq_is_left_for_the_session_service_to_allocate(
    emitted: list[dict[str, Any]],
) -> None:
    assert all(e["seq"] is None for e in emitted)


def test_event_ids_are_unique_and_sortable(
    emitted: list[dict[str, Any]],
) -> None:
    ids = [e["event_id"] for e in emitted]

    assert len(ids) == len(set(ids))
    assert all(i.startswith("evt_") for i in ids)
    # ULIDs are lexicographically sortable, so emission order is recoverable
    assert ids == sorted(ids)


def test_run_context_events_still_validate_against_the_contract() -> None:
    """Rebinding session and root per run must not break the event shape."""
    loop = AgentLoop(TwoStepPlanner(), tools={"echo": EchoTool()})
    state = loop.run(
        "pull the Q3 numbers into the table",
        session_id="ses_live",
        root_instruction_event_id="evt_root",
    )

    assert state["events"]
    for event in state["events"]:
        SessionEvent.model_validate(event)
        assert event["session_id"] == "ses_live"
        assert event["causality"]["root_instruction"] == "evt_root"


def test_event_ids_stay_monotonic_across_consecutive_runs() -> None:
    loop = AgentLoop(TwoStepPlanner(), tools={"echo": EchoTool()})
    loop.run("one", session_id="ses_a")
    loop.run("two", session_id="ses_b")

    ids = [e["event_id"] for e in loop.events]
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids)


def test_causality_carries_the_root_instruction() -> None:
    sink = ListSink()
    emitter = EventEmitter(
        sink,
        session_id="ses_1",
        agent_id="agent_1",
        display_name="Agent",
        root_instruction="evt_root",
    )
    emitter.agent_step(index=0, phase="plan", thought="x")

    event = sink.events[0]
    SessionEvent.model_validate(event)
    assert event["causality"]["root_instruction"] == "evt_root"


def test_a_parent_event_is_recorded_when_given() -> None:
    sink = ListSink()
    emitter = EventEmitter(
        sink, session_id="ses_1", agent_id="a", display_name="Agent"
    )
    parent = emitter.agent_step(index=0, phase="plan")
    child = emitter.agent_step(index=0, phase="act", parent_event=parent["event_id"])

    assert child["causality"]["parent_event"] == parent["event_id"]
    SessionEvent.model_validate(child)


def test_extra_fields_are_rejected_by_the_contract() -> None:
    """model_config forbids extras, so a stray key must fail loudly."""
    sink = ListSink()
    emitter = EventEmitter(
        sink, session_id="ses_1", agent_id="a", display_name="Agent"
    )
    event = emitter.agent_step(index=0, phase="plan")
    event["unexpected"] = True

    with pytest.raises(Exception):
        SessionEvent.model_validate(event)


def test_timestamps_are_utc_with_millisecond_precision() -> None:
    ts = utc_now_iso()

    assert ts.endswith("Z")
    assert len(ts.split(".")[-1]) == 4  # three digits plus the Z


def test_event_ids_are_distinct_across_rapid_calls() -> None:
    ids = [new_event_id() for _ in range(1000)]

    assert len(set(ids)) == 1000


def test_event_ids_stay_sortable_inside_one_millisecond() -> None:
    """Generation is monotonic, so emission order survives a burst."""
    ids = [new_event_id() for _ in range(1000)]

    assert ids == sorted(ids)


def test_event_ids_are_monotonic_across_threads() -> None:
    import threading

    collected: list[list[str]] = []
    lock = threading.Lock()

    def worker() -> None:
        mine = [new_event_id() for _ in range(200)]
        with lock:
            collected.append(mine)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    flat = [i for batch in collected for i in batch]
    assert len(set(flat)) == len(flat)
    for batch in collected:
        assert batch == sorted(batch)
