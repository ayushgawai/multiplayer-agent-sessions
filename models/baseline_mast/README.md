# MAST baseline judge

This folder holds the frozen MAST LLM-as-a-Judge prompt, the response parser,
and a static result viewer over saved prediction records. The evaluation
harness consumes `judge_prompt.txt` through `prompt_file` in
`eval/configs/base-*.yaml` (owned by the evaluation owner).

## Judge prompt mast-judge-v1

Upstream:
https://github.com/multi-agent-systems-failure-taxonomy/MAST at commit
`a70542e541b2104ef8fcd785778179e173fb8d70`. Source:
`llm_judge_pipeline.ipynb` cell 0 (`openai_evaluator`), with
`definitions.txt` and `examples.txt` inlined.

- File sha256:
  `6a73fd53d0e559cd0ee131adec530cf11f687f008132ae8c29a3eedff81bca7c`
- Golden render (trace `<<TRACE>>`): length 83204, same sha256 as the file
- Messages: one user message, no system message
- Section order: instructions, answer template, example answer, trace,
  definitions, examples
- Reference condition: model `o1`, temperature `1.0` (the environment owner's
  adapter chooses the live model and records it)
- Truncation: if `len(trace) + 67469 > 1048570`, keep
  `trace[:981101]` (`MAX_TRACE_CHARS`)
- Upstream sha256 of `definitions.txt`:
  `bfefa4f2c788fa1658f6879afa8a2b4577a027f224ce3e3b6ba0927dfd82f9ce`
- Upstream sha256 of `examples.txt`:
  `3cf84f024eccecbb1f51deddae889bd8d14d55b539002665210555f00fe60964`

## Response parser mast-parser-v1

`parse_judge.py` turns a judge reply into validated labels with an explicit
parse status. Validated labels never silently default missing codes to false.

| Status | Meaning |
|--------|---------|
| `ok` | All 14 codes present, no conflicts or ambiguity |
| `partial` | At least one code missing |
| `ambiguous` | Conflicting duplicates or unclear yes/no |
| `empty` | None or blank input |
| `malformed` | Non-string (non-dict) input, or no MAST codes found |

Fields include `raw_response` (unmodified), `labels`, `predicted_labels`,
`missing_codes`, `ambiguous_codes`, `conflicting_codes`, `unknown_codes`,
`summary`, `task_completed`, `warnings`, and `labels_official`.

Rules:
- `raw_response` is preserved byte-for-byte for string inputs
- Missing codes stay `null` (never coerced to false)
- `labels_official` is a faithful port of upstream cell-8 `parse_responses`
  for reproduction comparison only; it is not the validated label
- On all-yes template answers, validated predicted count is 14 while
  `sum(labels_official.values())` is 12 because upstream matches `yes`/`no`
  without word boundaries and misreads `2.5` (substring `no` in "Ignored")
  and `3.2` (leading "No" in the template name)
- How failed parses count in metrics is decided by the evaluation owner

## Result viewer

Field names follow ADR-002 (proposed). The viewer reads saved JSONL only; it
never calls a model.

```bash
PYTHONPATH=. python models/baseline_mast/view_results.py \
  --predictions path/to/predictions.jsonl \
  --manifest path/to/run_manifest.json \
  --out path/to/report.html
```

Header: run id, model, prompt version plus sha256 prefix, parser version,
dataset version, record count, counts by `parse_status`, disagreement count,
and per-code FP/FN totals.

Main table columns: `trace_id`, `framework`, `parse_status`, disagreement
count, then a 14-code grid. Each cell shows text `TP` / `FP` / `FN` / `TN` /
`NA` (colour is optional; text is the signal).

Filters (inline script): disagreements only; parse problems only
(`parse_status` not `ok`); framework dropdown; code dropdown (FP or FN on that
code); text search on `trace_id`. Default shows all rows with "N of M shown".

`tests/fixtures/sample_run/` is **test data only** (built by calling
`parse_judge_response` on parser fixtures). Do not treat it as a real judge run.

## Known quirks preserved on purpose

- Missing spaces between joined string literals (for example
  `behaviour.There are several`)
- Example answer lists codes `1.6` and `2.7`, which are absent from the answer
  template
- Codes `3.2` and `3.3` use swapped names between the answer template and
  `definitions.txt`
- Trailing spaces on example-answer lines; no final newline on the template
- Upstream `parse_responses` matches `yes`/`no` without word boundaries (can
  misread `2.5` and `3.2`) and defaults missing answers to 0

## Rules

`judge_prompt.txt` is written only by script, never saved from an editor. Any
content change creates `mast-judge-v2` and a new protocol version; `v1` stays
frozen for the reproduction condition.

## Verify

```bash
cd models/baseline_mast && pytest -q && cd ../..
ruff check models
mypy --ignore-missing-imports models/baseline_mast
PYTHONPATH=. python models/baseline_mast/check_prompt.py
PYTHONPATH=. python models/baseline_mast/check_parser.py
PYTHONPATH=. python models/baseline_mast/view_results.py \
  --predictions models/baseline_mast/tests/fixtures/sample_run/predictions.jsonl \
  --manifest models/baseline_mast/tests/fixtures/sample_run/run_manifest.json \
  --out /tmp/mast_viewer.html
```

## Open questions

- How `3.2` / `3.3` names map to human labels (dataset owner)
- Upstream repo has no LICENSE file; team to confirm committing the inlined text
- CI does not yet run pytest for this folder (request to environment owner)
- Root `.editorconfig` would trim trailing spaces and insert a final newline;
  request an exception for `judge_prompt.txt` from the environment owner
