# ADR-005: Freeze the M1 experiment and candidate-selection contract

- Status: Proposed (implementation complete; independent review pending)
- Date: 2026-10-22
- Owner: M1 contract owner. Reviewer: independent evaluation or model owner

## Context

M1 produces a session-state catch-up for a late joiner or agent hand-off. Earlier candidate
files represented an exploratory matrix and treated ROUGE-L as the primary metric. That is
not sufficient for the final product: a fluent summary can omit a blocker, assign an action
to the wrong person, or invent progress while still achieving high lexical overlap.

The four candidates also need one input/output contract and one frozen evaluation policy
before comparative runs begin. The prior Qwen3-1.7B run remains useful only as GPU,
checkpoint, resume, and inference-path evidence; it is not one of the final candidates.

## Decision

### Candidate matrix

| ID | Candidate | Role |
|---|---|---|
| `m1-a` | BM25 event ranker plus fixed structured template | Transparent CPU floor |
| `m1-b` | ModernBERT-base event selector plus the same template | Learned extractive arm |
| `m1-c` | Phi-4-mini-instruct with QLoRA | Compact generative family |
| `m1-d` | Qwen3.5-4B with QLoRA | Larger generative family |

Every model revision is a full 40-character commit. The learned candidates use three epochs,
4,096 input tokens, effective batch size 16, and seeds 13, 29, and 47. Architecture-specific
learning rates, loaders, and LoRA module names may differ and are committed before a run.
The CPU control has no fictitious training or GPU settings.

### Input and output

`eval.contracts.m1` is the executable source of truth:

- `m1-input-v1` contains a stable example ID, session ID, query, ordered events with stable
  event IDs, and an optional versioned list of human-approved behavioral lessons.
- `m1-output-v1` contains `completed`, `in_progress`, `blocked`, `decisions`, and
  `pending_actions`. Every claim contains non-blank text and one or more unique
  `source_event_ids` from the input.
- Approved memory can influence behavior but is not evidence for a session fact. Every output
  fact must cite current input events.
- The canonical text projection processes categories in the order above, retains item order,
  normalizes internal whitespace, and excludes category names, JSON, and evidence IDs.

QMSum context spans must be adapted to ordered events with deterministic event IDs before
entering a candidate. Product evaluation uses native session events. Free-form model text is
invalid until parsed into `m1-output-v1`.

QMSum supplies auxiliary query-focused summarization supervision and a separately reported
semantic/lexical benchmark. It does not contain the product status categories, claim-level
support labels, owner labels, or source-event entailment annotations required by the safety
gates. It therefore cannot select the final product winner by itself. ModernBERT relevance
labels derived from QMSum are training-only weak supervision; they must never be presented as
human evidence labels. Final selection requires the frozen annotated product-session split.

### Data and leakage rules

1. Use the committed QMSum train, validation, and test files and verify them against
   `data/splits/m1_v1/MANIFEST.json`.
2. Split product examples by `session_id`; no session may appear in more than one split.
3. Freeze split files, preprocessing, critical facts, evidence links, and manifest hashes
   before the first comparative run.
4. Use validation data for prompts, thresholds, early stopping, and hyperparameters. Inspect
   the test split only for the final frozen comparison.
5. Never write test outputs, verifier feedback, or human test corrections into approved
   memory. Candidate selection runs with memory disabled. The selected candidate is then
   measured separately with memory disabled and approved train/validation memory enabled.
6. Synthetic examples may augment training only. They never enter validation or test.

### Metrics

The machine-readable definitions are in `eval/configs/m1-contract.yaml`. BERTScore is pinned
to `bert-score==0.3.13`, `FacebookAI/roberta-large` revision
`722cf37b1afa9454edce342e7895e588b6ff1d59`, layer 17, without IDF weighting or baseline
rescaling. Report schema-valid
rate, critical-fact recall, unsupported-claim rate, attribution accuracy, status consistency,
ROUGE-L, BERTScore-F1, human edit rate, latency p50/p95, and peak VRAM. Report means,
per-seed values, and 95% confidence intervals; do not pool predictions across seeds before
computing the per-seed metric.

Critical facts, support judgments, evidence IDs, and status labels are frozen annotations.
Unsupported claims and attribution use claim-level denominators. Zero emitted claims do not
earn a perfect safety score: they fail critical-fact recall and are reported with zero
attribution accuracy plus the `generic_output` or `missing_critical_fact` failure code.

### Candidate selection

Only runs completing all three seeds are eligible. On the annotated product-session test
split, a candidate must achieve at least 98% schema validity, no more than 2% unsupported
claims, unsupported-claim performance no worse than `m1-a`, at least 95% attribution
accuracy, and at least 95% status consistency.

Rank eligible candidates by mean critical-fact recall, then BERTScore-F1, then ROUGE-L. Values
within 0.01 are a quality tie; resolve a tie by latency p95 and then peak VRAM. Confirm the
top two with a blinded human review before promotion. ROUGE alone can never select a winner.
If no candidate passes the gates, report that no model is promotable and continue using the
extractive control while failures are corrected.

### Reproducibility and hardware

Each result records the contract version, candidate config hash, dataset manifest hashes,
git SHA, model repository and revision, seed, memory condition and version, hardware, package
versions, latency, peak VRAM, raw structured outputs, verifier outputs, and metric convention
versions. GPU candidates run on the university RTX 4090 or 5090 pool; hardware-specific
latency and VRAM are never compared without naming the GPU.

## Consequences

- DAT-55 freezes the experiment but does not claim that all four implementations or the
  annotated product-session split already exist.
- Candidate-specific feasibility tests are required before the full bake-off. In particular,
  Qwen3.5 uses a conditional-generation architecture and must not be passed silently through
  the older causal-LM-only trainer.
- The prior Qwen3-1.7B checkpoint remains infrastructure evidence under
  `models/m1_catchup/feasibility/`; it cannot appear in final four-candidate results.
- Metric implementations may land in focused follow-up PRs, but their definitions and winner
  policy cannot change after test results are seen without a new contract version and ADR.
