"""Shared, fail-closed M1 evaluation harness.

Candidate owners provide a runner plugin that prepares a model and exposes
``predict(M1Input)``. Metric owners provide an evaluator plugin. The harness
owns seeds, contract validation, latency measurement, provenance, aggregation,
and result serialization.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import json
import math
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TypeVar, cast

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.contracts.m1 import M1Output, validate_m1_pair  # noqa: E402
from eval.run_contract import (  # noqa: E402
    HARNESS_METRICS,
    REPORTABLE_PROTOCOL,
    SMOKE_PROTOCOL,
    CandidateResult,
    EvaluationSummary,
    Evaluator,
    M1CandidateConfig,
    M1EvaluationExample,
    M1ExperimentContract,
    MetricSummary,
    PluginIdentity,
    PredictionRecord,
    PreparedCandidate,
    RunnerFactory,
    RunnerRequest,
    SeedRunResult,
    is_test_plugin,
)
from eval.seeding import set_all_seeds  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "eval" / "configs"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "eval" / "results"
M1_CANDIDATES = ("m1-a", "m1-b", "m1-c", "m1-d")
DEFAULT_RUNNERS = {
    "m1-a": "models.m1_catchup.bm25:build_eval_runner",
    "m1-b": "models.m1_catchup.modernbert:build_eval_runner",
    "m1-c": "models.m1_catchup.phi_qlora:build_eval_runner",
    "m1-d": "models.m1_catchup.qwen_qlora:build_eval_runner",
}
# Which MANIFEST.json split entry holds the examples evaluated for each reportable split.
MANIFEST_SPLIT_KEYS = {"qmsum_test": "test", "session_test": "test"}
T = TypeVar("T")


class HarnessError(RuntimeError):
    """A fail-closed contract, runner, evaluator, or provenance error."""


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise HarnessError(f"cannot load YAML {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise HarnessError(f"YAML root must be a mapping: {path}")
    return cast(dict[str, Any], payload)


def load_contract(path: Path = CONFIG_DIR / "m1-contract.yaml") -> M1ExperimentContract:
    try:
        return M1ExperimentContract.model_validate(_load_yaml(path))
    except ValueError as exc:
        raise HarnessError(f"invalid M1 experiment contract {path}: {exc}") from exc


def load_candidate_config(candidate_id: str) -> tuple[M1CandidateConfig, Path]:
    if candidate_id not in M1_CANDIDATES:
        raise HarnessError(f"unknown M1 candidate: {candidate_id}")
    path = CONFIG_DIR / f"{candidate_id}.yaml"
    try:
        config = M1CandidateConfig.model_validate(_load_yaml(path))
    except ValueError as exc:
        raise HarnessError(f"invalid candidate config {path}: {exc}") from exc
    if config.candidate_id != candidate_id:
        raise HarnessError(f"candidate config identity mismatch in {path}")
    return config, path


def load_task_configs(candidate_ids: Sequence[str]) -> list[tuple[M1CandidateConfig, Path]]:
    loaded = [load_candidate_config(candidate_id) for candidate_id in candidate_ids]
    first = loaded[0][0]
    shared_fields = (
        "contract",
        "task",
        "split",
        "evaluation_split",
        "schemas",
        "seeds",
        "metrics",
        "primary_metric",
        "failure_codes",
    )
    for config, path in loaded[1:]:
        for field in shared_fields:
            if getattr(config, field) != getattr(first, field):
                raise HarnessError(f"{path} disagrees on shared field {field}")
    learned = [config for config, _ in loaded if config.train is not None]
    for field in ("epochs", "max_seq_len", "effective_batch_size"):
        values = {getattr(config.train, field) for config in learned if config.train is not None}
        if len(values) > 1:
            raise HarnessError(f"learned candidates disagree on shared train field {field}")
    return loaded


def _load_symbol(spec: str) -> Any:
    module_name, separator, symbol_name = spec.partition(":")
    if not separator or not module_name or not symbol_name:
        raise HarnessError(f"plugin must use module:symbol syntax: {spec!r}")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise HarnessError(f"cannot import plugin module {module_name!r}: {exc}") from exc
    try:
        return getattr(module, symbol_name)
    except AttributeError as exc:
        raise HarnessError(f"plugin module {module_name!r} has no {symbol_name!r}") from exc


def load_runner(spec: str) -> RunnerFactory:
    runner = _load_symbol(spec)
    if not callable(runner):
        raise HarnessError(f"runner plugin is not callable: {spec}")
    return cast(RunnerFactory, runner)


def load_evaluator(spec: str) -> Evaluator:
    evaluator = _load_symbol(spec)
    if not callable(evaluator):
        raise HarnessError(f"evaluator plugin is not callable: {spec}")
    return cast(Evaluator, evaluator)


def plugin_identity(plugin: object, *, role: str) -> PluginIdentity:
    """Identify the callable that actually ran, by module:qualname and module source hash."""

    module = inspect.getmodule(plugin)
    qualname = getattr(plugin, "__qualname__", None)
    if module is None or not qualname:
        raise HarnessError(f"{role} plugin must be a named module-level callable")
    try:
        source_file = inspect.getsourcefile(module)
    except TypeError:
        source_file = None
    if source_file is None or not Path(source_file).is_file():
        raise HarnessError(f"{role} plugin module {module.__name__!r} has no source file to hash")
    return PluginIdentity(
        spec=f"{module.__name__}:{qualname}",
        module_sha256=hashlib.sha256(Path(source_file).read_bytes()).hexdigest(),
    )


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise HarnessError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def git_sha() -> str:
    return _git("rev-parse", "HEAD")


def require_clean_tracked_dataset(dataset_path: Path) -> None:
    """Reject missing, untracked, dirty, or manifest-less reportable datasets."""

    resolved = dataset_path.resolve()
    try:
        relative = resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise HarnessError("reportable dataset must be inside the repository") from exc
    if not resolved.is_dir():
        raise HarnessError(f"dataset directory does not exist: {relative}")
    if not (resolved / "MANIFEST.json").is_file():
        raise HarnessError(f"reportable dataset has no MANIFEST.json: {relative}")
    tracked = _git("ls-files", "--", relative.as_posix()).splitlines()
    if not tracked:
        raise HarnessError(f"reportable dataset is not tracked by git: {relative}")
    dirty = _git("status", "--porcelain", "--", relative.as_posix())
    if dirty:
        raise HarnessError(f"reportable dataset has uncommitted changes:\n{dirty}")


def require_clean_tracked_code() -> None:
    """Reject reportable runs whose tracked evaluation or candidate code differs from git_sha."""

    dirty = _git("status", "--porcelain", "--untracked-files=no", "--", "eval", "models")
    if dirty:
        raise HarnessError(
            "reportable runs require committed eval/ and models/ code; uncommitted changes:\n" + dirty
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_split_manifest(dataset_path: Path, split_key: str) -> tuple[str, int]:
    """Check every split file against MANIFEST.json and return (manifest sha256, split count).

    Each entry under ``splits`` must give ``sha256`` and ``count``; ``bytes`` is checked when
    present. The file is ``entry["file"]`` when given, otherwise ``<split name>.jsonl``.
    """

    manifest_path = dataset_path / "MANIFEST.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessError(f"cannot read dataset manifest {manifest_path}: {exc}") from exc
    splits = manifest.get("splits") if isinstance(manifest, dict) else None
    if not isinstance(splits, dict) or not splits:
        raise HarnessError(f"dataset manifest has no splits: {manifest_path}")
    if split_key not in splits:
        raise HarnessError(f"dataset manifest has no {split_key!r} split: {manifest_path}")
    for name, entry in splits.items():
        if not isinstance(entry, dict) or "sha256" not in entry or "count" not in entry:
            raise HarnessError(f"manifest split {name!r} must record sha256 and count")
        split_file = dataset_path / str(entry.get("file", f"{name}.jsonl"))
        if not split_file.is_file():
            raise HarnessError(f"manifest split file is missing: {split_file}")
        if "bytes" in entry and split_file.stat().st_size != entry["bytes"]:
            raise HarnessError(f"split file size does not match MANIFEST.json: {split_file}")
        if _sha256_file(split_file) != entry["sha256"]:
            raise HarnessError(f"split file sha256 does not match MANIFEST.json: {split_file}")
        with split_file.open("rb") as stream:
            rows = sum(1 for line in stream if line.strip())
        if rows != entry["count"]:
            raise HarnessError(
                f"split file {split_file} has {rows} rows; MANIFEST.json records {entry['count']}"
            )
    count = splits[split_key]["count"]
    if not isinstance(count, int) or count <= 0:
        raise HarnessError(f"manifest split {split_key!r} count must be a positive integer")
    return _sha256_file(manifest_path), count


def dataset_path_for_split(config: M1CandidateConfig, contract: M1ExperimentContract, split: str) -> Path:
    if split == "session_test":
        configured = config.evaluation_split
        expected = contract.split["session_path"]
    elif split == "qmsum_test":
        configured = config.split
        expected = contract.split["qmsum_path"]
    elif split == "smoke":
        configured = "data/m1_smoke/fixtures/"
        expected = configured
    else:
        raise HarnessError(f"unsupported M1 split: {split}")
    if configured != expected:
        raise HarnessError(
            f"candidate {config.candidate_id} split path {configured!r} does not match contract {expected!r}"
        )
    return REPO_ROOT / configured


def _portable_path(path: Path) -> str:
    """Return a repository-relative path when possible for portable provenance."""

    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _safe_json_number(value: float, *, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise HarnessError(f"{name} must be a finite number")
    return number


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise HarnessError("latency measurement produced no samples")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_predictions(path: Path, predictions: Sequence[PredictionRecord]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for prediction in predictions:
            stream.write(
                json.dumps(
                    prediction.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_examples(
    examples: Sequence[M1EvaluationExample], *, smoke: bool, max_examples: int | None
) -> list[M1EvaluationExample]:
    selected = list(examples)
    if smoke:
        selected = selected[: max_examples or 20]
    elif max_examples is not None:
        raise HarnessError("max_examples is allowed only for non-reportable smoke runs")
    if not selected:
        raise HarnessError("runner returned no evaluation examples")
    example_ids = [example.model_input.example_id for example in selected]
    if len(example_ids) != len(set(example_ids)):
        raise HarnessError("evaluation examples must have unique example_id values")
    if not smoke:
        leaking = [
            example.model_input.example_id
            for example in selected
            if example.model_input.approved_memory or example.model_input.memory_version is not None
        ]
        if leaking:
            raise HarnessError(
                "candidate-selection inputs must have memory disabled; offending examples: "
                + ", ".join(leaking[:5])
            )
    return selected


def _example_hashes(examples: Sequence[M1EvaluationExample]) -> tuple[str, str]:
    """Return (sha256 of sorted example ids, sha256 of the canonical example content)."""

    ordered = sorted(examples, key=lambda example: example.model_input.example_id)
    ids = "\n".join(example.model_input.example_id for example in ordered)
    content = "\n".join(
        json.dumps(example.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        for example in ordered
    )
    return (
        hashlib.sha256(ids.encode("utf-8")).hexdigest(),
        hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )


def _predict_and_validate(
    prepared: PreparedCandidate,
    examples: Sequence[M1EvaluationExample],
    config: M1CandidateConfig,
) -> list[PredictionRecord]:
    predictions: list[PredictionRecord] = []
    for example in examples:
        raw = prepared.predict(example.model_input)
        output = dict(raw) if isinstance(raw, Mapping) else {"_raw_repr": repr(raw)}
        valid = True
        error: str | None = None
        try:
            parsed = M1Output.model_validate(output)
            if parsed.candidate_id != config.candidate_id:
                raise ValueError(
                    f"output candidate_id {parsed.candidate_id!r} does not match {config.candidate_id!r}"
                )
            validate_m1_pair(example.model_input, parsed)
        except ValueError as exc:
            valid = False
            error = str(exc)
        predictions.append(
            PredictionRecord(
                example_id=example.model_input.example_id,
                output=output,
                valid=valid,
                validation_error=error,
            )
        )
    return predictions


def _measure_latency(
    prepared: PreparedCandidate,
    example: M1EvaluationExample,
    *,
    smoke: bool,
    timer: Callable[[], float],
) -> list[float]:
    warmups = 1 if smoke else 10
    measured = 3 if smoke else 100
    for _ in range(warmups):
        prepared.predict(example.model_input)
    samples: list[float] = []
    for _ in range(measured):
        started = timer()
        prepared.predict(example.model_input)
        elapsed_ms = (timer() - started) * 1000.0
        samples.append(_safe_json_number(elapsed_ms, name="latency sample"))
    return samples


def run_seed(
    *,
    config: M1CandidateConfig,
    seed: int,
    split: str,
    dataset_path: Path,
    output_dir: Path,
    runner_factory: RunnerFactory,
    evaluator: Evaluator,
    smoke: bool,
    max_examples: int | None = None,
    timer: Callable[[], float] = time.perf_counter,
) -> tuple[SeedRunResult, str]:
    set_all_seeds(seed)
    started = timer()
    request = RunnerRequest(
        config=config,
        seed=seed,
        split=split,
        dataset_path=dataset_path,
        smoke=smoke,
        max_examples=max_examples,
    )
    prepared = runner_factory(request)
    try:
        if not prepared.dataset_version.strip():
            raise HarnessError("runner dataset_version must not be blank")
        if not prepared.hardware.strip():
            raise HarnessError("runner hardware must not be blank")
        examples = _validate_examples(prepared.examples, smoke=smoke, max_examples=max_examples)
        example_ids_sha, examples_sha = _example_hashes(examples)
        latency = _measure_latency(prepared, examples[0], smoke=smoke, timer=timer)
        predictions = _predict_and_validate(prepared, examples, config)
        summary = evaluator(examples, predictions, config, seed)
        if not isinstance(summary, EvaluationSummary):
            summary = EvaluationSummary.model_validate(summary)

        overlap = HARNESS_METRICS.intersection(summary.metrics)
        if overlap:
            raise HarnessError(
                "evaluator attempted to overwrite harness-owned metrics: " + ", ".join(sorted(overlap))
            )
        valid_outputs = sum(prediction.valid for prediction in predictions)
        metrics = {
            **summary.metrics,
            "schema_valid_rate": valid_outputs / len(predictions),
            "latency_p50_ms": _percentile(latency, 0.50),
            "latency_p95_ms": _percentile(latency, 0.95),
            "peak_vram_mb": _safe_json_number(prepared.peak_vram_mb(), name="peak_vram_mb"),
        }
        missing_metrics = sorted(set(config.metrics) - set(metrics))
        extra_metrics = sorted(set(metrics) - set(config.metrics))
        if missing_metrics or extra_metrics:
            raise HarnessError(
                f"metric contract mismatch; missing={missing_metrics}, extra={extra_metrics}"
            )
        metrics = {
            name: _safe_json_number(metrics[name], name=f"metric {name}") for name in config.metrics
        }

        unknown_failures = sorted(set(summary.failures) - set(config.failure_codes))
        if unknown_failures:
            raise HarnessError(f"evaluator returned unknown failure codes: {unknown_failures}")
        failures = {code: int(summary.failures.get(code, 0)) for code in config.failure_codes}
        if any(count < 0 for count in failures.values()):
            raise HarnessError("failure counts must be non-negative")
        failures["invalid_schema"] = failures.get("invalid_schema", 0) + (
            len(predictions) - valid_outputs
        )

        prediction_path = (
            output_dir / "predictions" / split / config.candidate_id / f"seed-{seed}.jsonl"
        )
        if not smoke and prediction_path.exists():
            raise HarnessError(f"refusing to overwrite reportable predictions: {prediction_path}")
        prediction_sha = _write_predictions(prediction_path, predictions)
        elapsed_min = max(0.0, (timer() - started) / 60.0)
        try:
            prediction_file = prediction_path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            prediction_file = str(prediction_path)
        return (
            SeedRunResult(
                seed=seed,
                attempted_examples=len(predictions),
                example_ids_sha256=example_ids_sha,
                examples_sha256=examples_sha,
                valid_outputs=valid_outputs,
                metrics=metrics,
                failures=failures,
                prediction_file=prediction_file,
                prediction_sha256=prediction_sha,
                hardware=prepared.hardware,
                peak_vram_mb=metrics["peak_vram_mb"],
                wall_clock_min=elapsed_min,
            ),
            prepared.dataset_version,
        )
    finally:
        prepared.close()


def _metric_summaries(
    runs: Sequence[SeedRunResult], metric_names: Sequence[str]
) -> dict[str, MetricSummary]:
    summaries: dict[str, MetricSummary] = {}
    for metric_name in metric_names:
        values = [run.metrics[metric_name] for run in runs]
        summaries[metric_name] = MetricSummary(
            mean=float(statistics.fmean(values)),
            std=float(statistics.pstdev(values)),
            per_seed=values,
        )
    return summaries


def run_candidate(
    *,
    config: M1CandidateConfig,
    config_path: Path,
    contract: M1ExperimentContract,
    seeds: Sequence[int],
    split: str,
    dataset_path: Path,
    output_dir: Path,
    runner_factory: RunnerFactory,
    evaluator: Evaluator,
    smoke: bool,
    max_examples: int | None = None,
    timer: Callable[[], float] = time.perf_counter,
    enforce_clean_split: bool = True,
) -> CandidateResult:
    if not seeds or len(seeds) != len(set(seeds)):
        raise HarnessError("seeds must be a non-empty unique sequence")
    unknown_seeds = sorted(set(seeds) - set(contract.seeds))
    if unknown_seeds:
        raise HarnessError(f"seeds are outside the frozen contract: {unknown_seeds}")
    if not smoke and list(seeds) != contract.seeds:
        raise HarnessError("reportable runs require every frozen seed in contract order")
    if config.seeds != contract.seeds:
        raise HarnessError(f"{config.candidate_id} seeds do not match the experiment contract")
    if config.schemas != contract.schemas:
        raise HarnessError(f"{config.candidate_id} schemas do not match the experiment contract")
    if set(config.metrics) != set(contract.metrics):
        raise HarnessError(f"{config.candidate_id} metrics do not match the experiment contract")
    runner_identity = plugin_identity(runner_factory, role="runner")
    evaluator_identity = plugin_identity(evaluator, role="evaluator")
    manifest_sha: str | None = None
    manifest_count: int | None = None
    if not smoke:
        for role, identity in (("runner", runner_identity), ("evaluator", evaluator_identity)):
            if is_test_plugin(identity.spec):
                raise HarnessError(
                    f"reportable runs cannot use a test {role} plugin: {identity.spec}"
                )
        if split not in MANIFEST_SPLIT_KEYS:
            raise HarnessError(f"split {split!r} cannot produce a reportable result")
        if enforce_clean_split:
            require_clean_tracked_dataset(dataset_path)
            require_clean_tracked_code()
        manifest_sha, manifest_count = verify_split_manifest(
            dataset_path, MANIFEST_SPLIT_KEYS[split]
        )

    runs: list[SeedRunResult] = []
    dataset_versions: list[str] = []
    for seed in seeds:
        run, dataset_version = run_seed(
            config=config,
            seed=seed,
            split=split,
            dataset_path=dataset_path,
            output_dir=output_dir,
            runner_factory=runner_factory,
            evaluator=evaluator,
            smoke=smoke,
            max_examples=max_examples,
            timer=timer,
        )
        runs.append(run)
        dataset_versions.append(dataset_version)
    if len(set(dataset_versions)) != 1:
        raise HarnessError("runner changed dataset_version across seeds")
    if manifest_count is not None:
        check_reportable_examples(runs, manifest_count)

    failures = {
        code: sum(run.failures[code] for run in runs) for code in config.failure_codes
    }
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    return CandidateResult(
        protocol_mode=SMOKE_PROTOCOL if smoke else REPORTABLE_PROTOCOL,
        contract_version=contract.contract_version,
        task=config.task,
        candidate_id=config.candidate_id,
        label=config.label,
        mode=config.mode,
        trainer=config.trainer,
        split=split,
        split_path=_portable_path(dataset_path),
        dataset_version=dataset_versions[0],
        dataset_manifest_sha256=manifest_sha,
        manifest_example_count=manifest_count,
        runner=runner_identity,
        evaluator=evaluator_identity,
        git_sha=git_sha(),
        model_repo=config.model.repo,
        model_revision=config.model.revision,
        config_sha256=config_sha,
        seeds=list(seeds),
        metrics=_metric_summaries(runs, config.metrics),
        failures=failures,
        runs=runs,
        hardware=sorted({run.hardware for run in runs}),
        peak_vram_mb=max(run.peak_vram_mb for run in runs),
        wall_clock_min=sum(run.wall_clock_min for run in runs),
    )


def check_reportable_examples(runs: Sequence[SeedRunResult], manifest_count: int) -> None:
    """Every seed must evaluate the whole manifest split, and the same examples."""

    for run in runs:
        if run.attempted_examples != manifest_count:
            raise HarnessError(
                f"seed {run.seed} evaluated {run.attempted_examples} examples; "
                f"the manifest split has {manifest_count}"
            )
    if len({(run.example_ids_sha256, run.examples_sha256) for run in runs}) != 1:
        raise HarnessError("seeds evaluated different examples")


def _parse_seeds(raw: str | None, contract: M1ExperimentContract, smoke: bool) -> list[int]:
    if raw is None:
        return [contract.seeds[0]] if smoke else list(contract.seeds)
    try:
        seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    except ValueError as exc:
        raise HarnessError("seeds must be comma-separated integers") from exc
    return seeds


def _parse_runner_overrides(values: Sequence[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for value in values:
        candidate_id, separator, spec = value.partition("=")
        if not separator or candidate_id not in M1_CANDIDATES or not spec:
            raise HarnessError("runner override must use m1-a=module:symbol syntax")
        if candidate_id in overrides:
            raise HarnessError(f"duplicate runner override for {candidate_id}")
        overrides[candidate_id] = spec
    return overrides


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["m1"], default="m1")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--candidate", choices=M1_CANDIDATES)
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--seeds", help="comma-separated frozen seeds")
    parser.add_argument("--split", choices=["session_test", "qmsum_test", "smoke"])
    parser.add_argument("--smoke", action="store_true", help="non-reportable short pipeline run")
    parser.add_argument("--max-examples", type=int)
    parser.add_argument(
        "--runner",
        action="append",
        default=[],
        metavar="CANDIDATE=MODULE:SYMBOL",
        help="candidate runner override; repeat for multiple candidates",
    )
    parser.add_argument(
        "--evaluator",
        required=True,
        metavar="MODULE:SYMBOL",
        help="metric plugin; required so reportable runs cannot silently use a test evaluator",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    contract = load_contract()
    smoke = bool(args.smoke)
    split = args.split or ("smoke" if smoke else contract.split["candidate_selection_split"])
    if smoke and split != "smoke":
        raise HarnessError("--smoke requires --split smoke")
    if not smoke and split == "smoke":
        raise HarnessError("the smoke split is non-reportable and requires --smoke")
    if args.max_examples is not None and (not smoke or args.max_examples <= 0):
        raise HarnessError("--max-examples must be positive and is allowed only with --smoke")

    if args.candidate:
        candidate_ids = [args.candidate]
    elif args.all or smoke:
        candidate_ids = list(M1_CANDIDATES)
    else:
        raise HarnessError("choose --candidate or --all for a reportable run")

    loaded = load_task_configs(candidate_ids)
    overrides = _parse_runner_overrides(args.runner)
    evaluator = load_evaluator(args.evaluator)
    seeds = _parse_seeds(args.seeds, contract, smoke)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for config, _ in loaded:
        result_path = args.output_dir / f"{config.candidate_id}-{split}.json"
        if not smoke and result_path.exists():
            raise HarnessError(f"refusing to overwrite reportable result: {result_path}")

    for config, config_path in loaded:
        dataset_path = dataset_path_for_split(config, contract, split)
        runner_spec = overrides.get(config.candidate_id, DEFAULT_RUNNERS[config.candidate_id])
        result = run_candidate(
            config=config,
            config_path=config_path,
            contract=contract,
            seeds=seeds,
            split=split,
            dataset_path=dataset_path,
            output_dir=args.output_dir,
            runner_factory=load_runner(runner_spec),
            evaluator=evaluator,
            smoke=smoke,
            max_examples=args.max_examples,
        )
        result_path = args.output_dir / f"{config.candidate_id}-{split}.json"
        _write_json(result_path, result.model_dump(mode="json"))
        print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
