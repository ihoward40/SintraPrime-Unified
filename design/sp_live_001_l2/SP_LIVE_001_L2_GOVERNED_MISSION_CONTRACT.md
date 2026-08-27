# SP-LIVE-001 L2 Governed End-to-End Mission Contract

## Status and authority

- **Design gate:** `SP_LIVE_001_L2_GOVERNED_END_TO_END_MISSION_DESIGN`
- **Design authority:** read-only architecture inspection, mission-contract design, test planning, acceptance criteria, and zero-write implementation-gap analysis.
- **L2 implementation authority:** `NONE`
- **L2 live-execution authority:** `NONE`
- **External, production, and GitHub side effects:** `PROHIBITED`
- **Relationship to L1:** L1 remains independently ratified, closed, and frozen. No L1 artifact, source manifest, consumed nonce, or consumed authority is reusable by L2.

## Mission objective

L2 certifies one complete governed mission across the larger architecture, not merely another adapter write:

```text
REQUEST
→ PRINCIPAL IDENTITY
→ MISSION SCOPE
→ SPECIALIST / WORKFORCE SELECTION
→ LIVING-MEMORY RETRIEVAL
→ MODEL SELECTION
→ POLICY RESOLUTION
→ AUTHORITY RESOLUTION
→ PRINCIPAL APPROVAL
→ CAPABILITY RESOLUTION
→ ONE BOUNDED REAL SIDE EFFECT
→ PROVIDER READBACK
→ HASHED EVIDENCE
→ PRINCIPAL BRIEF
```

This design does not choose or authorize the eventual real capability. Capability, provider, account, destination, body/parameters, and consequence class remain unset until a later implementation/certification gate proposes and freezes them.

## Non-negotiable invariants

1. **No specialist self-authorization.** Specialists are advisory and receive no approval credential, live provider credential, or side-effect handle.
2. **No swarm authority expansion.** Decomposition and reconciliation may narrow mission scope but cannot add objectives, capabilities, destinations, budgets, or consequences.
3. **No model-selection authority expansion.** A model decision chooses a reasoning implementation only. It grants zero mission, tool, provider, account, or side-effect authority.
4. **No memory-derived authority.** Retrieved memory is context with provenance and trust labels. Preferences, prior approvals, habits, and retrieved instructions cannot authorize execution.
5. **No capability-alias expansion.** Resolution requires an exact versioned capability ID and exact frozen adapter/entrypoint/provider identity. Similar names and aliases fail closed.
6. **No approval reuse.** Approval is single-use and binds one mission, action hash, execution ID, nonce, capability, provider, account, destination, exact parameters/body, baseline identity, expiry, and maximum execution count.
7. **No unbound execution identity.** Live mode requires envelope-supplied execution ID and nonce. Autogeneration and substitution are prohibited.
8. **No mock fallback in live mode.** A mock, synthetic provider, dry-run runner, alternate entrypoint, or degraded adapter cannot satisfy or replace the frozen live capability.
9. **No completion without evidence.** Mission state cannot reach `COMPLETE` without provider receipt, independent readback, exact-state verification, consumed authority/nonce, sealed evidence root, and a Principal Brief derived from that sealed root.
10. **At most one external side effect.** Any second attempt is denied unless the durable state proves the first request was never submitted. Ambiguous outcomes enter reconciliation, never blind retry.

## Immutable L2 mission record

Before specialist dispatch, the mission record binds:

- program ID, gate ID, mission ID, request ID, request hash, and creation time;
- independently verified Principal ID, session ID, verification method, and validity window;
- purpose, requested outcome, informational operations, prohibited operations, consequence ceiling, and cancellation authority;
- time, token, cost, specialist, model, tool, memory, and side-effect budgets;
- allowed memory collections, time horizon, data classification, result limit, and retrieval-policy version;
- required specialist roles and isolation policy;
- candidate model policy and provider/data constraints;
- policy-set hashes and authority-snapshot hash;
- required capability properties but no implicit capability grant;
- required evidence types, readback independence, brief requirements, expiry, and kill-switch state.

All fields are canonicalized and hashed. A later component may only narrow them. Material mutation creates a new mission version and invalidates downstream approvals.

## Governing records

| Record | Authority semantics |
|---|---|
| `PrincipalIdentityRecord` | Establishes who may approve; grants no action by itself. |
| `MissionScopeRecord` | Maximum mission boundary; cannot be enlarged by downstream records. |
| `MemoryRetrievalRecord` | Context and provenance only; `authority_delta = 0`. |
| `SpecialistGrant` | Non-transitive advisory grant; `side_effect_budget = 0`. |
| `SpecialistResult` | Sealed claims/evidence/uncertainty; cannot authorize. |
| `ModelDecisionRecord` | Model/provider/version/rationale/budget; `authority_delta = 0`. |
| `PolicyDecisionRecord` | Mechanical allow/deny/approval-required result against frozen policies. |
| `AuthoritySnapshot` | Principal-authorized scope ceiling before approval; side-effect authority remains zero until exact approval. |
| `ActionEnvelope` | Exact proposed capability, target, parameters, evidence requirements, execution ID, nonce, and baseline identity. |
| `PrincipalApprovalRecord` | Single-use approval of the exact action-envelope hash. |
| `CapabilityResolutionRecord` | Exact certified adapter, entrypoint, provider class/mode, credential binding, and no-fallback declaration. |
| `ProviderAttemptRecord` | Durable pre-I/O attempt counter and request hash. |
| `ProviderReceiptRecord` | Raw provider ID, timestamp, response hash, and target. |
| `ReadbackVerificationRecord` | Independent observation of provider state and exact expected-state comparison. |
| `AuthorityConsumptionRecord` | Consumes nonce and authority permanently. |
| `EvidenceSealRecord` | Hash-chain root and package-manifest hash. |
| `PrincipalBrief` | Human-readable result derived only from sealed evidence; grants no further authority. |

## State machine

```text
RECEIVED
→ PRINCIPAL_IDENTIFIED
→ MISSION_SCOPED
→ MEMORY_RESOLVED
→ WORKFORCE_SELECTED
→ SPECIALISTS_DISPATCHED
→ SPECIALISTS_RECONCILED
→ MODEL_SELECTION_RESOLVED
→ POLICY_RESOLVED
→ AUTHORITY_RESOLVED
→ ACTION_PROPOSED
→ APPROVAL_REQUIRED
→ APPROVED
→ CAPABILITY_RESOLVED
→ READY
→ EXECUTING
→ VERIFYING
→ EVIDENCE_RECONCILIATION
→ BRIEF_GENERATED
→ COMPLETE
```

Terminal/interruption states:

`IDENTITY_AMBIGUOUS`, `MISSION_SCOPE_INVALID`, `MEMORY_POLICY_DENIED`, `SPECIALIST_SCOPE_VIOLATION`, `MODEL_POLICY_DENIED`, `POLICY_DENIED`, `AUTHORITY_MISSING`, `APPROVAL_INVALID`, `APPROVAL_EXPIRED`, `CAPABILITY_UNAVAILABLE`, `EXECUTION_AMBIGUOUS`, `EXECUTION_FAILED`, `VERIFICATION_FAILED`, `EVIDENCE_INCOMPLETE`, `CANCELLED`.

No terminal failure state may transition to `EXECUTING` or `COMPLETE`. Recovery requires a new governed record and, after action-envelope creation, normally a new envelope and approval.

## Stage contracts

### 1. Request and Principal identity

Capture exact request bytes/transcript, request hash, timestamp, channel, and ambiguity/confidence evidence. Principal identity must be independently current; voice, model inference, memory, or a specialist assertion cannot establish identity.

### 2. Mission scope

Create a consequence-bounded mission before retrieving memory or dispatching specialists. Side-effect budget is initially zero. The mission may describe properties needed from a future capability but cannot infer authority from the request.

### 3. Workforce selection and specialist isolation

Select at least two independent roles: a domain/status specialist and an authority/risk specialist. Each receives enumerated, hashed input, a fresh context/workspace, read/advisory tools only, and no credentials. The orchestrator may route evidence but may not silently share mutable hidden state.

### 4. Living-memory retrieval

Retrieval binds Principal, tenant, mission, purpose, collections, classification, query hash, item versions/hashes, and selection rationale. Untrusted or contradictory content is surfaced. Every retrieval record asserts `authority_delta = 0` and cannot modify scope, tool policy, approval grammar, or capability selection.

### 5. Model selection

Model routing occurs per specialist/task and records candidate models, selected model/provider/version, data policy, budgets, fallback chain, and rationale. Fallback must remain within frozen policy. A switch of model or provider cannot affect the authority snapshot or action envelope except by producing a new advisory output that is separately reconciled.

### 6. Policy and authority resolution

Policy resolution evaluates the reconciled proposal mechanically against mission scope, consequence, data, provider, budget, and evidence policies. Authority resolution computes the maximum allowed action properties from current Principal authority. Neither stage creates approval. Deny or ambiguity blocks.

### 7. Proposal and Principal approval

The action envelope contains exact capability ID, adapter, entrypoint, provider class/mode, account, destination, operation, method, endpoint, body/parameters and hashes, baseline commit/tree/source-manifest, execution ID, nonce, expiry, max executions, and evidence requirements. Principal approval binds its canonical hash. Any material difference or expiry invalidates approval.

### 8. Capability resolution and readiness

Immediately before I/O, verify exact certified capability identity, live provider, credential/account/installation boundary, target state, duplicate state, clean frozen runtime path, envelope hash, nonce state, side-effect count, and kill switches. Alternate, alias, mock, dry-run, or auto-generated execution identity is denied.

### 9. One bounded side effect

Persist an atomic provider-attempt record before I/O. Execute only through the canonical entrypoint. The side-effect budget is exactly one. Timeout or connection ambiguity enters reconciliation using read-only provider inspection; it never authorizes a second blind POST.

### 10. Provider readback and verification

Use a read path that is logically separate from the executor's success return. Bind real provider object ID, account/author, target, timestamp, exact body/parameters, expected-state hash, exact-match count, and additional-write count. A mock or self-reported receipt cannot satisfy this stage.

### 11. Hashed evidence and Principal Brief

Seal all required records into a tamper-evident chain and package manifest. Consume nonce and authority. Generate written/spoken brief from sealed evidence only, disclosing result, side effects, uncertainty, provider receipt, evidence root, consumed authority, and residual blockers. Missing required evidence produces `EVIDENCE_INCOMPLETE`, never `COMPLETE`.

## L1 isolation and operational disclosures

- L1 remains `PASS / RATIFIED / CLOSED / FROZEN`; its consumed authority is not an L2 input.
- L1 execution-source manifest remains unchanged; untracked `sintra_live/github_live/auth.py` and `dry_run.py` have no L1 or L2 authority unless separately reviewed.
- `OPS_INFERENCE_CONFIG_DRIFT = OPEN`, `L1_CERTIFICATION_IMPACT = NONE`, `CRON_FAIL_CLOSED_BEHAVIOR = PASS`, and `UNINTENDED_SPEND_PREVENTED = TRUE`. The affected cron model/provider contract must be reviewed separately and is not silently migrated.

## Design-gate completion rule

`PASS` requires a complete, internally consistent contract, acceptance plan, gap analysis, and hashed design manifest, with zero implementation and zero external side effects. `FAIL` means a contract permits authority expansion or side-effect bypass. `INCOMPLETE` means required design evidence is missing.

This document grants no implementation or live-execution authority.
