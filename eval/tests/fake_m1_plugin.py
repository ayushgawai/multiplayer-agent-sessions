"""CPU-only runner and evaluator used to test orchestration, never model quality."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from data.m1_smoke.loader import gold_reference, load_fixtures, to_m1_input, verify_manifest
from eval.contracts.m1 import M1Event, M1Input
from eval.run_contract import (
    CriticalFact,
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
                            event_type="tool_result",
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


class SmokeFixturePreparedCandidate:
    dataset_version = "m1-smoke-v1"
    hardware = "cpu-smoke-fixture"

    def __init__(self, request: RunnerRequest) -> None:
        verify_manifest(request.dataset_path)
        fixtures = load_fixtures(request.dataset_path)
        source_examples = [
            example
            for split in ("train", "dev", "smoke_holdout")
            for example in fixtures[split]
        ]
        self._candidate_id = request.config.candidate_id
        self._references = {
            example.example_id: gold_reference(example) for example in source_examples
        }
        self.examples: Sequence[M1EvaluationExample] = [
            M1EvaluationExample(
                model_input=M1Input.model_validate(to_m1_input(example)),
                reference=gold_reference(example),
                critical_facts=[
                    CriticalFact.model_validate(fact.model_dump())
                    for fact in example.critical_facts
                ],
                metadata={"smoke_fixture": True},
            )
            for example in source_examples
        ]

    def predict(self, model_input: M1Input) -> Mapping[str, Any]:
        return {
            **self._references[model_input.example_id],
            "candidate_id": self._candidate_id,
        }

    def peak_vram_mb(self) -> float:
        return 0.0

    def close(self) -> None:
        return None


def build_smoke_fixture_runner(request: RunnerRequest) -> PreparedCandidate:
    return SmokeFixturePreparedCandidate(request)


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
