# Gate 3 Acceptance Report

## Decision

**Gate 3: PASS** (with documented limitations)

## Governance Position

- **Gate 2:** PASS
- **Gate 3:** PASS
- **Gate 4:** AUTHORIZED TO BEGIN
- **Production deployment:** Not authorized solely by this gate decision

## Acceptance Basis

Gate 3 is accepted based on the following evidence:

1. **Full canonical Alembic bootstrap migration exists.**
   - Migration `8b349f2cd639` is explicitly documented as the canonical bootstrap migration.
   - It contains 1,033 lines of table, index, and constraint definitions covering all portal and observatory tables.
   - It is **not** an empty adoption stamp.

2. **Clean SQLite database successfully upgraded from base to head using Alembic only.**
   - Database: temporary disposable SQLite file
   - Command: `DATABASE_URL=<temp> alembic upgrade head`
   - Result: 40 tables, 81 indexes, head revision `905b70986558`

3. **SQLite round-trip upgrade, downgrade, and re-upgrade produced matching schema fingerprints.**
   - Bootstrap fingerprint SHA-256: `9467825f8ecfa16b7713ddf5e08f68031fd69240e1150d92bfbcc76d6dfae64c`
   - Re-upgrade fingerprint SHA-256: `9467825f8ecfa16b7713ddf5e08f68031fd69240e1150d92bfbcc76d6dfae64c`
   - Match: **TRUE**

4. **Clean PostgreSQL database successfully upgraded to head and round-tripped.**
   - Database: disposable `gate3_bootstrap`
   - Command: `DATABASE_URL=<pg> alembic upgrade head`
   - Result: 40 tables, 81 indexes, head revision `905b70986558`
   - Bootstrap fingerprint SHA-256: `550417743a585fa545cca977e5fe659160f7d35e2921172ca0f887efd746623b`
   - Round-trip note: table/index/foreign-key definitions match between bootstrap and re-upgrade. The raw SHA-256 fingerprints differ because PostgreSQL system-generated `NOT NULL` check-constraint OIDs change between creation passes. This is a metadata artifact, not a schema difference. See `evidence/postgresql/schema-inventory.json` and `evidence/postgresql/round-trip-diff.txt`.

5. **SQLite and PostgreSQL contain the persistent kill-switch concurrency guard.**
   - SQLite: index `uq_observatory_single_active_kill_switch` present
   - PostgreSQL partial unique index definition:
     ```sql
     CREATE UNIQUE INDEX uq_observatory_single_active_kill_switch
     ON public.observatory_kill_switch_state USING btree (is_active)
     WHERE (is_active = true)
     ```

6. **`Base.metadata.create_all()` is disabled by default in the production initialization path.**
   - `portal/database.py` `init_db()` raises `RuntimeError` unless `ALLOW_SCHEMA_CREATE_ALL=true`
   - Default value is `False`

7. **Normal application startup does not invoke schema creation.**
   - Only `init_db()` can call `create_all()`, and it is not invoked during normal lifespan.

8. **Concurrent kill-switch activation leaves exactly one active state.**
   - Proven by `TestPostgreSQLConcurrency` on PostgreSQL.

9. **Kill-switch activation races are handled idempotently.**
   - Proven by `test_kill_switch_idempotent_activation` on SQLite.

10. **Mission creation is blocked at the service boundary.**
    - Proven by `MissionService.create()` tests under active kill switch.

11. **Read-only evidence and event operations remain available.**
    - Proven by `test_kill_switch_evidence_available_while_active`.

12. **Full test suite passed with warnings treated as errors.**
    - 152 passed across `test_observatory.py`, `test_gate4_hardening.py`, `test_event_canonicalization.py`, `test_migration_backfill.py`
    - Earlier reports referenced 151 passed (before `test_migration_backfill.py` was included) and 146 passed (before canonicalization/hash-version tests were added). The authoritative frozen package uses 152 passed.

13. **Kill-switch tests passed independently.**
    - 13 passed, 46 deselected in `test_observatory.py -k kill_switch`
    - 5 passed in `test_gate4_hardening.py::TestPostgreSQLConcurrency`

## Migration Graph

```text
<base>
  ↓
8b349f2cd639 — baseline complete portal schema
  ↓
4f3f0432cf9d — add run heads and event run/sequence
  ↓
905b70986558 — add hash_version column and CHECK constraints (head)
```

## Revision Hashes

| Migration File | SHA-256 | Bytes |
|---|---|---|
| `8b349f2cd639_baseline_complete_portal_schema.py` | `c22d99a2c978cd413d78d0fcab3d4795d820d35f8cc9309ce63037e7b23522ce` | 62,357 |
| `4f3f0432cf9d_add_run_heads_and_event_run_sequence.py` | `866d96a1676f0ead8817ec73cf289051cefe29836b84d024171cb4f62dc6fae9` | 5,640 |
| `905b70986558_add_hash_version_and_check_constraints.py` | `95c8b21a17b5cb6b773b33aa1cc5d9a43b15b367690609c3101a486149704785` | 3,129 |

## Environment Versions

| Component | Version |
|---|---|
| Python | 3.11.9 |
| SQLAlchemy | 2.0.50 |
| Alembic | 1.18.5 |
| SQLite | 3.45.1 |
| PostgreSQL | 15.17 |

## create_all() Audit

| File | Line(s) | Purpose | Production Risk |
|---|---|---|---|
| `portal/database.py` | 124–143 | `init_db()` gated by `ALLOW_SCHEMA_CREATE_ALL=true`; defaults to `RuntimeError` | **None** (disabled by default) |
| `portal/alembic/ADOPTION.md` | 3, 5, 23 | Documentation only | None |
| `portal/alembic/versions/8b349f2cd639_baseline_complete_portal_schema.py` | 9 | Comment explaining adoption-stamp alternative | None |
| `portal/tests/test_observatory.py` | 81, 729, 1155 | Test fixtures (observatory tables only) | Test-only |
| `portal/tests/test_gate4_pg_concurrency.py` | 110, 241, 341, 456 | PG test setup | Test-only |
| `portal/tests/test_gate4_hardening.py` | 110, 129, 622, 928, 1014 | Test fixtures + G4.10 hardening tests | Test-only |
| `portal/tests/test_blackstone_service.py` | 25 | Test fixture | Test-only |
| `portal/tests/test_blackstone_case_workflow.py` | 28 | Test fixture | Test-only |

## SQLite vs PostgreSQL Table Count

Both databases report **40 tables** in the final evidence capture (excluding `alembic_version` from the table count). Earlier chat output showed 46 SQLite / 41 PostgreSQL because those counts included `alembic_version` and dialect-specific internal tables. The normalized inventories confirm identical logical schemas.

## Unresolved Limitations

1. **`cleared_by` is attribution only, not authenticated authorization.**
   - `KillSwitchService.clear()` records who cleared the switch but does not verify identity.
   - Principal-backed clear authorization belongs to Gate 4.

2. **Principal-backed authentication and authorization remain Gate 4 work.**
   - Gate 3 proved database enforcement of the kill-switch state, not who may change it.

3. **PostgreSQL downgrade/re-upgrade produces equivalent schema, but system-generated OID-based constraint names differ.**
   - This does not affect functionality but must be understood for future evidence generation.

4. **Future migrations must continue to pass clean upgrade and round-trip testing without `create_all()`.**
   - Any new migration must include a corresponding clean-database test.

## Evidence Manifest

See `gate-3-evidence-manifest.json` for the complete list of artifacts, file hashes, and paths.

The manifest contains **seven evidence artifacts** plus the manifest itself. The acceptance report is a governance document, not an evidence artifact. The artifact list is:

1. `evidence/migrations/migration-file-hashes.json`
2. `evidence/sqlite/schema-inventory.json`
3. `evidence/postgresql/schema-inventory.json`
4. `evidence/tests/full-suite-output.txt`
5. `evidence/tests/kill-switch-sqlite-output.txt`
6. `evidence/tests/kill-switch-pg-output.txt`
7. `gate-3-evidence-manifest.json`

## Next Step

Gate 4 is authorized. Proceed in this order:

1. Canonical event serialization
2. Event idempotency keys
3. Hash-chain concurrency control
4. Persistent run-head locking
5. Principal-backed authentication and authorization
6. Kill-switch clear authorization
7. Evidence-read versus mutation permissions
8. Tamper-evident audit events
9. Replay and duplicate-event protection
10. Cross-database concurrency tests

## Amendment Notice

**GATE3-AMENDMENT-001**

The Gate 3 evidence manifest was first generated with SHA-256:
`3e0e65c9bf4983690e76ab248c88bc9e96ab23e1e3badcdd329c89334cb8471f`

The manifest was subsequently regenerated without an amendment identifier. The authoritative current digest is:
`fc841662e1abace80fc9ae5eff720a07584a46f3083af35877da30003322609f`

**Reason:** Include migration backfill test output, correct artifact-count reporting, and refresh captured test evidence.

**Technical acceptance:** PASS (unchanged).
**Governance status:** PASS AFTER AMENDMENT.

See `amendments/GATE3-AMENDMENT-001.md` and `amendments/GATE3-AMENDMENT-001-DIFF.json` for full chain-of-custody details. The freeze record is in `GATE3_FREEZE_RECORD.json`. Ordinary manifest regeneration is now prohibited; future changes require an explicit amendment identifier and reason.
