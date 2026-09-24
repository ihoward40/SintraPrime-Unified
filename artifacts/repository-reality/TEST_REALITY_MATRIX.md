# Test Reality Matrix

**Generated:** 2026-08-08
**Commit:** e2ada66e
**Default CI lane (Tier 1):** 556 passed / 7 failed / 563 total

---

## Tier 1 (tests/ — default CI lane)

| Test Module | Unit | Real DB | Real Router | Real Service | Persistence | Restart | Confidence |
|---|---|---|---|---|---|---|---|
| test_credit_command_center | ✅ | SQLite | ❌ | ✅ | SQLite | ❌ | MODERATE |
| test_governed_inference | ✅ | SQLite | ❌ | ✅ | SQLite | ❌ | MODERATE |
| test_chat_agent_governed | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | LOW |
| test_fcra_reinvestigation | ✅ | SQLite | ❌ | ✅ | SQLite | ❌ | MODERATE |
| test_deadline_evidence | ✅ | SQLite | ❌ | ✅ | SQLite | ❌ | MODERATE |
| test_legal_authority_* | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | LOW |
| test_matter_export_* | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | LOW |
| test_scheduler_queue | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | LOW |
| test_audit_correlation | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | LOW |

7 tests FAILED: all `asyncpg.exceptions.InvalidPasswordError` — PG auth fails against local instance with default credentials. These are environment failures, not code failures.

## Tier 2 (portal/tests/ — excluded by conftest ignore_glob)

| Test Module | Unit | Real DB | Real Router | Real Service | Persistence | Restart | Confidence |
|---|---|---|---|---|---|---|---|
| test_auth | ✅ | SQLite | ✅ | ✅ | SQLite | ❌ | MODERATE |
| test_app_startup | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | MODERATE |
| test_admin_dashboard | ✅ | SQLite | ✅ | ✅ | SQLite | ❌ | LOW (4 fail: 401 staleness) |
| test_documents | ✅ | SQLite | ✅ | ✅ | SQLite | ❌ | MODERATE |
| test_cases | ✅ | SQLite | ✅ | ✅ | SQLite | ❌ | MODERATE |
| test_orchestration_api | ✅ | SQLite | ✅ | ✅ | SQLite | ❌ | LOW (9 fail) |
| test_voice_commands | ✅ | SQLite | ✅ | ✅ | SQLite | ❌ | MODERATE |
| test_jurisdictions_api | ✅ | SQLite | ✅ | ✅ | SQLite | ❌ | STALE (42 fail: unauthenticated calls) |

**Portal suite executed directly (bypassing ignore_glob, excluding 2 broken files): 66 FAILED / 5 ERROR.**

**Failure classification (PRE_EXISTING, not introduced by R0):**
- **41/66 = stale auth tests**: `assert 401 == 200/404/403/201` — tests call endpoints without tokens, but the app now correctly enforces authentication. The app is MORE secure than these tests assume. The tests were written before auth hardening.
- **~8 = signature drift**: e.g., `get_current_user() missing 1 required positional argument: 'request'` — tests call helpers with outdated signatures.
- **5 ERROR = test_runtime_schema_integrity**: migration checks fail against the current schema (consistent with SP-DEF-003 migration ordering).
- Remaining: mixed assertion drift (e.g., jurisdictions expecting 404 unauthenticated).

**134 test files excluded by conftest `collect_ignore_glob`.** Confidence per module above reflects direct execution.

## Tier 3-5 (agents/, core/, memory/, orchestration/, channels/ — all excluded)

All deferred. Zero runtime confidence.

## Key Concerns

1. **All Tier 1 tests use SQLite** — no Tier 1 test exercises PostgreSQL.
2. **Portal tests (Tier 2) are the highest-value tests** but are excluded from default CI.
3. **2 portal tests have stale imports** (test_mythos_brain_integration, test_pr_263_remediation).
4. **No integration tests exist** for the full HTTP → auth → service → PG → audit path.
5. **No provider invocation tests** (all providers are mock).
6. **No agent execution tests** (no execution harness).
