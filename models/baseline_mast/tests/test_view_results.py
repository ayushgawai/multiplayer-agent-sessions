"""MAST result viewer tests."""

from __future__ import annotations

import json
from pathlib import Path

from models.baseline_mast.view_results import (
    OUTCOME_FN,
    OUTCOME_FP,
    OUTCOME_NA,
    OUTCOME_TN,
    OUTCOME_TP,
    STATUS_UNREADABLE,
    build_html,
    compare,
    disagreement_count,
    load_records,
    main,
    status_counts,
)

SAMPLE = (
    Path(__file__).parent / "fixtures" / "sample_run" / "predictions.jsonl"
)
MANIFEST = (
    Path(__file__).parent / "fixtures" / "sample_run" / "run_manifest.json"
)


def test_compare_outcomes() -> None:
    assert compare(True, True) == OUTCOME_TP
    assert compare(False, True) == OUTCOME_FP
    assert compare(True, False) == OUTCOME_FN
    assert compare(False, False) == OUTCOME_TN
    assert compare(None, True) == OUTCOME_NA
    assert compare(False, None) == OUTCOME_NA
    assert compare(None, None) == OUTCOME_NA


def test_disagreement_counts_per_trace() -> None:
    records = load_records(SAMPLE)
    by_id = {r["trace_id"]: disagreement_count(r) for r in records}
    assert by_id["trace-agree-01"] == 0
    assert by_id["trace-agree-02"] == 0
    assert by_id["trace-disagree-01"] > 0
    assert by_id["trace-disagree-02"] > 0


def test_header_parse_status_counts() -> None:
    records = load_records(SAMPLE)
    counts = status_counts(records)
    assert counts.get("ok") == 4
    assert counts.get("empty") == 1
    assert counts.get("malformed") == 1
    page = build_html(
        records, json.loads(MANIFEST.read_text(encoding="utf-8"))
    )
    assert "parse_status counts" in page
    assert ">ok</td>" in page or ">ok<" in page


def test_script_payload_escaped() -> None:
    records = load_records(SAMPLE)
    page = build_html(records, None)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_unreadable_jsonl_line() -> None:
    path = Path("/tmp/mast_bad_line.jsonl")
    good = SAMPLE.read_text(encoding="utf-8").splitlines()[0]
    path.write_text(good + "\nNOT_JSON{{{{\n", encoding="utf-8")
    records = load_records(path)
    assert any(
        r.get("parse_status") == STATUS_UNREADABLE for r in records
    )
    page = build_html(records, None)
    assert "unreadable_record" in page
    assert "NOT_JSON" in page


def test_filter_controls_present() -> None:
    records = load_records(SAMPLE)
    page = build_html(records, None)
    assert 'id="f_dis"' in page
    assert 'id="f_bad"' in page
    assert 'id="f_fw"' in page
    assert 'id="f_code"' in page
    assert 'id="f_q"' in page
    assert "disagreements only" in page
    assert "parse problems only" in page


def test_deterministic_output() -> None:
    records = load_records(SAMPLE)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert build_html(records, manifest) == build_html(records, manifest)


def test_cli_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    rc = main(
        [
            "--predictions",
            str(SAMPLE),
            "--manifest",
            str(MANIFEST),
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "MAST result viewer" in text
    assert "trace-agree-01" in text


def _rec(**extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "run_id": "r1",
        "trace_id": "t1",
        "framework": "ChatDev",
        "parse_status": "ok",
        "human_labels": {},
        "labels": {},
    }
    base.update(extra)
    return base


def test_reference_source_in_header_or_unknown() -> None:
    with_src = build_html([_rec(reference_source="released_llm_annotation")], None)
    assert "<b>reference_source</b><br/>released_llm_annotation" in with_src
    without = build_html([_rec()], None)
    assert "<b>reference_source</b><br/>unknown" in without


def test_reference_labels_heading_replaces_human_labels() -> None:
    page = build_html([_rec(reference_source="human_consensus")], None)
    assert "<b>reference labels (human_consensus)</b>" in page
    assert "<b>human_labels</b>" not in page
    assert "human_labels</b>" not in page


def test_trace_key_llm_name_benchmark_escaped() -> None:
    page = build_html(
        [
            _rec(
                trace_key="<i>k</i>",
                llm_name="<b>gpt</b>",
                benchmark="<u>bench</u>",
            )
        ],
        None,
    )
    for raw in ("<i>k</i>", "<b>gpt</b>", "<u>bench</u>"):
        assert raw not in page
    assert "<b>trace_key</b>: &lt;i&gt;k&lt;/i&gt;" in page
    assert "<b>llm_name</b>: &lt;b&gt;gpt&lt;/b&gt;" in page
    assert "<b>benchmark</b>: &lt;u&gt;bench&lt;/u&gt;" in page
