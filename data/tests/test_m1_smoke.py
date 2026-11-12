"""Tests for the deterministic M1 smoke dataset (DAT-53)."""

from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "data" / "scripts"))

import make_m1_smoke as gen  # noqa: E402

from data.m1_smoke import loader  # noqa: E402
from data.m1_smoke.schema import (  # noqa: E402
    CATEGORIES,
    EVENT_TYPES,
    LABEL_TO_CATEGORY,
    M1SmokeExample,
)

FIXTURES = REPO_ROOT / "data" / "m1_smoke" / "fixtures"


def valid_record() -> dict[str, Any]:
    events = [
        {"source_event_id": "t-e001", "sequence": 1, "event_type": "instruction",
         "actor_id": "human-a", "text": "Build the thing."},
        {"source_event_id": "t-e002", "sequence": 2, "event_type": "agent_step",
         "actor_id": "agent-b", "text": "Built the thing."},
        {"source_event_id": "t-e003", "sequence": 3, "event_type": "arbitration",
         "actor_id": None, "text": "Merge selected."},
    ]
    return {
        "example_id": "t-x1",
        "session_id": "t",
        "query": "Catch me up.",
        "events": events,
        "event_labels": {"t-e002": "completed", "t-e003": "decision"},
        "reference": {
            "completed": [{"text": "B built the thing.", "source_event_ids": ["t-e002"]}],
            "decisions": [{"text": "Merge was selected.", "source_event_ids": ["t-e003"]}],
        },
        "critical_facts": [
            {"fact_id": "t-f01", "category": "completed", "text": "thing built",
             "evidence_event_ids": ["t-e002"]}
        ],
    }


@pytest.fixture(scope="module")
def dataset() -> dict[str, list[M1SmokeExample]]:
    return loader.load_fixtures(FIXTURES)


# --- schema ---------------------------------------------------------------------------------


def test_schema_accepts_valid_example() -> None:
    ex = M1SmokeExample.model_validate(valid_record())
    assert ex.events[2].actor_id is None


def _mutate(fn: Any) -> dict[str, Any]:
    rec = copy.deepcopy(valid_record())
    fn(rec)
    return rec


INVALID = {
    "missing source_event_id": lambda r: r["events"][0].pop("source_event_id"),
    "blank source_event_id": lambda r: r["events"][0].update(source_event_id="  "),
    "duplicate event ids": lambda r: r["events"][1].update(source_event_id="t-e001"),
    "unknown event type": lambda r: r["events"][0].update(event_type="chat"),
    "out of order sequence": lambda r: r["events"][1].update(sequence=0),
    "duplicate sequence": lambda r: r["events"][1].update(sequence=1),
    "blank event text": lambda r: r["events"][0].update(text=" "),
    "claim evidence not in events": lambda r: r["reference"]["completed"][0].update(
        source_event_ids=["t-e999"]
    ),
    "claim empty evidence": lambda r: r["reference"]["completed"][0].update(source_event_ids=[]),
    "fact evidence not in events": lambda r: r["critical_facts"][0].update(
        evidence_event_ids=["t-e999"]
    ),
    "fact empty evidence": lambda r: r["critical_facts"][0].update(evidence_event_ids=[]),
    "label for unknown event": lambda r: r["event_labels"].update({"t-e999": "completed"}),
    "claim category contradicts label": lambda r: r["reference"].update(
        blocked=[{"text": "B is stuck.", "source_event_ids": ["t-e002"]}]
    ),
    "fact category contradicts label": lambda r: r["critical_facts"][0].update(category="blocked"),
    "duplicate fact ids": lambda r: r["critical_facts"].append(copy.deepcopy(r["critical_facts"][0])),
    "no claims": lambda r: r.update(reference={}),
    "extra field on example": lambda r: r.update(surprise=1),
    "extra field on event": lambda r: r["events"][0].update(surprise=1),
    "no events": lambda r: r.update(events=[]),
}


@pytest.mark.parametrize("name", sorted(INVALID))
def test_schema_rejects(name: str) -> None:
    with pytest.raises(ValidationError):
        M1SmokeExample.model_validate(_mutate(INVALID[name]))


def test_event_types_match_session_service() -> None:
    path = REPO_ROOT / "session-service" / "app" / "schemas.py"
    spec = importlib.util.spec_from_file_location("_session_schemas", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_session_schemas"] = mod
    spec.loader.exec_module(mod)
    assert {e.value for e in mod.EventType} == set(EVENT_TYPES)


# --- loader ---------------------------------------------------------------------------------


def test_loader_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonl"
    ex = M1SmokeExample.model_validate(valid_record())
    path.write_text(json.dumps(ex.model_dump(mode="json")) + "\n", encoding="utf-8")
    assert loader.load_split(path) == [ex]


def test_loader_accepts_crlf(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonl"
    path.write_bytes((json.dumps(valid_record()) + "\r\n").encode())
    assert len(loader.load_split(path)) == 1


def test_loader_error_missing_file(tmp_path: Path) -> None:
    with pytest.raises(loader.SmokeDataError, match="file not found"):
        loader.load_split(tmp_path / "nope.jsonl")


def test_loader_error_invalid_json_has_line_number(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonl"
    path.write_text(json.dumps(valid_record()) + "\n{not json\n", encoding="utf-8")
    with pytest.raises(loader.SmokeDataError, match=r"x\.jsonl:2: invalid JSON"):
        loader.load_split(path)


def test_loader_error_schema_names_line_and_example(tmp_path: Path) -> None:
    bad = _mutate(INVALID["unknown event type"])
    path = tmp_path / "x.jsonl"
    path.write_text(json.dumps(valid_record()) + "\n" + json.dumps(bad) + "\n", encoding="utf-8")
    with pytest.raises(loader.SmokeDataError, match=r"x\.jsonl:2: example t-x1: events\.0\.event_type"):
        loader.load_split(path)


def test_loader_error_blank_line(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonl"
    path.write_text(json.dumps(valid_record()) + "\n\n", encoding="utf-8")
    with pytest.raises(loader.SmokeDataError, match=r"x\.jsonl:2: blank line"):
        loader.load_split(path)


def test_loader_error_duplicate_example_id(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonl"
    line = json.dumps(valid_record()) + "\n"
    path.write_text(line * 2, encoding="utf-8")
    with pytest.raises(loader.SmokeDataError, match=r"x\.jsonl:2: .*duplicate example_id"):
        loader.load_split(path)


# --- committed fixtures ---------------------------------------------------------------------


def test_fixture_sizes(dataset: dict[str, list[M1SmokeExample]]) -> None:
    assert sum(len(v) for v in dataset.values()) == 18
    assert len({e.session_id for v in dataset.values() for e in v}) == 12
    for examples in dataset.values():
        for ex in examples:
            assert 8 <= len(ex.events) <= 20


def test_event_ids_are_stable_and_readable(dataset: dict[str, list[M1SmokeExample]]) -> None:
    for examples in dataset.values():
        for ex in examples:
            for i, e in enumerate(ex.events, start=1):
                assert e.source_event_id == f"{ex.session_id}-e{i:03d}"


def test_sequences_are_gapless_from_one_like_the_service(
    dataset: dict[str, list[M1SmokeExample]],
) -> None:
    # The live service allocates seq 1, 2, 3, ... and rollback resets the next seq to to_seq + 1.
    for examples in dataset.values():
        for ex in examples:
            assert [e.sequence for e in ex.events] == list(range(1, len(ex.events) + 1))


def test_rollback_sessions_show_only_post_rollback_history(
    dataset: dict[str, list[M1SmokeExample]],
) -> None:
    seen = 0
    for examples in dataset.values():
        for ex in examples:
            texts = " ".join(e.text for e in ex.events)
            assert "Rewrote the pricing section" not in texts  # deleted by the rollback
            rollbacks = [e for e in ex.events if e.event_type == "rollback"]
            if rollbacks:
                seen += 1
                # appended right after the kept prefix, so seq 3 here
                assert rollbacks[0].sequence == 3
    assert seen >= 1


def test_no_split_is_called_test(dataset: dict[str, list[M1SmokeExample]]) -> None:
    assert set(dataset) == {"train", "dev", "smoke_holdout"}
    assert not (FIXTURES / "test.jsonl").exists()
    manifest = json.loads((FIXTURES / "MANIFEST.json").read_text(encoding="utf-8"))
    assert set(manifest["splits"]) == {"train", "dev", "smoke_holdout"}


def test_splits_are_session_disjoint_and_ids_unique(
    dataset: dict[str, list[M1SmokeExample]],
) -> None:
    sessions = {s: {e.session_id for e in v} for s, v in dataset.items()}
    assert not sessions["train"] & sessions["dev"]
    assert not sessions["train"] & sessions["smoke_holdout"]
    assert not sessions["dev"] & sessions["smoke_holdout"]
    example_ids = [e.example_id for v in dataset.values() for e in v]
    assert len(example_ids) == len(set(example_ids))
    event_ids = [ev.source_event_id for v in dataset.values() for e in v for ev in e.events]
    # Events repeat only between examples of the same session (full and joined-late views).
    owner: dict[str, str] = {}
    for v in dataset.values():
        for e in v:
            for ev in e.events:
                assert owner.setdefault(ev.source_event_id, e.session_id) == e.session_id
    assert event_ids


def test_every_split_has_all_categories_and_event_labels(
    dataset: dict[str, list[M1SmokeExample]],
) -> None:
    for split, examples in dataset.items():
        categories = {c for e in examples for c in CATEGORIES if getattr(e.reference, c)}
        assert categories == set(CATEGORIES), split
        labels = {lab for e in examples for lab in e.event_labels.values()}
        assert labels == set(LABEL_TO_CATEGORY), split


def test_every_event_type_used_is_real(dataset: dict[str, list[M1SmokeExample]]) -> None:
    used = {ev.event_type for v in dataset.values() for e in v for ev in e.events}
    assert {"instruction", "agent_step", "tool_call", "tool_result", "interrupt", "handoff",
            "rollback", "doc_update", "arbitration"} <= used


def test_critical_facts_have_existing_evidence(dataset: dict[str, list[M1SmokeExample]]) -> None:
    for examples in dataset.values():
        for ex in examples:
            ids = {e.source_event_id for e in ex.events}
            assert ex.critical_facts, ex.example_id
            for fact in ex.critical_facts:
                assert fact.evidence_event_ids
                assert set(fact.evidence_event_ids) <= ids


# --- determinism and manifest ---------------------------------------------------------------


def test_generation_is_byte_identical(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    gen.write_fixtures(a)
    gen.write_fixtures(b)
    names = ["train.jsonl", "dev.jsonl", "smoke_holdout.jsonl", "MANIFEST.json"]
    for name in names:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name
        assert b"\r" not in (a / name).read_bytes()
        assert str(tmp_path).encode() not in (a / name).read_bytes()


def test_committed_fixtures_match_generator(tmp_path: Path) -> None:
    gen.write_fixtures(tmp_path)
    for name in ("train.jsonl", "dev.jsonl", "smoke_holdout.jsonl", "MANIFEST.json"):
        assert (tmp_path / name).read_bytes() == (FIXTURES / name).read_bytes(), name


def test_different_seed_changes_output(tmp_path: Path) -> None:
    gen.write_fixtures(tmp_path, seed=14)
    assert (tmp_path / "train.jsonl").read_bytes() != (FIXTURES / "train.jsonl").read_bytes()


def test_manifest_hashes_match_files() -> None:
    manifest = json.loads((FIXTURES / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == 13
    assert manifest["split_policy"] == "by session_id"
    assert "created_at" not in json.dumps(manifest)
    for info in manifest["splits"].values():
        data = (FIXTURES / info["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == info["sha256"]
        assert len(data) == info["bytes"]
    loader.verify_manifest(FIXTURES)


def test_verify_manifest_detects_tampering(tmp_path: Path) -> None:
    gen.write_fixtures(tmp_path)
    with (tmp_path / "dev.jsonl").open("ab") as f:
        f.write(b"\n")
    with pytest.raises(loader.SmokeDataError, match="dev"):
        loader.verify_manifest(tmp_path)


# --- conversion -----------------------------------------------------------------------------


def test_to_m1_input_shape(dataset: dict[str, list[M1SmokeExample]]) -> None:
    ex = dataset["train"][0]
    out = loader.to_m1_input(ex)
    assert set(out) == {"schema_version", "example_id", "session_id", "query", "events",
                        "memory_version", "approved_memory"}
    assert out["schema_version"] == "m1-input-v1"
    assert out["memory_version"] is None and out["approved_memory"] == []
    assert set(out["events"][0]) == {"event_id", "sequence", "event_type", "actor_id", "text"}
    assert [e["event_id"] for e in out["events"]] == [e.source_event_id for e in ex.events]


def test_gold_reference_shape(dataset: dict[str, list[M1SmokeExample]]) -> None:
    ref = loader.gold_reference(dataset["train"][0])
    assert ref["schema_version"] == "m1-output-v1"
    assert "candidate_id" not in ref
    assert set(ref) == {"schema_version", "example_id", *CATEGORIES}
    for category in CATEGORIES:
        for claim in ref[category]:
            assert set(claim) == {"text", "source_event_ids"}


# --- DAT-55 contract compatibility (eval/contracts/m1.py is on main) ----------------------


def test_contract_compat(dataset: dict[str, list[M1SmokeExample]]) -> None:
    m1 = importlib.import_module("eval.contracts.m1")
    assert sum(len(examples) for examples in dataset.values()) == 18
    for examples in dataset.values():
        for ex in examples:
            model_input = m1.M1Input.model_validate(loader.to_m1_input(ex))
            ref = loader.gold_reference(ex)
            ref["candidate_id"] = "m1-a"
            model_output = m1.M1Output.model_validate(ref)
            m1.validate_m1_pair(model_input, model_output)
