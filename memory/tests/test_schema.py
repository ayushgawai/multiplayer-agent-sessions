"""Contract tests for the LearningEvent schema.

Linear: DAT-56 (M1-05). Owner: Shriram Dundigalla.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from memory.schema import (
    MAST_FAILURE_CODES,
    SCHEMA_VERSION,
    Decision,
    Feedback,
    FeedbackSource,
    LearningEvent,
    LessonState,
    Provenance,
    Split,
    Task,
    failure_codes_for,
    draft,
    new_lesson_id,
)
from memory.tests.conftest import event_id

# states and retrievability


def test_a_new_lesson_is_proposed_and_not_retrievable(make_lesson: Any) -> None:
    lesson = make_lesson()

    assert lesson.state is LessonState.proposed
    assert lesson.is_retrievable() is False
    assert lesson.decisions == []


def test_only_the_approved_state_is_retrievable(make_lesson: Any) -> None:
    for state in LessonState:
        lesson = make_lesson().model_copy(update={"state": state})
        assert lesson.is_retrievable() is (state is LessonState.approved)


# identity


def test_the_lesson_id_is_derived_from_the_evidence(make_lesson: Any) -> None:
    """Re-proposing identical evidence must not mint a second lesson."""
    events = [event_id()]
    first = make_lesson(source_event_ids=events)
    second = make_lesson(source_event_ids=events)

    assert first.lesson_id == second.lesson_id


def test_different_evidence_gives_a_different_lesson_id(make_lesson: Any) -> None:
    first = make_lesson(source_event_ids=[event_id()])
    second = make_lesson(source_event_ids=[event_id()])

    assert first.lesson_id != second.lesson_id


@pytest.mark.parametrize("bad", ["whatever", "les_short", "LES_abcdefgh12", "les_ABCDEFGH12", ""])
def test_a_malformed_lesson_id_is_rejected(make_lesson: Any, bad: str) -> None:
    raw = make_lesson().model_dump(mode="json") | {"lesson_id": bad}

    with pytest.raises(ValidationError, match="lesson_id"):
        LearningEvent.model_validate(raw)


def test_lesson_ids_are_stable_across_processes() -> None:
    """Derivation is a hash of the inputs, not a per-process counter."""
    assert new_lesson_id("m1|m1-a|run_1|m1.unsupported_claim|evt_x") == new_lesson_id(
        "m1|m1-a|run_1|m1.unsupported_claim|evt_x"
    )


# source-event references


def test_a_lesson_must_reference_at_least_one_source_event(make_lesson: Any) -> None:
    with pytest.raises(ValidationError, match="at least one source event"):
        make_lesson(source_event_ids=[])


def test_source_event_ids_must_match_the_frozen_event_contract(make_lesson: Any) -> None:
    with pytest.raises(ValidationError, match="evt_<ULID>"):
        make_lesson(source_event_ids=["not-an-event-id"])


def test_a_ulid_with_an_excluded_letter_is_rejected(make_lesson: Any) -> None:
    """Crockford base32 omits I, L, O and U, so those cannot appear."""
    with pytest.raises(ValidationError, match="evt_<ULID>"):
        make_lesson(source_event_ids=["evt_01M5FZGECQ32H9BKAHATWG5KRI"])


def test_repeated_source_event_ids_are_rejected(make_lesson: Any) -> None:
    same = event_id()
    with pytest.raises(ValidationError, match="must not repeat"):
        make_lesson(source_event_ids=[same, same])


# failure vocabulary


def test_the_m1_vocabulary_covers_the_verifier_checks() -> None:
    codes = failure_codes_for(Task.m1)

    for expected in (
        "m1.schema_invalid",
        "m1.missing_source_reference",
        "m1.unsupported_claim",
        "m1.critical_fact_missing",
        "m1.attribution_incorrect",
    ):
        assert expected in codes


def test_mast_codes_are_available_to_every_task() -> None:
    assert "mast.3.1" in MAST_FAILURE_CODES
    assert "mast.3.3" in MAST_FAILURE_CODES
    for task in Task:
        assert set(MAST_FAILURE_CODES) <= set(failure_codes_for(task))


def test_a_code_from_another_task_is_rejected(make_lesson: Any) -> None:
    with pytest.raises(ValidationError, match="not in the m1 vocabulary"):
        make_lesson(failure_code="m3.harmful_merge")


def test_an_unknown_code_is_rejected(make_lesson: Any) -> None:
    with pytest.raises(ValidationError, match="not in the m1 vocabulary"):
        make_lesson(failure_code="m1.made_this_up")


def test_a_bare_mast_code_without_the_prefix_is_rejected(make_lesson: Any) -> None:
    """`3.1` alone would be ambiguous in a results table, so it must not pass."""
    with pytest.raises(ValidationError, match="not in the m1 vocabulary"):
        make_lesson(failure_code="3.1")


# required content


def test_a_blank_lesson_is_rejected(make_lesson: Any) -> None:
    with pytest.raises(ValidationError):
        make_lesson(lesson="   ")


def test_a_blank_model_output_is_rejected(make_lesson: Any) -> None:
    with pytest.raises(ValidationError):
        make_lesson(model_output="")


def test_blank_feedback_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Feedback(source=FeedbackSource.human, author=" ", detail="x")
    with pytest.raises(ValidationError):
        Feedback(source=FeedbackSource.human, author="pramod", detail=" ")


def test_an_unexpected_field_is_rejected(make_lesson: Any) -> None:
    raw = make_lesson().model_dump(mode="json")
    raw["smuggled"] = True

    with pytest.raises(ValidationError):
        LearningEvent.model_validate(raw)


# timestamps and provenance


def test_timestamps_must_be_timezone_aware(make_lesson: Any) -> None:
    raw = make_lesson().model_dump(mode="python")
    raw["created_at"] = datetime(2026, 10, 21, 12, 0, 0)

    with pytest.raises(ValidationError, match="timezone-aware"):
        LearningEvent.model_validate(raw)


def test_every_lesson_records_code_provenance(make_lesson: Any) -> None:
    lesson = make_lesson()

    assert lesson.provenance.git_sha
    assert lesson.provenance.python_version
    assert lesson.provenance.platform


def test_provenance_capture_reads_the_working_tree() -> None:
    captured = Provenance.capture()

    assert captured.git_sha is not None
    assert captured.git_dirty in (True, False)


def test_every_lesson_records_the_schema_version(make_lesson: Any) -> None:
    assert make_lesson().schema_version == SCHEMA_VERSION


# decisions


def test_a_decision_cannot_record_the_proposed_state() -> None:
    from memory.schema import utc_now

    with pytest.raises(ValidationError, match="approval or rejection"):
        Decision(state=LessonState.proposed, decided_by="pramod", decided_at=utc_now())


# serialization


def test_a_lesson_round_trips_through_json(make_lesson: Any) -> None:
    lesson = make_lesson()

    restored = LearningEvent.model_validate(json.loads(json.dumps(lesson.to_record())))

    assert restored == lesson


def test_serialization_is_stable_for_the_same_lesson(make_lesson: Any) -> None:
    """Byte-identical output means a diff on the log shows real changes only."""
    lesson = make_lesson()

    first = json.dumps(lesson.to_record(), sort_keys=True)
    second = json.dumps(lesson.to_record(), sort_keys=True)

    assert first == second


def test_credential_shaped_text_is_redacted_before_it_is_written(make_lesson: Any) -> None:
    """Model output is free text that lands in a committed artifact."""
    leaked = "the agent printed sk-abcdefghijklmnopqrstuvwxyz while summarising"
    lesson = make_lesson(model_output=leaked)

    record = lesson.to_record()

    assert "sk-abcdefghijklmnopqrstuvwxyz" not in json.dumps(record)
    assert record["model_output"] == "[REDACTED]"


def test_the_test_split_is_representable_so_it_can_be_refused(make_lesson: Any) -> None:
    """The schema allows it; the store is what refuses it. See test_store."""
    lesson = make_lesson(split=Split.test)

    assert lesson.split is Split.test


def test_draft_never_returns_an_approved_lesson(verifier_feedback: Feedback) -> None:
    lesson = draft(
        task=Task.m4,
        candidate_id="m4-a",
        run_id="run_1",
        split=Split.train,
        model_output="plan: [a, b]",
        source_event_ids=[event_id()],
        failure_code="m4.invalid_dag",
        feedback=verifier_feedback,
        lesson="Reject plans whose edges form a cycle.",
    )

    assert lesson.state is LessonState.proposed
