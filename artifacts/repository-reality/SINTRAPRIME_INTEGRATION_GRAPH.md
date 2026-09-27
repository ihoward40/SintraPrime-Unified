# Integration Graph

**Generated:** 2026-08-08
**Commit:** e2ada66e

---

## Working Edges

```text
HTTP Request
  → Auth Middleware (JWT validation) ✅
  → RBAC Permission Check ✅
  → Route Handler ✅
  → Service Layer
  → Database (PG or SQLite) ✅ (with schema drift defects)
  → Correlation ID (audit) ✅

Health Endpoint
  → /health (unauthenticated) ✅
  → /api/system/health (authenticated) ✅

Message Thread
  → Create Thread (DB) ✅
  → Send Message (DB) ✅
  → FK Enforcement (cross-tenant) ✅

MC Command Service
  → Auth Middleware ✅
  → Permission Check ✅
  → Hash-chained Receipt ✅
  → Structlog Audit ✅
  → WebSocket Notify ✅
  → Database INSERT ❌ (UUID drift on PG)
```

## Broken Edges

```text
GovernanceEngine
  → [no caller] ❌ DISCONNECTED

MultiTenantGovernance
  → platform_hardening → simulation scripts only ❌ DISCONNECTED

Orchestrator
  → In-memory RUNS dict (no DB persistence) ❌ STUB_ONLY

Provider Router
  → Mock providers only ❌ STUB_ONLY

Event Hub
  → core/universe/ (not imported by portal/agents) ❌ DISCONNECTED

Agent Execution
  → [no provider invocation] ❌ MISSING

Workflow Runtime
  → [not on origin/main] ❌ MISSING

OmniBrain
  → [no code] ❌ DOCS_ONLY
```

## Disconnected Subsystems (no incoming or outgoing edges)

- `governance/` — isolated package, no callers
- `core/universe/event_hub/` — no importers
- `channels/` — Slack/Discord adapters, no runtime integration
- `memory/` — wired only to `principal_brief` and `session_store` (not agents)
- `agent_protocol/` — isolated, not called by agents

## Partially Connected

- MC command service: connected to auth + WS + audit, but DB layer broken on PG
- Audit trail: model exists, called by MC command service, but audit_records table depends on evidence_snapshots (ordering bug)
- Outbox model: exists, no service processes it
