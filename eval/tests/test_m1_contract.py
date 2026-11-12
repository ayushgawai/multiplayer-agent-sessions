"""Contract tests for the frozen M1 experiment and candidate matrix."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from eval.contracts.m1 import (
    M1Claim,
    M1Event,
    M1Input,
    M1MemoryItem,
    M1Output,
    project_m1_output_text,
    qmsum_row_to_m1_input,
    session_event_to_m1_event,
    validate_m1_pair,
)

REPO_ROOT = Path(__file__).parents[2]
CONFIG_DIR = REPO_ROOT / "eval" / "configs"
CANDIDATE_IDS = ("m1-a", "m1-b", "m1-c", "m1-d")


def _input() -> M1Input:
    return M1Input(
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
            ),
            M1Event(
                event_id="event-2",
                sequence=2,
                event_type="instruction",
                actor_id="human-1",
                text="Publish the verified report.",
            ),
        ],
        memory_version="memory-v3",
        approved_memory=[
            M1MemoryItem(
                learning_event_id="lesson-1",
                text="Always retain explicit blockers.",
            )
        ],
    )


def test_output_evidence_and_projection_follow_frozen_contract() -> None:
    model_input = _input()
    model_output = M1Output(
        example_id="example-1",
        candidate_id="m1-c",
        completed=[
            M1Claim(
                text="  The evaluation   passed. ",
                source_event_ids=["event-1"],
            )
        ],
        pending_actions=[
            M1Claim(
                text="Publish the verified report.",
                source_event_ids=["event-2"],
            )
        ],
    )

    validate_m1_pair(model_input, model_output)

    assert model_output.schema_version == "m1-output-v1"
    assert project_m1_output_text(model_output) == (
        "The evaluation passed.\nPublish the verified report."
    )


def test_unknown_source_event_is_rejected() -> None:
    model_output = M1Output(
        example_id="example-1",
        candidate_id="m1-d",
        blocked=[M1Claim(text="GPU is unavailable.", source_event_ids=["missing-event"])],
    )

    with pytest.raises(ValueError, match="unknown source_event_ids"):
        validate_m1_pair(_input(), model_output)


def test_input_requires_ordered_unique_events_and_versioned_memory() -> None:
    with pytest.raises(ValidationError, match="ascending order"):
        M1Input(
            example_id="example-1",
            session_id="session-1",
            query="What changed?",
            events=[
                M1Event(event_id="e2", sequence=2, event_type="tool_result", text="Two"),
                M1Event(event_id="e1", sequence=1, event_type="tool_result", text="One"),
            ],
        )

    with pytest.raises(ValidationError, match="memory_version is required"):
        M1Input(
            example_id="example-1",
            session_id="session-1",
            query="What changed?",
            events=[M1Event(event_id="e1", sequence=1, event_type="tool_result", text="One")],
            approved_memory=[M1MemoryItem(learning_event_id="l1", text="Retain blockers")],
        )


def test_output_forbids_unversioned_fields_and_empty_evidence() -> None:
    with pytest.raises(ValidationError):
        M1Output.model_validate(
            {
                "example_id": "example-1",
                "candidate_id": "m1-a",
                "summary": "legacy free-form output",
            }
        )

    with pytest.raises(ValidationError):
        M1Claim(text="A claim", source_event_ids=[])


def test_input_rejects_unknown_event_type() -> None:
    with pytest.raises(ValidationError, match="event_type"):
        M1Event.model_validate(
            {"event_id": "e1", "sequence": 1, "event_type": "result", "text": "One"}
        )


def test_session_event_adapter_handles_events_without_payload_text() -> None:
    base = {
        "event_id": "evt-1",
        "session_id": "session-1",
        "seq": 1,
        "actor": {"id": "p-1", "display_name": "Ada"},
    }

    joined = session_event_to_m1_event(
        {**base, "type": "join", "payload": {"display_name": "Ada", "role": "author"}}
    )
    left = session_event_to_m1_event({**base, "type": "leave", "payload": {}})
    rejected = session_event_to_m1_event(
        {
            **base,
            "type": "rejected",
            "payload": {"attempted_type": "instruction", "reason": "observer cannot write"},
        }
    )

    assert joined.text == "Ada joined the session as author."
    assert left.text == "Ada left the session."
    assert rejected.text == "Rejected instruction: observer cannot write."


def test_qmsum_adapter_builds_split_scoped_session_and_stable_events() -> None:
    row = {
        "id": "qmsum_val_4_s0",
        "query": "What changed?",
        "context_spans": ["A: First", "B: Second"],
        "reference_summary": "First and second changed.",
    }

    model_input = qmsum_row_to_m1_input(row)

    assert model_input.session_id == "qmsum:val:4"
    assert [event.event_id for event in model_input.events] == [
        "qmsum_val_4_s0:span:0000",
        "qmsum_val_4_s0:span:0001",
    ]
    assert [event.sequence for event in model_input.events] == [0, 1]
    assert {event.event_type for event in model_input.events} == {"doc_update"}


def test_candidate_configs_share_schema_order_metrics_and_failure_codes() -> None:
    configs = [
        yaml.safe_load((CONFIG_DIR / f"{candidate_id}.yaml").read_text(encoding="utf-8"))
        for candidate_id in CANDIDATE_IDS
    ]

    expected_keys = list(configs[0])
    for candidate_id, config in zip(CANDIDATE_IDS, configs, strict=True):
        assert list(config) == expected_keys
        assert config["candidate_id"] == candidate_id
        assert config["contract"] == "eval/configs/m1-contract.yaml"
        assert config["evaluation_split"] == "data/splits/m1_session_v1/"
        assert config["schemas"] == {"input": "m1-input-v1", "output": "m1-output-v1"}
        assert config["seeds"] == [13, 29, 47]
        assert config["metrics"] == configs[0]["metrics"]
        assert config["failure_codes"] == configs[0]["failure_codes"]
        assert config["primary_metric"] == "critical_fact_recall"


def test_candidate_matrix_and_revisions_are_the_approved_four() -> None:
    configs = {
        candidate_id: yaml.safe_load(
            (CONFIG_DIR / f"{candidate_id}.yaml").read_text(encoding="utf-8")
        )
        for candidate_id in CANDIDATE_IDS
    }

    assert configs["m1-a"]["trainer"] == "bm25_template"
    assert configs["m1-a"]["model"] == {"repo": None, "revision": None}
    assert configs["m1-a"]["train"] is None
    assert configs["m1-b"]["trainer"] == "encoder_selector"
    assert configs["m1-b"]["model"] == {
        "repo": "answerdotai/ModernBERT-base",
        "revision": "8949b909ec900327062f0ebf497f51aef5e6f0c8",
    }
    assert configs["m1-c"]["trainer"] == "causal_lm_qlora"
    assert configs["m1-c"]["model"] == {
        "repo": "microsoft/Phi-4-mini-instruct",
        "revision": "cfbefacb99257ffa30c83adab238a50856ac3083",
    }
    assert configs["m1-d"]["trainer"] == "conditional_generation_qlora"
    assert configs["m1-d"]["model"] == {
        "repo": "Qwen/Qwen3.5-4B",
        "revision": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
    }

    shared_train_fields = ("epochs", "max_seq_len", "effective_batch_size")
    for field in shared_train_fields:
        values = {
            configs[candidate_id]["train"][field]
            for candidate_id in ("m1-b", "m1-c", "m1-d")
        }
        assert len(values) == 1


def test_selection_contract_has_safety_gates_and_no_test_memory_leakage() -> None:
    contract = yaml.safe_load((CONFIG_DIR / "m1-contract.yaml").read_text(encoding="utf-8"))

    assert contract["seeds"] == [13, 29, 47]
    assert contract["split"]["candidate_selection_split"] == "session_test"
    assert contract["fairness"]["candidate_selection_condition"] == "memory_disabled"
    assert contract["fairness"]["test_feedback_may_enter_memory"] is False
    assert contract["selection"]["eligibility_gate_aggregation"] == "every_seed"
    assert contract["selection"]["baseline_comparison"] == "matched_seed"
    assert contract["selection"]["eligible_if"] == {
        "all_three_seed_runs_complete": True,
        "schema_valid_rate_min": 0.98,
        "unsupported_claim_rate_max": 0.02,
        "unsupported_claim_rate_no_worse_than_m1_a": True,
        "attribution_accuracy_min": 0.95,
        "status_consistency_min": 0.95,
    }
    assert contract["selection"]["rank_eligible_by"][0] == "critical_fact_recall"
    assert contract["selection"]["rank_aggregation"] == "mean_across_three_seeds"
    assert contract["selection"]["tie_policy"] == "retain_within_margin_of_stage_best"
    assert contract["selection"]["quality_tie_margins"] == {
        "critical_fact_recall": 0.01,
        "bertscore_f1": 0.01,
        "rouge_l": 1.0,
    }
    for metric, margin in contract["selection"]["quality_tie_margins"].items():
        scale = contract["metrics"][metric]["scale"]
        expected_margin = 1.0 if scale == "percentage_0_100" else 0.01
        assert margin == expected_margin
    assert contract["metrics"]["bertscore_f1"] == {
        "direction": "maximize",
        "scale": "unit_interval",
        "library": "bert-score==0.3.13",
        "model_repo": "FacebookAI/roberta-large",
        "model_revision": "722cf37b1afa9454edce342e7895e588b6ff1d59",
        "num_layers": 17,
        "idf": False,
        "rescale_with_baseline": False,
        "definition": "macro_f1_across_examples",
    }


def test_qmsum_manifest_matches_files_and_split_ids_do_not_overlap() -> None:
    split_dir = REPO_ROOT / "data" / "splits" / "m1_v1"
    manifest = json.loads((split_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    ids_by_split: dict[str, set[str]] = {}
    meeting_fingerprints_by_split: dict[str, set[str]] = {}

    for split_name, expected in manifest["splits"].items():
        split_path = split_dir / f"{split_name}.jsonl"
        payload = split_path.read_bytes().replace(b"\r\n", b"\n")
        rows = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line]
        ids_by_split[split_name] = {row["id"] for row in rows}
        rows_by_meeting: dict[str, list[dict[str, object]]] = {}
        for row in rows:
            meeting_index = row["id"].split("_")[2]
            rows_by_meeting.setdefault(meeting_index, []).append(
                {
                    "query": row["query"],
                    "context_spans": row["context_spans"],
                    "reference_summary": row["reference_summary"],
                }
            )
        meeting_fingerprints_by_split[split_name] = {
            hashlib.sha256(
                json.dumps(
                    sorted(meeting_rows, key=lambda item: str(item["query"])),
                    ensure_ascii=False,
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            for meeting_rows in rows_by_meeting.values()
        }
        assert len(rows) == expected["count"]
        assert len(ids_by_split[split_name]) == expected["count"]
        assert hashlib.sha256(payload).hexdigest() == expected["sha256"]

    assert ids_by_split["train"].isdisjoint(ids_by_split["val"])
    assert ids_by_split["train"].isdisjoint(ids_by_split["test"])
    assert ids_by_split["val"].isdisjoint(ids_by_split["test"])
    assert meeting_fingerprints_by_split["train"].isdisjoint(
        meeting_fingerprints_by_split["val"]
    )
    assert meeting_fingerprints_by_split["train"].isdisjoint(
        meeting_fingerprints_by_split["test"]
    )
    assert meeting_fingerprints_by_split["val"].isdisjoint(
        meeting_fingerprints_by_split["test"]
    )


def test_validate_pair_rejects_identity_mismatch_and_duplicate_claims() -> None:
    with pytest.raises(ValueError, match="example_id values must match"):
        validate_m1_pair(
            _input(),
            M1Output(example_id="other", candidate_id="m1-a"),
        )

    duplicate = M1Claim(text="The evaluation passed.", source_event_ids=["event-1"])
    with pytest.raises(ValueError, match="duplicate claims"):
        validate_m1_pair(
            _input(),
            M1Output(
                example_id="example-1",
                candidate_id="m1-a",
                completed=[duplicate],
                decisions=[duplicate],
            ),
        )


def test_validate_pair_allows_zero_claim_output_but_metrics_must_make_it_ineligible() -> None:
    validate_m1_pair(_input(), M1Output(example_id="example-1", candidate_id="m1-a"))
