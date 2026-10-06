"""Parse MAST LLM-as-a-Judge responses into explicit labels.

Validated labels never silently default missing codes to false. The
labels_official field mirrors the upstream notebook parser for comparison only.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from models.baseline_mast.prompt import PROMPT_VERSION

PARSER_VERSION: str = "mast-parser-v1"

MAST_CODES: tuple[str, ...] = (
    "1.1",
    "1.2",
    "1.3",
    "1.4",
    "1.5",
    "2.1",
    "2.2",
    "2.3",
    "2.4",
    "2.5",
    "2.6",
    "3.1",
    "3.2",
    "3.3",
)

# Names EXACTLY as in the answer template of judge_prompt.txt.
# definitions.txt swaps 3.2 and 3.3; mapping to human labels is pending
# the dataset owner.
MAST_NAMES: dict[str, str] = {
    "1.1": "Disobey Task Specification",
    "1.2": "Disobey Role Specification",
    "1.3": "Step Repetition",
    "1.4": "Loss of Conversation History",
    "1.5": "Unaware of Termination Conditions",
    "2.1": "Conversation Reset",
    "2.2": "Fail to Ask for Clarification",
    "2.3": "Task Derailment",
    "2.4": "Information Withholding",
    "2.5": "Ignored Other Agent's Input",
    "2.6": "Action-Reasoning Mismatch",
    "3.1": "Premature Termination",
    "3.2": "No or Incorrect Verification",
    "3.3": "Weak Verification",
}

ParseStatus = Literal["ok", "partial", "ambiguous", "empty", "malformed"]

_SECTION_C_RE = re.compile(r"^\s*C\s*[\.\):]\s*", re.MULTILINE)
_SECTION_A_RE = re.compile(
    r"^\s*A\s*[\.\):]\s*(.*?)(?=^\s*B\s*[\.\):])",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)
_SECTION_B_RE = re.compile(
    r"^\s*B\s*[\.\):]\s*(.*)$",
    re.MULTILINE | re.IGNORECASE,
)
_CODE_LINE_RE = re.compile(
    r"^\W*(?:C\.)?\s*(\d\.\d)\b(.*)$",
    re.IGNORECASE,
)
_YES_RE = re.compile(r"\byes\b", re.IGNORECASE)
_NO_RE = re.compile(r"\bno\b", re.IGNORECASE)
_FENCE_JSON_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)


class ParsedJudgeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_response: str | None
    raw_type: str
    parser_version: str
    prompt_version: str | None
    parse_status: ParseStatus
    labels: dict[str, bool | None]
    predicted_labels: list[str]
    missing_codes: list[str]
    ambiguous_codes: list[str]
    conflicting_codes: list[str]
    unknown_codes: list[str]
    summary: str | None
    task_completed: bool | None
    warnings: list[str]
    labels_official: dict[str, int] = Field(default_factory=dict)


def official_labels(response: str) -> dict[str, int]:
    """Faithful single-response port of upstream parse_responses (cell 8).

    Kept only to compare with the published pipeline. Must not be used as
    the validated label. Includes upstream bugs: no word boundaries on
    yes/no, and missing answers default to 0.
    """
    failure_modes = {code: 0 for code in MAST_CODES}
    try:
        cleaned = response.strip()
        if cleaned.startswith("@@"):
            cleaned = cleaned[2:]
        if cleaned.endswith("@@"):
            cleaned = cleaned[:-2]
        for mode in failure_modes:
            patterns = [
                rf"C\..*?{mode}.*?(yes|no)",
                rf"C{mode}\s+(yes|no)",
                rf"{mode}\s*[:]\s*(yes|no)",
                rf"{mode}\s+(yes|no)",
                rf"{mode}\s*\n\s*(yes|no)",
                rf"C\.{mode}\s*\n\s*(yes|no)",
            ]
            found = False
            for pattern in patterns:
                matches = re.findall(
                    pattern, cleaned, re.IGNORECASE | re.DOTALL
                )
                if matches:
                    failure_modes[mode] = (
                        1 if matches[0].lower() == "yes" else 0
                    )
                    found = True
                    break
            if not found:
                general = rf"(?:C\.)?{mode}.*?(yes|no)"
                match = re.search(
                    general, cleaned, re.IGNORECASE | re.DOTALL
                )
                if match:
                    failure_modes[mode] = (
                        1 if match.group(1).lower() == "yes" else 0
                    )
                else:
                    failure_modes[mode] = 0
    except Exception:
        for mode in failure_modes:
            failure_modes[mode] = 0
    return failure_modes


def _empty_labels() -> dict[str, bool | None]:
    return {code: None for code in MAST_CODES}


def _normalize_copy(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[*_`#]", "", text)
    lines = []
    for line in text.split("\n"):
        if line.lstrip().startswith("- "):
            line = line.lstrip()[2:]
        lines.append(line)
    return "\n".join(lines)


def _truthy_token(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("yes", "true", "1"):
            return True
        if low in ("no", "false", "0"):
            return False
    return None


def _parse_json_object(
    obj: dict[str, Any],
) -> tuple[dict[str, bool | None], list[str], list[str]]:
    labels = _empty_labels()
    unknown: list[str] = []
    ambiguous: list[str] = []
    for key, value in obj.items():
        key_str = str(key).strip()
        code = key_str.split()[0] if key_str else ""
        if code not in MAST_CODES:
            if re.match(r"^\d\.\d$", code):
                unknown.append(code)
            continue
        parsed = _truthy_token(value)
        if parsed is None:
            ambiguous.append(code)
            labels[code] = None
        else:
            labels[code] = parsed
    return labels, sorted(set(unknown)), sorted(set(ambiguous))


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = _FENCE_JSON_RE.search(text)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return None
    return None


def _value_from_rest(code: str, rest: str) -> bool | None | str:
    """Return True/False, 'ambiguous', based on yes/no tokens in rest."""
    cleaned = rest
    name = MAST_NAMES.get(code, "")
    if name:
        cleaned = re.sub(re.escape(name), "", cleaned, flags=re.IGNORECASE)
    if ":" in cleaned:
        cleaned = cleaned.rsplit(":", 1)[-1]
    has_yes = bool(_YES_RE.search(cleaned))
    has_no = bool(_NO_RE.search(cleaned))
    if has_yes and not has_no:
        return True
    if has_no and not has_yes:
        return False
    return "ambiguous"


def _parse_section_c(
    section: str,
) -> tuple[
    dict[str, bool | None],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    bool,
]:
    labels = _empty_labels()
    seen: dict[str, bool | None] = {}
    unknown: list[str] = []
    ambiguous: list[str] = []
    conflicting: list[str] = []
    warnings: list[str] = []
    any_mast_code = False

    for line in section.split("\n"):
        match = _CODE_LINE_RE.match(line.strip())
        if not match:
            continue
        code = match.group(1)
        rest = match.group(2)
        if code not in MAST_CODES:
            unknown.append(code)
            warnings.append(f"unknown_code:{code}")
            continue
        any_mast_code = True
        result = _value_from_rest(code, rest)
        value: bool | None
        if result == "ambiguous":
            ambiguous.append(code)
            value = None
        else:
            assert isinstance(result, bool)
            value = result
        if code in seen:
            if seen[code] == value and value is not None:
                warnings.append(f"duplicate_code:{code}")
            elif seen[code] != value:
                conflicting.append(code)
                labels[code] = None
                seen[code] = None
            continue
        seen[code] = value
        labels[code] = value

    missing = [c for c in MAST_CODES if c not in seen]
    return (
        labels,
        missing,
        sorted(set(ambiguous)),
        sorted(set(conflicting)),
        sorted(set(unknown)),
        warnings,
        any_mast_code,
    )


def _extract_summary(text: str) -> str | None:
    match = _SECTION_A_RE.search(text)
    if not match:
        return None
    summary = match.group(1).strip()
    return summary or None


def _extract_task_completed(text: str) -> bool | None:
    match = _SECTION_B_RE.search(text)
    if not match:
        return None
    body = match.group(1)
    has_yes = bool(_YES_RE.search(body))
    has_no = bool(_NO_RE.search(body))
    if has_yes and not has_no:
        return True
    if has_no and not has_yes:
        return False
    return None


def _finalize(
    *,
    raw_response: str | None,
    raw_type: str,
    prompt_version: str | None,
    labels: dict[str, bool | None],
    missing: list[str],
    ambiguous: list[str],
    conflicting: list[str],
    unknown: list[str],
    summary: str | None,
    task_completed: bool | None,
    warnings: list[str],
    labels_official: dict[str, int],
    any_code_found: bool,
    forced_status: ParseStatus | None = None,
) -> ParsedJudgeResponse:
    if forced_status is not None:
        status: ParseStatus = forced_status
    elif not any_code_found:
        status = "malformed"
    elif conflicting or ambiguous:
        status = "ambiguous"
    elif missing:
        status = "partial"
    else:
        status = "ok"

    predicted = sorted(c for c, v in labels.items() if v is True)
    return ParsedJudgeResponse(
        raw_response=raw_response,
        raw_type=raw_type,
        parser_version=PARSER_VERSION,
        prompt_version=prompt_version,
        parse_status=status,
        labels=labels,
        predicted_labels=predicted,
        missing_codes=sorted(missing),
        ambiguous_codes=sorted(set(ambiguous)),
        conflicting_codes=sorted(set(conflicting)),
        unknown_codes=sorted(set(unknown)),
        summary=summary,
        task_completed=task_completed,
        warnings=warnings,
        labels_official=labels_official,
    )


def parse_judge_response(
    raw: object,
    prompt_version: str | None = None,
) -> ParsedJudgeResponse:
    """Parse a judge response into validated labels and parse status."""
    raw_type = type(raw).__name__
    pv = prompt_version if prompt_version is not None else PROMPT_VERSION

    if raw is None:
        return _finalize(
            raw_response=None,
            raw_type=raw_type,
            prompt_version=pv,
            labels=_empty_labels(),
            missing=list(MAST_CODES),
            ambiguous=[],
            conflicting=[],
            unknown=[],
            summary=None,
            task_completed=None,
            warnings=[],
            labels_official={},
            any_code_found=False,
            forced_status="empty",
        )

    if isinstance(raw, dict):
        labels, unknown, ambiguous = _parse_json_object(raw)
        seen = {
            c
            for c in MAST_CODES
            if labels[c] is not None or c in ambiguous
        }
        missing = [c for c in MAST_CODES if c not in seen]
        return _finalize(
            raw_response=json.dumps(raw, default=str),
            raw_type=raw_type,
            prompt_version=pv,
            labels=labels,
            missing=missing,
            ambiguous=ambiguous,
            conflicting=[],
            unknown=unknown,
            summary=None,
            task_completed=None,
            warnings=["json_format"],
            labels_official={},
            any_code_found=bool(seen),
        )

    if not isinstance(raw, str):
        try:
            raw_text = json.dumps(raw, default=str)
        except TypeError:
            raw_text = repr(raw)
        return _finalize(
            raw_response=raw_text,
            raw_type=raw_type,
            prompt_version=pv,
            labels=_empty_labels(),
            missing=list(MAST_CODES),
            ambiguous=[],
            conflicting=[],
            unknown=[],
            summary=None,
            task_completed=None,
            warnings=["non_string_input"],
            labels_official={},
            any_code_found=False,
            forced_status="malformed",
        )

    raw_str: str = raw
    if raw_str.strip() == "":
        return _finalize(
            raw_response=raw_str,
            raw_type=raw_type,
            prompt_version=pv,
            labels=_empty_labels(),
            missing=list(MAST_CODES),
            ambiguous=[],
            conflicting=[],
            unknown=[],
            summary=None,
            task_completed=None,
            warnings=[],
            labels_official=official_labels(raw_str),
            any_code_found=False,
            forced_status="empty",
        )

    work = _normalize_copy(raw_str)
    warnings: list[str] = []
    labels_off = official_labels(raw_str)

    # Extract JSON before markdown stripping removes fence backticks.
    json_source = raw_str.replace("\r\n", "\n")
    json_obj = _extract_json_payload(json_source)
    if json_obj is None:
        json_obj = _extract_json_payload(work)
    if json_obj is not None:
        labels, unknown, ambiguous = _parse_json_object(json_obj)
        seen = {
            c
            for c in MAST_CODES
            if labels[c] is not None or c in ambiguous
        }
        missing = [c for c in MAST_CODES if c not in seen]
        warnings.append("json_format")
        return _finalize(
            raw_response=raw_str,
            raw_type=raw_type,
            prompt_version=pv,
            labels=labels,
            missing=missing,
            ambiguous=ambiguous,
            conflicting=[],
            unknown=unknown,
            summary=_extract_summary(work),
            task_completed=_extract_task_completed(work),
            warnings=warnings,
            labels_official=labels_off,
            any_code_found=bool(seen),
        )

    c_match = None
    for match in _SECTION_C_RE.finditer(work):
        c_match = match
    if c_match is None:
        warnings.append("no_section_c")
        section_c = work
    else:
        section_c = work[c_match.end() :]

    summary = _extract_summary(work)
    task_completed = _extract_task_completed(work)

    (
        labels,
        missing,
        ambiguous,
        conflicting,
        unknown,
        line_warnings,
        any_mast_code,
    ) = _parse_section_c(section_c)
    warnings.extend(line_warnings)

    return _finalize(
        raw_response=raw_str,
        raw_type=raw_type,
        prompt_version=pv,
        labels=labels,
        missing=missing,
        ambiguous=ambiguous,
        conflicting=conflicting,
        unknown=unknown,
        summary=summary,
        task_completed=task_completed,
        warnings=warnings,
        labels_official=labels_off,
        any_code_found=any_mast_code,
    )


def to_record_fields(parsed: ParsedJudgeResponse) -> dict[str, object]:
    """Flat json-serializable dict for the execution owner's runner."""
    return parsed.model_dump(mode="json")
