# Why the data pipeline does not use AWS or Airflow (yet)

DATA 298A, Team 4. Prepared for Team Meeting 2, 12 November 2026. The same argument is in Workbook 2, section 4.2, Table 39.

## Short answer

We evaluated both against what the pipeline has to do today and declined both for 298A. The pipeline ingests two static, pinned public datasets (about 220 MB) through four stages in a straight line and finishes in about 6 seconds on a laptop. Nothing is scheduled, nothing is too large for one machine, and training runs on the university GPU at $0. A scheduler would be idle and a cloud account would make the pipeline impossible to verify without our credentials.

What we built instead covers the same four things the rubric asks for:

| Rubric item | What we have | Where |
|---|---|---|
| Ingestion | Pinned downloads, SHA-256 and record-count verification, landed in a `raw` schema with source digest and load time | `data/scripts/download_mast.py`, `download_qmsum.py`, `infra/warehouse/pipeline.py` |
| Transformation | Validation and cleaning into `staging`, then a star schema in `marts` | `infra/warehouse/pipeline.py` |
| Data warehouse | DuckDB: 4 dimensions, 3 fact tables, 14 tables in all | `warehouse/mas.duckdb` (rebuilt by one command) |
| Monitoring and management | 19 quality gates in `meta.quality_checks`; per-stage run history (start, duration, rows in and out, status, git commit) in `meta.pipeline_runs`; fail-fast; idempotent reruns; tests in CI | `pipeline.py --report`, `.github/workflows/ci.yml` |

## The decision, question by question

| Question | Our workload | Decision |
|---|---|---|
| Is anything scheduled? | No. Both datasets are pinned to a commit and never change. No daily run, no backfill, no late data. | A scheduler would have nothing to schedule. The trigger is a code change, which GitHub Actions handles. |
| Is the graph complex? | Four stages, linear, no branching or fan-out. | An ordered list with fail-fast expresses it fully. Each stage is a plain function, so wrapping it in an Airflow task later is mechanical. |
| Is the data too big for one machine? | About 220 MB raw; marts are a few thousand rows. | DuckDB runs the whole pipeline in about 6 s. A cloud warehouse adds cost and credentials, not capability. |
| Do we need cloud compute? | One 16 GB GPU, provided by the university lab at $0. Baseline is API inference. | No cloud GPU (already decided in Workbook 1, section 2.3). |
| Reproducibility? | Clone, two commands, no account. | Local-first is the more reproducible option for a graded project. |
| Lightweight alternatives? | Local Airflow still needs a metadata DB, scheduler and web server to run four functions on unchanging data. | First step up will be a scheduled GitHub Actions job; Airflow only if the graph grows branches or backfills. |

## When we would adopt them

1. **Recurring ingestion.** When product sessions are recorded more often than weekly, the nightly export from the PostgreSQL event log to the warehouse becomes a real schedule with a freshness requirement. First a scheduled CI job, then Airflow if dependencies grow.
2. **First participant outside the team.** The 298B controlled study needs the platform reachable beyond the team. That is when the cloud deployment (FR-8) lands, with managed PostgreSQL.
3. **Checkpoints.** The shared checkpoint utility accepts `s3://` URIs (PR #32, merged), so adapter checkpoints can move to S3 without touching a trainer.

Mapping if we migrate: raw files to S3, stage functions to Airflow tasks, DuckDB schemas to Redshift or Athena, `meta.pipeline_runs` to Airflow's run history.

## Likely follow-up questions

**What happens if a stage fails halfway?** The run stops at that stage, the failure is written to `meta.pipeline_runs` with the error, and the exit code is non-zero. Layer tables are replaced on each run, so rerunning after a fix gives the same warehouse as a clean run. We do not have automatic retries; with local static files there is no transient failure to retry.

**Who is alerted?** The pipeline tests run on every pull request, so a broken stage or gate is a red check and an email to the author. Between changes the monitoring is passive. That is acceptable only because the data does not change between changes, and it stops being acceptable under trigger 1.

**Is a metadata table really monitoring?** It is run logging plus data-quality assertions: the same information Airflow's UI shows (task state, duration, history) plus row counts in and out, in a form we can query with SQL. It has no dashboard and no paging. We say so in the workbook.

**How is the warehouse governed once real sessions arrive?** Today it is a rebuildable local file with public data, so there is nothing to protect or back up: the pinned sources are the backup. Pseudonymised session data changes that, and access control, backup and retention are part of the 298B deployment work.

**Does the product's own data flow into the warehouse?** Not yet. No session has been recorded, so the event-log export is the one ingestion path that does not exist. It is listed in the Workbook 2 carry-forward table.
