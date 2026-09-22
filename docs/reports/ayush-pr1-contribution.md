# Ayush contribution notes for Progress Report 1

Use this when assembling `T4.A3.doc`. Naman owns the final report file.

## Part C row (Ayush)

| Member | Issues closed | Labels worked | Key artifact |
|--------|---------------|---------------|--------------|
| Ayush Gawai | DAT-1 through DAT-9 (local Linear ids pending board sync) | infra / model | https://github.com/ayushgawai/multiplayer-agent-sessions |

## Artifacts landed this period

- Repository hygiene, owned directory skeleton, pinned requirements + lock
- GitHub Actions CI (ruff, mypy, pytest)
- Frozen `SessionEvent` + committed `session-service/openapi.json` (ADR-001)
- Serving stubs for m1–m4 with `/healthz` and `/v1/models/{id}/predict`
- M1 candidate configs `eval/configs/m1-a.yaml` … `m1-d.yaml` with HF revision pins
- Shared `models/common/checkpointing.py`, M1 model card scaffold
- `infra/docker-compose.yml` plus Dockerfiles for session-service and serving

## Suggested Part A percentages (Ayush-owned rows only; team should align)

These are starting points for the team table, not final without discussion.

| Item | Planning | Investigation | Complete | Document |
|------|----------|---------------|----------|----------|
| 4.1 Model Proposals (M1) | 100 | 90 | 40 | 30 |
| 4.5 First Model Implementation (M1) | 80 | 40 | 15 | 10 |
| 5 Prototype and System Implementation | 90 | 60 | 25 | 15 |
| 7 Reproducibility (pins, CI, openapi) | 100 | 80 | 50 | 30 |

## Blockers for next period

| Blocker or risk | Impact | Owner | Next action |
|-----------------|--------|-------|-------------|
| QMSum download + m1 split freeze | Blocks M1 bake-off | Naman (+ Ayush consumes) | Run download script, freeze `data/splits/m1_v1/` |
| Harness one-candidate E2E | Blocks PR1 team claim | Pramod | Validate harness against m1 stub or m1-a |
| Postgres event log not yet wired | Session durability | Ayush | Replace in-memory store; keep OpenAPI unchanged |

## Next period outcomes (Ayush)

1. Postgres + alembic event log with monotonic seq
2. Redis WebSocket fan-out
3. Train m1-a on public/seed split once harness and data are ready (needs GPU)
