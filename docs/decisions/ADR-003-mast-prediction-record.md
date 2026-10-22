# ADR-003: MAST prediction record (predictions.jsonl, failures.jsonl, run_manifest.json)

- Status: Proposed
- Date: 2026-10-21
- Owners: prompt and parser owner (author). Reviewers: execution owner (co-owner of the record) and environment owner (ADR coordinator)

## Context

The MAST baseline pipeline already passes one JSON object per trace between its stages:
the runner (DAT-34/35) writes `predictions.jsonl`, `failures.jsonl` and `run_manifest.json`;
the parser (DAT-32) supplies the parsed block of every prediction; the viewer (DAT-33)
and the metrics (DAT-37) read the result. Each stage has been built against the code of
the stage before it, not against a written shape. This ADR records the shape that the code
on `main` produces today, so that no stage changes it silently.

ADR-001 froze the session event contract and ADR-002 persisted the event log, so this record
is ADR-003. It describes the MAST baseline only and does not touch the session service.

Every field below was checked against `models/baseline_mast/run_batch.py` (`_prediction_identity`,
`_record`, `run`), `parse_judge.py` (`ParsedJudgeResponse`, `to_record_fields`),
`provenance.py` (`build_run_manifest`) and `view_results.py`. Where this text and the code
disagree, the code is right and this ADR needs a revision.

## Decision

All files are UTF-8. The two `.jsonl` files are JSON Lines, append-only, and flushed to disk
after every line. A partial final line left by a killed run is closed off on restart and
ignored by readers. `run_manifest.json` is written atomically.

### 1. predictions.jsonl

One line per successfully judged trace. The final record is the identity, execution and
reference fields below, updated with the parsed block, so the parsed block wins where a name
appears in both.

Identity

| field | type | meaning | written by |
|---|---|---|---|
| run_id | string | Run that produced the line. Every line in one result directory has the same value. | runner |
| trace_id | string | Record key, `make_record_id(trace_key, trace_index)`, i.e. `<trace_key>::<trace_index>`. The dataset's own trace id repeats across source runs, so this pair is the only unique key. | runner |
| trace_key | string | First part of the record key (the dataset's `trace.key`). | runner |
| trace_index | integer | Second part of the record key (the dataset's `trace_id`). | runner |
| framework | string | Multi-agent framework of the trace (dataset `mas_name`). | runner |
| llm_name | string | Model that produced the trace (dataset `llm_name`). | runner |
| benchmark | string | Benchmark of the trace (dataset `benchmark_name`). | runner |

Versions

| field | type | meaning | written by |
|---|---|---|---|
| dataset_version | string | `manifest_version` of the frozen evaluation manifest, or `"unknown"`. It names the manifest, not the Hugging Face revision. | runner |
| dataset_sha256 | string | SHA-256 of the dataset file named by the evaluation manifest. | runner |
| prompt_version | string | Prompt version, `mast-judge-v1`. Repeated in the parsed block. | runner, parser |
| prompt_sha256 | string | SHA-256 of `judge_prompt.txt`. | runner |
| parser_version | string | Parser version. Repeated in the parsed block. | runner, parser |
| model_id | string | Identifier of the judge model. | runner |
| model_settings | object | Generation settings of the judge, after `provenance.redact` removes anything that looks like a credential. | runner |

Execution

| field | type | meaning | written by |
|---|---|---|---|
| timestamp_utc | string | UTC time of the record, format `YYYY-MM-DDTHH:MM:SSZ`. | runner |
| latency_ms | number | Judge call time in milliseconds, rounded to three decimals. | runner |
| retry_count | integer | Retries used before the call returned. | runner |
| error | string or null | Judge error. Always null on a predictions line, because a call with an error goes to `failures.jsonl`. | runner |
| truncated | boolean | True if the trace exceeded the prompt limit and was cut before sending. | runner |
| prompt_tokens | integer or null | Prompt tokens reported by the judge adapter. | runner |
| completion_tokens | integer or null | Completion tokens reported by the judge adapter. | runner |

Reference

| field | type | meaning | written by |
|---|---|---|---|
| reference_source | string | `reference_type` of the evaluation manifest that supplied the reference labels (for example `released_llm_annotation`, `human_consensus`). | runner |
| human_labels | object | Reference labels, failure mode code to true, false or null. The key keeps its name; the value is whatever `reference_source` names. | runner |

Raw

| field | type | meaning | written by |
|---|---|---|---|
| raw_response | string or null | The judge reply exactly as returned. Null if the adapter returned neither text nor an error. | parser (copied from the input) |
| raw_type | string | Python type name of the value handed to the parser (normally `str`). | parser |

Parsed (`to_record_fields(ParsedJudgeResponse)`)

| field | type | meaning | written by |
|---|---|---|---|
| parse_status | string | One of `ok`, `partial`, `ambiguous`, `empty`, `malformed`. | parser |
| labels | object | Validated labels, code to true, false or null. Null means the parser could not read that code. | parser |
| predicted_labels | array of string | Codes whose label is true. | parser |
| missing_codes | array of string | Codes with no answer in the reply. | parser |
| ambiguous_codes | array of string | Codes whose answer could not be read as yes or no. | parser |
| conflicting_codes | array of string | Codes answered twice with different values. | parser |
| unknown_codes | array of string | Codes in the reply that are not one of the 14 known codes. | parser |
| summary | string or null | One-line summary from the reply, if present. | parser |
| task_completed | boolean or null | Task-completed answer from the reply, if present. | parser |
| warnings | array of string | Parser notes such as `duplicate_code:<code>`. | parser |
| labels_official | object | Code to 0 or 1, from a port of the upstream scoring function. For comparison with the published pipeline only; never scored. | parser |

The parsed block also carries `raw_response`, `raw_type`, `prompt_version` and `parser_version`.
`prompt_version` and `parser_version` in the parsed block equal the identity values by
construction (the runner passes `PROMPT_VERSION` to the parser, which stamps its own
`PARSER_VERSION`).

### 2. failures.jsonl

| field | type | meaning | written by |
|---|---|---|---|
| run_id | string | Run that tried the trace. | runner |
| trace_id | string | Record key, as above. | runner |
| error | string | Error returned or raised by the judge after the last retry. | runner |
| retry_count | integer | Retries used. | runner |
| timestamp_utc | string | UTC time, same format as above. | runner |

A failed call is written here and not to `predictions.jsonl`. Completed traces are those with a
line in `predictions.jsonl`, so a resumed run retries every trace that only has a failure.

### 3. run_manifest.json

One JSON object per result directory, rewritten at the end of every runner invocation. The
counts describe the last invocation, not the whole directory. Names are exactly those of
`build_run_manifest`.

| group | fields | written by |
|---|---|---|
| Run | run_id, linear, owner (free text naming who wrote the manifest code) | runner |
| Code | git_sha, git_branch, git_dirty, git_dirty_files | runner |
| Environment | environment (object: python_version, platform, machine, cpu_count) | runner |
| Dataset | dataset_path, dataset_sha256, dataset_revision, reference_source | runner |
| Evaluation manifest | eval_manifest_path, eval_manifest_version, eval_manifest_status, eval_manifest_linear (the last only when the evaluation manifest could be read) | runner |
| Prompt and parser | prompt_version, prompt_sha256, prompt_upstream_commit, parser_version | runner (values from the prompt and parser modules) |
| Model | model_id, model_settings (redacted) | runner |
| Outcome | start_time_utc, end_time_utc, attempted, succeeded, failed, skipped, parse_status_counts, prompt_tokens, completion_tokens | runner |
| Where outputs live | result_dir, predictions_file, failures_file, raw_response_field, parsed_labels_field, record_key_field, record_key_note | runner |

`provenance.REQUIRED_MANIFEST_FIELDS` lists the fields that must be present and non-null:
run_id, git_sha, dataset_sha256, eval_manifest_version, prompt_version, prompt_sha256,
parser_version, model_id, model_settings, start_time_utc, end_time_utc, parse_status_counts,
predictions_file. The whole manifest passes through `provenance.redact` before it is written.

The runner refuses to append to a result directory whose existing files carry a different
identity: for `predictions.jsonl` any of run_id, dataset_version, dataset_sha256,
prompt_version, prompt_sha256, parser_version, model_id or model_settings; for `failures.jsonl`
the run_id; for `run_manifest.json` any of run_id, dataset_sha256, prompt_version,
prompt_sha256, parser_version, model_id or model_settings. The remedy is a new result directory.

### 4. Rules

a. `raw_response` is mandatory on every predictions line and is never rewritten or truncated
   after the call.
b. Re-parsing an existing run writes a new predictions file with a new `parser_version`. It
   never edits the old lines in place.
c. A label that the parser cannot read is null, never false. Null is not a negative label.
   How null is scored is the evaluation owner's decision and is out of scope here.
d. `human_labels` holds whatever `reference_source` names (a human file or released LLM-judge
   labels). Results from different reference sources are reported separately.
e. The answer template in `judge_prompt.txt` names 3.2 and 3.3 the other way round from
   `definitions.txt`. The parser keys labels by the template's numbering. The scoring meaning
   of 3.2 and 3.3 is the evaluation owner's decision.
f. The record key is `trace_id` as produced by `make_record_id`. Any change to the key policy
   (see DAT-54, MAST-17) needs a new record version and an update to this ADR.
g. Adding a field is allowed if every reader ignores unknown fields. Renaming or removing a
   field needs a new ADR revision.

## Consequences

- The viewer and the metrics read this shape. The viewer already reads these field names from
  its constants block and treats a missing field as empty.
- The metrics loader that turns `predictions.jsonl` into label matrices in `MAST_CODES` order,
  and the rule for null labels, are the next step, to be agreed with the evaluation owner.
- The prompt is frozen: version `mast-judge-v1`, sha256
  `6a73fd53d0e559cd0ee131adec530cf11f687f008132ae8c29a3eedff81bca7c`. A change creates a new
  prompt version and a new protocol version.
- Because manifest counts describe the last invocation, a resumed run's manifest does not show
  directory totals. Readers that need totals count lines in `predictions.jsonl` and
  `failures.jsonl`. Whether the manifest should accumulate is a question for the execution owner.
- Status stays Proposed until the execution owner and the environment owner have reviewed it.
