# Task

Session-state catch-up summarization for hand-off and late joiners. Inputs are a query plus context spans. Output is a short summary. Primary metric ROUGE-L. Supervised on QMSum; evaluated on the session split once recorded.

## Candidates Tested

| ID | Model | Mode | Parameters Trained | Loss | Latency (p50) | Peak VRAM | Status |
|---|---|---|---|---|---|---|---|
| m1-a | ModernBERT-base extractive | Finetune | Scheduled | Pending | Pending | Pending | Planned |
| m1-b (baseline) | Qwen3-1.7B LoRA (q/v only) | 4-bit QLoRA | 12.8M (0.7%) | 2.29 eval loss | 42 ms | ~9.2 GB | Completed |
| m1-b (high power) | Qwen3-1.7B LoRA (all linear) | 4-bit QLoRA | 34.8M (1.99%) | 2.14 train loss | 51 ms | ~15.9 GB | Completed (checkpoint-50) |
| m1-c | Qwen3.5-4B LoRA | 4-bit QLoRA | Scheduled | Pending | Pending | Pending | Planned |
| m1-d | Gemma 4 E4B LoRA | 4-bit QLoRA | Scheduled | Pending | Pending | Pending | Planned |

## High Power Training Specification (m1-b checkpoint-50)

* **Base Model:** `Qwen/Qwen3-1.7B`
* **LoRA Rank / Alpha:** $r=32$, $\alpha=64$
* **Target Modules:** `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
* **Trainable Parameters:** 34,865,152 / 1,755,440,128 (1.99%)
* **Effective Batch Size:** 16 (gradient accumulation 16, per-device batch 1)
* **Sequence Length:** 2,048 tokens
* **Loss Progression:**
  * Step 10: 3.9066
  * Step 20: 2.2755
  * Step 30: 2.2611
  * Step 40: 2.1478
  * Step 50: 2.1581
* **Checkpoint Path:** `checkpoints/m1-b/final-50` (synced locally, 133 MB adapter)

## Reproduction

* **Feasibility Notebook:** `models/m1_catchup/notebooks/m1_qwen3_gpu_verification.ipynb`
* **Training Command:** `python models/m1_catchup/train.py --config eval/configs/m1-b.yaml`
* **Verification Docs:** `docs/verification/m1_training_run.md` and `docs/verification/m1_smoke/run_manifest.json`
