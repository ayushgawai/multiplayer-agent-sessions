"""LangGraph plan, act, observe loop for the agent runtime.

Linear: DAT-18. Owner: Shriram Dundigalla.

Three nodes and one conditional edge:

    plan -> act -> observe -> plan | END

`plan` asks the planner what to do next. `act` runs the named tool. `observe`
folds the result into the step list and decides whether to go round again.
Every transition emits one agent_step SessionEvent, so the event log alone is
enough to replay what the agent did and why.

The step cap is hard. It is checked before planning and again on the edge out
of observe, so a planner that never returns a finish plan still terminates and
says so in `halted_reason` rather than running forever.

Cancellation is a terminal node, not an exception. Every edge routes to it
when the token is set, so a cancelled run still returns the steps it had
already completed and the events it had already emitted.

Tools arrive under DAT-19. The loop takes a registry and treats an unknown
tool as a failed observation rather than an exception, which keeps one bad
plan from killing the run.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from runtime.events import EventEmitter, ListSink, RecordingSink
from runtime.state import AgentState, Observation, Planner, Step, Tool

DEFAULT_MAX_STEPS = 12

DEFAULT_SESSION_ID = "ses_local"

HALT_STEP_CAP = "step_cap_reached"
HALT_PLANNER_FINISHED = "planner_finished"
HALT_CANCELLED = "cancelled"


class CancellationToken:
    """Cooperative stop signal checked between nodes.

    Full interruption semantics, including cancelling inside a long tool call,
    belong to the interrupt work that follows. This is the seam it plugs into.
    """

    def __init__(self) -> None:
        self._cancelled = False
        self.reason: str | None = None

    def cancel(self, reason: str = "interrupted") -> None:
        self._cancelled = True
        self.reason = reason

    @property
    def cancelled(self) -> bool:
        return self._cancelled


class AgentLoop:
    """Compiles and runs the plan, act, observe graph for one instruction."""

    def __init__(
        self,
        planner: Planner,
        *,
        tools: dict[str, Tool] | None = None,
        emitter: EventEmitter | None = None,
        max_steps: int = DEFAULT_MAX_STEPS,
        token: CancellationToken | None = None,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.planner = planner
        self.tools = tools or {}
        base = emitter or EventEmitter(
            ListSink(),
            session_id=DEFAULT_SESSION_ID,
            agent_id="agent_1",
            display_name="Agent",
        )
        # Everything the loop emits goes through one recorder, including events
        # bound for a caller's own sink, so `events` is the same stream the
        # sink saw rather than a second one kept alongside it.
        self.sink = RecordingSink(base.sink)
        self.emitter = base.derive(sink=self.sink)
        self.max_steps = max_steps
        self.token = token or CancellationToken()
        self.graph = self._build().compile()

    def _emitter_for(self, state: AgentState) -> EventEmitter:
        """An emitter carrying this run's session and root instruction.

        Built from state on every call rather than stored on the loop, so no
        run context survives into the next run and two loops sharing an
        emitter cannot overwrite each other's.
        """
        return self.emitter.derive(
            session_id=state.get("session_id"),
            root_instruction=state.get("root_instruction_event_id"),
        )

    # nodes

    def _plan(self, state: AgentState) -> dict[str, Any]:
        steps = state.get("steps", [])
        plan = self.planner.plan(state["instruction"], steps)
        self._emitter_for(state).agent_step(
            index=state.get("step_count", 0),
            phase="plan",
            thought=plan.thought,
            tool=plan.tool,
            args=plan.args if plan.kind == "act" else None,
        )
        return {"plan": plan}

    def _act(self, state: AgentState) -> dict[str, Any]:
        plan = state.get("plan")
        if plan is None or plan.kind == "finish":
            return {"observation": None}

        tool = self.tools.get(plan.tool or "")
        if tool is None:
            observation = Observation(
                tool=plan.tool or "",
                ok=False,
                error=f"unknown tool: {plan.tool}",
            )
        else:
            try:
                observation = tool.run(plan.args)
            except Exception as exc:  # a tool must not take the run down
                observation = Observation(
                    tool=plan.tool or "",
                    ok=False,
                    error=f"{type(exc).__name__}: {exc}",
                )

        self._emitter_for(state).agent_step(
            index=state.get("step_count", 0),
            phase="act",
            thought=plan.thought,
            tool=observation.tool,
            args=plan.args,
            ok=observation.ok,
            error=observation.error,
        )
        return {"observation": observation}

    def _observe(self, state: AgentState) -> dict[str, Any]:
        plan = state.get("plan")
        observation = state.get("observation")
        index = state.get("step_count", 0)
        steps = list(state.get("steps", []))
        emitter = self._emitter_for(state)

        if plan is not None and plan.kind == "finish":
            event = emitter.agent_step(
                index=index,
                phase="observe",
                thought=plan.thought,
                output=plan.answer,
            )
            steps.append(
                Step(
                    index=index,
                    thought=plan.thought,
                    tool=None,
                    args={},
                    ok=True,
                    output=plan.answer,
                    error=None,
                    event_id=event["event_id"],
                )
            )
            return {
                "steps": steps,
                "step_count": index + 1,
                "done": True,
                "answer": plan.answer,
                "halted_reason": HALT_PLANNER_FINISHED,
            }

        assert observation is not None
        event = emitter.agent_step(
            index=index,
            phase="observe",
            thought=plan.thought if plan else "",
            tool=observation.tool,
            ok=observation.ok,
            output=observation.output,
            error=observation.error,
        )
        steps.append(
            Step(
                index=index,
                thought=plan.thought if plan else "",
                tool=observation.tool,
                args=plan.args if plan else {},
                ok=observation.ok,
                output=observation.output,
                error=observation.error,
                event_id=event["event_id"],
            )
        )
        return {"steps": steps, "step_count": index + 1, "done": False}

    def _halt_on_cap(self, state: AgentState) -> dict[str, Any]:
        self._emitter_for(state).agent_step(
            index=state.get("step_count", 0),
            phase="halt",
            thought=f"step cap of {state.get('max_steps')} reached",
            error=HALT_STEP_CAP,
        )
        return {"done": True, "halted_reason": HALT_STEP_CAP}

    def _halt_on_cancel(self, state: AgentState) -> dict[str, Any]:
        self._emitter_for(state).agent_step(
            index=state.get("step_count", 0),
            phase="halt",
            thought=self.token.reason or HALT_CANCELLED,
            error=HALT_CANCELLED,
        )
        return {"done": True, "halted_reason": HALT_CANCELLED}

    # edges

    def _enter(self, state: AgentState) -> str:
        """Cancelling before the run starts still produces a halt event."""
        return "cancelled" if self.token.cancelled else "planner"

    def _after_planner(self, state: AgentState) -> str:
        return "cancelled" if self.token.cancelled else "actor"

    def _after_actor(self, state: AgentState) -> str:
        return "cancelled" if self.token.cancelled else "observer"

    def _should_continue(self, state: AgentState) -> str:
        # A run that has already finished is finished; a late cancellation
        # does not retroactively make a completed answer a cancelled one.
        if state.get("done"):
            return END
        if self.token.cancelled:
            return "cancelled"
        if state.get("step_count", 0) >= state.get("max_steps", self.max_steps):
            return "cap"
        return "planner"

    def _build(self) -> StateGraph:
        # Node names must not collide with state keys, so the nodes are named
        # for the actor rather than the phase: planner, actor, observer.
        #
        # Cancellation is a terminal node rather than an exception, so the
        # state LangGraph has accumulated - the completed steps above all -
        # survives into the returned state instead of being unwound.
        graph: StateGraph = StateGraph(AgentState)
        graph.add_node("planner", self._plan)
        graph.add_node("actor", self._act)
        graph.add_node("observer", self._observe)
        graph.add_node("cap", self._halt_on_cap)
        graph.add_node("cancelled", self._halt_on_cancel)

        graph.add_conditional_edges(
            START,
            self._enter,
            {"planner": "planner", "cancelled": "cancelled"},
        )
        graph.add_conditional_edges(
            "planner",
            self._after_planner,
            {"actor": "actor", "cancelled": "cancelled"},
        )
        graph.add_conditional_edges(
            "actor",
            self._after_actor,
            {"observer": "observer", "cancelled": "cancelled"},
        )
        graph.add_conditional_edges(
            "observer",
            self._should_continue,
            {
                "planner": "planner",
                "cap": "cap",
                "cancelled": "cancelled",
                END: END,
            },
        )
        graph.add_edge("cap", END)
        graph.add_edge("cancelled", END)
        return graph

    # entry point

    def run(
        self,
        instruction: str,
        *,
        session_id: str | None = None,
        run_id: str = "run_local",
        root_instruction_event_id: str | None = None,
    ) -> AgentState:
        """Run one instruction to completion, the step cap, or cancellation."""
        # session_id and root_instruction_event_id are read back out of state
        # by every node, so the run's context reaches the emitter without
        # being stored on the loop and outliving the run.
        initial: AgentState = {
            "session_id": session_id or self.emitter.session_id,
            "run_id": run_id,
            "instruction": instruction,
            "root_instruction_event_id": root_instruction_event_id,
            "max_steps": self.max_steps,
            "plan": None,
            "observation": None,
            "steps": [],
            "step_count": 0,
            "done": False,
            "answer": None,
            "halted_reason": None,
        }
        # recursion_limit guards the graph itself; the step cap is the real
        # bound, so give LangGraph enough room to reach it and halt cleanly.
        config = {"recursion_limit": self.max_steps * 4 + 10}
        final: AgentState = self.graph.invoke(initial, config=config)
        final["events"] = self.events
        return final

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self.sink.events)
