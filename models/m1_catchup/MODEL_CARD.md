# Task

Session-state catch-up summarization for hand-off and late joiners. Inputs are a query plus context spans. Output is a short summary. Primary metric ROUGE-L. Supervised on QMSum; evaluated on the session split once recorded.

## Candidates tested

| id | model | mode | primary metric (mean ± std) | latency p50 | peak VRAM | cost |
|----|-------|------|-----------------------------|-------------|-----------|------|
| m1-a | ModernBERT-base extractive | finetune | — | — | — | 0 |
| m1-b | Qwen3-1.7B LoRA | lora | — | — | — | 0 |
| m1-c | Qwen3.5-4B LoRA | lora | — | — | — | 0 |
| m1-d | Gemma 4 E4B LoRA | lora | — | — | — | 0 |

## Selection

Winner: to be filled after bake-off  
Runner-up: to be filled after bake-off  
Margin on primary metric: to be filled after bake-off  
Tie-break applied: to be filled after bake-off  

## Trade-off accepted

To be filled after bake-off.

## What would reverse this decision

To be filled after bake-off.

## Failure profile of the winner

| code | count | share of errors | example |
|------|-------|-----------------|---------|
| — | — | — | — |

## Reproduction

Command: `python eval/harness.py --task m1 --candidate m1-c --seeds 13,29,47 --split real`  
Result file: `eval/results/m1-c.json`  
Independent verification: `docs/verification/m1.md`
