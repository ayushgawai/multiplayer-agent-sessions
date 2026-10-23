"""Contract tests for the shared M1 ROUGE implementation."""

from __future__ import annotations

import json

import pytest

from eval.metrics.summarization import compute_rouge_metrics


def test_exact_match_returns_one_hundred_on_locked_scale() -> None:
    result = compute_rouge_metrics(["the blocker is resolved"], ["the blocker is resolved"])

    assert result["rouge_1"] == 100.0
    assert result["rouge_2"] == 100.0
    assert result["rouge_l"] == 100.0
    assert result["convention"] == "m1_rouge_macro_v1"
    assert result["library"] == "rouge-score"
    assert result["library_version"] == "0.1.2"
    assert result["n_samples"] == 1
    assert result["scale"] == "percentage_0_100"
    assert result["use_stemmer"] is True
    json.dumps(result, allow_nan=False)


def test_partial_overlap_matches_hand_calculation() -> None:
    result = compute_rouge_metrics(["alpha beta"], ["alpha beta gamma"])

    assert result["details"]["rouge_1"] == {
        "precision": 100.0,
        "recall": pytest.approx(200 / 3),
        "f1": 80.0,
    }
    assert result["details"]["rouge_2"] == {
        "precision": 100.0,
        "recall": 50.0,
        "f1": pytest.approx(200 / 3),
    }
    assert result["details"]["rouge_l"] == result["details"]["rouge_1"]
    assert result["rouge_l"] == 80.0


def test_scores_are_macro_averaged_per_record() -> None:
    result = compute_rouge_metrics(
        ["alpha beta", "unrelated words"],
        ["alpha beta", "gamma delta"],
    )

    assert result["rouge_1"] == 50.0
    assert result["rouge_2"] == 50.0
    assert result["rouge_l"] == 50.0
    assert result["per_sample"][0]["rouge_l"]["f1"] == 100.0
    assert result["per_sample"][1]["rouge_l"]["f1"] == 0.0


def test_porter_stemming_is_enabled() -> None:
    result = compute_rouge_metrics(["running"], ["run"])

    assert result["rouge_1"] == 100.0
    assert result["rouge_l"] == 100.0


def test_empty_prediction_is_a_valid_zero_score() -> None:
    result = compute_rouge_metrics([""], ["a required fact"])

    assert result["rouge_1"] == 0.0
    assert result["rouge_2"] == 0.0
    assert result["rouge_l"] == 0.0


@pytest.mark.parametrize(
    ("predictions", "references", "message"),
    [
        ([], [], "at least one summary"),
        (["one"], ["one", "two"], "identical lengths"),
        ("one", ["one"], "not one string"),
        (["one", 2], ["one", "two"], r"predictions\[1\] must be a string"),
        (["one"], [" \n\t"], r"references\[0\] must not be blank"),
    ],
)
def test_invalid_inputs_are_rejected(
    predictions: object,
    references: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        compute_rouge_metrics(predictions, references)  # type: ignore[arg-type]
