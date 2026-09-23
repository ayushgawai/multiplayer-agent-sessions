# MAST baseline judge

This folder holds the frozen MAST LLM-as-a-Judge prompt and, later, the response
parser and result viewer. The evaluation harness consumes `judge_prompt.txt`
through `prompt_file` in `eval/configs/base-*.yaml` (owned by the evaluation
owner).

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
```

## Open questions

- How `3.2` / `3.3` names map to human labels (dataset owner)
- Upstream repo has no LICENSE file; team to confirm committing the inlined text
- CI does not yet run pytest for this folder (request to environment owner)
- Root `.editorconfig` would trim trailing spaces and insert a final newline;
  request an exception for `judge_prompt.txt` from the environment owner
