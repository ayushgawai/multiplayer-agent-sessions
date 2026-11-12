# M1 Catch-up Summarizer

M1 creates an evidence-linked session catch-up for late joiners and agent hand-offs. The
frozen contract is `m1-input-v1` to `m1-output-v1`; every claim is categorized and cites one
or more source-event IDs.

## Final DAT-55 candidate matrix

| ID | Candidate | Training path |
|---|---|---|
| `m1-a` | BM25 event ranker plus fixed template | CPU, no training |
| `m1-b` | ModernBERT-base selector plus fixed template | Encoder fine-tune |
| `m1-c` | Phi-4-mini-instruct | Candidate-specific causal-LM QLoRA trainer required |
| `m1-d` | Qwen3.5-4B | Candidate-specific conditional-generation QLoRA trainer required |

Candidate selection is safety-gated and uses critical-fact recall as the first ranking
metric. ROUGE-L is supporting evidence only. See `eval/configs/m1-contract.yaml` and
`docs/decisions/ADR-005-m1-experiment-contract.md`.

QMSum is auxiliary summarization supervision. It does not provide the structured status and
claim-evidence annotations required for final promotion. The winner must be selected on the
frozen annotated product-session split; until that split exists, no candidate can win.

## Existing GPU feasibility evidence

The October Qwen3-1.7B run verified 4-bit NF4 loading, all-linear QLoRA, checkpoint saving,
resume, and inference on an RTX 5080 Laptop. It reached training loss 2.14 at step 50 and
saved a 133 MB adapter. This is infrastructure evidence, not a final candidate result and not
proof of model quality. Its executed configuration is preserved at
`models/m1_catchup/feasibility/qwen3-1.7b.yaml` so migration of `m1-b` to ModernBERT does not
make the verification notebook unreproducible.

## Paths

* **Contract:** `eval/contracts/m1.py`
* **Experiment policy:** `eval/configs/m1-contract.yaml`
* **Candidate configs:** `eval/configs/m1-a.yaml` through `m1-d.yaml`
* **Legacy feasibility trainer:** `models/m1_catchup/train.py`
* **Legacy GPU verification:** `models/m1_catchup/notebooks/m1_qwen3_gpu_verification.ipynb`
* **Serving stub:** `serving/adapters/m1.py`
