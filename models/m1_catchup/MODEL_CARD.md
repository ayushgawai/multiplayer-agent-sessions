# Task

Session-state catch-up summarization for hand-off and late joiners. Inputs are
a query plus context spans. Output is a short summary. Primary metric ROUGE-L.
Supervised on QMSum; evaluated additionally on the session split once recorded.

## Candidates tested

| id | model | mode | primary metric (mean ± std) | latency p50 | peak VRAM | cost |
|----|-------|------|-----------------------------|-------------|-----------|------|
| m1-a | ModernBERT-base extractive | finetune | pending | pending | pending | 0 |
| m1-b | Qwen3-1.7B LoRA | lora | pending | pending | pending | 0 |
| m1-c | Qwen3.5-4B LoRA | lora | pending | pending | pending | 0 |
| m1-d | Gemma 4 E4B LoRA | lora | pending | pending | pending | 0 |

## Selection

Winner: pending bake-off
Runner-up: pending
Margin on primary metric: pending
Tie-break applied: pending

## Trade-off accepted

Pending.

## What would reverse this decision

Pending.

## Failure profile of the winner

| code | count | share of errors | example |
|------|-------|-----------------|---------|
| pending | | | |

## Reproduction

Command: python eval/harness.py --task m1 --candidate m1-c --seeds 13,29,47 --split real
Result file: eval/results/m1-c.json
Independent verification: docs/verification/m1.md
