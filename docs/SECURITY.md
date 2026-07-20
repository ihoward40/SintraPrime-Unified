# Security Architecture (Current Controls)

> Authoritative as of commit `48e2caa759661cc75617cc752bcc26eaad666647` (tree `9ee6d193dd7f607cd59487df9ef26d46b9593803`).
> This document describes controls present in the codebase. It does **NOT** represent
> completed compliance certification.

## Authentication
- JWT issuance/refresh in `portal/auth/`.
- Identity-claim validation in `portal/auth/rbac.py` (PR #214). Authenticated actor
  and tenant binding enforced on all certified routes.
- Delegated SSO in `portal/sso/` (optional).

## Tenant isolation
- Mission Control enforces `tenant_id` scoping on every state transition
  (`portal/services/mission_control_run_control_service.py`). Cross-tenant requests
  match zero rows and are rejected (proven in the PostgreSQL race lane).
- Tenant-scoped route authorization enforced on `portal/routers/billing.py`,
  `portal/routers/blackstone.py`, `portal/routers/users.py` (PR #214).

## RBAC
- `portal/auth/rbac.py` + `portal/models/user.py` (Role / Permission / RolePermission /
  UserPermissionAssoc).
- Permission provisioning: `portal/services/permission_provisioning.py`
  (`verify` and `dry-run` are read-only; `reconcile` is explicit).
- RBAC escalation controls: identity-claim validation prevents unauthorized role
  escalation (PR #214, CERTIFIED FOR RECORDED SCOPE).

## Correlation and audit
- Immutable correlation context: `portal/auth/correlation.py` (PR #215). Provides
  request-scoped correlation IDs propagated through the service boundary.
- Audit-event envelopes: `portal/auth/audit_envelope.py` (PR #215). Immutable audit
  envelopes with actor, tenant, correlation, and action binding.
- HTTP request-ID middleware: `portal/middleware/correlation_middleware.py` (PR #217).
  Assigns and propagates `X-Request-ID` for every HTTP request.

## WebSocket security
- WebSocket authentication and authorization: `portal/auth/websocket_auth.py`
  (PR #215). Connection-level identity and tenant binding.
- WebSocket hardening: `portal/auth/ws_hardening.py` (PR #217). Capacity, rate,
  timeout, lifetime, and payload controls.

## Execution governance
- `portal/services/mission_control_command_guard.py` returns
  `COMMAND_EXECUTION_NOT_ENABLED` for all operational commands. Commands are
  **refusal-only** — no live execution is performed.

## Encryption
- TLS in transit (configure at proxy/ingress).
- AES-256 at rest is **configurable** via KMS — confirm your deployment enables it.

## Secrets
- No secrets in code. Keys via environment variables / secret stores.
- `.env.test` is git-ignored and never staged.

## Secure execution module
- `secure_execution/` provides TEE/zero-trust primitives (attestation, tee_manager,
  zero_trust). It is **not** wired into the portal RBAC authority and is experimental.

## Certification CI lanes

Three certification-specific CI lanes are defined in `.github/workflows/ci.yml`:

| CI lane | Scope | Certifying PR |
|---------|-------|----------------|
| `auth-tenant-rbac-certification` | Authentication, tenant isolation, RBAC | PR #214 |
| `audit-correlation-non-http-certification` | Audit correlation, non-HTTP authorization | PR #215 |
| `http-correlation-ws-hardening-certification` | HTTP request-ID correlation, WebSocket hardening | PR #217 |

These lanes are CERTIFIED FOR THE RECORDED SCOPE of their respective increments.

## Certification boundary

The security controls established through PRs #214–#217 are:

```
CERTIFIED FOR THE RECORDED SCOPE
```

This means the specific increment's test suite passes in CI. It does NOT mean:

```
production-certified
HIPAA compliant
SOC 2 compliant
PCI-DSS compliant
distributed WebSocket enforcement
complete server-level exception correlation
```

## Compliance posture
- **NOT certified.** HIPAA / SOC 2 / PCI-DSS readiness is claimed nowhere as completed.
  The platform provides audit logging and RBAC scaffolding that *support* future
  certification. Independent assessment is required before any compliance claim.

## Known gaps
- No centralized execution authority spanning API, workflow, and agent origins.
- Process-local WebSocket enforcement (no distributed enforcement).
- Deprecated query-token support for WebSocket authentication still present.
- Incomplete request-ID coverage for exceptions outside application control.
- No session revocation, token rotation, or logout invalidation.
- No key rotation lifecycle.
- No concurrent session policy.
- Deployment stack not verified by CI.
- Multiple feature packages declare their own models; unified schema authority pending.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [DATABASE_AUTHORITY.md](DATABASE_AUTHORITY.md).