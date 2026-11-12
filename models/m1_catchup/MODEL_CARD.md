# Task

Session-state catch-up summarization for hand-offs and late joiners. Input is a query plus
ordered session events. Output is structured into completed work, work in progress, blockers,
decisions, and pending actions, with evidence IDs on every claim.

## Frozen candidates

| ID | Model | Mode | Status |
|---|---|---|---|
| `m1-a` | BM25 ranker plus fixed template | Classical CPU | Implemented on `main` via DAT-58 / PR #26; smoke-only integration run passed 3/3 schema-valid examples; no reportable evaluation |
| `m1-b` | ModernBERT-base selector plus fixed template | Full fine-tune | Candidate code remains off `main`; 40-step GPU feasibility smoke passed; no reportable training or evaluation |
| `m1-c` | Phi-4-mini-instruct | 4-bit QLoRA | Candidate code remains off `main`; first feasibility run stopped after 2/15 steps and needs diagnosis |
| `m1-d` | Qwen3.5-4B | 4-bit QLoRA | Candidate code remains off `main`; feasibility run not started |

No final candidate has been evaluated or selected. Promotion requires the hard safety gates,
three seeds, and ranking policy in `eval/configs/m1-contract.yaml`.

## Current evidence and limitations

The DAT-55 contract and configs, DAT-61 harness, and harness follow-ups are on `main` through
PRs #20, #25, and #41. M1-A is also on `main` through PR #26 and exposes
`models.m1_catchup.bm25:build_eval_runner` to the shared harness. Its current 3/3 run uses the
synthetic `smoke_holdout` fixture and checks schema and integration only. The M1-A rules were
fitted on the synthetic smoke train/dev templates, so this run must not be reported as model
quality or generalization evidence.

There is still no frozen annotated product-session split at `data/splits/m1_session_v1/`, no
production metric-evaluator result, no committed candidate result JSON, and no selected winner.
The real bake-off begins only after the evaluator and session split are frozen and all candidates
can run through the same contract. Serving remains a stub until a winner passes those gates.

## Human-governed improvement condition

The frozen candidate comparison uses `memory_disabled`. After a winner is selected, the extension
compares that same model under `memory_disabled` and `approved_memory` on the same eligible examples.
Only human-approved `LearningEvent` records may be retrieved; proposed or rejected lessons and any
feedback from the frozen test split must never enter memory. This is retrieval-time adaptation, not
autonomous online weight updating. The `LearningEvent` implementation is not yet on `main`, so no
self-improvement result may be claimed from the current repository.

## Historical feasibility run—not a candidate result

Qwen3-1.7B was used to verify GPU loading, QLoRA, checkpoint/resume, and inference. The
50-step run reached training loss 2.14 and wrote a 133 MB adapter. Loss is not catch-up
quality, and this model is not part of the final matrix. The preserved configuration is
`models/m1_catchup/feasibility/qwen3-1.7b.yaml`; evidence remains in
`docs/verification/m1_training_run.md` and `docs/verification/m1_verification/`.

## Evaluation

Report critical-fact recall, unsupported-claim rate, evidence attribution, status
consistency, schema-valid rate, ROUGE-L, BERTScore-F1, human edit rate, latency p50/p95, and
peak VRAM. A higher ROUGE score cannot compensate for failure of a grounding safety gate.
