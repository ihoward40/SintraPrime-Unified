# Mission Control Security

**Status:** COMPLETE
**ADR:** ADR-002

## 1. Tenant Isolation

All Mission Control queries filter on `current_user.tenant_id`. No endpoint returns data belonging to a different tenant.

- List endpoints scope results to the current tenant.
- Detail endpoints return **404 Not Found** for cross-tenant access (never 403) to avoid leaking resource existence.
- Tenant isolation is enforced at the query layer; it is not optional.

Tenant isolation is verified by **5 dedicated tests** that confirm cross-tenant access returns 404.

## 2. Read-Only Enforcement

No new mutation routes were introduced. The only POST endpoint (`POST /api/v1/mission-control/commands`) is **pre-existing** and refusal-only.

Read-only enforcement is verified by **6 dedicated tests** confirming that POST, PUT, PATCH, and DELETE on the new projection surface return **405 Method Not Allowed**.

- No new POST route added.
- No new PUT route added.
- No new PATCH route added.
- No new DELETE route added.
- No cancellation, approval, retry, replay, lease, or dispatch mutation added.

## 3. Sigma Gate

- `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` is **BLOCKED**.
- All cancellation controls are **DISABLED**.
- `is_cancellation_blocked()` returns `True`.
- The gate status is read-only in Mission Control; it cannot be toggled via the API.
- The gate remains blocking until ADR-MC-001 is ratified and its criteria are implemented.

Sigma gate behavior is verified by **5 dedicated tests**.

## 4. Authentication & Authorization

- Authentication is required on all Mission Control endpoints.
- All new GET endpoints require the `MISSION_COMMAND_READ` permission.
- Unauthenticated requests are rejected.
- Authenticated requests lacking the permission are rejected.

Auth enforcement is verified by **2 dedicated tests**.

## 5. Pre-Existing POST /commands

The pre-existing `POST /api/v1/mission-control/commands` endpoint is **refusal-only**. It returns `COMMAND_EXECUTION_NOT_ENABLED` for all requests and cannot execute commands. It predates this phase and remains **unchanged**.

## 6. Persistence

**No persistence migrations were added.** Mission Control reads from existing projections and ledger data. No new tables, no schema changes, no migrations were introduced.

## 7. Sensitive Data

Mission Control stores **no card data, no secrets, and no sensitive data**. It is a read-only projection of command and run-control state. No credentials, tokens, or payment data pass through or persist in Mission Control.

## 8. Summary

| Control | Status |
|---------|--------|
| Tenant isolation | Enforced (5 tests) |
| Read-only enforcement | Enforced (6 tests) |
| Sigma gate | BLOCKED (5 tests) |
| Auth required | Enforced (2 tests) |
| Pre-existing POST | Refusal-only, unchanged |
| Persistence migrations | None added |
| Sensitive data | None stored |