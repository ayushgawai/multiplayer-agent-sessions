# M1 evaluation protocol

This document describes the executable M1 evaluation boundary introduced by DAT-61. The frozen
task, candidate matrix, schemas, seeds, metrics, safety gates, and winner policy live in
`eval/configs/m1-contract.yaml` and the four `eval/configs/m1-*.yaml` files. This document does not
change those decisions.

## What the shared harness owns

`eval/harness.py` is the only orchestration path for M1 candidate comparison. It:

- strictly validates the experiment and candidate YAML files;
- sets Python, NumPy, and (when installed) PyTorch seeds;
- requires all frozen seeds `13, 29, 47` for a reportable run;
- rejects a dirty, untracked, missing, or manifest-less reportable dataset, and tracked uncommitted
  changes under `eval/` or `models/`, so `git_sha` describes the code that ran;
- verifies every split file named in the dataset `MANIFEST.json` (sha256, row count, and byte size
  when recorded) before a reportable run, and requires each seed to evaluate exactly the manifest's
  `test` split row count;
- refuses runner or evaluator plugins from a `tests` package (for example
  `eval.tests.fake_m1_plugin`) for reportable runs;
- refuses to overwrite an existing reportable result or prediction file;
- rejects approved memory during candidate selection;
- validates every prediction against `m1-output-v1` and its input evidence ids;
- predicts every evaluated example once and times each call after a few untimed warm-up calls
  (1 for smoke, 10 for reportable runs), so `latency_p50_ms` and `latency_p95_ms` are percentiles
  over all evaluated examples, including the long-context tail; records peak VRAM reported by the
  runner;
- records a candidate exception on an example as an invalid prediction for that example
  (`output` is `{"_exception": "<type>"}`, counted under `invalid_schema` and in
  `schema_valid_rate`) instead of aborting the seed; the failed call is still timed;
- writes deterministic-key-order result JSON and prediction JSONL with checksums;
- records the git SHA, config digest, pinned model revision, dataset version, hardware, failures,
  runtime, and per-seed metrics;
- records the runner and evaluator that actually ran (`module:qualname` plus the sha256 of the
  module source), the dataset manifest sha256 and split row count, and for every seed the sha256
  of the sorted example ids and of the canonical example content.

Result files use schema `candidate-result-v2`.

Smoke runs are explicitly marked `smoke_non_reportable`. They cannot be accepted by
`eval/compare.py` or used to select a candidate.

## Candidate-owner runner interface

Each candidate owner supplies a Python factory using `module:symbol` syntax. The callable accepts a
`RunnerRequest` and returns a `PreparedCandidate` implementation:

```python
def build_eval_runner(request: RunnerRequest) -> PreparedCandidate:
    ...
```

The prepared candidate exposes:

- `dataset_version: str`
- `hardware: str`
- `examples: Sequence[M1EvaluationExample]`
- `predict(model_input: M1Input) -> Mapping[str, Any]`
- `peak_vram_mb() -> float`
- `close() -> None`

Training, checkpoint loading, prompts, and candidate-specific preprocessing stay in the candidate
module. They must not be added to the harness. The harness owns inference timing and validates the
candidate's returned object.

Ayush can implement these factories under `models/m1_catchup/` without modifying `eval/`.

## Metric-owner evaluator interface

The harness requires an evaluator plugin explicitly:

```python
def evaluate(
    examples: Sequence[M1EvaluationExample],
    predictions: Sequence[PredictionRecord],
    config: M1CandidateConfig,
    seed: int,
) -> EvaluationSummary:
    ...
```

The evaluator returns all contract metrics except the harness-owned metrics
`schema_valid_rate`, `latency_p50_ms`, `latency_p95_ms`, and `peak_vram_mb`. The harness rejects
missing metrics, extra metrics, unknown failure codes, non-finite numbers, and attempts to overwrite
harness-owned measurements.

There is deliberately no silent default evaluator. A reportable run must name the reviewed metric
implementation; the CPU test double under `eval/tests/` is only for orchestration tests and must
never be used for a bake-off.

## Commands

Run a CPU-only orchestration smoke test for one candidate (smoke runs may use the test double; a
reportable run with it is refused):

```bash
python -m eval.harness \
  --task m1 \
  --candidate m1-a \
  --split smoke \
  --smoke \
  --runner m1-a=eval.tests.fake_m1_plugin:build_eval_runner \
  --evaluator eval.tests.fake_m1_plugin:evaluate \
  --output-dir /tmp/m1-harness-smoke
```

The smoke output is pipeline evidence only. A real reportable candidate command has this shape:

```bash
python -m eval.harness \
  --task m1 \
  --candidate m1-c \
  --seeds 13,29,47 \
  --split session_test \
  --runner m1-c=models.m1_catchup.phi_qlora:build_eval_runner \
  --evaluator eval.m1_evaluator:evaluate
```

After all four reportable results exist, generate the comparison table:

```bash
python -m eval.compare \
  --task m1 \
  --split session_test \
  --results-dir eval/results \
  --out docs/tables/m1_bakeoff.md
```

`eval/compare.py` refuses incomplete or mixed artifacts. In addition to the contract version, task,
split, seeds, and metric set, all four results must agree on the split path, dataset version,
dataset manifest sha256, manifest row count, and evaluator identity (spec and module hash); every
candidate and seed must have evaluated the same example ids and content, and the full manifest row
count. A result produced by a runner or evaluator from a `tests` package is refused.

It then applies the frozen safety gates per seed and ranks only eligible candidates, keeping any
candidate within a metric's margin of the stage best (with a 1e-9 float tolerance). It labels the
leading result as provisional. The final winner still requires the frozen blinded human review of
the top two eligible candidates.

Only `session_test` can select a candidate. `--split qmsum_test` produces a diagnostic table with
no eligibility decision, no rank, and no leader, because ADR-005 forbids QMSum from selecting the
product winner.

## Required verification before a reportable run

```bash
ruff check eval
mypy eval
python -m pytest eval/tests -q
```

The reportable session split is not present until the data-owner artifact is reviewed and merged.
The metric evaluator is also a separately reviewed dependency. Until both exist, only the smoke
orchestration path is valid; no M1 quality or winner claim may be made.
