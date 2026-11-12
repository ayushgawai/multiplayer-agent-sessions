"""CPU-only runner and evaluator used to test orchestration, never model quality."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from eval.contracts.m1 import M1Event, M1Input
from eval.run_contract import (
    EvaluationSummary,
    M1CandidateConfig,
    M1EvaluationExample,
    PredictionRecord,
    PreparedCandidate,
    RunnerRequest,
)


class FakePreparedCandidate:
    dataset_version = "fake-dataset-v1"
    hardware = "cpu-test-double"

    def __init__(self, request: RunnerRequest) -> None:
        self._candidate_id = request.config.candidate_id
        self.examples: Sequence[M1EvaluationExample] = [
            M1EvaluationExample(
                model_input=M1Input(
                    example_id="example-1",
                    session_id="session-1",
                    query="What changed?",
                    events=[
                        M1Event(
                            event_id="event-1",
                            sequence=1,
                            event_type="result",
                            actor_id="agent-1",
                            text="The evaluation passed.",
                        )
                    ],
                ),
                reference={"completed": ["The evaluation passed."]},
            )
        ]

    def predict(self, model_input: M1Input) -> Mapping[str, Any]:
        return {
            "schema_version": "m1-output-v1",
            "example_id": model_input.example_id,
            "candidate_id": self._candidate_id,
            "completed": [
                {"text": "The evaluation passed.", "source_event_ids": ["event-1"]}
            ],
            "in_progress": [],
            "blocked": [],
            "decisions": [],
            "pending_actions": [],
        }

    def peak_vram_mb(self) -> float:
        return 0.0

    def close(self) -> None:
        return None


def build_eval_runner(request: RunnerRequest) -> PreparedCandidate:
    return FakePreparedCandidate(request)


def evaluate(
    examples: Sequence[M1EvaluationExample],
    predictions: Sequence[PredictionRecord],
    config: M1CandidateConfig,
    seed: int,
) -> EvaluationSummary:
    del examples, predictions, config, seed
    return EvaluationSummary(
        metrics={
            "critical_fact_recall": 1.0,
            "unsupported_claim_rate": 0.0,
            "attribution_accuracy": 1.0,
            "status_consistency": 1.0,
            "rouge_l": 100.0,
            "bertscore_f1": 1.0,
            "human_edit_rate": 0.0,
        },
        failures={},
    )
