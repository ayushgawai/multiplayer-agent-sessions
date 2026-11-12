"""Source -> DuckDB warehouse demo pipeline (stdlib + duckdb).

    ingest -> clean -> transform -> quality -> (monitoring in meta.*)

Layers (DuckDB schemas): raw -> staging -> marts, plus meta (run history, checks).
Each stage is timed, logged, fail-fast, and recorded in meta.pipeline_runs.
Re-running replaces the layer tables and appends to the run history.

    python infra/warehouse/pipeline.py                 # full run
    python infra/warehouse/pipeline.py --stage clean   # one stage (needs earlier layers)
    python infra/warehouse/pipeline.py --report        # run history + checks + analytics
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "data" / "scripts"))
# Reuse the frozen MAST cleaning rules rather than re-implementing them.
from eda_mast import (  # noqa: E402
    CATEGORY,
    EXPECTED_CODES,
    EdaError,
    check_key_uniqueness,
    normalize_labels,
)

MODE_NAMES = {
    "1.1": "Disobey Task Specification", "1.2": "Disobey Role Specification",
    "1.3": "Step Repetition", "1.4": "Loss of Conversation History",
    "1.5": "Unaware of Termination Conditions", "2.1": "Conversation Reset",
    "2.2": "Fail to Ask for Clarification", "2.3": "Task Derailment",
    "2.4": "Information Withholding", "2.5": "Ignored Other Agent's Input",
    "2.6": "Action-Reasoning Mismatch", "3.1": "Premature Termination",
    "3.2": "Weak Verification", "3.3": "No or Incorrect Verification",
}  # fmt: skip
RUN = {"id": ""}  # current run id, read by the quality stage
SPLITS = ("train", "val", "test")
FULL_NAME = "MAD_full_dataset.json"
PREVIEW = 500


class PipelineError(Exception):
    pass


def log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc):%H:%M:%S} {msg}", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count(con, table: str) -> int:
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def words(s: str) -> int:
    return len(s.split())


# ----------------------------------------------------------------------------
# Stages: each takes (con, data_root) and returns (rows_in, rows_out)
# ----------------------------------------------------------------------------


def ingest(con, root: Path) -> tuple[int, int]:
    full_path = root / "mast" / "hf" / FULL_NAME
    pins = json.loads((root / "mast" / "EDA_SUMMARY.json").read_text())["input_sha256"]
    manifest = json.loads((root / "splits" / "m1_v1" / "MANIFEST.json").read_text())

    # 1. verify sources against pinned checksums BEFORE loading anything
    mast_sha = sha256(full_path)
    if mast_sha != pins[FULL_NAME]:
        raise PipelineError(f"{FULL_NAME} sha256 {mast_sha[:12]} != pinned {pins[FULL_NAME][:12]}")
    log(f"  sha256 ok: {FULL_NAME} {mast_sha[:12]}")
    split_sha = {}
    for s in SPLITS:
        split_sha[s] = sha256(root / "splits" / "m1_v1" / f"{s}.jsonl")
        if split_sha[s] != manifest["splits"][s]["sha256"]:
            raise PipelineError(f"{s}.jsonl sha256 does not match MANIFEST.json")
        log(f"  sha256 ok: {s}.jsonl {split_sha[s][:12]}")

    con.execute("DROP SCHEMA IF EXISTS raw CASCADE; CREATE SCHEMA raw")
    con.execute("""CREATE TABLE raw.mast_traces (
        trace_key VARCHAR, trace_id INTEGER, mas_name VARCHAR, llm_name VARCHAR,
        benchmark_name VARCHAR, trajectory_chars INTEGER, trajectory_preview VARCHAR,
        labels_json VARCHAR, source_sha256 VARCHAR, loaded_at TIMESTAMP)""")
    con.execute("""CREATE TABLE raw.qmsum_examples (
        id VARCHAR, split VARCHAR, query VARCHAR, reference_summary VARCHAR,
        n_spans INTEGER, context_chars INTEGER, context_words INTEGER,
        context_fingerprint VARCHAR, source_sha256 VARCHAR, loaded_at TIMESTAMP)""")

    # 2. land MAST (full trajectory text is NOT stored: length + 500-char preview only)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    records = json.loads(full_path.read_text(encoding="utf-8"))
    rows = []
    for r in records:
        trace = r.get("trace") or {}
        traj = str(trace.get("trajectory") or "")
        ann = r.get("mast_annotation") or {}
        rows.append((
            trace.get("key"), r.get("trace_id"), r.get("mas_name"), r.get("llm_name"),
            r.get("benchmark_name"), len(traj), traj[:PREVIEW],
            json.dumps({c: ann.get(c) for c in EXPECTED_CODES}), mast_sha, now,
        ))  # fmt: skip
    del records
    con.executemany("INSERT INTO raw.mast_traces VALUES (?,?,?,?,?,?,?,?,?,?)", rows)

    # 3. land QMSum splits
    qrows = []
    for s in SPLITS:
        for line in (root / "splits" / "m1_v1" / f"{s}.jsonl").read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            spans = e.get("context_spans") or []
            fp = hashlib.md5(max(spans, key=len).encode()).hexdigest() if spans else None
            qrows.append((
                e["id"], s, e.get("query"), e.get("reference_summary"), len(spans),
                sum(len(x) for x in spans), sum(words(x) for x in spans), fp,
                split_sha[s], now,
            ))  # fmt: skip
    con.executemany("INSERT INTO raw.qmsum_examples VALUES (?,?,?,?,?,?,?,?,?,?)", qrows)
    return len(rows) + len(qrows), len(rows) + len(qrows)


def clean(con, root: Path) -> tuple[int, int]:
    raw_n = count(con, "raw.mast_traces")
    raw_q = count(con, "raw.qmsum_examples")
    con.execute("DROP SCHEMA IF EXISTS staging CASCADE; CREATE SCHEMA staging")

    # MAST: same rules as data/scripts/eda_mast.py (labels 0/1/null, unique key,
    # null never becomes 0, drop records whose 14 codes are all null).
    recs = con.execute(
        "SELECT trace_key, trace_id, mas_name, llm_name, benchmark_name, trajectory_chars,"
        " labels_json FROM raw.mast_traces ORDER BY trace_key, trace_id"
    ).fetchall()
    try:
        check_key_uniqueness([(r[0], r[1]) for r in recs])
        keep, long_rows = [], []
        for tk, tid, mas, llm, bench, chars, lj in recs:
            labels = normalize_labels(json.loads(lj), (tk, tid))
            if all(v is None for v in labels.values()):
                continue
            keep.append((tk, tid, (mas or "unknown").strip(), (llm or "unknown").strip(),
                         (bench or "unknown").strip(), chars,
                         sum(v is None for v in labels.values())))  # fmt: skip
            long_rows += [(tk, tid, c, v) for c, v in labels.items()]
    except EdaError as e:
        raise PipelineError(f"MAST validation failed: {e}") from e
    con.execute("""CREATE TABLE staging.mast_traces_clean (trace_key VARCHAR, trace_id INTEGER,
        mas_name VARCHAR, llm_name VARCHAR, benchmark_name VARCHAR, trajectory_chars INTEGER,
        n_null_labels INTEGER)""")
    con.executemany("INSERT INTO staging.mast_traces_clean VALUES (?,?,?,?,?,?,?)", keep)
    con.execute("""CREATE TABLE staging.mast_labels_long (trace_key VARCHAR, trace_id INTEGER,
        code VARCHAR, value TINYINT)""")  # value NULL = null label, never 0
    con.executemany("INSERT INTO staging.mast_labels_long VALUES (?,?,?,?)", long_rows)

    # QMSum: trim text, word counts, non-empty checks; meeting id derived from example id
    # (qmsum_<split>_<meeting_idx>_<s|g><n>).
    bad = con.execute(
        "SELECT count(*) FROM raw.qmsum_examples WHERE trim(coalesce(query,'')) = ''"
        " OR trim(coalesce(reference_summary,'')) = '' OR n_spans < 0"
    ).fetchone()[0]
    if bad:
        raise PipelineError(f"QMSum validation failed: {bad} examples with empty query/summary")
    bad_ids = con.execute(
        "SELECT count(*) FROM raw.qmsum_examples WHERE NOT regexp_matches(id, '^qmsum_[a-z]+_[0-9]+_[sg][0-9]+$')"
    ).fetchone()[0]
    if bad_ids:
        raise PipelineError(f"QMSum validation failed: {bad_ids} ids do not match the expected pattern")
    con.execute("""CREATE TABLE staging.qmsum_examples_clean AS
        SELECT id, split,
               split || '_' || regexp_extract(id, '^qmsum_[a-z]+_([0-9]+)_', 1) AS meeting_id,
               trim(query) AS query, trim(reference_summary) AS reference_summary,
               n_spans, context_chars, context_words, context_fingerprint
        FROM raw.qmsum_examples""")
    return raw_n + raw_q, count(con, "staging.mast_traces_clean") + count(
        con, "staging.qmsum_examples_clean"
    )


def transform(con, root: Path) -> tuple[int, int]:
    con.execute("DROP SCHEMA IF EXISTS marts CASCADE; CREATE SCHEMA marts")
    con.execute("CREATE TABLE marts.dim_failure_mode (code VARCHAR, name VARCHAR, category VARCHAR)")
    con.executemany(
        "INSERT INTO marts.dim_failure_mode VALUES (?,?,?)",
        [(c, MODE_NAMES[c], CATEGORY[c[0]]) for c in EXPECTED_CODES],
    )
    for dim, col, key in (("framework", "mas_name", "framework_key"),
                          ("llm", "llm_name", "llm_key"),
                          ("benchmark", "benchmark_name", "benchmark_key")):  # fmt: skip
        con.execute(f"""CREATE TABLE marts.dim_{dim} AS
            SELECT row_number() OVER (ORDER BY {col}) AS {key}, {col}
            FROM (SELECT DISTINCT {col} FROM staging.mast_traces_clean)""")
    con.execute("""CREATE TABLE marts.fact_trace AS
        WITH pos AS (
            SELECT l.trace_key, l.trace_id, count(*) AS n_failures,
                   count(*) FILTER (WHERE d.category = 'Specification issues') AS n_specification,
                   count(*) FILTER (WHERE d.category = 'Inter-agent misalignment') AS n_misalignment,
                   count(*) FILTER (WHERE d.category = 'Task verification / termination') AS n_verification
            FROM staging.mast_labels_long l JOIN marts.dim_failure_mode d ON d.code = l.code
            WHERE l.value = 1 GROUP BY 1, 2)
        SELECT row_number() OVER (ORDER BY t.trace_key, t.trace_id) AS trace_sk,
               t.trace_key, t.trace_id, f.framework_key, m.llm_key, b.benchmark_key,
               coalesce(p.n_failures, 0) AS n_failures,
               coalesce(p.n_specification, 0) AS n_specification,
               coalesce(p.n_misalignment, 0) AS n_misalignment,
               coalesce(p.n_verification, 0) AS n_verification,
               t.trajectory_chars
        FROM staging.mast_traces_clean t
        JOIN marts.dim_framework f ON f.mas_name = t.mas_name
        JOIN marts.dim_llm m ON m.llm_name = t.llm_name
        JOIN marts.dim_benchmark b ON b.benchmark_name = t.benchmark_name
        LEFT JOIN pos p ON p.trace_key = t.trace_key AND p.trace_id = t.trace_id""")
    con.execute("""CREATE TABLE marts.fact_trace_failure AS
        SELECT f.trace_sk, l.code AS failure_code
        FROM staging.mast_labels_long l
        JOIN marts.fact_trace f ON f.trace_key = l.trace_key AND f.trace_id = l.trace_id
        WHERE l.value = 1""")
    con.execute("""CREATE TABLE marts.fact_m1_example AS
        SELECT split, id AS example_id, meeting_id, n_spans,
               len(string_split(query, ' ')) AS query_words,
               len(string_split(reference_summary, ' ')) AS reference_words,
               context_words
        FROM staging.qmsum_examples_clean""")
    n_in = count(con, "staging.mast_traces_clean") + count(con, "staging.qmsum_examples_clean")
    n_out = count(con, "marts.fact_trace") + count(con, "marts.fact_m1_example")
    return n_in, n_out


def quality(con, root: Path) -> tuple[int, int]:
    pins = json.loads((root / "mast" / "EDA_SUMMARY.json").read_text())
    manifest = json.loads((root / "splits" / "m1_v1" / "MANIFEST.json").read_text())
    q = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    checks: list[tuple[str, object, object]] = []  # name, expected, actual
    raw_n, ok_n = q("SELECT count(*) FROM raw.mast_traces"), q("SELECT count(*) FROM staging.mast_traces_clean")
    checks += [
        ("mast raw records", pins["raw_record_count"], raw_n),
        ("mast scorable records", pins["scorable_record_count"], ok_n),
        ("mast excluded records (all-null)", pins["excluded_record_count"], raw_n - ok_n),
        ("mast key (trace_key, trace_id) duplicates", 0,
         q("SELECT count(*) - count(DISTINCT (trace_key, trace_id)) FROM raw.mast_traces")),
        ("mast label values outside {0,1,NULL}", 0,
         q("SELECT count(*) FROM staging.mast_labels_long WHERE value NOT IN (0,1)")),
        ("mast null labels converted to 0 (null cells raw vs staging)",
         q("SELECT sum(n_null_labels) FROM staging.mast_traces_clean"),
         q("SELECT count(*) FROM staging.mast_labels_long WHERE value IS NULL")),
    ]  # fmt: skip
    for s in SPLITS:
        checks.append((f"qmsum split {s} examples", manifest["splits"][s]["count"],
                       q(f"SELECT count(*) FROM marts.fact_m1_example WHERE split = '{s}'")))  # fmt: skip
    checks += [
        ("qmsum example ids in >1 split", 0,
         q("SELECT count(*) FROM (SELECT example_id FROM marts.fact_m1_example"
           " GROUP BY 1 HAVING count(DISTINCT split) > 1)")),
        # meeting_id = split + meeting index parsed from the example id (qmsum_<split>_<idx>_...)
        ("qmsum meetings in >1 split (by id-derived meeting)", 0,
         q("SELECT count(*) FROM (SELECT meeting_id FROM marts.fact_m1_example"
           " GROUP BY 1 HAVING count(DISTINCT split) > 1)")),
        # content check: md5 of each example's longest context span; a shared span means shared meeting text
        ("qmsum longest-context-span hashes shared across splits", 0,
         q("SELECT count(*) FROM (SELECT context_fingerprint FROM staging.qmsum_examples_clean"
           " WHERE context_fingerprint IS NOT NULL GROUP BY 1 HAVING count(DISTINCT split) > 1)")),
        ("reconcile: raw qmsum = staging qmsum", q("SELECT count(*) FROM raw.qmsum_examples"),
         q("SELECT count(*) FROM staging.qmsum_examples_clean")),
        ("reconcile: staging qmsum = fact_m1_example", q("SELECT count(*) FROM staging.qmsum_examples_clean"),
         q("SELECT count(*) FROM marts.fact_m1_example")),
        ("reconcile: staging traces = fact_trace", ok_n, q("SELECT count(*) FROM marts.fact_trace")),
        ("reconcile: positive labels = fact_trace_failure rows",
         q("SELECT count(*) FROM staging.mast_labels_long WHERE value = 1"),
         q("SELECT count(*) FROM marts.fact_trace_failure")),
        ("reconcile: sum(n_failures) = fact_trace_failure rows",
         q("SELECT count(*) FROM marts.fact_trace_failure"),
         q("SELECT sum(n_failures) FROM marts.fact_trace")),
        ("reconcile: category counts sum to n_failures", 0,
         q("SELECT count(*) FROM marts.fact_trace WHERE n_specification + n_misalignment"
           " + n_verification <> n_failures")),
        ("fact_trace rows with unmatched dimension key", 0,
         q("SELECT count(*) FROM marts.fact_trace WHERE framework_key IS NULL OR llm_key IS NULL"
           " OR benchmark_key IS NULL")),
    ]  # fmt: skip
    run_id = RUN["id"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    con.executemany(
        "INSERT INTO meta.quality_checks VALUES (?,?,?,?,?,?)",
        [(run_id, n, str(e), str(a), str(e) == str(a), now) for n, e, a in checks],
    )
    failed = [n for n, e, a in checks if str(e) != str(a)]
    for n, e, a in checks:
        log(f"  [{'PASS' if str(e) == str(a) else 'FAIL'}] {n}: expected {e}, actual {a}")
    if failed:
        raise PipelineError(f"{len(failed)} quality check(s) failed: {failed}")
    return len(checks), len(checks)


STAGES = {"ingest": ingest, "clean": clean, "transform": transform, "quality": quality}


# ----------------------------------------------------------------------------
# Orchestration + monitoring
# ----------------------------------------------------------------------------


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], text=True,
            stderr=subprocess.DEVNULL).strip()  # fmt: skip
    except Exception:
        return "unknown"


def connect(db: str):
    if db != ":memory:":
        Path(db).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(db)
    con.execute("CREATE SCHEMA IF NOT EXISTS meta")
    con.execute("""CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
        run_id VARCHAR, stage VARCHAR, started_at TIMESTAMP, finished_at TIMESTAMP,
        duration_s DOUBLE, rows_in BIGINT, rows_out BIGINT, status VARCHAR,
        git_sha VARCHAR, error VARCHAR)""")
    con.execute("""CREATE TABLE IF NOT EXISTS meta.quality_checks (
        run_id VARCHAR, check_name VARCHAR, expected VARCHAR, actual VARCHAR,
        passed BOOLEAN, checked_at TIMESTAMP)""")
    return con


def run(db: str, data_root: Path, only: str | None = None) -> int:
    con = connect(db)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    RUN["id"] = run_id
    sha = git_sha()
    shown = Path(db).resolve().relative_to(REPO) if Path(db).resolve().is_relative_to(REPO) else db
    log(f"run {run_id} git={sha} db={shown} stages={only or 'all'}")
    t_all = time.time()
    for name, fn in STAGES.items():
        if only and name != only:
            continue
        start = datetime.now(timezone.utc).replace(tzinfo=None)
        t0 = time.time()
        log(f"stage {name}: start")
        status, err, rin, rout = "success", None, None, None
        try:
            rin, rout = fn(con, data_root)
        except Exception as e:  # fail fast: record, stop
            status, err = "failed", f"{type(e).__name__}: {e}"
        dur = time.time() - t0
        con.execute(
            "INSERT INTO meta.pipeline_runs VALUES (?,?,?,?,?,?,?,?,?,?)",
            [run_id, name, start, datetime.now(timezone.utc).replace(tzinfo=None),
             round(dur, 3), rin, rout, status, sha, err],
        )  # fmt: skip
        log(f"stage {name}: {status} in {dur:.2f}s rows_in={rin} rows_out={rout}")
        if err:
            log(f"  ERROR {err}")
            log(f"run {run_id} FAILED at stage {name} after {time.time() - t_all:.2f}s")
            return 1
    log(f"run {run_id} SUCCESS in {time.time() - t_all:.2f}s")
    return 0


REPORT_QUERIES = {
    "Failure-mode prevalence by category (scorable traces)": """
        SELECT d.category, count(DISTINCT d.code) AS modes, count(*) AS positive_labels,
               round(100.0 * count(*) / (SELECT count(*) FROM marts.fact_trace), 1) AS labels_per_100_traces
        FROM marts.fact_trace_failure f JOIN marts.dim_failure_mode d ON d.code = f.failure_code
        GROUP BY 1 ORDER BY positive_labels DESC""",
    "Failures by framework": """
        SELECT fw.mas_name AS framework, count(*) AS traces, sum(t.n_failures) AS failures,
               round(avg(t.n_failures), 2) AS avg_failures_per_trace
        FROM marts.fact_trace t JOIN marts.dim_framework fw USING (framework_key)
        GROUP BY 1 ORDER BY failures DESC""",
    "QMSum split size / length summary": """
        SELECT split, count(*) AS examples, count(DISTINCT meeting_id) AS meetings,
               round(avg(query_words), 1) AS avg_query_words,
               round(avg(reference_words), 1) AS avg_summary_words,
               round(avg(context_words), 0) AS avg_context_words
        FROM marts.fact_m1_example GROUP BY 1
        ORDER BY CASE split WHEN 'train' THEN 1 WHEN 'val' THEN 2 ELSE 3 END""",
}


def table(con, sql: str) -> None:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = [[("" if v is None else str(v)) for v in r] for r in cur.fetchall()]
    w = [max(len(c), *(len(r[i]) for r in rows)) if rows else len(c) for i, c in enumerate(cols)]
    print("  " + "  ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
    print("  " + "  ".join("-" * x for x in w))
    for r in rows:
        print("  " + "  ".join(v.ljust(w[i]) for i, v in enumerate(r)))


def report(db: str, last: int) -> int:
    con = connect(db)
    print(f"== Last {last} stage runs (meta.pipeline_runs) ==")
    table(con, f"""SELECT run_id, stage, strftime(started_at, '%H:%M:%S') AS started, duration_s,
        rows_in, rows_out, status, git_sha, coalesce(error, '') AS error
        FROM (SELECT * FROM meta.pipeline_runs ORDER BY started_at DESC LIMIT {last})
        ORDER BY started_at""")
    print("\n== Latest quality checks (meta.quality_checks) ==")
    table(con, """SELECT check_name, expected, actual, CASE WHEN passed THEN 'PASS' ELSE 'FAIL' END AS result
        FROM meta.quality_checks WHERE run_id = (SELECT max(run_id) FROM meta.quality_checks)""")
    for title, sql in REPORT_QUERIES.items():
        print(f"\n== {title} ==")
        table(con, sql)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=str(REPO / "warehouse" / "mas.duckdb"))
    p.add_argument("--data-root", default=str(REPO / "data"), type=Path)
    p.add_argument("--stage", choices=list(STAGES))
    p.add_argument("--report", action="store_true")
    p.add_argument("--last", type=int, default=12, help="runs shown by --report")
    a = p.parse_args(argv)
    if a.report:
        return report(a.db, a.last)
    return run(a.db, a.data_root, a.stage)


if __name__ == "__main__":
    sys.exit(main())
