# Multiplayer Agent Sessions

DATA 298A Section 21 Team 4 Topic 4.

A shared live session where several humans and several agents work in one workspace with concurrent edits, hand-off, interruption, and rollback. Four learned models sit on the platform. One published MAST baseline is reproduced separately.

## Team

| Member | Primary area |
|--------|----------------|
| Ayush Gawai | session service, serving, deployment, M1 catch-up summarizer, integration |
| Manav | client, CRDT, M3 merge arbitration |
| Naman Chheda | data, annotation, M2 intent attribution, reports |
| Shriram | agent runtime, tests, M4 decompose and route |
| Pramod | evaluation harness, MAST baseline, protocol |

## Repository

- GitHub: https://github.com/ayushgawai/multiplayer-agent-sessions
- Linear: https://linear.app/data-298a-team-4/team/DAT
- Spec: [docs/build-plan.html](docs/build-plan.html)

## Quick start (local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# session service (OpenAPI: session-service/openapi.json)
cd session-service && uvicorn app.main:app --reload --port 8000

# model serving stubs
cd serving && uvicorn serve:app --reload --port 8001
```

Health checks: `GET http://localhost:8000/healthz` and `GET http://localhost:8001/healthz`.

Regenerate OpenAPI after schema changes:

```bash
cd session-service && PYTHONPATH=. python scripts/export_openapi.py
```

Full stack:

```bash
docker compose -f infra/docker-compose.yml up --build
```

## Tests

```bash
cd session-service && pytest -q
cd serving && pytest -q
PYTHONPATH=. python models/common/check_checkpointing.py
```

## Layout

See the build plan for ownership boundaries. Cross-boundary work is a network call or a committed file format. No shared process memory between owners.

## Progress Report 1 target

Repo pins and CI live, `SessionEvent` frozen with OpenAPI export, M1 candidate configs drafted, downloads and harness owned by teammates.
