"""Tests for the shared M1 orchestration boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from eval.harness import (
    HarnessError,
    check_reportable_examples,
    load_candidate_config,
    load_contract,
    main,
    run_candidate,
    verify_split_manifest,
)
from collections.abc import Mapping
from typing import Any

from eval.contracts.m1 import M1Input
from eval.run_contract import PreparedCandidate, RunnerRequest, SeedRunResult
from eval.tests.fake_m1_plugin import (
    SmokeFixturePreparedCandidate,
    build_eval_runner,
    build_smoke_fixture_runner,
    evaluate,
)


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
    plugin_source = Path("eval/tests/fake_m1_plugin.py").read_bytes()
    assert result.runner.spec == "eval.tests.fake_m1_plugin:build_eval_runner"
    assert result.runner.module_sha256 == hashlib.sha256(plugin_source).hexdigest()
    assert result.evaluator.spec == "eval.tests.fake_m1_plugin:evaluate"
    assert result.dataset_manifest_sha256 is None
    assert len(result.runs[0].example_ids_sha256) == 64


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


def test_reportable_run_rejects_test_double_plugins(tmp_path: Path) -> None:
    config, config_path = load_candidate_config("m1-a")

    with pytest.raises(HarnessError, match="cannot use a test runner plugin"):
        run_candidate(
            config=config,
            config_path=config_path,
            contract=load_contract(),
            seeds=[13, 29, 47],
            split="qmsum_test",
            dataset_path=Path("data/splits/m1_v1"),
            output_dir=tmp_path / "results",
            runner_factory=build_eval_runner,
            evaluator=evaluate,
            smoke=False,
            enforce_clean_split=False,
        )


def test_cli_refuses_the_reported_fake_plugin_bakeoff(tmp_path: Path) -> None:
    # The review scenario: all four candidates through the CPU test double on qmsum_test.
    fake = "eval.tests.fake_m1_plugin:build_eval_runner"
    argv = ["--all", "--split", "qmsum_test", "--evaluator", "eval.tests.fake_m1_plugin:evaluate"]
    for candidate_id in ("m1-a", "m1-b", "m1-c", "m1-d"):
        argv += ["--runner", f"{candidate_id}={fake}"]
    argv += ["--output-dir", str(tmp_path)]

    with pytest.raises(HarnessError, match="cannot use a test runner plugin"):
        main(argv)
    assert not list(tmp_path.glob("*.json"))


def test_reportable_cli_refuses_to_overwrite_a_result(tmp_path: Path) -> None:
    existing = tmp_path / "m1-a-qmsum_test.json"
    existing.write_text("{}", encoding="utf-8")

    with pytest.raises(HarnessError, match="refusing to overwrite reportable result"):
        main(
            [
                "--candidate",
                "m1-a",
                "--split",
                "qmsum_test",
                "--evaluator",
                "eval.tests.fake_m1_plugin:evaluate",
                "--output-dir",
                str(tmp_path),
            ]
        )
    assert existing.read_text(encoding="utf-8") == "{}"


def _write_split(dataset: Path, rows: list[str]) -> None:
    dataset.mkdir()
    body = "".join(row + "\n" for row in rows).encode("utf-8")
    (dataset / "test.jsonl").write_bytes(body)
    manifest = {
        "splits": {
            "test": {
                "count": len(rows),
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
            }
        }
    }
    (dataset / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_split_manifest_check_accepts_matching_files(tmp_path: Path) -> None:
    dataset = tmp_path / "split"
    _write_split(dataset, ['{"id": "a"}', '{"id": "b"}'])

    manifest_sha, count = verify_split_manifest(dataset, "test")

    assert count == 2
    assert manifest_sha == hashlib.sha256((dataset / "MANIFEST.json").read_bytes()).hexdigest()


def test_split_manifest_check_rejects_a_tampered_split_file(tmp_path: Path) -> None:
    dataset = tmp_path / "split"
    _write_split(dataset, ['{"id": "a"}', '{"id": "b"}'])
    (dataset / "test.jsonl").write_text('{"id": "a"}\n{"id": "x"}\n', encoding="utf-8")

    with pytest.raises(HarnessError, match="sha256 does not match MANIFEST.json"):
        verify_split_manifest(dataset, "test")


def test_committed_qmsum_split_matches_its_manifest() -> None:
    _, count = verify_split_manifest(Path("data/splits/m1_v1"), "test")

    assert count == 281


def _seed_run(seed: int, attempted: int, ids_sha: str) -> SeedRunResult:
    return SeedRunResult(
        seed=seed,
        attempted_examples=attempted,
        example_ids_sha256=ids_sha,
        examples_sha256="2" * 64,
        valid_outputs=attempted,
        metrics={},
        failures={},
        prediction_file="predictions.jsonl",
        prediction_sha256="a" * 64,
        hardware="test",
        peak_vram_mb=0.0,
        wall_clock_min=0.0,
    )


def test_reportable_run_must_evaluate_the_whole_manifest_split() -> None:
    with pytest.raises(HarnessError, match="evaluated 280 examples; the manifest split has 281"):
        check_reportable_examples([_seed_run(13, 281, "1" * 64), _seed_run(29, 280, "1" * 64)], 281)


def test_reportable_seeds_must_evaluate_the_same_examples() -> None:
    with pytest.raises(HarnessError, match="seeds evaluated different examples"):
        check_reportable_examples([_seed_run(13, 281, "1" * 64), _seed_run(29, 281, "3" * 64)], 281)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class CostedCandidate:
    """Smoke-fixture candidate whose predict advances a fake clock by a per-example cost."""

    def __init__(
        self, inner: SmokeFixturePreparedCandidate, clock: FakeClock, fail_on: str | None = None
    ) -> None:
        self._inner = inner
        self._clock = clock
        self._fail_on = fail_on
        self.dataset_version = inner.dataset_version
        self.hardware = inner.hardware
        self.examples = inner.examples
        self.cost_ms = {
            example.model_input.example_id: float(index + 1)
            for index, example in enumerate(inner.examples)
        }

    def predict(self, model_input: M1Input) -> Mapping[str, Any]:
        self._clock.now += self.cost_ms[model_input.example_id] / 1000.0
        if model_input.example_id == self._fail_on:
            raise RuntimeError("out of memory at 4,096 tokens")
        return self._inner.predict(model_input)

    def peak_vram_mb(self) -> float:
        return 0.0

    def close(self) -> None:
        return None


def _run_costed(tmp_path: Path, clock: FakeClock, fail_index: int | None = None) -> Any:
    config, config_path = load_candidate_config("m1-a")
    fixtures = Path("data/m1_smoke/fixtures")

    def costed_runner(request: RunnerRequest) -> PreparedCandidate:
        inner = SmokeFixturePreparedCandidate(request)
        fail_on = None if fail_index is None else inner.examples[fail_index].model_input.example_id
        return CostedCandidate(inner, clock, fail_on)

    return run_candidate(
        config=config,
        config_path=config_path,
        contract=load_contract(),
        seeds=[13],
        split="smoke",
        dataset_path=fixtures,
        output_dir=tmp_path / "results",
        runner_factory=costed_runner,
        evaluator=evaluate,
        smoke=True,
        max_examples=18,
        timer=clock,
    )


def test_latency_is_measured_across_all_examples_not_one(tmp_path: Path) -> None:
    # Example i costs i + 1 ms. Timing only examples[0] would report 1 ms at every percentile.
    result = _run_costed(tmp_path, FakeClock())

    assert result.runs[0].attempted_examples == 18
    assert result.metrics["latency_p50_ms"].mean == pytest.approx(9.5)
    assert result.metrics["latency_p95_ms"].mean == pytest.approx(17.15)


def test_candidate_exception_counts_as_invalid_output_not_a_failed_seed(tmp_path: Path) -> None:
    result = _run_costed(tmp_path, FakeClock(), fail_index=4)

    run = result.runs[0]
    assert run.attempted_examples == 18
    assert run.valid_outputs == 17
    assert result.metrics["schema_valid_rate"].mean == pytest.approx(17 / 18)
    assert result.failures["invalid_schema"] == 1
    records = [
        json.loads(line)
        for line in Path(run.prediction_file).read_text(encoding="utf-8").splitlines()
    ]
    failed = [record for record in records if not record["valid"]]
    assert len(failed) == 1
    assert failed[0]["output"] == {"_exception": "RuntimeError"}
    assert failed[0]["validation_error"].startswith("candidate raised RuntimeError")
