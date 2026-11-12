# Sample run (real output)

Everything below is pasted program output from `infra/warehouse/pipeline.py` against the real MAST-Data and QMSum splits. Nothing was edited.
`<repo>/data` stands for the repo `data/` directory (the raw MAST download is gitignored).

## Run 1

```
$ python infra/warehouse/pipeline.py --data-root <repo>/data
02:15:09 run 20261112T021509286923 git=70e378f db=warehouse/mas.duckdb stages=all
02:15:09 stage ingest: start
02:15:09   sha256 ok: MAD_full_dataset.json d636ac63dfc1
02:15:09   sha256 ok: train.jsonl bc44fd4bfd13
02:15:09   sha256 ok: val.jsonl 4b622ee535da
02:15:09   sha256 ok: test.jsonl 64d89302edbc
02:15:10 stage ingest: success in 1.21s rows_in=3452 rows_out=3452
02:15:10 stage clean: start
02:15:15 stage clean: success in 4.80s rows_in=3452 rows_out=3448
02:15:15 stage transform: start
02:15:15 stage transform: success in 0.02s rows_in=3448 rows_out=3448
02:15:15 stage quality: start
02:15:15   [PASS] mast raw records: expected 1642, actual 1642
02:15:15   [PASS] mast scorable records: expected 1638, actual 1638
02:15:15   [PASS] mast excluded records (all-null): expected 4, actual 4
02:15:15   [PASS] mast key (trace_key, trace_id) duplicates: expected 0, actual 0
02:15:15   [PASS] mast label values outside {0,1,NULL}: expected 0, actual 0
02:15:15   [PASS] mast null labels converted to 0 (null cells raw vs staging): expected 0, actual 0
02:15:15   [PASS] qmsum split train examples: expected 1257, actual 1257
02:15:15   [PASS] qmsum split val examples: expected 272, actual 272
02:15:15   [PASS] qmsum split test examples: expected 281, actual 281
02:15:15   [PASS] qmsum example ids in >1 split: expected 0, actual 0
02:15:15   [PASS] qmsum meetings in >1 split (by id-derived meeting): expected 0, actual 0
02:15:15   [PASS] qmsum longest-context-span hashes shared across splits: expected 0, actual 0
02:15:15   [PASS] reconcile: raw qmsum = staging qmsum: expected 1810, actual 1810
02:15:15   [PASS] reconcile: staging qmsum = fact_m1_example: expected 1810, actual 1810
02:15:15   [PASS] reconcile: staging traces = fact_trace: expected 1638, actual 1638
02:15:15   [PASS] reconcile: positive labels = fact_trace_failure rows: expected 5141, actual 5141
02:15:15   [PASS] reconcile: sum(n_failures) = fact_trace_failure rows: expected 5141, actual 5141
02:15:15   [PASS] reconcile: category counts sum to n_failures: expected 0, actual 0
02:15:15   [PASS] fact_trace rows with unmatched dimension key: expected 0, actual 0
02:15:15 stage quality: success in 0.01s rows_in=19 rows_out=19
02:15:15 run 20261112T021509286923 SUCCESS in 6.05s
```

## Run 2 (same command; layers replaced, run history appended)

```
$ python infra/warehouse/pipeline.py --data-root <repo>/data
02:15:16 run 20261112T021516470199 git=70e378f db=warehouse/mas.duckdb stages=all
02:15:16 stage ingest: start
02:15:16   sha256 ok: MAD_full_dataset.json d636ac63dfc1
02:15:16   sha256 ok: train.jsonl bc44fd4bfd13
02:15:16   sha256 ok: val.jsonl 4b622ee535da
02:15:16   sha256 ok: test.jsonl 64d89302edbc
02:15:17 stage ingest: success in 1.11s rows_in=3452 rows_out=3452
02:15:17 stage clean: start
02:15:22 stage clean: success in 4.94s rows_in=3452 rows_out=3448
02:15:22 stage transform: start
02:15:22 stage transform: success in 0.01s rows_in=3448 rows_out=3448
02:15:22 stage quality: start
02:15:22   [PASS] mast raw records: expected 1642, actual 1642
02:15:22   [PASS] mast scorable records: expected 1638, actual 1638
02:15:22   [PASS] mast excluded records (all-null): expected 4, actual 4
02:15:22   [PASS] mast key (trace_key, trace_id) duplicates: expected 0, actual 0
02:15:22   [PASS] mast label values outside {0,1,NULL}: expected 0, actual 0
02:15:22   [PASS] mast null labels converted to 0 (null cells raw vs staging): expected 0, actual 0
02:15:22   [PASS] qmsum split train examples: expected 1257, actual 1257
02:15:22   [PASS] qmsum split val examples: expected 272, actual 272
02:15:22   [PASS] qmsum split test examples: expected 281, actual 281
02:15:22   [PASS] qmsum example ids in >1 split: expected 0, actual 0
02:15:22   [PASS] qmsum meetings in >1 split (by id-derived meeting): expected 0, actual 0
02:15:22   [PASS] qmsum longest-context-span hashes shared across splits: expected 0, actual 0
02:15:22   [PASS] reconcile: raw qmsum = staging qmsum: expected 1810, actual 1810
02:15:22   [PASS] reconcile: staging qmsum = fact_m1_example: expected 1810, actual 1810
02:15:22   [PASS] reconcile: staging traces = fact_trace: expected 1638, actual 1638
02:15:22   [PASS] reconcile: positive labels = fact_trace_failure rows: expected 5141, actual 5141
02:15:22   [PASS] reconcile: sum(n_failures) = fact_trace_failure rows: expected 5141, actual 5141
02:15:22   [PASS] reconcile: category counts sum to n_failures: expected 0, actual 0
02:15:22   [PASS] fact_trace rows with unmatched dimension key: expected 0, actual 0
02:15:22 stage quality: success in 0.01s rows_in=19 rows_out=19
02:15:22 run 20261112T021516470199 SUCCESS in 6.08s
```

## Report

```
$ python infra/warehouse/pipeline.py --report
== Last 12 stage runs (meta.pipeline_runs) ==
  run_id                 stage      started   duration_s  rows_in  rows_out  status   git_sha  error
  ---------------------  ---------  --------  ----------  -------  --------  -------  -------  -----
  20261112T021509286923  ingest     02:15:09  1.215       3452     3452      success  70e378f       
  20261112T021509286923  clean      02:15:10  4.804       3452     3448      success  70e378f       
  20261112T021509286923  transform  02:15:15  0.016       3448     3448      success  70e378f       
  20261112T021509286923  quality    02:15:15  0.012       19       19        success  70e378f       
  20261112T021516470199  ingest     02:15:16  1.108       3452     3452      success  70e378f       
  20261112T021516470199  clean      02:15:17  4.941       3452     3448      success  70e378f       
  20261112T021516470199  transform  02:15:22  0.014       3448     3448      success  70e378f       
  20261112T021516470199  quality    02:15:22  0.012       19       19        success  70e378f       

== Latest quality checks (meta.quality_checks) ==
  check_name                                                   expected  actual  result
  -----------------------------------------------------------  --------  ------  ------
  mast raw records                                             1642      1642    PASS  
  mast scorable records                                        1638      1638    PASS  
  mast excluded records (all-null)                             4         4       PASS  
  mast key (trace_key, trace_id) duplicates                    0         0       PASS  
  mast label values outside {0,1,NULL}                         0         0       PASS  
  mast null labels converted to 0 (null cells raw vs staging)  0         0       PASS  
  qmsum split train examples                                   1257      1257    PASS  
  qmsum split val examples                                     272       272     PASS  
  qmsum split test examples                                    281       281     PASS  
  qmsum example ids in >1 split                                0         0       PASS  
  qmsum meetings in >1 split (by id-derived meeting)           0         0       PASS  
  qmsum longest-context-span hashes shared across splits       0         0       PASS  
  reconcile: raw qmsum = staging qmsum                         1810      1810    PASS  
  reconcile: staging qmsum = fact_m1_example                   1810      1810    PASS  
  reconcile: staging traces = fact_trace                       1638      1638    PASS  
  reconcile: positive labels = fact_trace_failure rows         5141      5141    PASS  
  reconcile: sum(n_failures) = fact_trace_failure rows         5141      5141    PASS  
  reconcile: category counts sum to n_failures                 0         0       PASS  
  fact_trace rows with unmatched dimension key                 0         0       PASS  

== Failure-mode prevalence by category (scorable traces) ==
  category                         modes  positive_labels  labels_per_100_traces
  -------------------------------  -----  ---------------  ---------------------
  Specification issues             5      1899             115.9                
  Inter-agent misalignment         6      1702             103.9                
  Task verification / termination  3      1540             94.0                 

== Failures by framework ==
  framework   traces  failures  avg_failures_per_trace
  ----------  ------  --------  ----------------------
  ChatDev     326     1520      4.66                  
  MetaGPT     430     1472      3.42                  
  AG2         597     928       1.55                  
  Magentic    195     796       4.08                  
  HyperAgent  30      185       6.17                  
  OpenManus   30      130       4.33                  
  AppWorld    30      110       3.67                  

== QMSum split size / length summary ==
  split  examples  meetings  avg_query_words  avg_summary_words  avg_context_words
  -----  --------  --------  ---------------  -----------------  -----------------
  train  1257      162       11.7             70.6               2122.0           
  val    272       35        11.4             70.6               2174.0           
  test   281       35        11.5             64.7               2227.0
```

## Table inventory (every table, every layer; queried from the DuckDB file after run 2)

| Layer | Table | Rows | Columns |
|---|---|---:|---:|
| raw | mast_traces | 1642 | 10 |
| raw | qmsum_examples | 1810 | 10 |
| staging | mast_labels_long | 22932 | 4 |
| staging | mast_traces_clean | 1638 | 7 |
| staging | qmsum_examples_clean | 1810 | 9 |
| marts | dim_benchmark | 8 | 2 |
| marts | dim_failure_mode | 14 | 3 |
| marts | dim_framework | 7 | 2 |
| marts | dim_llm | 5 | 2 |
| marts | fact_m1_example | 1810 | 7 |
| marts | fact_trace | 1638 | 11 |
| marts | fact_trace_failure | 5141 | 2 |
| meta | pipeline_runs | 8 | 10 |
| meta | quality_checks | 38 | 6 |
