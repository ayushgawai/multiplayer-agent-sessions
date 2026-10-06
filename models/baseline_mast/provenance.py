"""Run manifests and provenance for MAST baseline executions.

Linear: DAT-35 (MAST 11). Owner: Shriram Dundigalla.

A result directory is auditable when someone who did not run it can say
exactly which code, dataset, manifest, prompt, parser and model produced every
prediction in it. This module collects those facts and writes them next to the
predictions as run_manifest.json.

Secrets are never recorded. Model settings pass through a redactor before they
reach the manifest, so an adapter that carries an api key in its settings dict
cannot leak it into a committed artifact.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from models.baseline_mast.parse_judge import PARSER_VERSION
from models.baseline_mast.prompt import PROMPT_SHA256, PROMPT_VERSION, UPSTREAM_COMMIT

RUN_MANIFEST_FILE = "run_manifest.json"
REDACTED = "[REDACTED]"

# Key names whose value is never recorded. Matching is deliberate rather than
# broad: a bare "token" substring would also redact max_tokens and
# prompt_tokens, which are provenance we need.
_SECRET_KEY_SUBSTRINGS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "passwd",
    "credential",
    "authorization",
    "bearer",
    "private_key",
    "access_token",
    "api_token",
    "auth_token",
    "id_token",
    "refresh_token",
    "session_token",
    "session_key",
)

_SECRET_KEY_EXACT = frozenset(
    {"token", "tokens", "key", "auth", "authentication"}
)

# Values that look like credentials even under an innocent key name.
_SECRET_VALUE_RE = re.compile(
    r"""(
        sk-[A-Za-z0-9_\-]{16,}
      | lin_api_[A-Za-z0-9]{16,}
      | gh[pousr]_[A-Za-z0-9]{20,}
      | AKIA[0-9A-Z]{16}
      | xox[baprs]-[A-Za-z0-9\-]{10,}
      | ey[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}
    )""",
    re.VERBOSE,
)


def _is_secret_key(key: str) -> bool:
    low = key.lower()
    if low in _SECRET_KEY_EXACT:
        return True
    return any(part in low for part in _SECRET_KEY_SUBSTRINGS)


def redact(value: Any) -> Any:
    """Recursively strip anything that looks like a credential."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            out[name] = REDACTED if _is_secret_key(name) else redact(item)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return REDACTED if _SECRET_VALUE_RE.search(value) else value
    return value


def _git(repo_root: Path, *args: str) -> str | None:
    """Raw stdout of a git command, or None if it could not be run.

    Output is returned unstripped: `git status --porcelain` encodes state in
    the first two columns, so a leading space is meaningful.
    """
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def parse_status_paths(status: str) -> list[str]:
    """Paths from `git status --porcelain` output.

    Each line is 'XY PATH', so the path starts at column 3. Renames are
    reported as 'old -> new' and are kept verbatim.
    """
    return [line[3:] for line in status.splitlines() if line.strip()]


def git_provenance(repo_root: Path | None = None) -> dict[str, Any]:
    """Commit, branch and working-tree cleanliness of the running code."""
    root = repo_root or Path(__file__).resolve().parents[2]
    sha = (_git(root, "rev-parse", "HEAD") or "").strip() or None
    branch = (_git(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip() or None
    status = _git(root, "status", "--porcelain")
    return {
        "git_sha": sha,
        "git_branch": branch,
        "git_dirty": None if status is None else bool(status.strip()),
        "git_dirty_files": parse_status_paths(status) if status else [],
    }


def environment_provenance() -> dict[str, Any]:
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
    }


def manifest_provenance(manifest_path: Path) -> dict[str, Any]:
    """Identity of the frozen evaluation manifest the run was driven by."""
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "eval_manifest_path": str(manifest_path),
            "eval_manifest_version": None,
            "eval_manifest_status": None,
        }
    return {
        "eval_manifest_path": str(manifest_path),
        "eval_manifest_version": data.get("manifest_version"),
        "eval_manifest_status": data.get("status"),
        "eval_manifest_linear": data.get("linear"),
    }


def build_run_manifest(
    *,
    run_id: str,
    model_id: str,
    model_settings: dict[str, Any],
    dataset_path: Path,
    dataset_sha256: str,
    dataset_revision: str | None,
    eval_manifest_path: Path,
    reference_source: str,
    summary: Any,
    result_dir: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Assemble every fact needed to reproduce or audit one run."""
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "linear": "DAT-35 (MAST 11)",
        "owner": "Shriram Dundigalla",
        # Code
        **git_provenance(repo_root),
        "environment": environment_provenance(),
        # Dataset
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_sha256,
        "dataset_revision": dataset_revision,
        "reference_source": reference_source,
        # Evaluation manifest
        **manifest_provenance(eval_manifest_path),
        # Prompt and parser
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": PROMPT_SHA256,
        "prompt_upstream_commit": UPSTREAM_COMMIT,
        "parser_version": PARSER_VERSION,
        # Model
        "model_id": model_id,
        "model_settings": redact(model_settings),
        # Outcome
        "start_time_utc": getattr(summary, "started_at", None),
        "end_time_utc": getattr(summary, "ended_at", None),
        "attempted": getattr(summary, "attempted", None),
        "succeeded": getattr(summary, "succeeded", None),
        "failed": getattr(summary, "failed", None),
        "skipped": getattr(summary, "skipped", None),
        "parse_status_counts": dict(getattr(summary, "parse_status_counts", {})),
        "prompt_tokens": getattr(summary, "prompt_tokens", None),
        "completion_tokens": getattr(summary, "completion_tokens", None),
        # Where the outputs live
        "result_dir": str(result_dir),
        "predictions_file": "predictions.jsonl",
        "failures_file": "failures.jsonl",
        "raw_response_field": "raw_response",
        "parsed_labels_field": "labels",
        "record_key_field": "trace_id",
        "record_key_note": (
            "trace_id on a prediction is the composite "
            "'<trace.key>::<trace_id>' record key, because the dataset's own "
            "trace_id repeats across source runs. trace_key and trace_index "
            "hold the two parts separately."
        ),
    }
    return redact(manifest)


def write_run_manifest(result_dir: Path, manifest: dict[str, Any]) -> Path:
    """Write run_manifest.json atomically so a kill cannot truncate it."""
    result_dir.mkdir(parents=True, exist_ok=True)
    path = result_dir / RUN_MANIFEST_FILE
    tmp = path.with_suffix(".json.tmp")
    payload = json.dumps(manifest, indent=2, ensure_ascii=False, default=str)
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(payload + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    return path


REQUIRED_MANIFEST_FIELDS: tuple[str, ...] = (
    "run_id",
    "git_sha",
    "dataset_sha256",
    "eval_manifest_version",
    "prompt_version",
    "prompt_sha256",
    "parser_version",
    "model_id",
    "model_settings",
    "start_time_utc",
    "end_time_utc",
    "parse_status_counts",
    "predictions_file",
)


def missing_manifest_fields(manifest: dict[str, Any]) -> list[str]:
    """Required provenance fields that are absent or null."""
    return [f for f in REQUIRED_MANIFEST_FIELDS if manifest.get(f) is None]
