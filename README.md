# Multiplayer Agent Sessions

DATA 298A · Section 21 · Team 4 · Topic 4

Shared live sessions where humans and agents edit one workspace with concurrent edits, hand-off, interruption, and rollback. The platform hosts four task models. A published MAST baseline is reproduced separately for comparison.

## Team

| Member | Primary area |
|--------|----------------|
| Ayush Gawai | Session service, serving, deployment, M1 catch-up summarizer, integration |
| Manav | Client, CRDT, M3 merge arbitration |
| Naman Chheda | Data, annotation, M2 intent attribution, reports |
| Shriram | Agent runtime, tests, M4 decompose and route |
| Pramod | Evaluation harness, MAST baseline, protocol |

## Links

- Repository: https://github.com/ayushgawai/multiplayer-agent-sessions
- Linear: https://linear.app/data-298a-team-4/team/DAT
- Build specification: [docs/build-plan.html](docs/build-plan.html)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd session-service && uvicorn app.main:app --reload --port 8000
cd serving && uvicorn serve:app --reload --port 8001
```

- Session service health: `GET http://localhost:8000/healthz`
- Serving health: `GET http://localhost:8001/healthz`
- OpenAPI: `session-service/openapi.json`

```bash
cd session-service && PYTHONPATH=. python scripts/export_openapi.py
docker compose -f infra/docker-compose.yml up --build
```

## Tests

```bash
cd session-service && pytest -q
cd serving && pytest -q
PYTHONPATH=. python models/common/check_checkpointing.py
```

## Repository layout

Package ownership is exclusive. Interaction across packages is a network call or a committed file format. See `docs/build-plan.html`.
