# Demo 1 — Data Extraction, Cleaning, Preprocessing, and Quality Assessment

**DATA 298A · Team 4 · Topic 4 · Multiplayer Agent Sessions**  
**Dataset for this demo:** MAST-Data (Cemri et al., 2025) — our published baseline corpus  
**Owner:** Naman (data track) · anyone on the team can run the commands below

This document is the runbook for the ISA / Team Meeting **pipeline demo**. It maps 1:1 to the four required parts:

| Demo part | What we show | Script / artifact |
|-----------|--------------|-------------------|
| 1. Extraction | Pull pinned public data + taxonomy | `data/scripts/download_mast.py` → `data/mast/hf/`, `data/mast/taxonomy/` |
| 2. Cleaning | Validate labels, key records, exclude fully-null records | `data/scripts/eda_mast.py` Stage 2 |
| 3. Preprocessing | Flatten labels, category rollups, analysis table | Stage 3 → `data/mast/processed/mast_clean_summary.csv` |
| 4. Quality assessment | Automated gates + distribution summary | Stage 4 (must print **all checks passed**) |

> **Not this demo:** QMSum (Model 1 supervision only). MAST is the baseline failure-taxonomy corpus.

---

## Before you start

```bash
git pull
cd /path/to/multiplayer-agent-sessions
python -m venv .venv && source .venv/bin/activate   # if needed
pip install -r requirements.txt
```

Repo: https://github.com/ayushgawai/multiplayer-agent-sessions  
Linear: https://linear.app/data-298a-team-4/team/DAT  
Workbook (Canvas): `docs/reports/T4.A4.docx` → upload as **T4.A4.docx**

---

## One command sequence (live demo)

Run these two commands. Narrate the four stages as the second script prints them.

```bash
# Stage 0 / Extraction: download + checksum + STATS.md
python data/scripts/download_mast.py

# Stages 1–4: extract summary → clean → preprocess → quality gate + EDA
python data/scripts/eda_mast.py
```

**Success looks like:** the second script ends with

```text
QUALITY GATE: all checks passed — dataset ready for baseline / eval use.
```

Expected headline numbers:

- **1,642** annotated traces (matches the paper)
- **19** human-labelled rows (inter-annotator sample)
- **14** failure-mode codes in **3** categories
- **7** multi-agent frameworks, **5** LLMs, **8** benchmarks

---

## Part 1 — Data extraction

### What we extract

| Source | Where | What |
|--------|-------|------|
| Hugging Face `mcemri/MAD` (pinned commit) | `data/mast/hf/` | `MAD_full_dataset.json` (1,642), `MAD_human_labelled_dataset.json` (19), README |
| MAST GitHub taxonomy (pinned commit) | `data/mast/taxonomy/` | `definitions.txt`, `examples.txt` |

Pinned revisions and per-file SHA-256 are written to:

**`data/mast/STATS.md`**

Open this file on screen during the demo. It records:

- Source URLs and commit SHAs  
- Download timestamp  
- Record count vs paper (1,642 == 1,642)  
- Per-file size and SHA-256  

### Fields pulled per trace

From each row of `MAD_full_dataset.json`:

- `mas_name` — multi-agent framework (e.g. ChatDev, MetaGPT, AG2)  
- `llm_name` — model used in the trace  
- `benchmark_name` — task / benchmark  
- `trace_id` — id within that framework run  
- `trace.trajectory` — full logged interaction text  
- `mast_annotation` — 14 binary failure codes (`1.1` … `3.3`)

### Script

`data/scripts/download_mast.py` (Linear: DAT-28)

- Idempotent (skips re-download unless `--force`)  
- Re-validates checksums every run  
- Fails loudly if count or hash mismatches  
- Does **not** commit the JSON into git (data is reconstructed on demand)

---

## Part 2 — Cleaning

Implemented in **Stage 2** of `data/scripts/eda_mast.py`.

### Rules applied

1. Require `trace.key`, an integer `trace_id`, and an annotation object (otherwise a hard error, not a silent drop)  
2. Strip / normalize `mas_name`, `llm_name`, `benchmark_name`  
3. Each of the 14 MAST codes must be exactly `0` / `1` or `null`. Any other value is a hard error.  
4. A `null` or missing code stays `null`. It is never converted to `0`.  
5. Exclude a record from scoring only if all 14 codes are null (4 records). A partly-null record is kept with its nulls preserved (the pinned file has none).  

### Record key

The canonical key is (`trace.key`, `trace_id`), per `eval_manifest.json`. `trace_id` alone is **not** unique (it resets per source run). Uniqueness is asserted over all 1,642 raw records, and a duplicate fails the run with the duplicate keys listed. The old `row_id` is gone; nothing consumed it.

### What to say

> “We report all 1,642 raw records and score 1,638. The 4 records with no labels at all are excluded, and we never read a missing label as a negative one.”

---

## Part 3 — Preprocessing

Implemented in **Stage 3** of `data/scripts/eda_mast.py`.

### Transforms

| Output | Meaning |
|--------|---------|
| `trace_key`, `trace_id` | Canonical record key |
| `fail_1_1` … `fail_3_3` | Flattened label columns; a null label is an empty cell |
| `n_failures` | How many modes are positive (1) on that trace; nulls are not counted |
| `n_null_labels` | How many of the 14 codes are null on that trace |
| `failure_codes` | Pipe-joined list of active codes (e.g. `1.3\|2.6`) |
| `cat_specification` | Count of positives in category 1.x |
| `cat_misalignment` | Count of positives in category 2.x |
| `cat_verification` | Count of positives in category 3.x |

### MAST category map (paper)

| Category | Codes | Theme |
|----------|-------|--------|
| Specification issues | 1.1–1.5 | Task/role/spec failures |
| Inter-agent misalignment | 2.1–2.6 | Coordination / conversation failures |
| Task verification / termination | 3.1–3.3 | Checking and stopping failures |

### Artifact produced

**`data/mast/processed/mast_clean_summary.csv`** (gitignored; scorable records only)

**`data/mast/EDA_SUMMARY.json`** (committed, deterministic: raw / scorable counts, excluded keys, per-code 1/0/null counts, key-uniqueness result, input sha256). Two runs give byte-identical files.

Open a few rows in a spreadsheet or `head` during the demo to show the flattened schema.

```bash
head -n 3 data/mast/processed/mast_clean_summary.csv
wc -l data/mast/processed/mast_clean_summary.csv   # 1639 = header + 1638 scorable rows
```

---

## Part 4 — Quality assessment

Implemented in **Stage 4** of `data/scripts/eda_mast.py`.

### Automated quality gates (must PASS)

| Check | Pass criterion |
|-------|----------------|
| Raw record count | **1642** (paper; read from `eval_manifest.json`) |
| Scorable record count | **1638** |
| Excluded records | **4**, keys equal the manifest's `excluded_records` |
| Partially-null records | 0 |
| Unique (`trace_key`, `trace_id`) | 1642 unique keys over all raw records |
| Schema completeness | identity fields + 14 label columns present |
| Label domain | every label cell is `0`, `1`, or null |
| Taxonomy present | `definitions.txt` non-empty |
| Human-labelled IAA set | **19** rows |

Note: the 4-tuple `(mas, benchmark, llm, trace_id)` is not unique (1552 distinct), which is why the key is (`trace.key`, `trace_id`).

### Distribution summary (EDA for the walkthrough)

The script prints:

- Counts of frameworks / LLMs / benchmarks  
- Top frameworks (e.g. AG2, MetaGPT, ChatDev, …)  
- Top failure modes (e.g. 1.3 Step repetition, 3.3, 2.6, …)  
- Share of scorable traces with ≥1 failure (~75%)  
- Trace length: min / median / max characters  

Use this as the “we looked at the data” evidence for the ISA.

### Manual spot-checks (optional, 30 seconds)

```bash
# Provenance
sed -n '1,40p' data/mast/STATS.md

# Taxonomy definitions (failure mode names)
sed -n '1,30p' data/mast/taxonomy/definitions.txt

# One raw JSON record shape
python - <<'PY'
import json
r = json.load(open("data/mast/hf/MAD_full_dataset.json"))[0]
print(sorted(r.keys()))
print("annotation codes:", sorted(r["mast_annotation"].keys()))
print("mas/llm/bench:", r["mas_name"], r["llm_name"], r["benchmark_name"])
print("trajectory chars:", len(r["trace"]["trajectory"]))
PY
```

---

## Files to keep open during the demo

| Purpose | Path |
|---------|------|
| This runbook | `docs/demo1-data-pipeline.md` |
| Extract + checksum | `data/scripts/download_mast.py` |
| Clean / preprocess / QA | `data/scripts/eda_mast.py` |
| Provenance report | `data/mast/STATS.md` |
| Raw extracted data | `data/mast/hf/MAD_full_dataset.json` |
| Human-labelled sample | `data/mast/hf/MAD_human_labelled_dataset.json` |
| Taxonomy | `data/mast/taxonomy/definitions.txt` |
| Preprocessed table | `data/mast/processed/mast_clean_summary.csv` |
| Workbook §2.1 Data plan | `docs/reports/T4.A4.docx` |

---

## Suggested 3-minute script

1. **Open STATS.md** — “Pinned HF + GitHub revisions, SHA-256, count 1642 matches the paper.”  
2. **Run `download_mast.py`** — “Extraction is scripted and reproducible; data is not hand-copied.”  
3. **Run `eda_mast.py`** — walk Stages 1–4 as they print.  
4. **Open the CSV** — “Preprocessed flat table for analysis and the baseline path.”  
5. **Point at QUALITY GATE passed** — “Ready for MAST baseline eval work (prompt, parser, batch, metrics).”  
6. **Tie to project** — “MAST is the published baseline we reproduce. Our four models M1–M4 are separate bake-offs; M1 uses QMSum later.”

---

## How this ties to the project (if asked)

| Question | Short answer |
|----------|--------------|
| Why this dataset? | Published MAST baseline for failure analysis (AI-1 / DR-7 in the workbook). |
| Is this training data for M1–M4? | No. MAST = baseline. QMSum = M1 supervision. Pilot sessions = M2–M4 later. |
| Where is this in the workbook? | §1.2 data requirements (DR-7), §2.1 Data Management Plan, Table 11 baseline. |
| Where is tracking? | Linear DAT-28 (download), DAT-29/30 (schema/manifest), DAT-31+ (judge stack). |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Missing data/mast/hf/...` | Run `python data/scripts/download_mast.py` first |
| Checksum / count failure | Re-run with `python data/scripts/download_mast.py --force` |
| Import / `requests` missing | `pip install -r requirements.txt` |
| QUALITY GATE fail | Do not improvise; fix data with the download script and re-run EDA |

---

## Ownership reminder

| Person | Role in this demo |
|--------|-------------------|
| Naman | Data lead — download, STATS, schema/manifest |
| Ayush | Session platform / contracts (not required for Demo 1 runtime) |
| Manav | MAST prompt / parser / viewer (after this data is frozen) |
| Shriram | MAST batch + provenance (consumes frozen data) |
| Pramod | Metrics + published comparison (consumes predictions) |
