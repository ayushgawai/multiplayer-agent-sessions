"""Event-based smoke contract for M1 catch-up summarization.

This is NOT the frozen QMSum-shaped ``CatchupExample`` in
``session-service/app/schemas.py`` (``query``, ``context_spans``, ``reference_summary``)
and it does not change it. That model describes the QMSum ``m1_v1`` splits. The model here
describes ordered session events with stable ids, so it can be converted to the
``m1-input-v1`` / ``m1-output-v1`` contract from DAT-55 (see ``loader.to_m1_input`` and
``loader.gold_reference``).

Smoke fixtures are synthetic and exist only to exercise the pipeline before full training.
They are never an evaluation test split.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "m1-smoke-v1"

# Wire event types from session-service (EventType). Mirrored here so data/ has no
# dependency on session-service; a test checks the two sets stay equal.
EVENT_TYPES = (
    "doc_update",
    "instruction",
    "agent_step",
    "tool_call",
    "tool_result",
    "interrupt",
    "handoff",
    "rollback",
    "join",
    "leave",
    "arbitration",
    "rejected",
)
EventTypeName = Literal[
    "doc_update",
    "instruction",
    "agent_step",
    "tool_call",
    "tool_result",
    "interrupt",
    "handoff",
    "rollback",
    "join",
    "leave",
    "arbitration",
    "rejected",
]

# Category names and order follow m1-output-v1.
CATEGORIES = ("completed", "in_progress", "blocked", "decisions", "pending_actions")
CategoryName = Literal["completed", "in_progress", "blocked", "decisions", "pending_actions"]

# Per-event gold status label -> m1-output-v1 category.
StatusLabel = Literal["completed", "in_progress", "blocked", "decision", "pending_action"]
LABEL_TO_CATEGORY: dict[str, str] = {
    "completed": "completed",
    "in_progress": "in_progress",
    "blocked": "blocked",
    "decision": "decisions",
    "pending_action": "pending_actions",
}


def _require_nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


NonBlank = Annotated[str, AfterValidator(_require_nonblank)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SmokeEvent(_Strict):
    """One ordered session event. ``source_event_id`` is stable across regenerations."""

    source_event_id: NonBlank
    sequence: int = Field(ge=0)
    event_type: EventTypeName
    actor_id: NonBlank | None = None
    text: NonBlank


class Claim(_Strict):
    """One gold summary claim with the events that support it."""

    text: NonBlank
    source_event_ids: list[NonBlank] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        if len(self.source_event_ids) != len(set(self.source_event_ids)):
            raise ValueError("source_event_ids must be unique within a claim")
        return self


class Reference(_Strict):
    """Gold structured summary in the m1-output-v1 shape (without candidate_id)."""

    completed: list[Claim] = Field(default_factory=list)
    in_progress: list[Claim] = Field(default_factory=list)
    blocked: list[Claim] = Field(default_factory=list)
    decisions: list[Claim] = Field(default_factory=list)
    pending_actions: list[Claim] = Field(default_factory=list)


class CriticalFact(_Strict):
    """A fact a good catch-up must cover, with the events that prove it."""

    fact_id: NonBlank
    category: CategoryName
    text: NonBlank
    evidence_event_ids: list[NonBlank] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        if len(self.evidence_event_ids) != len(set(self.evidence_event_ids)):
            raise ValueError("evidence_event_ids must be unique within a fact")
        return self


class CatchupExample(_Strict):
    """Event-based smoke example (``m1-smoke-v1``). See the module docstring."""

    schema_version: Literal["m1-smoke-v1"] = SCHEMA_VERSION
    example_id: NonBlank
    session_id: NonBlank
    query: NonBlank
    events: list[SmokeEvent] = Field(min_length=1)
    event_labels: dict[NonBlank, StatusLabel] = Field(default_factory=dict)
    reference: Reference
    critical_facts: list[CriticalFact] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        ids = [e.source_event_id for e in self.events]
        if len(ids) != len(set(ids)):
            raise ValueError("events must have unique source_event_id values")
        seqs = [e.sequence for e in self.events]
        if seqs != sorted(seqs) or len(seqs) != len(set(seqs)):
            raise ValueError("events must have unique, strictly ascending sequence values")
        known = set(ids)

        unknown_labels = sorted(set(self.event_labels) - known)
        if unknown_labels:
            raise ValueError(f"event_labels reference unknown event ids: {unknown_labels}")

        def check_refs(what: str, category: str, refs: list[str]) -> None:
            missing = [r for r in refs if r not in known]
            if missing:
                raise ValueError(f"{what} cites event ids not in events: {missing}")
            for ref in refs:
                label = self.event_labels.get(ref)
                if label is not None and LABEL_TO_CATEGORY[label] != category:
                    raise ValueError(
                        f"{what} is in category {category!r} but cites {ref} labelled {label!r}"
                    )

        total_claims = 0
        for category in CATEGORIES:
            for i, claim in enumerate(getattr(self.reference, category)):
                total_claims += 1
                check_refs(f"reference.{category}[{i}]", category, claim.source_event_ids)
        if total_claims == 0:
            raise ValueError("reference must contain at least one claim")

        fact_ids = [f.fact_id for f in self.critical_facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("critical_facts must have unique fact_id values")
        for fact in self.critical_facts:
            check_refs(f"critical fact {fact.fact_id}", fact.category, fact.evidence_event_ids)
        return self
