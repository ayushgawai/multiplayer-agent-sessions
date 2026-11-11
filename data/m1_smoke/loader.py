"""Load and convert M1 smoke fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from data.m1_smoke.schema import CATEGORIES, CatchupExample

SPLITS = ("train", "dev", "test")
M1_INPUT_VERSION = "m1-input-v1"
M1_OUTPUT_VERSION = "m1-output-v1"


class SmokeDataError(ValueError):
    """Raised for unreadable or invalid fixture data. Messages name file and line."""


def load_split(path: str | Path) -> list[CatchupExample]:
    """Read one jsonl split. One JSON object per line, no blank lines."""
    path = Path(path)
    try:
        raw = path.read_bytes().decode("utf-8")
    except FileNotFoundError as exc:
        raise SmokeDataError(f"{path}: file not found") from exc
    except UnicodeDecodeError as exc:
        raise SmokeDataError(f"{path}: not valid UTF-8: {exc}") from exc

    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # trailing newline
    examples: list[CatchupExample] = []
    seen: dict[str, int] = {}
    for lineno, line in enumerate(lines, start=1):
        line = line.rstrip("\r")
        if not line.strip():
            raise SmokeDataError(f"{path}:{lineno}: blank line")
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SmokeDataError(f"{path}:{lineno}: invalid JSON: {exc.msg}") from exc
        example_id = obj.get("example_id", "<unknown>") if isinstance(obj, dict) else "<unknown>"
        try:
            example = CatchupExample.model_validate(obj)
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(str(p) for p in err['loc']) or '<root>'}: {err['msg']}"
                for err in exc.errors()
            )
            raise SmokeDataError(f"{path}:{lineno}: example {example_id}: {problems}") from exc
        if example.example_id in seen:
            raise SmokeDataError(
                f"{path}:{lineno}: example {example.example_id}: duplicate example_id "
                f"(first seen on line {seen[example.example_id]})"
            )
        seen[example.example_id] = lineno
        examples.append(example)
    return examples


def load_fixtures(fixtures_dir: str | Path) -> dict[str, list[CatchupExample]]:
    """Load train, dev and test from a fixtures directory."""
    fixtures_dir = Path(fixtures_dir)
    return {split: load_split(fixtures_dir / f"{split}.jsonl") for split in SPLITS}


def verify_manifest(fixtures_dir: str | Path) -> None:
    """Check MANIFEST.json counts, byte sizes and sha256 against the files on disk."""
    fixtures_dir = Path(fixtures_dir)
    manifest = json.loads((fixtures_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    for split, info in manifest["splits"].items():
        data = (fixtures_dir / info["file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != info["sha256"]:
            raise SmokeDataError(f"{split}: sha256 does not match MANIFEST.json")
        if len(data) != info["bytes"]:
            raise SmokeDataError(f"{split}: byte size does not match MANIFEST.json")
        if data.count(b"\n") != info["count"]:
            raise SmokeDataError(f"{split}: record count does not match MANIFEST.json")


def to_m1_input(example: CatchupExample) -> dict[str, Any]:
    """Convert to an m1-input-v1 dict. ``source_event_id`` becomes ``event_id``."""
    return {
        "schema_version": M1_INPUT_VERSION,
        "example_id": example.example_id,
        "session_id": example.session_id,
        "query": example.query,
        "events": [
            {
                "event_id": e.source_event_id,
                "sequence": e.sequence,
                "event_type": e.event_type,
                "actor_id": e.actor_id,
                "text": e.text,
            }
            for e in example.events
        ],
        "memory_version": None,
        "approved_memory": [],
    }


def gold_reference(example: CatchupExample) -> dict[str, Any]:
    """Gold summary as an m1-output-v1 dict, without ``candidate_id``."""
    out: dict[str, Any] = {
        "schema_version": M1_OUTPUT_VERSION,
        "example_id": example.example_id,
    }
    for category in CATEGORIES:
        out[category] = [
            {"text": c.text, "source_event_ids": list(c.source_event_ids)}
            for c in getattr(example.reference, category)
        ]
    return out
