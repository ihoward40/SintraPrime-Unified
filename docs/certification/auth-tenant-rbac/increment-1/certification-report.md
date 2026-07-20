# Authentication, Tenant Isolation, and RBAC Certification — Increment 1

Repository: `ihoward40/SintraPrime-Unified`
Branch: `cert/auth-tenant-rbac-increment-1`
Baseline: `0e31c20938a2abf32ee50c1f54622611642aa16b`
Security subject commit: `7f50bdc02b3750210a5424c70491a34d4079b9a1`
Evidence: this directory

Conclusion: CERTIFIED FOR THE RECORDED SCOPE

## Summary
- Authentication claim validation fails closed on missing/empty subject, tenant, role, malformed permissions, unsupported permissions, malformed JWTs, invalid signatures, expired access tokens, refresh tokens used as access tokens, and malformed authorization headers.
- Billing payment lookup is tenant-scoped before mutation.
- RBAC escalation paths deny ordinary users, insufficient permissions, self-role assignment, unauthorized role changes, and cross-tenant user-role mutation.
- The live `/api/v1/` route graph was enumerated dynamically; public exceptions are explicit and protected routes are guarded.
- WebSocket routes were discovered dynamically from source and classified separately from HTTP routes.

## Recorded route totals
- HTTP routes under `/api/v1/`: 93
- Explicit public exceptions: 11
- Protected routes with recognized guard: 82
- WebSocket routes discovered dynamically: 6

## Validation commands
- `python -m ruff check portal/auth/rbac.py portal/routers/billing.py portal/routers/users.py portal/routers/blackstone.py portal/tests/test_auth_tenant_rbac_certification.py`
- `python -m pytest portal/tests/test_auth_tenant_rbac_certification.py -q`
- `python -m pytest portal/tests/test_auth_units.py portal/tests/test_rbac.py portal/tests/test_service_units.py portal/tests/test_auth_tenant_rbac_certification.py -q`
- `python -m pytest --tb=short -q`
- `python scripts/ci/validate_repository_claims.py`
- `python scripts/ci/report_test_inventory.py`
- `ruff check . --output-format=github`
- `git diff --check`

## Discovered defects corrected
1. Malformed identity claims could escape the supported authentication-failure path.
2. Invoice payment lookup lacked tenant scope.
3. A Payment row could be added before invoice tenant validation.
4. Self-role assignment required explicit denial.
5. Blackstone protected routes lacked an explicit authentication guard.

## Evidence schema
Every JSON artifact in this directory is an object with the required fields: `schema_version`, `repository`, `baseline_commit`, `evidence_commit`, `generation_method`, `source_files`, `source_tests`, `result`, `limitations`. `route-permission-matrix.json` carries the 93 route records under its `routes` key.

## Known limitations
- Public exception routes remain public by design.
- The certification test fixture uses a short HS256 key, which raises a PyJWT `InsecureKeyLengthWarning` but does not fail the gate.
- `request_id` is not consistently populated by current router audit call sites; full request traceability is not claimed.