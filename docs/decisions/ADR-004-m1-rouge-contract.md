# ADR-004: M1 ROUGE scoring contract

- Status: Proposed (implementation complete; independent review pending)
- Date: 2026-10-22
- Owner: evaluation owner. Reviewer: one independent teammate

## Context

The four M1 candidates must be compared under one evaluation contract. Their configuration
files name `rouge_l`, but the repository did not define the library call, stemming behavior,
aggregation rule, scale, or treatment of empty outputs. Different defaults would make two
runs with the same predictions report different values.

This ADR locks only ROUGE. Grounding, unsupported claims, attribution, BERTScore, latency,
VRAM, confidence intervals, and the candidate-selection rule remain part of DAT-55.

## Decision

1. Use `rouge-score==0.1.2`, already pinned in `requirements.txt`.
2. Compute `rouge1`, `rouge2`, and `rougeL` with
   `rouge_scorer.RougeScorer(..., use_stemmer=True)`.
3. Call `score(reference, prediction)` for each aligned record. Do not concatenate the corpus.
4. For each metric, macro-average per-record precision, recall, and F1 with equal record
   weight. The primary `rouge_l` value is the macro-average ROUGE-L F1.
5. Report values on a 0 to 100 percentage scale without rounding in the metric layer.
6. Preserve per-record component scores for error analysis.
7. An empty prediction is a valid model output and receives the library-defined score. A
   reference must contain non-whitespace text because an empty gold summary cannot provide a
   meaningful evaluation target. Empty datasets, unequal collection lengths, and non-string
   values are rejected.
8. Use `rougeL`, not `rougeLsum`; newline-based sentence splitting is therefore not part of
   this contract.
9. Record `library: rouge-score`, its installed version, and the convention identifier with
   every result. The harness must also record each dataset example's stable ID beside its
   per-record scores; list position alone is not an auditable identity.
10. Project structured M1 output to scoring text before calling this metric. Process categories
    in this fixed order: `completed`, `in_progress`, `blocked`, `decisions`, then
    `pending_actions`. Within each category, retain item order and append only each item's
    normalized `text`, separated by a newline. Empty categories contribute no text. Exclude
    category names, JSON syntax, and `source_event_ids`; those IDs are evaluated by the
    grounding and attribution checks. Apply the identical projection to predictions and gold
    references. DAT-55 owns this serializer and its contract tests.
11. Treat ROUGE as a supporting similarity metric, not a standalone winner-selection rule.
    DAT-55 must combine it with critical-fact recall, unsupported-claim rate, attribution or
    owner accuracy, status consistency, BERTScore-F1, latency, peak VRAM, and the approved
    human-quality measure. A candidate cannot win solely through higher ROUGE when its
    unsupported-claim performance worsens.

The implementation is `eval.metrics.summarization.compute_rouge_metrics`, and its convention
identifier is `m1_rouge_macro_v1`.

## Consequences

- All M1 candidates can expose the same top-level `rouge_1`, `rouge_2`, and `rouge_l` keys.
- Per-record results remain traceable to stable dataset IDs in the harness while this metric
  stays reusable and independent of any one dataset schema.
- ROUGE measures the human-readable catch-up content, while source evidence and structured
  correctness are measured separately instead of being accidentally rewarded as text overlap.
- The 28.2 QMSum reference floor must be compared on the same 0 to 100 scale and only after
  confirming that its published preprocessing and ROUGE convention are compatible.
- A future change to stemming, aggregation, scale, or ROUGE-L variant requires a new
  convention identifier and an ADR revision.
