"""CPU-only checks for the m1-b/m1-c/m1-d paths. No torch, no model downloads."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from eval.contracts.m1 import M1Event, M1Input, qmsum_row_to_m1_input
from models.common.checkpointing import _local_path
from models.m1_catchup import candidates as c
from models.m1_catchup.qlora import AUTO_CLASSES, build_example, missing_target_modules

ROW = {
    "id": "qmsum_train_7_s0",
    "query": "What did the team decide about the budget?",
    "context_spans": [
        "Alice: Hello everyone, welcome.",
        "Bob: The budget for the marketing campaign was cut by ten percent.",
        "Carol: The marketing budget cut means fewer campaign events this quarter.",
        "Dan: Lunch is at noon.",
    ],
    "reference_summary": (
        "The marketing campaign budget was cut by ten percent. "
        "Fewer campaign events will happen this quarter."
    ),
}


class FakeTokenizer:
    """Whitespace tokenizer with a trivial chat template."""

    eos_token = "<eos>"

    def __call__(self, text: str, add_special_tokens: bool = False) -> SimpleNamespace:
        return SimpleNamespace(input_ids=text.split())

    def apply_chat_template(self, messages, tokenize, add_generation_prompt, **kwargs):  # noqa: ANN001
        text = "".join(f"<{m['role']}> {m['content']} </{m['role']}> " for m in messages)
        return text + ("<assistant> " if add_generation_prompt else "")


def test_configs_load_with_explicit_trainers() -> None:
    trainers = {cid: c.load_config(cid)["trainer"] for cid in c.LEARNED_CANDIDATES}
    assert trainers == {
        "m1-b": "encoder_selector",
        "m1-c": "causal_lm_qlora",
        "m1-d": "conditional_generation_qlora",
    }
    assert set(AUTO_CLASSES) == {"causal_lm_qlora", "conditional_generation_qlora"}
    assert c.checkpoint_uri(c.load_config("m1-c"), 13) == "file://./checkpoints/m1-c/seed-13/"
    with pytest.raises(ValueError):
        c.load_config("m1-a")


def test_relative_file_uri_stays_relative() -> None:
    assert _local_path("file://./checkpoints/m1-b/") == Path("checkpoints/m1-b")
    assert _local_path("file:///tmp/x") == Path("/tmp/x")


def test_weak_relevance_rule() -> None:
    texts = ROW["context_spans"]
    assert c.weak_relevance_labels(texts, ROW["reference_summary"]) == [0, 1, 1, 0]
    # Below WEAK_MIN_OVERLAP nothing is positive, even in the top k.
    assert c.weak_relevance_labels(["budget talk", "lunch"], "budget review") == [0, 0]


def test_weak_target_is_valid_output() -> None:
    model_input = qmsum_row_to_m1_input(ROW)
    target = c.weak_target(model_input.events, ROW["reference_summary"])
    assert [claim["source_event_ids"] for claim in target["completed"]] == [
        ["qmsum_train_7_s0:span:0001"],
        ["qmsum_train_7_s0:span:0002"],
    ]
    assert all(not target[k] for k in ("in_progress", "blocked", "decisions", "pending_actions"))
    output = c.parse_generation(c.target_text(target), ROW["id"], "m1-c")
    assert c.validation_error(output, model_input) is None


def test_fit_events_keeps_prefix_within_budget() -> None:
    events = qmsum_row_to_m1_input(ROW).events
    words = lambda text: len(text.split())  # noqa: E731
    assert len(c.fit_events(events, words, budget=10)) == 1
    assert len(c.fit_events(events, words, budget=26)) == 2
    assert len(c.fit_events(events, words, budget=10_000)) == 4


def test_build_example_masks_prompt_and_targets_json() -> None:
    tok = FakeTokenizer()
    example = build_example(tok, ROW, max_len=4096)
    assert example is not None
    answer = [t for t, label in zip(example["input_ids"], example["labels"]) if label != -100]
    assert answer[-1] == "</assistant>"
    target = json.loads(" ".join(answer[:-1]))
    assert len(target["completed"]) == 2
    assert example["labels"][0] == -100
    assert build_example(tok, ROW, max_len=20) is None  # prompt alone fills the window


@pytest.mark.parametrize(
    ("text", "valid"),
    [
        ('{"completed":[{"text":"Budget cut.","source_event_ids":["E1"]}]}', True),
        ('```json\n{"decisions":[{"text":"Cut it.","source_event_ids":["E1"]}]}\n```', True),
        ('<think>hmm {"x":1}</think>{"blocked":[]} trailing', True),
        ("The budget was cut.", False),
        ('{"completed":[{"text":"Budget cut.","source_event_ids":["E9"]}]}', False),
        ('{"completed":[{"text":"Budget cut.","source_event_ids":[]}]}', False),
    ],
)
def test_parse_generation(text: str, valid: bool) -> None:
    model_input = M1Input(
        example_id="ex-1",
        session_id="s-1",
        query="q",
        events=[M1Event(event_id="E1", sequence=0, event_type="doc_update", text="Budget cut.")],
    )
    output = c.parse_generation(text, "ex-1", "m1-d")
    assert (c.validation_error(output, model_input) is None) is valid


def test_missing_target_modules_reports_names() -> None:
    names = ["model.language_model.layers.0.linear_attn.in_proj_qkv", "model.visual.blocks.0.qkv"]
    assert missing_target_modules(names, ["in_proj_qkv", "q_proj"]) == ["q_proj"]


@pytest.mark.parametrize("module", ["modernbert", "phi_qlora", "qwen_qlora"])
def test_harness_runner_entry_points_exist(module: str) -> None:
    loaded = importlib.import_module(f"models.m1_catchup.{module}")
    assert callable(loaded.build_eval_runner)


def test_m1b_fills_m1a_template_from_scores() -> None:
    pytest.importorskip("models.m1_catchup.bm25", reason="M1-A template (PR #26) not on this branch")
    from models.m1_catchup.modernbert import fill_template

    model_input = qmsum_row_to_m1_input(ROW)
    output = fill_template(model_input, [0.1, 0.9, 0.8, 0.2])
    assert c.validation_error(output, model_input) is None
    cited = [claim["source_event_ids"][0][-4:] for claim in output["completed"]]
    assert cited == ["0001", "0002", "0003"]  # top 3 by score, emitted in event order
