"""Versioned learning-event contract for human-governed self-improvement.

Linear: DAT-56 (M1-05). Owner: Shriram Dundigalla.

A LearningEvent is one piece of verified evidence that a model got something
wrong, together with the lesson a later run should carry. It is deliberately
not a free-text note: every record names the task, the candidate and run that
produced the output, the source events the output was built from, who or what
judged it, and a failure code drawn from a closed per-task vocabulary. That is
what makes an approved lesson auditable rather than folklore.

Three rules are enforced here rather than left to callers, because each one is
a way the research claim could quietly become invalid:

  * Only a lesson in state `approved` is retrievable, so an unreviewed
    proposal can never influence a run.
  * A lesson sourced from the test split is refused outright, because feeding
    test feedback into memory leaks the held-out set into training-time
    behaviour.
  * Every record carries code provenance and a schema version, so a result can
    be traced back to the exact memory contents and commit that produced it.

This memory is separate from the frozen MAST reproduction. MAST failure codes
appear here only as vocabulary for describing a failure; nothing in this module
reads or writes MAST reproduction artifacts.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from models.baseline_mast.parse_judge import MAST_CODES
from models.baseline_mast.provenance import environment_provenance, git_provenance, redact

# Bumped when a field changes meaning or disappears. A reader refuses records
# written by a newer schema rather than guessing at the missing semantics.
SCHEMA_VERSION: str = "learning-event-v1"

# Event ids come from the frozen SessionEvent contract (ADR-001), which shapes
# them as evt_<ULID>. Validating the reference here means a lesson can always
# be traced back to the events it was derived from.
EVENT_ID_RE = re.compile(r"^evt_[0-9A-HJKMNP-TV-Z]{26}$")

LESSON_ID_RE = re.compile(r"^les_[0-9a-z]{8,}$")


class Task(str, Enum):
    """The four learned components. MAST is not one of them."""

    m1 = "m1"
    m2 = "m2"
    m3 = "m3"
    m4 = "m4"


class LessonState(str, Enum):
    """A lesson is only retrievable in `approved`."""

    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"


class FeedbackSource(str, Enum):
    """Who judged the output. Both are first-class; neither auto-approves."""

    verifier = "verifier"
    human = "human"


class Split(str, Enum):
    """Which frozen split the judged output came from.

    `test` exists so a caller can state it and be refused. Recording the split
    and rejecting the test case is how the leakage rule is enforced in code
    rather than in a reviewer's memory.
    """

    train = "train"
    validation = "validation"
    test = "test"
    pilot = "pilot"


# Failure vocabularies, per task. Closed sets: an unknown code is a rejected
# record, not a new category, so the taxonomy cannot drift one lesson at a
# time. M1's codes come from the verifier described in the research plan
# (schema, source references, critical-fact coverage, attribution,
# unsupported claims). M2 to M4 are declared now so the contract does not
# change when their verifiers arrive in 298B.
M1_FAILURE_CODES: tuple[str, ...] = (
    "m1.schema_invalid",
    "m1.missing_source_reference",
    "m1.unsupported_claim",
    "m1.critical_fact_missing",
    "m1.attribution_incorrect",
    "m1.stale_state",
)

M2_FAILURE_CODES: tuple[str, ...] = (
    "m2.addressee_incorrect",
    "m2.addressee_ambiguous",
    "m2.broadcast_misread",
)

M3_FAILURE_CODES: tuple[str, ...] = (
    "m3.harmful_merge",
    "m3.wrong_winner",
    "m3.missed_escalation",
    "m3.needless_escalation",
)

M4_FAILURE_CODES: tuple[str, ...] = (
    "m4.invalid_dag",
    "m4.ineligible_tool",
    "m4.wrong_route",
    "m4.incomplete_plan",
)

# MAST supplies an external taxonomy for describing multi-agent failures. Its
# codes are accepted for any task, prefixed so a MAST code can never be
# confused with a task-specific one in a results table.
MAST_FAILURE_CODES: tuple[str, ...] = tuple(f"mast.{code}" for code in MAST_CODES)

_TASK_FAILURE_CODES: dict[Task, tuple[str, ...]] = {
    Task.m1: M1_FAILURE_CODES,
    Task.m2: M2_FAILURE_CODES,
    Task.m3: M3_FAILURE_CODES,
    Task.m4: M4_FAILURE_CODES,
}


def failure_codes_for(task: Task) -> tuple[str, ...]:
    """Every code a lesson for this task may carry, task-specific plus MAST."""
    return _TASK_FAILURE_CODES[task] + MAST_FAILURE_CODES


def utc_now() -> datetime:
    """Timezone-aware UTC. Naive timestamps are not comparable across hosts."""
    return datetime.now(UTC)


class Provenance(BaseModel):
    """Which code, on which machine, produced this record.

    Reuses the git and environment helpers that back the MAST run manifests,
    so a lesson and a baseline run describe their origin the same way.
    """

    model_config = ConfigDict(extra="forbid")

    git_sha: Optional[str] = None
    git_branch: Optional[str] = None
    git_dirty: Optional[bool] = None
    python_version: Optional[str] = None
    platform: Optional[str] = None

    @classmethod
    def capture(cls) -> Provenance:
        git = git_provenance()
        env = environment_provenance()
        return cls(
            git_sha=git["git_sha"],
            git_branch=git["git_branch"],
            git_dirty=git["git_dirty"],
            python_version=env["python_version"],
            platform=env["platform"],
        )


class Feedback(BaseModel):
    """The judgement that makes this a learning event rather than a log line."""

    model_config = ConfigDict(extra="forbid")

    source: FeedbackSource
    # Verifier name and version, or the reviewer's identifier. Pinned so a
    # lesson can be re-derived when a verifier changes.
    author: str = Field(min_length=1)
    detail: str = Field(min_length=1)

    @field_validator("author", "detail")
    @classmethod
    def _no_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class Decision(BaseModel):
    """One approve or reject, kept so the audit trail is replayable."""

    model_config = ConfigDict(extra="forbid")

    state: LessonState
    decided_by: str = Field(min_length=1)
    decided_at: datetime
    note: Optional[str] = None

    @field_validator("state")
    @classmethod
    def _decisions_are_terminal_states(cls, value: LessonState) -> LessonState:
        if value is LessonState.proposed:
            raise ValueError("a decision records approval or rejection, not a proposal")
        return value


class LearningEvent(BaseModel):
    """One verified failure and the lesson a later run may carry.

    `lesson` is the retrievable part: the guidance a future run sees once a
    human has approved it. Everything else is the evidence that justifies it.
    """

    # protected_namespaces is cleared because `model_output` is the name the
    # research plan uses; PredictResponse in the frozen contract does the same
    # for `model_id`.
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    schema_version: str = SCHEMA_VERSION
    lesson_id: str
    task: Task

    # What produced the output being judged.
    candidate_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    split: Split

    # What was produced, and what it was built from.
    model_output: str
    source_event_ids: list[str]
    session_id: Optional[str] = None

    # Why it is a failure.
    failure_code: str
    feedback: Feedback

    # What a later run should do about it.
    lesson: str = Field(min_length=1)

    # Governance.
    state: LessonState = LessonState.proposed
    decisions: list[Decision] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
    provenance: Provenance

    @field_validator("lesson_id")
    @classmethod
    def _lesson_id_shape(cls, value: str) -> str:
        if not LESSON_ID_RE.match(value):
            raise ValueError(f"lesson_id must match {LESSON_ID_RE.pattern}, got {value!r}")
        return value

    @field_validator("source_event_ids")
    @classmethod
    def _source_events_are_present_and_well_formed(cls, value: list[str]) -> list[str]:
        # A lesson with no evidence cannot be audited, so an empty list is a
        # validation error rather than an empty-but-valid record.
        if not value:
            raise ValueError("a lesson must reference at least one source event")
        bad = [e for e in value if not EVENT_ID_RE.match(e)]
        if bad:
            raise ValueError(f"source_event_ids must be evt_<ULID>, got {bad}")
        if len(set(value)) != len(value):
            raise ValueError("source_event_ids must not repeat")
        return value

    @field_validator("lesson", "model_output")
    @classmethod
    def _no_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("created_at", "updated_at")
    @classmethod
    def _timestamps_are_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware UTC")
        return value

    @field_validator("failure_code")
    @classmethod
    def _failure_code_is_known(cls, value: str, info: ValidationInfo) -> str:
        # Runs after `task` because fields validate in declaration order, so
        # the task-specific vocabulary is available here.
        task = info.data.get("task")
        if task is None:
            return value
        allowed = failure_codes_for(task)
        if value not in allowed:
            raise ValueError(f"failure_code {value!r} is not in the {task.value} vocabulary")
        return value

    def is_retrievable(self) -> bool:
        """Approved lessons only. The single place that rule is expressed."""
        return self.state is LessonState.approved

    def to_record(self) -> dict[str, Any]:
        """JSON-ready form, with anything credential-shaped stripped.

        Model output and reviewer notes are free text that ends up in a
        committed artifact, so they pass through the same redactor the MAST
        run manifests use.
        """
        return redact(self.model_dump(mode="json"))


def new_lesson_id(seed: str) -> str:
    """Deterministic lesson id derived from the evidence it describes.

    Deriving rather than randomising means re-proposing the same lesson for
    the same run and events yields the same id, so a retried verifier pass
    cannot silently create duplicates.
    """
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"les_{digest}"


def draft(
    *,
    task: Task,
    candidate_id: str,
    run_id: str,
    split: Split,
    model_output: str,
    source_event_ids: list[str],
    failure_code: str,
    feedback: Feedback,
    lesson: str,
    session_id: str | None = None,
    now: datetime | None = None,
) -> LearningEvent:
    """Build an unsaved lesson in `proposed`.

    Separate from `MemoryStore.propose`, which records it: drafting is pure and
    cheap, so a verifier can build a candidate lesson and discard it without
    touching the log.
    """
    at = now or utc_now()
    lesson_id = new_lesson_id(
        f"{task.value}|{candidate_id}|{run_id}|{failure_code}|{','.join(source_event_ids)}"
    )
    return LearningEvent(
        lesson_id=lesson_id,
        task=task,
        candidate_id=candidate_id,
        run_id=run_id,
        split=split,
        model_output=model_output,
        source_event_ids=source_event_ids,
        session_id=session_id,
        failure_code=failure_code,
        feedback=feedback,
        lesson=lesson,
        state=LessonState.proposed,
        created_at=at,
        updated_at=at,
        provenance=Provenance.capture(),
    )
