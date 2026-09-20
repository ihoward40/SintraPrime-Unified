# HERMES QUICKSILVER — GAP ANALYSIS

## Executive Decision

**REVISE**

The previous `PASS TO IMPLEMENTATION` preparation report is rejected. This gap analysis replaces it and documents why the corrected preparation effort remains **REVISE**: source-level mapping is materially complete, the clean isolated baseline exists, several Hermes capabilities are validated, but evidence reconciliation, some test-environment failures, and the SintraPrime adapter boundary remain unresolved.

---

## Canonical Baseline

| Field | Value |
| ----- | ----- |
| Authority repository | `C:\Users\admin\Desktop\Projects\SintraPrime-Unified` |
| Remote | `https://github.com/ihoward40/SintraPrime-Unified.git` |
| `origin/main` | `8622cb298a0186760e7618a58598a90911f7083b` |
| Commit message | `fix(db): reconcile PostgreSQL bootstrap and evidence schema authority (#223)` |
| Commit date | `2026-07-23T13:44:56-04:00` |
| Clean worktree | `C:\Users\admin\Desktop\Projects\SintraPrime-Unified-hermes-quicksilver` |
| Worktree branch | `feat/hermes-quicksilver-governed-fleet-increment-1` |
| Worktree HEAD | `8622cb298a0186760e7618a58598a90911f7083b` |
| Worktree status | clean |

---

## Hermes Version Observations

| Source | Value | Interpretation |
| ------ | ----- | -------------- |
| `pyproject.toml` | `0.18.2` | Python package version |
| `package.json` | `1.0.0` | Node workspace root version |
| `hermes --version` | `v0.15.2` | Installed runtime command version |

"Quicksilver" is a target capability architecture, not a verified installed version. The runtime command is 1893 commits behind the source tree, so the installed executable does not match the `0.18.2` source.

---

## Requirement-to-Capability Matrix

| Requirement | Hermes evidence | SintraPrime evidence | Owner | Status | Actual gap | Proposed integration |
| ----------- | --------------- | -------------------- | ----- | ------ | ---------- | -------------------- |
| Profile routing | `gateway/profile_routing.py`: `ProfileRoute`, `match_profile_route`; tests pass (32/32) | `channels/message_router.py`: `MessageRouter` | Hermes | EXISTING | SintraPrime mapping not yet defined | Adapter reads Hermes profile list; SintraPrime maps specialists to profiles |
| Approval / deny rules | `tools/approval.py`: pattern detection, per-session state; `tests/tools/test_approval_deny_rules.py` 19/19 pass | `agents/nova/approval_gateway.py`: `ApprovalGateway`, `ApprovalRequest`, `ApprovalTier` | Hermes mechanics; SintraPrime policy | EXISTING (Hermes); PARTIAL (SintraPrime) | No bridge between Hermes dangerous-command approval and SintraPrime Nova approval tier | Use Hermes runtime approval; SintraPrime supplies policy overlay and audit evidence |
| Approval isolation | `tests/acp/test_approval_isolation.py` 8/8 pass | none observed | Hermes | EXISTING | No SintraPrime equivalent | Treat as Hermes-internal until policy bridge is defined |
| Approval redaction | `agent/redact.py`; `tests/gateway/test_approval_prompt_redaction.py` collection error; `tests/gateway/test_tui_approval_redaction.py` 1 failed, 5 passed | `agents/nova/execution_ledger.py`: `LedgerEntry` | Hermes mechanics; SintraPrime audit | PARTIAL | Hermes redaction tests not fully passing in this environment; redaction contract not mapped to SintraPrime ledger | Verify environment; define contract for redacted entries passed to SintraPrime |
| Session persistence | `gateway/session.py`; `tests/gateway/test_async_session_store.py` 5/5 pass | none observed directly | Hermes | EXISTING | No SintraPrime session store integration needed for Increment One | Leave in Hermes; no new DB |
| Session stale guard | `gateway/session.py`; `tests/gateway/test_session_store_runtime_stale_guard.py` 12/12 pass | none observed | Hermes | EXISTING | Same as above | No action for Increment One |
| Checkpoint resumption | `hermes_cli/checkpoints.py`; `tests/integration/test_checkpoint_resumption.py` 3 deselected | none observed | Hermes | UNKNOWN | Tests deselected; behavior not verified on this host | Investigate deselection reason before relying on it |
| Provider fallback | `hermes_cli/fallback_cmd.py`, `hermes_cli/providers.py`; `tests/run_agent/test_provider_fallback.py` 17 failed, 6 passed (`concurrent_log_handler` missing) | none observed | Hermes | PARTIAL / BROKEN IN ENV | Fails in this runtime due to missing dependency | Resolve environment or treat fallback as not-yet-validated |
| Secret scope | `agent/secret_scope.py`; `tests/agent/test_secret_scope.py` 13/13 pass | none observed | Hermes | EXISTING | No SintraPrime secret bridge defined | Use Hermes secret scoping; SintraPrime only consumes redacted audit events |
| Session export | `hermes_cli/session_export.py`, `session_export_html.py`, `session_export_md.py`; tests 10/10, 3/3, 7/7 pass | none observed | Hermes | EXISTING | No SintraPrime evidence export bridge defined | Optional adapter for SintraPrime evidence ingestion |
| Gateway restart / recovery | `gateway/restart.py`, `gateway/restart_loop_guard.py`; `tests/hermes_cli/test_gateway_restart_loop.py` 65/65 pass | none observed | Hermes | EXISTING | No bridge to SintraPrime observatory | Gateway recovery remains Hermes-internal |
| Agent registry / discovery | `acp_registry` / `acp_adapter` present | `agent_protocol/agent_discovery.py`, `agent_protocol/agent_node.py`, `AgentNetwork` | SintraPrime | PARTIAL (source located) | Two different registry concepts; no mapping | Define adapter from SintraPrime specialist IDs to Hermes profiles |
| Tenant authorization | not observed directly in Hermes | `portal/` 7 RBAC roles, RLS in DB | SintraPrime | UNKNOWN | Hermes is multi-tenant by profile, not by SintraPrime tenant | Define tenant-to-profile boundary in adapter |
| Audit / evidence ledger | observer hooks in `tools/approval.py` | `agents/nova/execution_ledger.py`, `blackstone/bra/cel.py` | SintraPrime | PARTIAL | Hermes observer payload shape not mapped to SintraPrime ledger | Define redacted audit event contract |
| Kill switch / hard deny | deny patterns in `tools/approval.py` | `agents/nova/approval_gateway.py` | Shared | PARTIAL | No unified hard-deny policy | Increment One: SintraPrime hard-deny evaluated before delegation |
| Idempotency | not directly located | not directly located | UNKNOWN | UNKNOWN | Need source evidence | Locate existing idempotency mechanisms before Increment Two |
| Model routing / cost controls | `hermes_cli/model_cost_guard.py`: `expensive_model_warning` | not observed | Hermes | EXISTING (source located) | No SintraPrime cost policy | Keep in Hermes; surface warnings through adapter if needed |

---

## Duplicate-Clone Risk

There are at least two independent clones:

```text
C:\SintraPrime-Unified
  branch: fix/monetization-security-ledger-integrity
  state:  dirty, ahead 1, many deletions and untracked artifacts
  HEAD:   0aaffdc4

C:\Users\admin\Desktop\Projects\SintraPrime-Unified
  branch: feat/payment-webhook-validation-idempotency-increment-1
  state:  dirty
  HEAD:   4dda1a49
```

These clones have different active branches, different dirty states, and different worktrees. Implementation must not begin until a single canonical clone and baseline are declared.

---

## Uncommitted Work Preservation

No existing uncommitted work was reset, cleaned, stashed, checked out, deleted, or modified during this correction. The new Quicksilver worktree was added from `origin/main` without touching the authority worktree's files.

---

## Migration Impact

No migrations are proposed in Increment One. The first increment is read-only and feature-flagged.

---

## API Impact

No public API changes are proposed in Increment One.

---

## Security Impact

- Hard-deny policy evaluation before Hermes delegation reduces blast radius.
- Redacted audit events prevent secret leakage from Hermes to SintraPrime.
- Feature flag defaulting to disabled prevents accidental activation.
- Cross-profile / cross-tenant access must be explicitly denied in the adapter.

---

## Test Strategy

For Increment One:

1. Specialist registry schema validation.
2. Unknown specialist rejected.
3. Disabled feature flag rejects delegation.
4. Profile mapping deterministic.
5. Cross-profile access denied.
6. Hard deny overrides allow.
7. Secret values absent from audit output.
8. Approval context redacted.
9. Tenant context preserved.
10. No external action executed.
11. Hermes unavailable fails closed.
12. Unsupported Hermes version handled safely.

Use the repository's existing pytest conventions.

---


## Adapter Boundary Findings

### SintraPrime ownership (source-verified)

- **Agent identity**: `agent_id: str` + `AgentCapabilities` dataclass in `agent_protocol/message_types.py`; peer discovery via `AgentDiscovery` (`agent_protocol/agent_discovery.py`); network facade `AgentNetwork` (`agent_protocol/__init__.py`). No "specialist" concept exists; it must be a SintraPrime-owned construct.
- **Routing**: `channels/message_router.py` performs keyword-based intent detection and dispatches to handlers. It does not currently delegate to external runtimes.
- **Approval**: `agents/nova/approval_gateway.py` manages `ApprovalRequest`, `ApprovalStatus`, `ApprovalTier`, auto-approve sets, and expiry. Hard deny is implicit via rejection; a dedicated hard-deny policy engine does not yet exist.
- **Audit/evidence**: `agents/nova/execution_ledger.py` provides a hash-chained JSONL ledger (`LedgerEntry`). `blackstone/bra/cel.py` provides the `ConstitutionalEvidenceLedger` with chain-of-custody, source classes, integrity status, legal hold, and deprecation. Either can receive audit events.
- **Tenant/context**: `portal/models/user.py` defines `Tenant`, `User`, `Role`, `Permission`. `tenant_id` and `user_id` are UUID strings. Models across the portal consistently carry `tenant_id`.
- **Feature flags**: No centralized feature-flag database model was found. Existing toggles use environment variables (`SINTRA_ENABLE_SWARMS`, `NOVA_ALLOW_DYNAMIC_EXEC`, docker-compose `ENABLE_*`).

### Hermes integration surface (source-verified)

- Profiles are filesystem-isolated under `~/.hermes/profiles/<name>/` (`hermes_cli/profiles.py`).
- Profile routing maps platform/guild/chat/thread to a profile (`gateway/profile_routing.py`).
- Profile description is generated into `profile.yaml` (`hermes_cli/profile_describer.py`).
- The narrowest read-only surface is parsing the profile directory and `profile.yaml`; CLI fallback is `hermes profile list --json` / `hermes profile describe <name> --json`.

### Ownership boundary

The hypothesized boundary is confirmed: Hermes owns runtime mechanics; SintraPrime owns tenant authorization, specialist identity, policy, audit, and governance. See `HERMES_SINTRAPRIME_OWNERSHIP_MATRIX.md`.

### Dependency failure disposition

`ENVIRONMENT MISMATCH CONFIRMED`. `concurrent-log-handler==0.9.29; sys_platform == 'win32'` is declared in `pyproject.toml` line 140, but the active interpreter (`C:\Python314\python.exe`) and the installed Hermes CLI (`v0.15.2` from `C:\Python314\Lib\site-packages`) lack it. The CLI is also 1893 commits behind the source tree. Checkpoint resumption tests are deselected because they carry `pytest.mark.integration` and no integration marker was selected.

## New Artifacts Produced

- `docs/architecture/HERMES_SINTRAPRIME_OWNERSHIP_MATRIX.md`
- `docs/architecture/HERMES_SPECIALIST_PROFILE_CONTRACT.md`
- `docs/architecture/HERMES_QUICKSILVER_AUDIT_EVENT_CONTRACT.md`
- `docs/implementation/HERMES_QUICKSILVER_INCREMENT_1_FILE_PLAN.md`


## Rollback Strategy

- Feature flag default `False`.
- Adapter code isolated in `adapters/` and `policies/`.
- No database migrations in Increment One.
- Revertible by removing the feature flag and adapter imports.

---

## Decision

**REVISE** — implementation unauthorized. The prior preparation output was invalid, the capability matrix has unresolved gaps, the Hermes runtime version is ambiguous, and some Hermes tests fail or are deselected in this environment. A new preparation gate must be requested after these items are resolved.
