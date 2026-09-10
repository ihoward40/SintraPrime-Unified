# SINTRAPRIME DEFICIENCY REGISTER

## P0 — CRITICAL

### SP-DEF-001: Schema/Model UUID Drift (Mission Control)
- **Subsystem:** persistence / mission-control
- **Classification:** BROKEN
- **Description:** ORM model `MissionControlCommand.tenant_id` is `String(36)` but SQL migration creates it as `UUID`. PostgreSQL rejects the query: `operator does not exist: uuid = character varying`. Mission Control command ledger cannot function on PostgreSQL.
- **Evidence:** portal/models/mission_control_command.py:30 (`String(36)`) vs portal/migrations/add_mission_control_command_ledger.sql:9 (`UUID NOT NULL`). Runtime error reproduced: `asyncpg.exceptions.UndefinedFunctionError`.
- **Blocking:** Mission Control command persistence on PostgreSQL.
- **Recommended Action:** REPAIR — align ORM model to UUID or migration to String.

### SP-DEF-002: Schema/Model Body/Content Drift (Messages)
- **Subsystem:** persistence / messaging
- **Classification:** BROKEN
- **Description:** ORM model `Message.body` (String) but SQL schema has `content` (String). `content_encrypted` is boolean in SQL but ORM treats it as string. Application-level message creation will fail on PostgreSQL.
- **Evidence:** portal/models/message.py (`body: Mapped[str]`) vs portal/migrations/portal_schema.sql (`content VARCHAR NOT NULL`, `content_encrypted BOOLEAN NOT NULL`). Runtime: `column "body" does not exist`.
- **Blocking:** Application-level message creation on PostgreSQL.
- **Recommended Action:** REPAIR — align ORM model column names to SQL schema.

## P1 — BLOCKING

### SP-DEF-003: Migration Chain Ordering
- **Subsystem:** persistence / migrations
- **Classification:** BROKEN
- **Description:** Migration files reference tables created by later files. `add_audit_records.sql` requires `evidence_snapshots` (created by `add_evidence_snapshots.sql`). No ordering enforcement. `runtime_schema_integrity_2026_07_27.sql` references columns that don't exist in the base schema.
- **Evidence:** psql execution of migrations out-of-order produces `ERROR: relation does not exist`. 6 migration ordering failures observed.
- **Blocking:** Clean PostgreSQL bootstrap from empty database.
- **Recommended Action:** REPAIR — reorder migrations, add dependency checks, or adopt alembic.

### SP-DEF-004: Default Config Uses SQLite
- **Subsystem:** configuration
- **Classification:** PARTIALLY_WORKING
- **Description:** `.env` sets `DATABASE_URL=sqlite+aiosqlite`. PostgreSQL credentials fail (`portal:portal@localhost:5432` — password auth failure). SQLite hides PG-specific defects.
- **Evidence:** portal/config.py default, .env content. `set_config()` function not available on SQLite.
- **Blocking:** PostgreSQL is not the tested default path.
- **Recommended Action:** REPAIR — make PostgreSQL the default; document SQLite as dev-only.

### SP-DEF-005: Alembic Not Wired
- **Subsystem:** persistence / migrations
- **Classification:** MISSING
- **Description:** `portal/alembic/` directory exists with `versions/` (empty, 0 files). Alembic is not configured or connected to the migration process.
- **Evidence:** `ls portal/alembic/versions/*.py` → 0 files. Migrations are hand-rolled SQL.
- **Blocking:** No automated migration management.
- **Recommended Action:** DEFER — adopt in R1B if migration chain is repaired.

### SP-DEF-006: No Smoke Runner
- **Subsystem:** repository-automation
- **Classification:** MISSING
- **Description:** No `sintraprime_smoke` or equivalent exists (per §30).
- **Evidence:** `find . -name "*smoke*" -not -path "*/node_modules/*"` → 0 results in portal/.
- **Blocking:** No quick startup/integration health check.
- **Recommended Action:** IMPLEMENT in R1.

### SP-DEF-007: Governance Engine Disconnected
- **Subsystem:** governance
- **Classification:** DISCONNECTED
- **Description:** `GovernanceEngine` (risk/approval/audit) has zero callers outside `governance/`. Not imported by any router, middleware, or service. Documented but not enforced at runtime.
- **Evidence:** `grep -rln "GovernanceEngine" --include="*.py" portal/ agents/ core/` → 0 results.
- **Blocking:** No governance enforcement on agent actions.
- **Recommended Action:** REPAIR — wire into middleware or agent execution path.

## P2 — MAJOR

### SP-DEF-008: Provider Registry Mock-Only
- **Subsystem:** providers
- **Classification:** STUB_ONLY
- **Description:** `provider_registry.py` returns mock providers. Header: "no external providers are connected." All providers marked `mock_only: True`.
- **Evidence:** portal/services/orchestration/provider_registry.py:18-48.
- **Blocking:** No real provider invocation possible.
- **Recommended Action:** DEFER — implement in R1E.

### SP-DEF-009: Orchestrator In-Memory Only
- **Subsystem:** workflow
- **Classification:** STUB_ONLY
- **Description:** `RUNS: dict[str, dict] = {}` — no database persistence. Header: "Deterministic mock orchestration coordinator." No restart recovery.
- **Evidence:** portal/services/orchestration/orchestrator.py:21.
- **Blocking:** Orchestration state lost on restart.
- **Recommended Action:** DEFER — implement in R2.

### SP-DEF-010: Event Hub Isolated
- **Subsystem:** events
- **Classification:** DISCONNECTED
- **Description:** `core/universe/event_hub/` (644-line test) not imported by portal, agents, or runtime services.
- **Evidence:** No imports found outside `core/`.
- **Blocking:** No event-driven agent activation.
- **Recommended Action:** DEFER — integrate in R1D.

### SP-DEF-011: JWT Key Too Short
- **Subsystem:** security
- **Classification:** PARTIALLY_WORKING
- **Description:** HMAC key is 28 bytes (< 32 recommended by RFC 7518). Works but produces `InsecureKeyLengthWarning`.
- **Evidence:** `jwt.api_jwt.py:147: InsecureKeyLengthWarning`
- **Blocking:** Security audit concern; not a runtime blocker.
- **Recommended Action:** REPAIR — rotate to 32+ byte key.

### SP-DEF-012: Two Stale Portal Test Imports
- **Subsystem:** testing
- **Classification:** BROKEN
- **Description:** `test_mythos_brain_integration.py` imports `PolicyEnforcementPoint` (doesn't exist). `test_pr_263_remediation.py` imports `MemoryEntry` from wrong module.
- **Evidence:** pytest --collect-only errors at collection.
- **Blocking:** 2 test files cannot be collected.
- **Recommended Action:** REPAIR — fix imports or remove stale tests.

### SP-DEF-013: Outbox Model Without Service
- **Subsystem:** messaging
- **Classification:** STUB_ONLY
- **Description:** `mission_control_outbox.py` model exists. No outbox service processes it. Only consumer is `mythos_brain.py` (which has stale imports).
- **Evidence:** `grep -rln "MissionControlOutbox" portal/services/` → only mythos_brain.py.
- **Blocking:** No transactional outbox processing.
- **Recommended Action:** DEFER — implement in R1D.

## P3 — MODERATE

### SP-DEF-014: Collect Ignore Glob Excludes Most Tests
- **Subsystem:** testing
- **Classification:** PARTIALLY_WORKING
- **Description:** Root conftest `collect_ignore_glob` excludes `portal/*`, `agents/*`, `core/*`, `memory/*`, `orchestration/*`, etc. Default CI lane runs only 26 files (Tier 1). 134 test files deferred.
- **Evidence:** conftest.py:48-125.
- **Blocking:** No portal/agent/event integration tests in default CI.
- **Recommended Action:** IMPLEMENT — unlock test lanes after fixing dependencies.

### SP-DEF-015: OmniBrain = Docs Only
- **Subsystem:** memory
- **Classification:** DOCS_ONLY
- **Description:** No OmniBrain code exists. Only planning documents reference it.
- **Evidence:** docs/planning/*.md only.
- **Blocking:** No OmniBrain functionality.
- **Recommended Action:** DEFER — implement in R3.

### SP-DEF-016: Channels Disconnected
- **Subsystem:** messaging
- **Classification:** DISCONNECTED
- **Description:** `channels/` has Slack/Discord adapters not integrated into runtime.
- **Evidence:** No imports from portal or agents.
- **Blocking:** No external channel integration.
- **Recommended Action:** DEFER — integrate in R4.

### SP-DEF-017: Workflow Runtime Not on Main
- **Subsystem:** workflow
- **Classification:** MISSING
- **Description:** `workflow_runtime/` only exists on feature branch `feat/governed-workflow-runtime` (PR #275, unmerged).
- **Evidence:** Branch inspection; not in origin/main.
- **Blocking:** No durable governed workflow execution.
- **Recommended Action:** DEFER — merge or reimplement in R2.

### SP-DEF-018: MC Run Control Not Verified
- **Subsystem:** mission-control
- **Classification:** PRESENT_BUT_UNVERIFIED
- **Description:** Run control models and routes exist. No evidence of actual pause/resume/cancel operations working.
- **Evidence:** Models exist; service file exists; no runtime proof.
- **Blocking:** No verified run control.
- **Recommended Action:** TEST — verify in R1G.
