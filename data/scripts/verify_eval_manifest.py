"""MAST 06 (DAT-30): verify data/mast/eval_manifest.json against the raw dataset files.

Owner: Naman Chheda. Lives under data/ only.

This is deliberately a standalone check, not a pytest suite: it recomputes facts
straight from the files on disk (never trusting the manifest's own numbers back
against itself) and exits non-zero on the first thing that doesn't hold. Run it
after any manual edit to eval_manifest.json, and before any push that touches it.

Checks
------
1. reference_sources[*].reference_type is exactly {released_llm_annotation,
   human_consensus}, one of each, and no record ever mixes the two label fields
   (mast_annotation vs. human_majority_labels).
2. The released_llm_annotation entry's label_field is still "mast_annotation"
   (never renamed to human_labels or anything else: those are LLM-judge labels).
3. The record key (trace.key, trace_id) resolves with zero collisions across the
   full MAD_full_dataset.json on disk, matching the manifest's record_key.fields
   and record_key.note.
4. The dataset file checksums, sizes, and record counts in the manifest match
   what's actually on disk right now (catches a stale manifest after a
   re-download).
5. The human_consensus block's majority-vote labels are independently
   recomputed from MAD_human_labelled_dataset.json and match the manifest
   exactly, record for record, code for code.

Usage
-----
    python data/scripts/verify_eval_manifest.py
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "mast"
HF_DIR = DATA_DIR / "hf"
MANIFEST_PATH = DATA_DIR / "eval_manifest.json"

EXPECTED_REFERENCE_TYPES = {"released_llm_annotation", "human_consensus"}
ANN = ("annotator_1", "annotator_2", "annotator_3")


class VerificationError(RuntimeError):
    """A manifest check failed."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _missing(v: object) -> bool:
    return isinstance(v, float) and math.isnan(v)


def _majority_vote(entry: dict) -> int | None:
    valid = [entry[k] for k in ANN if not _missing(entry[k])]
    true_count = sum(1 for v in valid if v is True)
    false_count = len(valid) - true_count
    if true_count >= 2:
        return 1
    if false_count >= 2:
        return 0
    return None


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise VerificationError(f"{MANIFEST_PATH} does not exist.")
    with MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def check_reference_types(manifest: dict) -> list[str]:
    checks: list[str] = []
    sources = manifest.get("reference_sources", [])
    types = [s.get("reference_type") for s in sources]
    type_set = set(types)

    if type_set != EXPECTED_REFERENCE_TYPES:
        raise VerificationError(
            f"reference_sources reference_type values are {type_set!r}, "
            f"expected exactly {EXPECTED_REFERENCE_TYPES!r}."
        )
    checks.append(f"reference_type values are exactly {sorted(EXPECTED_REFERENCE_TYPES)}.")

    if sorted(types) != sorted(EXPECTED_REFERENCE_TYPES):
        raise VerificationError(f"expected exactly one entry per reference_type, got {types!r}.")
    checks.append("exactly one reference_sources entry per reference_type (no duplicates).")

    label_fields = {s["reference_type"]: s.get("label_field") for s in sources}
    if label_fields.get("released_llm_annotation") != "mast_annotation":
        raise VerificationError(
            "released_llm_annotation.label_field must be 'mast_annotation' (unchanged from "
            f"the source file); got {label_fields.get('released_llm_annotation')!r}."
        )
    checks.append("released_llm_annotation.label_field is still 'mast_annotation'.")

    if label_fields.get("human_consensus") == "mast_annotation":
        raise VerificationError(
            "human_consensus.label_field must not be 'mast_annotation': that field name is "
            "reserved for the LLM-judge labels, and reusing it here would conflate the two "
            "reference sources on the same key."
        )
    checks.append(
        f"human_consensus.label_field is {label_fields.get('human_consensus')!r}, "
        "distinct from 'mast_annotation'."
    )

    human_source = next(s for s in sources if s["reference_type"] == "human_consensus")
    human_field = human_source["label_field"]
    for rec in human_source.get("records", []):
        if "mast_annotation" in rec:
            raise VerificationError(
                f"human_consensus record trace_id={rec.get('trace_id')} carries a "
                "'mast_annotation' key; the two reference sources must never be mixed on "
                "the same record."
            )
        if human_field not in rec:
            raise VerificationError(
                f"human_consensus record trace_id={rec.get('trace_id')} is missing its own "
                f"label field {human_field!r}."
            )
    checks.append(
        f"no human_consensus record carries a 'mast_annotation' key; all carry {human_field!r}."
    )
    return checks


def check_record_key_no_collisions(manifest: dict) -> list[str]:
    checks: list[str] = []
    fields = manifest.get("record_key", {}).get("fields")
    if fields != ["trace.key", "trace_id"]:
        raise VerificationError(f"record_key.fields is {fields!r}, expected ['trace.key', 'trace_id'].")

    full_path = HF_DIR / "MAD_full_dataset.json"
    with full_path.open("r", encoding="utf-8") as fh:
        full = json.load(fh)

    keys = [(r["trace"]["key"], r["trace_id"]) for r in full]
    if len(keys) != len(set(keys)):
        seen: set[tuple[str, int]] = set()
        dupes = []
        for k in keys:
            if k in seen:
                dupes.append(k)
            seen.add(k)
        raise VerificationError(
            f"(trace.key, trace_id) collides for {len(dupes)} record(s) in "
            f"MAD_full_dataset.json, e.g. {dupes[:5]!r}."
        )
    checks.append(
        f"(trace.key, trace_id) resolves without collisions across all {len(full)} records "
        "in MAD_full_dataset.json."
    )
    return checks


def check_dataset_files(manifest: dict) -> list[str]:
    checks: list[str] = []
    for entry in manifest["dataset"]["files"]:
        path = REPO_ROOT / entry["relative_path"]
        if not path.exists():
            raise VerificationError(f"{path} (from manifest) does not exist on disk.")

        actual_size = path.stat().st_size
        if actual_size != entry["size_bytes"]:
            raise VerificationError(
                f"{entry['filename']}: manifest size {entry['size_bytes']}, actual "
                f"{actual_size}."
            )

        actual_sha256 = sha256_of(path)
        if actual_sha256 != entry["sha256"]:
            raise VerificationError(
                f"{entry['filename']}: manifest sha256 {entry['sha256']}, actual "
                f"{actual_sha256}."
            )
        checks.append(f"{entry['filename']}: size and sha256 match the manifest.")

        if "record_count" in entry:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
            actual_count = len(payload) if isinstance(payload, list) else None
            if actual_count != entry["record_count"]:
                raise VerificationError(
                    f"{entry['filename']}: manifest record_count {entry['record_count']}, "
                    f"actual {actual_count}."
                )
            checks.append(f"{entry['filename']}: record_count matches the manifest.")
    return checks


def check_human_consensus_labels(manifest: dict) -> list[str]:
    checks: list[str] = []
    human_path = HF_DIR / "MAD_human_labelled_dataset.json"
    with human_path.open("r", encoding="utf-8") as fh:
        human = json.load(fh)

    source = next(s for s in manifest["reference_sources"] if s["reference_type"] == "human_consensus")
    manifest_by_id = {rec["trace_id"]: rec["human_majority_labels"] for rec in source["records"]}

    recomputed_ids = set()
    for r in human:
        if r["round"] != "Generlazability":
            continue
        recomputed_ids.add(r["trace_id"])
        recomputed = {}
        for a in r["annotations"]:
            code = a["failure mode"].split()[0]
            recomputed[code] = _majority_vote(a)

        if r["trace_id"] not in manifest_by_id:
            raise VerificationError(
                f"trace_id {r['trace_id']} (Generlazability round) is on disk but missing "
                "from the manifest's human_consensus records."
            )
        if manifest_by_id[r["trace_id"]] != recomputed:
            raise VerificationError(
                f"trace_id {r['trace_id']}: manifest labels {manifest_by_id[r['trace_id']]!r} "
                f"do not match recomputed majority vote {recomputed!r}."
            )

    if recomputed_ids != set(manifest_by_id):
        raise VerificationError(
            f"manifest human_consensus record set {sorted(manifest_by_id)} does not match "
            f"the Generlazability round on disk {sorted(recomputed_ids)}."
        )
    checks.append(
        f"human_consensus majority-vote labels for all {len(recomputed_ids)} Generlazability "
        "records match an independent recomputation from MAD_human_labelled_dataset.json."
    )
    return checks


def main() -> int:
    try:
        manifest = load_manifest()
        checks = []
        checks += check_reference_types(manifest)
        checks += check_record_key_no_collisions(manifest)
        checks += check_dataset_files(manifest)
        checks += check_human_consensus_labels(manifest)
    except VerificationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"FAIL (could not complete verification): {exc!r}", file=sys.stderr)
        return 1

    print(f"PASS: {len(checks)} checks against {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    for c in checks:
        print(f"  - {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
