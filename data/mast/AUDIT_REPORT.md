# MAST data audit and evaluation-subset options

Linear: DAT-30 (MAST 06). Owner: Naman Chheda.

**Status: recommendation for team review. Nothing here is a final decision.** This report does not choose or freeze an evaluation set. `eval_manifest.DRAFT.json` in this folder is a draft of one option (Option A) so the team has something concrete to look at. It is not frozen and must not be treated as the evaluation set until Pramod (owner of `eval/` and `models/baseline_mast/`) and the team sign off.

Every number below was recomputed from the raw files for this report, not copied from `DATA_DICTIONARY.md` or `TAXONOMY.md`:

- `data/mast/hf/MAD_full_dataset.json` (1642 records)
- `data/mast/hf/MAD_human_labelled_dataset.json` (19 records, 316 annotation entries)

Both were loaded with `json.load(open(path, encoding="utf-8"))`. No metrics comparing a judge to human labels are computed here; per CONTEXT.md those belong in `eval/metrics/`.

---

## 1. Missing and invalid labels

### `MAD_full_dataset.json`

| Nulls per record (out of 14 codes) | Records |
|---|---|
| 0 | 1638 |
| 1 to 13 (partial) | 0 |
| 14 (complete) | 4 |

There are no partially null records. The 4 completely null records:

| List index | trace.key | trace_id | mas_name / llm_name / benchmark_name | trajectory length (chars) |
|---|---|---|---|---|
| 1446 | ChatDev_ProgramDev-v2_CodeLlama | 4 | ChatDev / CodeLlama / ProgramDev-v2 | 819,034 |
| 1514 | ChatDev_ProgramDev-v2_CodeLlama | 72 | ChatDev / CodeLlama / ProgramDev-v2 | 599,037 |
| 1515 | ChatDev_ProgramDev-v2_CodeLlama | 73 | ChatDev / CodeLlama / ProgramDev-v2 | 564,931 |
| 1523 | ChatDev_ProgramDev-v2_CodeLlama | 81 | ChatDev / CodeLlama / ProgramDev-v2 | 837,072 |

Across all 1642 x 14 = 22,988 label slots: 17,791 are `0`, 5,141 are `1`, 56 are `null`. No other values occur.

### `MAD_human_labelled_dataset.json`

Of 948 annotator values (316 entries x 3 annotators), 946 are booleans and 2 are not:

| trace_id | round | annotator | failure mode | value |
|---|---|---|---|---|
| 18 | Generlazability | annotator_3 | 3.2 No or Incomplete Verification | `NaN` (float) |
| 18 | Generlazability | annotator_3 | 3.3 Incorrect Verification | `NaN` (float) |

There are no `null` annotator values and no missing annotator keys. (The raw file contains 13 `null` tokens, but all of them sit inside `trace` strings: 2 in trace_id 0, 5 in trace_id 5, 6 in trace_id 11.)

---

## 2. Label frequencies

### 2.1 `MAD_full_dataset.json` (LLM-judge labels, 1642 records)

| Code | `1` | `0` | `null` |
|---|---|---|---|
| 1.1 | 591 | 1047 | 4 |
| 1.2 | 91 | 1547 | 4 |
| 1.3 | 664 | 974 | 4 |
| 1.4 | 117 | 1521 | 4 |
| 1.5 | 436 | 1202 | 4 |
| 2.1 | 80 | 1558 | 4 |
| 2.2 | 265 | 1373 | 4 |
| 2.3 | 353 | 1285 | 4 |
| 2.4 | 24 | 1614 | 4 |
| 2.5 | 370 | 1268 | 4 |
| 2.6 | 610 | 1028 | 4 |
| 3.1 | 274 | 1364 | 4 |
| 3.2 | 608 | 1030 | 4 |
| 3.3 | 658 | 980 | 4 |

### 2.2 `MAD_human_labelled_dataset.json`, majority vote per group

**Vote rule.** For each record and mode: label `1` if at least 2 annotators marked True, `0` if at least 2 marked False. `NaN` counts as missing. If no 2 valid annotators agreed, the label would be `null`; that never happened. Every label where the annotators were **not** all in agreement is flagged in the "Not unanimous" column, with the raw votes as (annotator_1, annotator_2, annotator_3).

Codes and titles in Rounds 1 to 3 are the **old taxonomy's** codes, exactly as stored in the file. They do not mean the same thing as the current 14 codes (see section 4b).

**Round 1** (5 records: trace_id 0 to 4; 18 modes; 90 labels, 90 unanimous)

| Code | Title (as stored) | Majority 1 | Majority 0 | Not unanimous |
|---|---|---|---|---|
| 1.1 | Poor task constraint compliance | 0 | 5 | none |
| 1.2 | Inconsistency between reasoning and action | 2 | 3 | none |
| 1.3 | Undetected conversation ambiguities and contradictions | 0 | 5 | none |
| 1.4 | Fail to elicit clarification | 0 | 5 | none |
| 1.5 | Unaware of stopping conditions | 5 | 0 | none |
| 2.1 | Unbatched repetitive execution | 0 | 5 | none |
| 2.2 | Step repetition | 2 | 3 | none |
| 2.3 | Backtracking interruption | 0 | 5 | none |
| 2.4 | Conversation reset | 2 | 3 | none |
| 2.5 | Derailment from task | 2 | 3 | none |
| 2.6 | Disobey role specification | 2 | 3 | none |
| 3.1 | Disagreement induced inaction | 0 | 5 | none |
| 3.2 | Withholding relevant information | 0 | 5 | none |
| 3.3 | Ignoring suggestions from agents | 3 | 2 | none |
| 3.4 | Waiting for known information | 2 | 3 | none |
| 4.1 | Ill specified termination condition leading to premature termination | 0 | 5 | none |
| 4.3 | Lack of critical verification | 2 | 3 | none |
| 4.2 | Lack of result verification | 2 | 3 | none |

**Round 2** (5 records: trace_id 5 to 9; 17 modes; 85 labels, 85 unanimous)

| Code | Title (as stored) | Majority 1 | Majority 0 | Not unanimous |
|---|---|---|---|---|
| 1.1 | Poor task constraint compliance | 0 | 5 | none |
| 1.2 | Inconsistency between reasoning and action | 2 | 3 | none |
| 1.3 | Unaware of stopping conditions | 0 | 5 | none |
| 1.4 | Unbatched repetitive execution | 0 | 5 | none |
| 1.5 | Step repetition | 0 | 5 | none |
| 1.6 | Backtracking interruption | 2 | 3 | none |
| 1.7 | Disobey role specification | 0 | 5 | none |
| 2.1 | Conversation reset | 0 | 5 | none |
| 2.2 | Fail to elicit clarification | 0 | 5 | none |
| 2.3 | Derailment from task | 0 | 5 | none |
| 2.4 | Undetected conversation ambiguities and contradictions | 0 | 5 | none |
| 2.5 | Disagreement induced inaction | 0 | 5 | none |
| 2.6 | Withholding relevant information | 0 | 5 | none |
| 2.7 | Ignoring suggestions from agents | 0 | 5 | none |
| 3.1 | Ill specified termination condition leading to premature termination | 0 | 5 | none |
| 3.2 | Lack of critical verification | 0 | 5 | none |
| 3.3 | Lack of result verification | 3 | 2 | none |

**Round 3** (5 records: trace_id 10 to 14; 17 modes; 85 labels, 77 unanimous, 8 split 2-1)

| Code | Title (as stored) | Majority 1 | Majority 0 | Not unanimous |
|---|---|---|---|---|
| 1.1 | Poor task constraint compliance | 3 | 2 | none |
| 1.2 | Inconsistency between reasoning and action | 0 | 5 | none |
| 1.3 | Unaware of stopping conditions | 0 | 5 | none |
| 1.4 | Unbatched repetitive execution | 0 | 5 | none |
| 1.5 | Step repetition | 0 | 5 | tid 10, 11, 12: (T, F, F) |
| 1.6 | Backtracking interruption | 0 | 5 | none |
| 1.7 | Disobey role specification | 0 | 5 | none |
| 2.1 | Conversation reset | 0 | 5 | none |
| 2.2 | Fail to elicit clarification | 5 | 0 | tid 13, 14: (F, T, T) |
| 2.3 | Derailment from task | 3 | 2 | none |
| 2.4 | Undetected conversation ambiguities and contradictions | 0 | 5 | none |
| 2.5 | Disagreement induced inaction | 0 | 5 | none |
| 2.6 | Withholding relevant information | 0 | 5 | none |
| 2.7 | Ignoring suggestions from agents | 0 | 5 | tid 10, 11, 12: (T, F, F) |
| 3.1 | Ill specified termination condition leading to premature termination | 0 | 5 | none |
| 3.2 | Lack of critical verification | 2 | 3 | none |
| 3.3 | Lack of result verification | 3 | 2 | none |

**Generlazability** (4 records: trace_id 15 to 18; current 14 modes; 56 labels, 48 unanimous, 6 split 2-1, 2 decided by the 2 non-missing annotators)

| Code | Title (as stored) | Majority 1 | Majority 0 | Not unanimous |
|---|---|---|---|---|
| 1.1 | Disobey Task Specification | 3 | 1 | tid 15, 16, 17: (T, F, T) |
| 1.2 | Disobey Role Specification | 0 | 4 | none |
| 1.3 | Step Repetition | 0 | 4 | none |
| 1.4 | Loss of Conversation History | 0 | 4 | none |
| 1.5 | Unaware of Termination Conditions | 0 | 4 | none |
| 2.1 | Conversation reset | 0 | 4 | none |
| 2.2 | Fail to ask for clarification | 0 | 4 | none |
| 2.3 | Task derailment | 0 | 4 | none |
| 2.4 | Information Witholding | 0 | 4 | none |
| 2.5 | Ignored Other Agents' Input | 0 | 4 | none |
| 2.6 | Reasoning-Action Mismatch | 0 | 4 | none |
| 3.1 | Premature Termination | 0 | 4 | none |
| 3.2 | No or Incomplete Verification | 3 | 1 | tid 15, 16, 17: (T, F, T); tid 18: (F, F, NaN) |
| 3.3 | Incorrect Verification | 3 | 1 | tid 18: (F, F, NaN) |

### 2.3 Warning: identical label matrices on different traces

While computing the tables above, a pattern showed up that the team needs to see before using any of these labels. Within every group, several records with **different traces** have **byte-identical 3-annotator label matrices** (every annotator's value on every mode is the same):

| Group | Records sharing one identical label matrix | Records sharing a second identical label matrix |
|---|---|---|
| Round 1 | trace_id 0, 1, 2 (AppWorld, HyperAgent, AG2) | trace_id 3, 4 (ChatDev, MetaGPT) |
| Round 2 | trace_id 5, 6, 7 (AppWorld, HyperAgent, AG2) | trace_id 8, 9 (ChatDev, MetaGPT) |
| Round 3 | trace_id 10, 11, 12 (HyperAgent, AppWorld, AG2) | trace_id 13, 14 (ChatDev, MetaGPT) |
| Generlazability | trace_id 15, 16, 17 (ChatDev, MetaGPT, row with mas_name "GAIA") | trace_id 18 alone |

The traces in each set are different (for example, 15 and 16 are ChatDev and MetaGPT runs on MMLU). The file holds **8 distinct label matrices** across 19 records.

Also:

- In Round 1 and Round 2, annotator_1, annotator_2, and annotator_3 agree with each other on every mode of every record (175 of 175 labels unanimous). That is unusual for an inter-annotator agreement study.
- trace_id 3 (Round 1) and trace_id 8 (Round 2) have byte-identical traces. annotator_1 marks 9 modes True on trace_id 3 and 2 modes True on trace_id 8. The two rounds use different taxonomies, so the counts are not directly comparable.

This report does not claim a cause. The pattern (the first 3 records of a group share one matrix and the rest share another) looks like labels were copied or filled down when the file was built, rather than labelled per trace. **Before either option is used, someone should compare these labels against the MAST authors' original annotation files** (upstream repository linked in `data/mast/hf/README.md`). If the pattern is an export artifact, the "4 records" of Option A are really 2 independent label matrices, and the "15 records" of Option B are really 6.

---

## 3. Multi-label distribution

### `MAD_full_dataset.json`

Number of codes equal to `1` per record. `null` is excluded, not counted as `0`. The 4 completely null records have no defined count, so they are left out: 1638 records counted.

| Codes = 1 | Records |
|---|---|
| 0 | 401 |
| 1 | 189 |
| 2 | 237 |
| 3 | 208 |
| 4 | 153 |
| 5 | 133 |
| 6 | 85 |
| 7 | 76 |
| 8 | 45 |
| 9 | 30 |
| 10 | 24 |
| 11 | 29 |
| 12 | 20 |
| 13 | 6 |
| 14 | 2 |
| **Total** | **1638** |

Mean 3.14, median 2, max 14. 1237 of 1638 records (75.5%) have at least one failure, and 1048 (64.0%) have two or more.

### `MAD_human_labelled_dataset.json` (majority vote from section 2.2)

Counts in Rounds 1 to 3 are out of that round's 18 or 17 old-taxonomy modes, not the current 14.

| Group | Modes | Distribution (positives: records) | Per record (trace_id: positives) |
|---|---|---|---|
| Round 1 | 18 | 2: 3, 9: 2 | 0: 2, 1: 2, 2: 2, 3: 9, 4: 9 |
| Round 2 | 17 | 1: 3, 2: 2 | 5: 1, 6: 1, 7: 1, 8: 2, 9: 2 |
| Round 3 | 17 | 2: 2, 4: 3 | 10: 4, 11: 4, 12: 4, 13: 2, 14: 2 |
| Generlazability | 14 | 0: 1, 3: 3 | 15: 3, 16: 3, 17: 3, 18: 0 |

The repeated per-record counts inside each group follow directly from the identical label matrices in section 2.3.

---

## 4. Evaluation subset options (presented, not decided)

Targets as given in the DAT-30 brief: accuracy 0.94, precision 0.833, recall 0.77, F1 0.80, Cohen's kappa 0.77. `docs/build-plan.html` (line 683) states the accuracy 94% and kappa 0.77 targets ("against expert annotation on the released MAST-Data traces", tolerance 2 percentage points); the precision, recall, and F1 figures do not appear in `docs/`.

A fact that applies to both options: of the 19 human-labelled traces, only 3 are exact string matches of a `trace.trajectory` in `MAD_full_dataset.json` (trace_id 0, 5, and 11, all AppWorld). None of the 4 Generlazability traces match. So the full file has no published LLM-judge label for any Option A trace; the judge has to be run on them. (Only exact string equality was checked; a trace stored with different formatting would not be found.)

### 4a. Option A: the 4 Generlazability records only

What it is: trace_id 15, 16, 17, 18, labelled with the current 14-mode taxonomy, so no crosswalk is needed. Drafted in `eval_manifest.DRAFT.json`.

**n = 4 is too small for a statistically meaningful accuracy, precision, recall, F1, or kappa estimate against the targets above.** Specifically:

- 4 traces x 14 codes = 56 code-level labels: 9 positive, 47 negative.
- All 9 positives are on 3 codes: 1.1 (3), 3.2 (3), 3.3 (3). The other 11 codes have **zero** positive labels, so recall and F1 per mode are undefined for 11 of the 14 modes. The build plan asks for per-mode F1 across all 14 modes.
- Even treating all 56 labels as independent (they are not: 14 labels come from each trace), an observed accuracy of exactly 0.94 would have a 95% Wilson interval of about [0.845, 0.978]. That reaches 0.095 below and 0.038 above 0.94, against a tolerance of 0.02 either way. Counting traces (n = 4), the interval is [0.452, 0.997].
- Recall rests on 9 positives. An observed recall of 0.77 on 9 positives has a 95% Wilson interval of about [0.445, 0.933].
- One wrong label moves accuracy by 1/56 = 0.018, close to the whole tolerance.
- Per section 2.3, trace_id 15, 16, 17 share one label matrix, so there may be only 2 independent sets of human labels.
- Data issues carried into the draft as stored: trace_id 17 and 18 have mas_name and benchmark_name swapped in the source; trace_id 18 has 2 NaN annotator values. For 3.2 and 3.3 on trace_id 18, the other two annotators both said False, so the majority label is 0.

### 4b. Option B: add the 15 Round 1 to 3 records through a crosswalk

No crosswalk is proposed here. The table below only sorts the old mode titles by how much judgment a crosswalk would need. The sorting uses the definition text the annotators were shown, stored in each `failure mode` string, compared with the Generlazability (14-mode) entries in the same file:

- **1:1**: the old definition text is identical to, or fully contained in, the definition text of exactly one current code.
- **Ambiguous**: there is one obvious candidate, but the text or labelling rules differ in a way that could change labels.
- **No clean mapping**: the old definition matches no current code.

| Old title (as stored) | Round 1 code | Round 2 and 3 code | Candidate current code | Category | Basis |
|---|---|---|---|---|---|
| Poor task constraint compliance | 1.1 | 1.1 | 1.1 Disobey Task Specification | 1:1 | Identical definition text; title renamed |
| Disobey role specification | 2.6 | 1.7 | 1.2 Disobey Role Specification | 1:1 | Identical definition text |
| Step repetition | 2.2 | 1.5 | 1.3 Step Repetition | 1:1 | Identical definition text |
| Backtracking interruption | 2.3 | 1.6 | 1.4 Loss of Conversation History | 1:1 | Identical definition text; title renamed |
| Unaware of stopping conditions | 1.5 | 1.3 | 1.5 Unaware of Termination Conditions | 1:1 | Identical definition text; title renamed |
| Conversation reset | 2.4 | 2.1 | 2.1 Conversation reset | 1:1 | Identical definition text |
| Fail to elicit clarification | 1.4 | 2.2 | 2.2 Fail to ask for clarification | 1:1 | Identical definition text; title renamed |
| Derailment from task | 2.5 | 2.3 | 2.3 Task derailment | 1:1 | Identical definition text; title renamed |
| Withholding relevant information | 3.2 | 2.6 | 2.4 Information Witholding | 1:1 | Identical definition text; title renamed |
| Ignoring suggestions from agents | 3.3 | 2.7 | 2.5 Ignored Other Agents' Input | 1:1 | Identical definition text; title renamed |
| Inconsistency between reasoning and action | 1.2 | 1.2 | 2.6 Reasoning-Action Mismatch | 1:1 | Old text fully contained in the 2.6 entry, which keeps the old title as a subtitle |
| Ill specified termination condition leading to premature termination | 4.1 | 3.1 | 3.1 Premature Termination | 1:1 | Old text fully contained in the 3.1 entry, which keeps the old title as a subtitle |
| Lack of critical verification | 4.3 | 3.2 | 3.2 No or Incomplete Verification | **Ambiguous** | Text contained in the 3.2 entry. But Rounds 2, 3, and Generlazability carry the rule "This is implicitly True if 3.3 Lack of result verification is true, so no longer need to explicitly specify as True"; Round 1's 4.3 does not. So when 3.3 is True, a 3.2 label of False may mean "not present" or "not re-marked". There is also the 3.2 naming conflict between `definitions.txt` and the HF README found in MAST 05. |
| Lack of result verification | 4.2 | 3.3 | 3.3 Incorrect Verification | **Ambiguous** | Old text is **not** contained in the Generlazability 3.3 entry. Rounds 1 to 3 include "NEW: FUNCTION CORRECTNESS here", "1. no verification in MAS", and "2. verification is designed to exist in MAS, but verifier fail to complete what was exactly prompted to do..."; the Generlazability 3.3 entry drops those lines. Whether "no verification at all" belongs under current 3.2 or 3.3 is the open question from MAST 05. |
| Undetected conversation ambiguities and contradictions | 1.3 | 2.4 | none | **No clean mapping** | Matches no current definition. Round 3 uses a much longer definition than Round 2 (the only substantive text change between those rounds), which mentions agents proceeding "without raising appropriate alerts or clarifications". That overlaps current 2.2 but is not the same. |
| Unbatched repetitive execution | 2.1 | 1.4 | none | **No clean mapping** | Matches no current definition. Possible overlap with 1.3 Step Repetition. |
| Disagreement induced inaction | 3.1 | 2.5 | none | **No clean mapping** | Matches no current definition. |
| Waiting for known information | 3.4 | (not in Rounds 2, 3) | none | **No clean mapping** | Matches no current definition. The stored text adds "Tere is a case where it is different to holding information", which points at a relation to 2.4 without defining it. |

How much judgment Option B needs, counted from the majority labels in section 2.2:

- 12 old titles map 1:1 onto 12 current codes (1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1). Every current code has at least one source.
- 2 old titles are ambiguous and map onto the verification codes 3.2 and 3.3. They carry **12** of the positive labels in Rounds 1 to 3: Round 1 4.3: 2, 4.2: 2; Round 2 3.2: 0, 3.3: 3; Round 3 3.2: 2, 3.3: 3.
- 4 old titles have no clean mapping. Together they carry **2** positive labels: Round 1 3.4 "Waiting for known information", on trace_id 3 and 4. The other three have 0 positives in every round.
- The mapping is not only a relabelling. If an annotator filed a behaviour under a mode that no longer exists (for example "Unbatched repetitive execution"), the current-taxonomy label for a related code (for example 1.3) might have been 1, but the old data records it as 0. Deciding whether to adjust for this is a judgment call for every record where a dropped mode is positive.
- Other issues Option B brings in: trace_id 3 and 8 are the same trace; the identical label matrices in section 2.3 mean 15 records yield only 6 distinct label matrices; and Round 1 lists its 4.x codes in the order 4.1, 4.3, 4.2.

### 4c. Recommendation to raise with Pramod and the team

This is a recommendation for the team to discuss, not a decision.

**Option A looks safer.** It needs no crosswalk, so no labels depend on team judgment calls, and the draft can be traced directly to the source file. Option B adds 15 records but only 6 distinct label matrices, needs judgment on the two verification codes (which hold most of the positive labels), and imports old-taxonomy labels that may not mean what the current codes mean. That risk seems out of proportion to the few pipeline points at stake.

Whichever option is chosen, the report should not claim to reproduce the published 0.94 accuracy or 0.77 kappa. With 4 traces (or 19), a result can only be reported as a sanity check or smoke test, with the interval widths from section 4a stated next to it. And before either option is used, the label-duplication pattern in section 2.3 should be checked against the upstream MAST annotation files.

Decisions for the team:

1. Option A, Option B, or neither (for example, report only a smoke test).
2. Whether someone checks the section 2.3 duplication against the upstream source first, and who.
3. If Option B: who makes the 3.2 / 3.3 crosswalk call, and how the 4 dropped modes are handled. The 3.2 / 3.3 question is already open in CONTEXT.md under Manav.
4. Whether to correct the swapped mas_name / benchmark_name on trace_id 17 and 18 in any frozen file, or keep them as stored with a note.

---

## Reproducing these numbers

All figures come from Python 3 scripts run over the two raw JSON files with `encoding="utf-8"`. The majority-vote rule is in section 2.2. The Wilson intervals use z = 1.96. The trace overlap check is exact string equality between `trace` (human file) and `trace.trajectory` (full file).
