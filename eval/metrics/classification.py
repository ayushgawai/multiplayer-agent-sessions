"""Classification metrics for binary multilabel predictions.

MAST assigns fourteen independent yes/no failure-mode labels to every trace. Our
provisional project convention treats every trace-label cell as one binary
decision. This convention must be validated against the released human labels
before it is described as reproducing the paper. Additional exact-match, macro,
weighted, and per-label values make the convention explicit instead of relying
on scikit-learn defaults.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix
from sklearn.metrics import precision_recall_fscore_support

METRIC_CONVENTION = "mast_binary_label_cells_v1"


def _validated_binary_matrix(values: ArrayLike, *, name: str) -> NDArray[np.int_]:
    """Return a two-dimensional integer matrix containing only zero and one."""

    try:
        matrix = np.asarray(values)
    except ValueError as exc:
        raise ValueError(f"{name} must be a rectangular two-dimensional matrix") from exc

    if matrix.ndim != 2:
        raise ValueError(f"{name} must be two-dimensional; received shape {matrix.shape}")
    if matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError(f"{name} must contain at least one sample and one label")
    if not np.isin(matrix, (0, 1)).all():
        raise ValueError(f"{name} must contain only binary values 0 and 1")

    return matrix.astype(int, copy=False)


def _validated_label_names(label_names: Sequence[str], *, expected: int) -> tuple[str, ...]:
    labels = tuple(label_names)
    if len(labels) != expected:
        raise ValueError(f"label_names has {len(labels)} entries; expected {expected}")
    if any(not isinstance(label, str) or not label.strip() for label in labels):
        raise ValueError("label_names must contain non-empty strings")
    if len(set(labels)) != len(labels):
        raise ValueError("label_names must be unique")
    return labels


def _averaged_scores(
    y_true: NDArray[np.int_],
    y_pred: NDArray[np.int_],
    *,
    average: str,
) -> dict[str, float]:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average=average,
        zero_division=0,
    )
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def compute_multilabel_metrics(
    y_true: ArrayLike,
    y_pred: ArrayLike,
    *,
    label_names: Sequence[str],
) -> dict[str, Any]:
    """Compute project-convention and diagnostic metrics for binary labels.

    The primary ``accuracy``, ``precision``, ``recall``, ``f1``, and
    ``cohen_kappa`` values operate on the flattened trace-label matrix. This is
    equivalent to micro aggregation for the positive-class precision, recall,
    and F1 values. ``exact_match_accuracy`` is stricter: a trace is correct only
    when every label matches.

    Undefined Cohen's Kappa, which occurs when both inputs contain one identical
    class, is emitted as ``None`` with a warning. Precision, recall, and F1 use
    ``zero_division=0`` throughout.
    """

    truth = _validated_binary_matrix(y_true, name="y_true")
    predictions = _validated_binary_matrix(y_pred, name="y_pred")
    if truth.shape != predictions.shape:
        raise ValueError(
            "y_true and y_pred must have identical shapes; "
            f"received {truth.shape} and {predictions.shape}"
        )

    labels = _validated_label_names(label_names, expected=truth.shape[1])
    flat_truth = truth.ravel()
    flat_predictions = predictions.ravel()

    precision, recall, f1, _ = precision_recall_fscore_support(
        flat_truth,
        flat_predictions,
        average="binary",
        pos_label=1,
        zero_division=0,
    )
    micro_scores = {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }
    tn, fp, fn, tp = confusion_matrix(
        flat_truth,
        flat_predictions,
        labels=[0, 1],
    ).ravel()

    warnings: list[str] = []
    if np.array_equal(flat_truth, flat_predictions) and np.unique(flat_truth).size == 1:
        kappa: float | None = None
        warnings.append("cohen_kappa_undefined_single_class")
    else:
        raw_kappa = cohen_kappa_score(flat_truth, flat_predictions, labels=[0, 1])
        kappa = None if np.isnan(raw_kappa) else float(raw_kappa)
        if kappa is None:
            warnings.append("cohen_kappa_undefined")

    per_label_precision, per_label_recall, per_label_f1, per_label_support = (
        precision_recall_fscore_support(
            truth,
            predictions,
            average=None,
            zero_division=0,
        )
    )
    per_label: dict[str, dict[str, float | int]] = {}
    for index, label in enumerate(labels):
        per_label[label] = {
            "accuracy": float(accuracy_score(truth[:, index], predictions[:, index])),
            "precision": float(per_label_precision[index]),
            "recall": float(per_label_recall[index]),
            "f1": float(per_label_f1[index]),
            "support": int(per_label_support[index]),
            "predicted_positive": int(predictions[:, index].sum()),
        }

    return {
        "convention": METRIC_CONVENTION,
        "n_samples": int(truth.shape[0]),
        "n_labels": int(truth.shape[1]),
        "n_label_decisions": int(truth.size),
        "accuracy": float(accuracy_score(flat_truth, flat_predictions)),
        "exact_match_accuracy": float(accuracy_score(truth, predictions)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "cohen_kappa": kappa,
        "averages": {
            "micro": micro_scores,
            "macro": _averaged_scores(truth, predictions, average="macro"),
            "weighted": _averaged_scores(truth, predictions, average="weighted"),
        },
        "confusion": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
        "per_label": per_label,
        "warnings": warnings,
    }
