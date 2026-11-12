"""Validate M1 result artifacts and generate the frozen bake-off table."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cmp_to_key
from pathlib import Path
import sys

from pydantic import ValidationError

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.harness import (  # noqa: E402
    CONFIG_DIR,
    DEFAULT_OUTPUT_DIR,
    HarnessError,
    M1_CANDIDATES,
    load_contract,
)
from eval.run_contract import (  # noqa: E402
    REPORTABLE_PROTOCOL,
    CandidateResult,
    M1ExperimentContract,
    MetricSummary,
)


@dataclass(frozen=True)
class CandidateAssessment:
    result: CandidateResult
    eligible: bool
    reasons: tuple[str, ...]


def load_result(path: Path) -> CandidateResult:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessError(f"cannot load result {path}: {exc}") from exc
    try:
        return CandidateResult.model_validate(payload)
    except ValidationError as exc:
        raise HarnessError(f"invalid result schema {path}: {exc}") from exc


def load_results(results_dir: Path, split: str) -> list[CandidateResult]:
    results: list[CandidateResult] = []
    for candidate_id in M1_CANDIDATES:
        path = results_dir / f"{candidate_id}-{split}.json"
        if not path.is_file():
            raise HarnessError(f"missing result for {candidate_id}: {path}")
        result = load_result(path)
        if result.candidate_id != candidate_id:
            raise HarnessError(f"result identity mismatch in {path}")
        results.append(result)
    return results


def _mean(result: CandidateResult, metric: str) -> float:
    try:
        return result.metrics[metric].mean
    except KeyError as exc:
        raise HarnessError(f"{result.candidate_id} is missing metric {metric}") from exc


def validate_result_set(
    results: Sequence[CandidateResult], contract: M1ExperimentContract, split: str
) -> None:
    if [result.candidate_id for result in results] != list(M1_CANDIDATES):
        raise HarnessError("result set must contain m1-a through m1-d in order")
    expected_metrics = set(contract.metrics)
    for result in results:
        if result.protocol_mode != REPORTABLE_PROTOCOL:
            raise HarnessError(f"{result.candidate_id} is a non-reportable smoke result")
        if result.contract_version != contract.contract_version:
            raise HarnessError(f"{result.candidate_id} uses a different contract version")
        if result.task != contract.task:
            raise HarnessError(f"{result.candidate_id} uses a different task")
        if result.split != split:
            raise HarnessError(f"{result.candidate_id} uses split {result.split!r}, expected {split!r}")
        if result.seeds != contract.seeds:
            raise HarnessError(f"{result.candidate_id} does not contain all frozen seeds")
        if set(result.metrics) != expected_metrics:
            raise HarnessError(f"{result.candidate_id} metric set differs from the contract")
        for name, summary in result.metrics.items():
            _validate_metric_summary(result.candidate_id, name, summary, len(contract.seeds))

    shared_fields = ("split_path", "dataset_version")
    reference = results[0]
    for result in results[1:]:
        for field in shared_fields:
            if getattr(result, field) != getattr(reference, field):
                raise HarnessError(f"mixed result set: candidates disagree on {field}")


def _validate_metric_summary(
    candidate_id: str, metric: str, summary: MetricSummary, expected_seeds: int
) -> None:
    if len(summary.per_seed) != expected_seeds:
        raise HarnessError(f"{candidate_id} metric {metric} is incomplete")


def assess_eligibility(
    results: Sequence[CandidateResult], contract: M1ExperimentContract
) -> list[CandidateAssessment]:
    gates = contract.selection.eligible_if
    baseline_unsupported = _mean(results[0], "unsupported_claim_rate")
    assessments: list[CandidateAssessment] = []
    for result in results:
        reasons: list[str] = []
        if gates.all_three_seed_runs_complete and result.seeds != contract.seeds:
            reasons.append("incomplete frozen seed set")
        checks = (
            ("schema_valid_rate", _mean(result, "schema_valid_rate") >= gates.schema_valid_rate_min),
            (
                "unsupported_claim_rate",
                _mean(result, "unsupported_claim_rate") <= gates.unsupported_claim_rate_max,
            ),
            (
                "attribution_accuracy",
                _mean(result, "attribution_accuracy") >= gates.attribution_accuracy_min,
            ),
            (
                "status_consistency",
                _mean(result, "status_consistency") >= gates.status_consistency_min,
            ),
        )
        reasons.extend(f"failed {metric} gate" for metric, passed in checks if not passed)
        if (
            gates.unsupported_claim_rate_no_worse_than_m1_a
            and _mean(result, "unsupported_claim_rate") > baseline_unsupported
        ):
            reasons.append("unsupported_claim_rate worse than m1-a")
        assessments.append(
            CandidateAssessment(result=result, eligible=not reasons, reasons=tuple(reasons))
        )
    return assessments


def rank_eligible(
    assessments: Sequence[CandidateAssessment], contract: M1ExperimentContract
) -> list[CandidateAssessment]:
    eligible = [assessment for assessment in assessments if assessment.eligible]
    if not eligible:
        return []
    directions = {
        name: definition.get("direction") for name, definition in contract.metrics.items()
    }

    def compare_candidates(left: CandidateAssessment, right: CandidateAssessment) -> int:
        for metric in contract.selection.rank_eligible_by:
            left_value = _mean(left.result, metric)
            right_value = _mean(right.result, metric)
            if abs(left_value - right_value) <= contract.selection.quality_tie_margin:
                continue
            if directions.get(metric) == "maximize":
                return -1 if left_value > right_value else 1
            return -1 if left_value < right_value else 1
        for metric in contract.selection.tie_break_by:
            left_value = _mean(left.result, metric)
            right_value = _mean(right.result, metric)
            if left_value == right_value:
                continue
            if directions.get(metric) == "maximize":
                return -1 if left_value > right_value else 1
            return -1 if left_value < right_value else 1
        left_index = M1_CANDIDATES.index(left.result.candidate_id)
        right_index = M1_CANDIDATES.index(right.result.candidate_id)
        return (left_index > right_index) - (left_index < right_index)

    return sorted(eligible, key=cmp_to_key(compare_candidates))


def _format_metric(value: float) -> str:
    return f"{value:.4f}"


def render_markdown(
    assessments: Sequence[CandidateAssessment],
    ranked: Sequence[CandidateAssessment],
    contract: M1ExperimentContract,
    split: str,
) -> str:
    rank_by = list(contract.selection.rank_eligible_by)
    tie_breaks = list(contract.selection.tie_break_by)
    columns = [
        "Candidate",
        "Eligible",
        *rank_by,
        "schema_valid_rate",
        "unsupported_claim_rate",
        "attribution_accuracy",
        "status_consistency",
        *tie_breaks,
        "Decision",
    ]
    rank = {assessment.result.candidate_id: index + 1 for index, assessment in enumerate(ranked)}
    rows = [f"| {' | '.join(columns)} |", f"| {' | '.join(['---'] * len(columns))} |"]
    for assessment in assessments:
        result = assessment.result
        decision = (
            f"provisional rank {rank[result.candidate_id]}"
            if assessment.eligible
            else "; ".join(assessment.reasons)
        )
        values = [
            result.candidate_id,
            "yes" if assessment.eligible else "no",
            *(_format_metric(_mean(result, metric)) for metric in rank_by),
            _format_metric(_mean(result, "schema_valid_rate")),
            _format_metric(_mean(result, "unsupported_claim_rate")),
            _format_metric(_mean(result, "attribution_accuracy")),
            _format_metric(_mean(result, "status_consistency")),
            *(_format_metric(_mean(result, metric)) for metric in tie_breaks),
            decision,
        ]
        rows.append(f"| {' | '.join(values)} |")

    if ranked:
        leader = ranked[0].result.candidate_id
        conclusion = (
            f"Provisional machine-ranked leader: **{leader}**. This is not the final winner. "
            f"The frozen contract requires {contract.selection.final_confirmation.replace('_', ' ')} "
            "of the top two eligible candidates."
        )
    else:
        conclusion = "No candidate passed every frozen safety gate; no winner can be selected."
    return "\n".join(
        [
            "# M1 candidate bake-off",
            "",
            f"Split: `{split}` · Contract: `{contract.contract_version}` · Seeds: "
            + ", ".join(str(seed) for seed in contract.seeds),
            "",
            *rows,
            "",
            conclusion,
            "",
            "Values are the mean across the frozen seeds; per-seed values remain in the result JSON.",
            "",
        ]
    )


def compare(
    *, results_dir: Path, split: str, contract_path: Path, output_path: Path
) -> str:
    contract = load_contract(contract_path)
    results = load_results(results_dir, split)
    validate_result_set(results, contract, split)
    assessments = assess_eligibility(results, contract)
    ranked = rank_eligible(assessments, contract)
    markdown = render_markdown(assessments, ranked, contract, split)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8", newline="\n")
    return markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["m1"], default="m1")
    parser.add_argument("--split", choices=["session_test", "qmsum_test"], required=True)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--contract", type=Path, default=CONFIG_DIR / "m1-contract.yaml")
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    compare(
        results_dir=args.results_dir,
        split=args.split,
        contract_path=args.contract,
        output_path=args.out,
    )
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
