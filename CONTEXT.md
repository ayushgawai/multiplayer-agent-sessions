# Team context — Multiplayer Agent Sessions

**DATA 298A · Section 21 · Team 4 · Topic 4**  
**Repo:** https://github.com/ayushgawai/multiplayer-agent-sessions  
**Linear:** https://linear.app/data-298a-team-4/team/DAT  
**Spec:** [docs/build-plan.html](docs/build-plan.html)

Everyone (and every coding agent) should read this file after `git pull` before changing code. Update this file in the same PR when ownership, status, or contracts change.

This file is also the live answer sheet for Team Meeting 1 and later reviews. If a fact is not in this file, say it is not settled. Do not invent metrics, winners, or costs.

---

## How to use this file

1. Pull `main`.
2. Read this file and the section for your name.
3. Build only what you own. Do not edit another owner's files.
4. Commit with a Linear id prefix (`DAT-xx: …`).
5. If you change a schema, API route, or metric definition, add an ADR under `docs/decisions/` first.
6. When your Progress Report 1 work lands, update **Current status** and your row in **Progress Report 1** below, then commit.

---

## Product in one paragraph

Shared live sessions where several humans and several agents work in one workspace with concurrent edits, hand-off, interruption, and rollback. Four learned models (M1–M4) sit on the platform. A published MAST baseline is reproduced separately (not one of the four).

---

## Ownership (exclusive)

| Person | Build | Do not touch |
|--------|-------|--------------|
| **Ayush Gawai** | `session-service/`, `serving/`, `models/common/`, `models/m1_catchup/`, `infra/`, `.github/workflows/`, `requirements*.txt`, `eval/configs/m1-*.yaml`, `docs/decisions/` | `client/`, `agent-runtime/`, `data/`, `eval/harness.py`, `tests/` |
| **Manav** | `client/`, `crdt-server/`, `models/m3_arbitration/`, `eval/configs/m3-*.yaml`, `docs/slides/`, `models/baseline_mast/` prompt, parser, viewer files (DAT-31/32/33) | session-service internals, `agent-runtime/`, `data/`, `eval/harness.py` |
| **Naman Chheda** | `data/`, `tools/annotator/`, `models/m2_intent/`, `eval/configs/m2-*.yaml`, `docs/reports/` | `session-service/`, `client/`, `agent-runtime/`, `eval/harness.py` |
| **Shriram** | `agent-runtime/`, `tests/`, `models/m4_routing/`, `eval/configs/m4-*.yaml`, `docs/verification/` | `client/`, session-service internals, `data/`, `eval/harness.py` |
| **Pramod** | `eval/` (exclusive except each person's configs), `models/baseline_mast/` (run_judge.py, MODEL_CARD.md), `docs/protocol.md`, `docs/failure-analysis.md` | other training scripts, services, `client/` |

Cross-boundary work is a **network call** or a **committed file format**. No shared process memory between owners.

---

## Frozen contracts (do not change casually)

| Contract | Location | Notes |
|----------|----------|-------|
| SessionEvent + HTTP API | `session-service/app/schemas.py` | ADR-001 |
| OpenAPI | `session-service/openapi.json` | Manav generates client types; Shriram builds fixtures |
| Predict interface | `POST /v1/models/{model_id}/predict` | Serving stubs in `serving/` |
| Candidate config schema | `docs/build-plan.html` § harness | Seeds **13, 29, 47**; pin HF `repo` + `revision` |
| Metrics / harness | `eval/` only | Never compute ROUGE/F1/latency outside `eval/metrics/` |

Regenerate OpenAPI after schema changes:

```bash
cd session-service && PYTHONPATH=. python scripts/export_openapi.py
```

---

## Progress Report 1

- **Due:** Thursday Sep 24/25, 2026 (Canvas)
- **Upload name:** `T4.A3.doc` (or pdf)
- **Working copy:** [docs/reports/T4.A3.docx](docs/reports/T4.A3.docx) (also `.doc` / `.pdf`)
- **Template source:** `reference_docs/`

### Checklist (team)

| Item | Owner | Status |
|------|-------|--------|
| Repo, pins, CI live | Ayush | Done |
| SessionEvent frozen + OpenAPI committed | Ayush | Done |
| Serving stubs m1–m4 | Ayush | Done |
| M1 configs `m1-a`…`m1-d` | Ayush | Done |
| Docker Compose skeleton | Ayush | Done |
| Progress Report 1 (`T4.A3`) | Team | Submitted / past due |
| Workbook 1 (`T4.A4.docx`) | Team | On `main` at `docs/reports/T4.A4.docx`. Canvas upload is the team's copy of that file. |
| MAST download script + `data/mast/STATS.md` | Naman (DAT-28, PR #1) | Done on `main` |
| MAST dictionary + taxonomy | Naman (DAT-29, PR #2) | Done on `main`: `data/mast/DATA_DICTIONARY.md`, `data/mast/TAXONOMY.md` |
| Frozen eval manifest | Naman (DAT-30, PR #4) | Done on `main`: `data/mast/eval_manifest.json` |
| QMSum download + STATS.md | Naman (DAT-11) | Open |
| MAST classification metrics | Pramod (DAT-37, PR #3) | Done on `main`: `eval/metrics/classification.py`. Convention `mast_binary_label_cells_v1` is provisional until checked against the paper. |
| Harness runs one candidate end to end | Pramod | Open. `eval/harness.py` is not on `main`. |
| M3 configs `m3-a`…`m3-d` | Manav (DAT-40, PR #10) | Done on `main` |
| M2 / M4 configs | Naman, Shriram | Not started |
| MAST judge prompt / parser / viewer | Manav (DAT-31/32/33, PRs #7 #8 #9) | Done on `main` under `models/baseline_mast/` |
| MAST batch + provenance | Shriram (DAT-34/35, PR #5) | Done on `main`: `run_batch.py`, `provenance.py` |
| Client / CRDT / presence | Manav (DAT-15/16/17) | In review: PRs #12, #13, #14. `client/` on `main` is still the scaffold. |
| Agent runtime on fixture | Shriram (DAT-18) | In review: PR #6 |
| Stub label `escalate_human` to `escalate` | Manav (DAT-40 follow-up) | Open PR #11. Serving owner reviews. |

### Part C — fill your row in the report

| Member | What to record when done |
|--------|---------------------------|
| Ayush | Already filled (DAT-1–DAT-11 style commits on `main`) |
| Naman | Issues closed, labels, link to download STATS / PRs |
| Manav | Issues closed, labels, link to client / m3 config PRs |
| Shriram | Issues closed, labels, link to runtime / tests / m4 configs |
| Pramod | Issues closed, labels, link to harness smoke result |

---

## Current status (update on pull / after each feature)

**Last updated:** 2026-10-08 (Ayush)

- Session service on `main`: durable event log (SQLAlchemy; SQLite in CI, Postgres in Compose) and Redis or in-process fan-out (ADR-002). OpenAPI routes unchanged.
- MAST track on `main` through download, dictionary, manifest, prompt, parser, viewer, batch, provenance, and classification metrics. No reproduction score has been posted.
- M1 configs and M3 configs are on `main`. M2 and M4 configs are not. No model has been trained.
- **Not on `main` yet:** React client and Yjs (PRs #12, #13, #14), LangGraph runtime (PR #6), `eval/harness.py`, QMSum, M2/M4 configs, ADR-003.

**Open PRs:** #6 DAT-18 (Shriram), #11 stub label rename (Manav), #12 DAT-15, #13 DAT-16, #14 DAT-17 (Manav).

When you finish a feature, add one bullet here under your name and bump **Last updated**.

### Ayush
- Foundation, ADR-001/002, durable event log and fan-out, serving stubs, M1 configs, Compose, CI.
- Workbook 1 figures: Gantt and PERT. MAST is parallel to the critical path, not on it.
- Next: pin the MAST judge environment (DAT-25), judge metadata (DAT-26), clean-environment smoke test (DAT-27). Branch protection (DAT-10) is still open.

### Naman
- On `main`: DAT-28 download and checksums, DAT-29 dictionary and taxonomy, DAT-30 eval manifest.
- Still open: QMSum download (DAT-11), six scenario briefs (DAT-21), team sign-off (DAT-22).

### Manav
- On `main`: judge prompt `mast-judge-v1`, parser `mast-parser-v1.1`, result viewer, M3 configs `m3-a` through `m3-d`.
- In review: client scaffold (#12), Yjs editor and crdt-server (#13), presence (#14). Browser-tested against the session service with up to three participants. Not merged, so do not demo the client from `main`.
- Open: ADR-003 prediction record (DAT-52, in progress). PR #11 renames the serving stub label `escalate_human` to `escalate`.

### Shriram
- On `main`: resumable MAST batch and run provenance (DAT-34/35, PR #5). Notes in `docs/verification/dat-34-dat-35-batch-execution.md`.
- In review: LangGraph plan, act, observe loop (DAT-18, PR #6). `agent-runtime/` on `main` is still the scaffold.
- Still open: final MAST runs (DAT-36), `doc_read` and `calc` (DAT-19), end-to-end loop on a fixture (DAT-20).

### Pramod
- On `main`: MAST classification metrics (DAT-37, PR #3), including CI for `eval/tests`.
- Still open: harness one-candidate end to end, published comparison (DAT-38, due 5 Nov), error analysis (DAT-39, due 11 Nov), dataset screenshot (DAT-12), locking the ROUGE call (DAT-13).

---

## How to answer

- Lead with the result, then the file or table that backs it.
- Separate three clocks: **past** (on `main` now), **current** (open pull requests), **future** (rest of 298A, then 298B).
- MAST is the published baseline. It is not Model 1, 2, 3, or 4.
- QMSum supervises Model 1 only. It is not a baseline, and we are not reproducing its BART score.
- Thresholds are targets. No bake-off winner exists. No MAST reproduction score has been posted.
- Training compute is the university GPU lab at $0. The cloud VM is a separate line, about $20 to $40 per month.

## Architecture

Two kinds of state, on purpose.

| State | Mechanism | Why |
|-------|-----------|-----|
| Document | Yjs CRDT (Manav, in review: PR #13) | Replicas converge without a central transform server. |
| Commands | Append-only SQL event log (Ayush, on `main`, ADR-002) | Order, audit, interrupt, and rollback. A CRDT does not decide whose instruction was intended. |

```
humans + agents
    |
    v
client (Vite + React, Yjs, presence)     <-- PRs #12 #13 #14, not on main
    |  HTTP + WebSocket
    v
session-service (FastAPI)                 <-- on main
    sessions, participants, events
    SQLite in CI, Postgres 16 in Compose
    Redis pub/sub, or in-process if REDIS_URL is unset
    |
    +--> agent-runtime (LangGraph plan, act, observe)   <-- PR #6, not on main
    |         five tools: web_search, doc_read, doc_write, table_build, calc
    |
    +--> serving  POST /v1/models/{model_id}/predict    <-- stubs on main
              M1 catch-up, M2 attribution, M3 arbitration, M4 routing
              |
              v
         eval/   metrics only. Harness not written yet.
```

Session service routes (ADR-001, unchanged by ADR-002):

| Method | Path | What it does |
|--------|------|----------------|
| GET | `/healthz` | Process is up |
| POST | `/v1/sessions` | Create a session and a join code |
| POST | `/v1/sessions/{id}/join` | Join with a role: author, reviewer, or observer |
| GET | `/v1/sessions/{id}/events` | Events after a sequence number |
| POST | `/v1/sessions/{id}/events` | Append one event |
| POST | `/v1/sessions/{id}/rollback` | Delete events after `to_seq` and rebuild the snapshot |
| WebSocket | `/v1/sessions/{id}/stream` | Live fan-out |

Event types on the wire: `doc_update`, `instruction`, `agent_step`, `tool_call`, `tool_result`, `interrupt`, `handoff`, `rollback`, `join`, `leave`, `arbitration`, `rejected`. An observer write is stored as `rejected`. It is not applied as the attempted type.

Sequence numbers are gapless. They are allocated inside a transaction with a row lock. Event rows are never updated. Rollback deletes rows with `seq` greater than `to_seq`. `app/replay.py` rebuilds a snapshot from events alone.

Serving is one predict route for all four models. The handlers are stubs until a bake-off winner exists.

The five tools are fixed so rollback has a defined meaning. Each has a timeout and a cap (`docs/build-plan.html`). `doc_read` and `calc` are still backlog (DAT-19). The runtime that calls them is PR #6.

## What we chose, and why

| Choice | Instead of | Reason |
|--------|------------|--------|
| Yjs for the document | Operational transform | OT needs a transform server and is easy to get wrong. CRDTs converge by design. |
| Event log for commands | CRDT for everything | Convergence is not intent. The log records who acted, supports interrupt within 2 seconds (FR-6), and supports rollback (FR-7). |
| LangGraph as the runtime | AutoGen or CrewAI as the product | Those frameworks coordinate agents under one supervisor. They do not model several humans giving conflicting instructions. LangGraph is the loop, not the session. |
| Four-candidate bake-off per model | Picking one architecture up front | Table 8 in the workbook is a comparison, not a pre-chosen winner. BART and Flan-T5 were surveyed. They are not the M1 plan. |
| MAST as the baseline | QMSum, or MultiAgentBench | MAST is a published failure taxonomy plus a validated LLM judge, which matches "did the multi-agent system fail, and how." QMSum is a summarization corpus, so it supervises M1 only. MultiAgentBench is the documented fallback if the MAST reproduction misses, inference only. |
| LoRA and encoders only | Full fine-tune of a large model | No full fine-tune above 4B parameters. Checkpoints go through `models/common/checkpointing.py`. |
| University GPU lab | Paid cloud GPU | The team has lab access. Do not quote $150 or $250. Colab is fallback only. |
| Seeds 13, 29, 47 | One seed | Report mean, standard deviation, and each seed. |
| Metrics only inside `eval/` | Each model script printing its own F1 | Stops four owners from implementing four different scores. |

ADRs:

- **ADR-001** (22 Sep 2026, accepted). Freezes `SessionEvent` and the HTTP API. Source of truth is `session-service/app/schemas.py`. OpenAPI is committed and regenerated only by `cd session-service && PYTHONPATH=. python scripts/export_openapi.py`.
- **ADR-002** (6 Oct 2026, accepted). Persists the log in SQL and fans events out over Redis. Public routes stay the same as ADR-001.
- **ADR-003** (DAT-52, in progress, Manav). Proposed format for a MAST prediction record. The viewer already reads that shape. It is not accepted yet.

## Models

No winner. No training run. Numbers below are acceptance targets.

| ID | Task | Candidates on disk | Target | When |
|----|------|--------------------|--------|------|
| M1 | Catch-up summary for a late joiner | `m1-a` ModernBERT-base extractive control. `m1-b` Qwen3-1.7B + LoRA. `m1-c` Qwen3.5-4B + LoRA. `m1-d` Gemma 4 E4B Instruct + LoRA. Configs in `eval/configs/m1-*.yaml`. | Held-out mean ROUGE-L at least 28.2 over three seeds, 95% CI. Also report ROUGE-1, ROUGE-2, BERTScore-F1. 28.2 is a QMSum reference floor, not a result we posted. | 298A |
| M2 | Which participant an instruction addresses | Configs not written. Plan: TF-IDF control, DeBERTa and ModernBERT cross-encoders, Qwen classification head. | macro-F1 at least 0.75 | 298B |
| M3 | Accept A, accept B, merge, or escalate | `m3-a` last-writer-wins. `m3-b` ModernBERT-base pairwise. `m3-c` Qwen3.5-4B + LoRA. `m3-d` few-shot Qwen3.5-4B. Configs in `eval/configs/m3-*.yaml`. | macro-F1 at least 0.70 and safer than last-writer-wins | 298B |
| M4 | Decompose and route | Configs not written. Plan: rules-only control, then planner and router arms. | Must emit a valid DAG before accuracy, latency, and cost count | 298B |
| MAST | Published judge, not one of the four | Prompt, parser, batch, provenance, metrics on `main`. Judge call not run. | Table 2 row o1 few-shot: accuracy 0.94, F1 0.80, kappa 0.77. Tolerances: accuracy within 0.02, F1 within 0.03, kappa within 0.05. | 298A |

Shared training rules: same epochs, max sequence length, and effective batch size inside one task (the configs use 3 epochs, 4096 tokens, batch 16). Prompted arms read prompts from committed files. Result JSON records split, git SHA, model revision, hardware, peak VRAM, and wall clock. Pin Hugging Face repo and revision. Splits are frozen before any candidate run, and session splits are by `session_id`. No synthetic rows in a test split.

## Papers and what each one is for

Full IEEE list is at the end of `docs/reports/T4.A4.docx`, references [1] through [17].

| # | Work | Role for us |
|---|------|-------------|
| 1 | Y Combinator, Requests for Startups, Fall 2026, Multiplayer AI | Motivation. Agent tools still assume one person. |
| 2 | Zhong et al., QMSum, NAACL-HLT 2021 | Supervision for M1 only. 1,808 query-summary pairs. MIT. Not a baseline. |
| 3 | Cemri et al., "Why do multi-agent LLM systems fail?", NeurIPS 2025 Datasets and Benchmarks. arXiv:2503.13657 | The baseline we reproduce. |
| 4 | Ellis and Gibbs, concurrency control in groupware, SIGMOD 1989 | Why OT is the alternative we did not take. |
| 5 | Shapiro et al., conflict-free replicated data types, SSS 2011 | Why the document can converge without a lock. |
| 6 | Nicolaescu et al., Yjs, GROUP 2016 | The CRDT we use for the document. |
| 7 | Wu et al., AutoGen, 2023 | Runtime reference. Agents coordinate under one supervisor. |
| 8 | Lewis et al., BART, ACL 2020 | Surveyed for summarization. Not the M1 plan. |
| 9 | Chung et al., instruction-tuned models (Flan-T5), JMLR 2024 | Surveyed. Not the M1 plan. |
| 10 | Hu et al., LoRA, ICLR 2022 | How the generator arms train without a full fine-tune. |
| 11 | He et al., DeBERTaV3, ICLR 2023 | Planned encoder family for M2. |
| 12 | Hong et al., MetaGPT, ICLR 2024 | Runtime reference, and one of the frameworks inside the MAST traces. |
| 13 | LangGraph documentation | The plan, act, observe loop (PR #6). |
| 14 | CrewAI documentation | Surveyed multi-agent framework. Not our runtime. |
| 15 | Warner et al., ModernBERT, 2024 | Extractive control for M1 and a pairwise encoder for M3. |
| 16 | Yang et al., Qwen3 technical report, 2025 | LoRA generator arms. |
| 17 | Zhu et al., MultiAgentBench, 2025 | Fallback baseline only, if MAST reproduction misses. Inference only. |

### MAST numbers to quote exactly

- Paper row: Table 2, **o1 (few shot)**. Accuracy 0.94, recall 0.77, precision 0.833, F1 0.80, Cohen's kappa 0.77, on 1,642 traces.
- Zero-shot in the paper is weaker. If someone asks why the score is off, first check that the judge was o1 few-shot, not zero-shot.
- Hugging Face dataset `mcemri/MAD`, pin `95118ac951421753cf1deb87ddea3b01e693c41b`.
- Taxonomy repo `multi-agent-systems-failure-taxonomy/MAST`, pin `a70542e541b2104ef8fcd785778179e173fb8d70`.
- Prompt file `models/baseline_mast/judge_prompt.txt`, version `mast-judge-v1`, sha256 `6a73fd53d0e559cd0ee131adec530cf11f687f008132ae8c29a3eedff81bca7c`. One user message, no system message. Reference condition: model `o1`, temperature `1.0`.
- Parser `mast-parser-v1.1`. Missing codes stay null. They are not coerced to false. Parse statuses: `ok`, `partial`, `ambiguous`, `empty`, `malformed`.
- Upstream quirk, preserved on purpose: the answer template swaps the names of 3.2 and 3.3 relative to `definitions.txt`. The parser follows the answer template because that is what the judge replies in. Scoring against meaning is the evaluation owner's decision.
- Upstream `parse_responses` matches `yes`/`no` without word boundaries and can misread codes 2.5 and 3.2. `labels_official` keeps that behavior for comparison. Validated labels do not.
- Licence: CC-BY-4.0.

## Data

| Source | What it is | Where | Status |
|--------|------------|-------|--------|
| MAST full file | 1,642 traces. Labels are from an LLM judge, not humans. | `data/mast/hf/MAD_full_dataset.json` (gitignored; script downloads it) | Download script and `STATS.md` on `main` |
| MAST human file | 19 rows, inter-annotator sample. Rounds 1 to 3 use older taxonomies (18, 17, 17 modes). Only 4 rows (`Generlazability`, spelled that way in the file) use the current 14 codes. Do not pool rounds. | `MAD_human_labelled_dataset.json` | Same download |
| Dictionary and taxonomy | Field counts and the 14 definitions | `data/mast/DATA_DICTIONARY.md`, `data/mast/TAXONOMY.md` | On `main` |
| Eval manifest | Frozen link from download to eval | `data/mast/eval_manifest.json` | On `main` |
| QMSum | M1 supervision only | Not downloaded. DAT-11 | Open |
| Pilot sessions | About 30 in-house sessions, event logs only, double annotated, for M2 to M4 | Not collected | After the integration gate |

Observed on the full MAST file (dictionary, not a model result): 7 frameworks (AG2 597, MetaGPT 430, ChatDev 330, Magentic 195, OpenManus 30, AppWorld 30, HyperAgent 30), 5 LLM names (GPT-4o, Claude, Qwen, CodeLlama, GPT-4o-mini), 8 benchmarks. `trace_id` is not unique across frameworks. Top-level keys are `mas_name`, `llm_name`, `benchmark_name`, `trace_id`, `trace`, `mast_annotation`.

Taxonomy families: 1.x specification (1.1 to 1.5), 2.x inter-agent misalignment (2.1 to 2.6), 3.x task verification (3.1 to 3.3). Mode names in `definitions.txt` are the reference. 3.2 there is "Weak Verification" and 3.3 is "No or Incorrect Verification". The judge prompt template uses the opposite names. See the parser note above.

Demo, from the repo root, after `source .venv/bin/activate`:

```bash
python data/scripts/download_mast.py
python data/scripts/eda_mast.py
```

Success line: `QUALITY GATE: all checks passed`. The cleaner keeps all 1,642 rows. Null annotation cells become 0 in that demo script. That coercion is for the EDA quality gate. The judge parser does not do the same thing. Runbook: `docs/demo1-data-pipeline.md`.

## Requirements worth quoting

| ID | Requirement | Test |
|----|-------------|------|
| FR-1 | Up to 8 concurrent participants, one document | Replicas converge |
| FR-2 | Roles enforced | Disallowed actions rejected |
| FR-3 | Agent commands totally ordered | Replay matches state |
| FR-4 | Audit trail: actor, time, target, cause | 100% of scripted actions present |
| FR-5 | Hand-off | New owner recorded |
| FR-6 | Interrupt | Agent halts within 2 seconds in tests |
| FR-7 | Rollback across the five tools | Prior state restored |
| FR-8 | Cloud deployment | Clean deploy and a smoke test. This is the $20 to $40 VM, not the GPU. |
| FR-9 | Two actors redirecting one agent | Conflict event. Target recall at least 95%. |
| AI-1 | MAST o1 few-shot | Within the tolerances above |
| AI-3 | M1 bake-off | ROUGE-L at least 28.2 |
| AI-4 | M2 | macro-F1 at least 0.75 |
| AI-5 | M3 | macro-F1 at least 0.70 and safer than last-writer-wins |
| AI-8 | Failure analysis | At least 50 failures tagged with the MAST taxonomy |
| DR-1 | QMSum counts match the paper | After DAT-11 |
| DR-4 | Splits by session | No row from a test session in train |

Workbook section map: 1.1 background (Ayush), 1.2 requirements and 1.3 deliverables (Pramod), 1.4 technology survey (Manav), 1.5 literature (Pramod), 2.1 data (Naman), 2.2 methodology and 2.3 organization (Shriram; the template numbers WBS as 2.2.4), 2.4 resources (Ayush; template section 2.3), 2.5 schedule (Pramod; template section 2.4). Abstract presentation is 2 points. The pipeline demo is 3 points. Total 15.

## Schedule and money

Critical path, slack 0, in order: freeze the event schema, integration gate, session collection, frozen splits, controlled study, defence. MAST and the M1 bake-off are parallel. A slip there delays a reported number. It does not move the defence.

| Date | Milestone |
|------|-----------|
| 24 Sep 2026 | Progress Report 1 (`docs/reports/T4.A3.docx`) |
| 7 Oct 2026 | Workbook 1 (`docs/reports/T4.A4.docx`) and the integration gate |
| 8 Oct 2026 | Team Meeting 1. Live demo is the data pipeline, not a trained model. |
| 22 Oct 2026 | Progress Report 2 |
| 11 Nov 2026 | Workbook 2 |
| 12 Nov 2026 | Team Meeting 2 |
| 7 Dec 2026 | Final report and slides |
| 8 Dec 2026 | Project presentation |

Gantt colors in the workbook figures: green done, orange in progress, slate planned. The red line is Workbook 1 day.

| Item | Cost |
|------|------|
| University GPU lab, about 60 GPU-hours, adapters only | $0 |
| Open-source stack (Python, PyTorch, Transformers, PEFT, Yjs, React, LangGraph, Postgres, GitHub, Linear) | $0 |
| Cloud VM and managed Postgres so the session service is reachable (FR-8) | $20 to $40 per month |
| OpenAI o1 for the exact MAST few-shot judge | Pay as you go. Keep receipts. |
| Colab | Only if the GPU lab is down |
| MAST data, QMSum | $0. CC-BY-4.0 and MIT. |

Do not name a specific lab GPU unless the workbook in front of the professor does. The safe sentence is "university GPU lab, $0".

## Likely questions

**Why not just use LangGraph or AutoGen?**  
Those coordinate agents under one supervisor. They do not give several humans a shared document, an audit log, interrupt, and rollback. LangGraph is the runtime. The product is the session.

**Why both Yjs and Postgres?**  
Yjs merges the document. The log orders commands and makes replay, interrupt, and rollback possible.

**Is MAST one of your four models?**  
No. The four are catch-up, attribution, arbitration, and routing. MAST is the external baseline.

**Is QMSum the baseline?**  
No. It supervises the catch-up summarizer.

**Have you beaten 0.94?**  
No. 0.94 is the published target. Data, prompt, parser, batch, provenance, and metric code are on `main`. The judge has not been run, and no score has been posted.

**What do you demo today?**  
`download_mast.py` then `eda_mast.py`. Extract, clean, preprocess, quality check. Not the client, and not a trained model.

**What if MAST does not reproduce?**  
Check the prompt hash and the scoring convention before blaming the model. Confirm o1 few-shot. The metric code itself says `mast_binary_label_cells_v1` must be checked against the paper before anyone calls it a reproduction. If it still misses, MultiAgentBench is the fallback, inference only.

**What if the lab machine is wiped mid-training?**  
Adapters only, checkpoints off the machine. The loss is the work since the last checkpoint.

**What about people outside the team?**  
No recruitment outside the team until that question is settled. Internal sessions and synthetic training replays cover the gap. Test sets stay real.

**Where is the critical path?**  
Schema, integration, sessions, frozen splits, study, defence.

## Do not claim

- That M1 through M4 are trained, scored, or have a winner.
- That the MAST judge has been reproduced to 0.94, 0.80, or 0.77.
- That the client or the LangGraph runtime is on `main`. They are open pull requests.
- That the 1,642 MAST labels are human labels. They are LLM-judge labels. The human file has 19 rows.
- That null labels in the judge parser become 0. Only the EDA script does that.
- A paid cloud GPU price, or a specific lab GPU model, unless the workbook on the table says it.
- That synthetic data is in any test split.

## Compute (team truth)

Do **not** budget paid cloud GPU for 298A unless the GPU lab is unavailable.

| Resource | Detail | Cost |
|----------|--------|------|
| GPU lab | University GPU lab access (team has ongoing free access) | $0 |
| LLM APIs | OpenRouter and/or OpenAI / Anthropic / Kiro CLI as needed for MAST judge and prompted arms | pay-as-you-go; keep receipts; no fixed $100–$250 commitment |

Workbook section 2.3 should say training runs in the GPU lab at $0, not invented cloud GPU spend. Colab is fallback only if the GPU lab is unavailable.

## Local commands

```bash
git pull
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# session service
cd session-service && uvicorn app.main:app --reload --port 8000

# model serving
cd serving && uvicorn serve:app --reload --port 8001

# tests (Ayush packages today; Shriram owns root tests/ later)
cd session-service && pytest -q
cd serving && pytest -q
```

Training extras (on the lab GPU host): `pip install -r requirements-models.txt`

---

## Rules for coding agents

Paste the agent briefing from `docs/build-plan.html` § Agent briefing **plus exactly one** build package (one person's Owns list). Hard constraints that always apply:

1. All evaluation through `eval/harness.py` only.
2. Seeds 13, 29, 47; report mean, std, and per-seed values.
3. Pin model weights by repo id **and** commit revision in config.
4. LoRA / encoders only; no full fine-tune above 4B; use `models/common/checkpointing.py`.
5. Splits frozen and committed before candidate runs; session splits by `session_id`.
6. Within a task, shared epochs / max_seq_len / effective_batch_size.
7. Prompted candidates read prompts from committed files only.
8. Result JSON records split, git_sha, model_revision, hardware, peak_vram_gb, wall_clock_min.
9. No browser storage APIs in the client; no network calls outside Compose services.
10. Schema / route / metric changes require an ADR first.

Commit style: `DAT-xx: short imperative summary`  
Prose in repo docs: no em dashes or en dashes.

---

## Milestones (from build plan)

| Date | Deliverable |
|------|-------------|
| 24 Sep | Progress Report 1 |
| 7 Oct | Workbook 1 / integration gate |
| 8 Oct | Team Meeting 1 |
| 22 Oct | Progress Report 2 |
| 11 Nov | Workbook 2 |
| 12 Nov | Team Meeting 2 |
| 7 Dec | Final report + slides |
| 8 Dec | Project presentation |

---

## Questions

Unresolved decisions go in Linear and, if they change an interface, in `docs/decisions/`. Do not leave conflicting copies of ownership or API shape in personal notes — update **this file** so the next pull stays consistent.
