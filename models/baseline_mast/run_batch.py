"""Resumable batch execution of the frozen MAST evaluation set.

Linear: DAT-34 (MAST 10). Owner: Shriram Dundigalla.

The runner loads traces named by the frozen evaluation manifest, renders the
frozen judge prompt, sends it through a judge adapter, parses the reply with
the frozen parser, and appends one prediction record per trace. Every record
is flushed to disk before the next trace starts, so an interrupted run keeps
its partial output and a restart skips traces that are already recorded.

MAST 02 (DAT-26) owns the real judge adapter. The Judge protocol below states
only what this runner needs from it; StubJudge is a deterministic stand-in so
the runner and its tests need no credentials or network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from models.baseline_mast.parse_judge import (
    MAST_CODES,
    MAST_NAMES,
    PARSER_VERSION,
    parse_judge_response,
    to_record_fields,
)
from models.baseline_mast.prompt import (
    PROMPT_SHA256,
    PROMPT_VERSION,
    render_prompt,
    was_truncated,
)
from models.baseline_mast.provenance import (
    build_run_manifest,
    missing_manifest_fields,
    write_run_manifest,
)

PREDICTIONS_FILE = "predictions.jsonl"
FAILURES_FILE = "failures.jsonl"

# trace_id repeats across source runs in MAD_full_dataset.json, so the pair
# (trace.key, trace_id) is the only unique record key. See DAT-29 data
# dictionary, "trace_id -- Not a unique id".
RECORD_ID_SEP = "::"


def make_record_id(trace_key: str, trace_index: int) -> str:
    return f"{trace_key}{RECORD_ID_SEP}{trace_index}"


@dataclass(frozen=True)
class EvalRecord:
    """One trace selected for evaluation, with its reference labels."""

    record_id: str
    trace_key: str
    trace_index: int
    framework: str
    llm_name: str
    benchmark: str
    trajectory: str
    reference_labels: dict[str, bool | None]
    reference_source: str


@dataclass(frozen=True)
class JudgeCall:
    """What the runner needs back from one judge invocation."""

    raw_response: object
    latency_ms: float
    retry_count: int = 0
    error: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class Judge(Protocol):
    """Contract the runner needs from the MAST 02 adapter (DAT-26).

    Provisional until DAT-26 lands; that issue is authoritative on the real
    adapter's shape. A judge must never raise for a model-side failure, it
    returns a JudgeCall carrying `error` instead.
    """

    @property
    def model_id(self) -> str: ...

    @property
    def model_settings(self) -> dict[str, Any]: ...

    def judge(self, prompt: str) -> JudgeCall: ...


class StubJudge:
    """Deterministic judge stand-in. Never calls a network service.

    The reply is derived from a digest of the prompt, so the same trace always
    produces the same labels and a resumed run is byte-identical to an
    uninterrupted one.
    """

    def __init__(self, model_id: str = "stub-judge-v1", temperature: float = 1.0) -> None:
        self._model_id = model_id
        self._settings: dict[str, Any] = {"temperature": temperature, "stub": True}

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def model_settings(self) -> dict[str, Any]:
        return dict(self._settings)

    def judge(self, prompt: str) -> JudgeCall:
        digest = hashlib.sha256(prompt.encode("utf-8")).digest()
        lines = [f"{code} {MAST_NAMES[code]}: {'yes' if digest[i] % 4 == 0 else 'no'}"
                 for i, code in enumerate(MAST_CODES)]
        body = "\n".join(lines)
        reply = (
            f"A. Deterministic stub verdict {digest[:4].hex()}.\n"
            f"B. {'yes' if digest[14] % 2 == 0 else 'no'}\n"
            f"C.\n{body}\n"
        )
        return JudgeCall(raw_response=reply, latency_ms=0.0)


def _as_reference_labels(raw: object) -> dict[str, bool | None]:
    """Normalize a 14-code annotation map to bool/None, keyed by code."""
    out: dict[str, bool | None] = {code: None for code in MAST_CODES}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        code = str(key).strip().split()[0] if str(key).strip() else ""
        if code not in MAST_CODES:
            continue
        if isinstance(value, bool):
            out[code] = value
        elif isinstance(value, (int, float)) and value in (0, 1):
            out[code] = bool(value)
        elif isinstance(value, str) and value.strip().lower() in ("0", "1"):
            out[code] = value.strip() == "1"
    return out


def load_eval_records(
    manifest_path: Path,
    dataset_path: Path,
    reference_type: str = "released_llm_annotation",
) -> list[EvalRecord]:
    """Build the evaluation set named by the frozen manifest.

    Records listed under the reference source's `excluded_records` are dropped,
    matching the manifest's own inclusion rule rather than re-deriving it here.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = {s["reference_type"]: s for s in manifest.get("reference_sources", [])}
    if reference_type not in sources:
        raise ValueError(
            f"reference_type {reference_type!r} not in manifest; "
            f"have {sorted(sources)}"
        )
    source = sources[reference_type]
    label_field = source["label_field"]

    excluded = {
        make_record_id(str(e["trace_key"]), int(e["trace_id"]))
        for e in source.get("excluded_records", [])
    }

    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    records: list[EvalRecord] = []
    for row in raw:
        trace = row.get("trace") or {}
        trace_key = str(trace.get("key", ""))
        trace_index = int(row.get("trace_id", trace.get("index", -1)))
        record_id = make_record_id(trace_key, trace_index)
        if record_id in excluded:
            continue
        records.append(
            EvalRecord(
                record_id=record_id,
                trace_key=trace_key,
                trace_index=trace_index,
                framework=str(row.get("mas_name", "")),
                llm_name=str(row.get("llm_name", "")),
                benchmark=str(row.get("benchmark_name", "")),
                trajectory=str(trace.get("trajectory", "")),
                reference_labels=_as_reference_labels(row.get(label_field)),
                reference_source=reference_type,
            )
        )

    expected = source.get("scorable_record_count")
    if expected is not None and len(records) != int(expected):
        raise ValueError(
            f"loaded {len(records)} records but manifest declares "
            f"scorable_record_count={expected}; refusing to run on a set that "
            f"does not match the frozen manifest"
        )
    return records


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield complete JSON objects, tolerating a truncated final line.

    A run killed mid-write can leave a partial last line. That line is skipped
    rather than treated as corruption, so resume still works.
    """
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.endswith("\n"):
                continue
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def completed_record_ids(result_dir: Path) -> set[str]:
    return {
        str(rec["trace_id"])
        for rec in read_jsonl(result_dir / PREDICTIONS_FILE)
        if rec.get("trace_id")
    }


def failed_record_ids(result_dir: Path) -> list[str]:
    """Failed ids in first-seen order, excluding any later succeeded."""
    done = completed_record_ids(result_dir)
    seen: list[str] = []
    for rec in read_jsonl(result_dir / FAILURES_FILE):
        rid = str(rec.get("trace_id", ""))
        if rid and rid not in done and rid not in seen:
            seen.append(rid)
    return seen


def seal_partial_line(path: Path) -> bool:
    """Terminate a partial final line left by a killed run.

    A hard kill can leave the last line without its newline. Appending
    straight onto that byte would glue the next record to the fragment and
    silently lose it, so the fragment is closed off first. It stays on its own
    line, where read_jsonl discards it. Returns True when a seal was needed.
    """
    if not path.exists() or path.stat().st_size == 0:
        return False
    with path.open("rb+") as handle:
        handle.seek(-1, os.SEEK_END)
        if handle.read(1) == b"\n":
            return False
        handle.write(b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    return True


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append one record and force it to disk before returning."""
    line = json.dumps(payload, ensure_ascii=False, default=str)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


@dataclass
class RunSummary:
    run_id: str
    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    parse_status_counts: dict[str, int] = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    started_at: str = ""
    ended_at: str = ""


class BatchRunner:
    """Execute traces through the judge and parser, one record at a time."""

    def __init__(
        self,
        judge: Judge,
        result_dir: Path,
        *,
        dataset_version: str,
        dataset_sha256: str,
        run_id: str,
        max_retries: int = 2,
        log: Any = None,
    ) -> None:
        self.judge = judge
        self.result_dir = result_dir
        self.dataset_version = dataset_version
        self.dataset_sha256 = dataset_sha256
        self.run_id = run_id
        self.max_retries = max_retries
        self.log = log or (lambda msg: print(msg, file=sys.stderr))
        self.result_dir.mkdir(parents=True, exist_ok=True)

    def _call_judge(self, prompt: str) -> JudgeCall:
        """Invoke the judge, retrying only on a returned error."""
        attempts = 0
        last: JudgeCall | None = None
        while attempts <= self.max_retries:
            started = time.perf_counter()
            try:
                call = self.judge.judge(prompt)
            except Exception as exc:  # adapter contract breach, not a model error
                elapsed = (time.perf_counter() - started) * 1000.0
                call = JudgeCall(
                    raw_response=None,
                    latency_ms=elapsed,
                    error=f"{type(exc).__name__}: {exc}",
                )
            last = call
            if call.error is None:
                return JudgeCall(
                    raw_response=call.raw_response,
                    latency_ms=call.latency_ms,
                    retry_count=attempts,
                    error=None,
                    prompt_tokens=call.prompt_tokens,
                    completion_tokens=call.completion_tokens,
                )
            attempts += 1
        assert last is not None
        return JudgeCall(
            raw_response=last.raw_response,
            latency_ms=last.latency_ms,
            retry_count=attempts - 1,
            error=last.error,
            prompt_tokens=last.prompt_tokens,
            completion_tokens=last.completion_tokens,
        )

    def _record(self, rec: EvalRecord, call: JudgeCall) -> dict[str, Any]:
        parsed = parse_judge_response(call.raw_response, prompt_version=PROMPT_VERSION)
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "trace_id": rec.record_id,
            "trace_key": rec.trace_key,
            "trace_index": rec.trace_index,
            "framework": rec.framework,
            "llm_name": rec.llm_name,
            "benchmark": rec.benchmark,
            "dataset_version": self.dataset_version,
            "dataset_sha256": self.dataset_sha256,
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": PROMPT_SHA256,
            "parser_version": PARSER_VERSION,
            "model_id": self.judge.model_id,
            "model_settings": self.judge.model_settings,
            "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "latency_ms": round(call.latency_ms, 3),
            "retry_count": call.retry_count,
            "error": call.error,
            "truncated": was_truncated(rec.trajectory),
            "prompt_tokens": call.prompt_tokens,
            "completion_tokens": call.completion_tokens,
            "reference_source": rec.reference_source,
            "human_labels": rec.reference_labels,
        }
        payload.update(to_record_fields(parsed))
        return payload

    def run(
        self,
        records: Sequence[EvalRecord],
        *,
        only: Iterable[str] | None = None,
    ) -> RunSummary:
        """Judge every record not already recorded, appending as it goes."""
        summary = RunSummary(
            run_id=self.run_id,
            started_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        predictions = self.result_dir / PREDICTIONS_FILE
        failures = self.result_dir / FAILURES_FILE
        for path in (predictions, failures):
            if seal_partial_line(path):
                self.log(f"sealed a partial final line in {path.name}")

        done = completed_record_ids(self.result_dir)
        wanted = set(only) if only is not None else None

        for rec in records:
            if wanted is not None and rec.record_id not in wanted:
                continue
            if rec.record_id in done:
                summary.skipped += 1
                continue

            summary.attempted += 1
            call = self._call_judge(render_prompt(rec.trajectory))
            payload = self._record(rec, call)

            if call.error is not None:
                summary.failed += 1
                _append_jsonl(
                    failures,
                    {
                        "run_id": self.run_id,
                        "trace_id": rec.record_id,
                        "error": call.error,
                        "retry_count": call.retry_count,
                        "timestamp_utc": payload["timestamp_utc"],
                    },
                )
                self.log(f"FAIL {rec.record_id}: {call.error}")
                continue

            _append_jsonl(predictions, payload)
            done.add(rec.record_id)
            summary.succeeded += 1
            status = str(payload.get("parse_status", "unknown"))
            summary.parse_status_counts[status] = (
                summary.parse_status_counts.get(status, 0) + 1
            )
            summary.prompt_tokens += call.prompt_tokens or 0
            summary.completion_tokens += call.completion_tokens or 0

        summary.ended_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return summary


def _default_run_id() -> str:
    return datetime.now(UTC).strftime("run-%Y%m%dT%H%M%SZ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_batch",
        description="Resumable MAST baseline batch execution (DAT-34).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/mast/eval_manifest.json"),
        help="Frozen evaluation manifest (DAT-30).",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/mast/hf/MAD_full_dataset.json"),
        help="Dataset file named by the manifest.",
    )
    parser.add_argument(
        "--reference",
        default="released_llm_annotation",
        help="reference_type from the manifest to use for reference labels.",
    )
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=None, help="First N records only.")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Run only records recorded in failures.jsonl and not yet succeeded.",
    )
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument(
        "--stub-judge",
        action="store_true",
        help="Use the deterministic stub judge instead of the MAST 02 adapter.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.stub_judge:
        print(
            "No judge adapter available. MAST 02 (DAT-26) owns it; pass "
            "--stub-judge to exercise the runner without one.",
            file=sys.stderr,
        )
        return 2

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    dataset_files = {f["filename"]: f for f in manifest["dataset"]["files"]}
    entry = dataset_files.get(args.dataset.name, {})

    records = load_eval_records(args.manifest, args.dataset, args.reference)
    if args.limit is not None:
        records = records[: args.limit]

    runner = BatchRunner(
        judge=StubJudge(),
        result_dir=args.result_dir,
        dataset_version=str(manifest.get("manifest_version", "unknown")),
        dataset_sha256=str(entry.get("sha256", "")),
        run_id=args.run_id or _default_run_id(),
        max_retries=args.max_retries,
    )

    only = failed_record_ids(args.result_dir) if args.retry_failed else None
    summary = runner.run(records, only=only)

    run_manifest = build_run_manifest(
        run_id=runner.run_id,
        model_id=runner.judge.model_id,
        model_settings=runner.judge.model_settings,
        dataset_path=args.dataset,
        dataset_sha256=runner.dataset_sha256,
        dataset_revision=manifest.get("dataset", {}).get("pinned_revision"),
        eval_manifest_path=args.manifest,
        reference_source=args.reference,
        summary=summary,
        result_dir=args.result_dir,
    )
    write_run_manifest(args.result_dir, run_manifest)

    incomplete = missing_manifest_fields(run_manifest)
    if incomplete:
        print(
            f"run manifest is missing provenance fields: {incomplete}",
            file=sys.stderr,
        )

    print(json.dumps(summary.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
