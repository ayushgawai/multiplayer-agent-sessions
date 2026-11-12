"""Frozen M1 input, output, evidence, and text-projection contracts."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

M1_INPUT_VERSION: Literal["m1-input-v1"] = "m1-input-v1"
M1_OUTPUT_VERSION: Literal["m1-output-v1"] = "m1-output-v1"
M1_CATEGORIES = (
    "completed",
    "in_progress",
    "blocked",
    "decisions",
    "pending_actions",
)
M1_EVENT_TYPES = (
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
M1EventType: TypeAlias = Literal[
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
_QMSUM_ID = re.compile(r"^qmsum_(train|val|test)_(\d+)_[sg]\d+$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def _require_nonblank(value: str, *, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


class M1Event(_StrictModel):
    """One ordered event visible to an M1 candidate."""

    event_id: str
    sequence: int = Field(ge=0)
    event_type: M1EventType
    actor_id: str | None = None
    text: str

    @field_validator("event_id", "event_type", "text")
    @classmethod
    def validate_required_text(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "value")
        return _require_nonblank(value, field_name=field_name)

    @field_validator("actor_id")
    @classmethod
    def validate_optional_actor(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_nonblank(value, field_name="actor_id")


class M1MemoryItem(_StrictModel):
    """A human-approved behavioral lesson; never a source of session facts."""

    learning_event_id: str
    text: str

    @field_validator("learning_event_id", "text")
    @classmethod
    def validate_required_text(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "value")
        return _require_nonblank(value, field_name=field_name)


class M1Input(_StrictModel):
    """Common model input for product sessions and adapted QMSum examples."""

    schema_version: Literal["m1-input-v1"] = M1_INPUT_VERSION
    example_id: str
    session_id: str
    query: str
    events: list[M1Event] = Field(min_length=1)
    memory_version: str | None = None
    approved_memory: list[M1MemoryItem] = Field(default_factory=list)

    @field_validator("example_id", "session_id", "query")
    @classmethod
    def validate_required_text(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "value")
        return _require_nonblank(value, field_name=field_name)

    @field_validator("memory_version")
    @classmethod
    def validate_optional_version(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_nonblank(value, field_name="memory_version")

    @model_validator(mode="after")
    def validate_unique_identifiers(self) -> Self:
        event_ids = [event.event_id for event in self.events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("events must have unique event_id values")
        sequences = [event.sequence for event in self.events]
        if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
            raise ValueError("events must have unique sequence values in ascending order")
        memory_ids = [item.learning_event_id for item in self.approved_memory]
        if len(memory_ids) != len(set(memory_ids)):
            raise ValueError("approved_memory must have unique learning_event_id values")
        if self.approved_memory and self.memory_version is None:
            raise ValueError("memory_version is required when approved_memory is present")
        return self


class M1Claim(_StrictModel):
    """One structured catch-up claim with explicit session evidence."""

    text: str
    source_event_ids: list[str] = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _require_nonblank(value, field_name="text")

    @field_validator("source_event_ids")
    @classmethod
    def validate_source_ids(cls, values: list[str]) -> list[str]:
        for value in values:
            _require_nonblank(value, field_name="source_event_ids item")
        if len(values) != len(set(values)):
            raise ValueError("source_event_ids must be unique within a claim")
        return values


class M1Output(_StrictModel):
    """Shared structured output emitted by every M1 candidate."""

    schema_version: Literal["m1-output-v1"] = M1_OUTPUT_VERSION
    example_id: str
    candidate_id: Literal["m1-a", "m1-b", "m1-c", "m1-d"]
    completed: list[M1Claim] = Field(default_factory=list)
    in_progress: list[M1Claim] = Field(default_factory=list)
    blocked: list[M1Claim] = Field(default_factory=list)
    decisions: list[M1Claim] = Field(default_factory=list)
    pending_actions: list[M1Claim] = Field(default_factory=list)

    @field_validator("example_id")
    @classmethod
    def validate_example_id(cls, value: str) -> str:
        return _require_nonblank(value, field_name="example_id")

    def claims(self) -> list[M1Claim]:
        """Return all claims in the frozen category and within-category order."""

        return [claim for category in M1_CATEGORIES for claim in getattr(self, category)]


def validate_m1_pair(model_input: M1Input, model_output: M1Output) -> None:
    """Validate output identity and evidence references against one input."""

    if model_output.example_id != model_input.example_id:
        raise ValueError("input and output example_id values must match")
    allowed_event_ids = {event.event_id for event in model_input.events}
    unknown_event_ids = sorted(
        {
            event_id
            for claim in model_output.claims()
            for event_id in claim.source_event_ids
            if event_id not in allowed_event_ids
        }
    )
    if unknown_event_ids:
        raise ValueError(f"output references unknown source_event_ids: {unknown_event_ids}")

    normalized_claims = [" ".join(claim.text.split()).casefold() for claim in model_output.claims()]
    duplicate_claims = sorted(
        {claim for claim in normalized_claims if normalized_claims.count(claim) > 1}
    )
    if duplicate_claims:
        raise ValueError(f"output contains duplicate claims: {duplicate_claims}")


def project_m1_output_text(model_output: M1Output) -> str:
    """Project structured output to canonical text for ROUGE and BERTScore."""

    return "\n".join(" ".join(claim.text.split()) for claim in model_output.claims())


def session_event_to_m1_event(event: Mapping[str, Any]) -> M1Event:
    """Adapt one SessionEvent JSON object into the frozen M1 event schema."""

    event_type = event.get("type")
    payload = event.get("payload")
    actor = event.get("actor")
    if not isinstance(payload, Mapping):
        raise ValueError("SessionEvent payload must be an object")
    if not isinstance(actor, Mapping):
        raise ValueError("SessionEvent actor must be an object")

    text_value = payload.get("text")
    text = text_value.strip() if isinstance(text_value, str) else ""
    display_name_value = payload.get("display_name", actor.get("display_name", actor.get("id")))
    display_name = str(display_name_value)

    if not text and event_type == "join":
        role = payload.get("role")
        role_suffix = f" as {role}" if isinstance(role, str) and role.strip() else ""
        text = f"{display_name} joined the session{role_suffix}."
    elif not text and event_type == "leave":
        text = f"{display_name} left the session."
    elif not text and event_type == "rejected":
        attempted_type = payload.get("attempted_type", "event")
        reason = payload.get("reason", "unspecified reason")
        text = f"Rejected {attempted_type}: {reason}."
    elif not text:
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        text = f"{event_type}: {payload_json}"

    return M1Event.model_validate(
        {
            "event_id": event.get("event_id"),
            "sequence": event.get("seq"),
            "event_type": event_type,
            "actor_id": actor.get("id"),
            "text": text,
        }
    )


def qmsum_row_to_m1_input(row: Mapping[str, Any]) -> M1Input:
    """Adapt one committed QMSum split row into a deterministic M1 input."""

    example_id = row.get("id")
    if not isinstance(example_id, str):
        raise ValueError("QMSum row id must be a string")
    match = _QMSUM_ID.fullmatch(example_id)
    if match is None:
        raise ValueError("QMSum row id must include split, meeting index, and query index")

    spans = row.get("context_spans")
    if not isinstance(spans, Sequence) or isinstance(spans, (str, bytes)) or not spans:
        raise ValueError("QMSum context_spans must be a non-empty sequence")
    if not all(isinstance(span, str) and span.strip() for span in spans):
        raise ValueError("QMSum context_spans must contain non-blank strings")

    split_name, meeting_index = match.groups()
    events = [
        M1Event(
            event_id=f"{example_id}:span:{index:04d}",
            sequence=index,
            event_type="doc_update",
            text=span,
        )
        for index, span in enumerate(spans)
    ]
    return M1Input.model_validate(
        {
            "example_id": example_id,
            "session_id": f"qmsum:{split_name}:{meeting_index}",
            "query": row.get("query"),
            "events": events,
        }
    )
