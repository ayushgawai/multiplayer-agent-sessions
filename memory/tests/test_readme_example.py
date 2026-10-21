"""The README's usage example must keep working.

Linear: DAT-56 (M1-05). Owner: Shriram Dundigalla.

Documentation that drifts from the code is worse than none, because a reader
trusts it. This runs the README's three-step example end to end against a
temporary store.
"""

from __future__ import annotations

import re
from pathlib import Path

from memory.schema import Feedback, FeedbackSource, Split, Task, draft
from memory.store import MemoryStore

README = Path(__file__).resolve().parents[1] / "README.md"


def test_the_documented_flow_works(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "m1-lessons.jsonl")

    lesson = store.propose(
        draft(
            task=Task.m1,
            candidate_id="m1-a",
            run_id="run_2026_10_21_a",
            split=Split.validation,
            model_output="Ana approved the Q3 budget.",
            source_event_ids=["evt_01M5FZGECQ32H9BKAHATWG5KRW"],
            failure_code="m1.unsupported_claim",
            feedback=Feedback(
                source=FeedbackSource.verifier,
                author="m1-verifier-v1",
                detail="no source event records a budget approval",
            ),
            lesson="Every factual claim must cite the event id it came from.",
        )
    )
    assert store.retrieve(Task.m1) == []

    store.approve(lesson.lesson_id, decided_by="pramod")

    lessons = store.retrieve(Task.m1, candidate_id="m1-a", limit=5)
    assert [hit.lesson_id for hit in lessons] == [lesson.lesson_id]


def test_the_readme_documents_every_retrieve_argument() -> None:
    """A new filter must be documented, not just shipped."""
    import inspect

    documented = set(re.findall(r"^\| `(\w+)` \|", README.read_text(encoding="utf-8"), re.M))
    signature = inspect.signature(MemoryStore.retrieve)
    actual = {name for name in signature.parameters if name != "self"}

    assert actual == documented


def test_the_readme_names_the_current_schema_version() -> None:
    from memory.schema import SCHEMA_VERSION

    assert SCHEMA_VERSION in README.read_text(encoding="utf-8")
