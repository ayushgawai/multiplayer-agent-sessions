"""Validate M1 result artifacts and generate the frozen bake-off table."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
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
    is_test_plugin,
)

# Absolute slack on tie margins, so a value exactly at the margin is not dropped by float error
# (for example 0.80 - 0.79 is slightly above 0.01 in binary floating point).
TIE_TOLERANCE = 1e-9


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


def _per_seed(result: CandidateResult, metric: str) -> list[float]:
    try:
        return result.metrics[metric].per_seed
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

    for result in results:
        for role, identity in (("runner", result.runner), ("evaluator", result.evaluator)):
            if is_test_plugin(identity.spec):
                raise HarnessError(
                    f"{result.candidate_id} was produced by a test {role} plugin: {identity.spec}"
                )
        if result.dataset_manifest_sha256 is None or result.manifest_example_count is None:
            raise HarnessError(f"{result.candidate_id} has no verified dataset manifest")
        for run in result.runs:
            if run.attempted_examples != result.manifest_example_count:
                raise HarnessError(
                    f"{result.candidate_id} seed {run.seed} evaluated {run.attempted_examples} "
                    f"examples; the manifest split has {result.manifest_example_count}"
                )

    shared_fields = (
        "split_path",
        "dataset_version",
        "dataset_manifest_sha256",
        "manifest_example_count",
        "evaluator",
    )
    reference = results[0]
    for result in results[1:]:
        for field in shared_fields:
            if getattr(result, field) != getattr(reference, field):
                raise HarnessError(f"mixed result set: candidates disagree on {field}")

    example_sets = {
        (run.example_ids_sha256, run.examples_sha256) for result in results for run in result.runs
    }
    if len(example_sets) != 1:
        raise HarnessError("mixed result set: candidates or seeds evaluated different examples")


def _validate_metric_summary(
    candidate_id: str, metric: str, summary: MetricSummary, expected_seeds: int
) -> None:
    if len(summary.per_seed) != expected_seeds:
        raise HarnessError(f"{candidate_id} metric {metric} is incomplete")


def assess_eligibility(
    results: Sequence[CandidateResult], contract: M1ExperimentContract
) -> list[CandidateAssessment]:
    gates = contract.selection.eligible_if
    baseline_unsupported = _per_seed(results[0], "unsupported_claim_rate")
    assessments: list[CandidateAssessment] = []
    for result in results:
        reasons: list[str] = []
        if gates.all_three_seed_runs_complete and result.seeds != contract.seeds:
            reasons.append("incomplete frozen seed set")
        per_seed_checks = (
            (
                "schema_valid_rate",
                _per_seed(result, "schema_valid_rate"),
                lambda value: value >= gates.schema_valid_rate_min,
            ),
            (
                "unsupported_claim_rate",
                _per_seed(result, "unsupported_claim_rate"),
                lambda value: value <= gates.unsupported_claim_rate_max,
            ),
            (
                "attribution_accuracy",
                _per_seed(result, "attribution_accuracy"),
                lambda value: value >= gates.attribution_accuracy_min,
            ),
            (
                "status_consistency",
                _per_seed(result, "status_consistency"),
                lambda value: value >= gates.status_consistency_min,
            ),
        )
        for metric, values, passes in per_seed_checks:
            failed_seeds = [
                seed for seed, value in zip(result.seeds, values, strict=True) if not passes(value)
            ]
            if failed_seeds:
                reasons.append(f"failed {metric} gate on seeds {failed_seeds}")
        if gates.unsupported_claim_rate_no_worse_than_m1_a:
            failed_seeds = [
                seed
                for seed, value, baseline_value in zip(
                    result.seeds,
                    _per_seed(result, "unsupported_claim_rate"),
                    baseline_unsupported,
                    strict=True,
                )
                if value > baseline_value
            ]
            if failed_seeds:
                reasons.append(
                    "unsupported_claim_rate worse than matched-seed m1-a on seeds "
                    f"{failed_seeds}"
                )
        assessments.append(
            CandidateAssessment(result=result, eligible=not reasons, reasons=tuple(reasons))
        )
    return assessments


def rank_eligible(
    assessments: Sequence[CandidateAssessment], contract: M1ExperimentContract
) -> list[CandidateAssessment]:
    remaining = [assessment for assessment in assessments if assessment.eligible]
    ranked: list[CandidateAssessment] = []
    directions = {
        name: definition.get("direction") for name, definition in contract.metrics.items()
    }

    def retain_stage_best(
        candidates: Sequence[CandidateAssessment], metric: str, margin: float
    ) -> list[CandidateAssessment]:
        values = [_mean(candidate.result, metric) for candidate in candidates]
        direction = directions.get(metric)
        if direction == "maximize":
            stage_best = max(values)
            return [
                candidate
                for candidate, value in zip(candidates, values, strict=True)
                if stage_best - value <= margin + TIE_TOLERANCE
            ]
        if direction == "minimize":
            stage_best = min(values)
            return [
                candidate
                for candidate, value in zip(candidates, values, strict=True)
                if value - stage_best <= margin + TIE_TOLERANCE
            ]
        raise HarnessError(f"metric {metric} has invalid direction {direction!r}")

    def select_next(candidates: Sequence[CandidateAssessment]) -> CandidateAssessment:
        finalists = list(candidates)
        for metric in contract.selection.rank_eligible_by:
            finalists = retain_stage_best(
                finalists, metric, contract.selection.quality_tie_margins[metric]
            )
            if len(finalists) == 1:
                return finalists[0]
        for metric in contract.selection.tie_break_by:
            finalists = retain_stage_best(finalists, metric, 0.0)
            if len(finalists) == 1:
                return finalists[0]
        return min(finalists, key=lambda item: M1_CANDIDATES.index(item.result.candidate_id))

    while remaining:
        selected = select_next(remaining)
        ranked.append(selected)
        remaining.remove(selected)
    return ranked


def _format_metric(value: float) -> str:
    return f"{value:.4f}"


def render_markdown(
    assessments: Sequence[CandidateAssessment],
    ranked: Sequence[CandidateAssessment],
    contract: M1ExperimentContract,
    split: str,
    *,
    selection: bool = True,
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
        if not selection:
            decision = "diagnostic only"
        elif assessment.eligible:
            decision = f"provisional rank {rank[result.candidate_id]}"
        else:
            decision = "; ".join(assessment.reasons)
        values = [
            result.candidate_id,
            ("yes" if assessment.eligible else "no") if selection else "n/a",
            *(_format_metric(_mean(result, metric)) for metric in rank_by),
            _format_metric(_mean(result, "schema_valid_rate")),
            _format_metric(_mean(result, "unsupported_claim_rate")),
            _format_metric(_mean(result, "attribution_accuracy")),
            _format_metric(_mean(result, "status_consistency")),
            *(_format_metric(_mean(result, metric)) for metric in tie_breaks),
            decision,
        ]
        rows.append(f"| {' | '.join(values)} |")

    if not selection:
        conclusion = (
            f"Diagnostic comparison on `{split}`. This is not a selection result: the frozen "
            f"contract selects the M1 winner only on "
            f"`{contract.split['candidate_selection_split']}`, so no candidate is ranked here."
        )
    elif ranked:
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
    selection = split == contract.split["candidate_selection_split"]
    assessments = assess_eligibility(results, contract)
    ranked = rank_eligible(assessments, contract) if selection else []
    markdown = render_markdown(assessments, ranked, contract, split, selection=selection)
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
