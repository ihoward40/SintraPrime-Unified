# ADR-0001 — AI-OS Foundation migration framework

- Status: Proposed (Increment 0 deliverable; awaiting owner acceptance)
- Date: 2026-08-01
- Scope: FOUNDATION IMPLEMENTATION, Increment 0 only
- Supersedes: the Foundation Scoping assertion that the repository has no
  migration mechanism (that finding was made at `maxdepth 3` inside a stale
  feature worktree and is corrected below)

## Context

The Foundation Scoping packet recorded R-1 as blocking: "no migration
framework". Re-inspection from `origin/main` shows that conclusion was wrong in
one direction and right in another.

What exists (verified on `main`):

- `portal/migrations/` — a raw-SQL migration corpus owned by `portal/AGENTS.md`:
  - `portal_schema.sql`
  - `add_evidence_snapshots.sql`
  - `add_audit_records.sql`
  - `add_mission_control_command_ledger.sql`
  - `add_mission_control_run_control_projection.sql`
  - `runtime_schema_baseline.sql` (PostgreSQL runtime baseline, captured
    2026-07-27)
  - `runtime_schema_integrity_2026_07_27.sql` and its `_down.sql` pair
- `portal/scripts/postgresql_bootstrap.py` — the authoritative fresh-bootstrap
  runner. Its own docstring states it "is not an Alembic replacement and does
  not certify upgrades from unknown schemas". It applies a hardcoded
  `MIGRATION_SEQUENCE` and asserts `EXPECTED_TABLES`.
- `portal/scripts/verify_runtime_schema_integrity.py` — applies baseline +
  migration to a target PostgreSQL database and verifies constraints/indexes.
- `portal/database.py::init_db()` — `Base.metadata.create_all`, documented as
  "for testing / first run. In prod use Alembic". `portal/main.py` does **not**
  call it during lifespan.
- Tests create schema via `Base.metadata.create_all` (SQLite and the
  `postgresql-race` CI lane).
- CI (`.github/workflows/ci.yml`) has two database lanes: `postgresql-race`
  (ORM `create_all`) and `postgresql-bootstrap-certification` (raw-SQL
  bootstrap, fails if any test is SKIPPED).
- `portal/AGENTS.md` binds: "Runtime schema migrations live in
  `portal/migrations/` and must include inline DOWN migration comments or a
  separate `_down.sql` file."
- `docs/DATABASE_AUTHORITY.md` is the controlling schema-authority document. It
  states "Alembic status: **Absent.** Migration authority is raw ordered SQL",
  declares model/migration divergence a release blocker, and recommends a future
  increment introduce "versioned migrations (Alembic **or equivalent**)". This
  ADR proposes the "or equivalent" branch of that recommendation. Amending
  `docs/DATABASE_AUTHORITY.md` to record the runner is a follow-up that requires
  separate authorization and is **not** performed by Increment 0.

What does not exist:

- No Alembic (`alembic.ini`, `env.py`, `versions/` are absent).
- No migration ledger. Nothing records which migrations have been applied to a
  given database. `schema_migrations`/`schema_version` exist nowhere in the
  portal (only an unrelated `discord_schema_version` in `core/universe`).
- No deterministic ordering rule; order is hardcoded in one Python tuple.
- No general downgrade path. Exactly one migration has a `_down.sql`.
- No deployment-owned migration step. `deploy-staging.yml` and
  `deploy-production.yml` contain no migration, `psql`, or bootstrap invocation.
  Deployment database bootstrapping is currently unowned.

So the real gap is not "no migration tool". It is **no ledger, no order, no
reversibility, no deployment owner**.

## Decision

Adopt **Option 2 — extend the repository-native mechanism** rather than
Option 1 (Alembic) or Option 3 (a third-party alternative).

Concretely, Increment 0 introduces `portal/scripts/migration_runner.py`, which
adds the three missing properties to the mechanism the repository already uses:

1. **Ledger** — a `schema_migrations` table (`version`, `name`, `checksum`,
   `applied_at`) created on demand.
2. **Deterministic order** — migrations are directories named
   `NNNN_slug/` containing `up.sql` and a mandatory `down.sql`, applied in
   ascending version order. Optional `up.<dialect>.sql` / `down.<dialect>.sql`
   overrides support the PostgreSQL/SQLite split the repository already lives
   with.
3. **Reversibility** — `downgrade()` executes `down.sql` and deletes the ledger
   row in the same transaction. A `down.sql` is required for every migration,
   which encodes the existing `portal/AGENTS.md` rule as executable behavior.

Re-applying a migration whose on-disk `up` script no longer matches the recorded
checksum is refused (fail closed).

### Alternatives considered

**Option 1 — Alembic with a stamped baseline.** Rejected for Foundation.
Reasons: (a) it would introduce a second, competing schema authority next to the
certified raw-SQL bootstrap lane, and the CI bootstrap certification job would
then be testing a path that production no longer uses; (b) autogenerate against
this ORM would produce a very large first revision covering tables that already
exist in three different creation paths, and stamping it correctly requires a
schema-equivalence proof that does not exist yet; (c) Alembic's value is
autogenerate and branching, neither of which the Foundation needs — the AI-OS
tables are new, additive, and hand-writable. Alembic remains a reasonable future
option once a single schema authority exists; this ADR does not foreclose it.

**Option 3 — a different third-party tool** (sqlx-style, yoyo, dbmate).
Rejected: adds a runtime dependency and a second file format for a repository
that already has a working SQL corpus and a hard requirement to run on both
PostgreSQL and SQLite.

## Proposed migration directory

AI-OS migrations, when authorized, go in:

    portal/migrations/ai_os/NNNN_<slug>/up.sql
    portal/migrations/ai_os/NNNN_<slug>/down.sql

This keeps them inside the `portal/migrations/` boundary that `portal/AGENTS.md`
already owns, while isolating them from the legacy flat `.sql` corpus so the
existing bootstrap sequence is untouched. **No such directory is created by
Increment 0.**

## Baseline-stamping strategy

The legacy flat corpus is **not** retro-converted. Instead:

1. `schema_migrations` starts empty on every database.
2. The legacy corpus continues to be applied by
   `portal/scripts/postgresql_bootstrap.py` exactly as today. Nothing about the
   certified bootstrap lane changes.
3. The AI-OS ledger tracks only `portal/migrations/ai_os/*`. Version `0000` is
   reserved and never used, so an empty ledger unambiguously means "no AI-OS
   schema present".
4. Therefore no stamping of pre-existing schema is required, and there is no
   risk of a mis-stamped baseline silently skipping a legacy migration.

This is deliberately narrower than an Alembic baseline stamp: the runner claims
authority only over the schema it created.

## Upgrade procedure

    python portal/scripts/migration_runner.py upgrade \
      --url "postgresql+psycopg2://<user>:<pw>@<host>:<port>/<db>" \
      --root portal/migrations/ai_os

Optional `--target NNNN` applies a prefix of the sequence. Re-running is a
no-op.

## Downgrade procedure

    python portal/scripts/migration_runner.py downgrade \
      --url "postgresql+psycopg2://<user>:<pw>@<host>:<port>/<db>" \
      --root portal/migrations/ai_os --target NNNN

Reverts in descending order down to, but not including, `--target`. Omitting
`--target` reverts every AI-OS migration and leaves only the empty ledger table.

## CI integration proposal (not implemented)

Add a third database lane, `ai-os-migration-reversibility`, that:

1. starts `postgres:16`;
2. runs `portal/tests/test_migration_framework.py` with
   `AI_OS_MIGRATION_TEST_POSTGRES_URL` set;
3. fails if any test is SKIPPED, mirroring the existing
   `postgresql-bootstrap-certification` job's anti-skip guard;
4. uploads the run log as an artifact.

The existing `postgresql-race` and `postgresql-bootstrap-certification` lanes
are unchanged.

## Deployment compatibility analysis

- `deploy-staging.yml` and `deploy-production.yml` perform no schema work today.
  Introducing AI-OS tables therefore requires an explicit deployment decision:
  either add a gated migration step, or continue to apply schema out of band.
  This is unresolved and is raised as a risk, not silently assumed.
- `portal/database.py::init_db()` is not called at startup, so adding AI-OS ORM
  models will not cause implicit table creation in a running service.
- The `postgresql-race` CI lane calls `Base.metadata.create_all`. Once AI-OS ORM
  models exist, that lane will create AI-OS tables from the ORM while the
  migration runner would create them from SQL. Those two definitions must be
  proven equivalent by a parity test in the increment that introduces them
  (this is the same class of drift that
  `portal/tests/test_postgresql_bootstrap_schema_authority.py` already guards
  for UUID/VARCHAR foreign keys).

## Consequences

- The repository gains reversibility and a ledger without gaining a second
  schema authority.
- AI-OS schema is quarantined from the legacy corpus and can be fully removed by
  a single `downgrade` invocation.
- If Alembic is later adopted repository-wide, the AI-OS ledger is small,
  self-contained, and convertible.
- Retention behavior is explicitly out of scope: `RETENTION_POLICY_PENDING`. The
  runner creates no scheduled job and performs no destructive cleanup.
