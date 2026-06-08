# portal/routers — API Route Handlers

## Purpose

Owns all FastAPI route handler modules. These are the API surface — the contract between the portal and its consumers (React SPA, mobile app, external integrations). Routers enforce request validation via `schemas/` and delegate business logic to `services/`.

## Ownership

- All files in `portal/routers/` (auth, admin, billing, cases, clients, documents, messages, notifications, recovery, sso, trust_compliance, users)
- Router tests in `portal/routers/tests/`

## Local Contracts

- Every router function should accept an async `Session` from dependency injection
- Production routers must call through to a `portal/services/` layer function — no inline business logic
- Every router function should return a Pydantic schema (from `portal/schemas/`)
- Auth routes: rate-limited (10 req/min/IP), require JWT validation
- All other routes: rate-limited (100 req/min/user), require session/auth middleware

**Legacy/demo exception:** `recovery.py` and `trust_compliance.py` may temporarily contain minimal orchestration logic (lightweight JSON/demo endpoints). New production logic should move into `portal/services/` where practical.

## Work Guidance

*(No project-specific standards yet — fill when engineering conventions emerge.)*

## Verification

*(No verification framework documented yet — fill when test/coverage thresholds exist.)*

## Child DOX Index

*(None — all router files are leaf modules.)*
