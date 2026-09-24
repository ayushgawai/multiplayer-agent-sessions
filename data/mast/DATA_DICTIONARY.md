# MAST data dictionary

Linear: DAT-29 (MAST 05). Owner: Naman Chheda.

This file documents the two MAST (MAD) data files that MAST 04 downloaded into `data/mast/hf/`. Every count and value below was produced by scanning the files on disk with `json.load(open(path, encoding="utf-8"))`. Nothing here is copied from the dataset card without being checked, except where a line says "per the dataset card".

| File | Top-level type | Records |
|------|----------------|---------|
| `data/mast/hf/MAD_full_dataset.json` | JSON array of objects | 1642 |
| `data/mast/hf/MAD_human_labelled_dataset.json` | JSON array of objects | 19 |

For the 14 failure-mode codes and their definitions, see [TAXONOMY.md](TAXONOMY.md).

---

## Read this first: two warnings about the labels

**1. The labels in `MAD_full_dataset.json` were produced by an LLM judge. They are not human annotations.**
The dataset card (`data/mast/hf/README.md`, "Notes") says: "Annotations are produced by an LLM judge, not by human labelling." The file itself has no field that records who or what produced each label, so this cannot be confirmed from the data alone. Treat every value in `mast_annotation` as a model prediction, not as ground truth.

**2. `MAD_human_labelled_dataset.json` cannot be used as a 14-mode gold set.**
It holds 19 records split into four groups. Rounds 1, 2, and 3 (15 records) were labelled against older revisions of the taxonomy with 18, 17, and 17 failure modes. Their codes do not line up with the current 14 codes: for example, code `1.2` means "Inconsistency between reasoning and action" in Round 1 but "Disobey Role Specification" in the current taxonomy. Only the fourth group, named `Generlazability` in the file (4 records), uses the 14-mode taxonomy. The dataset card says the same thing: "each round uses a different revision of the taxonomy (18, 17, 17 and 14 modes) and the codes are not comparable across rounds." Do not pool labels across rounds, and do not compare Round 1 to 3 labels with `mast_annotation` by code.

---

## `MAD_full_dataset.json`

Every one of the 1642 records has exactly these six keys, in this order: `mas_name`, `llm_name`, `benchmark_name`, `trace_id`, `trace`, `mast_annotation`.

### `mas_name`

- **Type:** string (all 1642 records)
- **Meaning:** the multi-agent system (MAS) framework that produced the trace.
- **Observed values (7):**

| Value | Records |
|-------|---------|
| `AG2` | 597 |
| `MetaGPT` | 430 |
| `ChatDev` | 330 |
| `Magentic` | 195 |
| `OpenManus` | 30 |
| `AppWorld` | 30 |
| `HyperAgent` | 30 |

### `llm_name`

- **Type:** string (all 1642 records)
- **Meaning:** the LLM that powered the agents in the MAS run.
- **Observed values (5):**

| Value | Records |
|-------|---------|
| `GPT-4o` | 751 |
| `Claude` | 323 |
| `Qwen` | 200 |
| `CodeLlama` | 200 |
| `GPT-4o-mini` | 168 |

The file gives no model version beyond these names (for example, no Claude or Qwen version string).

### `benchmark_name`

- **Type:** string (all 1642 records)
- **Meaning:** the benchmark the task came from.
- **Observed values (8):**

| Value | Records |
|-------|---------|
| `ProgramDev-v2` | 400 |
| `ProgramDev` | 390 |
| `GSM` | 223 |
| `Olympiad` | 206 |
| `GAIA` | 195 |
| `MMLU` | 168 |
| `Test-C` | 30 |
| `SWE-Bench-Lite` | 30 |

Note: `trace.key` for the 223 `GSM` records reads `AG2_GSM_Plus_...`, and the human-labelled file calls the same benchmark `GSM-Plus`. The 200 records with keys `ChatDev_ProgramDev2_GPT4o` and `MetaGPT_ProgramDev2_*` have `benchmark_name` = `ProgramDev`, not `ProgramDev-v2`. Use `benchmark_name` as written; do not infer the benchmark from `trace.key`.

### Observed combinations

Only 15 of the 7 x 5 x 8 possible (MAS, LLM, benchmark) combinations exist:

| mas_name | llm_name | benchmark_name | Records |
|----------|----------|----------------|---------|
| AG2 | GPT-4o | Olympiad | 206 |
| AG2 | GPT-4o | GSM | 30 |
| AG2 | Claude | GSM | 193 |
| AG2 | GPT-4o-mini | MMLU | 168 |
| MetaGPT | GPT-4o | ProgramDev | 130 |
| MetaGPT | Claude | ProgramDev | 100 |
| MetaGPT | Qwen | ProgramDev-v2 | 100 |
| MetaGPT | CodeLlama | ProgramDev-v2 | 100 |
| ChatDev | GPT-4o | ProgramDev | 130 |
| ChatDev | Qwen | ProgramDev-v2 | 100 |
| ChatDev | CodeLlama | ProgramDev-v2 | 100 |
| Magentic | GPT-4o | GAIA | 195 |
| OpenManus | GPT-4o | ProgramDev | 30 |
| AppWorld | GPT-4o | Test-C | 30 |
| HyperAgent | Claude | SWE-Bench-Lite | 30 |

(14 distinct MAS/LLM pairs; AG2 + GPT-4o appears with two benchmarks.)

### `trace_id`

- **Type:** integer (all 1642 records)
- **Meaning:** position of the trace within its source run, identified by `trace.key`. It always equals `trace.index` (1642 of 1642).
- **Observed values:** 0 to 205. Only 206 distinct values across the file.
- **Not a unique id.** The pair (`trace.key`, `trace_id`) is unique across all 1642 records. The tuple (`mas_name`, `benchmark_name`, `llm_name`, `trace_id`) is **not** unique (1552 distinct), because some combinations come from two source runs (see `trace.key`). Use (`trace.key`, `trace_id`) as the record key.

### `trace`

- **Type:** object with exactly three keys, `key`, `index`, `trajectory` (all 1642 records).

| Sub-field | Type | Meaning | Observed |
|-----------|------|---------|----------|
| `trace.key` | string | Name of the source run the trace belongs to. | 18 distinct values, listed below |
| `trace.index` | integer | Index within that run. | Always equals `trace_id` |
| `trace.trajectory` | string | The full raw execution log of the MAS run, as one string. Format varies by framework (JSON-like message lists, log lines, markdown tables). | Length 1,262 to 2,004,123 characters; median 9,746 |

`trace.key` values (records, `trace_id` range):

| trace.key | Records | trace_id | (mas, benchmark, llm) |
|-----------|---------|----------|-----------------------|
| `AG2_GSM_Plus_Claude` | 193 | 0..192 | AG2, GSM, Claude |
| `AG2_GSM_Plus_GPT4o` | 30 | 0..29 | AG2, GSM, GPT-4o |
| `AG2_MMLU_GPT4o_Mini` | 168 | 0..167 | AG2, MMLU, GPT-4o-mini |
| `AG2_Olympiad_GPT4o` | 206 | 0..205 | AG2, Olympiad, GPT-4o |
| `AppWorld_Test-C_GPT-4o` | 30 | 0..29 | AppWorld, Test-C, GPT-4o |
| `ChatDev_ProgramDev-v2_CodeLlama` | 100 | 0..99 | ChatDev, ProgramDev-v2, CodeLlama |
| `ChatDev_ProgramDev-v2_Qwen` | 100 | 0..99 | ChatDev, ProgramDev-v2, Qwen |
| `ChatDev_ProgramDev2_GPT4o` | 100 | 0..99 | ChatDev, ProgramDev, GPT-4o |
| `ChatDev_ProgramDev_GPT4o` | 30 | 0..29 | ChatDev, ProgramDev, GPT-4o |
| `HyperAgent_SWE-Bench-Lite_Claude` | 30 | 0..29 | HyperAgent, SWE-Bench-Lite, Claude |
| `MagenticOne_GAIA_GPT4o` | 30 | 0..29 | Magentic, GAIA, GPT-4o |
| `Magentic_One_GPT4o` | 165 | 0..164 | Magentic, GAIA, GPT-4o |
| `MetaGPT_ProgramDev-v2_CodeLlama` | 100 | 0..99 | MetaGPT, ProgramDev-v2, CodeLlama |
| `MetaGPT_ProgramDev-v2_Qwen` | 100 | 0..99 | MetaGPT, ProgramDev-v2, Qwen |
| `MetaGPT_ProgramDev2_Claude` | 100 | 0..99 | MetaGPT, ProgramDev, Claude |
| `MetaGPT_ProgramDev2_GPT4o` | 100 | 0..99 | MetaGPT, ProgramDev, GPT-4o |
| `MetaGPT_ProgramDev_GPT4o` | 30 | 0..29 | MetaGPT, ProgramDev, GPT-4o |
| `OpenManus_ProgramDev_GPT4o` | 30 | 0..29 | OpenManus, ProgramDev, GPT-4o |

### `mast_annotation`

- **Type:** object (all 1642 records).
- **Meaning:** one binary flag per MAST failure mode, saying whether the **LLM judge** found that failure in the trace. See warning 1 above: these are not human labels.
- **Keys:** every record has exactly the same 14 keys: `1.1`, `1.2`, `1.3`, `1.4`, `1.5`, `2.1`, `2.2`, `2.3`, `2.4`, `2.5`, `2.6`, `3.1`, `3.2`, `3.3`. These are the same 14 codes as `data/mast/taxonomy/definitions.txt` (see [TAXONOMY.md](TAXONOMY.md)). No record has extra or missing keys.
- **Values:** integer `1` (failure present), integer `0` (absent), or `null` (no annotation available). No other values occur (22,932 ints, 56 nulls).
- **Nulls:** the 56 nulls are 4 records x 14 codes. Each of those 4 records is null on all 14 codes; no record is partly null. All 4 are `ChatDev_ProgramDev-v2_CodeLlama`, `trace_id` 4, 72, 73, 81, and all have very long trajectories (564,931 to 837,072 characters). Drop or mask these 4 records; do not read `null` as `0`.

Per-code counts across all 1642 records:

| Code | `1` | `0` | `null` |
|------|-----|-----|--------|
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

---

## `MAD_human_labelled_dataset.json`

A different schema from the full file. Every one of the 19 records has exactly these six keys: `round`, `mas_name`, `benchmark_name`, `trace_id`, `trace`, `annotations`. There is **no `llm_name`** field and **no `mast_annotation`** field.

Per the dataset card, this file is the inter-annotator agreement study with 3 annotators. See warning 2 above before using it.

### `round`

- **Type:** string
- **Meaning:** which annotation round, and so which taxonomy revision, the record was labelled with.
- **Observed values (4):**

| Value | Records | Failure modes per record | Taxonomy |
|-------|---------|--------------------------|----------|
| `Round 1` | 5 | 18 | Old revision. Codes 1.1 to 1.5, 2.1 to 2.6, 3.1 to 3.4, 4.1 to 4.3. |
| `Round 2` | 5 | 17 | Old revision. Codes 1.1 to 1.7, 2.1 to 2.7, 3.1 to 3.3. |
| `Round 3` | 5 | 17 | Same 17 titles and order as Round 2, but the definition text inside the `failure mode` strings is not identical to Round 2. |
| `Generlazability` | 4 | 14 | Current 14 codes. The value is spelled `Generlazability` in the file. |

The codes in Rounds 1 to 3 do not mean the same thing as the current codes. Round 1 and Round 2/3 mode titles, as they appear in the file:

| Round 1 (18) | Rounds 2 and 3 (17) |
|--------------|---------------------|
| 1.1 Poor task constraint compliance | 1.1 Poor task constraint compliance |
| 1.2 Inconsistency between reasoning and action | 1.2 Inconsistency between reasoning and action |
| 1.3 Undetected conversation ambiguities and contradictions | 1.3 Unaware of stopping conditions |
| 1.4 Fail to elicit clarification | 1.4 Unbatched repetitive execution |
| 1.5 Unaware of stopping conditions | 1.5 Step repetition |
| 2.1 Unbatched repetitive execution | 1.6 Backtracking interruption |
| 2.2 Step repetition | 1.7 Disobey role specification |
| 2.3 Backtracking interruption | 2.1 Conversation reset |
| 2.4 Conversation reset | 2.2 Fail to elicit clarification |
| 2.5 Derailment from task | 2.3 Derailment from task |
| 2.6 Disobey role specification | 2.4 Undetected conversation ambiguities and contradictions |
| 3.1 Disagreement induced inaction | 2.5 Disagreement induced inaction |
| 3.2 Withholding relevant information | 2.6 Withholding relevant information |
| 3.3 Ignoring suggestions from agents | 2.7 Ignoring suggestions from agents |
| 3.4 Waiting for known information | 3.1 Ill specified termination condition leading to premature termination |
| 4.1 Ill specified termination condition leading to premature termination | 3.2 Lack of critical verification |
| 4.3 Lack of critical verification | 3.3 Lack of result verification |
| 4.2 Lack of result verification | |

(Round 1 lists 4.3 before 4.2; that is the order in the file.)

The `Generlazability` group's 14 titles, as they appear in the file: 1.1 Disobey Task Specification, 1.2 Disobey Role Specification, 1.3 Step Repetition, 1.4 Loss of Conversation History, 1.5 Unaware of Termination Conditions, 2.1 Conversation reset, 2.2 Fail to ask for clarification, 2.3 Task derailment, 2.4 Information Witholding, 2.5 Ignored Other Agents' Input, 2.6 Reasoning-Action Mismatch, 3.1 Premature Termination, 3.2 No or Incomplete Verification, 3.3 Incorrect Verification. Three of these titles differ from `definitions.txt` (2.6, 3.2, 3.3); see [TAXONOMY.md](TAXONOMY.md#name-differences-between-sources).

### `mas_name`

- **Type:** string
- **Meaning:** the MAS framework.
- **Observed values:** `AppWorld` (3), `HyperAgent` (3), `AG2` (3), `ChatDev` (4), `MetaGPT` (4), `GAIA` (2).
- **Data error:** the two `Generlazability` records with `trace_id` 17 and 18 have `mas_name` = `GAIA` and `benchmark_name` = `Magentic` / `OpenManus`. The two fields are swapped in the source file. The intended values are almost certainly `mas_name` = `Magentic` / `OpenManus`, `benchmark_name` = `GAIA`. The file has not been edited.

### `benchmark_name`

- **Type:** string
- **Observed values:** `Test-C` (3), `SWE-Bench-Lite` (3), `GSM-Plus` (3), `ProgramDev` (6), `MMLU` (2), `Magentic` (1), `OpenManus` (1). The last two are the swapped values described above. Note `GSM-Plus` here versus `GSM` in the full file.

### `trace_id`

- **Type:** integer
- **Observed values:** 0 to 18, unique across the file (one per record). It is not related to `trace_id` in `MAD_full_dataset.json`; do not join the two files on it.

### `trace`

- **Type:** string (the raw trajectory as one string). In the full file `trace` is an object; here it is a plain string.
- **Observed lengths:** 2,503 to 644,556 characters.
- **Duplicate:** the Round 1 ChatDev record (`trace_id` 3) and the Round 2 ChatDev record (`trace_id` 8) have byte-identical `trace` strings. The file therefore contains 18 distinct traces across 19 records.

### `annotations`

- **Type:** list of objects. List length is 18, 17, 17, or 14 depending on `round` (see above).
- Each list item has exactly four keys:

| Key | Type | Meaning |
|-----|------|---------|
| `failure mode` | string (key contains a space) | The code, title, and full definition text that the annotators were shown, as one string. Starts with the code and title on the first line, for example `"1.1 Poor task constraint compliance\n\n..."`. |
| `annotator_1` | boolean | Annotator 1's judgment: `true` = failure present. |
| `annotator_2` | boolean | Annotator 2's judgment. |
| `annotator_3` | boolean | Annotator 3's judgment. |

- **Observed values:** 946 booleans and 2 floats. The 2 floats are `NaN`, both on `annotator_3` of `trace_id` 18 (`Generlazability`), for codes 3.2 and 3.3. The file stores them as the bare token `NaN`, which Python's `json` module accepts but strict JSON parsers reject. Treat them as missing.

---

## Encoding

All files were read with `encoding="utf-8"`. No mojibake markers (`Ã`, `Â`, `â€`, U+FFFD) were found in either JSON file, `definitions.txt`, `examples.txt`, or the HF `README.md`. `definitions.txt` and `examples.txt` are pure ASCII.
