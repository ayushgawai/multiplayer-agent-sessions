"""Generate the deterministic M1 smoke fixtures (DAT-53).

Usage (from the repo root):
  python data/scripts/make_m1_smoke.py --seed 13 --out data/m1_smoke/fixtures

No network, no model calls, no timestamps, no absolute paths in the output. Output bytes are
identical on Windows and Linux (UTF-8, LF, sorted keys, compact separators).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.m1_smoke.loader import SPLITS, load_fixtures  # noqa: E402
from data.m1_smoke.schema import (  # noqa: E402
    LABEL_TO_CATEGORY,
    SCHEMA_VERSION,
    CatchupExample,
)
from data.m1_smoke.scenarios import SCENARIOS, Blueprint, instantiate  # noqa: E402

DEFAULT_SEED = 13
DEFAULT_OUT = "data/m1_smoke/fixtures"
CANONICAL_COMMAND = f"python data/scripts/make_m1_smoke.py --seed {DEFAULT_SEED} --out {DEFAULT_OUT}"
N_SESSIONS = 12
# Sessions per split, and how many sessions in each split also get a "joined late" example.
SPLIT_SESSIONS = {"train": 8, "dev": 2, "test": 2}
SPLIT_PREFIX_EXAMPLES = {"train": 4, "dev": 1, "test": 1}
LATE_QUERY = "I just joined. Catch me up on everything up to this point."


def _example(bp: Blueprint, suffix: str, query: str, cut: int | None) -> CatchupExample:
    """Build one example from a blueprint, optionally truncated to its first ``cut`` events."""
    events = bp.events if cut is None else bp.events[:cut]
    kept = {e["source_event_id"] for e in events}
    reference: dict[str, list[dict[str, Any]]] = {
        c: [] for c in ("completed", "in_progress", "blocked", "decisions", "pending_actions")
    }
    facts: list[dict[str, Any]] = []
    fact_no = 0
    for label, text, support, fact in bp.claims:
        # Fact ids come from the full session so they stay stable across truncation.
        if fact:
            fact_no += 1
        if not set(support) <= kept:
            continue
        category = LABEL_TO_CATEGORY[label]
        reference[category].append({"text": text, "source_event_ids": support})
        if fact:
            facts.append(
                {
                    "fact_id": f"{bp.session_id}-f{fact_no:02d}",
                    "category": category,
                    "text": fact,
                    "evidence_event_ids": support,
                }
            )
    return CatchupExample.model_validate(
        {
            "example_id": f"{bp.session_id}-{suffix}",
            "session_id": bp.session_id,
            "query": query,
            "events": events,
            "event_labels": {k: v for k, v in bp.labels.items() if k in kept},
            "reference": reference,
            "critical_facts": facts,
        }
    )


def build_dataset(seed: int = DEFAULT_SEED) -> dict[str, list[CatchupExample]]:
    """Build all splits in memory. Depends only on ``seed``."""
    rng = random.Random(seed)
    blueprints = [
        instantiate(n, SCENARIOS[(n - 1) % len(SCENARIOS)], rng) for n in range(1, N_SESSIONS + 1)
    ]
    order = [bp.session_id for bp in blueprints]
    rng.shuffle(order)
    by_id = {bp.session_id: bp for bp in blueprints}

    out: dict[str, list[CatchupExample]] = {}
    start = 0
    for split in SPLITS:
        count = SPLIT_SESSIONS[split]
        session_ids = sorted(order[start : start + count])
        start += count
        examples: list[CatchupExample] = []
        for i, sid in enumerate(session_ids):
            bp = by_id[sid]
            examples.append(_example(bp, "x1", bp.query, None))
            if i < SPLIT_PREFIX_EXAMPLES[split]:
                n = len(bp.events)
                cut = rng.randint(max(8, (n * 6) // 10), (n * 8) // 10)
                examples.append(_example(bp, "x2", LATE_QUERY, cut))
        out[split] = sorted(examples, key=lambda e: e.example_id)
    return out


def _dump(example: CatchupExample) -> str:
    return json.dumps(
        example.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def write_fixtures(out_dir: Path, seed: int = DEFAULT_SEED) -> dict[str, Any]:
    """Write the jsonl splits and MANIFEST.json to ``out_dir`` and return the manifest."""
    dataset = build_dataset(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "task": "m1_catchup_smoke",
        "contract": SCHEMA_VERSION,
        "converts_to": ["m1-input-v1", "m1-output-v1"],
        "purpose": "smoke fixtures for pipeline validation; never an M1 evaluation split",
        "seed": seed,
        "split_policy": "by session_id",
        "generator": {"command": CANONICAL_COMMAND, "script": "data/scripts/make_m1_smoke.py"},
        "splits": {},
    }
    for split, examples in dataset.items():
        data = "".join(_dump(e) + "\n" for e in examples).encode("utf-8")
        with (out_dir / f"{split}.jsonl").open("wb") as f:
            f.write(data)
        manifest["splits"][split] = {
            "file": f"{split}.jsonl",
            "count": len(examples),
            "sessions": sorted({e.session_id for e in examples}),
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    with (out_dir / "MANIFEST.json").open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    load_fixtures(out_dir)  # re-validate what was written
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the deterministic M1 smoke fixtures")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=Path(DEFAULT_OUT))
    args = parser.parse_args()
    out_dir = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    manifest = write_fixtures(out_dir, seed=args.seed)
    for split, info in manifest["splits"].items():
        print(f"{split:<5} {info['count']:>3} examples {info['bytes']:>7,} bytes sha256 {info['sha256'][:12]}")
    print("M1 smoke fixtures written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
