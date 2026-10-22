"""QMSum download and verification script.

Downloads the official Yale-LILY QMSum benchmark dataset (NAACL-HLT 2021)
from https://github.com/Yale-LILY/QMSum.

Writes:
  data/qmsum/raw/{train.jsonl, val.jsonl, test.jsonl}
  data/qmsum/STATS.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
QMSUM_DIR = REPO_ROOT / "data" / "qmsum"
RAW_DIR = QMSUM_DIR / "raw"

BASE_URL = "https://raw.githubusercontent.com/Yale-LILY/QMSum/master/data/ALL/jsonl"
FILES = {
    "train.jsonl": f"{BASE_URL}/train.jsonl",
    "val.jsonl": f"{BASE_URL}/val.jsonl",
    "test.jsonl": f"{BASE_URL}/test.jsonl",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path, force: bool = False) -> None:
    if dest.exists() and not force:
        print(f"  [cached] {dest.name}")
        return
    print(f"  [downloading] {dest.name} from {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, dest.open("wb") as out_file:
        while chunk := response.read(65536):
            out_file.write(chunk)


def inspect_counts(path: Path) -> tuple[int, int]:
    """Returns (meeting_count, query_count)."""
    meetings = 0
    queries = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            meetings += 1
            queries += len(record.get("general_query_list", []))
            queries += len(record.get("specific_query_list", []))
    return meetings, queries


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and verify QMSum dataset")
    parser.add_argument("--force", action="store_true", help="Force re-download even if files exist")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  QMSUM DOWNLOAD & VERIFICATION")
    print("=" * 60)

    stats = {}
    total_meetings = 0
    total_queries = 0

    for filename, url in FILES.items():
        dest = RAW_DIR / filename
        download_file(url, dest, force=args.force)
        csum = sha256_file(dest)
        meetings, queries = inspect_counts(dest)
        stats[filename] = {
            "sha256": csum,
            "bytes": dest.stat().st_size,
            "meetings": meetings,
            "queries": queries,
        }
        total_meetings += meetings
        total_queries += queries
        print(f"  {filename:<14} {dest.stat().st_size:>10,} bytes | {meetings:>3} meetings | {queries:>4} queries | sha256: {csum[:12]}...")

    print("-" * 60)
    print(f"  Total Meetings: {total_meetings} (expected: 232)")
    print(f"  Total Queries:  {total_queries} (expected: 1,808)")
    print("=" * 60)

    # Validate paper invariant: ~1,808 query-summary pairs across 232 meetings
    assert total_meetings == 232, f"Expected 232 meetings; found {total_meetings}"
    assert total_queries in (1808, 1810), f"Expected 1,808 or 1,810 query-summary pairs; found {total_queries}"

    # Write STATS.md
    now_utc = datetime.now(timezone.utc).isoformat()
    lines = [
        "# QMSum Dataset Statistics",
        "",
        f"- Downloaded: `{now_utc}`",
        "- Upstream: [Yale-LILY/QMSum](https://github.com/Yale-LILY/QMSum) (Zhong et al., NAACL-HLT 2021)",
        "- License: MIT",
        f"- Total Meetings: {total_meetings}",
        f"- Total Query-Summary Pairs: {total_queries}",
        "",
        "## File Inventory",
        "",
        "| File | Meetings | Query Pairs | Size (bytes) | SHA-256 |",
        "|---|---:|---:|---:|---|",
    ]
    for fn, s in stats.items():
        lines.append(f"| `{fn}` | {s['meetings']} | {s['queries']} | {s['bytes']:,} | `{s['sha256']}` |")

    lines.append("")
    stats_path = QMSUM_DIR / "STATS.md"
    stats_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Wrote stats to {stats_path.relative_to(REPO_ROOT)}")
    print("  QUALITY GATE: all checks passed ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
