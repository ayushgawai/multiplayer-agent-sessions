"""Tests for the shared M1 orchestration boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.harness import HarnessError, load_candidate_config, load_contract, run_candidate
from eval.tests.fake_m1_plugin import build_eval_runner, build_smoke_fixture_runner, evaluate


class StepTimer:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.001
        return self.value


def test_smoke_run_validates_outputs_and_writes_prediction_provenance(tmp_path: Path) -> None:
    config, config_path = load_candidate_config("m1-a")
    contract = load_contract()

    result = run_candidate(
        config=config,
        config_path=config_path,
        contract=contract,
        seeds=[13],
        split="smoke",
        dataset_path=tmp_path / "fixtures",
        output_dir=tmp_path / "results",
        runner_factory=build_eval_runner,
        evaluator=evaluate,
        smoke=True,
        timer=StepTimer(),
    )

    assert result.protocol_mode == "smoke_non_reportable"
    assert result.seeds == [13]
    assert result.metrics["schema_valid_rate"].mean == 1.0
    assert result.metrics["latency_p50_ms"].mean == pytest.approx(1.0)
    assert result.metrics["latency_p95_ms"].mean == pytest.approx(1.0)
    assert result.hardware == ["cpu-test-double"]
    prediction_path = Path(result.runs[0].prediction_file)
    assert prediction_path.is_file()
    prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
    assert prediction["valid"] is True
    assert prediction["output"]["candidate_id"] == "m1-a"


def test_reportable_run_requires_every_frozen_seed(tmp_path: Path) -> None:
    config, config_path = load_candidate_config("m1-a")

    with pytest.raises(HarnessError, match="every frozen seed"):
        run_candidate(
            config=config,
            config_path=config_path,
            contract=load_contract(),
            seeds=[13],
            split="session_test",
            dataset_path=tmp_path,
            output_dir=tmp_path / "results",
            runner_factory=build_eval_runner,
            evaluator=evaluate,
            smoke=False,
            enforce_clean_split=False,
        )


def test_evaluator_cannot_overwrite_harness_metrics(tmp_path: Path) -> None:
    config, config_path = load_candidate_config("m1-a")

    def invalid_evaluator(*args: object) -> dict[str, object]:
        del args
        return {
            "metrics": {"schema_valid_rate": 0.0},
            "failures": {},
        }

    with pytest.raises(HarnessError, match="overwrite harness-owned"):
        run_candidate(
            config=config,
            config_path=config_path,
            contract=load_contract(),
            seeds=[13],
            split="smoke",
            dataset_path=tmp_path,
            output_dir=tmp_path / "results",
            runner_factory=build_eval_runner,
            evaluator=invalid_evaluator,  # type: ignore[arg-type]
            smoke=True,
            timer=StepTimer(),
        )


def test_smoke_run_on_committed_m1_smoke_fixtures(tmp_path: Path) -> None:
    config, config_path = load_candidate_config("m1-a")

    result = run_candidate(
        config=config,
        config_path=config_path,
        contract=load_contract(),
        seeds=[13],
        split="smoke",
        dataset_path=Path("data/m1_smoke/fixtures"),
        output_dir=tmp_path / "results",
        runner_factory=build_smoke_fixture_runner,
        evaluator=evaluate,
        smoke=True,
        timer=StepTimer(),
    )

    assert result.protocol_mode == "smoke_non_reportable"
    assert result.dataset_version == "m1-smoke-v1"
    assert result.runs[0].attempted_examples == 18
    assert result.metrics["schema_valid_rate"].mean == 1.0
