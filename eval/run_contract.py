"""Strict schemas and plugin interfaces for the shared M1 evaluation path."""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from eval.contracts.m1 import M1Input

RESULT_SCHEMA_VERSION: Literal["candidate-result-v1"] = "candidate-result-v1"
REPORTABLE_PROTOCOL: Literal["reportable"] = "reportable"
SMOKE_PROTOCOL: Literal["smoke_non_reportable"] = "smoke_non_reportable"
HARNESS_METRICS = frozenset(
    {"schema_valid_rate", "latency_p50_ms", "latency_p95_ms", "peak_vram_mb"}
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        protected_namespaces=(),
        allow_inf_nan=False,
    )


class ModelReference(_StrictModel):
    repo: str | None
    revision: str | None


class TrainingConfig(_StrictModel):
    epochs: int = Field(gt=0)
    max_seq_len: int = Field(gt=0)
    effective_batch_size: int = Field(gt=0)
    lr: float = Field(gt=0)
    warmup_ratio: float = Field(ge=0, lt=1)
    save_steps: int = Field(gt=0)
    checkpoint_uri: str


class LoraConfig(_StrictModel):
    r: int = Field(gt=0)
    alpha: int = Field(gt=0)
    dropout: float = Field(ge=0, lt=1)
    target_modules: list[str] = Field(min_length=1)


class SchemaReferences(_StrictModel):
    input: Literal["m1-input-v1"]
    output: Literal["m1-output-v1"]


class M1CandidateConfig(_StrictModel):
    """Frozen candidate configuration consumed by the harness."""

    contract: str
    task: Literal["m1_catchup"]
    candidate_id: Literal["m1-a", "m1-b", "m1-c", "m1-d"]
    label: str
    mode: Literal["classical", "finetune", "qlora", "lora", "prompt"]
    trainer: str
    model: ModelReference
    split: str
    evaluation_split: str
    schemas: SchemaReferences
    seeds: list[int] = Field(min_length=1)
    train: TrainingConfig | None
    lora: LoraConfig | None
    prompt_file: str | None
    metrics: list[str] = Field(min_length=1)
    primary_metric: str
    ablation: dict[str, list[bool | int | str]]
    failure_codes: list[str] = Field(min_length=1)

    @field_validator(
        "contract",
        "label",
        "trainer",
        "split",
        "evaluation_split",
        "primary_metric",
    )
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @model_validator(mode="after")
    def validate_candidate(self) -> Self:
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("candidate seeds must be unique")
        if len(self.metrics) != len(set(self.metrics)):
            raise ValueError("candidate metrics must be unique")
        if len(self.failure_codes) != len(set(self.failure_codes)):
            raise ValueError("candidate failure_codes must be unique")
        if self.primary_metric not in self.metrics:
            raise ValueError("primary_metric must be listed in metrics")
        if self.candidate_id == "m1-a":
            if self.mode != "classical" or self.train is not None:
                raise ValueError("m1-a must be classical and have no train config")
            if self.model.repo is not None or self.model.revision is not None:
                raise ValueError("m1-a must not define model weights")
        else:
            if self.model.repo is None or self.model.revision is None:
                raise ValueError("learned candidates require model repo and revision")
            if len(self.model.revision) != 40 or any(
                char not in "0123456789abcdef" for char in self.model.revision.lower()
            ):
                raise ValueError("model revision must be a full 40-character commit hash")
            if self.train is None:
                raise ValueError("learned candidates require a train config")
        return self


class M1SelectionGates(_StrictModel):
    all_three_seed_runs_complete: bool
    schema_valid_rate_min: float
    unsupported_claim_rate_max: float
    unsupported_claim_rate_no_worse_than_m1_a: bool
    attribution_accuracy_min: float
    status_consistency_min: float


class M1SelectionContract(_StrictModel):
    eligibility_gate_aggregation: Literal["every_seed"]
    baseline_comparison: Literal["matched_seed"]
    eligible_if: M1SelectionGates
    rank_eligible_by: list[str] = Field(min_length=1)
    rank_aggregation: Literal["mean_across_three_seeds"]
    tie_policy: Literal["retain_within_margin_of_stage_best"]
    quality_tie_margins: dict[str, float]
    tie_break_by: list[str] = Field(min_length=1)
    final_confirmation: str

    @model_validator(mode="after")
    def validate_ranking_policy(self) -> Self:
        if set(self.quality_tie_margins) != set(self.rank_eligible_by):
            raise ValueError("quality_tie_margins must match rank_eligible_by")
        if any(margin < 0 for margin in self.quality_tie_margins.values()):
            raise ValueError("quality tie margins must be non-negative")
        return self


class M1ExperimentContract(_StrictModel):
    """Subset of the frozen experiment contract enforced by orchestration."""

    contract_version: Literal["m1-experiment-v1"]
    task: Literal["m1_catchup"]
    schemas: SchemaReferences
    seeds: list[int] = Field(min_length=1)
    split: dict[str, Any]
    fairness: dict[str, Any]
    metrics: dict[str, dict[str, Any]]
    selection: M1SelectionContract

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("contract seeds must be unique")
        required_split = {
            "qmsum_path",
            "qmsum_manifest",
            "session_path",
            "grouping_key",
            "test_policy",
            "candidate_selection_split",
        }
        if set(self.split) != required_split:
            raise ValueError("contract split keys do not match the frozen schema")
        if self.fairness.get("test_feedback_may_enter_memory") is not False:
            raise ValueError("test feedback must never enter memory")
        if self.fairness.get("candidate_selection_condition") != "memory_disabled":
            raise ValueError("candidate selection must run with memory disabled")
        metric_names = set(self.metrics)
        ranked_metrics = set(self.selection.rank_eligible_by)
        tie_break_metrics = set(self.selection.tie_break_by)
        if not ranked_metrics <= metric_names:
            raise ValueError("rank_eligible_by contains an unknown metric")
        if not tie_break_metrics <= metric_names:
            raise ValueError("tie_break_by contains an unknown metric")
        return self


class CriticalFact(_StrictModel):
    fact_id: str
    category: Literal["completed", "in_progress", "blocked", "decisions", "pending_actions"]
    text: str
    evidence_event_ids: list[str] = Field(min_length=1)


class M1EvaluationExample(_StrictModel):
    """One evaluation input plus frozen gold metadata supplied by a data adapter."""

    model_input: M1Input
    reference: dict[str, Any]
    critical_facts: list[CriticalFact] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class RunnerRequest:
    config: M1CandidateConfig
    seed: int
    split: str
    dataset_path: Path
    smoke: bool
    max_examples: int | None


class PreparedCandidate(Protocol):
    """Candidate-owner boundary. The harness controls inference and timing."""

    dataset_version: str
    hardware: str
    examples: Sequence[M1EvaluationExample]

    def predict(self, model_input: M1Input) -> Mapping[str, Any]: ...

    def peak_vram_mb(self) -> float: ...

    def close(self) -> None: ...


RunnerFactory = Callable[[RunnerRequest], PreparedCandidate]


class PredictionRecord(_StrictModel):
    example_id: str
    output: dict[str, Any]
    valid: bool
    validation_error: str | None = None


class EvaluationSummary(_StrictModel):
    metrics: dict[str, float]
    failures: dict[str, int]


Evaluator = Callable[
    [Sequence[M1EvaluationExample], Sequence[PredictionRecord], M1CandidateConfig, int],
    EvaluationSummary,
]


class SeedRunResult(_StrictModel):
    seed: int
    attempted_examples: int = Field(gt=0)
    valid_outputs: int = Field(ge=0)
    metrics: dict[str, float]
    failures: dict[str, int]
    prediction_file: str
    prediction_sha256: str
    hardware: str
    peak_vram_mb: float = Field(ge=0)
    wall_clock_min: float = Field(ge=0)


class MetricSummary(_StrictModel):
    mean: float
    std: float = Field(ge=0)
    per_seed: list[float] = Field(min_length=1)


class CandidateResult(_StrictModel):
    schema_version: Literal["candidate-result-v1"] = RESULT_SCHEMA_VERSION
    protocol_mode: Literal["reportable", "smoke_non_reportable"]
    contract_version: Literal["m1-experiment-v1"]
    task: Literal["m1_catchup"]
    candidate_id: Literal["m1-a", "m1-b", "m1-c", "m1-d"]
    label: str
    mode: str
    trainer: str
    split: str
    split_path: str
    dataset_version: str
    git_sha: str
    model_repo: str | None
    model_revision: str | None
    config_sha256: str
    seeds: list[int] = Field(min_length=1)
    metrics: dict[str, MetricSummary]
    failures: dict[str, int]
    runs: list[SeedRunResult] = Field(min_length=1)
    hardware: list[str] = Field(min_length=1)
    peak_vram_mb: float = Field(ge=0)
    wall_clock_min: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_runs(self) -> Self:
        run_seeds = [run.seed for run in self.runs]
        if run_seeds != self.seeds:
            raise ValueError("runs must appear once in the same order as seeds")
        for name, metric in self.metrics.items():
            if len(metric.per_seed) != len(self.seeds):
                raise ValueError(f"metric {name} must contain one value per seed")
            run_values: list[float] = []
            for run in self.runs:
                if name not in run.metrics:
                    raise ValueError(f"run seed {run.seed} is missing metric {name}")
                run_values.append(run.metrics[name])
            if metric.per_seed != run_values:
                raise ValueError(f"metric {name} per_seed values differ from runs")
            expected_mean = float(statistics.fmean(run_values))
            expected_std = float(statistics.pstdev(run_values))
            if not math.isclose(metric.mean, expected_mean, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"metric {name} mean differs from per_seed values")
            if not math.isclose(metric.std, expected_std, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"metric {name} std differs from per_seed values")
        if any(set(run.metrics) != set(self.metrics) for run in self.runs):
            raise ValueError("run metric sets must match the candidate metric set")
        expected_failures = {
            code: sum(run.failures.get(code, 0) for run in self.runs) for code in self.failures
        }
        if any(set(run.failures) != set(self.failures) for run in self.runs):
            raise ValueError("run failure-code sets must match the candidate failure-code set")
        if self.failures != expected_failures:
            raise ValueError("candidate failure totals differ from seed runs")
        if self.peak_vram_mb != max(run.peak_vram_mb for run in self.runs):
            raise ValueError("candidate peak_vram_mb differs from seed runs")
        if not math.isclose(
            self.wall_clock_min,
            sum(run.wall_clock_min for run in self.runs),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("candidate wall_clock_min differs from seed runs")
        if self.hardware != sorted({run.hardware for run in self.runs}):
            raise ValueError("candidate hardware differs from seed runs")
        return self
