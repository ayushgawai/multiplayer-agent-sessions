"""M1-C (Phi-4-mini-instruct) and M1-D (Qwen3.5-4B): 4-bit NF4 QLoRA generative candidates.

The config's ``trainer`` field picks the loader explicitly:

* ``causal_lm_qlora`` -> ``AutoModelForCausalLM`` (Phi-4-mini-instruct, ``Phi3ForCausalLM``).
* ``conditional_generation_qlora`` -> ``AutoModelForImageTextToText`` (Qwen3.5-4B, whose
  checkpoint is ``Qwen3_5ForConditionalGeneration``: a vision-language model with a hybrid
  Gated DeltaNet / full-attention text stack). Only text is fed; the vision tower is unused
  and gets no LoRA because the frozen target names exist only in the language model.

Frozen ``lora.target_modules`` are checked against the loaded model; a missing name raises
instead of being silently dropped or renamed.

The model emits only the five category keys as JSON; ``candidates.parse_generation`` adds the
identity fields and the harness validates against ``m1-output-v1``. Free text stays invalid.
Training targets come from ``candidates.weak_target`` (weak QMSum supervision, see there).
"""

from __future__ import annotations

import statistics
import time
from typing import Any

from eval.contracts.m1 import M1Input, qmsum_row_to_m1_input
from models.m1_catchup.candidates import (
    REPO_ROOT,
    SYSTEM_PROMPT,
    PreparedCandidate,
    checkpoint_uri,
    fit_events,
    load_qmsum,
    parse_generation,
    run_trainer,
    target_text,
    user_prompt,
    validation_error,
    weak_target,
)

AUTO_CLASSES = {
    "causal_lm_qlora": "AutoModelForCausalLM",
    "conditional_generation_qlora": "AutoModelForImageTextToText",
}
MAX_NEW_TOKENS = 768
TEMPLATE_OVERHEAD = 64  # chat-template tokens around system/user/assistant text


def _chat(tokenizer: Any, messages: list[dict[str, str]], add_generation_prompt: bool) -> str:
    # enable_thinking is read by the Qwen3.5 template and ignored by Phi-4-mini's.
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=add_generation_prompt, enable_thinking=False
    )


def _count(tokenizer: Any) -> Any:
    return lambda text: len(tokenizer(text, add_special_tokens=False).input_ids)


def build_prompt(tokenizer: Any, model_input: M1Input, budget: int) -> tuple[list[dict], list]:
    """Chat messages with the longest event prefix that fits ``budget`` tokens."""

    events = fit_events(model_input.events, _count(tokenizer), budget)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(model_input.query, events)},
    ]
    return messages, events


def build_example(tokenizer: Any, row: dict[str, Any], max_len: int) -> dict[str, list[int]] | None:
    """Tokenized training example; loss only on the JSON answer. None if nothing to learn."""

    model_input = qmsum_row_to_m1_input(row)
    reference = row["reference_summary"]
    estimate = _count(tokenizer)(target_text(weak_target(model_input.events, reference)))
    messages, events = build_prompt(tokenizer, model_input, max_len - estimate - TEMPLATE_OVERHEAD)
    answer = target_text(weak_target(events, reference))
    prompt = _chat(tokenizer, messages, add_generation_prompt=True)
    full = _chat(tokenizer, [*messages, {"role": "assistant", "content": answer}], False)
    if not full.startswith(prompt):
        full = prompt + answer + tokenizer.eos_token
    prompt_len = len(tokenizer(prompt, add_special_tokens=False).input_ids)
    ids = tokenizer(full, add_special_tokens=False).input_ids[:max_len]
    labels = ([-100] * prompt_len + ids[prompt_len:])[: len(ids)]
    if all(label == -100 for label in labels):
        return None
    return {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": labels}


def _tokenizer(config: dict[str, Any]) -> Any:
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        config["model"]["repo"], revision=config["model"]["revision"]
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def load_base(config: dict[str, Any]) -> Any:
    import torch
    import transformers

    trainer = config["trainer"]
    if trainer not in AUTO_CLASSES:
        raise ValueError(f"qlora.py does not handle trainer {trainer!r}")
    auto = getattr(transformers, AUTO_CLASSES[trainer])
    model = auto.from_pretrained(
        config["model"]["repo"],
        revision=config["model"]["revision"],
        quantization_config=transformers.BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        ),
        device_map={"": 0},
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    if trainer == "conditional_generation_qlora" and not type(model).__name__.endswith(
        "ForConditionalGeneration"
    ):
        raise TypeError(f"expected a conditional-generation model, got {type(model).__name__}")
    return model


def missing_target_modules(module_names: list[str], targets: list[str]) -> list[str]:
    leaves = {name.rsplit(".", 1)[-1] for name in module_names}
    return [target for target in targets if target not in leaves]


def train(
    *,
    config: dict[str, Any],
    seed: int,
    max_steps: int | None = None,
    max_train_examples: int | None = None,
    max_seq_len: int | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import DataCollatorForSeq2Seq, set_seed

    set_seed(seed)
    max_len = max_seq_len or int(config["train"]["max_seq_len"])
    tokenizer = _tokenizer(config)
    rows = load_qmsum(REPO_ROOT / config["split"], "train")[:max_train_examples]
    examples = [ex for ex in (build_example(tokenizer, row, max_len) for row in rows) if ex]

    model = load_base(config)
    lora = config["lora"]
    missing = missing_target_modules([name for name, _ in model.named_modules()], lora["target_modules"])
    if missing:
        raise ValueError(f"frozen lora.target_modules not found in {type(model).__name__}: {missing}")
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    model = get_peft_model(
        model,
        LoraConfig(
            task_type="CAUSAL_LM",
            r=int(lora["r"]),
            lora_alpha=int(lora["alpha"]),
            lora_dropout=float(lora["dropout"]),
            bias="none",
            target_modules=list(lora["target_modules"]),
        ),
    )
    trainable, total = model.get_nb_trainable_parameters()
    stats = run_trainer(
        model=model,
        dataset=examples,
        collator=DataCollatorForSeq2Seq(tokenizer, padding=True, label_pad_token_id=-100),
        config=config,
        seed=seed,
        per_device_batch=1,
        max_steps=max_steps,
        resume=resume,
        optim="paged_adamw_8bit",
        gradient_checkpointing=True,
    )
    lengths = [len(ex["input_ids"]) for ex in examples]
    return {
        **stats,
        "model_class": type(model.get_base_model()).__name__,
        "max_seq_len": max_len,
        "train_rows": len(rows),
        "train_examples": len(examples),
        "seq_len_mean": round(statistics.fmean(lengths), 1),
        "seq_len_max": max(lengths),
        "examples_at_max_seq_len": sum(length >= max_len for length in lengths),
        "trainable_params": trainable,
        "total_params": total,
    }


class Generator:
    """Loaded base model plus the newest adapter checkpoint for one seed."""

    def __init__(self, config: dict[str, Any], seed: int, max_seq_len: int | None = None) -> None:
        from peft import PeftModel

        from models.common.checkpointing import resume_from_checkpoint

        step_dir = resume_from_checkpoint(checkpoint_uri(config, seed))
        if step_dir is None:
            raise FileNotFoundError(f"no trained {config['candidate_id']} adapter for seed {seed}")
        self.step_dir = step_dir
        self.candidate_id = config["candidate_id"]
        self.tokenizer = _tokenizer(config)
        self.model = PeftModel.from_pretrained(load_base(config), str(step_dir))
        self.model.eval()
        self.max_len = max_seq_len or int(config["train"]["max_seq_len"])
        self.last_new_tokens = 0
        self.last_raw_text = ""

    def predict(self, model_input: M1Input) -> dict[str, Any]:
        import torch

        budget = self.max_len - MAX_NEW_TOKENS - TEMPLATE_OVERHEAD
        messages, _ = build_prompt(self.tokenizer, model_input, budget)
        prompt = _chat(self.tokenizer, messages, add_generation_prompt=True)
        encoded = self.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").to("cuda")
        with torch.no_grad():
            generated = self.model.generate(
                **encoded,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=self.tokenizer.pad_token_id,
            )
        new_tokens = generated[0, encoded["input_ids"].shape[1] :]
        self.last_new_tokens = int(new_tokens.shape[0])
        self.last_raw_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return parse_generation(self.last_raw_text, model_input.example_id, self.candidate_id)


def predict_validation(
    config: dict[str, Any], seed: int, *, n: int, max_seq_len: int | None = None
) -> dict[str, Any]:
    """Feasibility inference on the first n validation rows (never test)."""

    import torch

    generator = Generator(config, seed, max_seq_len)
    rows = load_qmsum(REPO_ROOT / config["split"], "val")[:n]
    torch.cuda.reset_peak_memory_stats()
    latencies, errors, new_tokens, raw = [], [], [], []
    for row in rows:
        model_input = qmsum_row_to_m1_input(row)
        started = time.perf_counter()
        output = generator.predict(model_input)
        latencies.append(time.perf_counter() - started)
        new_tokens.append(generator.last_new_tokens)
        errors.append(validation_error(output, model_input))
        raw.append(generator.last_raw_text)
    return {
        "checkpoint": generator.step_dir.as_posix(),
        "examples": len(rows),
        "valid_m1_output_v1": sum(error is None for error in errors),
        "errors": [error[:300] for error in errors if error][:3],
        "hit_max_new_tokens": sum(count >= MAX_NEW_TOKENS for count in new_tokens),
        "latency_ms_mean": round(1000 * statistics.fmean(latencies), 1),
        "latency_ms_median": round(1000 * statistics.median(latencies), 1),
        "generated_tokens_per_s": round(sum(new_tokens) / sum(latencies), 2),
        "peak_vram_mb": round(torch.cuda.max_memory_allocated() / 2**20, 1),
        "sample_raw_output": raw[0][:600] if raw else "",
    }


def build_eval_runner(request: Any) -> PreparedCandidate:
    """Harness entry point for m1-c and m1-d (re-exported by phi_qlora / qwen_qlora)."""

    config = request.config.model_dump()
    return PreparedCandidate(request, Generator(config, request.seed).predict)
