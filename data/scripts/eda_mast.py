"""Demo 1: MAST data pipeline — extract, clean, preprocess, quality assess.

Owner: data track (Naman). Run from repo root after venv is active.

    python data/scripts/download_mast.py   # Stage 0 / extract sources
    python data/scripts/eda_mast.py        # Stages 1-4 below

Writes a small cleaned table to data/mast/processed/ (gitignored with other mast data).
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAST = ROOT / "data" / "mast"
FULL = MAST / "hf" / "MAD_full_dataset.json"
HUMAN = MAST / "hf" / "MAD_human_labelled_dataset.json"
TAX_DEF = MAST / "taxonomy" / "definitions.txt"
OUT_DIR = MAST / "processed"
OUT_CSV = OUT_DIR / "mast_clean_summary.csv"

# Paper: 14 failure modes in 3 categories (Cemri et al., 2025)
EXPECTED_CODES = [
    "1.1", "1.2", "1.3", "1.4", "1.5",
    "2.1", "2.2", "2.3", "2.4", "2.5", "2.6",
    "3.1", "3.2", "3.3",
]
EXPECTED_N = 1642
CATEGORY = {
    "1": "Specification issues",
    "2": "Inter-agent misalignment",
    "3": "Task verification / termination",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path):
    if not path.is_file():
        raise SystemExit(f"Missing {path}\nRun: python data/scripts/download_mast.py")
    with path.open() as f:
        return json.load(f)


def stage1_extract() -> tuple[list, list, str]:
    print("=" * 60)
    print("STAGE 1 — DATA EXTRACTION")
    print("=" * 60)
    full = _load(FULL)
    human = _load(HUMAN)
    tax = TAX_DEF.read_text(encoding="utf-8") if TAX_DEF.is_file() else ""
    print(f"  Source A (HF MAD full):     {FULL}")
    print(f"    records: {len(full)}")
    print(f"    sha256:  {_sha256(FULL)[:16]}…")
    print(f"  Source B (HF human labels): {HUMAN}")
    print(f"    records: {len(human)}")
    print(f"  Source C (taxonomy defs):   {TAX_DEF}")
    print(f"    chars:   {len(tax)}")
    print(f"  Provenance write-up:        {MAST / 'STATS.md'}")
    print("  Fields extracted per row: mas_name, llm_name, benchmark_name,")
    print("    trace_id, trace.trajectory, mast_annotation (14 binary codes)")
    return full, human, tax


def stage2_clean(full: list) -> list[dict]:
    print()
    print("=" * 60)
    print("STAGE 2 — CLEANING")
    print("=" * 60)
    kept: list[dict] = []
    drop_reasons: Counter = Counter()
    null_cells = 0
    for idx, r in enumerate(full):
        if not isinstance(r, dict):
            drop_reasons["not_object"] += 1
            continue
        tid = r.get("trace_id")
        ann = r.get("mast_annotation")
        traj = (r.get("trace") or {}).get("trajectory")
        if tid is None:
            drop_reasons["missing_trace_id"] += 1
            continue
        if not isinstance(ann, dict):
            drop_reasons["bad_annotation"] += 1
            continue
        if not traj or not str(traj).strip():
            drop_reasons["empty_trajectory"] += 1
            continue
        # normalize strings; null / missing label cells → 0 (no failure)
        clean_ann = {}
        for code in EXPECTED_CODES:
            v = ann.get(code, 0)
            if v is None:
                null_cells += 1
                clean_ann[code] = 0
            elif v in (0, 1, True, False):
                clean_ann[code] = int(bool(v))
            else:
                drop_reasons["non_binary_label"] += 1
                clean_ann = None
                break
        if clean_ann is None:
            continue
        kept.append(
            {
                "row_id": idx,  # stable id: source order (trace_id alone is not global)
                "trace_id": int(tid),
                "mas_name": str(r.get("mas_name") or "unknown").strip(),
                "llm_name": str(r.get("llm_name") or "unknown").strip(),
                "benchmark_name": str(r.get("benchmark_name") or "unknown").strip(),
                "mast_annotation": clean_ann,
                "trace_chars": len(str(traj)),
                "n_failures": sum(clean_ann.values()),
            }
        )
    print(f"  input rows:  {len(full)}")
    print(f"  kept rows:   {len(kept)}")
    print(f"  dropped:     {len(full) - len(kept)}")
    if drop_reasons:
        for reason, n in drop_reasons.most_common():
            print(f"    - {reason}: {n}")
    else:
        print("    - no rows dropped")
    print(f"  null label cells set to 0: {null_cells}")
    print("  Cleaning rules applied:")
    print("    • require trace_id + non-empty trajectory + annotation object")
    print("    • strip framework / LLM / benchmark names")
    print("    • coerce each of 14 MAST codes to binary 0/1 (null → 0)")
    print("    • assign row_id from source order (trace_id is per-framework)")
    return kept


def stage3_preprocess(rows: list[dict]) -> list[dict]:
    print()
    print("=" * 60)
    print("STAGE 3 — PREPROCESSING")
    print("=" * 60)
    out = []
    for r in rows:
        ann = r["mast_annotation"]
        cat_hits = Counter(CATEGORY[code[0]] for code, v in ann.items() if v)
        active = [c for c, v in ann.items() if v]
        out.append(
            {
                **{k: r[k] for k in (
                    "row_id", "trace_id", "mas_name", "llm_name", "benchmark_name",
                    "trace_chars", "n_failures",
                )},
                "failure_codes": "|".join(active),
                "cat_specification": cat_hits.get("Specification issues", 0),
                "cat_misalignment": cat_hits.get("Inter-agent misalignment", 0),
                "cat_verification": cat_hits.get("Task verification / termination", 0),
                **{f"fail_{c.replace('.', '_')}": ann[c] for c in EXPECTED_CODES},
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(out[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out)

    print("  Feature engineering:")
    print("    • flatten 14 binary failure labels into columns")
    print("    • derive n_failures and pipe-joined failure_codes")
    print("    • roll up into 3 MAST categories (spec / misalignment / verification)")
    print(f"  Wrote analysis table: {OUT_CSV}")
    print(f"  rows × cols: {len(out)} × {len(fieldnames)}")
    return out


def stage4_quality(rows: list[dict], human: list, tax: str) -> None:
    print()
    print("=" * 60)
    print("STAGE 4 — QUALITY ASSESSMENT")
    print("=" * 60)
    checks = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append(ok)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}: {detail}")

    check(
        "Record count vs paper",
        len(rows) == EXPECTED_N,
        f"cleaned {len(rows)}, paper states {EXPECTED_N}",
    )

    row_ids = [r["row_id"] for r in rows]
    check(
        "Unique row_id",
        len(row_ids) == len(set(row_ids)),
        f"{len(row_ids)} rows, {len(set(row_ids))} unique row_ids",
    )

    composite = [
        (r["mas_name"], r["benchmark_name"], r["llm_name"], r["trace_id"]) for r in rows
    ]
    n_composite = len(set(composite))
    print(
        f"  [INFO] Composite key (mas, benchmark, llm, trace_id): "
        f"{n_composite} unique / {len(rows)} rows "
        f"(source reuses trace_id within frameworks; we key by row_id)"
    )

    schema_ok = all(
        all(f"fail_{c.replace('.', '_')}" in r for c in EXPECTED_CODES) for r in rows[:1]
    ) and all(r["mas_name"] and r["llm_name"] for r in rows)
    check("Schema completeness", schema_ok, "required identity + 14 label columns present")

    bad_vals = 0
    for r in rows:
        for c in EXPECTED_CODES:
            v = r[f"fail_{c.replace('.', '_')}"]
            if v not in (0, 1):
                bad_vals += 1
    check("Label domain (0/1 only)", bad_vals == 0, f"non-binary cells={bad_vals}")

    check(
        "Taxonomy file present",
        len(tax) > 0 and TAX_DEF.is_file(),
        f"{len(tax)} chars in definitions.txt",
    )

    check(
        "Human-labelled IAA set",
        isinstance(human, list) and len(human) == 19,
        f"{len(human) if isinstance(human, list) else '?'} rows (agreement study sample)",
    )

    # distribution summary (EDA for the ISA)
    print()
    print("  Distribution summary (for walkthrough):")
    print(f"    frameworks: {len({r['mas_name'] for r in rows})}")
    print(f"    LLMs:       {len({r['llm_name'] for r in rows})}")
    print(f"    benchmarks: {len({r['benchmark_name'] for r in rows})}")
    print("    Top frameworks:")
    for name, n in Counter(r["mas_name"] for r in rows).most_common(7):
        print(f"      {n:4d}  {name}")
    mode_c: Counter = Counter()
    for r in rows:
        for c in EXPECTED_CODES:
            if r[f"fail_{c.replace('.', '_')}"]:
                mode_c[c] += 1
    print("    Top failure modes:")
    for code, n in mode_c.most_common(5):
        print(f"      {n:4d}  {code}  ({CATEGORY[code[0]]})")
    any_fail = sum(1 for r in rows if r["n_failures"] > 0)
    chars = sorted(r["trace_chars"] for r in rows)
    print(
        f"    traces with ≥1 failure: {any_fail}/{len(rows)} "
        f"({100 * any_fail / len(rows):.1f}%)"
    )
    print(
        f"    trace length (chars): min={chars[0]}  "
        f"median={chars[len(chars) // 2]}  max={chars[-1]}"
    )

    print()
    if all(checks):
        print("QUALITY GATE: all checks passed — dataset ready for baseline / eval use.")
    else:
        print("QUALITY GATE: one or more checks failed — do not freeze this manifest.")
        raise SystemExit(1)


def main() -> int:
    print("Demo 1: Data Extraction, Cleaning, Preprocessing, and Quality Assessment")
    print("Dataset: MAST-Data (Cemri et al., 2025) — baseline reproduction path\n")
    full, human, tax = stage1_extract()
    cleaned = stage2_clean(full)
    processed = stage3_preprocess(cleaned)
    stage4_quality(processed, human, tax)
    print()
    print("Artifacts to show:")
    print(f"  • {MAST / 'STATS.md'}")
    print(f"  • {FULL}")
    print(f"  • {TAX_DEF}")
    print(f"  • {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
