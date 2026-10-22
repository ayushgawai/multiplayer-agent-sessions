"""Approval, rejection, retrieval and audit behaviour of the memory store.

Linear: DAT-56 (M1-05). Owner: Shriram Dundigalla.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from memory.schema import SCHEMA_VERSION, LessonState, Split, Task
from memory.store import (
    DuplicateLesson,
    FrozenArtifactError,
    IllegalTransition,
    LeakageError,
    MemoryStore,
    SchemaVersionError,
    UnknownLesson,
)

# proposing


def test_an_empty_store_has_nothing_in_it(store: MemoryStore) -> None:
    assert store.revisions() == []
    assert store.current() == {}
    assert store.version == 0
    assert store.retrieve(Task.m1) == []


def test_a_proposed_lesson_is_stored_but_not_retrievable(
    store: MemoryStore, make_lesson: Any
) -> None:
    lesson = store.propose(make_lesson())

    assert store.get(lesson.lesson_id) is not None
    assert store.retrieve(Task.m1) == []


def test_re_proposing_identical_evidence_is_idempotent(
    store: MemoryStore, make_lesson: Any
) -> None:
    from memory.tests.conftest import event_id

    events = [event_id()]
    first = store.propose(make_lesson(source_event_ids=events))
    second = store.propose(make_lesson(source_event_ids=events))

    assert first.lesson_id == second.lesson_id
    assert store.version == 1


def test_a_lesson_cannot_enter_the_store_already_approved(
    store: MemoryStore, make_lesson: Any
) -> None:
    pre_approved = make_lesson().model_copy(update={"state": LessonState.approved})

    with pytest.raises(IllegalTransition, match="enters the store as proposed"):
        store.propose(pre_approved)


def test_re_proposing_a_rejected_lesson_is_refused(store: MemoryStore, make_lesson: Any) -> None:
    """Otherwise a rejected lesson would quietly reappear as a fresh proposal."""
    from memory.tests.conftest import event_id

    events = [event_id()]
    lesson = store.propose(make_lesson(source_event_ids=events))
    store.reject(lesson.lesson_id, decided_by="pramod", note="not reproducible")

    with pytest.raises(DuplicateLesson, match="already rejected"):
        store.propose(make_lesson(source_event_ids=events))


# the leakage rule


def test_a_test_split_lesson_is_refused(store: MemoryStore, make_lesson: Any) -> None:
    with pytest.raises(LeakageError, match="test split"):
        store.propose(make_lesson(split=Split.test))

    assert store.version == 0


@pytest.mark.parametrize("split", [Split.train, Split.validation, Split.pilot])
def test_every_other_split_is_accepted(
    store: MemoryStore, make_lesson: Any, split: Split
) -> None:
    stored = store.propose(make_lesson(split=split))

    assert store.get(stored.lesson_id) is not None


def test_a_store_cannot_be_opened_inside_the_frozen_reproduction(tmp_path: Path) -> None:
    for guarded in ("data/mast", "models/baseline_mast"):
        target = tmp_path / guarded / "lessons.jsonl"
        with pytest.raises(FrozenArtifactError, match=guarded):
            MemoryStore(target)


def test_a_similarly_named_directory_is_still_allowed(tmp_path: Path) -> None:
    """The guard matches path segments, not substrings of a longer name."""
    store = MemoryStore(tmp_path / "data" / "mast_lessons" / "lessons.jsonl")

    assert store.revisions() == []


# approving and rejecting


def test_approving_makes_a_lesson_retrievable(store: MemoryStore, make_lesson: Any) -> None:
    lesson = store.propose(make_lesson())

    approved = store.approve(lesson.lesson_id, decided_by="pramod")

    assert approved.state is LessonState.approved
    assert [hit.lesson_id for hit in store.retrieve(Task.m1)] == [lesson.lesson_id]


def test_rejecting_keeps_a_lesson_out_of_retrieval(store: MemoryStore, make_lesson: Any) -> None:
    lesson = store.propose(make_lesson())

    store.reject(lesson.lesson_id, decided_by="pramod", note="verifier was misconfigured")

    stored = store.get(lesson.lesson_id)
    assert stored is not None
    assert stored.state is LessonState.rejected
    assert store.retrieve(Task.m1) == []


def test_an_approved_lesson_can_be_withdrawn(store: MemoryStore, make_lesson: Any) -> None:
    lesson = store.propose(make_lesson())
    store.approve(lesson.lesson_id, decided_by="pramod")

    store.reject(lesson.lesson_id, decided_by="pramod", note="superseded by a schema fix")

    assert store.retrieve(Task.m1) == []


def test_a_rejected_lesson_can_be_approved_on_appeal(
    store: MemoryStore, make_lesson: Any
) -> None:
    lesson = store.propose(make_lesson())
    store.reject(lesson.lesson_id, decided_by="pramod", note="looked like a parser bug")

    store.approve(lesson.lesson_id, decided_by="ayush", note="parser was fine, failure is real")

    assert len(store.retrieve(Task.m1)) == 1


def test_reversing_a_decision_requires_a_note(store: MemoryStore, make_lesson: Any) -> None:
    lesson = store.propose(make_lesson())
    store.approve(lesson.lesson_id, decided_by="pramod")

    with pytest.raises(IllegalTransition, match="requires a note"):
        store.reject(lesson.lesson_id, decided_by="pramod")


def test_a_first_decision_does_not_require_a_note(store: MemoryStore, make_lesson: Any) -> None:
    lesson = store.propose(make_lesson())

    assert store.approve(lesson.lesson_id, decided_by="pramod").state is LessonState.approved


def test_approving_twice_is_refused(store: MemoryStore, make_lesson: Any) -> None:
    """A double submit is far likelier than an intentional re-approval."""
    lesson = store.propose(make_lesson())
    store.approve(lesson.lesson_id, decided_by="pramod")

    with pytest.raises(IllegalTransition, match="approved to approved"):
        store.approve(lesson.lesson_id, decided_by="pramod", note="again")


def test_deciding_an_unknown_lesson_is_refused(store: MemoryStore) -> None:
    with pytest.raises(UnknownLesson):
        store.approve("les_deadbeef00", decided_by="pramod")


# audit trail and rollback


def test_every_decision_is_recorded_on_the_lesson(store: MemoryStore, make_lesson: Any) -> None:
    lesson = store.propose(make_lesson())
    store.reject(lesson.lesson_id, decided_by="pramod", note="looked wrong")
    final = store.approve(lesson.lesson_id, decided_by="ayush", note="on review it is right")

    assert [d.state for d in final.decisions] == [LessonState.rejected, LessonState.approved]
    assert [d.decided_by for d in final.decisions] == ["pramod", "ayush"]
    assert all(d.decided_at.tzinfo is not None for d in final.decisions)


def test_the_log_keeps_every_revision(store: MemoryStore, make_lesson: Any) -> None:
    lesson = store.propose(make_lesson())
    store.approve(lesson.lesson_id, decided_by="pramod")
    store.reject(lesson.lesson_id, decided_by="pramod", note="withdrawn")

    history = store.history(lesson.lesson_id)

    assert [r.state for r in history] == [
        LessonState.proposed,
        LessonState.approved,
        LessonState.rejected,
    ]
    assert store.version == 3


def test_a_past_version_can_be_replayed(store: MemoryStore, make_lesson: Any) -> None:
    """A run pins the memory version, so its inputs stay reproducible."""
    lesson = store.propose(make_lesson())
    store.approve(lesson.lesson_id, decided_by="pramod")
    approved_at = store.version
    store.reject(lesson.lesson_id, decided_by="pramod", note="withdrawn later")

    assert store.retrieve(Task.m1) == []
    assert len(store.retrieve(Task.m1, version=approved_at)) == 1


def test_version_zero_is_an_empty_memory(store: MemoryStore, make_lesson: Any) -> None:
    """This is the memory-disabled arm of the comparison."""
    lesson = store.propose(make_lesson())
    store.approve(lesson.lesson_id, decided_by="pramod")

    assert store.retrieve(Task.m1, version=0) == []


def test_a_negative_version_is_rejected(store: MemoryStore) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        store.at_version(-1)


# retrieval filters


def test_retrieval_is_scoped_to_one_task(store: MemoryStore, make_lesson: Any) -> None:
    m1 = store.propose(make_lesson())
    m3 = store.propose(
        make_lesson(task=Task.m3, candidate_id="m3-a", failure_code="m3.harmful_merge")
    )
    store.approve(m1.lesson_id, decided_by="pramod")
    store.approve(m3.lesson_id, decided_by="pramod")

    assert [h.lesson_id for h in store.retrieve(Task.m1)] == [m1.lesson_id]
    assert [h.lesson_id for h in store.retrieve(Task.m3)] == [m3.lesson_id]


def test_retrieval_can_be_filtered_by_candidate(store: MemoryStore, make_lesson: Any) -> None:
    a = store.propose(make_lesson(candidate_id="m1-a"))
    b = store.propose(make_lesson(candidate_id="m1-d"))
    store.approve(a.lesson_id, decided_by="pramod")
    store.approve(b.lesson_id, decided_by="pramod")

    assert [h.lesson_id for h in store.retrieve(Task.m1, candidate_id="m1-d")] == [b.lesson_id]


def test_retrieval_can_be_filtered_by_failure_code(store: MemoryStore, make_lesson: Any) -> None:
    unsupported = store.propose(make_lesson(failure_code="m1.unsupported_claim"))
    attribution = store.propose(make_lesson(failure_code="m1.attribution_incorrect"))
    store.approve(unsupported.lesson_id, decided_by="pramod")
    store.approve(attribution.lesson_id, decided_by="pramod")

    hits = store.retrieve(Task.m1, failure_codes=["m1.attribution_incorrect"])

    assert [h.lesson_id for h in hits] == [attribution.lesson_id]


def test_retrieval_can_be_filtered_by_session(store: MemoryStore, make_lesson: Any) -> None:
    scoped = store.propose(make_lesson(session_id="ses_1"))
    other = store.propose(make_lesson(session_id="ses_2"))
    store.approve(scoped.lesson_id, decided_by="pramod")
    store.approve(other.lesson_id, decided_by="pramod")

    assert [h.lesson_id for h in store.retrieve(Task.m1, session_id="ses_1")] == [
        scoped.lesson_id
    ]


def test_retrieval_respects_a_limit(store: MemoryStore, make_lesson: Any) -> None:
    for _ in range(5):
        lesson = store.propose(make_lesson())
        store.approve(lesson.lesson_id, decided_by="pramod")

    assert len(store.retrieve(Task.m1, limit=2)) == 2


def test_retrieval_order_is_deterministic(store: MemoryStore, make_lesson: Any) -> None:
    for _ in range(6):
        lesson = store.propose(make_lesson())
        store.approve(lesson.lesson_id, decided_by="pramod")

    first = [h.lesson_id for h in store.retrieve(Task.m1)]
    second = [h.lesson_id for h in MemoryStore(store.path).retrieve(Task.m1)]

    assert first == second


def test_a_mix_of_states_returns_only_the_approved_ones(
    store: MemoryStore, make_lesson: Any
) -> None:
    approved = store.propose(make_lesson())
    rejected = store.propose(make_lesson())
    store.propose(make_lesson())  # left proposed
    store.approve(approved.lesson_id, decided_by="pramod")
    store.reject(rejected.lesson_id, decided_by="pramod", note="duplicate")

    assert [h.lesson_id for h in store.retrieve(Task.m1)] == [approved.lesson_id]


# on-disk format


def test_the_log_is_one_json_object_per_line(store: MemoryStore, make_lesson: Any) -> None:
    lesson = store.propose(make_lesson())
    store.approve(lesson.lesson_id, decided_by="pramod")

    lines = store.path.read_text(encoding="utf-8").strip().split("\n")

    assert len(lines) == 2
    for line in lines:
        assert json.loads(line)["schema_version"] == SCHEMA_VERSION


def test_blank_lines_in_the_log_are_skipped(store: MemoryStore, make_lesson: Any) -> None:
    store.propose(make_lesson())
    with store.path.open("a", encoding="utf-8") as handle:
        handle.write("\n")

    assert len(store.revisions()) == 1


def test_a_record_from_a_newer_schema_is_refused(store: MemoryStore, make_lesson: Any) -> None:
    """Guessing at a field whose meaning changed would corrupt results."""
    lesson = store.propose(make_lesson())
    record = lesson.to_record() | {"schema_version": "learning-event-v99"}
    with store.path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    with pytest.raises(SchemaVersionError, match="learning-event-v99"):
        store.revisions()


def test_a_corrupt_line_names_its_position(store: MemoryStore, make_lesson: Any) -> None:
    store.propose(make_lesson())
    with store.path.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")

    with pytest.raises(SchemaVersionError, match=":2"):
        store.revisions()


def test_a_second_store_sees_what_the_first_wrote(store: MemoryStore, make_lesson: Any) -> None:
    """Separate processes share state through the file, not memory."""
    lesson = store.propose(make_lesson())
    store.approve(lesson.lesson_id, decided_by="pramod")

    reopened = MemoryStore(store.path)

    assert len(reopened.retrieve(Task.m1)) == 1
    assert reopened.version == 2


def test_concurrent_appends_do_not_interleave(tmp_path: Path, make_lesson: Any) -> None:
    """Each append holds an exclusive lock, so no line is torn in half."""
    import threading

    path = tmp_path / "lessons.jsonl"
    lessons = [make_lesson() for _ in range(24)]

    def write(index: int) -> None:
        MemoryStore(path).propose(lessons[index])

    threads = [threading.Thread(target=write, args=(i,)) for i in range(len(lessons))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    reopened = MemoryStore(path)
    assert reopened.version == len(lessons)
    assert len({r.lesson_id for r in reopened.revisions()}) == len(lessons)


def test_concurrent_proposals_of_one_lesson_write_it_once(
    tmp_path: Path, make_lesson: Any
) -> None:
    """Read and append share one lock, so the idempotency check cannot race."""
    import threading

    from memory.tests.conftest import event_id

    path = tmp_path / "lessons.jsonl"
    events = [event_id()]
    lessons = [make_lesson(source_event_ids=events) for _ in range(16)]
    assert len({lesson.lesson_id for lesson in lessons}) == 1

    def write(index: int) -> None:
        MemoryStore(path).propose(lessons[index])

    threads = [threading.Thread(target=write, args=(i,)) for i in range(len(lessons))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert MemoryStore(path).version == 1


def test_concurrent_approvals_produce_exactly_one_decision(
    tmp_path: Path, make_lesson: Any
) -> None:
    """Only the first approval wins; the rest see the state they would create."""
    import threading

    path = tmp_path / "lessons.jsonl"
    store = MemoryStore(path)
    lesson = store.propose(make_lesson())
    refused: list[Exception] = []
    lock = threading.Lock()

    def approve() -> None:
        try:
            MemoryStore(path).approve(lesson.lesson_id, decided_by="pramod")
        except IllegalTransition as exc:
            with lock:
                refused.append(exc)

    threads = [threading.Thread(target=approve) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    final = MemoryStore(path).get(lesson.lesson_id)
    assert final is not None
    assert len(final.decisions) == 1
    assert len(refused) == 7
