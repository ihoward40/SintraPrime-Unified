# CI-BASELINE-RECOVERY — Phase 2A Certification: PostgreSQL FK Type Consistency

**Branch:** `chore/ci-baseline-recovery`
**Prior checkpoint:** `e93a052eb828b1b30715d35274ef105d4d3ced43` (Phase 1 —
root-cause classification, no code changes)
**Scope:** Category A only — the UUID vs. VARCHAR(36) foreign-key type
mismatch identified in Phase 1. No Category B, C, or D work performed.

## Exact changed columns

All 7 changes are in `portal/models/orchestration.py`, switching the
declared SQLAlchemy column type from `UUID(as_uuid=True)` to `String(36)`
for columns that are foreign keys into `tenants.id` or `users.id` (both of
which are — and remain — `String(36)` in `portal/models/user.py`):

| Class | Column | Before | After |
|---|---|---|---|
| `OrchestrationRun` | `tenant_id` | `UUID(as_uuid=True)` | `String(36)` |
| `OrchestrationRun` | `created_by` | `UUID(as_uuid=True)` | `String(36)` |
| `ApprovalRequest` | `principal_id` | `UUID(as_uuid=True)` | `String(36)` |
| `OrchestrationLinkage` | `tenant_id` | `UUID(as_uuid=True)` | `String(36)` |
| `PrincipalAuthority` | `tenant_id` | `UUID(as_uuid=True)` | `String(36)` |
| `PrincipalAuthority` | `user_id` | `UUID(as_uuid=True)` | `String(36)` |
| `MemoryEntry` (table `memory_vault`) | `tenant_id` | `UUID(as_uuid=True)` | `String(36)` |

**Nothing else was changed.** In particular:

- `tenants.id` and `users.id` themselves (`portal/models/user.py`) were
  **not** touched — they remain `String(36)`, per the explicit instruction
  to fix the dependent columns to the existing schema authority rather
  than converting the parent IDs.
- Every *internal* orchestration-to-orchestration foreign key (e.g.
  `OrchestrationNode.run_id → orchestration_runs.id`,
  `OrchestrationLinkage.event_id → orchestration_events.id`,
  `BudgetUsage.run_id → orchestration_runs.id`) was left as
  `UUID(as_uuid=True)` on both sides — these were never mismatched (both
  the primary keys of orchestration-domain tables and their internal FKs
  are consistently UUID-to-UUID) and are out of this fix's scope.

## Inspection performed before editing (per instruction)

1. **Read the full `portal/models/orchestration.py`** to confirm exactly
   which columns cross-reference `tenants.id`/`users.id` vs. which are
   purely internal to the orchestration domain (UUID-to-UUID, correct
   as-is).
2. **Searched for existing Alembic/raw-SQL migrations** referencing these
   tables. Found `portal/migrations/add_adaptive_orchestration_domain.sql`,
   which independently declares the same columns with the same
   `UUID ... REFERENCES tenants(id)` pattern — i.e. the raw-SQL migration
   has an identical, pre-existing inconsistency with `tenants.id`'s actual
   type. **This file is not part of `MIGRATION_SEQUENCE`** (confirmed via
   `portal/tests/test_postgresql_bootstrap_schema_authority.py::
   test_authoritative_migration_sequence_is_ordered`, which enumerates the
   five migrations that *are* authoritative — this one is not among them),
   so it is not applied by any certified bootstrap path and was left
   untouched. **Flagged as a related, out-of-scope finding** (see below) —
   not fixed in this pass since instructions were to fix only the ORM
   model, and this file is dead/unused from the perspective of the tested
   bootstrap flow.
3. **Confirmed both failing jobs operate purely on `Base.metadata` (the
   ORM), never the raw-SQL migrations**:
   - `postgresql-race`'s equivalent test
     (`test_postgresql_race_prepare_schema_create_all_path_executes`)
     drops/recreates a bare `public` schema and runs only
     `Base.metadata.create_all()` — no raw SQL migration is applied first.
   - `postgresql-bootstrap-certification`'s failing test
     (`test_postgresql_orm_foreign_key_column_types_are_internally_consistent`)
     inspects only `Base.metadata.tables` — comparing each FK column's
     type against its *referred* column's type, both read from the same
     ORM metadata object.

   This confirms the correct, narrowly-scoped fix target is exactly the
   ORM model — not the raw-SQL migration, and not `tenants.id`/`users.id`.
4. **Searched all `portal/` code referencing the affected model classes**
   (`OrchestrationRun`, `ApprovalRequest`, `OrchestrationLinkage`,
   `PrincipalAuthority`, `MemoryEntry`) for any code that would depend on
   these columns actually being Python `uuid.UUID` objects (e.g. `.hex`
   access, `isinstance(x, uuid.UUID)`, `uuid.UUID(...)` reconstruction).
   **None found.** Every consumer (`portal/services/orchestration/persistence.py`,
   `portal/services/memory_vault.py`, `portal/services/principal_brief.py`,
   `portal/services/auditable_trails.py`, `portal/services/log_automation.py`,
   `portal/services/remediation_service.py`) already treats these fields
   as plain strings, consistent with their existing `Mapped[str]` /
   `Mapped[str | None]` type hints. This confirms the type-level change is
   safe.

## Migration impact

**No live database currently has these tables in their old (mismatched)
form** — the schema-creation failure (`asyncpg.exceptions.DatatypeMismatchError`)
means no environment has ever successfully created these tables against
real PostgreSQL with the old `UUID(as_uuid=True)` declaration. There is
therefore **no existing production/staging data to migrate** for this
specific defect — the tables simply never came into existence with the
broken types. No new Alembic migration was required or written for this
fix; the corrected ORM model will simply succeed where the schema-creation
step previously failed at `Base.metadata.create_all()` time.

The one related-but-out-of-scope finding (`add_adaptive_orchestration_domain.sql`
having the same latent inconsistency) is **not exercised by any tested
path** and was left untouched, per the explicit instruction to fix the
Category A defect only where it actually manifests. It is flagged here so
a future maintainer doesn't rediscover it from scratch.

## Test results

### 1. FK consistency guard test (pure metadata inspection, no live DB required)

```
python -m pytest portal/tests/test_postgresql_bootstrap_schema_authority.py::test_postgresql_orm_foreign_key_column_types_are_internally_consistent -v
→ 1 passed
```

Before the fix, this test failed with 7 enumerated mismatches (see Phase 1
report). After the fix: zero mismatches, `assert mismatches == []` passes.

### 2. Real PostgreSQL certification (isolated, throwaway container)

A dedicated, isolated `postgres:16-alpine` Docker container (matching the
exact image used by CI's `postgresql-race`/`postgresql-bootstrap-certification`
jobs) was started on a private port (`55432`, distinct from both the
native Windows PostgreSQL 18 service on 5432 and an unrelated
pre-existing `sintraprime-cah-p1` container on 5441 — neither of which
were touched). The container was destroyed after testing.

```
# Exact equivalent of postgresql-race CI's schema-creation step:
python -m pytest portal/tests/test_postgresql_bootstrap_schema_authority.py::test_postgresql_race_prepare_schema_create_all_path_executes -v -m postgresql
→ 1 passed

# Full postgresql-bootstrap-certification test file (15 tests, all raw-SQL
# bootstrap + ORM create_all + live-catalog + CRUD/UUID-binding tests):
python -m pytest portal/tests/test_postgresql_bootstrap_schema_authority.py -v -m postgresql
→ 15 passed in 110.09s
```

Before the fix, both `test_postgresql_race_prepare_schema_create_all_path_executes`
and the file-level `test_postgresql_orm_foreign_key_column_types_are_internally_consistent`
failed against this same real-PostgreSQL setup (reproducing the exact
`DatatypeMismatchError` seen in CI). After the fix: all 15 tests in the
file pass, including the ones that were already passing before (the raw-SQL
bootstrap tests, live-catalog constraint checks, and real ORM CRUD/UUID-
binding tests were never affected by this defect and continue to pass).

### 3. Regression: orchestration API test file

```
python -m pytest portal/tests/test_orchestration_api.py -v
→ 9 failed, 2 passed  (IDENTICAL before and after the fix — confirmed via
  git stash / stash pop A-B comparison)
```

These 9 failures are **pre-existing** (Category B — the auth regression
returning 401 instead of the expected 200 — documented in the Phase 1
classification report) and are **unrelated to and unaffected by** this
Category A fix. Confirmed byte-for-byte identical failure set with and
without the fix applied.

### 4. Regression: full default test suite (matches CI's `test` job invocation)

```
python -m pytest -q   (bare invocation, using pytest.ini's default testpaths)
→ Same 3 pre-existing failures as main tip's `test` job:
  - tests/test_legal_authority_phase_two_b.py::test_phase_2b_api_new_states_comparison_and_ucc_endpoints
  - tests/test_legal_authority_phase_two_c_one.py::test_federal_read_only_api_endpoints
  - tests/test_matter_export_phase_two_c_five.py::test_export_route_returns_hash_headers
```

All three are Category B/C defects documented in Phase 1, **not**
introduced or affected by this Category A fix. Zero new failures.

*(Note: `portal/tests/test_pr_263_remediation.py` has a pre-existing,
unrelated collection error — `ImportError: cannot import name 'MemoryEntry'
from 'portal.models.mission_control_outbox'` — confirmed identical before
and after this fix via stash comparison. Out of scope for Category A.)*

### 5. Lint check on the changed file (exact CI-pinned ruff==0.15.20)

```
ruff check portal/models/orchestration.py
→ 5 pre-existing findings (I001 import order, 4x UP037 quoted-annotation),
  confirmed byte-for-byte identical before and after this fix via stash
  comparison. Zero new findings introduced by this change.
```

These 5 findings are part of Category D (pre-existing lint debt across
`portal/`), explicitly out of scope for this Phase 2A pass and deferred to
the Category D sub-track per the recommended fix order.

## PostgreSQL certification result

**CERTIFIED.** The exact schema-creation path used by both
`postgresql-race` and `postgresql-bootstrap-certification` CI jobs now
succeeds against a real PostgreSQL 16 instance (matching CI's image
exactly), with zero foreign-key type mismatches remaining anywhere in
`Base.metadata`.

## Regression risk assessment (post-hoc, confirmed empirically)

- **Python-level behavior**: no change. All 7 columns were already
  `Mapped[str]`/`Mapped[str | None]` typed and consumed as plain strings
  everywhere in the codebase; switching the underlying SQLAlchemy column
  type from `UUID(as_uuid=True)` (which would have auto-converted to/from
  `uuid.UUID` objects on a real Postgres connection) to `String(36)`
  (plain string round-trip) changes nothing observable to existing
  callers, since no such round-trip has ever successfully occurred against
  real Postgres before this fix (schema creation always failed first).
- **No existing data migration required** — confirmed no environment ever
  had these tables successfully created with the old types.
- **No test regressions** — confirmed via direct git-stash A/B comparison
  across the guard test, the full `postgresql-bootstrap-certification`
  suite, `test_orchestration_api.py`, the full default test suite, and
  ruff on the changed file.

## What was explicitly NOT done in this pass

- Category B (auth regression) — untouched.
- Category C (Postgres-dependent test lacking proper marker/isolation) —
  untouched.
- Category D (repo-wide lint debt, including the 5 pre-existing findings
  in this same file) — untouched.
- `portal/migrations/add_adaptive_orchestration_domain.sql` — left as-is
  (unused by any tested path; flagged, not fixed).
- `tenants.id` / `users.id` — left as `String(36)`, not converted to UUID.
- No push, no PR opened. This work remains local-only on
  `chore/ci-baseline-recovery`, on top of the Phase 1 evidence checkpoint
  `e93a052e`, pending explicit authorization to commit/push/continue.

## Next step

Per the authorized sequence (A → C → B → re-verify shared jobs → D),
Category C (the Postgres-dependent test lacking proper isolation/marking)
is next, followed by Category B (the auth regression, which requires a
design decision before implementation). Awaiting explicit authorization
before proceeding.
