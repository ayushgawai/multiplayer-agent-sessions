"""Safety-gate and ranking tests for the M1 comparison report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest

from eval.compare import compare
from eval.harness import HarnessError, load_contract
from eval.run_contract import CandidateResult, MetricSummary, SeedRunResult

METRICS = {
    "schema_valid_rate": 1.0,
    "critical_fact_recall": 0.80,
    "unsupported_claim_rate": 0.01,
    "attribution_accuracy": 0.99,
    "status_consistency": 0.99,
    "rouge_l": 70.0,
    "bertscore_f1": 0.90,
    "human_edit_rate": 0.10,
    "latency_p50_ms": 10.0,
    "latency_p95_ms": 20.0,
    "peak_vram_mb": 100.0,
}


CandidateId = Literal["m1-a", "m1-b", "m1-c", "m1-d"]
CANDIDATE_IDS: tuple[CandidateId, ...] = ("m1-a", "m1-b", "m1-c", "m1-d")


def _result(candidate_id: CandidateId, **overrides: float) -> CandidateResult:
    values = {**METRICS, **overrides}
    seeds = [13, 29, 47]
    runs = [
        SeedRunResult(
            seed=seed,
            attempted_examples=10,
            valid_outputs=10,
            metrics=values,
            failures={
                "invalid_schema": 0,
                "missing_critical_fact": 0,
                "unsupported_claim": 0,
                "wrong_attribution": 0,
                "wrong_status": 0,
                "generic_output": 0,
                "truncated": 0,
            },
            prediction_file=f"predictions/{candidate_id}/seed-{seed}.jsonl",
            prediction_sha256="a" * 64,
            hardware="test-gpu",
            peak_vram_mb=values["peak_vram_mb"],
            wall_clock_min=1.0,
        )
        for seed in seeds
    ]
    return CandidateResult(
        protocol_mode="reportable",
        contract_version="m1-experiment-v1",
        task="m1_catchup",
        candidate_id=candidate_id,
        label=candidate_id,
        mode="classical" if candidate_id == "m1-a" else "qlora",
        trainer="test",
        split="session_test",
        split_path="data/splits/m1_session_v1",
        dataset_version="dataset-v1",
        git_sha="b" * 40,
        model_repo=None if candidate_id == "m1-a" else "example/model",
        model_revision=None if candidate_id == "m1-a" else "c" * 40,
        config_sha256="d" * 64,
        seeds=seeds,
        metrics={
            name: MetricSummary(mean=value, std=0.0, per_seed=[value] * 3)
            for name, value in values.items()
        },
        failures={name: 0 for name in runs[0].failures},
        runs=runs,
        hardware=["test-gpu"],
        peak_vram_mb=values["peak_vram_mb"],
        wall_clock_min=3.0,
    )


def _write_results(results_dir: Path, results: list[CandidateResult]) -> None:
    results_dir.mkdir()
    for result in results:
        path = results_dir / f"{result.candidate_id}-session_test.json"
        path.write_text(
            json.dumps(result.model_dump(mode="json"), sort_keys=True), encoding="utf-8"
        )


def test_compare_applies_safety_gates_and_keeps_human_confirmation(tmp_path: Path) -> None:
    results = [
        _result("m1-a", critical_fact_recall=0.75),
        _result("m1-b", critical_fact_recall=0.90),
        _result("m1-c", critical_fact_recall=0.88, unsupported_claim_rate=0.03),
        _result("m1-d", critical_fact_recall=0.85),
    ]
    results_dir = tmp_path / "results"
    _write_results(results_dir, results)
    output = tmp_path / "m1_bakeoff.md"

    markdown = compare(
        results_dir=results_dir,
        split="session_test",
        contract_path=Path("eval/configs/m1-contract.yaml"),
        output_path=output,
    )

    assert "Provisional machine-ranked leader: **m1-b**" in markdown
    assert "This is not the final winner" in markdown
    assert "m1-c | no" in markdown
    assert "failed unsupported_claim_rate gate" in markdown
    assert output.read_text(encoding="utf-8") == markdown


def test_compare_rejects_mixed_dataset_versions(tmp_path: Path) -> None:
    results = [_result(candidate_id) for candidate_id in CANDIDATE_IDS]
    results[3] = results[3].model_copy(update={"dataset_version": "different-dataset"})
    results_dir = tmp_path / "results"
    _write_results(results_dir, results)

    with pytest.raises(HarnessError, match="disagree on dataset_version"):
        compare(
            results_dir=results_dir,
            split="session_test",
            contract_path=Path("eval/configs/m1-contract.yaml"),
            output_path=tmp_path / "out.md",
        )


def test_quality_tie_uses_latency_tie_break(tmp_path: Path) -> None:
    results = [
        _result("m1-a", critical_fact_recall=0.70),
        _result("m1-b", critical_fact_recall=0.805, bertscore_f1=0.905),
        _result(
            "m1-c",
            critical_fact_recall=0.800,
            bertscore_f1=0.900,
            latency_p95_ms=8.0,
        ),
        _result("m1-d", critical_fact_recall=0.60),
    ]
    results_dir = tmp_path / "results"
    _write_results(results_dir, results)

    markdown = compare(
        results_dir=results_dir,
        split="session_test",
        contract_path=Path("eval/configs/m1-contract.yaml"),
        output_path=tmp_path / "out.md",
    )

    assert "Provisional machine-ranked leader: **m1-c**" in markdown


def test_compare_rejects_summary_that_disagrees_with_seed_runs(tmp_path: Path) -> None:
    results = [_result(candidate_id) for candidate_id in CANDIDATE_IDS]
    results_dir = tmp_path / "results"
    _write_results(results_dir, results)
    path = results_dir / "m1-b-session_test.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metrics"]["critical_fact_recall"]["mean"] = 0.01
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HarnessError, match="mean differs from per_seed"):
        compare(
            results_dir=results_dir,
            split="session_test",
            contract_path=Path("eval/configs/m1-contract.yaml"),
            output_path=tmp_path / "out.md",
        )


def test_contract_used_by_comparison_is_frozen() -> None:
    contract = load_contract()

    assert contract.seeds == [13, 29, 47]
    assert contract.selection.final_confirmation == "blinded_human_review_of_top_two"
