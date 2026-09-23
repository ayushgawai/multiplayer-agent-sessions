"""MAST judge response parser tests."""

from __future__ import annotations

import json
from pathlib import Path

from models.baseline_mast.parse_judge import (
    MAST_CODES,
    PARSER_VERSION,
    official_labels,
    parse_judge_response,
    to_record_fields,
)

FIX = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_valid_template_format_ok() -> None:
    text = _load("valid_template_format.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "ok"
    assert parsed.predicted_labels == ["1.1", "2.3", "2.6", "3.2"]
    assert parsed.missing_codes == []
    assert parsed.parser_version == PARSER_VERSION


def test_valid_short_format_ok() -> None:
    text = _load("valid_short_format.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "ok"
    assert parsed.predicted_labels == ["1.2", "2.5", "3.3"]


def test_all_yes_fourteen_vs_official_twelve() -> None:
    text = _load("all_yes_template.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "ok"
    assert len(parsed.predicted_labels) == 14
    assert sum(parsed.labels_official.values()) == 12
    assert parsed.labels_official["2.5"] == 0
    assert parsed.labels_official["3.2"] == 0


def test_multi_label_exact_set() -> None:
    text = _load("mixed_multi_label.txt")
    parsed = parse_judge_response(text)
    assert parsed.predicted_labels == ["1.1", "2.3", "2.6", "3.2"]


def test_empty_string() -> None:
    parsed = parse_judge_response("")
    assert parsed.parse_status == "empty"
    assert all(v is None for v in parsed.labels.values())


def test_whitespace_only() -> None:
    parsed = parse_judge_response("   \n\t  ")
    assert parsed.parse_status == "empty"


def test_none_input() -> None:
    parsed = parse_judge_response(None)
    assert parsed.parse_status == "empty"
    assert parsed.raw_response is None
    assert parsed.raw_type == "NoneType"


def test_refusal_malformed() -> None:
    text = _load("refusal.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "malformed"
    assert all(v is None for v in parsed.labels.values())
    assert all(v == 0 for v in parsed.labels_official.values())
    assert len(parsed.labels_official) == 14


def test_missing_codes_partial() -> None:
    text = _load("missing_codes.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "partial"
    assert "2.1" in parsed.missing_codes
    assert len(parsed.missing_codes) == 9


def test_unknown_codes_listed() -> None:
    text = _load("unknown_codes.txt")
    parsed = parse_judge_response(text)
    assert parsed.unknown_codes == ["1.6", "2.7"]
    assert parsed.parse_status == "ok"
    assert parsed.labels["1.1"] is False
    assert parsed.predicted_labels == ["2.3", "2.6", "3.2"]


def test_duplicate_agree_warning_ok() -> None:
    text = _load("duplicate_agree.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "ok"
    assert "duplicate_code:1.1" in parsed.warnings
    assert parsed.labels["1.1"] is True


def test_duplicate_conflict_ambiguous() -> None:
    text = _load("duplicate_conflict.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "ambiguous"
    assert parsed.conflicting_codes == ["1.1"]
    assert parsed.labels["1.1"] is None


def test_echoed_template_ambiguous() -> None:
    text = _load("echoed_template.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "ambiguous"
    assert parsed.ambiguous_codes == list(MAST_CODES)
    assert all(v is None for v in parsed.labels.values())


def test_markdown_bold() -> None:
    text = _load("markdown_bold.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "ok"
    assert parsed.predicted_labels == ["1.2", "2.5", "3.3"]


def test_preamble_and_trailer() -> None:
    text = _load("with_preamble_and_trailer.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "ok"
    assert parsed.predicted_labels == ["1.1", "2.3", "2.6", "3.2"]


def test_json_reply() -> None:
    text = _load("json_reply.txt")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "ok"
    assert "json_format" in parsed.warnings
    assert parsed.predicted_labels == ["1.1", "2.3", "2.6", "3.2"]


def test_dict_input() -> None:
    payload = {code: False for code in MAST_CODES}
    payload["2.3"] = True
    parsed = parse_judge_response(payload)
    assert parsed.raw_type == "dict"
    assert "json_format" in parsed.warnings
    assert parsed.predicted_labels == ["2.3"]
    assert parsed.labels_official == {}


def test_int_input_malformed() -> None:
    parsed = parse_judge_response(42)
    assert parsed.parse_status == "malformed"
    assert "non_string_input" in parsed.warnings
    assert all(v is None for v in parsed.labels.values())


def test_raw_response_byte_for_byte() -> None:
    for path in sorted(FIX.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        parsed = parse_judge_response(text)
        assert parsed.raw_response == text, path.name


def test_deterministic_parse() -> None:
    text = _load("valid_template_format.txt")
    a = parse_judge_response(text)
    b = parse_judge_response(text)
    assert a.model_dump() == b.model_dump()


def test_summary_and_task_completed() -> None:
    text = _load("valid_template_format.txt")
    parsed = parse_judge_response(text)
    assert parsed.summary == (
        "Agents derailed and verification was weak."
    )
    assert parsed.task_completed is False


def test_to_record_fields_json_serializable() -> None:
    text = _load("valid_short_format.txt")
    parsed = parse_judge_response(text)
    blob = json.dumps(to_record_fields(parsed))
    assert "parse_status" in blob


def test_no_silent_false_defaults() -> None:
    text = _load("missing_codes.txt")
    parsed = parse_judge_response(text)
    for code in parsed.missing_codes:
        assert parsed.labels[code] is None
    for code, value in parsed.labels.items():
        if value is False:
            assert f"{code}" in text
            # False only when the text said no for that code.
            assert "no" in text.lower()


def test_official_labels_helper() -> None:
    text = _load("all_yes_template.txt")
    assert sum(official_labels(text).values()) == 12
