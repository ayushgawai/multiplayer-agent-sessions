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
uvicorn session_service.app.main:app --app-dir session-service --reload --port 8000
# in another shell
uvicorn serving.serve:app --reload --port 8001
```

Health checks: `GET http://localhost:8000/healthz` and `GET http://localhost:8001/healthz`.

Full stack (when Compose services are wired):

```bash
docker compose -f infra/docker-compose.yml up
```

## Layout

See the build plan for ownership boundaries. Cross-boundary work is a network call or a committed file format. No shared process memory between owners.

## Progress Report 1 target

Repo pins and CI live, `SessionEvent` frozen with OpenAPI export, M1 candidate configs drafted, downloads and harness owned by teammates.
