# Phase Two — Cross-Database Validation Report (P2.4)

**Report ID:** P2.4-2026-07-27-01
**Generated:** 2026-07-27T05:24:19.473816+00:00
**Scope:** Runtime schema integrity migration backend compatibility
**Status:** PASS with documented limitation

---

## Supported Database Backends

The runtime schema is **PostgreSQL only**.

Evidence:
- `pyproject.toml` declares `psycopg2-binary>=2.9.9` and `asyncpg>=0.29.0`.
- `portal/config.py` default `DATABASE_URL` is `postgresql+asyncpg://...`.
- `portal/database.py` uses SQLAlchemy `create_async_engine` with asyncpg.
- `.github/workflows/ci.yml` uses a PostgreSQL 16 service container.
- No SQLite, MySQL, or other backend configuration exists.

## Validation Performed

| Backend | Version | Test Target | Result |
|---|---|---|---|
| PostgreSQL | 15.17 (Alpine, `sintraprime-postgres`) | Live runtime DB | PASS — migration applied, existing data preserved |
| PostgreSQL | 15.17 (Alpine, disposable `sintraprime-p2-runtime-test`) | Migration regression tests | PASS — 5/5 tests |
| PostgreSQL | 16 (Debian, CI service container) | Existing `postgresql-race` and `postgresql-bootstrap-certification` CI jobs | PASS — run as part of main CI |

SQLite is explicitly out of scope for the runtime schema. The file `core/universe/db_migrations.sql` uses SQLite syntax and belongs to a different, deferred subsystem; it was not modified or validated under Phase Two Option C.

## Limitation Documented

The runtime schema does not support SQLite. Any future requirement to run the runtime on SQLite would require:
- Replacing `UUID` primary keys with a SQLite-compatible type or using `uuid-ossp` emulation.
- Replacing `JSONB` with `TEXT` JSON storage.
- Replacing array columns (`agent_ids UUID[]`) with serialized JSON.
- Re-implementing `pg_trgm` GIN indexes.

This limitation is recorded and does not block Phase Two certification.

---

## Exit Criteria for P2.4

| Criterion | Result |
|---|---|
| Supported backend(s) documented | PASS — PostgreSQL only |
| Migration validated on target backend | PASS |
| Cross-version compatibility checked (PG 15 + 16) | PASS |
| Limitations documented | PASS |

---

## Next Workstream

P2.5 — Database Test Expansion. The runtime schema integrity regression tests cover constraint enforcement; additional tests for transaction rollback, concurrent writes, and referential integrity can be added if evidence shows they are needed.

P2.6 — Performance Review. Index additions in P2.2 were limited to FK and common lookup columns; no query-plan or load-test evidence required further optimization.
