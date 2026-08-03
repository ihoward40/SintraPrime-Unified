# portal/routers - API Route Handlers

## Purpose

Owns all FastAPI route handler modules. These are the API surface: the contract between the portal and its consumers (React SPA, mobile app, external integrations). Routers enforce request validation and delegate business logic to `services/`.

## Ownership

- All files in `portal/routers/` (auth, admin, billing, cases, clients, documents, messages, notifications, recovery, sso, trust_compliance, users, mission_control_commands, voice_commands, jurisdictions)
- Router tests in `portal/routers/tests/`

## Local Contracts

- Every production router should call through to a `portal/services/` layer function; no inline legal/business logic.
- Production routers should return Pydantic schemas where a stable schema module exists; lightweight JSON-backed pilot routers may use local request models while contracts harden.
- Auth routes: rate-limited (10 req/min/IP), require JWT validation.
- All other production routes: rate-limited (100 req/min/user), require session/auth middleware.
- Jurisdiction Phase 2A write endpoints are controlled and must require reviewer role and identity headers until integrated with the portal's full authorization stack.
- Review/challenge/stale-source write routes must not claim automatic credential verification and must create audit records through the service layer.

**Legacy/demo exception:** `recovery.py` and `trust_compliance.py` may temporarily contain minimal orchestration logic (lightweight JSON/demo endpoints). New production logic should move into `portal/services/` where practical.

## Work Guidance

*(No project-specific standards yet - fill when engineering conventions emerge.)*

## Verification

- Run `portal/tests/test_jurisdictions_api.py` after changing jurisdiction routes.

## Child DOX Index

*(None - all router files are leaf modules.)*
