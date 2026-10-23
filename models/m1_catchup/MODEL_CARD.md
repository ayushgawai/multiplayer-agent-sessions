# Task

Session-state catch-up summarization for hand-offs and late joiners. Input is a query plus
ordered session events. Output is structured into completed work, work in progress, blockers,
decisions, and pending actions, with evidence IDs on every claim.

## Frozen candidates

| ID | Model | Mode | Status |
|---|---|---|---|
| `m1-a` | BM25 ranker plus fixed template | Classical CPU | Contract frozen; implementation pending |
| `m1-b` | ModernBERT-base selector plus fixed template | Full fine-tune | Contract frozen; implementation pending |
| `m1-c` | Phi-4-mini-instruct | 4-bit QLoRA | Contract frozen; feasibility pending |
| `m1-d` | Qwen3.5-4B | 4-bit QLoRA | Contract frozen; conditional loader pending |

No final candidate has been evaluated or selected. Promotion requires the hard safety gates,
three seeds, and ranking policy in `eval/configs/m1-contract.yaml`.

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
