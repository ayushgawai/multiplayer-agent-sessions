"""Demo 1: MAST data pipeline: extract, clean, preprocess, quality assess.

Owner: data track (Naman). Run from repo root after venv is active.

Reproduce (exact commands, from the repo root):

    python data/scripts/download_mast.py   # Stage 0 / extract sources
    python data/scripts/eda_mast.py        # Stages 1-4 below

Label and key policy (frozen in data/mast/eval_manifest.json):

* Canonical record key is (trace.key, trace_id). trace_id alone is not unique.
  Uniqueness is asserted over ALL raw records, and a duplicate is a hard error.
* A label is exactly 0, 1 (or a bool), or null. A missing code key is null.
  Null is never converted to 0. Any other value is a hard error.
* A record whose 14 codes are all null is excluded from scoring. A record that is
  only partly null is kept with its nulls preserved (the pinned file has none).
* Raw count 1,642 (paper); scorable count 1,638; 4 excluded.
* All downstream statistics are over scorable records and ignore nulls.

Outputs:

* data/mast/processed/mast_clean_summary.csv (gitignored; null labels are empty cells)
* data/mast/EDA_SUMMARY.json (committed; deterministic, byte-identical across runs)

The cleaning logic is split into pure functions (clean_records, flatten_rows,
build_summary, ...) that take records and return results, so tests do not need
the 190 MB file.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MAST = ROOT / "data" / "mast"
FULL = MAST / "hf" / "MAD_full_dataset.json"
HUMAN = MAST / "hf" / "MAD_human_labelled_dataset.json"
TAX_DEF = MAST / "taxonomy" / "definitions.txt"
MANIFEST = MAST / "eval_manifest.json"
OUT_DIR = MAST / "processed"
OUT_CSV = OUT_DIR / "mast_clean_summary.csv"
OUT_SUMMARY = MAST / "EDA_SUMMARY.json"

REPRODUCE_COMMAND = "python data/scripts/download_mast.py && python data/scripts/eda_mast.py"

# Paper: 14 failure modes in 3 categories (Cemri et al., 2025)
EXPECTED_CODES = [
    "1.1", "1.2", "1.3", "1.4", "1.5",
    "2.1", "2.2", "2.3", "2.4", "2.5", "2.6",
    "3.1", "3.2", "3.3",
]  # fmt: skip
CATEGORY = {
    "1": "Specification issues",
    "2": "Inter-agent misalignment",
    "3": "Task verification / termination",
}
# Mirror of data/mast/eval_manifest.json (reference_sources[0]). main() reads the
# manifest and cross-checks; these are the fallback when the manifest is absent.
EXPECTED_RAW = 1642
EXPECTED_SCORABLE = 1638
EXPECTED_EXCLUDED = (
    ("ChatDev_ProgramDev-v2_CodeLlama", 4),
    ("ChatDev_ProgramDev-v2_CodeLlama", 72),
    ("ChatDev_ProgramDev-v2_CodeLlama", 73),
    ("ChatDev_ProgramDev-v2_CodeLlama", 81),
)

RecordKey = tuple[str, int]


class EdaError(ValueError):
    """Base class for hard data errors (never silently dropped)."""


class InvalidLabelError(EdaError):
    """A label that is not exactly 0, 1, bool, or null."""


class InvalidRecordError(EdaError):
    """A record that is structurally unusable (no key, no annotation object)."""


class DuplicateKeyError(EdaError):
    """(trace_key, trace_id) is not unique."""


@dataclass
class CleanResult:
    """Output of clean_records. `labels` use None for null; never 0 for null."""

    raw: list[dict[str, Any]]  # every raw record, source order
    scorable: list[dict[str, Any]]
    excluded: list[RecordKey]  # fully-null records, source order
    partial_null: list[RecordKey]  # kept, but some (not all) codes null
    key_count: int  # distinct keys over ALL raw records


# --------------------------------------------------------------------------
# Pure logic
# --------------------------------------------------------------------------


def is_valid_label(v: Any) -> bool:
    """True only for exact 0/1 ints or bools. Floats (1.0) and strings are invalid."""
    return isinstance(v, bool) or (type(v) is int and v in (0, 1))


def normalize_labels(ann: dict, key: RecordKey) -> dict[str, int | None]:
    """Return {code: 0|1|None}. A missing code is None. Anything invalid raises."""
    out: dict[str, int | None] = {}
    for code in EXPECTED_CODES:
        v = ann.get(code)  # missing key and explicit null are both None
        if v is None:
            out[code] = None
        elif is_valid_label(v):
            out[code] = int(v)
        else:
            raise InvalidLabelError(f"record {key}: code {code} has non-binary value {v!r}")
    return out


def check_key_uniqueness(keys: list[RecordKey]) -> int:
    """Raise DuplicateKeyError listing the duplicates; else return distinct count."""
    counts = Counter(keys)
    dups = sorted(k for k, n in counts.items() if n > 1)
    if dups:
        raise DuplicateKeyError(
            f"{len(dups)} duplicate (trace_key, trace_id) keys: {dups}"
        )
    return len(counts)


def extract_key(r: dict, idx: int) -> RecordKey:
    trace = r.get("trace")
    trace_key = trace.get("key") if isinstance(trace, dict) else None
    tid = r.get("trace_id")
    if not isinstance(trace_key, str) or not trace_key:
        raise InvalidRecordError(f"record at index {idx}: missing trace.key")
    if type(tid) is not int:
        raise InvalidRecordError(f"record at index {idx}: trace_id {tid!r} is not an int")
    return (trace_key, tid)


def clean_records(full: list) -> CleanResult:
    """Normalize every raw record, enforce key uniqueness, split scorable/excluded."""
    raw: list[dict[str, Any]] = []
    for idx, r in enumerate(full):
        if not isinstance(r, dict):
            raise InvalidRecordError(f"record at index {idx} is not an object")
        key = extract_key(r, idx)
        ann = r.get("mast_annotation")
        if not isinstance(ann, dict):
            raise InvalidRecordError(f"record {key}: mast_annotation is not an object")
        traj = (r.get("trace") or {}).get("trajectory")
        labels = normalize_labels(ann, key)
        raw.append(
            {
                "trace_key": key[0],
                "trace_id": key[1],
                "mas_name": str(r.get("mas_name") or "unknown").strip(),
                "llm_name": str(r.get("llm_name") or "unknown").strip(),
                "benchmark_name": str(r.get("benchmark_name") or "unknown").strip(),
                "labels": labels,
                "trace_chars": len(str(traj)) if traj else 0,
            }
        )
    key_count = check_key_uniqueness([(r["trace_key"], r["trace_id"]) for r in raw])

    scorable, excluded, partial = [], [], []
    for r in raw:
        n_null = sum(1 for v in r["labels"].values() if v is None)
        k = (r["trace_key"], r["trace_id"])
        if n_null == len(EXPECTED_CODES):
            excluded.append(k)
            continue
        if n_null:
            partial.append(k)
        scorable.append(r)
    return CleanResult(raw, scorable, excluded, partial, key_count)


def _col(code: str) -> str:
    return f"fail_{code.replace('.', '_')}"


def flatten_rows(scorable: list[dict]) -> list[dict]:
    """Flat analysis rows. Null labels stay None; counts ignore nulls."""
    out = []
    for r in scorable:
        lab = r["labels"]
        active = [c for c, v in lab.items() if v == 1]
        cat = Counter(CATEGORY[c[0]] for c in active)
        out.append(
            {
                "trace_key": r["trace_key"],
                "trace_id": r["trace_id"],
                "mas_name": r["mas_name"],
                "llm_name": r["llm_name"],
                "benchmark_name": r["benchmark_name"],
                "trace_chars": r["trace_chars"],
                "n_failures": len(active),
                "n_null_labels": sum(1 for v in lab.values() if v is None),
                "failure_codes": "|".join(active),
                "cat_specification": cat.get("Specification issues", 0),
                "cat_misalignment": cat.get("Inter-agent misalignment", 0),
                "cat_verification": cat.get("Task verification / termination", 0),
                **{_col(c): lab[c] for c in EXPECTED_CODES},
            }
        )
    return out


def write_csv(rows: list[dict], path: Path) -> list[str]:
    """Write rows; None becomes an empty cell (never 0). Returns the field names."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows({k: ("" if v is None else v) for k, v in r.items()} for r in rows)
    return fieldnames


def label_counts(records: list[dict]) -> dict[str, dict[str, int]]:
    """Per-code counts of 1 / 0 / null, fixed code order."""
    out = {}
    for c in EXPECTED_CODES:
        vals = [r["labels"][c] for r in records]
        out[c] = {
            "1": sum(1 for v in vals if v == 1),
            "0": sum(1 for v in vals if v == 0),
            "null": sum(1 for v in vals if v is None),
        }
    return out


def build_summary(result: CleanResult, input_sha256: dict[str, str]) -> dict:
    """Deterministic summary: no timestamps, no absolute paths."""
    hist = Counter(sum(1 for v in r["labels"].values() if v == 1) for r in result.scorable)
    return {
        "record_key_fields": ["trace.key", "trace_id"],
        "key_uniqueness": {
            "distinct_keys": result.key_count,
            "raw_records": len(result.raw),
            "unique": result.key_count == len(result.raw),
            "duplicates": [],
        },
        "raw_record_count": len(result.raw),
        "scorable_record_count": len(result.scorable),
        "excluded_record_count": len(result.excluded),
        "excluded_records": [
            {"trace_key": k, "trace_id": i} for k, i in sorted(result.excluded)
        ],
        "excluded_reason": "all 14 mast_annotation codes are null",
        "partial_null_record_count": len(result.partial_null),
        "null_label_cells_raw": sum(
            1 for r in result.raw for v in r["labels"].values() if v is None
        ),
        "label_counts_raw": label_counts(result.raw),
        "label_counts_scorable": label_counts(result.scorable),
        "scorable_records_with_any_failure": sum(
            1 for r in result.scorable if any(v == 1 for v in r["labels"].values())
        ),
        "n_failures_histogram_scorable": {str(k): hist[k] for k in sorted(hist)},
        "null_policy": "null and missing labels stay null; never converted to 0",
        "input_sha256": dict(sorted(input_sha256.items())),
        "reproduce": REPRODUCE_COMMAND,
    }


def write_summary(summary: dict, path: Path) -> None:
    """Sorted keys, fixed indent, LF newlines: byte-identical for equal input."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def load_manifest_expectations(path: Path = MANIFEST) -> dict[str, Any]:
    """Read raw/scorable counts and excluded keys for the full file from the manifest."""
    m = json.loads(path.read_text(encoding="utf-8"))
    src = next(s for s in m["reference_sources"] if s["source_file"].endswith(FULL.name))
    return {
        "raw": src["total_record_count"],
        "scorable": src["scorable_record_count"],
        "excluded": sorted((e["trace_key"], e["trace_id"]) for e in src["excluded_records"]),
    }


# --------------------------------------------------------------------------
# Stages (print + I/O wrappers around the pure functions)
# --------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path):
    if not path.is_file():
        raise SystemExit(f"Missing {path}\nRun: python data/scripts/download_mast.py")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def stage1_extract() -> tuple[list, list, str, dict[str, str]]:
    print("=" * 60)
    print("STAGE 1: DATA EXTRACTION")
    print("=" * 60)
    full = _load(FULL)
    human = _load(HUMAN)
    tax = TAX_DEF.read_text(encoding="utf-8") if TAX_DEF.is_file() else ""
    shas = {FULL.name: _sha256(FULL), HUMAN.name: _sha256(HUMAN)}
    if TAX_DEF.is_file():
        shas[TAX_DEF.name] = _sha256(TAX_DEF)
    print(f"  Source A (HF MAD full):     {FULL}")
    print(f"    records: {len(full)}")
    print(f"    sha256:  {shas[FULL.name][:16]}...")
    print(f"  Source B (HF human labels): {HUMAN}")
    print(f"    records: {len(human)}")
    print(f"  Source C (taxonomy defs):   {TAX_DEF}")
    print(f"    chars:   {len(tax)}")
    print(f"  Provenance write-up:        {MAST / 'STATS.md'}")
    print("  Fields extracted per row: mas_name, llm_name, benchmark_name,")
    print("    trace_id, trace.key, trace.trajectory, mast_annotation (14 codes)")
    return full, human, tax, shas


def stage2_clean(full: list) -> CleanResult:
    print()
    print("=" * 60)
    print("STAGE 2: CLEANING")
    print("=" * 60)
    res = clean_records(full)
    n_null_cells = sum(1 for r in res.raw for v in r["labels"].values() if v is None)
    print(f"  raw records:                 {len(res.raw)}")
    print(f"  distinct (trace_key, trace_id): {res.key_count}")
    print(f"  excluded (all 14 codes null): {len(res.excluded)}")
    for k in sorted(res.excluded):
        print(f"    - {k}")
    print(f"  scorable records:            {len(res.scorable)}")
    print(f"  partially-null (kept):       {len(res.partial_null)}")
    print(f"  null label cells (preserved as null): {n_null_cells}")
    print("  Cleaning rules applied:")
    print("    - canonical key is (trace.key, trace_id); uniqueness checked on all raw rows")
    print("    - labels must be exactly 0/1 or null; anything else is a hard error")
    print("    - missing and null codes stay null (never converted to 0)")
    print("    - exclude a record only if all 14 codes are null")
    return res


def stage3_preprocess(scorable: list[dict]) -> list[dict]:
    print()
    print("=" * 60)
    print("STAGE 3: PREPROCESSING")
    print("=" * 60)
    out = flatten_rows(scorable)
    fieldnames = write_csv(out, OUT_CSV)
    print("  Feature engineering (scorable records only):")
    print("    - flatten 14 labels into columns; null labels are empty cells")
    print("    - derive n_failures (count of 1s) and pipe-joined failure_codes")
    print("    - roll up into 3 MAST categories (spec / misalignment / verification)")
    print(f"  Wrote analysis table: {OUT_CSV}")
    print(f"  rows x cols: {len(out)} x {len(fieldnames)}")
    return out


def stage4_quality(
    res: CleanResult, rows: list[dict], human: list, tax: str, shas: dict[str, str]
) -> None:
    print()
    print("=" * 60)
    print("STAGE 4: QUALITY ASSESSMENT")
    print("=" * 60)
    checks = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append(ok)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}: {detail}")

    if MANIFEST.is_file():
        exp = load_manifest_expectations()
        source = "eval_manifest.json"
    else:
        exp = {"raw": EXPECTED_RAW, "scorable": EXPECTED_SCORABLE,
               "excluded": sorted(EXPECTED_EXCLUDED)}  # fmt: skip
        source = "built-in constants (manifest missing)"
    print(f"  Expectations from: {source}")

    check("Raw record count", len(res.raw) == exp["raw"],
          f"raw {len(res.raw)}, expected {exp['raw']}")  # fmt: skip
    check("Scorable record count", len(res.scorable) == exp["scorable"],
          f"scorable {len(res.scorable)}, expected {exp['scorable']}")  # fmt: skip
    check("Excluded record count", len(res.excluded) == len(exp["excluded"]),
          f"excluded {len(res.excluded)}, expected {len(exp['excluded'])}")  # fmt: skip
    check("Excluded keys match manifest", sorted(res.excluded) == exp["excluded"],
          f"{sorted(res.excluded)}")  # fmt: skip
    check("Partially-null records", len(res.partial_null) == 0,
          f"{len(res.partial_null)} (expected 0)")  # fmt: skip
    check("Unique (trace_key, trace_id)", res.key_count == len(res.raw),
          f"{len(res.raw)} raw records, {res.key_count} unique keys")  # fmt: skip

    check(
        "Schema completeness",
        len(rows) > 0
        and all(_col(c) in rows[0] for c in EXPECTED_CODES)
        and all(r["mas_name"] and r["llm_name"] and r["trace_key"] for r in rows),
        "identity fields + 14 label columns present",
    )

    bad_vals = sum(
        1 for r in rows for c in EXPECTED_CODES if r[_col(c)] not in (0, 1, None)
    )
    check("Label domain (0/1/null only)", bad_vals == 0, f"invalid cells={bad_vals}")

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

    # distribution summary (scorable records only, null-aware)
    print()
    print("  Distribution summary (scorable records only):")
    print(f"    frameworks: {len({r['mas_name'] for r in rows})}")
    print(f"    LLMs:       {len({r['llm_name'] for r in rows})}")
    print(f"    benchmarks: {len({r['benchmark_name'] for r in rows})}")
    print("    Top frameworks:")
    for name, n in Counter(r["mas_name"] for r in rows).most_common(7):
        print(f"      {n:4d}  {name}")
    counts = label_counts(res.scorable)
    top = sorted(EXPECTED_CODES, key=lambda c: (-counts[c]["1"], c))[:5]
    print("    Top failure modes:")
    for code in top:
        print(f"      {counts[code]['1']:4d}  {code}  ({CATEGORY[code[0]]})")
    any_fail = sum(1 for r in rows if r["n_failures"] > 0)
    chars = sorted(r["trace_chars"] for r in rows)
    print(
        f"    traces with >=1 failure: {any_fail}/{len(rows)} "
        f"({100 * any_fail / len(rows):.1f}%)"
    )
    print(
        f"    trace length (chars): min={chars[0]}  "
        f"median={chars[len(chars) // 2]}  max={chars[-1]}"
    )

    write_summary(build_summary(res, shas), OUT_SUMMARY)
    print(f"  Wrote committed summary: {OUT_SUMMARY}")

    print()
    if all(checks):
        print("QUALITY GATE: all checks passed. Dataset ready for baseline / eval use.")
    else:
        print("QUALITY GATE: one or more checks failed. Do not freeze this manifest.")
        raise SystemExit(1)


def main() -> int:
    print("Demo 1: Data Extraction, Cleaning, Preprocessing, and Quality Assessment")
    print("Dataset: MAST-Data (Cemri et al., 2025), baseline reproduction path\n")
    full, human, tax, shas = stage1_extract()
    try:
        res = stage2_clean(full)
    except EdaError as e:
        print(f"\nHARD ERROR: {e}")
        return 1
    processed = stage3_preprocess(res.scorable)
    stage4_quality(res, processed, human, tax, shas)
    print()
    print("Artifacts to show:")
    print(f"  - {MAST / 'STATS.md'}")
    print(f"  - {FULL}")
    print(f"  - {TAX_DEF}")
    print(f"  - {OUT_CSV}")
    print(f"  - {OUT_SUMMARY}")
    print()
    print(f"Reproduce: {REPRODUCE_COMMAND}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
