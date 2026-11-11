"""Deterministic ROUGE metrics for M1 catch-up summaries.

The M1 candidate configurations name ``rouge_l`` as a metric. This module
locks the exact library call, aggregation rule, and reporting scale so every
candidate is evaluated under the same convention.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib.metadata import version
from statistics import fmean
from typing import Any

from rouge_score import rouge_scorer  # type: ignore[import-untyped]

ROUGE_CONVENTION = "m1_rouge_macro_v1"
ROUGE_LIBRARY = "rouge-score"
ROUGE_LIBRARY_VERSION = version(ROUGE_LIBRARY)
ROUGE_SCALE = 100.0

_LIBRARY_KEYS = ("rouge1", "rouge2", "rougeL")
_RESULT_KEYS = {
    "rouge1": "rouge_1",
    "rouge2": "rouge_2",
    "rougeL": "rouge_l",
}


def _validated_texts(
    values: Sequence[str],
    *,
    name: str,
    allow_blank: bool,
) -> tuple[str, ...]:
    """Return validated strings without changing their scoring contents."""

    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be a sequence of strings, not one string")

    texts = tuple(values)
    if not texts:
        raise ValueError(f"{name} must contain at least one summary")

    for index, value in enumerate(texts):
        if not isinstance(value, str):
            raise ValueError(f"{name}[{index}] must be a string")
        if not allow_blank and not value.strip():
            raise ValueError(f"{name}[{index}] must not be blank")
    return texts


def _percentage(value: float) -> float:
    """Convert a rouge-score value from the unit interval to percent."""

    return float(value) * ROUGE_SCALE


def compute_rouge_metrics(
    predictions: Sequence[str],
    references: Sequence[str],
) -> dict[str, Any]:
    """Compute macro-averaged ROUGE-1, ROUGE-2, and ROUGE-L.

    ``rouge-score==0.1.2`` scores each ``(reference, prediction)`` pair with
    Porter stemming enabled. Precision, recall, and F1 are averaged across
    records, then reported on a 0--100 percentage scale without rounding.
    Empty strings are valid model outputs, but reference summaries must contain
    non-whitespace text. The two collections must be non-empty and have
    identical lengths.

    Inputs must already be projected to the canonical M1 summary text defined
    by ADR-004. This metric intentionally does not score JSON field names,
    category labels, or source-event identifiers.

    The top-level ``rouge_1``, ``rouge_2``, and ``rouge_l`` values are the
    macro F1 scores used by the evaluation harness. ``details`` and
    ``per_sample`` retain the component scores for audit and error analysis.
    """

    prediction_texts = _validated_texts(
        predictions,
        name="predictions",
        allow_blank=True,
    )
    reference_texts = _validated_texts(
        references,
        name="references",
        allow_blank=False,
    )
    if len(prediction_texts) != len(reference_texts):
        raise ValueError(
            "predictions and references must have identical lengths; "
            f"received {len(prediction_texts)} and {len(reference_texts)}"
        )

    scorer = rouge_scorer.RougeScorer(list(_LIBRARY_KEYS), use_stemmer=True)
    per_sample: list[dict[str, dict[str, float]]] = []

    for prediction, reference in zip(prediction_texts, reference_texts, strict=True):
        library_scores = scorer.score(reference, prediction)
        sample: dict[str, dict[str, float]] = {}
        for library_key in _LIBRARY_KEYS:
            score = library_scores[library_key]
            sample[_RESULT_KEYS[library_key]] = {
                "precision": _percentage(score.precision),
                "recall": _percentage(score.recall),
                "f1": _percentage(score.fmeasure),
            }
        per_sample.append(sample)

    details: dict[str, dict[str, float]] = {}
    for result_key in _RESULT_KEYS.values():
        details[result_key] = {
            component: fmean(sample[result_key][component] for sample in per_sample)
            for component in ("precision", "recall", "f1")
        }

    return {
        "convention": ROUGE_CONVENTION,
        "library": ROUGE_LIBRARY,
        "library_version": ROUGE_LIBRARY_VERSION,
        "n_samples": len(prediction_texts),
        "scale": "percentage_0_100",
        "use_stemmer": True,
        "rouge_1": details["rouge_1"]["f1"],
        "rouge_2": details["rouge_2"]["f1"],
        "rouge_l": details["rouge_l"]["f1"],
        "details": details,
        "per_sample": per_sample,
    }
