"""Tests for M1-A (BM25 extractive baseline)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from data.m1_smoke.loader import load_fixtures, to_m1_input
from data.m1_smoke.schema import M1SmokeExample, Reference
from eval import harness
from eval.contracts.m1 import (
    M1_CATEGORIES,
    M1Event,
    M1Input,
    M1Output,
    validate_m1_pair,
)
from eval.run_contract import M1EvaluationExample, RunnerRequest
from models.m1_catchup import bm25
from models.m1_catchup.bm25 import (
    MAX_CLAIMS_PER_CATEGORY,
    BM25Index,
    build_eval_runner,
    classify_event,
    collapse_whitespace,
    normalize_claim_text,
    predict,
    tokenize,
)

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "m1_smoke" / "fixtures"
SPLITS = load_fixtures(FIXTURES)
ALL_EXAMPLES = [
    (split, example) for split, examples in SPLITS.items() for example in examples
]


def event(
    event_id: str, sequence: int, event_type: str, text: str, actor: str | None = None
) -> M1Event:
    return M1Event(
        event_id=event_id,
        sequence=sequence,
        event_type=event_type,
        actor_id=actor,
        text=text,
    )


def make_input(events: list[M1Event], query: str = "Catch me up.") -> M1Input:
    return M1Input(example_id="ex-1", session_id="s-1", query=query, events=events)


def runner_request(split: str, max_examples: int | None = None) -> RunnerRequest:
    config, _ = harness.load_candidate_config("m1-a")
    return RunnerRequest(
        config=config,
        seed=13,
        split=split,
        dataset_path=FIXTURES,
        smoke=True,
        max_examples=max_examples,
    )


# --- tokenizer --------------------------------------------------------------


def test_tokenizer_lowercases_and_splits_on_punctuation() -> None:
    assert tokenize("Retry-Policy, v2/Backoff!") == ["retry", "policy", "v2", "backoff"]


def test_tokenizer_drops_stopwords_and_keeps_numbers() -> None:
    tokens = tokenize("The soak test is at 31 of 100 runs")
    for stopword in ("the", "is", "at", "of"):
        assert stopword not in tokens
    assert "31" in tokens
    assert "100" in tokens
    assert tokens == ["soak", "test", "31", "100", "runs"]


def test_tokenizer_empty_and_all_stopwords() -> None:
    assert tokenize("") == []
    assert tokenize("the a an") == []


# --- BM25 --------------------------------------------------------------------


def test_bm25_rare_term_document_ranks_first() -> None:
    documents = [
        ["cache", "update", "done"],
        ["cache", "update", "proxy", "timeout"],
        ["cache", "update", "tests"],
    ]
    scores = BM25Index(documents).scores(["proxy"])
    best = max(range(len(scores)), key=scores.__getitem__)
    assert best == 1
    assert scores[0] == 0.0
    assert scores[2] == 0.0
    assert scores[1] > 0.0


def test_bm25_scores_are_deterministic() -> None:
    documents = [["a", "b", "c"], ["b", "c", "d"], ["c", "d", "e", "e"]]
    index = BM25Index(documents)
    query = ["c", "e", "b"]
    assert index.scores(query) == index.scores(query)
    assert BM25Index(documents).scores(query) == index.scores(query)


def test_bm25_idf_follows_the_formula() -> None:
    import math

    index = BM25Index([["x"], ["y"], ["y"]])
    # N=3, df(x)=1: idf = ln(1 + (3 - 1 + 0.5) / (1 + 0.5)); tf=1, dl=avgdl => norm=1
    idf = math.log(1.0 + (3 - 1 + 0.5) / (1 + 0.5))
    expected = idf * 1 * (1.5 + 1.0) / (1 + 1.5 * 1.0)
    assert index.scores(["x"])[0] == pytest.approx(expected)


def test_bm25_handles_empty_corpus_and_unknown_terms() -> None:
    assert BM25Index([]).scores(["x"]) == []
    assert BM25Index([[], []]).scores(["x"]) == [0.0, 0.0]
    assert BM25Index([["a"]]).scores(["zzz"]) == [0.0]


# --- classify_event ----------------------------------------------------------


@pytest.mark.parametrize(
    ("event_type", "text", "expected"),
    [
        ("agent_step", "I am blocked on the vendor API.", "blocked"),
        ("instruction", "We decided to keep the cache.", "decisions"),
        ("arbitration", "Conflict resolved by the arbiter.", "decisions"),
        ("interrupt", "Halt the export now.", "decisions"),
        ("instruction", "I will update the changelog tomorrow.", "pending_actions"),
        ("instruction", "Ada, please send the report.", "pending_actions"),
        ("agent_step", "Running the migration, 3 of 10 tables copied.", "in_progress"),
        ("agent_step", "Created the export module.", "completed"),
        ("doc_update", "Changed the header text.", "completed"),
        ("rollback", "Rolled back the draft; it was not approved.", "completed"),
    ],
)
def test_classify_event_one_positive_case_per_category(
    event_type: str, text: str, expected: str
) -> None:
    assert classify_event(event("e1", 1, event_type, text)) == expected


@pytest.mark.parametrize("event_type", ["join", "leave"])
def test_join_and_leave_never_produce_a_claim(event_type: str) -> None:
    assert classify_event(event("e1", 1, event_type, "I am blocked and done")) is None


def test_neutral_events_have_no_category() -> None:
    assert classify_event(event("e1", 1, "tool_call", "run pytest tests/")) is None
    rows = event("e2", 2, "tool_result", "Read 40 rows from data.csv.")
    paused = event("e3", 3, "agent_step", "Pausing the export, 2 of 5 done.")
    assert classify_event(rows) is None
    assert classify_event(paused) is None


def test_pause_wording_does_not_override_always_decision_event_types() -> None:
    interrupt = event(
        "e1", 1, "interrupt", "Stop. Pausing the migration until legal signs off."
    )
    arbitration = event("e2", 2, "arbitration", "Paused proposal B; proposal A wins.")
    assert classify_event(interrupt) == "decisions"
    assert classify_event(arbitration) == "decisions"


def test_a_pause_by_an_agent_step_still_yields_no_claim() -> None:
    text = "Pausing dark mode as requested. Token mapping is saved at 2 of 5."
    assert classify_event(event("e1", 1, "agent_step", text)) is None


def test_a_tool_error_is_not_work_in_progress() -> None:
    error = event("e1", 1, "tool_result", "Error: permission denied writing to prod.")
    failed = event("e2", 2, "tool_result", "Write failed: writing to disk timed out.")
    assert classify_event(error) != "in_progress"
    assert classify_event(failed) != "in_progress"
    assert classify_event(error) is None
    assert classify_event(failed) is None


def test_existing_in_progress_cases_keep_their_category() -> None:
    writing_text = (
        "Writing 9 tests for pdf_export: empty input, unicode text, and large payloads."
    )
    writing = event("e1", 1, "agent_step", writing_text)
    progress_text = "Running the soak test, 27 of 100 runs done."
    progress = event("e2", 2, "tool_result", progress_text)
    mixed = event("e3", 3, "tool_result", "4 passed, 1 failed: one test timed out.")
    assert classify_event(writing) == "in_progress"
    assert classify_event(progress) == "in_progress"
    assert classify_event(mixed) is None


def test_priority_order_blocked_beats_completed() -> None:
    text = "The export is blocked, although the parser is done."
    assert classify_event(event("e1", 1, "agent_step", text)) == "blocked"


def test_priority_order_decisions_beat_pending_and_in_progress() -> None:
    text = "We decided that Ada will start the work."
    assert classify_event(event("e1", 1, "instruction", text)) == "decisions"
    text = "I will keep running the soak test."
    assert classify_event(event("e2", 2, "instruction", text)) == "pending_actions"


def test_in_progress_beats_completed() -> None:
    text = "Running the soak test, 27 of 100 runs done."
    assert classify_event(event("e1", 1, "agent_step", text)) == "in_progress"


def test_passed_with_a_failure_is_not_completed() -> None:
    mixed = event("e1", 1, "tool_result", "4 passed, 1 failed: one test timed out.")
    clean = event("e2", 2, "tool_result", "All checks passed.")
    assert classify_event(mixed) is None
    assert classify_event(clean) == "completed"


# --- predict: contract on every smoke example --------------------------------


@pytest.mark.parametrize(
    ("split", "example"), ALL_EXAMPLES, ids=[e.example_id for _, e in ALL_EXAMPLES]
)
def test_predict_output_is_valid_and_extractive(
    split: str, example: M1SmokeExample
) -> None:
    model_input = M1Input.model_validate(to_m1_input(example))
    output = predict(model_input)

    parsed = M1Output.model_validate(output)
    validate_m1_pair(model_input, parsed)
    assert parsed.candidate_id == "m1-a"
    expected_keys = {"schema_version", "example_id", "candidate_id", *M1_CATEGORIES}
    assert set(output) == expected_keys

    texts = {e.event_id: collapse_whitespace(e.text) for e in model_input.events}
    sequence = {e.event_id: e.sequence for e in model_input.events}
    cited: list[str] = []
    for category in M1_CATEGORIES:
        claims = parsed_claims(output, category)
        assert len(claims) <= MAX_CLAIMS_PER_CATEGORY
        previous = -1
        for claim in claims:
            assert len(claim["source_event_ids"]) == 1
            event_id = claim["source_event_ids"][0]
            assert event_id in texts
            assert claim["text"] == texts[event_id]
            assert sequence[event_id] > previous
            previous = sequence[event_id]
            cited.append(event_id)
    assert len(cited) == len(set(cited)), "an event appears in more than one claim"


def parsed_claims(output: dict[str, object], category: str) -> list[dict[str, object]]:
    value = output[category]
    assert isinstance(value, list)
    return value


def test_claims_cover_every_category_on_the_fixtures() -> None:
    seen: set[str] = set()
    for _, example in ALL_EXAMPLES:
        output = predict(M1Input.model_validate(to_m1_input(example)))
        seen.update(c for c in M1_CATEGORIES if output[c])
    assert seen == set(M1_CATEGORIES)


# --- predict: extraction and ranking -----------------------------------------


def test_claim_text_is_whitespace_collapsed_event_text() -> None:
    events = [event("e1", 1, "doc_update", "Created   the\n report \t today.")]
    output = predict(make_input(events))
    assert output["completed"] == [
        {"text": "Created the report today.", "source_event_ids": ["e1"]}
    ]


def test_long_text_is_emitted_in_full() -> None:
    long_text = " ".join(["segment"] * 100)
    assert len(long_text) > 240
    output = predict(make_input([event("e1", 1, "doc_update", long_text)]))
    claim_text = output["completed"][0]["text"]
    assert claim_text == collapse_whitespace(long_text)
    assert len(claim_text) > 240


def test_a_trailing_qualifier_is_never_cut_from_a_claim() -> None:
    long_text = (
        "We will ship the billing page on Friday and notify the support team and "
        "the partner accounts about the new invoice layout, the updated tax lines, "
        "the renamed export columns, the changed refund wording and the new "
        "reminder emails, but only if legal does not object."
    )
    assert len(long_text) > 240
    output = predict(make_input([event("e1", 1, "instruction", long_text)]))
    claims = parsed_claims(output, "pending_actions")
    assert [c["text"] for c in claims] == [collapse_whitespace(long_text)]
    assert str(claims[0]["text"]).endswith("only if legal does not object.")


def test_at_most_three_claims_ranked_by_bm25_then_later_sequence() -> None:
    events = [
        event("e1", 1, "doc_update", "Updated the login page."),
        event("e2", 2, "doc_update", "Updated the invoice parser."),
        event("e3", 3, "doc_update", "Updated the invoice template parser module."),
        event("e4", 4, "doc_update", "Updated the footer."),
        event("e5", 5, "doc_update", "Updated the sidebar."),
    ]
    output = predict(make_input(events, query="invoice parser"))
    kept = [claim["source_event_ids"][0] for claim in output["completed"]]
    # e2 and e3 match the query; e5 wins the tie among the rest (later sequence first).
    assert kept == ["e2", "e3", "e5"]


def test_events_without_a_category_are_dropped() -> None:
    events = [
        event("e1", 1, "tool_call", "run pytest"),
        event("e2", 2, "join", "someone joined"),
    ]
    output = predict(make_input(events))
    assert all(output[category] == [] for category in M1_CATEGORIES)
    M1Output.model_validate(output)


# --- duplicate claim text ----------------------------------------------------


def all_claims(output: dict[str, object]) -> list[dict[str, object]]:
    return [
        claim
        for category in M1_CATEGORIES
        for claim in parsed_claims(output, category)
    ]


def test_duplicate_text_in_one_category_emits_one_claim() -> None:
    events = [
        event("e1", 1, "doc_update", "Created the export module."),
        event("e2", 2, "doc_update", "created   the EXPORT module."),
    ]
    output = predict(make_input(events))
    claims = parsed_claims(output, "completed")
    assert len(claims) == 1
    # Equal text means equal BM25 score, so the later event ranks higher.
    assert claims[0]["source_event_ids"] == ["e2"]


def test_same_text_in_two_categories_is_emitted_once_in_the_higher_priority() -> None:
    text = "Created the report; I will ship it."
    pending = event("e1", 1, "instruction", text)
    completed = event("e2", 2, "doc_update", text)
    assert classify_event(pending) == "pending_actions"
    assert classify_event(completed) == "completed"
    output = predict(make_input([pending, completed]))
    pending_claims = parsed_claims(output, "pending_actions")
    assert [c["source_event_ids"] for c in pending_claims] == [["e1"]]
    assert parsed_claims(output, "completed") == []


def test_a_skipped_duplicate_does_not_use_up_a_slot() -> None:
    events = [
        event("e1", 1, "doc_update", "Created the alpha module."),
        event("e2", 2, "doc_update", "Created the beta module."),
        event("e3", 3, "doc_update", "Created the gamma module."),
        event("e4", 4, "doc_update", "Created the delta module."),
        event("e5", 5, "doc_update", "created THE alpha   module."),
    ]
    output = predict(make_input(events, query="alpha"))
    claims = parsed_claims(output, "completed")
    assert len(claims) == MAX_CLAIMS_PER_CATEGORY
    normalized = [normalize_claim_text(str(c["text"])) for c in claims]
    assert len(set(normalized)) == len(normalized)
    # e5 and e1 are the two best matches; e5 wins the pair, e1 is skipped, and the
    # two remaining slots go to the next best distinct events.
    assert [c["source_event_ids"] for c in claims] == [["e3"], ["e4"], ["e5"]]


def test_long_texts_with_a_shared_prefix_are_distinct_claims() -> None:
    prefix = " ".join(["segment"] * 60)
    events = [
        event("e1", 1, "doc_update", prefix + " alpha ending"),
        event("e2", 2, "doc_update", prefix + " beta ending"),
    ]
    output = predict(make_input(events))
    claims = parsed_claims(output, "completed")
    assert [c["text"] for c in claims] == [
        collapse_whitespace(prefix + " alpha ending"),
        collapse_whitespace(prefix + " beta ending"),
    ]


def test_identical_long_texts_are_still_deduplicated() -> None:
    prefix = " ".join(["segment"] * 60)
    events = [
        event("e1", 1, "doc_update", prefix + " ending"),
        event("e2", 2, "doc_update", prefix.upper() + "   ending"),
    ]
    output = predict(make_input(events))
    assert len(parsed_claims(output, "completed")) == 1


@pytest.mark.parametrize(
    ("split", "example"), ALL_EXAMPLES, ids=[e.example_id for _, e in ALL_EXAMPLES]
)
def test_no_smoke_output_has_duplicate_claim_text(
    split: str, example: M1SmokeExample
) -> None:
    output = predict(M1Input.model_validate(to_m1_input(example)))
    normalized = [normalize_claim_text(str(c["text"])) for c in all_claims(output)]
    assert len(normalized) == len(set(normalized))


# --- no gold leakage and determinism -----------------------------------------


def test_changing_gold_does_not_change_the_output() -> None:
    example = SPLITS["dev"][0]
    baseline = predict(M1Input.model_validate(to_m1_input(example)))
    other = SPLITS["dev"][2]
    altered = example.model_copy(
        update={
            "reference": Reference(completed=other.reference.completed),
            "event_labels": {},
            "critical_facts": [],
        }
    )
    assert predict(M1Input.model_validate(to_m1_input(altered))) == baseline


def test_predict_code_never_names_gold_fields() -> None:
    forbidden = ("event_labels", "critical_facts", "reference", "gold_reference")
    for function in (
        predict,
        classify_event,
        tokenize,
        collapse_whitespace,
        BM25Index.scores,
        BM25Index.__init__,
    ):
        source = inspect.getsource(function)
        for name in forbidden:
            assert name not in source, f"{function.__qualname__} mentions {name}"


def test_predict_ignores_approved_memory() -> None:
    plain = make_input([event("e1", 1, "doc_update", "Created the report.")])
    payload = plain.model_dump()
    payload["memory_version"] = "memory-v1"
    payload["approved_memory"] = [
        {"learning_event_id": "l1", "text": "Always report blockers first."}
    ]
    with_memory = M1Input.model_validate(payload)
    assert with_memory.approved_memory
    assert predict(with_memory) == predict(plain)


@pytest.mark.parametrize(
    ("split", "example"), ALL_EXAMPLES, ids=[e.example_id for _, e in ALL_EXAMPLES]
)
def test_predict_is_deterministic(split: str, example: M1SmokeExample) -> None:
    model_input = M1Input.model_validate(to_m1_input(example))
    assert predict(model_input) == predict(model_input)
    assert json.dumps(predict(model_input), sort_keys=True) == json.dumps(
        predict(model_input), sort_keys=True
    )


# --- runner plugin -----------------------------------------------------------


def test_build_eval_runner_smoke_returns_the_holdout_examples() -> None:
    prepared = build_eval_runner(runner_request("smoke"))
    try:
        assert len(prepared.examples) == len(SPLITS["smoke_holdout"])
        assert all(isinstance(e, M1EvaluationExample) for e in prepared.examples)
        assert prepared.hardware.startswith("cpu:")
        assert prepared.peak_vram_mb() == 0.0
        expected_sha = json.loads((FIXTURES / "MANIFEST.json").read_text())["splits"][
            "smoke_holdout"
        ]["sha256"]
        assert prepared.dataset_version == f"m1-smoke-v1:{expected_sha[:12]}"
        first = prepared.examples[0]
        assert first.metadata["session_id"] == first.model_input.session_id
        output = prepared.predict(first.model_input)
        validate_m1_pair(first.model_input, M1Output.model_validate(output))
    finally:
        prepared.close()


def test_build_eval_runner_honors_max_examples() -> None:
    prepared = build_eval_runner(runner_request("smoke", max_examples=2))
    assert len(prepared.examples) == 2
    prepared.close()


@pytest.mark.parametrize("split", ["session_test", "qmsum_test"])
def test_build_eval_runner_rejects_splits_without_an_adapter(split: str) -> None:
    with pytest.raises(NotImplementedError, match="not available yet"):
        build_eval_runner(runner_request(split))


def test_runner_carries_critical_facts_for_the_evaluator() -> None:
    prepared = build_eval_runner(runner_request("smoke"))
    gold = {e.example_id: e for e in SPLITS["smoke_holdout"]}
    for item in prepared.examples:
        source = gold[item.model_input.example_id]
        assert [f.fact_id for f in item.critical_facts] == [
            f.fact_id for f in source.critical_facts
        ]
    prepared.close()


# --- end to end through the shared harness -----------------------------------


def test_harness_smoke_run_succeeds_for_m1_a(tmp_path: Path) -> None:
    exit_code = harness.main(
        [
            "--candidate",
            "m1-a",
            "--smoke",
            "--split",
            "smoke",
            "--evaluator",
            "eval.tests.fake_m1_plugin:evaluate",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    result = json.loads((tmp_path / "m1-a-smoke.json").read_text(encoding="utf-8"))
    assert result["candidate_id"] == "m1-a"
    assert result["protocol_mode"] == "smoke_non_reportable"
    assert result["dataset_version"].startswith("m1-smoke-v1:")
    assert result["metrics"]["schema_valid_rate"]["mean"] == 1.0
    assert result["failures"]["invalid_schema"] == 0
    run = result["runs"][0]
    holdout_count = len(SPLITS["smoke_holdout"])
    assert run["attempted_examples"] == run["valid_outputs"] == holdout_count
    assert run["hardware"].startswith("cpu:")
    lines = Path(run["prediction_file"]).read_text(encoding="utf-8").splitlines()
    assert len(lines) == run["attempted_examples"]
    assert all(json.loads(line)["valid"] for line in lines)


def test_module_exposes_the_default_runner_symbol() -> None:
    assert harness.DEFAULT_RUNNERS["m1-a"] == "models.m1_catchup.bm25:build_eval_runner"
    assert callable(bm25.build_eval_runner)
