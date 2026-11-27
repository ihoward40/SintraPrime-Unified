# SINTRAPRIME CAPABILITY REALITY LEDGER

**Generated:** 2026-08-08T06:45Z
**Commit:** e2ada66e
**Base:** origin/main
**Environment:** Windows 10, PostgreSQL 15.17 (Docker 5433), Python 3.11.9 (.venv)

---

## Foundation

### Application Startup
- **Code:** `portal/main.py`, `portal/config.py`
- **Status:** VERIFIED_WORKING
- **Evidence:** FastAPI app imports cleanly, 197 routes registered, lifespan handlers execute. App runs on uvicorn. Health endpoint `/health` returns 200 without auth.
- **Defects:** `portal/config.py` defaults `DATABASE_URL` to `sqlite+aiosqlite` — PostgreSQL not the default. JWT key is 28 bytes (< 32 recommended by RFC 7518).

### Configuration
- **Code:** `portal/config.py`
- **Status:** PARTIALLY_WORKING
- **Evidence:** Pydantic-settings loads from `.env`. Config defaults to SQLite. `.env.example` shows `POSTGRES_PASSWORD=change_me` but the actual `.env` uses sqlite+aiosqlite. No production-secret validation gate (config loads placeholder secrets without error).
- **Defects:** No fail-closed on default secrets.

### Database Bootstrap
- **Code:** `portal/database.py`, `portal/migrations/`
- **Status:** PARTIALLY_WORKING
- **Evidence:** `portal_schema.sql` creates 25 base tables. 13 SQL migration files create 60+ additional tables. No alembic versions (0 files). Alembic directory exists but is not wired. Migrations are hand-rolled SQL files with no ordering enforcement.
- **Defects:** Migration ordering is not dependency-safe. `add_audit_records.sql` runs before `add_evidence_snapshots.sql` and fails (relation not found). `runtime_schema_integrity_2026_07_27.sql` references columns that don't exist in the base schema.

### PostgreSQL
- **Code:** Docker compose (postgres:15-alpine), local PG 18 service
- **Status:** PARTIALLY_WORKING
- **Evidence:** PG 15 container starts on 5433. 70 tables created from full migration chain. Schema/model drift detected: ORM model declares `body` (String), SQL schema has `content` (String). ORM declares `tenant_id` as `String(36)` in MissionControlCommand, SQL has `UUID`.
- **Defects:** Two P1 schema/model drifts discovered. Default config uses SQLite, not PG.

### SQLite Compatibility
- **Status:** PRESENT_BUT_UNVERIFIED
- **Evidence:** `.env` configures `sqlite+aiosqlite`. App starts on SQLite. 556 tests pass on SQLite in the default CI lane. But SQLite hides PG-specific defects (set_config function, UUID type mismatch, FK enforcement differences).

---

## Identity / Security

### Authentication
- **Code:** `portal/auth/jwt_handler.py`, `portal/services/auth.py`
- **Status:** VERIFIED_WORKING
- **Evidence:** JWT access tokens (15-min), refresh tokens (30d). Password hashing via bcrypt. Auth middleware enforced: 401 returned for unauthenticated requests to protected routes. `POST /api/v1/mission-control/commands` → 401 without token.

### Authorization / RBAC
- **Code:** `portal/auth/rbac.py`
- **Status:** VERIFIED_WORKING
- **Evidence:** 7-role hierarchy: SUPER_ADMIN > FIRM_ADMIN > ATTORNEY > PARALEGAL > ACCOUNTANT > CLIENT > VIEWER. Permission validation enforced: `MISSION_COMMAND_CREATE` / `MISSION_COMMAND_READ` checked. `POST /api/v1/mission-control/commands` → 403 "Missing permissions" with wrong permissions.
- **Defects:** Role "admin" rejected — correct role is "SUPER_ADMIN" (good, but API documentation may be misleading).

### Tenant Isolation
- **Code:** `portal/auth/rbac.py`, `portal/database.py`
- **Status:** VERIFIED_WORKING (DB-level)
- **Evidence:** PostgreSQL FK constraints reject cross-tenant message inserts: `CROSS_TENANT: REJECTED`. `set_config('app.current_tenant_id', ...)` called on each session (PG RLS functions).
- **Defects:** RLS functions (`set_config`) don't exist on SQLite — tenant isolation works only on PostgreSQL.

### Secrets Handling
- **Code:** `portal/config.py`
- **Status:** PARTIALLY_WORKING
- **Evidence:** API keys loaded from environment variables. `.env` file present. No hardcoded secrets found in scanned code.
- **Defects:** No production-secret validation gate. Config accepts placeholder values without failing.

---

## Audit / Governance

### Correlation IDs
- **Code:** `portal/auth/correlation.py`
- **Status:** VERIFIED_WORKING
- **Evidence:** Correlation middleware generates `req-*` request IDs on every request. Observed in health endpoint logs: `correlation.request_id_replaced reason=missing request_id=req-xxxx`.

### Audit Records
- **Code:** `portal/models/audit_record.py`, `portal/services/audit_service.py`
- **Status:** PRESENT_BUT_UNVERIFIED
- **Evidence:** Audit model exists. `audit()` function called by MC command service. Integration not tested on PG (audit_records table requires evidence_snapshots table to exist first — ordering bug in migrations).

### Command Ledger
- **Code:** `portal/services/mission_control_command_service.py`
- **Status:** PARTIALLY_WORKING
- **Evidence:** Full implementation: hash-chained receipts (SHA-256), structlog audit, WebSocket notification. Auth middleware enforced. DB layer fails on PG due to schema/model UUID drift (`mission_control_commands.tenant_id` = UUID in SQL, String(36) in ORM model).
- **Defects:** P1: UUID/String(36) drift prevents PG operation. Command guard refuses execution: "Increment One authorizes command recording only, never execution."

### Governance Engine
- **Code:** `governance/governance_engine.py`
- **Status:** DISCONNECTED
- **Evidence:** `GovernanceEngine` class implements risk assessment + approval gates + audit. Zero callers outside `governance/` directory. Never imported by portal, agents, or any runtime service. Only `governance/blackstone/` documentation references it.

### Multi-Tenant Governance
- **Code:** `portal/services/multi_tenant_governance.py`
- **Status:** DISCONNECTED
- **Evidence:** `MultiTenantGovernanceService` uses `policy_engine`. Called only by `platform_hardening.py` and simulation scripts (`phase_7_simulation.py`, `comprehensive_e2e_simulation.py`). Never called by any router or runtime request path.

### Policy Engine
- **Code:** `portal/services/policy_as_code.py`
- **Status:** DISCONNECTED
- **Evidence:** Policy engine used by `multi_tenant_governance.py` which is itself disconnected from runtime. No route or middleware calls `evaluate_action`.

---

## Mission Control

### Backend Routes
- **Code:** `portal/routers/mission_control.py`, `portal/routers/mission_control_commands.py`
- **Status:** PARTIALLY_WORKING
- **Evidence:** 13 routes: `/commands`, `/intents`, `/intents/{id}`, `/intents/{id}/causation-chain`, `/real-time-metrics`, `/run-controls`, `/run-controls/{id}`, `/sigma-gate`. Auth enforced. POST command → 401/403 as appropriate.
- **Defects:** Command creation fails on PG (UUID drift). GET intents returns 405 (method not allowed — only POST exists for submission).

### Run Control
- **Code:** `portal/services/mission_control_run_control_service.py`, `portal/models/mission_control_run_control.py`
- **Status:** MISSING
- **Evidence:** Models exist. Service file exists. `GET /run-controls` returns 401 (auth enforced) but the run control projection table was created by migration. No evidence of pause/resume/cancel operations actually working.

### Frontend
- **Code:** `apps/SintraPrime/`
- **Status:** PRESENT_BUT_UNVERIFIED
- **Evidence:** Frontend application exists with routing. Command-related files exist (`run-command.ts`, `normalizeCommand.ts`, `uiCommandRunner.ts`). No Mission Control dashboard page identified.
- **Defects:** Frontend/backend connection unverified.

---

## Agents

### Agent Registry
- **Code:** `agents/`
- **Status:** STUB_ONLY
- **Evidence:** Multiple agent directories: `chat/`, `nova/`, `sigma/`, `zero/`, `howard_*`. `chat_agent.py` has rich docstring claims ("autonomous task delegation", "god-mode autonomous operation"). No `AgentRegistry` class found. No runtime execution harness.

### Agent Execution
- **Code:** `agents/chat/chat_agent.py`
- **Status:** STUB_ONLY
- **Evidence:** Chat agent imports succeed. 263-line docstring. No provider invocation observed. No receipt generation. No runtime proof possible.
- **Defects:** No end-to-end execution path demonstrated.

---

## Providers

### Provider Registry
- **Code:** `portal/services/orchestration/provider_registry.py`
- **Status:** STUB_ONLY
- **Evidence:** `mock_provider_registry()` returns mock providers only. Header comment: "Determinate mock providers; no external providers are connected." All providers have `mock_only: True`.
- **Defects:** Zero real provider connections. No OpenAI/Anthropic/Google adapters found.

### Model Router
- **Code:** `portal/services/orchestration/model_router.py`
- **Status:** STUB_ONLY
- **Evidence:** `route_provider()` implements policy-driven routing using `ProviderCapability` and `BudgetUsageSnapshot`. Routes against mock providers only.

### Orchestrator
- **Code:** `portal/services/orchestration/orchestrator.py`
- **Status:** STUB_ONLY
- **Evidence:** `RUNS: dict[str, dict[str, Any]] = {}` — in-memory, not persisted. Header: "Deterministic mock orchestration coordinator." No database persistence. No restart recovery.

---

## Memory

### Memory Models
- **Code:** `memory/`
- **Status:** PARTIALLY_WORKING
- **Evidence:** 10 files: `episodic_memory.py`, `semantic_memory.py`, `working_memory.py`, `memory_engine.py`, `memory_api.py`, `user_profile.py`, `memory_types.py`. Wired to `portal/services/principal_brief.py` and `portal/sso/session_store.py`.
- **Defects:** Storage backend not verified (episodic/semantic likely in-memory or JSON). Graph queries not verified.

### OmniBrain
- **Status:** DOCS_ONLY
- **Evidence:** Zero code files. Only documentation references: `docs/planning/GOD_MODE_EXTENSIONS_ROADMAP.md`, `docs/planning/PHASE_3B_MISSION_CONTROL_PLAN.md`. No `omnibrain` module exists.

---

## Workflow / Orchestration

### Workflow Runtime
- **Status:** MISSING (on origin/main)
- **Evidence:** `workflow_runtime/` does not exist on `origin/main` (e2ada66e). Exists only on feature branch `feat/governed-workflow-runtime` (PR #275, draft, unmerged). Not part of the production codebase.

### Orchestration Service
- **Code:** `portal/services/orchestration/`
- **Status:** STUB_ONLY
- **Evidence:** Deterministic mock orchestrator. In-memory RUNS dict. No persistence. No checkpoint. No resumability. No cancellation.

---

## Messaging / Collaboration

### Message Persistence
- **Code:** `portal/models/message.py`, `portal/migrations/portal_schema.sql`
- **Status:** VERIFIED_WORKING (PG)
- **Evidence:** 10 parallel inserts to PostgreSQL: 10/10 stored. Ordered retrieval: correct by `created_at`. Restart persistence: 10/10 survived new engine. Cross-tenant FK rejection: REJECTED.
- **Defects:** Schema/model drift: ORM declares `body` (String), SQL has `content` (String). ORM declares `sender_id` required, SQL has it nullable.

### WebSocket
- **Code:** `portal/websocket/connection_manager.py`
- **Status:** PRESENT_BUT_UNVERIFIED
- **Evidence:** `ConnectionManager` implements user+tenant connection pool. `asyncio.Lock` thread safety. `ws_manager` imported by MC command service. Runtime verification not performed.

### Event Hub
- **Code:** `core/universe/event_hub/`
- **Status:** PRESENT_BUT_UNVERIFIED
- **Evidence:** `event_hub.py` (644-line test), `event_router.py`, `event_filters.py`. Not imported by portal or agents. Isolated in `core/universe/`.

### Channels
- **Code:** `channels/`
- **Status:** DISCONNECTED
- **Evidence:** `slack_channel.py`, `discord_channel.py`, `message_router.py`, `channel_hub.py`. Not integrated into portal runtime or agent execution.

### Dead Letter
- **Code:** None
- **Status:** MISSING
- **Evidence:** `mission_control_outbox.py` model exists but no dead letter queue implementation. Outbox model only used by `mythos_brain.py` (which itself is broken — stale import).

---

## Repository Automation

### CI
- **Code:** `.github/workflows/`
- **Status:** PRESENT_BUT_UNVERIFIED
- **Evidence:** Default test lane (Tier 1) via `tests/`: 556 passed, 7 failed (PG auth failures). Tier 2-5 (portal, agents, core, memory, orchestration, etc.) deferred — `collect_ignore_glob` in root conftest excludes them.

### Test Coverage
- **Status:** PARTIALLY_WORKING
- **Evidence:** 160 test files in repo. Default CI lane runs only `tests/` (26 files, 563 tests). Portal tests (50 files) excluded by conftest glob. 2 stale import errors in portal tests (test_mythos_brain_integration, test_pr_263_remediation).
