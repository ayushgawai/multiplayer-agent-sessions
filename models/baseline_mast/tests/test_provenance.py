"""Tests for MAST run manifests and provenance capture.

Linear: DAT-35 (MAST 11). Owner: Shriram Dundigalla.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.baseline_mast.provenance import (
    REDACTED,
    RUN_MANIFEST_FILE,
    build_run_manifest,
    environment_provenance,
    git_provenance,
    manifest_provenance,
    missing_manifest_fields,
    parse_status_paths,
    redact,
    write_run_manifest,
)
from models.baseline_mast.run_batch import BatchRunner, StubJudge
from models.baseline_mast.tests.test_run_batch import DATASET_SHA, make_records

LEAKY_SETTINGS: dict[str, Any] = {
    "temperature": 1.0,
    "api_key": "sk-abcdefghijklmnopqrstuvwxyz0123",
    "nested": {"Authorization": "Bearer abc123", "max_tokens": 4096},
    "note": "contact via lin_api_EXAMPLE0000EXAMPLE0000EXAMPLE",
    "headers": ["x-trace: ok", "ghp_abcdefghijklmnopqrstuvwxyz012345"],
}


def _summary(result_dir: Path) -> Any:
    runner = BatchRunner(
        judge=StubJudge(),
        result_dir=result_dir,
        dataset_version="test-v1",
        dataset_sha256=DATASET_SHA,
        run_id="run-test-001",
        log=lambda _m: None,
    )
    return runner.run(make_records(3))


def _manifest_file(tmp_path: Path) -> Path:
    path = tmp_path / "eval_manifest.json"
    path.write_text(
        json.dumps(
            {
                "manifest_version": "1.0.0",
                "status": "FROZEN",
                "linear": "DAT-30 (MAST 06)",
            }
        ),
        encoding="utf-8",
    )
    return path


def _build(tmp_path: Path, settings: dict[str, Any] | None = None) -> dict[str, Any]:
    result_dir = tmp_path / "run"
    summary = _summary(result_dir)
    return build_run_manifest(
        run_id="run-test-001",
        model_id="stub-judge-v1",
        model_settings=settings if settings is not None else {"temperature": 1.0},
        dataset_path=tmp_path / "MAD_full_dataset.json",
        dataset_sha256=DATASET_SHA,
        dataset_revision="95118ac951421753cf1deb87ddea3b01e693c41b",
        eval_manifest_path=_manifest_file(tmp_path),
        reference_source="released_llm_annotation",
        summary=summary,
        result_dir=result_dir,
    )


def test_manifest_records_code_dataset_manifest_prompt_and_model_versions(
    tmp_path: Path,
) -> None:
    manifest = _build(tmp_path)

    assert manifest["git_sha"]
    assert manifest["dataset_sha256"] == DATASET_SHA
    assert manifest["dataset_revision"] == "95118ac951421753cf1deb87ddea3b01e693c41b"
    assert manifest["eval_manifest_version"] == "1.0.0"
    assert manifest["eval_manifest_status"] == "FROZEN"
    assert manifest["prompt_version"] == "mast-judge-v1"
    assert manifest["prompt_sha256"]
    assert manifest["parser_version"] == "mast-parser-v1"
    assert manifest["model_id"] == "stub-judge-v1"


def test_manifest_has_no_missing_required_fields(tmp_path: Path) -> None:
    assert missing_manifest_fields(_build(tmp_path)) == []


def test_manifest_records_timing_outcome_and_token_usage(tmp_path: Path) -> None:
    manifest = _build(tmp_path)

    assert manifest["start_time_utc"] and manifest["end_time_utc"]
    assert manifest["attempted"] == 3
    assert manifest["succeeded"] == 3
    assert manifest["failed"] == 0
    assert sum(manifest["parse_status_counts"].values()) == 3
    assert manifest["prompt_tokens"] is not None
    assert manifest["completion_tokens"] is not None


def test_manifest_points_at_raw_and_parsed_output_locations(tmp_path: Path) -> None:
    manifest = _build(tmp_path)

    assert manifest["predictions_file"] == "predictions.jsonl"
    assert manifest["failures_file"] == "failures.jsonl"
    assert manifest["raw_response_field"] == "raw_response"
    assert manifest["parsed_labels_field"] == "labels"
    assert manifest["record_key_field"] == "trace_id"


def test_no_secret_values_reach_the_manifest(tmp_path: Path) -> None:
    manifest = _build(tmp_path, LEAKY_SETTINGS)
    blob = json.dumps(manifest)

    assert "sk-abcdefghijklmnopqrstuvwxyz0123" not in blob
    assert "Bearer abc123" not in blob
    assert "lin_api_EXAMPLE0000EXAMPLE0000EXAMPLE" not in blob
    assert "ghp_abcdefghijklmnopqrstuvwxyz012345" not in blob
    assert manifest["model_settings"]["temperature"] == 1.0
    assert manifest["model_settings"]["nested"]["max_tokens"] == 4096


def test_redact_handles_keys_values_and_nesting() -> None:
    out = redact(
        {
            "api_key": "harmless-looking",
            "deep": [{"password": "x"}, "sk-abcdefghijklmnopqrstuvwxyz0123"],
            "keep": "plain text",
            "count": 7,
        }
    )

    assert out["api_key"] == REDACTED
    assert out["deep"][0]["password"] == REDACTED
    assert out["deep"][1] == REDACTED
    assert out["keep"] == "plain text"
    assert out["count"] == 7


def test_token_count_settings_are_not_mistaken_for_credentials() -> None:
    """max_tokens and friends are provenance, not secrets."""
    out = redact(
        {
            "max_tokens": 4096,
            "prompt_tokens": 120,
            "completion_tokens": 31,
            "total_tokens": 151,
            "token": "should-go",
            "access_token": "should-go",
        }
    )

    assert out["max_tokens"] == 4096
    assert out["prompt_tokens"] == 120
    assert out["completion_tokens"] == 31
    assert out["total_tokens"] == 151
    assert out["token"] == REDACTED
    assert out["access_token"] == REDACTED


def test_git_provenance_reports_commit_branch_and_cleanliness() -> None:
    prov = git_provenance()

    assert prov["git_sha"] and len(prov["git_sha"]) == 40
    assert prov["git_branch"]
    assert isinstance(prov["git_dirty"], bool)


def test_status_paths_keep_their_first_character() -> None:
    """The leading status column is significant; it must not be stripped."""
    status = (
        " M models/baseline_mast/run_batch.py\n"
        "?? models/baseline_mast/provenance.py\n"
        "M  docs/verification/notes.md\n"
        "R  old/path.py -> new/path.py\n"
    )

    assert parse_status_paths(status) == [
        "models/baseline_mast/run_batch.py",
        "models/baseline_mast/provenance.py",
        "docs/verification/notes.md",
        "old/path.py -> new/path.py",
    ]


def test_dirty_file_paths_are_reported_intact(tmp_path: Path) -> None:
    prov = git_provenance()

    assert all(not p.startswith("odels/") for p in prov["git_dirty_files"])
    assert all(p == p.lstrip() for p in prov["git_dirty_files"])


def test_environment_provenance_records_python_and_platform() -> None:
    env = environment_provenance()

    assert env["python_version"].startswith("3.")
    assert env["platform"]


def test_manifest_provenance_survives_a_missing_file(tmp_path: Path) -> None:
    prov = manifest_provenance(tmp_path / "nope.json")

    assert prov["eval_manifest_version"] is None


def test_write_run_manifest_is_atomic_and_leaves_no_temp_file(
    tmp_path: Path,
) -> None:
    manifest = _build(tmp_path)
    result_dir = tmp_path / "out"

    path = write_run_manifest(result_dir, manifest)

    assert path.name == RUN_MANIFEST_FILE
    assert json.loads(path.read_text(encoding="utf-8"))["run_id"] == "run-test-001"
    assert list(result_dir.glob("*.tmp")) == []


def test_a_teammate_can_tie_any_prediction_back_to_the_run(tmp_path: Path) -> None:
    """Every prediction's run_id resolves to exactly one run manifest."""
    result_dir = tmp_path / "run"
    summary = _summary(result_dir)
    manifest = build_run_manifest(
        run_id=summary.run_id,
        model_id="stub-judge-v1",
        model_settings={"temperature": 1.0},
        dataset_path=tmp_path / "ds.json",
        dataset_sha256=DATASET_SHA,
        dataset_revision=None,
        eval_manifest_path=_manifest_file(tmp_path),
        reference_source="released_llm_annotation",
        summary=summary,
        result_dir=result_dir,
    )
    write_run_manifest(result_dir, manifest)

    written = json.loads(
        (result_dir / RUN_MANIFEST_FILE).read_text(encoding="utf-8")
    )
    predictions = [
        json.loads(line)
        for line in (result_dir / "predictions.jsonl").read_text().splitlines()
    ]

    assert predictions
    for record in predictions:
        assert record["run_id"] == written["run_id"]
        assert record["prompt_version"] == written["prompt_version"]
        assert record["parser_version"] == written["parser_version"]
        assert record["model_id"] == written["model_id"]
        assert record["trace_id"]
