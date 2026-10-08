# Team context — Multiplayer Agent Sessions

**DATA 298A · Section 21 · Team 4 · Topic 4**  
**Repo:** https://github.com/ayushgawai/multiplayer-agent-sessions  
**Linear:** https://linear.app/data-298a-team-4/team/DAT  
**Spec:** [docs/build-plan.html](docs/build-plan.html)

Everyone (and every coding agent) should read this file after `git pull` before changing code. Update this file in the same PR when ownership, status, or contracts change.

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
- **Not on `main` yet:** React client and Yjs (PRs #12–#14), LangGraph runtime (PR #6), `eval/harness.py`, QMSum, M2/M4 configs, ADR-003.

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
