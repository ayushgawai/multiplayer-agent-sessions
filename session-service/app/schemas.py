"""Pydantic v2 contracts for Multiplayer Agent Sessions.

Frozen for Progress Report 1. Changes require an ADR under docs/decisions/.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ActorKind(str, Enum):
    human = "human"
    agent = "agent"
    system = "system"


class ParticipantRole(str, Enum):
    author = "author"
    reviewer = "reviewer"
    observer = "observer"


class EventType(str, Enum):
    DOC_UPDATE = "doc_update"
    INSTRUCTION = "instruction"
    AGENT_STEP = "agent_step"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    INTERRUPT = "interrupt"
    HANDOFF = "handoff"
    ROLLBACK = "rollback"
    JOIN = "join"
    LEAVE = "leave"
    ARBITRATION = "arbitration"
    REJECTED = "rejected"


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ActorKind
    id: str
    display_name: str
    role: ParticipantRole


class Causality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_event: Optional[str] = None
    root_instruction: Optional[str] = None


class Labels(BaseModel):
    """Annotation fields. Null in production; written by annotators."""

    model_config = ConfigDict(extra="forbid")

    serves_participant: Optional[str] = None
    conflict_group: Optional[str] = None
    conflict_resolution: Optional[str] = None
    mast_failure: Optional[str] = None


class SessionEvent(BaseModel):
    """Append-only event. seq is assigned by the session service on write."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    session_id: str
    seq: Optional[int] = None
    ts: datetime
    actor: Actor
    type: EventType
    payload: dict[str, Any]
    causality: Causality = Field(default_factory=Causality)
    labels: Optional[Labels] = None


class SessionEventCreate(BaseModel):
    """Client write shape: seq is allocated server-side."""

    model_config = ConfigDict(extra="forbid")

    event_id: Optional[str] = None
    actor: Actor
    type: EventType
    payload: dict[str, Any]
    causality: Causality = Field(default_factory=Causality)


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    scenario_id: Optional[str] = None


class CreateSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    join_code: str


class JoinSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    join_code: str
    display_name: str
    role: ParticipantRole


class JoinSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participant_id: str
    snapshot: dict[str, Any]
    catchup_summary: Optional[str] = None


class EventsPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[SessionEvent]
    next_seq: int


class AppendEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    seq: int


class RollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_seq: int


class RollbackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot: dict[str, Any]
    rolled_back_events: list[SessionEvent]


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inputs: dict[str, Any]
    params: dict[str, Any] = Field(default_factory=dict)


class PredictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    model_id: str
    version: str
    outputs: dict[str, Any]
    latency_ms: float
    seed: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: Literal[True] = True
    version: str


class CatchupExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    context_spans: list[str]
    reference_summary: str
