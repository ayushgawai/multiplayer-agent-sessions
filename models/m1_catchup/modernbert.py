"""M1-B: ModernBERT-base extractive event selector plus M1-A's fixed structured template.

A cross-encoder scores each (query, event) pair for relevance. The scores replace BM25 in
M1-A's template (``models.m1_catchup.bm25``, PR #26): the same keyword status rules pick each
event's category, the top events per category become extractive claims citing that event.

Training labels come from ``candidates.weak_relevance_labels``: lexical overlap with the QMSum
reference summary. They are training-only weak supervision, never human evidence labels.
``max_seq_len`` caps each (query, event) pair; the selector sees every event of a session.
"""

from __future__ import annotations

import statistics
import time
from typing import Any

from eval.contracts.m1 import M1_CATEGORIES, M1Input, qmsum_row_to_m1_input
from models.m1_catchup.candidates import (
    OUTPUT_VERSION,
    REPO_ROOT,
    PreparedCandidate,
    checkpoint_uri,
    load_qmsum,
    run_trainer,
    validation_error,
    weak_relevance_labels,
)

CANDIDATE_ID = "m1-b"
SCORE_BATCH = 64


def fill_template(model_input: M1Input, scores: list[float]) -> dict[str, Any]:
    """M1-A's template with learned scores: mirrors ``bm25.predict`` minus the BM25 ranking."""

    from models.m1_catchup import bm25

    events = model_input.events
    texts = [bm25.truncate_at_word(bm25.collapse_whitespace(event.text)) for event in events]
    candidates: dict[str, list[int]] = {category: [] for category in M1_CATEGORIES}
    for position, event in enumerate(events):
        category = bm25.classify_event(event)
        if category is not None:
            candidates[category].append(position)
    seen: set[str] = set()
    selected: dict[str, list[int]] = {category: [] for category in M1_CATEGORIES}
    for rule in bm25.CATEGORY_RULES:
        ranked = sorted(
            candidates[rule.category], key=lambda p: (-scores[p], -events[p].sequence)
        )
        for position in ranked:
            if len(selected[rule.category]) == bm25.MAX_CLAIMS_PER_CATEGORY:
                break
            key = bm25.normalize_claim_text(texts[position])
            if key not in seen:
                seen.add(key)
                selected[rule.category].append(position)
    output: dict[str, Any] = {
        "schema_version": OUTPUT_VERSION,
        "example_id": model_input.example_id,
        "candidate_id": CANDIDATE_ID,
    }
    for category in M1_CATEGORIES:
        output[category] = [
            {"text": texts[p], "source_event_ids": [events[p].event_id]}
            for p in sorted(selected[category], key=lambda p: events[p].sequence)
        ]
    return output


def _tokenizer(config: dict[str, Any]) -> Any:
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(config["model"]["repo"], revision=config["model"]["revision"])


def train(
    *,
    config: dict[str, Any],
    seed: int,
    max_steps: int | None = None,
    max_train_examples: int | None = None,
    max_seq_len: int | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    from transformers import AutoModelForSequenceClassification, DataCollatorWithPadding, set_seed

    set_seed(seed)
    max_len = max_seq_len or int(config["train"]["max_seq_len"])
    tokenizer = _tokenizer(config)
    rows = load_qmsum(REPO_ROOT / config["split"], "train")[:max_train_examples]
    pairs = []
    for row in rows:
        model_input = qmsum_row_to_m1_input(row)
        labels = weak_relevance_labels(
            [event.text for event in model_input.events], row["reference_summary"]
        )
        for event, label in zip(model_input.events, labels, strict=True):
            encoded = tokenizer(
                model_input.query, event.text, truncation="only_second", max_length=max_len
            )
            pairs.append({**encoded, "labels": label})
    model = AutoModelForSequenceClassification.from_pretrained(
        config["model"]["repo"], revision=config["model"]["revision"], num_labels=2
    )
    stats = run_trainer(
        model=model,
        dataset=pairs,
        collator=DataCollatorWithPadding(tokenizer),
        config=config,
        seed=seed,
        per_device_batch=int(config["train"]["effective_batch_size"]),
        max_steps=max_steps,
        resume=resume,
        optim="adamw_torch",
        gradient_checkpointing=False,
    )
    positives = sum(pair["labels"] for pair in pairs)
    return {
        **stats,
        "max_seq_len": max_len,
        "train_rows": len(rows),
        "train_pairs": len(pairs),
        "weak_positive_pairs": positives,
    }


class Selector:
    """Loaded m1-b checkpoint: scores events and fills the template."""

    def __init__(self, config: dict[str, Any], seed: int, max_seq_len: int | None = None) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification

        from models.common.checkpointing import resume_from_checkpoint

        step_dir = resume_from_checkpoint(checkpoint_uri(config, seed))
        if step_dir is None:
            raise FileNotFoundError(f"no trained m1-b checkpoint for seed {seed}")
        self.step_dir = step_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = _tokenizer(config)
        self.model = AutoModelForSequenceClassification.from_pretrained(step_dir).to(self.device)
        self.model.eval()
        self.max_len = max_seq_len or int(config["train"]["max_seq_len"])

    def scores(self, model_input: M1Input) -> list[float]:
        import torch

        texts = [event.text for event in model_input.events]
        scores: list[float] = []
        for start in range(0, len(texts), SCORE_BATCH):
            batch = texts[start : start + SCORE_BATCH]
            encoded = self.tokenizer(
                [model_input.query] * len(batch),
                batch,
                truncation="only_second",
                max_length=self.max_len,
                padding=True,
                return_tensors="pt",
            ).to(self.device)
            with torch.no_grad(), torch.autocast(self.device, enabled=self.device == "cuda"):
                logits = self.model(**encoded).logits.float()
            scores.extend(logits.softmax(-1)[:, 1].tolist())
        return scores

    def predict(self, model_input: M1Input) -> dict[str, Any]:
        return fill_template(model_input, self.scores(model_input))


def predict_validation(
    config: dict[str, Any], seed: int, *, n: int, max_seq_len: int | None = None
) -> dict[str, Any]:
    """Feasibility inference on the first n validation rows (never test)."""

    import torch

    selector = Selector(config, seed, max_seq_len)
    rows = load_qmsum(REPO_ROOT / config["split"], "val")[:n]
    torch.cuda.reset_peak_memory_stats()
    latencies, errors = [], []
    for row in rows:
        model_input = qmsum_row_to_m1_input(row)
        started = time.perf_counter()
        output = selector.predict(model_input)
        latencies.append((time.perf_counter() - started) * 1000)
        errors.append(validation_error(output, model_input))
    return {
        "checkpoint": selector.step_dir.as_posix(),
        "examples": len(rows),
        "valid_m1_output_v1": sum(error is None for error in errors),
        "errors": [error for error in errors if error][:3],
        "latency_ms_mean": round(statistics.fmean(latencies), 1),
        "latency_ms_median": round(statistics.median(latencies), 1),
        "events_scored": sum(len(row["context_spans"]) for row in rows),
        "peak_vram_mb": round(torch.cuda.max_memory_allocated() / 2**20, 1),
    }


def build_eval_runner(request: Any) -> PreparedCandidate:
    """Harness entry point (``eval.harness.DEFAULT_RUNNERS['m1-b']``)."""

    config = request.config.model_dump()
    return PreparedCandidate(request, Selector(config, request.seed).predict)
