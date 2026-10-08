"""MAST judge prompt template tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import models.baseline_mast.prompt as prompt_mod
from models.baseline_mast.prompt import (
    MAX_TRACE_CHARS,
    PROMPT_FILE,
    PROMPT_SHA256,
    PROMPT_VERSION,
    TRACE_TOKEN,
    UPSTREAM_COMMIT,
    build_messages,
    load_template,
    prompt_metadata,
    render_prompt,
    truncate_trace,
    was_truncated,
)


def test_template_hash_matches_upstream() -> None:
    raw = PROMPT_FILE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == PROMPT_SHA256
    assert load_template().count(TRACE_TOKEN) == 1


def test_golden_render_matches_upstream() -> None:
    rendered = render_prompt("<<TRACE>>")
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    assert len(rendered) == 83204
    assert digest == PROMPT_SHA256


def test_single_user_message_no_system() -> None:
    messages = build_messages("sample trace")
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert "content" in messages[0]
    roles = {m["role"] for m in messages}
    assert "system" not in roles


def test_section_order() -> None:
    # Exact markers confirmed against judge_prompt.txt via Path.read_text.
    answer = "*** begin of things you should answer ***"
    trace_heading = "Here is the trace"
    definitions = "1.1 Disobey Task Specification: \nThis error"
    examples = "BELOW ARE THE EXAMPLES"
    body = "SECTION_ORDER_TRACE_BODY"
    text = render_prompt(body)
    assert text.index(answer) < text.index(trace_heading)
    assert text.index(trace_heading) < text.index(body)
    assert text.index(body) < text.index(definitions)
    assert text.index(definitions) < text.index(examples)


def test_trace_with_token_text_not_reexpanded() -> None:
    trace = "start<<TRACE>>mid<<TRACE>>end"
    text = render_prompt(trace)
    assert trace in text
    assert text.count(TRACE_TOKEN) == 2


def test_truncation_matches_upstream() -> None:
    assert MAX_TRACE_CHARS == 981101
    long_trace = "a" * (MAX_TRACE_CHARS + 50)
    truncated = truncate_trace(long_trace)
    assert len(truncated) == MAX_TRACE_CHARS
    assert was_truncated(long_trace) is True
    short = "short"
    assert truncate_trace(short) == short
    assert was_truncated(short) is False


def test_quirks_preserved() -> None:
    text = load_template()
    assert "behaviour.There are several" in text
    # Exact spacing taken from judge_prompt.txt (trailing space before \n).
    assert "1.6 yes \n" in text
    assert "2.7 no \n" in text


def test_tampered_template_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tampered = tmp_path / "judge_prompt.txt"
    data = bytearray(PROMPT_FILE.read_bytes())
    data[0] = (data[0] + 1) % 256
    tampered.write_bytes(bytes(data))
    monkeypatch.setattr(prompt_mod, "PROMPT_FILE", tampered)
    with pytest.raises(ValueError):
        load_template()


def test_deterministic_render() -> None:
    trace = "deterministic-trace-body"
    assert render_prompt(trace) == render_prompt(trace)


def test_metadata_fields() -> None:
    meta = prompt_metadata()
    assert meta["prompt_version"] == PROMPT_VERSION
    assert meta["prompt_sha256"] == PROMPT_SHA256
    assert meta["upstream_commit"] == UPSTREAM_COMMIT
    assert meta["max_trace_chars"] == MAX_TRACE_CHARS
    assert meta["reference_model"] == "o1"
    assert meta["reference_temperature"] == 1.0
