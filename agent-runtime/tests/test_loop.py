"""Tests for the LangGraph plan, act, observe loop.

Linear: DAT-18. Owner: Shriram Dundigalla.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest

from runtime.events import EventEmitter, ListSink
from runtime.loop import (
    DEFAULT_SESSION_ID,
    HALT_CANCELLED,
    HALT_PLANNER_FINISHED,
    HALT_STEP_CAP,
    AgentLoop,
    CancellationToken,
)
from runtime.state import Observation, Plan, Step


class ScriptedPlanner:
    """Acts n times, then finishes."""

    def __init__(self, acts: int = 2, tool: str = "echo") -> None:
        self.acts = acts
        self.tool = tool
        self.calls = 0
        self.seen_steps: list[int] = []

    def plan(self, instruction: str, steps: list[Step]) -> Plan:
        self.calls += 1
        self.seen_steps.append(len(steps))
        if self.calls <= self.acts:
            return Plan(
                kind="act",
                thought=f"step {self.calls}",
                tool=self.tool,
                args={"n": self.calls},
            )
        return Plan(kind="finish", thought="done", answer="final answer")


class NeverFinishes:
    """Always asks to act. Exists to prove the cap is hard."""

    def __init__(self) -> None:
        self.calls = 0

    def plan(self, instruction: str, steps: list[Step]) -> Plan:
        self.calls += 1
        return Plan(kind="act", thought="again", tool="echo", args={})


class EchoTool:
    name = "echo"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run(self, args: dict[str, Any]) -> Observation:
        self.calls.append(args)
        return Observation(tool="echo", ok=True, output=args)


class ExplodingTool:
    name = "boom"

    def run(self, args: dict[str, Any]) -> Observation:
        raise RuntimeError("tool blew up")


def make_loop(planner: Any, **kw: Any) -> AgentLoop:
    kw.setdefault("tools", {"echo": EchoTool(), "boom": ExplodingTool()})
    return AgentLoop(planner, **kw)


def test_loop_runs_plan_act_observe_until_the_planner_finishes() -> None:
    loop = make_loop(ScriptedPlanner(acts=2))

    state = loop.run("pull the Q3 numbers into the table")

    assert state["done"] is True
    assert state["answer"] == "final answer"
    assert state["halted_reason"] == HALT_PLANNER_FINISHED
    assert state["step_count"] == 3


def test_each_transition_emits_exactly_one_agent_step_event() -> None:
    loop = make_loop(ScriptedPlanner(acts=2))
    loop.run("do it")

    phases = [e["payload"]["phase"] for e in loop.events]
    # two full passes, then a plan and observe for the finish
    assert phases == [
        "plan",
        "act",
        "observe",
        "plan",
        "act",
        "observe",
        "plan",
        "observe",
    ]
    assert all(e["type"] == "agent_step" for e in loop.events)


def test_the_planner_sees_the_steps_so_far() -> None:
    planner = ScriptedPlanner(acts=3)
    make_loop(planner).run("do it")

    assert planner.seen_steps == [0, 1, 2, 3]


def test_tools_receive_the_planned_arguments() -> None:
    echo = EchoTool()
    make_loop(ScriptedPlanner(acts=2), tools={"echo": echo}).run("do it")

    assert echo.calls == [{"n": 1}, {"n": 2}]


def test_step_cap_is_hard_when_the_planner_never_finishes() -> None:
    planner = NeverFinishes()
    loop = make_loop(planner, max_steps=4)

    state = loop.run("loop forever please")

    assert state["done"] is True
    assert state["halted_reason"] == HALT_STEP_CAP
    assert state["step_count"] == 4
    assert planner.calls == 4


def test_step_cap_of_one_still_terminates() -> None:
    loop = make_loop(NeverFinishes(), max_steps=1)

    state = loop.run("do it")

    assert state["halted_reason"] == HALT_STEP_CAP
    assert state["step_count"] == 1


def test_a_zero_step_cap_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_steps"):
        make_loop(ScriptedPlanner(), max_steps=0)


def test_reaching_the_cap_is_recorded_in_the_event_log() -> None:
    loop = make_loop(NeverFinishes(), max_steps=2)
    loop.run("do it")

    halts = [e for e in loop.events if e["payload"]["phase"] == "halt"]
    assert len(halts) == 1
    assert halts[0]["payload"]["error"] == HALT_STEP_CAP


def test_an_unknown_tool_is_a_failed_observation_not_a_crash() -> None:
    loop = make_loop(ScriptedPlanner(acts=1, tool="nope"), max_steps=5)

    state = loop.run("do it")

    assert state["done"] is True
    failed = [s for s in state["steps"] if s.get("ok") is False]
    assert len(failed) == 1
    assert "unknown tool: nope" in failed[0]["error"]


def test_a_tool_that_raises_is_a_failed_observation_not_a_crash() -> None:
    loop = make_loop(ScriptedPlanner(acts=1, tool="boom"), max_steps=5)

    state = loop.run("do it")

    assert state["done"] is True
    failed = [s for s in state["steps"] if s.get("ok") is False]
    assert "tool blew up" in failed[0]["error"]


def test_the_loop_continues_after_a_failed_step() -> None:
    loop = make_loop(ScriptedPlanner(acts=2, tool="boom"), max_steps=6)

    state = loop.run("do it")

    assert state["halted_reason"] == HALT_PLANNER_FINISHED
    assert sum(1 for s in state["steps"] if s.get("ok") is False) == 2


def test_cancellation_stops_the_loop_and_is_recorded() -> None:
    token = CancellationToken()
    planner = ScriptedPlanner(acts=10)
    loop = make_loop(planner, max_steps=20, token=token)
    token.cancel("reviewer pulled the handbrake")

    state = loop.run("do it")

    assert state["done"] is True
    assert state["halted_reason"] == HALT_CANCELLED
    assert planner.calls == 0
    halts = [e for e in loop.events if e["payload"]["phase"] == "halt"]
    assert halts[0]["payload"]["thought"] == "reviewer pulled the handbrake"


def test_cancellation_midway_leaves_the_steps_already_taken() -> None:
    token = CancellationToken()

    class CancelAfterTwo:
        def __init__(self) -> None:
            self.calls = 0

        def plan(self, instruction: str, steps: list[Step]) -> Plan:
            self.calls += 1
            if self.calls == 3:
                token.cancel("stop now")
            return Plan(kind="act", thought="go", tool="echo", args={})

    loop = make_loop(CancelAfterTwo(), max_steps=20, token=token)
    state = loop.run("do it")

    assert state["halted_reason"] == HALT_CANCELLED
    observed = [e for e in loop.events if e["payload"]["phase"] == "observe"]
    assert len(observed) == 2


def test_every_step_records_the_event_that_logged_it() -> None:
    loop = make_loop(ScriptedPlanner(acts=2))

    state = loop.run("do it")

    ids = {e["event_id"] for e in loop.events}
    for step in state["steps"]:
        assert step["event_id"] in ids


# run context: session and root instruction


def test_every_emitted_event_carries_the_runs_session_and_root() -> None:
    loop = make_loop(ScriptedPlanner(acts=2))

    loop.run(
        "instruction",
        session_id="ses_expected",
        root_instruction_event_id="evt_expected",
    )

    assert len(loop.events) == 8
    for event in loop.events:
        assert event["session_id"] == "ses_expected"
        assert event["causality"]["root_instruction"] == "evt_expected"


def test_the_halt_event_carries_the_run_context_too() -> None:
    """The cap event is emitted outside the three main nodes, so check it."""
    loop = make_loop(NeverFinishes(), max_steps=2)

    loop.run("do it", session_id="ses_cap", root_instruction_event_id="evt_cap")

    halt = next(e for e in loop.events if e["payload"]["phase"] == "halt")
    assert halt["session_id"] == "ses_cap"
    assert halt["causality"]["root_instruction"] == "evt_cap"


def test_consecutive_runs_do_not_leak_context_into_each_other() -> None:
    loop = make_loop(ScriptedPlanner(acts=1))

    first = loop.run("one", session_id="ses_a", root_instruction_event_id="evt_a")
    second = loop.run("two", session_id="ses_b", root_instruction_event_id="evt_b")

    tail = loop.events[len(first["events"]) :]
    assert {e["session_id"] for e in first["events"]} == {"ses_a"}
    assert {e["causality"]["root_instruction"] for e in first["events"]} == {"evt_a"}
    assert {e["session_id"] for e in tail} == {"ses_b"}
    assert {e["causality"]["root_instruction"] for e in tail} == {"evt_b"}
    assert len(second["events"]) == len(first["events"]) + len(tail)


def test_a_run_without_context_falls_back_to_the_emitter_default() -> None:
    loop = make_loop(ScriptedPlanner(acts=1))

    loop.run("no context given")

    assert {e["session_id"] for e in loop.events} == {DEFAULT_SESSION_ID}
    assert {e["causality"]["root_instruction"] for e in loop.events} == {None}


def test_concurrent_loops_keep_their_own_run_context() -> None:
    """Run context lives in graph state, so parallel loops cannot collide."""
    results: dict[str, list[dict[str, Any]]] = {}
    lock = threading.Lock()

    def run_one(suffix: str) -> None:
        loop = make_loop(ScriptedPlanner(acts=3))
        state = loop.run(
            "do it",
            session_id=f"ses_{suffix}",
            root_instruction_event_id=f"evt_{suffix}",
        )
        with lock:
            results[suffix] = state["events"]

    threads = [threading.Thread(target=run_one, args=(s,)) for s in "abcdefgh"]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 8
    for suffix, events in results.items():
        assert events
        assert {e["session_id"] for e in events} == {f"ses_{suffix}"}
        assert {e["causality"]["root_instruction"] for e in events} == {
            f"evt_{suffix}"
        }


# one authoritative event stream


def test_a_supplied_emitter_still_reports_through_the_loop() -> None:
    external = ListSink()
    emitter = EventEmitter(
        external, session_id="ses_x", agent_id="agent_1", display_name="Agent"
    )
    loop = make_loop(ScriptedPlanner(acts=2), emitter=emitter)

    state = loop.run("do it")

    assert len(external.events) == 8
    assert loop.events == external.events
    assert state["events"] == external.events


def test_a_sink_without_an_events_list_is_still_recorded() -> None:
    """The session service sink only writes; it has nothing to read back."""

    class WriteOnlySink:
        def __init__(self) -> None:
            self.count = 0

        def emit(self, event: dict[str, Any]) -> None:
            self.count += 1

    sink = WriteOnlySink()
    emitter = EventEmitter(
        sink, session_id="ses_x", agent_id="agent_1", display_name="Agent"
    )
    loop = make_loop(ScriptedPlanner(acts=2), emitter=emitter)

    state = loop.run("do it")

    assert sink.count == 8
    assert len(loop.events) == 8
    assert len(state["events"]) == 8


def test_a_supplied_emitter_is_not_mutated_by_the_loop() -> None:
    external = ListSink()
    emitter = EventEmitter(
        external, session_id="ses_x", agent_id="agent_1", display_name="Agent"
    )
    loop = make_loop(ScriptedPlanner(acts=1), emitter=emitter)

    loop.run("do it", session_id="ses_run", root_instruction_event_id="evt_run")

    assert emitter.sink is external
    assert emitter.session_id == "ses_x"
    assert emitter.root_instruction is None


# cancellation


def test_cancellation_before_the_first_step_returns_a_usable_state() -> None:
    token = CancellationToken()
    planner = ScriptedPlanner(acts=10)
    loop = make_loop(planner, max_steps=20, token=token)
    token.cancel("stopped before we began")

    state = loop.run("do it", session_id="ses_c", root_instruction_event_id="evt_c")

    assert planner.calls == 0
    assert state["steps"] == []
    assert state["done"] is True
    assert state["halted_reason"] == HALT_CANCELLED
    assert len(state["events"]) == 1
    assert state["events"][0]["payload"]["phase"] == "halt"
    assert state["events"][0]["session_id"] == "ses_c"


def test_cancellation_after_two_steps_keeps_those_steps_and_events() -> None:
    token = CancellationToken()

    class CancelOnTheThirdPlan:
        def __init__(self) -> None:
            self.calls = 0

        def plan(self, instruction: str, steps: list[Step]) -> Plan:
            self.calls += 1
            if self.calls == 3:
                token.cancel("stop now")
            return Plan(kind="act", thought="go", tool="echo", args={})

    loop = make_loop(CancelOnTheThirdPlan(), max_steps=20, token=token)

    state = loop.run("do it")

    assert len(state["steps"]) == 2
    assert [s["index"] for s in state["steps"]] == [0, 1]
    assert state["done"] is True
    assert state["halted_reason"] == HALT_CANCELLED
    assert state["events"] == loop.events
    assert len(state["events"]) == 8


def test_cancellation_emits_exactly_one_halt_event() -> None:
    token = CancellationToken()

    class CancelOnTheSecondPlan:
        def __init__(self) -> None:
            self.calls = 0

        def plan(self, instruction: str, steps: list[Step]) -> Plan:
            self.calls += 1
            if self.calls == 2:
                token.cancel("enough")
            return Plan(kind="act", thought="go", tool="echo", args={})

    loop = make_loop(CancelOnTheSecondPlan(), max_steps=20, token=token)
    loop.run("do it")

    halts = [e for e in loop.events if e["payload"]["phase"] == "halt"]
    assert len(halts) == 1
    assert halts[0]["payload"]["error"] == HALT_CANCELLED
    assert halts[0]["payload"]["thought"] == "enough"


def test_cancellation_during_the_final_plan_wins_over_the_finish() -> None:
    """A stop that lands before the answer is observed is a cancellation.

    The finish plan never reaches observe, so there is no recorded answer to
    report. Calling the run finished would claim a result the loop never
    committed.
    """
    token = CancellationToken()

    class FinishButCancelFirst:
        def __init__(self) -> None:
            self.calls = 0

        def plan(self, instruction: str, steps: list[Step]) -> Plan:
            self.calls += 1
            if self.calls == 2:
                token.cancel("too late")
                return Plan(kind="finish", thought="done", answer="final answer")
            return Plan(kind="act", thought="go", tool="echo", args={})

    loop = make_loop(FinishButCancelFirst(), max_steps=20, token=token)
    state = loop.run("do it")

    assert state["halted_reason"] == HALT_CANCELLED
    assert state["answer"] is None
    assert len(state["steps"]) == 1
    assert len([e for e in loop.events if e["payload"]["phase"] == "halt"]) == 1


def test_a_run_that_already_finished_is_not_relabelled_as_cancelled() -> None:
    """Cancelling after observe has recorded the answer changes nothing."""
    token = CancellationToken()
    loop = make_loop(ScriptedPlanner(acts=1), max_steps=20, token=token)

    state = loop.run("do it")
    token.cancel("after the fact")

    assert state["halted_reason"] == HALT_PLANNER_FINISHED
    assert state["answer"] == "final answer"
    assert not [e for e in loop.events if e["payload"]["phase"] == "halt"]


def test_every_run_returns_its_events_in_the_state() -> None:
    for planner, kw in (
        (ScriptedPlanner(acts=2), {}),
        (NeverFinishes(), {"max_steps": 3}),
    ):
        loop = make_loop(planner, **kw)
        state = loop.run("do it")
        assert state["events"] == loop.events
        assert state["events"]
