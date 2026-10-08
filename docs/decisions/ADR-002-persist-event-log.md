# ADR-002: Persist SessionEvent log in SQL; fan-out over Redis

- Status: Accepted
- Date: 2026-10-06
- Owners: Ayush Gawai

## Context

Progress Report 1 froze the HTTP/WebSocket contracts (ADR-001) on an in-memory store.
Workbook 1 / Team Meeting 1 need durable sessions, gapless monotonic `seq`, role checks,
and live event fan-out so client and runtime can integrate.

## Decision

1. Persist `sessions`, `participants`, and append-only `events` via SQLAlchemy.
2. Default local/CI URL is SQLite in-memory (`DATABASE_URL`). Compose/production uses
   Postgres 16 (`postgresql+psycopg://...`) without changing route shapes.
3. Allocate `seq` inside a transaction with a row lock on the session (`SELECT ... FOR UPDATE`).
4. Event rows are never UPDATE-d. Rollback DELETEs rows with `seq > to_seq` and resets `next_seq`.
5. Rejected human writes (unknown participant or observer role) are still appended as
   `type: rejected` and are not applied as the attempted type.
6. Publish each appended event on Redis channel `session:{session_id}` when `REDIS_URL` is set;
   otherwise use in-process subscribers so tests and single-process runs still stream.
7. `app/replay.py` rebuilds a snapshot from events alone; join and rollback responses use it.
8. OpenAPI paths and schemas from ADR-001 stay unchanged.

## Consequences

- Teammates keep coding against `session-service/openapi.json`.
- CI needs no Docker; Compose brings up Postgres and Redis for full-stack runs.
- Schema or route changes still require a new ADR.
