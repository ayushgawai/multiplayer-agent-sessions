# M1 Catch-up Training Run Verification & Metrics

This document records the exact configuration, training dynamics, loss values, and verification manifest for the M1 Catch-up Summarizer full power training run.

## Executive Summary

* **Task ID:** DAT-55
* **Candidate ID:** `m1-b`
* **Base Architecture:** `Qwen/Qwen3-1.7B`
* **Fine-tuning Strategy:** 4-bit NF4 QLoRA on all 7 linear projection layers
* **LoRA Configuration:** Rank $r=32$, $\alpha=64$, dropout 0.05
* **Parameters Trained:** 34,865,152 (1.99% of total 1.75B parameters)
* **Dataset:** Yale-LILY QMSum (`data/splits/m1_v1/`), 1,194 train sequences, 261 val sequences
* **Effective Batch Size:** 16 (gradient accumulation 16)
* **Sequence Length:** 2,048 tokens
* **Hardware:** NVIDIA GeForce RTX 5080 Laptop GPU (16 GB VRAM)
* **Peak VRAM Allocated:** 15.98 GB / 16.30 GB (98% utilization)
* **GPU Compute Load:** 100% sustained
* **Total Sequences Processed:** 800 sequences (50 optimizer steps)
* **Initial Loss:** 3.9066 (step 10)
* **Final Converged Loss:** 2.1478 (step 40) / 2.1581 (step 50)
* **Checkpoints:** `checkpoints/m1-b/checkpoint-50` and `checkpoints/m1-b/final-50` (133 MB adapter safetensors, verified and synced locally)

## Step-by-Step Training Log

| Step | Epoch | Training Loss | Grad Norm | Learning Rate | VRAM Used |
|---|---|---|---|---|---|
| 10 | 0.13 | 3.9066 | 1.2749 | 1.17e-4 | 15.98 GB |
| 20 | 0.27 | 2.2755 | 0.7864 | 2.48e-4 | 15.98 GB |
| 30 | 0.40 | 2.2611 | 0.7424 | 3.00e-4 | 15.98 GB |
| 40 | 0.54 | 2.1478 | 0.6960 | 2.98e-4 | 15.98 GB |
| 50 | 0.67 | 2.1581 | 0.6657 | 2.96e-4 | 15.98 GB |

## Validation Results

* **Validation Split:** 261 multi-turn meeting transcripts and query-summary pairs
* **Evaluation Batches:** 33 batches evaluated at step 50
* **Evaluation Throughput:** 6.25 seconds per evaluation batch
* **Verification Status:** Adapter safetensors loaded successfully in PyTorch float16 and bfloat16 inference tests

## Artifact Locations

* **Local Checkpoints:** `checkpoints/m1-b/final-50/` (`adapter_model.safetensors`, `adapter_config.json`)
* **Training Code:** `models/m1_catchup/train.py`
* **Feasibility Notebook:** `models/m1_catchup/notebooks/m1_qwen3_gpu_verification.ipynb`
* **Executed Configuration:** originally `eval/configs/m1-b.yaml`; preserved after DAT-55 at `models/m1_catchup/feasibility/qwen3-1.7b.yaml`
* **Dataset Splits:** `data/splits/m1_v1/`
