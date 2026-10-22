"""Agent loop state and the planner contract.

Linear: DAT-18. Owner: Shriram Dundigalla.

The loop state is a plain TypedDict so LangGraph can merge node returns
without any custom reducer. Everything the audit trail needs is derivable
from it: each step carries the action that was planned, what came back, and
the event id that recorded it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, TypedDict

# A plan either names an action to run or declares the task finished.
PlanKind = Literal["act", "finish"]


@dataclass(frozen=True)
class Plan:
    """What the planner decided to do next."""

    kind: PlanKind
    thought: str = ""
    tool: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    answer: str | None = None

    def __post_init__(self) -> None:
        if self.kind == "act" and not self.tool:
            raise ValueError("a plan to act must name a tool")


@dataclass(frozen=True)
class Observation:
    """What came back from acting on a plan."""

    tool: str
    ok: bool
    output: Any = None
    error: str | None = None


class Step(TypedDict, total=False):
    """One completed pass through plan, act and observe."""

    index: int
    thought: str
    tool: str | None
    args: dict[str, Any]
    ok: bool
    output: Any
    error: str | None
    event_id: str


class AgentState(TypedDict, total=False):
    """State threaded through the plan, act and observe nodes."""

    session_id: str
    run_id: str
    instruction: str
    root_instruction_event_id: str | None
    max_steps: int

    plan: Plan | None
    observation: Observation | None
    steps: list[Step]
    step_count: int

    done: bool
    answer: str | None
    halted_reason: str | None
    events: list[dict[str, Any]]


class Planner(Protocol):
    """Chooses the next action from the instruction and what has happened.

    A planner must not raise for a model side failure. It returns a finish
    plan carrying the problem in `thought` so the loop can close cleanly and
    the audit trail keeps the reason.
    """

    def plan(self, instruction: str, steps: list[Step]) -> Plan: ...


class Tool(Protocol):
    """One of the five fixed tools. Implemented under DAT-19."""

    @property
    def name(self) -> str: ...

    def run(self, args: dict[str, Any]) -> Observation: ...
