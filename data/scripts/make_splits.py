"""Split generation script for task datasets.

Usage:
  python data/scripts/make_splits.py --task m1 --by document --seed 13 --out data/splits/m1_v1/

Produces frozen CatchupExample jsonl files:
  data/splits/m1_v1/train.jsonl
  data/splits/m1_v1/val.jsonl
  data/splits/m1_v1/test.jsonl
  data/splits/m1_v1/MANIFEST.json

Schema for CatchupExample:
  {
    "id": str,
    "query": str,
    "context_spans": list[str],
    "reference_summary": str
  }
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def process_qmsum_split(raw_file: Path, split_name: str) -> list[dict[str, Any]]:
    examples = []
    with raw_file.open("r", encoding="utf-8") as f:
        for meeting_idx, line in enumerate(f):
            if not line.strip():
                continue
            doc = json.loads(line)
            transcripts = doc.get("meeting_transcripts", [])
            
            # Format transcript utterances as "Speaker: Content"
            formatted_turns = [
                f"{turn.get('speaker', 'Speaker')}: {turn.get('content', '').strip()}"
                for turn in transcripts
            ]

            # 1. Process specific queries with relevant spans
            for q_idx, item in enumerate(doc.get("specific_query_list", [])):
                query = item.get("query", "").strip()
                answer = item.get("answer", "").strip()
                spans = []
                for span_pair in item.get("relevant_text_span", []):
                    try:
                        s_idx = int(span_pair[0])
                        e_idx = int(span_pair[1]) + 1
                        spans.extend(formatted_turns[s_idx:e_idx])
                    except (ValueError, IndexError):
                        pass
                
                # If spans empty, fall back to entire meeting turns
                if not spans:
                    spans = formatted_turns

                examples.append({
                    "id": f"qmsum_{split_name}_{meeting_idx}_s{q_idx}",
                    "query": query,
                    "context_spans": spans,
                    "reference_summary": answer,
                })

            # 2. Process general queries (context is whole meeting)
            for q_idx, item in enumerate(doc.get("general_query_list", [])):
                query = item.get("query", "").strip()
                answer = item.get("answer", "").strip()
                examples.append({
                    "id": f"qmsum_{split_name}_{meeting_idx}_g{q_idx}",
                    "query": query,
                    "context_spans": formatted_turns,
                    "reference_summary": answer,
                })

    return examples


def build_m1_splits(out_dir: Path, seed: int) -> dict[str, Any]:
    raw_dir = REPO_ROOT / "data" / "qmsum" / "raw"
    if not (raw_dir / "train.jsonl").exists():
        raise FileNotFoundError(
            f"QMSum raw files missing in {raw_dir}. Run `python data/scripts/download_qmsum.py` first."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "task": "m1_catchup",
        "contract": "CatchupExample",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "seed": seed,
        "splits": {},
    }

    random.seed(seed)

    for split in ("train", "val", "test"):
        raw_file = raw_dir / f"{split}.jsonl"
        examples = process_qmsum_split(raw_file, split)

        # Shuffle deterministic by seed
        random.shuffle(examples)

        dest_file = out_dir / f"{split}.jsonl"
        with dest_file.open("w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        manifest["splits"][split] = {
            "count": len(examples),
            "sha256": sha256_file(dest_file),
            "bytes": dest_file.stat().st_size,
        }
        print(f"  {split:<6} -> {len(examples):>5} examples | {dest_file.stat().st_size:>10,} bytes | sha256: {manifest['splits'][split]['sha256'][:12]}...")

    manifest_path = out_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"  Wrote manifest to {manifest_path.relative_to(REPO_ROOT)}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate frozen task dataset splits")
    parser.add_argument("--task", required=True, choices=["m1", "m2", "m3", "m4"], help="Task name")
    parser.add_argument("--by", default="document", choices=["document", "session"], help="Split grouping")
    parser.add_argument("--seed", type=int, default=13, help="Random seed")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    args = parser.parse_args()

    out_dir = REPO_ROOT / args.out if not args.out.is_absolute() else args.out

    print("=" * 60)
    print(f"  GENERATING SPLITS: Task={args.task} by={args.by} seed={args.seed}")
    print(f"  Destination: {out_dir}")
    print("=" * 60)

    if args.task == "m1":
        build_m1_splits(out_dir, seed=args.seed)
    else:
        print(f"Task {args.task} split builder will land with its respective corpus.")
        return 1

    print("-" * 60)
    print("  SPLIT GENERATION COMPLETED ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
