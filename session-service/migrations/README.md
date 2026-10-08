# Alembic migrations for session-service.

For local Compose/Postgres:

```bash
cd session-service
DATABASE_URL=postgresql+psycopg://mas:mas@localhost:5432/mas alembic upgrade head
```

SQLite/CI uses `Base.metadata.create_all` on startup (see `app/db.py`) so tests do not
require a migration runner.
