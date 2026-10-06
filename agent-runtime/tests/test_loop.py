"""Tests for the LangGraph plan, act, observe loop.

Linear: DAT-18. Owner: Shriram Dundigalla.
"""

from __future__ import annotations

from typing import Any

import pytest

from runtime.loop import (
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
