"""Shared fixtures for the learning-memory tests.

Linear: DAT-56 (M1-05). Owner: Shriram Dundigalla.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ulid import ULID

from memory.schema import Feedback, FeedbackSource, LearningEvent, Split, Task, draft
from memory.store import MemoryStore


def event_id() -> str:
    """A well-formed SessionEvent reference, as the runtime would emit."""
    return f"evt_{ULID()}"


@pytest.fixture
def verifier_feedback() -> Feedback:
    return Feedback(
        source=FeedbackSource.verifier,
        author="m1-verifier-v1",
        detail="summary asserts a budget approval that no source event records",
    )


@pytest.fixture
def make_lesson(verifier_feedback: Feedback) -> Any:
    """Builds a proposed lesson, with every field overridable per test."""

    def _make(**overrides: Any) -> LearningEvent:
        kwargs: dict[str, Any] = {
            "task": Task.m1,
            "candidate_id": "m1-a",
            "run_id": "run_2026_10_21_a",
            "split": Split.validation,
            "model_output": "Ana approved the Q3 budget in the second half of the session.",
            "source_event_ids": [event_id()],
            "failure_code": "m1.unsupported_claim",
            "feedback": verifier_feedback,
            "lesson": "Every factual claim must cite the event id it came from.",
        }
        kwargs.update(overrides)
        return draft(**kwargs)

    return _make


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "lessons.jsonl")
