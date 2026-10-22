"""Append-only store for approved-memory lessons.

Linear: DAT-56 (M1-05). Owner: Shriram Dundigalla.

The store is a JSONL log of lesson revisions, not a mutable table. Proposing,
approving and rejecting all append a full new snapshot of the lesson, and the
current state of a lesson is the last snapshot carrying its id. Three things
fall out of that choice:

  * The audit trail is the file. Who approved what, when, and with what note
    cannot be edited away without rewriting history that git is tracking.
  * Rollback is a prefix of the log. `at_version` replays the first N
    revisions, so a run can be reproduced against the memory contents as they
    stood when it executed rather than as they stand today.
  * A crash mid-write loses at most the record being appended, because each
    append is a single flushed line under an exclusive lock.

Retrieval reads the approved set only. That is enforced here and in
`LearningEvent.is_retrievable`, so neither a caller that forgets to filter nor
a filter that is later loosened can expose an unreviewed proposal.
"""

from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO

from pydantic import ValidationError

from memory.schema import (
    SCHEMA_VERSION,
    Decision,
    LearningEvent,
    LessonState,
    Split,
    Task,
    utc_now,
)

# Writing memory anywhere under these paths would mix the self-improvement
# layer into the frozen published-reproduction artifacts, which the research
# plan requires to stay experimentally separate.
FROZEN_REPRODUCTION_PATHS: tuple[str, ...] = (
    "data/mast",
    "models/baseline_mast",
)

# Transitions a reviewer may make. Same-state moves are absent on purpose: an
# approve on an already-approved lesson is far more likely to be a double
# submit than an intention, and silently accepting it would add a second
# decision to the audit trail that nothing actually decided.
LEGAL_TRANSITIONS: dict[LessonState, frozenset[LessonState]] = {
    LessonState.proposed: frozenset({LessonState.approved, LessonState.rejected}),
    LessonState.approved: frozenset({LessonState.rejected}),
    LessonState.rejected: frozenset({LessonState.approved}),
}


class MemoryStoreError(Exception):
    """Base class for refusals the store raises."""


class LeakageError(MemoryStoreError):
    """Raised when a write would put held-out feedback into memory."""


class FrozenArtifactError(MemoryStoreError):
    """Raised when a store would be opened inside the MAST reproduction tree."""


class UnknownLesson(MemoryStoreError):
    """Raised when a decision names a lesson the store has never seen."""


class IllegalTransition(MemoryStoreError):
    """Raised when a decision is not a legal move from the current state."""


class SchemaVersionError(MemoryStoreError):
    """Raised when the log holds a record this build cannot interpret."""


class DuplicateLesson(MemoryStoreError):
    """Raised when a proposal would resurrect an already-decided lesson."""


def _assert_outside_frozen_artifacts(path: Path) -> None:
    resolved = path.resolve()
    parts = resolved.as_posix()
    for guarded in FROZEN_REPRODUCTION_PATHS:
        if f"/{guarded}/" in parts or parts.endswith(f"/{guarded}"):
            raise FrozenArtifactError(
                f"refusing to store lessons under {guarded}: the published MAST "
                f"reproduction must stay separate from the self-improvement layer"
            )


@contextmanager
def _exclusive(path: Path) -> Iterator[TextIO]:
    """Hold an exclusive advisory lock on `path` for the whole block.

    Opened "a+" so the same handle can both read the existing log and append
    to it. Every write is a read-modify-append - "is this lesson already
    decided?", then append - and holding one lock across both halves is what
    stops two verifier processes from each reading "absent" and both writing.

    The lock is POSIX advisory, which is sufficient because every environment
    in the build plan is Linux or macOS and every writer goes through here.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield handle
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


class MemoryStore:
    """Approved-memory lessons for one task family, backed by one JSONL log."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        _assert_outside_frozen_artifacts(self.path)

    # reading

    def revisions(self) -> list[LearningEvent]:
        """Every appended snapshot, oldest first. This is the audit trail."""
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as handle:
            return self._parse(handle)

    def _parse(self, handle: TextIO) -> list[LearningEvent]:
        out: list[LearningEvent] = []
        for lineno, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            out.append(self._parse_line(line, lineno))
        return out

    def _parse_line(self, line: str, lineno: int) -> LearningEvent:
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SchemaVersionError(f"{self.path}:{lineno} is not valid JSON: {exc}") from exc
        found = raw.get("schema_version")
        # A record from a newer schema may use a field this build reads with
        # different meaning, so refuse it instead of silently mis-reading it.
        if found != SCHEMA_VERSION:
            raise SchemaVersionError(
                f"{self.path}:{lineno} has schema_version {found!r}; "
                f"this build understands {SCHEMA_VERSION!r}"
            )
        try:
            return LearningEvent.model_validate(raw)
        except ValidationError as exc:
            raise SchemaVersionError(f"{self.path}:{lineno} failed validation: {exc}") from exc

    @property
    def version(self) -> int:
        """Number of revisions appended. A run pins this to be reproducible."""
        return len(self.revisions())

    def at_version(self, version: int) -> dict[str, LearningEvent]:
        """Current lessons as they stood after the first `version` revisions.

        This is the rollback primitive: evaluating against `at_version(n)`
        reproduces the memory a past run actually saw.
        """
        if version < 0:
            raise ValueError("version must not be negative")
        state: dict[str, LearningEvent] = {}
        for revision in self.revisions()[:version]:
            state[revision.lesson_id] = revision
        return state

    def current(self) -> dict[str, LearningEvent]:
        """Latest revision of every lesson, keyed by lesson id."""
        state: dict[str, LearningEvent] = {}
        for revision in self.revisions():
            state[revision.lesson_id] = revision
        return state

    def get(self, lesson_id: str) -> Optional[LearningEvent]:
        return self.current().get(lesson_id)

    def history(self, lesson_id: str) -> list[LearningEvent]:
        """Every revision of one lesson, oldest first."""
        return [r for r in self.revisions() if r.lesson_id == lesson_id]

    def retrieve(
        self,
        task: Task,
        *,
        candidate_id: str | None = None,
        failure_codes: Sequence[str] | None = None,
        session_id: str | None = None,
        limit: int | None = None,
        version: int | None = None,
    ) -> list[LearningEvent]:
        """Approved lessons for one task, newest decision first.

        Ordering is by decision time so the most recently approved guidance
        leads, with lesson id breaking ties to keep the result deterministic
        across runs on the same contents. Ranking by relevance is deliberately
        not attempted here; see README.md.
        """
        state = self.current() if version is None else self.at_version(version)
        hits = [
            lesson
            for lesson in state.values()
            if lesson.is_retrievable()
            and lesson.task is task
            and (candidate_id is None or lesson.candidate_id == candidate_id)
            and (session_id is None or lesson.session_id == session_id)
            and (failure_codes is None or lesson.failure_code in set(failure_codes))
        ]
        hits.sort(key=lambda lesson: (lesson.updated_at, lesson.lesson_id), reverse=True)
        return hits[:limit] if limit is not None else hits

    # writing

    def propose(self, lesson: LearningEvent) -> LearningEvent:
        """Record a proposed lesson. Refuses held-out feedback outright."""
        if lesson.split is Split.test:
            raise LeakageError(
                f"lesson {lesson.lesson_id} is sourced from the test split; writing "
                f"held-out feedback into memory would leak the frozen evaluation"
            )
        if lesson.state is not LessonState.proposed:
            raise IllegalTransition(
                f"a new lesson enters the store as {LessonState.proposed.value}, "
                f"not {lesson.state.value}"
            )
        with _exclusive(self.path) as handle:
            existing = self._current_locked(handle).get(lesson.lesson_id)
            if existing is not None:
                # Lesson ids are derived from the evidence, so an identical
                # proposal is a retried verifier pass and is safely idempotent.
                # Re-proposing something already decided is not: it would
                # quietly return a rejected lesson to review.
                if existing.state is LessonState.proposed:
                    return existing
                raise DuplicateLesson(
                    f"lesson {lesson.lesson_id} is already {existing.state.value}; "
                    f"use approve() or reject() to change a decided lesson"
                )
            self._append_locked(handle, lesson)
        return lesson

    def approve(self, lesson_id: str, *, decided_by: str, note: str | None = None) -> LearningEvent:
        """Make a lesson retrievable. The only path into the approved set."""
        return self._decide(lesson_id, LessonState.approved, decided_by=decided_by, note=note)

    def reject(self, lesson_id: str, *, decided_by: str, note: str | None = None) -> LearningEvent:
        """Keep a lesson out of retrieval, or withdraw one already approved."""
        return self._decide(lesson_id, LessonState.rejected, decided_by=decided_by, note=note)

    def _decide(
        self,
        lesson_id: str,
        target: LessonState,
        *,
        decided_by: str,
        note: str | None,
        now: datetime | None = None,
    ) -> LearningEvent:
        # The whole read-decide-append sequence runs under one lock, so a
        # concurrent reviewer cannot slip a second decision in between the
        # legality check and the write.
        with _exclusive(self.path) as handle:
            lesson = self._current_locked(handle).get(lesson_id)
            if lesson is None:
                raise UnknownLesson(f"no lesson {lesson_id} in {self.path}")
            if target not in LEGAL_TRANSITIONS[lesson.state]:
                raise IllegalTransition(
                    f"lesson {lesson_id} cannot move from {lesson.state.value} to {target.value}"
                )
            # Reversing an earlier decision needs a stated reason, because the
            # audit trail would otherwise show a lesson flipping with nothing
            # to explain it to whoever reads the results later.
            if lesson.state is not LessonState.proposed and not (note and note.strip()):
                raise IllegalTransition(
                    f"reversing the decision on {lesson_id} requires a note explaining why"
                )
            at = now or utc_now()
            decision = Decision(state=target, decided_by=decided_by, decided_at=at, note=note)
            updated = lesson.model_copy(
                update={
                    "state": target,
                    "decisions": [*lesson.decisions, decision],
                    "updated_at": at,
                }
            )
            self._append_locked(handle, updated)
        return updated

    def _current_locked(self, handle: TextIO) -> dict[str, LearningEvent]:
        """Latest revision per lesson, read through an already-locked handle."""
        handle.seek(0)
        state: dict[str, LearningEvent] = {}
        for revision in self._parse(handle):
            state[revision.lesson_id] = revision
        return state

    def _append_locked(self, handle: TextIO, lesson: LearningEvent) -> None:
        """Append one revision as a single flushed, fsynced line."""
        payload = json.dumps(lesson.to_record(), ensure_ascii=False, sort_keys=True)
        handle.seek(0, os.SEEK_END)
        handle.write(payload + "\n")
        handle.flush()
        os.fsync(handle.fileno())
