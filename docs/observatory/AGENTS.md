# Observatory DOX

## Purpose
SintraPrime Observatory — Agent Operations, Observability, Governance, and Control Plane (AOGCP). Provides live visibility, control, governance gates, evidence ledger, and replay for all autonomous agents.

## Ownership
Owned by Isiah Howard. Phase 1 implementation in progress.

## Local Contracts
- Event schema: `agent.event.v1` (defined in `portal/schemas/observatory.py`)
- Database models: hash-chained events, agents, missions, approvals, evidence, artifacts, incidents (in `portal/models/observatory.py`)
- API routes: `/api/v1/missions/*`, `/api/v1/agents/*`, `/api/v1/events`, `/api/v1/approvals/*`, `/api/v1/evidence/*`, `/api/v1/runs/*`, `/ws/observatory`, `/api/v1/emergency/kill-switch` (in `portal/routers/observatory.py`)
- Business logic: event service (hash chaining), mission service, agent service, approval service, governance gates (G-01 through G-10), evidence service, incident service, replay service (in `portal/services/observatory_service.py`)
- UI: React + TypeScript web dashboard (future: `apps/observatory-web/`)

## Work Guidance
- All events must be hash-chained (SHA-256 of previous_hash + canonical_payload)
- Sensitive data (SSN, API keys, tokens, passwords) must be masked in stored events
- Kill switch NEVER deletes evidence
- Governance gates enforce human approval before consequential actions
- WebSocket broadcasts new events to all connected clients
- Async SQLAlchemy for both SQLite (tests) and PostgreSQL (production)

## Verification
- `python -m pytest portal/tests/test_observatory.py -q --tb=short`
- `python -m ruff check portal/routers/observatory.py portal/services/observatory_service.py portal/schemas/observatory.py portal/models/observatory.py`
- Event hash chain integrity test
- Sensitive data masking test
- Mission lifecycle test
- Governance gate blocking test

## Child DOX Index

- `gates/gate-3/` — G3 evidence manifest, freeze record, amendments
- `gates/gate-4/` — Gate 4 decisions, incl. `G4.7_EXECUTION_GUARD.md` (decision package), `CREDENTIAL_PROVENANCE.md`, `DATABASE_CLASSIFICATION.md`, `RISK-G4-PRODUCTION-ROLE-PRIVILEGE-001.md`