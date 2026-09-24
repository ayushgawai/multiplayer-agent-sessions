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
| **Manav** | `client/`, `crdt-server/`, `models/m3_arbitration/`, `eval/configs/m3-*.yaml`, `docs/slides/` | session-service internals, `agent-runtime/`, `data/`, `eval/harness.py` |
| **Naman Chheda** | `data/`, `tools/annotator/`, `models/m2_intent/`, `eval/configs/m2-*.yaml`, `docs/reports/` | `session-service/`, `client/`, `agent-runtime/`, `eval/harness.py` |
| **Shriram** | `agent-runtime/`, `tests/`, `models/m4_routing/`, `eval/configs/m4-*.yaml`, `docs/verification/` | `client/`, session-service internals, `data/`, `eval/harness.py` |
| **Pramod** | `eval/` (exclusive except each person's configs), `models/baseline_mast/`, `docs/protocol.md`, `docs/failure-analysis.md` | other training scripts, services, `client/` |

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
| Progress Report draft Parts A–D | Ayush (scaffold) | Done — teammates fill `[TBD]` |
| MAST + QMSum downloaded + STATS.md row counts | Naman | Open |
| Harness runs one candidate end to end | Pramod | Open |
| Configs m2 / m3 / m4 / baseline (16 files) | Naman, Manav, Shriram, Pramod | Open |
| Meeting minutes times / attendance | Team | Open — fill Part B `[TBD]` |

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

**Last updated:** 2026-09-23 (Manav)

- `main` has repository skeleton, requirements + lock, CI, session service (in-memory) + OpenAPI, serving stubs, M1 configs, checkpointing helper, Compose files, ADR-001, Progress Report draft.
- Session persistence is still **in-memory** (Postgres/Redis next for Ayush).
- No training runs yet (needs QMSum/split + harness + GPU).
- No client, agent-runtime, harness, or public data downloads in repo yet.

When you finish a feature, add one bullet here under your name and bump **Last updated**.

### Ayush
- Foundation through Progress Report scaffold (see git log DAT-1…).

### Naman
- (none yet)

### Manav
- MAST 07 (DAT-31): Locked the judge prompt (mast-judge-v1) so it matches the upstream
  MAST file exactly. Branch: dat-31-mast-judge-prompt.
- MAST 08 (DAT-32): Built a parser (mast-parser-v1) that reads the judge reply, marks
  whether parsing worked, and keeps the raw text. Branch: dat-32-mast-judge-parser.
- MAST 09 (DAT-33): Built a local HTML viewer to spot disagreements and parse problems.
  Branch: dat-33-mast-result-viewer.
- M3 configs (DAT-40): Drafted four config files (m3-a through m3-d) for the bake-off.
  Branch: dat-40-m3-configs.
- Still open: Need approval to keep files under models/baseline_mast/, agreement on the
  ADR-002 prediction record shape, and clarity on labels 3.2 / 3.3. Client work not
  started yet.

### Shriram
- (none yet)

### Pramod
- (none yet)

---

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

Training extras (GPU hosts only): `pip install -r requirements-models.txt`

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
