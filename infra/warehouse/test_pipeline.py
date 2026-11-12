"""Pipeline test on tiny synthetic fixtures (no real data needed)."""

import hashlib
import json
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
import pipeline  # noqa: E402

CODES = pipeline.EXPECTED_CODES


def rec(i, labels):
    return {"mas_name": "AG2", "llm_name": "GPT-4o", "benchmark_name": "GSM", "trace_id": i,
            "trace": {"key": "k", "trajectory": "x" * 800}, "mast_annotation": labels}  # fmt: skip


def build(tmp_path, bad=False):
    root = tmp_path / "data"
    (root / "mast" / "hf").mkdir(parents=True)
    (root / "splits" / "m1_v1").mkdir(parents=True)
    ones = {c: 0 for c in CODES} | {"1.1": 1, "2.3": 1}
    recs = [rec(0, ones), rec(1, {c: 0 for c in CODES}), rec(2, {c: None for c in CODES})]
    if bad:
        recs[1]["mast_annotation"]["1.2"] = 2
    full = root / "mast" / "hf" / pipeline.FULL_NAME
    full.write_text(json.dumps(recs))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    (root / "mast" / "EDA_SUMMARY.json").write_text(json.dumps({
        "input_sha256": {pipeline.FULL_NAME: sha(full)}, "raw_record_count": 3,
        "scorable_record_count": 2, "excluded_record_count": 1}))  # fmt: skip
    manifest = {"splits": {}}
    for s, n in (("train", 2), ("val", 1), ("test", 1)):
        rows = [{"id": f"qmsum_{s}_{j}_s0", "query": " q ", "reference_summary": "a b c",
                 "context_spans": [f"{s} meeting {j} text"]} for j in range(n)]  # fmt: skip
        f = root / "splits" / "m1_v1" / f"{s}.jsonl"
        f.write_text("\n".join(json.dumps(r) for r in rows))
        manifest["splits"][s] = {"count": n, "sha256": sha(f)}
    (root / "splits" / "m1_v1" / "MANIFEST.json").write_text(json.dumps(manifest))
    return root


def test_full_run_layer_counts(tmp_path):
    db = str(tmp_path / "t.duckdb")
    assert pipeline.run(db, build(tmp_path)) == 0
    con = duckdb.connect(db)

    def n(t):
        return con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]

    assert (n("raw.mast_traces"), n("staging.mast_traces_clean")) == (3, 2)
    assert n("staging.mast_labels_long") == 2 * 14
    assert (n("marts.fact_trace"), n("marts.fact_trace_failure")) == (2, 2)
    assert n("marts.fact_m1_example") == 4
    assert n("marts.dim_failure_mode") == 14
    assert con.execute("SELECT max(length(trajectory_preview)) FROM raw.mast_traces").fetchone()[0] == 500
    assert n("meta.quality_checks WHERE NOT passed") == 0
    assert pipeline.run(db, tmp_path / "data") == 0  # idempotent: layers replaced, history appended
    assert n("marts.fact_trace") == 2 and n("meta.pipeline_runs") == 8


def test_bad_label_fails_run(tmp_path):
    db = str(tmp_path / "t.duckdb")
    assert pipeline.run(db, build(tmp_path, bad=True)) == 1
    status = dict(duckdb.connect(db).execute("SELECT stage, status FROM meta.pipeline_runs").fetchall())
    assert status == {"ingest": "success", "clean": "failed"}  # fail-fast: later stages never ran


def test_tampered_source_fails_ingest(tmp_path):
    root = build(tmp_path)
    (root / "mast" / "hf" / pipeline.FULL_NAME).write_text("[]")
    assert pipeline.run(str(tmp_path / "t.duckdb"), root) == 1
