# M1 Catch-up Summarizer

Session-state catch-up summarizer for late joiners and agent hand-offs. Given an incoming participant query and a sliding event context window, M1 generates a structured summary covering completed actions, in-progress tasks, and current blockers.

## Architecture and Training Setup

* **Base Model:** `Qwen/Qwen3-1.7B` (revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`)
* **Quantization:** 4-bit NF4 with double quantization and bfloat16 compute dtype
* **Parameter-Efficient Tuning:** QLoRA with rank $r=32$, $\alpha=64$, dropout 0.05
* **Target Modules:** All 7 projection layers (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`)
* **Trainable Parameters:** 34,865,152 of 1,755,440,128 total (1.99%)
* **Optimizer:** `paged_adamw_8bit` with gradient checkpointing and PyTorch SDPA attention
* **Context Length:** 2,048 tokens
* **Effective Batch Size:** 16 (gradient accumulation 16)
* **Dataset Supervision:** Yale-LILY QMSum frozen splits in `data/splits/m1_v1/` (1,194 train, 261 val, 281 test)

## Training Progress and Metrics

* **Initial Step Loss:** 3.9066 (step 10)
* **Mid-Run Loss:** 2.2755 (step 20)
* **Converged Loss:** 2.1478 (step 40) to 2.1581 (step 50)
* **Sequences Processed:** 800 meeting dialogue sequences
* **Checkpoints:** Stored in `checkpoints/m1-b/checkpoint-50` and `checkpoints/m1-b/final-50`
* **Local Checkpoint Size:** 133 MB adapter safetensors (`adapter_model.safetensors`)

## Scripts and Notebooks

* **Training Entrypoint:** `models/m1_catchup/train.py`
* **Infrastructure Smoke Test:** `models/m1_catchup/notebooks/m1_qwen3_gpu_smoke_test.ipynb`
* **Configuration:** `eval/configs/m1-b.yaml`
* **Serving Stub:** `serving/adapters/m1.py`
