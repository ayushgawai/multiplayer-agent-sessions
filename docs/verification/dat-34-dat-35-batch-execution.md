# Verification: resumable MAST batch execution and run provenance

Linear: [DAT-34](https://linear.app/data-298a-team-4/issue/DAT-34) (MAST 10) and
[DAT-35](https://linear.app/data-298a-team-4/issue/DAT-35) (MAST 11).
Owner: Shriram Dundigalla. Reviewer: Ayush.

This is the completion evidence both issues ask for: a sample batch, logs
showing an interrupted run resumed, a completed run manifest, and one
prediction record carrying every required provenance field.

## What was run

The real judge adapter is MAST 02 ([DAT-26](https://linear.app/data-298a-team-4/issue/DAT-26)),
which is still open, so these runs use `StubJudge`: a deterministic stand-in
that derives its reply from a digest of the prompt and makes no network call.
Determinism is what makes the comparison below meaningful, because an
interrupted-then-resumed run and a single clean run must produce byte-identical
output. Swapping in the real adapter changes the judge, not the execution,
resume, or provenance logic that these issues cover.

The dataset is a synthetic stand-in with the same shape as
`MAD_full_dataset.json`: 30,000 records across two `trace.key` source runs that
deliberately reuse the same `trace_id` range, with one record excluded by the
evaluation manifest, giving 29,999 scorable records. The real file is not
committed and the reproduction scale is 1,638 records, so a larger synthetic
set was used to make the kill land reliably mid-run.

## 1. A run is interrupted by a hard kill

```
$ python -m models.baseline_mast.run_batch --result-dir run1 --run-id demo-run-001 --stub-judge
[1]    75736 killed
$ wc -l run1/predictions.jsonl
    6623
$ ls run1/
predictions.jsonl
```

6,623 of 29,999 predictions survived `SIGKILL`. No `run_manifest.json` exists,
which is correct: the run never reached the end, so it must not look complete.

`SIGKILL` rather than `SIGINT` is deliberate. A non-interactive shell sets
background jobs to ignore `SIGINT`, and a hard kill is also the closer analogue
of the wiped lab machine in our risk register.

## 2. The kill left a partial line

```
$ tail -c 55 run1/predictions.jsonl   # partial line from the kill
"run_id": "demo-run-001", "trace_id": "AG2_GSM_Plus_Cla
```

## 3. The run resumes into the same result directory

```
$ python -m models.baseline_mast.run_batch --result-dir run1 --run-id demo-run-002-resume --stub-judge
sealed a partial final line in predictions.jsonl
{
  "run_id": "demo-run-002-resume",
  "attempted": 23376,
  "succeeded": 23376,
  "failed": 0,
  "skipped": 6623,
  "parse_status_counts": {
    "ok": 23376
  },
  "prompt_tokens": 0,
  "completion_tokens": 0,
  "started_at": "2026-10-06T04:28:03Z",
  "ended_at": "2026-10-06T04:28:09Z"
}

$ ls run1/
predictions.jsonl
run_manifest.json
```

6,623 skipped plus 23,376 attempted is 29,999. Nothing was judged twice.

## 4. The resumed result equals one uninterrupted run

```
interrupted+resumed vs one clean run
  unique trace_ids   resumed=29999  clean=29999
  duplicate records  0
  unparsable fragments skipped  1
  id sets identical             True
  parsed labels identical       True
  raw responses identical       True
  run manifest missing fields   none
```

## Two defects this run found

**A resumed append could silently lose one record.** When the kill left the
final line without its newline, the next append landed on the same line and
glued two records into one unparsable string. The resumed directory held 29,998
records where the clean run held 29,999, and nothing reported an error. The
runner now seals a partial final line before appending, so the fragment stays
on its own line and is discarded by the reader. Covered by
`test_resume_after_a_partial_line_loses_no_record` and
`test_seal_partial_line_only_acts_when_needed`. The test that should have
caught this asserted only on the summary counts, not on the file, and has been
tightened.

**Dirty file paths in the run manifest lost their first character.** The git
helper stripped its whole output, which removes the leading status column of
the first `git status --porcelain` line, so
`models/baseline_mast/run_batch.py` was recorded as
`odels/baseline_mast/run_batch.py`. Parsing is now a separate pure function
covered by `test_status_paths_keep_their_first_character`.

## Record key

`trace_id` on a prediction is the composite `<trace.key>::<trace_id>`. The
dataset's own `trace_id` is not unique, only 206 distinct values across 1,642
records, and the pair (`trace.key`, `trace_id`) is the unique key per the
[DAT-29](https://linear.app/data-298a-team-4/issue/DAT-29) data dictionary.
`trace_key` and `trace_index` carry the two parts separately. The evidence run
includes two source runs sharing a `trace_id` range specifically to exercise
this, and `test_trace_id_is_unique_across_runs_that_share_a_trace_index` pins
it.

## Reference source is recorded on every prediction

Each record carries `reference_source`. The
[DAT-30](https://linear.app/data-298a-team-4/issue/DAT-30) manifest warns that
`mast_annotation` in `MAD_full_dataset.json` was produced by the original LLM
judge rather than by human annotators, and that agreement against it must not
be presented as reproducing the paper's human evaluation. Recording the source
on the record makes that distinction impossible to lose downstream.

## Secrets

`model_settings` passes through a redactor before reaching the manifest. Key
names such as `api_key` and `authorization` are dropped, as are values matching
known credential formats, while `max_tokens` and the token counts survive
because they are provenance we need. Covered by
`test_no_secret_values_reach_the_manifest` and
`test_token_count_settings_are_not_mistaken_for_credentials`.

## Reproducing this

```bash
source .venv/bin/activate
cd models/baseline_mast && python -m pytest -q     # 67 passed
cd ../.. && ruff check session-service serving models
```

The batch runner tests cover the sample batch, stable and unique record ids,
partial results surviving an interrupt, resume without duplication, resume
equalling a clean run, tolerated truncation, failure capture, targeted retry,
retry counting, adapter exceptions becoming structured failures, raw and parsed
output staying linked, and the manifest exclusion and count checks.

## Still open

- MAST 02 (DAT-26) owns the real judge adapter. The `Judge` protocol in
  `run_batch.py` is provisional and states only what the runner needs; DAT-26
  is authoritative and this should be reconciled when it lands.
- `models/baseline_mast/tests` is not yet wired into CI. The workflow file
  belongs to Ayush, so adding the step needs his change, not mine.
- MAST 12 (DAT-36) depends on this plus MAST 03 (DAT-27), and cannot run its
  final protocol until the real adapter exists.
