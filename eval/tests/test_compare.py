"""Safety-gate and ranking tests for the M1 comparison report."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Literal

import pytest

from eval.compare import assess_eligibility, compare, rank_eligible
from eval.harness import DEFAULT_RUNNERS, HarnessError, load_contract
from eval.run_contract import (
    CandidateResult,
    M1ExperimentContract,
    MetricSummary,
    PluginIdentity,
    SeedRunResult,
)

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
EXAMPLES = 10
IDS_SHA = "1" * 64
CONTENT_SHA = "2" * 64
EVALUATOR = PluginIdentity(spec="eval.m1_evaluator:evaluate", module_sha256="e" * 64)
FAKE_RUNNER = "eval.tests.fake_m1_plugin:build_eval_runner"


def _result(
    candidate_id: CandidateId,
    per_seed: dict[str, list[float]] | None = None,
    **overrides: float,
) -> CandidateResult:
    values = {**METRICS, **overrides}
    seeds = [13, 29, 47]
    seed_values = {name: [value] * len(seeds) for name, value in values.items()}
    seed_values.update(per_seed or {})
    runs = [
        SeedRunResult(
            seed=seed,
            attempted_examples=EXAMPLES,
            example_ids_sha256=IDS_SHA,
            examples_sha256=CONTENT_SHA,
            valid_outputs=EXAMPLES,
            metrics={name: series[index] for name, series in seed_values.items()},
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
            peak_vram_mb=seed_values["peak_vram_mb"][index],
            wall_clock_min=1.0,
        )
        for index, seed in enumerate(seeds)
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
        dataset_manifest_sha256="f" * 64,
        manifest_example_count=EXAMPLES,
        runner=PluginIdentity(spec=DEFAULT_RUNNERS[candidate_id], module_sha256="9" * 64),
        evaluator=EVALUATOR,
        git_sha="b" * 40,
        model_repo=None if candidate_id == "m1-a" else "example/model",
        model_revision=None if candidate_id == "m1-a" else "c" * 40,
        config_sha256="d" * 64,
        seeds=seeds,
        metrics={
            name: MetricSummary(
                mean=float(statistics.fmean(series)),
                std=float(statistics.pstdev(series)),
                per_seed=series,
            )
            for name, series in seed_values.items()
        },
        failures={name: 0 for name in runs[0].failures},
        runs=runs,
        hardware=["test-gpu"],
        peak_vram_mb=max(seed_values["peak_vram_mb"]),
        wall_clock_min=3.0,
    )


def _write_results(
    results_dir: Path, results: list[CandidateResult], split: str = "session_test"
) -> None:
    results_dir.mkdir()
    for result in results:
        payload = result.model_dump(mode="json")
        payload["split"] = split
        path = results_dir / f"{result.candidate_id}-{split}.json"
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _edit_result(results_dir: Path, candidate_id: str, edit: object, split: str = "session_test") -> None:
    """Apply ``edit(payload)`` to one written result file, as a tampered or mixed artifact would."""

    path = results_dir / f"{candidate_id}-{split}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    edit(payload)  # type: ignore[operator]
    path.write_text(json.dumps(payload), encoding="utf-8")


def _compare(tmp_path: Path, results_dir: Path, split: str = "session_test") -> str:
    return compare(
        results_dir=results_dir,
        split=split,
        contract_path=Path("eval/configs/m1-contract.yaml"),
        output_path=tmp_path / "out.md",
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


def test_one_unsafe_seed_is_not_hidden_by_the_three_seed_mean() -> None:
    contract = load_contract()
    # Mean unsupported_claim_rate is 0.01, under the 0.02 gate, but seed 47 is 0.03.
    results = [
        _result("m1-a", unsupported_claim_rate=0.05),
        _result("m1-b", per_seed={"unsupported_claim_rate": [0.0, 0.0, 0.03]}),
        _result("m1-c"),
        _result("m1-d"),
    ]

    assessments = assess_eligibility(results, contract)

    m1_b = assessments[1]
    assert m1_b.result.metrics["unsupported_claim_rate"].mean == pytest.approx(0.01)
    assert m1_b.eligible is False
    assert "failed unsupported_claim_rate gate on seeds [47]" in m1_b.reasons


def test_baseline_gate_compares_each_seed_with_matched_m1_a_seed() -> None:
    contract = load_contract()
    # Equal means (0.01), so a mean-based check passes, but seed 13 is worse than m1-a seed 13.
    results = [
        _result("m1-a", per_seed={"unsupported_claim_rate": [0.005, 0.015, 0.010]}),
        _result("m1-b", per_seed={"unsupported_claim_rate": [0.010, 0.010, 0.010]}),
        _result("m1-c", per_seed={"unsupported_claim_rate": [0.005, 0.015, 0.010]}),
        _result("m1-d"),
    ]

    assessments = assess_eligibility(results, contract)

    assert assessments[1].eligible is False
    assert assessments[1].reasons == (
        "unsupported_claim_rate worse than matched-seed m1-a on seeds [13]",
    )
    assert assessments[2].eligible is True


def test_ranking_retains_only_candidates_within_margin_of_stage_best() -> None:
    contract = load_contract()
    # Pairwise, m1-b ties m1-c and m1-c ties m1-d on recall, but m1-b is 0.018 below the
    # stage best. The stage-best rule drops m1-b, then bertscore_f1 separates m1-c and m1-d.
    results = [
        _result("m1-a", critical_fact_recall=0.70),
        _result("m1-b", critical_fact_recall=0.800, bertscore_f1=0.99),
        _result("m1-c", critical_fact_recall=0.809, bertscore_f1=0.95),
        _result("m1-d", critical_fact_recall=0.818, bertscore_f1=0.90),
    ]

    ranked = rank_eligible(assess_eligibility(results, contract), contract)

    assert [item.result.candidate_id for item in ranked] == ["m1-c", "m1-d", "m1-b", "m1-a"]


def test_contract_rejects_tie_margins_that_do_not_match_ranked_metrics() -> None:
    payload = load_contract().model_dump(mode="json")
    payload["selection"]["quality_tie_margins"].pop("rouge_l")

    with pytest.raises(ValueError, match="quality_tie_margins must match rank_eligible_by"):
        M1ExperimentContract.model_validate(payload)


def test_compare_rejects_results_produced_by_the_test_double(tmp_path: Path) -> None:
    results = [
        _result(candidate_id).model_copy(
            update={"runner": PluginIdentity(spec=FAKE_RUNNER, module_sha256="9" * 64)}
        )
        for candidate_id in CANDIDATE_IDS
    ]
    results_dir = tmp_path / "results"
    _write_results(results_dir, results)

    with pytest.raises(HarnessError, match="produced by a test runner plugin"):
        _compare(tmp_path, results_dir)


def test_compare_rejects_a_test_evaluator(tmp_path: Path) -> None:
    fake = {"spec": "eval.tests.fake_m1_plugin:evaluate", "module_sha256": "e" * 64}
    results_dir = tmp_path / "results"
    _write_results(results_dir, [_result(candidate_id) for candidate_id in CANDIDATE_IDS])
    for candidate_id in CANDIDATE_IDS:
        _edit_result(results_dir, candidate_id, lambda payload: payload.update(evaluator=fake))

    with pytest.raises(HarnessError, match="produced by a test evaluator plugin"):
        _compare(tmp_path, results_dir)


@pytest.mark.parametrize("field", ["spec", "module_sha256"])
def test_compare_rejects_mixed_evaluators(tmp_path: Path, field: str) -> None:
    other = {"spec": "eval.other_evaluator:evaluate", "module_sha256": "d" * 64}
    results_dir = tmp_path / "results"
    _write_results(results_dir, [_result(candidate_id) for candidate_id in CANDIDATE_IDS])
    _edit_result(results_dir, "m1-c", lambda payload: payload["evaluator"].update({field: other[field]}))

    with pytest.raises(HarnessError, match="disagree on evaluator"):
        _compare(tmp_path, results_dir)


def test_qmsum_comparison_is_diagnostic_and_names_no_leader(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    _write_results(
        results_dir,
        [
            _result("m1-a", critical_fact_recall=0.70),
            _result("m1-b", critical_fact_recall=0.90),
            _result("m1-c"),
            _result("m1-d"),
        ],
        split="qmsum_test",
    )

    markdown = _compare(tmp_path, results_dir, split="qmsum_test")

    assert "This is not a selection result" in markdown
    assert "leader" not in markdown
    assert "provisional rank" not in markdown
    assert "diagnostic only" in markdown


def test_compare_rejects_a_candidate_that_evaluated_fewer_examples(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    _write_results(results_dir, [_result(candidate_id) for candidate_id in CANDIDATE_IDS])

    def evaluate_subset(payload: dict[str, object]) -> None:
        for run in payload["runs"]:  # type: ignore[attr-defined]
            run["attempted_examples"] = EXAMPLES - 1
            run["valid_outputs"] = EXAMPLES - 1

    _edit_result(results_dir, "m1-b", evaluate_subset)

    with pytest.raises(HarnessError, match="evaluated 9 examples; the manifest split has 10"):
        _compare(tmp_path, results_dir)


def test_compare_rejects_a_candidate_with_different_example_ids(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    _write_results(results_dir, [_result(candidate_id) for candidate_id in CANDIDATE_IDS])
    _edit_result(
        results_dir, "m1-d", lambda payload: payload["runs"][1].update(example_ids_sha256="3" * 64)
    )

    with pytest.raises(HarnessError, match="evaluated different examples"):
        _compare(tmp_path, results_dir)


def test_compare_rejects_mixed_dataset_manifests(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    _write_results(results_dir, [_result(candidate_id) for candidate_id in CANDIDATE_IDS])
    _edit_result(results_dir, "m1-a", lambda payload: payload.update(dataset_manifest_sha256="0" * 64))

    with pytest.raises(HarnessError, match="disagree on dataset_manifest_sha256"):
        _compare(tmp_path, results_dir)


def test_candidate_exactly_at_the_tie_margin_is_retained() -> None:
    contract = load_contract()
    # 0.80 - 0.79 is slightly above 0.01 in floating point; m1-c must still tie with m1-b
    # on recall, and then win on BERTScore-F1.
    results = [
        _result("m1-a", critical_fact_recall=0.50),
        _result("m1-b", critical_fact_recall=0.80, bertscore_f1=0.90),
        _result("m1-c", critical_fact_recall=0.79, bertscore_f1=0.95),
        _result("m1-d", critical_fact_recall=0.50),
    ]
    assert 0.80 - 0.79 > 0.01

    ranked = rank_eligible(assess_eligibility(results, contract), contract)

    assert ranked[0].result.candidate_id == "m1-c"
