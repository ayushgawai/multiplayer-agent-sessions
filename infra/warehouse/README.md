# Source-to-warehouse pipeline demo (DuckDB)

One script, `pipeline.py`, takes two real datasets (MAST-Data failure traces, QMSum M1 splits) from source files to a small star-schema warehouse, with quality gates and run history. Stdlib + DuckDB only. Real output: [SAMPLE_RUN.md](SAMPLE_RUN.md).

## Layers

```
 SOURCES                      WAREHOUSE  (warehouse/mas.duckdb, gitignored)
 data/mast/hf/MAD_full_dataset.json (1,642 traces, sha256-pinned)
 data/splits/m1_v1/{train,val,test}.jsonl (1,810 examples, sha256-pinned)
        |  1 ingest  : verify sha256, land as-is (trajectory text -> length + 500-char preview)
        v
   raw.mast_traces  raw.qmsum_examples
        |  2 clean   : labels 0/1/null only, unique key, drop 4 all-null, trim text, non-empty
        v
   staging.mast_traces_clean  staging.mast_labels_long  staging.qmsum_examples_clean
        |  3 transform: star schema
        v
   marts.dim_failure_mode / dim_framework / dim_llm / dim_benchmark
   marts.fact_trace  fact_trace_failure  fact_m1_example
        |  4 quality : 19 gates -> meta.quality_checks (any FAIL stops the run, exit 1)
   meta.pipeline_runs (one row per stage per run; history accumulates)
```

## Demo (about 5 minutes)

Setup once: `pip install -r requirements.txt`. The raw MAST file is gitignored; run `python data/scripts/download_mast.py` first, or pass `--data-root <dir-with-mast/ and splits/>`.

```bash
python infra/warehouse/pipeline.py          # 1. full run, ~6 s: prints per-stage timing, rows in/out, 19 PASS/FAIL gates
python infra/warehouse/pipeline.py          # 2. again: idempotent, layers replaced, run history appended
python infra/warehouse/pipeline.py --report # 3. monitoring: last runs, latest checks, 3 analytic queries
python infra/warehouse/pipeline.py --stage quality   # 4. re-run one stage on the existing warehouse
pytest -q infra/warehouse                   # 5. tests on synthetic fixtures, incl. bad label => run fails
```

Talking points: ingest refuses a file whose SHA-256 differs from the pinned value; null labels are never turned into 0; a failed stage is recorded in `meta.pipeline_runs` with its error and later stages do not run.
Flags: `--db` (default `warehouse/mas.duckdb`), `--data-root` (default `data/`), `--stage ingest|clean|transform|quality`, `--report`, `--last N`.

Split-leakage check: QMSum ids look like `qmsum_<split>_<meeting_idx>_<s|g><n>`, so the meeting is derived from the id (split + meeting index), and we also hash each example's longest context span and require no hash in more than one split.

## SQL to try in the `duckdb` CLI

```bash
duckdb warehouse/mas.duckdb
```

```sql
-- top failure modes
SELECT d.code, d.name, d.category, count(*) AS traces
FROM marts.fact_trace_failure f JOIN marts.dim_failure_mode d ON d.code = f.failure_code
GROUP BY ALL ORDER BY traces DESC LIMIT 5;

-- failures per LLM x framework
SELECT fw.mas_name, l.llm_name, count(*) AS traces, round(avg(n_failures), 2) AS avg_failures
FROM marts.fact_trace t JOIN marts.dim_framework fw USING (framework_key) JOIN marts.dim_llm l USING (llm_key)
GROUP BY ALL ORDER BY avg_failures DESC;

-- lineage: raw -> staging row counts (4 all-null records excluded)
SELECT (SELECT count(*) FROM raw.mast_traces) AS raw, (SELECT count(*) FROM staging.mast_traces_clean) AS staged;

-- monitoring
SELECT run_id, stage, duration_s, rows_in, rows_out, status FROM meta.pipeline_runs ORDER BY started_at DESC LIMIT 8;
SELECT * FROM meta.quality_checks WHERE NOT passed;
```
