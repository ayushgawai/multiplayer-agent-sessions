"""Hand-calculated checks for binary multilabel classification metrics."""

from __future__ import annotations

import json

import pytest

from eval.metrics.classification import compute_multilabel_metrics

LABELS = ("1.1", "1.2", "1.3")


def test_perfect_predictions() -> None:
    truth = [[1, 0, 1], [0, 1, 0]]

    result = compute_multilabel_metrics(truth, truth, label_names=LABELS)

    assert result["accuracy"] == 1.0
    assert result["exact_match_accuracy"] == 1.0
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0
    assert result["cohen_kappa"] == 1.0
    assert result["confusion"] == {
        "true_negative": 3,
        "false_positive": 0,
        "false_negative": 0,
        "true_positive": 3,
    }
    assert result["warnings"] == []


def test_partially_correct_predictions_match_hand_calculation() -> None:
    truth = [[1, 0, 1], [0, 1, 0]]
    predictions = [[1, 1, 0], [0, 1, 0]]

    result = compute_multilabel_metrics(truth, predictions, label_names=LABELS)

    assert result["accuracy"] == pytest.approx(2 / 3)
    assert result["exact_match_accuracy"] == pytest.approx(1 / 2)
    assert result["precision"] == pytest.approx(2 / 3)
    assert result["recall"] == pytest.approx(2 / 3)
    assert result["f1"] == pytest.approx(2 / 3)
    assert result["cohen_kappa"] == pytest.approx(1 / 3)
    assert result["averages"]["micro"] == {
        "precision": pytest.approx(2 / 3),
        "recall": pytest.approx(2 / 3),
        "f1": pytest.approx(2 / 3),
    }
    assert result["averages"]["macro"] == {
        "precision": pytest.approx(1 / 2),
        "recall": pytest.approx(2 / 3),
        "f1": pytest.approx(5 / 9),
    }
    assert result["averages"]["weighted"] == result["averages"]["macro"]
    assert result["confusion"] == {
        "true_negative": 2,
        "false_positive": 1,
        "false_negative": 1,
        "true_positive": 2,
    }
    assert result["per_label"]["1.2"] == {
        "accuracy": pytest.approx(1 / 2),
        "precision": pytest.approx(1 / 2),
        "recall": 1.0,
        "f1": pytest.approx(2 / 3),
        "support": 1,
        "predicted_positive": 2,
    }
    assert result["convention"] == "mast_binary_label_cells_v1"
    assert result["n_samples"] == 2
    assert result["n_labels"] == 3
    assert result["n_label_decisions"] == 6
    json.dumps(result, allow_nan=False)


def test_imbalanced_predictions_and_zero_support_labels() -> None:
    truth = [[1, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]
    predictions = [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]

    result = compute_multilabel_metrics(truth, predictions, label_names=LABELS)

    assert result["accuracy"] == pytest.approx(11 / 12)
    assert result["exact_match_accuracy"] == pytest.approx(3 / 4)
    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["f1"] == 0.0
    assert result["cohen_kappa"] == 0.0
    assert result["per_label"]["1.2"] == {
        "accuracy": 1.0,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": 0,
        "predicted_positive": 0,
    }


def test_single_class_kappa_is_explicitly_undefined() -> None:
    truth = [[0, 0, 0], [0, 0, 0]]

    result = compute_multilabel_metrics(truth, truth, label_names=LABELS)

    assert result["cohen_kappa"] is None
    assert result["warnings"] == ["cohen_kappa_undefined_single_class"]


def test_single_all_negative_label_keeps_primary_and_micro_scores_consistent() -> None:
    result = compute_multilabel_metrics([[0]], [[0]], label_names=("1.1",))

    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["f1"] == 0.0
    assert result["averages"]["micro"] == {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
    }


@pytest.mark.parametrize(
    ("truth", "predictions", "labels", "message"),
    [
        ([[1, 0]], [[1], [0]], ("1.1", "1.2"), "identical shapes"),
        ([[1, 2]], [[1, 0]], ("1.1", "1.2"), "binary values"),
        ([1, 0], [1, 0], ("1.1", "1.2"), "two-dimensional"),
        ([[1, 0]], [[1, 0]], ("1.1",), "expected 2"),
        ([[1, 0]], [[1, 0]], ("1.1", "1.1"), "unique"),
    ],
)
def test_invalid_inputs_are_rejected(
    truth: list[object],
    predictions: list[object],
    labels: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        compute_multilabel_metrics(truth, predictions, label_names=labels)
