# Learning memory

Linear: DAT-56 (M1-05). Owner: Shriram Dundigalla.

The minimal versioned-memory foundation for verifier-backed self-improvement.
A verifier or a human judges a model output, that judgement becomes a proposed
`LearningEvent`, a human approves or rejects it, and only approved lessons are
visible to a later run.

```text
model output -> verifier or human feedback -> proposed LearningEvent
             -> human approve or reject     -> approved memory
             -> retrieval for a later run   -> new versioned output and evaluation
```

This package is the governance and storage layer only. It does not call a
model, does not run a verifier, and does not change any weights.

## Scope

In scope for DAT-56: the `LearningEvent` contract, the three lesson states,
approved-only retrieval, provenance and schema versioning, the append-only
audit log, and rollback to a past memory version.

Out of scope, deliberately: the M1 verifier itself, prompt assembly, relevance
ranking, embeddings, and any automatic approval. Retrieval returns an ordered
list; deciding which lessons to put in a prompt and how to phrase them belongs
to the M1 integration ticket.

## Retrieval interface

```python
from memory.schema import Feedback, FeedbackSource, Split, Task, draft
from memory.store import MemoryStore

store = MemoryStore("memory/lessons/m1-lessons.jsonl")

# 1. A verifier drafts a lesson and proposes it. Nothing is retrievable yet.
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

# 2. A human decides. This is the only way into the approved set.
store.approve(lesson.lesson_id, decided_by="pramod")

# 3. A later run retrieves. Approved lessons only, ever.
lessons = store.retrieve(Task.m1, candidate_id="m1-a", limit=5)
```

### `retrieve`

| Argument | Effect |
|---|---|
| `task` | Required. Lessons never cross task boundaries. |
| `candidate_id` | Restrict to lessons raised against one candidate. |
| `failure_codes` | Restrict to particular failure modes. |
| `session_id` | Restrict to lessons derived from one session. |
| `limit` | Cap the result length after ordering. |
| `version` | Read memory as it stood after the first N revisions. |

Results are ordered by decision time, newest first, with `lesson_id` breaking
ties so repeated reads of the same contents return the same order. There is no
relevance scoring: a caller that needs the most pertinent lessons rather than
the most recent must rank them itself, and should say so in its method section.

## The two rules that protect the research claim

**Only approved lessons are retrievable.** Enforced in two places:
`LearningEvent.is_retrievable()` is the single expression of the rule, and
`MemoryStore.retrieve` applies it. A proposal that nobody reviewed cannot
influence a run even if a caller forgets to filter.

**Test-split feedback is refused.** `MemoryStore.propose` raises
`LeakageError` for any lesson whose `split` is `test`. Writing held-out
feedback into memory would leak the frozen evaluation into training-time
behaviour, which would invalidate every number downstream of it.

## Versioning and rollback

The store is an append-only JSONL log of lesson revisions. Proposing,
approving and rejecting each append a full snapshot; the current state of a
lesson is its last snapshot. Two consequences:

- `store.version` is the number of revisions. A run that records this value
  can be reproduced later against the memory it actually saw, using
  `retrieve(..., version=N)`.
- `store.history(lesson_id)` returns every revision of one lesson, so an
  approval or a withdrawal is auditable rather than a silent edit.

`version=0` is an empty memory. That is the memory-disabled arm of the
comparison the research plan requires, obtained without deleting anything.

Logs live under `memory/lessons/` and are committed. The audit trail is only
tamper-evident if git is tracking it, and these files are the evidence behind
any memory-assisted result. The store never writes inside `eval/`, which
Pramod owns exclusively.

## Separation from the MAST reproduction

The published MAST reproduction and the memory-assisted extension are separate
experimental conditions and must stay separate in code. `MemoryStore` refuses
to open a log under `data/mast/` or `models/baseline_mast/`, raising
`FrozenArtifactError`. MAST failure codes are available as vocabulary, prefixed
`mast.` so they can never be confused with a task-specific code in a results
table, but nothing here reads or writes a reproduction artifact.

## Schema version

`learning-event-v1`. A record whose `schema_version` does not match raises
`SchemaVersionError` rather than being read with guessed semantics. Bump the
constant in `memory/schema.py` when a field changes meaning or disappears, and
record the change in an ADR under `docs/decisions/`.

## Tests

```bash
cd memory && python -m pytest -q
```
