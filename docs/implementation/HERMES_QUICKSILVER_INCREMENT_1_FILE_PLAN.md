# Hermes Quicksilver — Increment One File Plan

## Authority

This plan is bounded by the adapter-boundary verification gate. Increment One remains read-only and feature-flagged. No external action is executed.

## Proposed files

### 1. `adapters/hermes_profile_registry.py`

| Attribute | Value |
| --------- | ----- |
| Purpose | Read-only adapter to enumerate and describe Hermes profiles without importing Hermes internals |
| Governing AGENTS.md | `AGENTS.md`, `agents/AGENTS.md` |
| New or modified | New |
| Existing abstraction extended | None (new adapter) |
| Public interface | `list_profiles() -> list[ProfileSummary]`, `describe_profile(profile_id) -> ProfileDescription` |
| Migration impact | None |
| Rollback | Delete file and references |
| Tests | `tests/unit/test_hermes_profile_registry.py` |

Implementation note: reads `~/.hermes/profiles/<name>/profile.yaml` and directory existence; CLI fallback optional.

### 2. `models/hermes_quicksilver/specialist_profile_mapping.py`

| Attribute | Value |
| --------- | ----- |
| Purpose | Pydantic model for the specialist-to-profile contract |
| Governing AGENTS.md | `AGENTS.md`, `agents/AGENTS.md` |
| New or modified | New |
| Existing abstraction extended | None |
| Public interface | `SpecialistProfileMapping` dataclass/Pydantic model |
| Migration impact | None |
| Rollback | Delete file |
| Tests | `tests/unit/test_specialist_profile_contract.py` |

### 3. `config/features.py`

| Attribute | Value |
| --------- | ----- |
| Purpose | Feature flag `HERMES_QUICKSILVER_ENABLED` defaulting to `False` |
| Governing AGENTS.md | `AGENTS.md` |
| New or modified | Modified (add flag to existing feature configuration) |
| Existing abstraction extended | Follows existing env-var flag conventions (`SINTRA_ENABLE_*`, `NOVA_ALLOW_*`, `ENABLE_*`) |
| Public interface | `is_hermes_quicksilver_enabled() -> bool` |
| Migration impact | None |
| Rollback | Remove flag and helper |
| Tests | `tests/unit/test_hermes_quicksilver_feature_flag.py` |

### 4. `services/hermes_quicksilver/hard_deny_policy.py`

| Attribute | Value |
| --------- | ----- |
| Purpose | Evaluate hard-deny rules before any Hermes delegation |
| Governing AGENTS.md | `AGENTS.md`, `agents/AGENTS.md`, `portal/AGENTS.md` |
| New or modified | New |
| Existing abstraction extended | `agents/nova/approval_gateway.py` rejection behavior |
| Public interface | `evaluate_hard_deny(request: DelegationRequest) -> HardDenyResult` |
| Migration impact | None |
| Rollback | Delete file |
| Tests | `tests/unit/test_hermes_hard_deny.py` |

### 5. `services/hermes_quicksilver/mapping_service.py`

| Attribute | Value |
| --------- | ----- |
| Purpose | Resolve SintraPrime specialist + tenant to Hermes profile; deterministic and fail-closed |
| Governing AGENTS.md | `AGENTS.md`, `agents/AGENTS.md` |
| New or modified | New |
| Existing abstraction extended | None |
| Public interface | `resolve_mapping(specialist_id: str, tenant_id: str) -> ResolvedMapping` |
| Migration impact | None |
| Rollback | Delete file |
| Tests | `tests/unit/test_hermes_mapping_service.py` |

### 6. `audit/hermes_quicksilver/delegation_audit_event.py`

| Attribute | Value |
| --------- | ----- |
| Purpose | Construct redacted audit event for every delegation attempt |
| Governing AGENTS.md | `AGENTS.md`, `agents/AGENTS.md`, `.mesh/AGENTS.md` |
| New or modified | New |
| Existing abstraction extended | `agents/nova/execution_ledger.py` / `blackstone/bra/cel.py` evidence conventions |
| Public interface | `build_audit_event(...) -> HermesDelegationAuditEvent` |
| Migration impact | None |
| Rollback | Delete file |
| Tests | `tests/unit/test_hermes_delegation_audit_event.py` |

### 7. `api/routers/hermes_quicksilver.py` (or `portal/routers/hermes_quicksilver.py`)

| Attribute | Value |
| --------- | ----- |
| Purpose | Internal admin/test router to exercise read-only profile discovery (no external side effects) |
| Governing AGENTS.md | `AGENTS.md`, `portal/AGENTS.md`, `portal/routers/AGENTS.md` |
| New or modified | New |
| Existing abstraction extended | FastAPI router conventions in `portal/routers/` |
| Public interface | `GET /hermes-quicksilver/profiles` (lists mapped profiles), `POST /hermes-quicksilver/resolve` (test resolution, no execution) |
| Migration impact | None |
| Rollback | Delete file and remove router inclusion |
| Tests | `portal/routers/tests/test_hermes_quicksilver.py` |

### 8. `tests/unit/test_hermes_quicksilver_increment_1.py`

| Attribute | Value |
| --------- | ----- |
| Purpose | Consolidated unit tests for Increment One |
| Governing AGENTS.md | `AGENTS.md`, `tests/AGENTS.md` |
| New or modified | New |
| Existing abstraction extended | None |
| Public interface | Test suite only |
| Migration impact | None |
| Rollback | Delete file |
| Tests | Self-contained |

## Not in Increment One

- New job queue
- New session database
- New profile engine
- New approval engine
- External messaging / email / webhooks
- Migrations
- Production deployment
- Actual Hermes invocation beyond read-only discovery

## Increment One delegation sequence

1. Authenticate actor (existing portal auth).
2. Resolve tenant and case context (existing `Tenant`/`Case` models).
3. Resolve SintraPrime specialist (new mapping registry).
4. Evaluate feature flag `HERMES_QUICKSILVER_ENABLED`.
5. Evaluate hard-deny policy.
6. Evaluate authorization / approval requirements (existing `ApprovalGateway`).
7. Resolve mapped Hermes profile via `mapping_service`.
8. Validate Hermes version compatibility.
9. Construct redacted delegation envelope.
10. **Increment One stops here** — no Hermes invocation.
11. Emit redacted SintraPrime audit event.
12. Preserve evidence identifiers.
