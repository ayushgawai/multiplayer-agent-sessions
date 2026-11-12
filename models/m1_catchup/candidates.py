"""Shared, framework-light pieces for the learned M1 candidates m1-b, m1-c and m1-d.

Everything above the "Training" section is plain Python so it can be unit-tested on CPU
without torch. Heavy imports live inside functions.

Supervision honesty (read before using any result):

* Training data is QMSum (``data/splits/m1_v1``), adapted to ordered events by
  ``eval.contracts.m1.qmsum_row_to_m1_input``.
* QMSum has no status categories and no claim-level evidence labels. Two weak rules below
  fill that gap for training only. They are not human labels and must never be reported as
  evidence annotations:

  - ``weak_relevance_labels`` (m1-b): an event is positive when it is one of the
    ``WEAK_TOP_K`` events containing the most distinct reference-summary content words,
    with at least ``WEAK_MIN_OVERLAP`` such words.
  - ``weak_target`` (m1-c, m1-d): each reference-summary sentence becomes one claim under
    ``completed`` (QMSum gives no basis for any other category), citing the single event
    that shares the most content words with that sentence.

* Product-quality evaluation needs the annotated ``m1_session_v1`` split, which does not
  exist yet. Anything trained here is feasibility evidence, not a candidate result.

CLI (run from the repository root)::

    python -m models.m1_catchup.candidates train --candidate m1-c --seed 13 \
        --max-steps 15 --max-train-examples 128 [--max-seq-len 2048] [--resume]
    python -m models.m1_catchup.candidates smoke --candidate m1-c --seed 13 \
        --max-steps 30 --max-train-examples 128 --predict-examples 10 --out smoke-m1-c.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import yaml

from eval.contracts.m1 import (
    M1_CATEGORIES,
    M1Event,
    M1Input,
    M1Output,
    qmsum_row_to_m1_input,
    validate_m1_pair,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "eval" / "configs"
LEARNED_CANDIDATES = ("m1-b", "m1-c", "m1-d")
OUTPUT_VERSION = "m1-output-v1"

WEAK_TOP_K = 3
WEAK_MIN_OVERLAP = 2
WEAK_TARGET_CATEGORY = "completed"

_TOKEN_RE = re.compile(r"[^\W_]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_STOPWORDS = frozenset(
    "a an and are as at be been but by can could did do does for from had has have he her "
    "his how i if in into is it its me my not of on or our she so some that the their them "
    "then there they this to was we were what when which who why will with would you your".split()
)


# ---------------------------------------------------------------------------
# Config and data
# ---------------------------------------------------------------------------


def load_config(candidate_id: str) -> dict[str, Any]:
    """Load a frozen candidate config. Overrides are passed as arguments, never written back."""

    if candidate_id not in LEARNED_CANDIDATES:
        raise ValueError(f"not a learned M1 candidate: {candidate_id}")
    config = yaml.safe_load((CONFIG_DIR / f"{candidate_id}.yaml").read_text(encoding="utf-8"))
    if config.get("candidate_id") != candidate_id:
        raise ValueError(f"config identity mismatch for {candidate_id}")
    return config


def load_qmsum(split_dir: Path, split_name: str) -> list[dict[str, Any]]:
    path = split_dir / f"{split_name}.jsonl"
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def checkpoint_uri(config: dict[str, Any], seed: int) -> str:
    return config["train"]["checkpoint_uri"].rstrip("/") + f"/seed-{seed}/"


# ---------------------------------------------------------------------------
# Weak supervision rules (training only, never human labels)
# ---------------------------------------------------------------------------


def content_words(text: str) -> set[str]:
    return {word for word in _TOKEN_RE.findall(text.lower()) if word not in _STOPWORDS}


def weak_relevance_labels(event_texts: Sequence[str], reference: str) -> list[int]:
    """Weak 0/1 relevance per event from lexical overlap with the reference summary."""

    ref = content_words(reference)
    overlap = [len(content_words(text) & ref) for text in event_texts]
    # ponytail: favors long spans; switch to a length-normalized score if m1-b over-selects them.
    ranked = sorted(range(len(overlap)), key=lambda i: (-overlap[i], i))[:WEAK_TOP_K]
    keep = {i for i in ranked if overlap[i] >= WEAK_MIN_OVERLAP}
    return [int(i in keep) for i in range(len(overlap))]


def reference_sentences(reference: str) -> list[str]:
    seen: set[str] = set()
    sentences = []
    for sentence in _SENTENCE_RE.split(reference.strip()):
        text = " ".join(sentence.split())
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            sentences.append(text)
    return sentences


def weak_target(events: Sequence[M1Event], reference: str) -> dict[str, list[dict[str, Any]]]:
    """Weak structured target: reference sentences under one category, best-overlap evidence."""

    words = [content_words(event.text) for event in events]
    claims = []
    for sentence in reference_sentences(reference):
        target = content_words(sentence)
        best = max(range(len(events)), key=lambda i: (len(words[i] & target), -i))
        claims.append({"text": sentence, "source_event_ids": [events[best].event_id]})
    target_json = {category: [] for category in M1_CATEGORIES}
    target_json[WEAK_TARGET_CATEGORY] = claims
    return target_json


# ---------------------------------------------------------------------------
# Generative prompt, target, and output parsing (m1-c, m1-d)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You write a catch-up for someone joining a shared work session. Answer the query using "
    "only the listed events. Reply with one JSON object and nothing else. It has exactly the "
    "keys completed, in_progress, blocked, decisions, pending_actions. Each value is a list of "
    'claims like {"text": "...", "source_event_ids": ["<event id>"]}, where every claim cites '
    "the ids of the events that support it."
)


def event_line(event: M1Event) -> str:
    return f"[{event.event_id}] {' '.join(event.text.split())}"


def user_prompt(query: str, events: Sequence[M1Event]) -> str:
    return f"Query: {query}\n\nEvents:\n" + "\n".join(event_line(event) for event in events)


def fit_events(
    events: Sequence[M1Event], count_tokens: Callable[[str], int], budget: int
) -> list[M1Event]:
    """Longest event prefix whose rendered lines fit the token budget (at least one event)."""

    kept: list[M1Event] = []
    used = 0
    for event in events:
        used += count_tokens(event_line(event)) + 1
        if kept and used > budget:
            break
        kept.append(event)
    return kept


def target_text(target: dict[str, Any]) -> str:
    return json.dumps(target, ensure_ascii=False, separators=(",", ":"))


def parse_generation(text: str, example_id: str, candidate_id: str) -> dict[str, Any]:
    """Turn generated text into an m1-output-v1 dict; unparseable text stays visibly invalid."""

    body = text.split("</think>")[-1]
    start = body.find("{")
    try:
        if start < 0:
            raise ValueError("no JSON object")
        obj, _ = json.JSONDecoder().raw_decode(body, start)
        if not isinstance(obj, dict):
            raise ValueError("JSON is not an object")
    except ValueError:
        return {"_raw_text": text}
    return {
        "schema_version": OUTPUT_VERSION,
        "example_id": example_id,
        "candidate_id": candidate_id,
        **{category: obj.get(category, []) for category in M1_CATEGORIES},
    }


def validation_error(output: dict[str, Any], model_input: M1Input) -> str | None:
    """Same checks the shared harness applies; None means valid m1-output-v1."""

    try:
        validate_m1_pair(model_input, M1Output.model_validate(output))
    except ValueError as exc:
        return str(exc)
    return None


# ---------------------------------------------------------------------------
# Runner plumbing for the shared harness (eval.run_contract, PR #25)
# ---------------------------------------------------------------------------


def eval_examples(request: Any) -> tuple[str, list[Any]]:
    """Return (dataset_version, M1EvaluationExample list) for a harness RunnerRequest."""

    from eval.run_contract import M1EvaluationExample

    if request.split == "smoke":
        # Reuse M1-A's smoke-fixture adapter instead of a second copy of it.
        from models.m1_catchup.bm25 import build_eval_runner as bm25_runner

        prepared = bm25_runner(request)
        return prepared.dataset_version, list(prepared.examples)
    if request.split != "qmsum_test":
        raise NotImplementedError(
            f"split {request.split!r} has no adapter: the annotated m1_session_v1 split does "
            "not exist yet"
        )
    manifest = (Path(request.dataset_path) / "MANIFEST.json").read_bytes()
    version = "m1_v1:" + hashlib.sha256(manifest).hexdigest()[:12]
    rows = load_qmsum(Path(request.dataset_path), "test")[: request.max_examples]
    examples = [
        M1EvaluationExample(
            model_input=qmsum_row_to_m1_input(row),
            reference={"reference_summary": row["reference_summary"]},
        )
        for row in rows
    ]
    return version, examples


class PreparedCandidate:
    """Harness-facing wrapper around a loaded candidate's predict function."""

    def __init__(self, request: Any, predict: Callable[[M1Input], dict[str, Any]]) -> None:
        self.dataset_version, self.examples = eval_examples(request)
        self.hardware = hardware_name()
        self._predict = predict

    def predict(self, model_input: M1Input) -> dict[str, Any]:
        return self._predict(model_input)

    def peak_vram_mb(self) -> float:
        import torch

        if not torch.cuda.is_available():
            return 0.0
        return torch.cuda.max_memory_allocated() / 2**20

    def close(self) -> None:
        import torch

        self._predict = None  # type: ignore[assignment]
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def hardware_name() -> str:
    import torch

    return torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"


# ---------------------------------------------------------------------------
# Training (shared HF Trainer loop with save/resume through models.common.checkpointing)
# ---------------------------------------------------------------------------


def run_trainer(
    *,
    model: Any,
    dataset: Sequence[dict[str, Any]],
    collator: Any,
    config: dict[str, Any],
    seed: int,
    per_device_batch: int,
    max_steps: int | None,
    resume: bool,
    optim: str,
    gradient_checkpointing: bool,
) -> dict[str, Any]:
    """Train with the frozen config, mirroring every save to checkpoint_uri via the shared helper."""

    import torch
    from transformers import Trainer, TrainerCallback, TrainingArguments

    from models.common.checkpointing import _local_path, resume_from_checkpoint, save_checkpoint

    train_cfg = config["train"]
    uri = checkpoint_uri(config, seed)
    work_dir = _local_path(uri) / "_work"
    meta = {
        "candidate_id": config["candidate_id"],
        "model_repo": config["model"]["repo"],
        "model_revision": config["model"]["revision"],
        "seed": seed,
    }

    class MirrorCheckpoint(TrainerCallback):
        def on_save(self, args, state, control, **kwargs):  # noqa: ANN001
            src = Path(args.output_dir) / f"checkpoint-{state.global_step}"
            save_checkpoint(src, uri, state.global_step, meta)

    save_steps = int(train_cfg["save_steps"])
    if max_steps is not None:
        save_steps = min(save_steps, max_steps)
    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    args = TrainingArguments(
        output_dir=str(work_dir),
        num_train_epochs=int(train_cfg["epochs"]),
        max_steps=max_steps if max_steps is not None else -1,
        per_device_train_batch_size=per_device_batch,
        gradient_accumulation_steps=max(1, int(train_cfg["effective_batch_size"]) // per_device_batch),
        learning_rate=float(train_cfg["lr"]),
        # transformers 5.x dropped warmup_ratio; a warmup_steps value below 1 is read as a ratio
        warmup_steps=float(train_cfg["warmup_ratio"]),
        lr_scheduler_type="cosine",
        logging_steps=1 if max_steps is not None else 10,
        save_strategy="steps",
        save_steps=save_steps,
        save_total_limit=2,
        optim=optim,
        bf16=bf16,
        fp16=torch.cuda.is_available() and not bf16,
        gradient_checkpointing=gradient_checkpointing,
        remove_unused_columns=False,
        dataloader_num_workers=0,
        report_to=[],
        seed=seed,
        data_seed=seed,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
        data_collator=collator,
        callbacks=[MirrorCheckpoint()],
    )
    resume_dir = resume_from_checkpoint(uri) if resume else None
    if resume and resume_dir is None:
        raise FileNotFoundError(f"--resume given but no checkpoint under {uri}")
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    result = trainer.train(resume_from_checkpoint=str(resume_dir) if resume_dir else None)
    losses = [row["loss"] for row in trainer.state.log_history if "loss" in row]
    return {
        "resumed_from": resume_dir.as_posix() if resume_dir else None,
        "global_step": trainer.state.global_step,
        "loss_first": losses[0] if losses else None,
        "loss_last": losses[-1] if losses else None,
        "train_runtime_s": round(time.perf_counter() - started, 1),
        "train_samples_per_second": result.metrics.get("train_samples_per_second"),
        "peak_vram_mb": round(torch.cuda.max_memory_allocated() / 2**20, 1)
        if torch.cuda.is_available()
        else 0.0,
        "latest_checkpoint": resume_from_checkpoint(uri).as_posix(),
    }


def _module(candidate_id: str) -> Any:
    if candidate_id == "m1-b":
        from models.m1_catchup import modernbert

        return modernbert
    from models.m1_catchup import qlora

    return qlora


def smoke(args: argparse.Namespace) -> dict[str, Any]:
    """Feasibility smoke: train half, resume to full, predict on validation. Not a metric run."""

    config = load_config(args.candidate)
    module = _module(args.candidate)
    common = dict(
        config=config,
        seed=args.seed,
        max_train_examples=args.max_train_examples,
        max_seq_len=args.max_seq_len,
    )
    first = module.train(**common, max_steps=args.max_steps // 2, resume=False)
    second = module.train(**common, max_steps=args.max_steps, resume=True)
    inference = module.predict_validation(
        config, args.seed, n=args.predict_examples, max_seq_len=args.max_seq_len
    )
    return {"first_run": first, "resumed_run": second, "inference": inference}


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["train", "smoke"])
    parser.add_argument("--candidate", choices=LEARNED_CANDIDATES, required=True)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--max-train-examples", type=int)
    parser.add_argument("--max-seq-len", type=int, help="smoke override; frozen value is 4096")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--predict-examples", type=int, default=10)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    config = load_config(args.candidate)
    if args.seed not in config["seeds"]:
        parser.error(f"seed {args.seed} is not one of the frozen seeds {config['seeds']}")
    if args.command == "train":
        result = _module(args.candidate).train(
            config=config,
            seed=args.seed,
            max_steps=args.max_steps,
            max_train_examples=args.max_train_examples,
            max_seq_len=args.max_seq_len,
            resume=args.resume,
        )
    else:
        if args.max_steps is None:
            parser.error("smoke requires --max-steps")
        result = smoke(args)
    text = json.dumps(result, indent=2, default=str)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
