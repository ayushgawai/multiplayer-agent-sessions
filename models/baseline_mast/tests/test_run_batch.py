"""Tests for the resumable MAST batch runner.

Linear: DAT-34 (MAST 10). Owner: Shriram Dundigalla.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from models.baseline_mast.parse_judge import MAST_CODES
from models.baseline_mast.run_batch import (
    FAILURES_FILE,
    PREDICTIONS_FILE,
    BatchRunner,
    EvalRecord,
    JudgeCall,
    StubJudge,
    completed_record_ids,
    failed_record_ids,
    load_eval_records,
    make_record_id,
    read_jsonl,
)

DATASET_SHA = "a" * 64


def make_records(n: int, trace_key: str = "AG2_GSM_Plus_Claude") -> list[EvalRecord]:
    return [
        EvalRecord(
            record_id=make_record_id(trace_key, i),
            trace_key=trace_key,
            trace_index=i,
            framework="AG2",
            llm_name="Claude",
            benchmark="GSM",
            trajectory=f"trajectory text for trace {i}",
            reference_labels={code: False for code in MAST_CODES},
            reference_source="released_llm_annotation",
        )
        for i in range(n)
    ]


def make_runner(result_dir: Path, judge: Any = None, **kw: Any) -> BatchRunner:
    return BatchRunner(
        judge=judge or StubJudge(),
        result_dir=result_dir,
        dataset_version="test-v1",
        dataset_sha256=DATASET_SHA,
        run_id=kw.pop("run_id", "run-test-001"),
        log=lambda _msg: None,
        **kw,
    )


class FlakyJudge:
    """Fails the named records until their attempt budget is exhausted."""

    def __init__(self, fail_substrings: set[str], fail_times: int = 99) -> None:
        self.fail_substrings = fail_substrings
        self.fail_times = fail_times
        self.calls: list[str] = []
        self._seen: dict[str, int] = {}

    @property
    def model_id(self) -> str:
        return "flaky-judge"

    @property
    def model_settings(self) -> dict[str, Any]:
        return {"temperature": 0.0}

    def judge(self, prompt: str) -> JudgeCall:
        self.calls.append(prompt)
        for needle in self.fail_substrings:
            if needle in prompt:
                self._seen[needle] = self._seen.get(needle, 0) + 1
                if self._seen[needle] <= self.fail_times:
                    return JudgeCall(
                        raw_response=None, latency_ms=1.0, error="upstream 503"
                    )
        return StubJudge().judge(prompt)


class ExplodingJudge:
    """Raises instead of returning a structured error."""

    @property
    def model_id(self) -> str:
        return "exploding-judge"

    @property
    def model_settings(self) -> dict[str, Any]:
        return {}

    def judge(self, prompt: str) -> JudgeCall:
        raise RuntimeError("socket closed")


def test_sample_batch_completes_end_to_end(tmp_path: Path) -> None:
    summary = make_runner(tmp_path).run(make_records(5))

    assert summary.attempted == 5
    assert summary.succeeded == 5
    assert summary.failed == 0
    records = list(read_jsonl(tmp_path / PREDICTIONS_FILE))
    assert len(records) == 5
    assert sum(summary.parse_status_counts.values()) == 5


def test_every_result_carries_a_stable_unique_trace_id(tmp_path: Path) -> None:
    make_runner(tmp_path).run(make_records(5))
    ids = [r["trace_id"] for r in read_jsonl(tmp_path / PREDICTIONS_FILE)]

    assert ids == [make_record_id("AG2_GSM_Plus_Claude", i) for i in range(5)]
    assert len(set(ids)) == 5


def test_trace_id_is_unique_across_runs_that_share_a_trace_index(
    tmp_path: Path,
) -> None:
    """trace_index collides across source runs; the record id must not."""
    records = make_records(3, "AG2_GSM_Plus_Claude") + make_records(3, "ChatDev_MMLU_GPT4o")
    make_runner(tmp_path).run(records)

    ids = [r["trace_id"] for r in read_jsonl(tmp_path / PREDICTIONS_FILE)]
    indexes = [r["trace_index"] for r in read_jsonl(tmp_path / PREDICTIONS_FILE)]
    assert len(set(ids)) == 6
    assert len(set(indexes)) == 3


def test_partial_results_survive_an_interrupted_run(tmp_path: Path) -> None:
    records = make_records(6)

    class StopAfterThree(StubJudge):
        def __init__(self) -> None:
            super().__init__()
            self.n = 0

        def judge(self, prompt: str) -> JudgeCall:
            if self.n >= 3:
                raise KeyboardInterrupt
            self.n += 1
            return super().judge(prompt)

    with pytest.raises(KeyboardInterrupt):
        make_runner(tmp_path, judge=StopAfterThree()).run(records)

    assert len(list(read_jsonl(tmp_path / PREDICTIONS_FILE))) == 3


def test_restart_resumes_without_duplicating_completed_predictions(
    tmp_path: Path,
) -> None:
    records = make_records(6)

    class StopAfterThree(StubJudge):
        def __init__(self) -> None:
            super().__init__()
            self.n = 0

        def judge(self, prompt: str) -> JudgeCall:
            if self.n >= 3:
                raise KeyboardInterrupt
            self.n += 1
            return super().judge(prompt)

    with pytest.raises(KeyboardInterrupt):
        make_runner(tmp_path, judge=StopAfterThree()).run(records)

    summary = make_runner(tmp_path).run(records)

    assert summary.skipped == 3
    assert summary.succeeded == 3
    ids = [r["trace_id"] for r in read_jsonl(tmp_path / PREDICTIONS_FILE)]
    assert len(ids) == 6
    assert len(set(ids)) == 6


def test_resume_is_byte_identical_to_an_uninterrupted_run(tmp_path: Path) -> None:
    records = make_records(6)

    class StopAfterThree(StubJudge):
        def __init__(self) -> None:
            super().__init__()
            self.n = 0

        def judge(self, prompt: str) -> JudgeCall:
            if self.n >= 3:
                raise KeyboardInterrupt
            self.n += 1
            return super().judge(prompt)

    split = tmp_path / "split"
    with pytest.raises(KeyboardInterrupt):
        make_runner(split, judge=StopAfterThree()).run(records)
    make_runner(split).run(records)

    whole = tmp_path / "whole"
    make_runner(whole).run(records)

    def labels(path: Path) -> list[Any]:
        return [(r["trace_id"], r["labels"]) for r in read_jsonl(path / PREDICTIONS_FILE)]

    assert labels(split) == labels(whole)


def test_truncated_final_line_is_tolerated_on_resume(tmp_path: Path) -> None:
    make_runner(tmp_path).run(make_records(3))
    path = tmp_path / PREDICTIONS_FILE
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"run_id": "run-test-001", "trace_id": "AG2_GSM_Plus_Cla')

    assert len(completed_record_ids(tmp_path)) == 3
    summary = make_runner(tmp_path).run(make_records(4))
    assert summary.skipped == 3
    assert summary.succeeded == 1


def test_failed_items_are_recorded_and_identifiable(tmp_path: Path) -> None:
    judge = FlakyJudge({"trace 2"})
    summary = make_runner(tmp_path, judge=judge).run(make_records(4))

    assert summary.succeeded == 3
    assert summary.failed == 1
    assert failed_record_ids(tmp_path) == [make_record_id("AG2_GSM_Plus_Claude", 2)]
    failures = list(read_jsonl(tmp_path / FAILURES_FILE))
    assert failures[0]["error"] == "upstream 503"


def test_failed_items_are_retryable_without_redoing_successes(tmp_path: Path) -> None:
    judge = FlakyJudge({"trace 2"}, fail_times=3)
    make_runner(tmp_path, judge=judge).run(make_records(4))
    assert failed_record_ids(tmp_path) == [make_record_id("AG2_GSM_Plus_Claude", 2)]

    healthy = make_runner(tmp_path, judge=StubJudge())
    summary = healthy.run(make_records(4), only=failed_record_ids(tmp_path))

    assert summary.attempted == 1
    assert summary.succeeded == 1
    assert failed_record_ids(tmp_path) == []
    ids = [r["trace_id"] for r in read_jsonl(tmp_path / PREDICTIONS_FILE)]
    assert len(ids) == len(set(ids)) == 4


def test_retries_are_counted_and_exhausted(tmp_path: Path) -> None:
    judge = FlakyJudge({"trace 0"}, fail_times=1)
    make_runner(tmp_path, judge=judge, max_retries=2).run(make_records(1))

    record = next(iter(read_jsonl(tmp_path / PREDICTIONS_FILE)))
    assert record["retry_count"] == 1


def test_adapter_exception_becomes_a_structured_failure(tmp_path: Path) -> None:
    summary = make_runner(tmp_path, judge=ExplodingJudge()).run(make_records(2))

    assert summary.failed == 2
    assert summary.succeeded == 0
    failures = list(read_jsonl(tmp_path / FAILURES_FILE))
    assert all("socket closed" in f["error"] for f in failures)


def test_raw_and_parsed_outputs_stay_linked(tmp_path: Path) -> None:
    make_runner(tmp_path).run(make_records(1))
    record = next(iter(read_jsonl(tmp_path / PREDICTIONS_FILE)))

    assert record["raw_response"].startswith("A. Deterministic stub verdict")
    assert record["parse_status"] == "ok"
    assert set(record["labels"]) == set(MAST_CODES)
    assert record["raw_type"] == "str"


def test_record_carries_full_version_provenance(tmp_path: Path) -> None:
    make_runner(tmp_path).run(make_records(1))
    record = next(iter(read_jsonl(tmp_path / PREDICTIONS_FILE)))

    assert record["prompt_version"] == "mast-judge-v1"
    assert record["parser_version"] == "mast-parser-v1"
    assert record["dataset_sha256"] == DATASET_SHA
    assert record["model_id"] == "stub-judge-v1"
    assert record["run_id"] == "run-test-001"


def test_reference_source_is_recorded_on_every_prediction(tmp_path: Path) -> None:
    """Prevents LLM-judge labels being read as human ground truth (DAT-30)."""
    make_runner(tmp_path).run(make_records(1))
    record = next(iter(read_jsonl(tmp_path / PREDICTIONS_FILE)))

    assert record["reference_source"] == "released_llm_annotation"
    assert set(record["human_labels"]) == set(MAST_CODES)


def _write_manifest(tmp_path: Path, scorable: int, excluded: list[dict[str, Any]]) -> Path:
    manifest = {
        "manifest_version": "1.0.0",
        "dataset": {"files": [{"filename": "ds.json", "sha256": DATASET_SHA}]},
        "reference_sources": [
            {
                "reference_type": "released_llm_annotation",
                "label_field": "mast_annotation",
                "excluded_records": excluded,
                "scorable_record_count": scorable,
            }
        ],
    }
    path = tmp_path / "eval_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _write_dataset(tmp_path: Path, rows: list[dict[str, Any]]) -> Path:
    path = tmp_path / "ds.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def _row(key: str, idx: int) -> dict[str, Any]:
    return {
        "mas_name": "ChatDev",
        "llm_name": "CodeLlama",
        "benchmark_name": "ProgramDev-v2",
        "trace_id": idx,
        "trace": {"key": key, "index": idx, "trajectory": f"log {key} {idx}"},
        "mast_annotation": {code: 0 for code in MAST_CODES},
    }


def test_loader_applies_the_manifest_exclusion_list(tmp_path: Path) -> None:
    rows = [_row("ChatDev_ProgramDev-v2_CodeLlama", i) for i in range(5)]
    dataset = _write_dataset(tmp_path, rows)
    manifest = _write_manifest(
        tmp_path,
        scorable=3,
        excluded=[
            {"trace_key": "ChatDev_ProgramDev-v2_CodeLlama", "trace_id": 1},
            {"trace_key": "ChatDev_ProgramDev-v2_CodeLlama", "trace_id": 4},
        ],
    )

    records = load_eval_records(manifest, dataset)

    assert [r.trace_index for r in records] == [0, 2, 3]


def test_loader_refuses_a_set_that_contradicts_the_frozen_manifest(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(tmp_path, [_row("k", i) for i in range(5)])
    manifest = _write_manifest(tmp_path, scorable=99, excluded=[])

    with pytest.raises(ValueError, match="scorable_record_count"):
        load_eval_records(manifest, dataset)


def test_loader_rejects_an_unknown_reference_type(tmp_path: Path) -> None:
    dataset = _write_dataset(tmp_path, [_row("k", 0)])
    manifest = _write_manifest(tmp_path, scorable=1, excluded=[])

    with pytest.raises(ValueError, match="reference_type"):
        load_eval_records(manifest, dataset, reference_type="human_consensus")
