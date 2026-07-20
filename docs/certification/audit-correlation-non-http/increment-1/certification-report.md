# Audit Correlation and Non-HTTP Authorization Certification — Increment 1

Repository: `ihoward40/SintraPrime-Unified`
Branch: `cert/audit-correlation-non-http-increment-1`
Baseline: `a93d2513e73e3a89faf11e3e5b36abfb4e090613`

Conclusion: CERTIFIED FOR THE RECORDED SCOPE

## Summary
- Correlation context authority established with contextvar-based isolation for concurrent requests.
- Audit event envelope defined with schema_version, event_id, request/correlation/causation IDs, actor, tenant, action, resource, transport, outcome, denial_reason, metadata, and integrity_hash.
- Secret redaction prevents passwords, tokens, bearer values, private keys, cookies, and authorization headers from entering audit metadata or logs.
- WebSocket authentication enforces JWT validation before connection acceptance.
- WebSocket authorization enforces RBAC permissions (ADMIN_DASHBOARD for the admin dashboard WS).
- WebSocket tenant isolation: the connection binds to the tenant derived from the JWT, ignoring client-supplied tenant IDs.
- WebSocket audit events emitted for connect and disconnect lifecycle.
- Non-HTTP entry-point inventory is deterministic regardless of process working directory.
- The admin dashboard WebSocket endpoint was previously broken (importing a non-existent `verify_token`); it now uses the proper authentication/authorization/correlation stack.

## Dynamic entry-point totals

### WebSocket route scope reconciliation

The prior auth/tenant/RBAC increment (PR #214) recorded 6 WebSocket routes via repository-wide source discovery (scanning all .py files for @router.websocket decorators). This increment distinguishes between two discovery scopes:

- **Repository-wide source discovery**: 6 WebSocket route declarations found across 5 modules (portal/admin/dashboard.py, docket/docket_api.py, performance/performance_api.py, workflow_builder/workflow_api.py, core/universe/hive_mind_api.py).
- **Mounted production application routes**: 1 WebSocket route is actually registered in the running FastAPI application (/api/v1/admin/ws).

The 5 unmounted modules (docket, performance, workflow_builder, hive_mind) are NOT included in portal/main.py's `include_router` calls. They are source-level modules that exist in the repository but are not wired into the production application. Their routers cannot be imported (import errors or missing router attributes). They are classified as OUT OF SUPPORTED SCOPE — unmounted, non-production modules.

This increment certifies the 1 mounted production WebSocket route. The prior increment's 6-route count was repository-wide source discovery, not production-mounted routes. No routes were lost; the boundary is explicitly: 1 CERTIFIED (mounted) + 5 OUT OF SUPPORTED SCOPE (unmounted) = 6 total discovered in source.

### Totals
- WebSocket routes (mounted production, CERTIFIED): 1 (portal/admin/dashboard.py /api/v1/admin/ws)
- WebSocket routes (unmounted source, OUT OF SUPPORTED SCOPE): 5 (docket, performance, workflow_builder, hive_mind x2)
- WebSocket routes (total source discovery): 6
- Background tasks: none discovered
- Scheduler jobs: none discovered in portal scope
- CLI/admin scripts: scripts/ directory classified OUT OF SUPPORTED SCOPE
- Service-to-service invocations: SSO provider HTTP calls classified OUT OF SUPPORTED SCOPE
- Webhooks: none discovered

## Controls implemented
1. CorrelationContext with request_id, correlation_id, causation_id, actor_id, tenant_id, invocation_type, source_transport, timestamp
2. Contextvar-based storage (no global mutable state, no concurrent leakage)
3. Inbound identifier validation and secure generation
4. Tenant/actor immutability (prevent_override functions ignore client input)
5. Nested service propagation (propagate_to_child preserves correlation_id, sets causation_id)
6. AuditEvent envelope with integrity_hash (SHA-256 over canonical JSON)
7. Secret redaction (recursive, case-insensitive, 14 known secret field names)
8. WebSocket authenticate_websocket, authorize_websocket_connection, bind_websocket_context
9. WebSocket safe close codes (4401, 4403, 4404, 4429, 4400)
10. WebSocket audit event emission for connect and disconnect

## Known limitations
- request_id is not yet propagated in HTTP response headers (deferred to a follow-up HTTP middleware increment).
- WebSocket rate/size/abuse controls are not implemented (the existing architecture does not support them yet).
- Background-task identity propagation is defined in the correlation module but no production background tasks exist in the current codebase to bind.
- Webhook signature verification is not implemented because no production webhooks exist.
- CLI administrative authorization is classified OUT OF SUPPORTED SCOPE for this increment.

## Validation commands
- `python -m ruff check <changed Python files>`
- `python -m pytest portal/tests/test_audit_correlation_non_http_certification.py -q`
- `python -m pytest portal/tests/test_auth_tenant_rbac_certification.py portal/tests/test_audit_correlation_non_http_certification.py -q`
- `python -m pytest --tb=short -q`
- `python scripts/ci/validate_repository_claims.py`
- `python scripts/ci/report_test_inventory.py`
- `ruff check . --output-format=github`
- `git diff --check`

## Evidence provenance
Every JSON artifact uses `generated_from_commit` tied to the immutable implementation commit. No self-referential `evidence_commit: "pending"` placeholders.