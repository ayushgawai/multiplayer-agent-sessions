# M1 smoke dataset (DAT-53)

A tiny, deterministic, synthetic set of session event logs for checking the M1 catch-up pipeline
(loading, input conversion, output validation, metrics wiring) before full training.

**These fixtures are for smoke tests only.** They are synthetic. They are never the M1 evaluation
test split, never training data for a reported result, and no score computed on them may be quoted
as a model result. The `test` file here is a fixture split, not the frozen evaluation split.

## Contents

- 12 sessions built from 5 hand-written scenarios: a feature built by a human and two agents, an
  agent blocked on a failed tool call, a handoff between humans, an arbitration between two agents,
  and an interrupt with rollback. 14 to 16 events each (9 to 11 in the "joined late" prefixes).
- 18 examples: one full catch-up per session, plus a "joined late" example (a prefix of the log) for
  6 sessions.
- Splits are disjoint by `session_id`: train 8 sessions (12 examples), dev 2 (3), test 2 (3).
- Every split contains all five categories.

Files in `fixtures/`: `train.jsonl`, `dev.jsonl`, `test.jsonl`, `MANIFEST.json` (seed, split policy,
per-split count, sessions, sha256 and bytes, generator command; no timestamps).

## Reproduce

From the repo root (no network, no model calls):

```bash
python data/scripts/make_m1_smoke.py --seed 13 --out data/m1_smoke/fixtures
```

Output is byte-identical on Windows and Linux (UTF-8, LF, sorted keys, compact separators).
`fixtures/` is marked `eol=lf` in `.gitattributes` so checkouts keep the hashes.

## Validate

```bash
pytest -q data/tests/test_m1_smoke.py
```

```python
from data.m1_smoke.loader import load_split, load_fixtures, verify_manifest, to_m1_input, gold_reference

splits = load_fixtures("data/m1_smoke/fixtures")   # {"train": [...], "dev": [...], "test": [...]}
verify_manifest("data/m1_smoke/fixtures")          # sha256, bytes and counts vs MANIFEST.json
```

Load errors name the file, line number and example id.

## Schema (`m1-smoke-v1`, `data/m1_smoke/schema.py`)

`CatchupExample` (pydantic v2, `extra="forbid"`):

| Field | Meaning |
|-------|---------|
| `example_id`, `session_id`, `query` | Ids and the late joiner's request |
| `events[]` | `source_event_id` (stable, like `smoke-s03-e007`), `sequence` (strictly ascending), `event_type` (a `SessionEvent` type string), `actor_id` (`human-...`, `agent-...`, or null for system events), `text` |
| `event_labels` | Gold status per event id: `completed`, `in_progress`, `blocked`, `decision`, `pending_action`. Neutral events have no entry. |
| `reference` | Gold summary in the `m1-output-v1` shape: five lists of claims `{text, source_event_ids}` |
| `critical_facts[]` | `{fact_id, category, text, evidence_event_ids}`, at least one evidence id each |

Validators: unique event ids, ascending unique sequences, non-blank text, every cited id exists,
every claim and fact is consistent with the labels of the events it cites, at least one claim.

This is the event-based smoke contract. It is different from the frozen QMSum-shaped
`CatchupExample` in `session-service/app/schemas.py` (`query`, `context_spans`,
`reference_summary`), which is unchanged and still describes `data/splits/m1_v1/`.

## The five categories

| Category (`m1-output-v1`) | Event label | Typical events |
|---------------------------|-------------|----------------|
| `completed` | `completed` | `doc_update`, `agent_step`, `tool_result`, `rollback` |
| `in_progress` | `in_progress` | `agent_step` with partial progress |
| `blocked` | `blocked` | `agent_step` after a failed `tool_result` |
| `decisions` | `decision` | `instruction`, `interrupt`, `handoff`, `arbitration` |
| `pending_actions` | `pending_action` | `instruction` assigning future work |

A label sits on the event that settles an item's final state. A claim cites that event and,
sometimes, supporting events (for example the failing tool result behind a blocker).

## Relationship to other contracts

- **QMSum `m1_v1`** (`data/splits/m1_v1/`, frozen): meeting transcripts for ROUGE supervision. Not
  touched. The smoke set is a separate, event-shaped dataset.
- **DAT-55 `m1-input-v1` / `m1-output-v1`** (Pramod): `to_m1_input` maps `source_event_id` to
  `event_id` and sets `memory_version` to null and `approved_memory` to `[]`. `gold_reference`
  returns the `m1-output-v1` shape without `candidate_id`. When this was written the contract was
  not on `main` (it is on the DAT-55 branch, PR #20). The compatibility test imports
  `eval.contracts.m1` and skips with a reason until it lands. All 18 examples were checked by hand
  against the DAT-55 branch version of `M1Input`, `M1Output` and `validate_m1_pair` and passed.
  Pramod should confirm the mapping.
- The contract plans real session data in `data/splits/m1_session_v1/`. That is not this dataset.

## Known simplification

Rolled-back events stay in the log here, with the `rollback` event after them, so a catch-up can
describe them. In the live service, rollback deletes events after `to_seq`. Open question for review.
