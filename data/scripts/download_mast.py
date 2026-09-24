"""MAST 04 (DAT-28): download the MAST dataset release and taxonomy reference.

Owner: Naman Chheda. Lives under data/ only.

Sources
-------
- MAST Data release (Hugging Face dataset): https://huggingface.co/datasets/mcemri/MAD
  Files pulled: every file in the dataset repo except `.gitattributes`
  (currently: MAD_full_dataset.json, MAD_human_labelled_dataset.json, README.md).
- Official MAST GitHub repo (taxonomy/label reference not shipped in the HF release):
  https://github.com/multi-agent-systems-failure-taxonomy/MAST
  Files pulled: taxonomy_definitions_examples/definitions.txt and
  taxonomy_definitions_examples/examples.txt. These two are the taxonomy label
  definitions and worked examples; they are not part of the HF dataset repo, which
  only contains the trace/annotation JSON and its own README.

What this script does
----------------------
1. Downloads the files above into data/mast/hf/ and data/mast/taxonomy/.
2. Is idempotent for the HF release: if a target file already exists, it is
   skipped unless --force is passed. Skipped files are still checksummed and
   listed in STATS.md. The two small GitHub taxonomy reference files are
   re-fetched every run against a commit sha resolved at fetch time (see
   resolve_github_main_sha), so the pinned URL recorded in STATS.md always
   matches the checksum recorded next to it; --force only affects the HF
   release.
3. Computes a SHA-256 checksum for every file it manages.
4. Reads the record count out of MAD_full_dataset.json and compares it against the
   paper's stated 1,642 annotated traces (Cemri et al., 2025), flagging any mismatch
   instead of silently reporting a possibly-wrong number.
5. Writes data/mast/STATS.md with source URLs, download date/time, per-file
   checksums, and the record-count comparison.

Dependencies
------------
Only huggingface_hub and requests are used, both already present transitively in
requirements.lock.txt (huggingface_hub via bert-score -> transformers; requests via
mlflow / docker / databricks-sdk). No change to any requirements*.txt was needed or
made; that file is Ayush's, not mine, and installing requirements.txt alone already
provides both packages.

Usage
-----
    python data/scripts/download_mast.py [--force]

Not committed: data/mast/** (except README.md and STATS.md) is left out of git,
see data/mast/README.md and the root .gitignore. This script only ever writes
under data/mast/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "requests is required. It is already a transitive dependency of "
        "requirements.txt (via mlflow/docker/databricks-sdk); run "
        "`pip install -r requirements.txt` from the repo root."
    ) from exc

try:
    from huggingface_hub import HfApi, hf_hub_download
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "huggingface_hub is required. It is already a transitive dependency of "
        "requirements.txt (via bert-score -> transformers); run "
        "`pip install -r requirements.txt` from the repo root."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "mast"
HF_DIR = DATA_DIR / "hf"
TAXONOMY_DIR = DATA_DIR / "taxonomy"
STATS_PATH = DATA_DIR / "STATS.md"

HF_REPO_ID = "mcemri/MAD"
HF_REPO_TYPE = "dataset"
HF_DATASET_URL = f"https://huggingface.co/datasets/{HF_REPO_ID}"

MAST_GITHUB_REPO = "multi-agent-systems-failure-taxonomy/MAST"
MAST_GITHUB_URL = f"https://github.com/{MAST_GITHUB_REPO}"
MAST_GITHUB_API_COMMITS_URL = f"https://api.github.com/repos/{MAST_GITHUB_REPO}/commits/main"
GITHUB_TAXONOMY_FILES = [
    "taxonomy_definitions_examples/definitions.txt",
    "taxonomy_definitions_examples/examples.txt",
]

# Paper: Cemri et al., 2025, "Why Do Multi-Agent LLM Systems Fail?" (arXiv:2503.13657)
EXPECTED_TRACE_COUNT = 1642
FULL_DATASET_FILENAME = "MAD_full_dataset.json"


@dataclass
class FileRecord:
    relative_path: str
    source_url: str
    size_bytes: int
    sha256: str
    status: str  # "downloaded" or "skipped (cached)"


@dataclass
class RunStats:
    started_at: str
    files: list[FileRecord] = field(default_factory=list)
    hf_revision: str | None = None
    github_taxonomy_sha: str | None = None
    record_count: int | None = None
    record_count_note: str = ""
    human_labelled_count: int | None = None
    warnings: list[str] = field(default_factory=list)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_hf_release(force: bool, stats: RunStats) -> None:
    api = HfApi()
    info = api.dataset_info(HF_REPO_ID)
    stats.hf_revision = info.sha

    filenames = sorted(
        f for f in api.list_repo_files(HF_REPO_ID, repo_type=HF_REPO_TYPE)
        if f != ".gitattributes"
    )
    if not filenames:
        stats.warnings.append(
            f"HfApi.list_repo_files returned no files for {HF_REPO_ID}; "
            "dataset repo layout may have changed."
        )

    HF_DIR.mkdir(parents=True, exist_ok=True)

    for filename in filenames:
        dest = HF_DIR / filename
        file_url = f"{HF_DATASET_URL}/resolve/{info.sha}/{filename}"
        if dest.exists() and not force:
            status = "skipped (cached)"
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            hf_hub_download(
                repo_id=HF_REPO_ID,
                repo_type=HF_REPO_TYPE,
                filename=filename,
                revision=info.sha,
                local_dir=str(HF_DIR),
                force_download=force,
            )
            status = "downloaded"
        stats.files.append(
            FileRecord(
                relative_path=str(dest.relative_to(DATA_DIR)).replace("\\", "/"),
                source_url=file_url,
                size_bytes=dest.stat().st_size,
                sha256=sha256_of(dest),
                status=status,
            )
        )


def resolve_github_main_sha() -> str:
    """Resolve the current commit sha of the MAST repo's main branch.

    Pinning by commit sha (instead of the floating "main" ref) keeps the raw
    file URLs reproducible: a raw.githubusercontent.com/.../main/... URL can
    silently start serving different bytes if main advances, whereas a URL
    built from a resolved sha always serves the same content.
    """
    resp = requests.get(
        MAST_GITHUB_API_COMMITS_URL,
        timeout=30,
        headers={"Accept": "application/vnd.github+json"},
    )
    resp.raise_for_status()
    return resp.json()["sha"]


def download_github_taxonomy(force: bool, stats: RunStats) -> None:
    TAXONOMY_DIR.mkdir(parents=True, exist_ok=True)

    sha = resolve_github_main_sha()
    stats.github_taxonomy_sha = sha
    raw_base = f"https://raw.githubusercontent.com/{MAST_GITHUB_REPO}/{sha}"

    for rel in GITHUB_TAXONOMY_FILES:
        filename = Path(rel).name
        dest = TAXONOMY_DIR / filename
        url = f"{raw_base}/{rel}"
        # These two files are small (well under 100 KB combined), so unlike the
        # multi-hundred-MB HF release we do not skip-on-exists here: every run
        # re-fetches from the sha resolved above, so the checksum recorded in
        # STATS.md always corresponds to the exact pinned URL recorded next to
        # it. --force has no extra effect here; it only controls the HF release
        # download, which is the part worth skipping for idempotency.
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        status = "downloaded (re-verified against resolved sha)"
        stats.files.append(
            FileRecord(
                relative_path=str(dest.relative_to(DATA_DIR)).replace("\\", "/"),
                source_url=url,
                size_bytes=dest.stat().st_size,
                sha256=sha256_of(dest),
                status=status,
            )
        )


def _count_records(payload: Any) -> int | None:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                return len(value)
    return None


def inspect_dataset(stats: RunStats) -> None:
    full_path = HF_DIR / FULL_DATASET_FILENAME
    if not full_path.exists():
        stats.warnings.append(
            f"{FULL_DATASET_FILENAME} not found under {HF_DIR}; cannot verify record count."
        )
        return

    with full_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    count = _count_records(payload)
    stats.record_count = count

    if count is None:
        stats.record_count_note = (
            "Could not determine a record count: JSON root was neither a list "
            "nor a dict containing a list."
        )
        stats.warnings.append(stats.record_count_note)
    elif count == EXPECTED_TRACE_COUNT:
        stats.record_count_note = (
            f"MATCH: retrieved {count} records, equal to the paper's stated "
            f"{EXPECTED_TRACE_COUNT} annotated traces."
        )
    else:
        stats.record_count_note = (
            f"MISMATCH: retrieved {count} records, paper states "
            f"{EXPECTED_TRACE_COUNT}. Flagging for review, not silently reporting."
        )
        stats.warnings.append(stats.record_count_note)

    human_path = HF_DIR / "MAD_human_labelled_dataset.json"
    if human_path.exists():
        with human_path.open("r", encoding="utf-8") as fh:
            human_payload = json.load(fh)
        stats.human_labelled_count = _count_records(human_payload)


def write_stats_md(stats: RunStats, force: bool) -> None:
    lines: list[str] = []
    lines.append("# MAST dataset download stats (MAST 04 / DAT-28)")
    lines.append("")
    lines.append("Generated by `data/scripts/download_mast.py`. Do not hand-edit; rerun the script.")
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    lines.append(f"- MAST Data release (Hugging Face): {HF_DATASET_URL}")
    if stats.hf_revision:
        lines.append(f"  - Resolved commit sha: `{stats.hf_revision}`")
    lines.append(
        f"- Official MAST GitHub repo (taxonomy/label reference not in the HF release): {MAST_GITHUB_URL}"
    )
    if stats.github_taxonomy_sha:
        lines.append(f"  - Resolved commit sha (main, at fetch time): `{stats.github_taxonomy_sha}`")
    for rel in GITHUB_TAXONOMY_FILES:
        lines.append(f"  - `{rel}`")
    lines.append("")
    lines.append("## Download date/time")
    lines.append("")
    lines.append(f"- {stats.started_at} (UTC)")
    lines.append(f"- Command: `python data/scripts/download_mast.py{' --force' if force else ''}`")
    lines.append("")
    lines.append("## Record count vs. paper")
    lines.append("")
    lines.append(f"- Paper's stated annotated traces: {EXPECTED_TRACE_COUNT}")
    lines.append(f"- Retrieved from `MAD_full_dataset.json`: {stats.record_count}")
    lines.append(f"- {stats.record_count_note}")
    if stats.human_labelled_count is not None:
        lines.append(
            f"- `MAD_human_labelled_dataset.json` record count: {stats.human_labelled_count} "
            "(inter-annotator agreement study; taxonomy revision differs across rounds, "
            "per the HF dataset card. Not comparable to the 1,642 figure.)"
        )
    lines.append("")
    lines.append("## Per-file SHA-256 checksums")
    lines.append("")
    lines.append("| file | status | size (bytes) | sha256 | source |")
    lines.append("|---|---|---|---|---|")
    for rec in stats.files:
        lines.append(
            f"| `{rec.relative_path}` | {rec.status} | {rec.size_bytes} | `{rec.sha256}` | {rec.source_url} |"
        )
    lines.append("")
    if stats.warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in stats.warnings:
            lines.append(f"- {w}")
        lines.append("")

    STATS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download every file even if it already exists locally.",
    )
    args = parser.parse_args()

    stats = RunStats(started_at=datetime.now(timezone.utc).isoformat())

    download_hf_release(force=args.force, stats=stats)
    download_github_taxonomy(force=args.force, stats=stats)
    inspect_dataset(stats=stats)
    write_stats_md(stats=stats, force=args.force)

    print(f"Wrote {STATS_PATH.relative_to(REPO_ROOT)}")
    for w in stats.warnings:
        print(f"WARNING: {w}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
