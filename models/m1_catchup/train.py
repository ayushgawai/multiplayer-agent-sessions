"""M1 Catch-up Summarizer Full Training Script.

Trains LoRA adapter for candidate models (e.g. m1-b Qwen3-1.7B) using QLoRA.
Supports resuming from checkpoint, structured validation, and artifact export.

Usage:
  python models/m1_catchup/train.py --config eval/configs/m1-b.yaml [--resume]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import torch
import yaml
from packaging.version import Version
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
    default_data_collator,
)
from transformers.trainer_utils import get_last_checkpoint

REPO_ROOT = Path(__file__).resolve().parents[2]

SYSTEM_PROMPT = (
    "You summarize a multiplayer agent session. Given a query and dialogue context spans, "
    "provide a concise, accurate catch-up summary directly addressing the query."
)


class CatchupDataset(Dataset):
    def __init__(self, jsonl_path: Path, tokenizer: Any, max_length: int = 2048):
        self.items: list[dict[str, torch.Tensor]] = []
        if not jsonl_path.exists():
            raise FileNotFoundError(f"Split file missing: {jsonl_path}")

        print(f"  Loading dataset from {jsonl_path.name}...")
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                query = row.get("query", "")
                spans = row.get("context_spans", [])
                reference = row.get("reference_summary", "")

                context_str = "\n".join(spans[:40])  # bound context window
                user_content = f"Query: {query}\n\nContext:\n{context_str}"

                prompt_messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ]
                full_messages = prompt_messages + [
                    {"role": "assistant", "content": reference}
                ]

                try:
                    prompt_text = tokenizer.apply_chat_template(
                        prompt_messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
                    )
                    full_text = tokenizer.apply_chat_template(
                        full_messages, tokenize=False, add_generation_prompt=False, enable_thinking=False
                    )
                except Exception:
                    prompt_text = f"<system>\n{SYSTEM_PROMPT}\n<user>\n{user_content}\n<assistant>\n"
                    full_text = f"{prompt_text}{reference}"

                prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
                encoded = tokenizer(
                    full_text, truncation=True, max_length=max_length, padding="max_length", add_special_tokens=False
                )

                labels = list(encoded["input_ids"])
                prompt_length = min(len(prompt_ids), max_length)
                labels[:prompt_length] = [-100] * prompt_length
                labels = [label if mask else -100 for label, mask in zip(labels, encoded["attention_mask"])]

                if any(lbl != -100 for lbl in labels):
                    self.items.append({
                        "input_ids": torch.tensor(encoded["input_ids"], dtype=torch.long),
                        "attention_mask": torch.tensor(encoded["attention_mask"], dtype=torch.long),
                        "labels": torch.tensor(labels, dtype=torch.long),
                    })

        print(f"  Loaded {len(self.items)} valid training samples from {jsonl_path.name}")

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        return self.items[index]


def train(config_path: Path, resume: bool = False, max_steps: int | None = None) -> None:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    candidate_id = config["candidate_id"]
    model_id = config["model"]["repo"]
    revision = config["model"]["revision"]
    train_cfg = config["train"]
    lora_cfg = config["lora"]

    output_dir = REPO_ROOT / "checkpoints" / candidate_id
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"  M1 FULL TRAINING — Candidate: {candidate_id} ({model_id})")
    print(f"  Checkpoints Directory: {output_dir}")
    print("=" * 70)

    # Dtype and device
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

    # Tokenizer
    print("  Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Datasets
    split_dir = REPO_ROOT / config["split"]
    max_seq_len = min(int(train_cfg.get("max_seq_len", 2048)), 2048)  # safe memory ceiling
    train_dataset = CatchupDataset(split_dir / "train.jsonl", tokenizer, max_length=max_seq_len)
    eval_dataset = CatchupDataset(split_dir / "val.jsonl", tokenizer, max_length=max_seq_len)

    # Model in 4-bit NF4
    print("  Loading base model in 4-bit NF4...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        revision=revision,
        quantization_config=bnb_config,
        device_map={"": 0},
        torch_dtype=compute_dtype,
        attn_implementation="sdpa",
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    # LoRA
    peft_config = LoraConfig(
        task_type="CAUSAL_LM",
        r=int(lora_cfg["r"]),
        lora_alpha=int(lora_cfg["alpha"]),
        lora_dropout=float(lora_cfg["dropout"]),
        bias="none",
        target_modules=list(lora_cfg["target_modules"]),
    )
    model = get_peft_model(model, peft_config)
    trainable, total = model.get_nb_trainable_parameters()
    print(f"  Trainable Parameters: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # Training arguments
    batch_size = 1
    gradient_accumulation_steps = max(1, int(train_cfg.get("effective_batch_size", 16)) // batch_size)
    epochs = int(train_cfg.get("epochs", 3))
    learning_rate = float(train_cfg.get("lr", 2e-4))
    save_steps = int(train_cfg.get("save_steps", 50))

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs if max_steps is None else 1,
        max_steps=max_steps if max_steps is not None else -1,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=float(train_cfg.get("warmup_ratio", 0.06)),
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=save_steps,
        save_strategy="steps",
        save_steps=save_steps,
        save_total_limit=3,
        save_safetensors=True,
        optim="paged_adamw_8bit",
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        remove_unused_columns=False,
        dataloader_num_workers=0,
        report_to=[],
        seed=298,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=default_data_collator,
    )

    last_checkpoint = get_last_checkpoint(str(output_dir)) if resume else None
    if last_checkpoint:
        print(f"  Resuming from checkpoint: {last_checkpoint}")

    start_time = time.perf_counter()
    train_result = trainer.train(resume_from_checkpoint=last_checkpoint)
    elapsed = time.perf_counter() - start_time

    # Save final model adapter and tokenizer
    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    print("=" * 70)
    print("  TRAINING COMPLETED ✅")
    print(f"  Elapsed Time: {elapsed/60:.2f} minutes")
    print(f"  Final Loss:   {train_result.training_loss:.4f}")
    print(f"  Final Model:  {final_dir}")
    print("=" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(description="M1 Full Training")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "eval" / "configs" / "m1-b.yaml")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--max-steps", type=int, default=None, help="Cap training steps")
    args = parser.parse_args()

    train(args.config, resume=args.resume, max_steps=args.max_steps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
