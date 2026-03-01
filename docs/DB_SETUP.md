# Database Setup (Production-Ready)

## Core Principles
- Always manage schema with Alembic migrations.
- Avoid runtime `create_all()` in production (`DB_AUTO_CREATE=0`).
- Use connection pool settings for PostgreSQL under load.
- Keep a rollback path for every migration.

## Required Environment
- `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/vigil`

## Optional Pool Tuning
- `DB_POOL_SIZE=10`
- `DB_MAX_OVERFLOW=20`
- `DB_POOL_TIMEOUT=30`
- `DB_POOL_RECYCLE=1800`
- `DB_ECHO=0`

## Migration Workflow
```bash
python -m alembic upgrade head
python -m alembic current
```

Current head revision:
- `20260301_03`

## Incident Table Hardening
- Indexed for hot queries:
  - `ix_incidents_timestamp`
  - `ix_incidents_camera_timestamp`
  - `ix_incidents_status_timestamp`
  - `ix_incidents_type_timestamp`
- Data constraints in ORM model:
  - `confidence` in `[0, 100]`
  - `acknowledged` in `{0, 1}`
  - `status` in `{active, acknowledged, dispatched, resolved}`

Constraint rollout notes:
- `ck_incidents_status_enum` is applied via Alembic for non-SQLite engines.
- SQLite local/dev keeps parity when schema is created from ORM metadata.

## Operational Advice
- Run daily backups for production DB.
- Test migrations in staging before production.
- Monitor slow queries and index hit rate.
