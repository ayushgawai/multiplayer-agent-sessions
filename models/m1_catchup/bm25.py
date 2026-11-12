"""M1-A: BM25 event ranker plus a fixed structured template.

M1-A is the transparent, deterministic, CPU-only floor under the shared
``m1-output-v1`` contract. It has no weights and no training. For each example it

1. assigns every event to at most one status category with fixed keyword rules
   (``classify_event``),
2. ranks the events inside each category with Okapi BM25 against the late
   joiner's query plus that category's cue words,
3. keeps the best few per category and emits each as an extractive claim: the
   event's own text, whitespace collapsed, citing exactly that event.

``predict`` reads only the ``M1Input`` it is given. It never reads gold labels,
reference summaries or critical facts, and it ignores ``approved_memory``
because memory is a behavioral lesson, not evidence for a session fact.

The runner plugin ``build_eval_runner`` follows ``eval.run_contract``. The seed
is accepted but unused: M1-A is deterministic, so every seed gives the same
output. Data adapters exist only for the ``smoke`` split so far; any other split
raises a clear error instead of inventing data.

A dev-only diagnostic is available with
``python -m models.m1_catchup.bm25 --dev-diagnostic``. It reads gold labels from
``dev.jsonl`` for inspection and is not an evaluation result.

Rule provenance and limits. The keyword rules are frozen as "m1-a rules v1". They
were fitted only on ``data/m1_smoke`` ``train.jsonl`` and ``dev.jsonl``, which are
synthetic template text. ``smoke_holdout`` was never used for tuning. The rules must
not be changed after looking at ``session_test`` or any other evaluation split. Each
claim cites exactly one source event, so a critical fact whose evidence spans two
events can be covered only partially. This is a known limit of the extractive design.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data.m1_smoke.loader import (
    gold_reference,
    load_split,
    to_m1_input,
    verify_manifest,
)
from data.m1_smoke.schema import LABEL_TO_CATEGORY, M1SmokeExample
from eval.contracts.m1 import (
    M1_CATEGORIES,
    M1Event,
    M1Input,
    M1Output,
    validate_m1_pair,
)
from eval.run_contract import (
    CriticalFact,
    M1EvaluationExample,
    PreparedCandidate,
    RunnerRequest,
)

CANDIDATE_ID = "m1-a"
OUTPUT_VERSION = "m1-output-v1"
MAX_CLAIMS_PER_CATEGORY = 3
MAX_CLAIM_CHARS = 240
BM25_K1 = 1.5
BM25_B = 0.75

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_FIXTURES = REPO_ROOT / "data" / "m1_smoke" / "fixtures"

# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
        "from", "had", "has", "have", "i", "if", "in", "is", "it", "its", "me",
        "my", "of", "on", "or", "so", "that", "the", "their", "then", "there",
        "this", "to", "was", "we", "were", "with", "you", "your",
    }
)  # fmt: skip

_TOKEN_RE = re.compile(r"[^\W_]+")


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric characters, drop stopwords, keep numbers."""

    tokens = _TOKEN_RE.findall(text.lower())
    return [token for token in tokens if token not in STOPWORDS]


# ---------------------------------------------------------------------------
# Okapi BM25
# ---------------------------------------------------------------------------


class BM25Index:
    """Okapi BM25 over a small list of tokenized documents. No randomness."""

    def __init__(
        self,
        documents: Sequence[Sequence[str]],
        k1: float = BM25_K1,
        b: float = BM25_B,
    ) -> None:
        self.k1 = k1
        self.b = b
        self._documents = [list(document) for document in documents]
        self._count = len(self._documents)
        lengths = [len(document) for document in self._documents]
        self._lengths = lengths
        self._average_length = sum(lengths) / self._count if self._count else 0.0
        self._term_frequencies = [Counter(document) for document in self._documents]
        document_frequency: Counter[str] = Counter()
        for frequencies in self._term_frequencies:
            document_frequency.update(frequencies.keys())
        self._idf = {
            term: math.log(1.0 + (self._count - df + 0.5) / (df + 0.5))
            for term, df in document_frequency.items()
        }

    def scores(self, query_tokens: Sequence[str]) -> list[float]:
        """BM25 score of every document. Each distinct query term counts once."""

        distinct = list(dict.fromkeys(query_tokens))
        result: list[float] = []
        pairs = zip(self._term_frequencies, self._lengths, strict=True)
        for frequencies, length in pairs:
            if self._average_length > 0:
                norm = 1.0 - self.b + self.b * length / self._average_length
            else:
                norm = 1.0
            score = 0.0
            for term in distinct:
                tf = frequencies.get(term, 0)
                if tf == 0:
                    continue
                score += self._idf[term] * tf * (self.k1 + 1.0) / (tf + self.k1 * norm)
            result.append(score)
        return result


# ---------------------------------------------------------------------------
# Status rules (fixed template)
# ---------------------------------------------------------------------------
#
# The rules were written from the starting cue lists and then adjusted by
# reading train.jsonl and dev.jsonl only. smoke_holdout.jsonl was never used to
# tune anything (contract test_policy: frozen_no_tuning). Each adjustment names
# the kind of train or dev event that motivated it.


def _patterns(*sources: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(source, re.IGNORECASE) for source in sources)


@dataclass(frozen=True)
class CategoryRule:
    """Keyword rule for one category.

    ``patterns`` are matched against the event text. If ``pattern_event_types``
    is set, the patterns apply only to those event types. Events whose type is in
    ``always_event_types`` match the category whatever their text says.
    """

    category: str
    patterns: tuple[re.Pattern[str], ...]
    pattern_event_types: frozenset[str] | None = None
    always_event_types: frozenset[str] = frozenset()


# Event types that never yield a claim.
NO_CLAIM_EVENT_TYPES = frozenset({"join", "leave"})

# Event types whose category is fixed. A rollback is a completed action even when
# its reason text says "approved" (train: a rollback "because finance has not
# approved the new tiers").
FIXED_EVENT_TYPE_CATEGORY: dict[str, str] = {"rollback": "completed"}

# Text that marks a pause, not a state worth reporting (train: "Pausing dark mode
# as requested. Token mapping is saved at 2 of 5.", which would read as progress).
NO_CLAIM_PATTERNS = _patterns(r"\bpaus(?:ed|ing)\b")

BLOCKED_PATTERNS = _patterns(
    r"\bblocked\b",
    r"\bblockers?\b",
    r"\bwaiting on\b",
    r"\bcannot\b",
    r"\bcan't\b",
    r"\bfailing\b",
    r"\bfails\b",
    r"\berror\b",
    r"\blimit\b",
    r"\bstuck\b",
)
# Only agent steps report being blocked. Without this, a tool result "Error: calc
# timed out" and a request "please raise the staging proxy limit" both matched.
BLOCKED_EVENT_TYPES = frozenset({"agent_step"})

DECISION_PATTERNS = _patterns(
    r"\bdecided\b",
    r"\bdecision\b",
    r"\bagreed\b",
    r"\bchose\b",
    r"\bapprove",
    r"\bmerged the proposals\b",
    r"\bdo not\b",  # "Use the existing serializer. Do not write a new one."
    r"\backnowledged\b",  # "Acknowledged. Ship the redesign by Friday."
    r"^skip\b",  # "Skip the quarterly growth numbers for now."
    r"\bhold the\b",  # "Finance will confirm ... Hold the rewrite until then."
    r"\bownership of\b.*\bmoves\b",  # handoff "Ownership of the billing page moves ..."
)
# Arbitration picks a winner and an interrupt stops work: both are decisions.
DECISION_EVENT_TYPES = frozenset({"arbitration", "interrupt"})

PENDING_ACTION_PATTERNS = _patterns(
    r"\bwill\b",
    r"\bmust\b",  # "Someone must update the changelog before the release."
    r",\s*please\b",  # "Chen, please send the draft to legal tomorrow."
    r"\bnext step\b",
    r"\bto do\b",
    r"\btodo\b",
    r"\bneeds to\b",
    r"\bfollow up\b",
    r"\bassign",
    r"\bby end of\b",
)
# Assignments are instructions. A handoff such as "Handing over to X: ..., please
# write tests" is neutral in train and dev, so it must not match ", please".
PENDING_ACTION_EVENT_TYPES = frozenset({"instruction"})

IN_PROGRESS_PATTERNS = _patterns(
    r"\bin progress\b",
    r"\brunning\b",
    r"\bstarted\b",
    r"\bworking on\b",
    r"\bongoing\b",
    r"\b\d+ of \d+\b",
    r"\bwriting\b",  # "Writing 9 tests for pdf_export: ..."
    r"\bhalted\b",  # "Halted. Draft saved ... about 80 percent done."
    r"\b\d+ percent\b",
)

COMPLETED_PATTERNS = _patterns(
    r"\bdone\b",
    r"\bcompleted\b",
    r"\bfinished\b",
    # "4 passed, 1 failed: ..." is a neutral tool result, so passed needs no failure.
    r"^(?!.*\bfail).*\bpassed\b",
    r"\bmerged\b",
    r"\bresolved\b",
    r"\bshipped\b",
    # "Visual regression: 13 snapshots updated, 0 failures."
    r"\b0 failures\b",
    # Past-tense work reports: "Created ...", "Built the revenue table ...".
    r"^(?:created|switched|updated|built|replaced|applied|added|removed)\b",
)
# Document edits are completed work (train: 7 of 8 doc_update events).
COMPLETED_EVENT_TYPES = frozenset({"doc_update"})

# Priority order when several categories match: first rule wins. "fixed" was
# dropped from the completed cues: "Proposal A: ... with a fixed 2 s backoff."
# is neutral in train and dev.
CATEGORY_RULES: tuple[CategoryRule, ...] = (
    CategoryRule("blocked", BLOCKED_PATTERNS, pattern_event_types=BLOCKED_EVENT_TYPES),
    CategoryRule(
        "decisions", DECISION_PATTERNS, always_event_types=DECISION_EVENT_TYPES
    ),
    CategoryRule(
        "pending_actions",
        PENDING_ACTION_PATTERNS,
        pattern_event_types=PENDING_ACTION_EVENT_TYPES,
    ),
    CategoryRule("in_progress", IN_PROGRESS_PATTERNS),
    CategoryRule(
        "completed", COMPLETED_PATTERNS, always_event_types=COMPLETED_EVENT_TYPES
    ),
)

# Cue words added to the BM25 query for each category.
CATEGORY_CUE_WORDS: dict[str, tuple[str, ...]] = {
    "blocked": (
        "blocked", "blocker", "waiting", "cannot", "failing", "error", "limit", "stuck",
    ),
    "decisions": (
        "decided", "decision", "agreed", "chose", "approved", "selected", "stop",
    ),
    "pending_actions": (
        "will", "must", "please", "next", "todo", "needs", "follow", "assign",
    ),
    "in_progress": (
        "progress", "running", "started", "working", "writing", "ongoing",
    ),
    "completed": (
        "done", "completed", "finished", "passed", "merged", "created", "updated",
    ),
}  # fmt: skip


def classify_event(event: M1Event) -> str | None:
    """Return the status category of one event, or None if it yields no claim."""

    if event.event_type in NO_CLAIM_EVENT_TYPES:
        return None
    fixed = FIXED_EVENT_TYPE_CATEGORY.get(event.event_type)
    if fixed is not None:
        return fixed
    text = event.text
    if any(pattern.search(text) for pattern in NO_CLAIM_PATTERNS):
        return None
    for rule in CATEGORY_RULES:
        if event.event_type in rule.always_event_types:
            return rule.category
        restricted = rule.pattern_event_types
        if restricted is not None and event.event_type not in restricted:
            continue
        if any(pattern.search(text) for pattern in rule.patterns):
            return rule.category
    return None


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def truncate_at_word(text: str, limit: int = MAX_CLAIM_CHARS) -> str:
    """Cut to at most ``limit`` characters at a word boundary when possible."""

    if len(text) <= limit:
        return text
    cut = text[:limit]
    if text[limit] != " ":
        boundary = cut.rfind(" ")
        if boundary > 0:
            cut = cut[:boundary]
    return cut.rstrip()


def normalize_claim_text(text: str) -> str:
    """Normalize claim text the way ``validate_m1_pair`` does to find duplicates."""

    return " ".join(text.split()).casefold()


def predict(model_input: M1Input) -> dict[str, Any]:
    """Build an ``m1-output-v1`` dict for one example from its own events only.

    The contract rejects duplicate claim text, so a claim whose normalized text
    equals one already chosen in any category is skipped. Categories are
    visited in rule priority order, then by BM25 rank, so the first one wins. A
    skipped duplicate does not use up a ``MAX_CLAIMS_PER_CATEGORY`` slot.
    """

    events = model_input.events
    index = BM25Index([tokenize(event.text) for event in events])
    query_tokens = tokenize(model_input.query)

    candidates: dict[str, list[int]] = {category: [] for category in M1_CATEGORIES}
    for position, event in enumerate(events):
        category = classify_event(event)
        if category is not None:
            candidates[category].append(position)

    claim_texts = {
        position: truncate_at_word(collapse_whitespace(event.text))
        for position, event in enumerate(events)
    }
    seen: set[str] = set()
    selected: dict[str, list[int]] = {category: [] for category in M1_CATEGORIES}
    for rule in CATEGORY_RULES:
        category = rule.category
        positions = candidates[category]
        if not positions:
            continue
        scores = index.scores(query_tokens + list(CATEGORY_CUE_WORDS[category]))
        ranked = sorted(positions, key=lambda p: (-scores[p], -events[p].sequence))
        for position in ranked:
            if len(selected[category]) == MAX_CLAIMS_PER_CATEGORY:
                break
            normalized = normalize_claim_text(claim_texts[position])
            if normalized in seen:
                continue
            seen.add(normalized)
            selected[category].append(position)

    output: dict[str, Any] = {
        "schema_version": OUTPUT_VERSION,
        "example_id": model_input.example_id,
        "candidate_id": CANDIDATE_ID,
    }
    for category in M1_CATEGORIES:
        kept = sorted(selected[category], key=lambda p: events[p].sequence)
        output[category] = [
            {
                "text": claim_texts[p],
                "source_event_ids": [events[p].event_id],
            }
            for p in kept
        ]

    parsed = M1Output.model_validate(output)
    validate_m1_pair(model_input, parsed)
    return output


# ---------------------------------------------------------------------------
# Runner plugin (eval.run_contract)
# ---------------------------------------------------------------------------


class BM25PreparedCandidate:
    """Prepared M1-A candidate. Deterministic, so the seed has no effect."""

    def __init__(
        self,
        dataset_version: str,
        examples: Sequence[M1EvaluationExample],
    ) -> None:
        self.dataset_version = dataset_version
        self.hardware = "cpu:" + platform.machine()
        self.examples: Sequence[M1EvaluationExample] = list(examples)

    def predict(self, model_input: M1Input) -> Mapping[str, Any]:
        return predict(model_input)

    def peak_vram_mb(self) -> float:
        return 0.0

    def close(self) -> None:
        return None


def _evaluation_example(example: M1SmokeExample) -> M1EvaluationExample:
    return M1EvaluationExample(
        model_input=M1Input.model_validate(to_m1_input(example)),
        reference=gold_reference(example),
        critical_facts=[
            CriticalFact(
                fact_id=fact.fact_id,
                category=fact.category,
                text=fact.text,
                evidence_event_ids=list(fact.evidence_event_ids),
            )
            for fact in example.critical_facts
        ],
        metadata={"session_id": example.session_id},
    )


def build_eval_runner(request: RunnerRequest) -> PreparedCandidate:
    """Harness entry point. Only the non-reportable ``smoke`` split is supported."""

    if request.split != "smoke":
        raise NotImplementedError(
            f"the M1-A data adapter for split {request.split!r} is not available yet; "
            "only the 'smoke' split is supported"
        )
    verify_manifest(request.dataset_path)
    manifest_path = request.dataset_path / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    holdout_sha = manifest["splits"]["smoke_holdout"]["sha256"]
    dataset_version = f"m1-smoke-v1:{holdout_sha[:12]}"
    smoke = load_split(request.dataset_path / "smoke_holdout.jsonl")
    examples = [_evaluation_example(example) for example in smoke]
    if request.max_examples is not None:
        examples = examples[: request.max_examples]
    return BM25PreparedCandidate(dataset_version, examples)


# ---------------------------------------------------------------------------
# Dev-only diagnostic
# ---------------------------------------------------------------------------


def _dev_diagnostic(fixtures_dir: Path) -> int:
    verify_manifest(fixtures_dir)
    dev = load_split(fixtures_dir / "dev.jsonl")
    print("dev diagnostic, not an evaluation result")
    print(f"split: dev ({len(dev)} examples)")
    print("gold is read here only, never inside predict()")
    header = (
        f"{'example':<14}{'events':>7}  "
        + " ".join(f"{name[:9]:>9}" for name in M1_CATEGORIES)
        + f"  {'fact_cov':>12}  {'cat_agree':>11}  {'extra':>5}"
    )
    print(header)
    total_covered = total_facts = total_agree = total_labeled = total_extra = 0
    for example in dev:
        model_input = M1Input.model_validate(to_m1_input(example))
        output = predict(model_input)
        cited = {
            event_id
            for category in M1_CATEGORIES
            for claim in output[category]
            for event_id in claim["source_event_ids"]
        }
        covered = sum(
            all(event_id in cited for event_id in fact.evidence_event_ids)
            for fact in example.critical_facts
        )
        agree = labeled = extra = 0
        for event in model_input.events:
            predicted = classify_event(event)
            label = example.event_labels.get(event.event_id)
            if label is None:
                extra += predicted is not None
            else:
                labeled += 1
                agree += predicted == LABEL_TO_CATEGORY[label]
        counts = " ".join(f"{len(output[category]):>9}" for category in M1_CATEGORIES)
        facts = len(example.critical_facts)
        cov_text = f"{covered}/{facts}"
        agree_text = f"{agree}/{labeled}"
        print(
            f"{example.example_id:<14}{len(model_input.events):>7}  {counts}"
            f"  {cov_text:>12}  {agree_text:>11}  {extra:>5}"
        )
        total_covered += covered
        total_facts += facts
        total_agree += agree
        total_labeled += labeled
        total_extra += extra
    blank = " ".join(f"{'':>9}" for _ in M1_CATEGORIES)
    cov_total = f"{total_covered}/{total_facts}"
    agree_total = f"{total_agree}/{total_labeled}"
    print(
        f"{'all':<14}{'':>7}  {blank}  {cov_total:>12}  {agree_total:>11}"
        f"  {total_extra:>5}"
    )
    print("fact_cov: gold critical facts whose evidence ids are all cited by a claim")
    print("cat_agree: labeled events whose template category equals the gold label")
    print("extra: unlabeled events the template still assigned a category to")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dev-diagnostic",
        action="store_true",
        help="inspect the template on dev.jsonl (not an evaluation result)",
    )
    args = parser.parse_args(argv)
    if args.dev_diagnostic:
        return _dev_diagnostic(SMOKE_FIXTURES)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
