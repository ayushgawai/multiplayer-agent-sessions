# ADR-001: Freeze SessionEvent and session service OpenAPI

- Status: Accepted
- Date: 2026-09-22
- Owners: Ayush Gawai (proposer), Team 4

## Context

Progress Report 1 requires a frozen `SessionEvent` contract. Manav generates client types from OpenAPI. Shriram builds agent-runtime fixtures from the same schema. Changing the wire format after teammates start coding creates churn and broken integrations.

## Decision

1. `session-service/app/schemas.py` is the source of truth for SessionEvent, actor, causality, labels, and the HTTP request/response models listed in the build plan.
2. `session-service/openapi.json` is exported from the FastAPI app and committed. Regenerated only via `PYTHONPATH=. python scripts/export_openapi.py` inside `session-service/`.
3. Event `type` values on the wire remain lowercase strings (`join`, `instruction`, ...). Python enum member names may use SCREAMING_SNAKE to avoid `str` method name clashes.
4. Persistence for Progress Report 1 is an in-memory store. Postgres and Redis arrive in a follow-up ADR without changing the public route shapes.

## Consequences

- Any change to a schema field, route path, or status code requires a new ADR before the code change.
- Client and runtime owners should generate types and fixtures from the committed `openapi.json`, not from informal notes.
- Catch-up summary on join may be null until M1 serving is wired.
