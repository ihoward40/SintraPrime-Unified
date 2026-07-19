# Security Architecture (Current Controls)

> Authoritative as of commit `10cad07f046b5675ed10a1fba1aa4a955636f739`.
> This document describes controls present in the codebase. It does **NOT** represent
> completed compliance certification.

## Authentication
- JWT issuance/refresh in `portal/auth/`.
- Delegated SSO in `portal/sso/` (optional).

## Tenant isolation
- Mission Control enforces `tenant_id` scoping on every state transition
  (`portal/services/mission_control_run_control_service.py`). Cross-tenant requests
  match zero rows and are rejected (proven in the PostgreSQL race lane).

## RBAC
- `portal/auth/rbac.py` + `portal/models/user.py` (Role / Permission / RolePermission /
  UserPermissionAssoc).
- Permission provisioning: `portal/services/permission_provisioning.py`
  (`verify` and `dry-run` are read-only; `reconcile` is explicit).

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

## Compliance posture
- **NOT certified.** HIPAA / SOC 2 / PCI-DSS readiness is claimed nowhere as completed.
  The platform provides audit logging and RBAC scaffolding that *support* future
  certification. Independent assessment is required before any compliance claim.

## Known gaps
- No centralized execution authority spanning API, workflow, and agent origins.
- Deployment stack not verified by CI.
- Multiple feature packages declare their own models; unified schema authority pending.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [DATABASE_AUTHORITY.md](DATABASE_AUTHORITY.md).

