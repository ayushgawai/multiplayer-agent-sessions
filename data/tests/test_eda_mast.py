"""Unit tests for data/scripts/eda_mast.py (DAT-54 / MAST-17).

Owner: Naman Chheda. Synthetic fixtures only; no network. The final test runs
against the real MAD_full_dataset.json and skips cleanly when it is absent.

Run with: pytest data/tests/test_eda_mast.py -q
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import eda_mast as eda  # noqa: E402

CODES = eda.EXPECTED_CODES


def rec(trace_key="KeyA", trace_id=0, labels=None, **over):
    """Build a raw record. `labels` maps code -> value; unspecified codes default to 0.

    Pass labels=ALL_NULL for a fully-null record, or a dict with None / omitted
    (via MISSING) codes for the other cases.
    """
    ann = {c: 0 for c in CODES}
    for c, v in (labels or {}).items():
        if v is MISSING:
            ann.pop(c, None)
        else:
            ann[c] = v
    r = {
        "mas_name": "FW",
        "llm_name": "LLM",
        "benchmark_name": "BM",
        "trace_id": trace_id,
        "trace": {"key": trace_key, "trajectory": "some text"},
        "mast_annotation": ann,
    }
    r.update(over)
    return r


MISSING = object()
ALL_NULL = {c: None for c in CODES}


@pytest.fixture
def good():
    return [
        rec("KeyA", 0, {"1.1": 1}),
        rec("KeyA", 1, {"2.6": 1, "3.3": 1}),
        rec("KeyB", 0),  # same trace_id under a different trace_key: allowed
        rec("KeyB", 1, ALL_NULL),  # fully null: excluded
    ]


# ---- counts, exclusion -------------------------------------------------


def test_raw_vs_scorable_counts(good):
    res = eda.clean_records(good)
    assert len(res.raw) == 4
    assert len(res.scorable) == 3
    assert len(res.excluded) == 1


def test_fully_null_record_excluded_and_key_reported(good):
    res = eda.clean_records(good)
    assert res.excluded == [("KeyB", 1)]
    assert ("KeyB", 1) not in {(r["trace_key"], r["trace_id"]) for r in res.scorable}


def test_partially_null_record_kept_with_null_preserved():
    partial = rec("KeyA", 0, {"1.1": None, "1.2": 1})
    res = eda.clean_records([partial])
    assert len(res.scorable) == 1
    assert res.partial_null == [("KeyA", 0)]
    assert res.scorable[0]["labels"]["1.1"] is None
    assert res.scorable[0]["labels"]["1.2"] == 1


def test_missing_code_key_is_null_not_zero():
    res = eda.clean_records([rec("KeyA", 0, {"2.3": MISSING})])
    assert res.scorable[0]["labels"]["2.3"] is None
    assert res.partial_null == [("KeyA", 0)]


def test_record_missing_every_code_is_excluded():
    r = rec("KeyA", 0)
    r["mast_annotation"] = {}
    res = eda.clean_records([r])
    assert res.excluded == [("KeyA", 0)]
    assert res.scorable == []


def test_bool_labels_are_accepted_as_ints():
    res = eda.clean_records([rec("KeyA", 0, {"1.1": True, "1.2": False})])
    assert res.scorable[0]["labels"]["1.1"] == 1
    assert res.scorable[0]["labels"]["1.2"] == 0


@pytest.mark.parametrize("bad", [2, -1, "1", "yes", 1.0, 0.5, [1], {}])
def test_non_binary_value_raises(bad):
    with pytest.raises(eda.InvalidLabelError, match=r"1\.4"):
        eda.clean_records([rec("KeyA", 0, {"1.4": bad})])


def test_record_without_trace_key_raises():
    r = rec("KeyA", 0)
    del r["trace"]["key"]
    with pytest.raises(eda.InvalidRecordError, match="trace.key"):
        eda.clean_records([r])


# ---- no null is ever 0 -------------------------------------------------


def test_no_null_becomes_zero_in_rows_csv_or_summary(tmp_path):
    data = [
        rec("KeyA", 0, {"1.1": None, "1.2": MISSING, "1.3": 1}),
        rec("KeyA", 1, ALL_NULL),
        rec("KeyA", 2),
    ]
    res = eda.clean_records(data)

    rows = eda.flatten_rows(res.scorable)
    partial = next(r for r in rows if r["trace_id"] == 0)
    assert partial["fail_1_1"] is None and partial["fail_1_2"] is None
    assert partial["fail_1_3"] == 1
    assert partial["n_failures"] == 1  # nulls are not counted as anything
    assert partial["n_null_labels"] == 2

    path = tmp_path / "out.csv"
    eda.write_csv(rows, path)
    with path.open(newline="", encoding="utf-8") as f:
        csv_rows = {int(r["trace_id"]): r for r in csv.DictReader(f)}
    assert csv_rows[0]["fail_1_1"] == "" and csv_rows[0]["fail_1_2"] == ""
    assert csv_rows[0]["fail_1_3"] == "1"
    assert csv_rows[2]["fail_1_1"] == "0"
    assert 1 not in csv_rows  # excluded record is not in the CSV
    assert "trace_key" in csv_rows[0]

    summary = eda.build_summary(res, {"f.json": "0" * 64})
    c = summary["label_counts_raw"]["1.1"]
    assert c == {"1": 0, "0": 1, "null": 2}  # two null records on 1.1, one zero
    assert summary["label_counts_scorable"]["1.1"] == {"1": 0, "0": 1, "null": 1}
    assert summary["label_counts_scorable"]["1.2"] == {"1": 0, "0": 1, "null": 1}
    assert summary["null_label_cells_raw"] == 14 + 2


# ---- key uniqueness ----------------------------------------------------


def test_keys_unique_on_good_data(good):
    res = eda.clean_records(good)
    assert res.key_count == len(good)


def test_same_trace_id_across_trace_keys_is_allowed():
    res = eda.clean_records([rec("KeyA", 5), rec("KeyB", 5), rec("KeyC", 5)])
    assert res.key_count == 3


def test_duplicate_key_raises_with_key_in_message():
    with pytest.raises(eda.DuplicateKeyError, match=r"KeyA.*7"):
        eda.clean_records([rec("KeyA", 7), rec("KeyB", 7), rec("KeyA", 7)])


def test_duplicate_among_fully_null_records_still_detected():
    # uniqueness is checked over ALL raw records, not just scorable ones
    with pytest.raises(eda.DuplicateKeyError, match="KeyZ"):
        eda.clean_records([rec("KeyZ", 1, ALL_NULL), rec("KeyZ", 1, ALL_NULL)])


# ---- summary determinism ----------------------------------------------


def test_summary_file_is_byte_identical_across_runs(good, tmp_path):
    shas = {"b.json": "b" * 64, "a.json": "a" * 64}
    p1, p2 = tmp_path / "s1.json", tmp_path / "s2.json"
    eda.write_summary(eda.build_summary(eda.clean_records(good), shas), p1)
    eda.write_summary(eda.build_summary(eda.clean_records(list(good)), shas), p2)
    assert p1.read_bytes() == p2.read_bytes()
    text = p1.read_text(encoding="utf-8")
    assert text.endswith("\n") and "\r" not in text
    data = json.loads(text)
    assert data["raw_record_count"] == 4
    assert data["scorable_record_count"] == 3
    assert data["excluded_records"] == [{"trace_key": "KeyB", "trace_id": 1}]
    assert data["key_uniqueness"]["unique"] is True
    assert str(tmp_path) not in text  # no absolute paths


# ---- real data ---------------------------------------------------------


@pytest.mark.skipif(not eda.FULL.is_file(), reason="MAD_full_dataset.json not downloaded")
def test_real_data_counts_and_excluded_keys():
    with eda.FULL.open(encoding="utf-8") as f:
        full = json.load(f)
    res = eda.clean_records(full)
    assert len(res.raw) == 1642
    assert len(res.scorable) == 1638
    assert res.key_count == 1642
    assert res.partial_null == []
    assert sorted(res.excluded) == [
        ("ChatDev_ProgramDev-v2_CodeLlama", 4),
        ("ChatDev_ProgramDev-v2_CodeLlama", 72),
        ("ChatDev_ProgramDev-v2_CodeLlama", 73),
        ("ChatDev_ProgramDev-v2_CodeLlama", 81),
    ]
    if eda.MANIFEST.is_file():
        exp = eda.load_manifest_expectations()
        assert exp["raw"] == 1642 and exp["scorable"] == 1638
        assert exp["excluded"] == sorted(res.excluded)
