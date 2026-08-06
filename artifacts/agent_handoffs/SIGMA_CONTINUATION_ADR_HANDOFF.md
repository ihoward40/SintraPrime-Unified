# SIGMA EXECUTOR CONTINUATION ADR — HANDOFF RECORD

## Branch

- Branch: feat/sigma-executor-continuation-adr
- Base: main at 97bd539f82ee9099003b0ba5c3729092bf470604
- Baseline tag: mission-control-foundation-v1
- Worktree: C:/Users/admin/Desktop/Projects/sigma-adr-branch
- Created: 2026-08-05
- Created by: Hermes

## Governance Context

- ADR-002: ACCEPTED and merged to main (PR #256, merge commit 22b384a7)
- Mission Control Foundation: MERGED to main (PR #258, merge commit 97bd539f)
- Baseline tag: mission-control-foundation-v1 at 97bd539f
- Sigma gate: BLOCKED — SIGMA_LEASE_EXPIRY_CONTINUATION_GATE
- Phase 3B: BLOCKED pending Sigma gate satisfaction
- Deployment: NOT AUTHORIZED

## Purpose

This branch carries the Sigma Executor Continuation ADR (ADR-MC-001) — the
architectural decision record that defines explicit criteria for executor
continuation after lease expiry during Brain unavailability.

This is the mandatory gate defined by ADR-002 Section 2.5 and carried forward
through the Mission Control Foundation review cycles. The Sigma gate cannot
transition from BLOCKED to SATISFIED until this ADR is ratified and its
criteria are implemented and certified.

## Authorized Scope

This branch is documentation and architecture only.

- Executor continuation after lease expiry
- Brain-unavailability decision criteria
- Reconciliation requirements
- Conflicting executor result handling
- Policy snapshot validity
- Side-effect safety
- Completion receipts
- Recovery reporting
- Acceptance tests and governance gates

## Prohibited Actions

- No executor implementation
- No cancellation activation
- No command authority
- No deployment
- No Phase 3B
- No changes to unrelated worktrees
- Do not modify ADR-002 (accepted and frozen)
- ADR body has been written and corrected; no further ADR edits unless authorized

## ADR-002 Section 2.5 — Sigma Condition

The Sigma condition from ADR-002 requires:

> Define explicit criteria for executor continuation after lease expiry
> during Brain unavailability, including mandatory reconciliation and
> completion reporting when the Brain recovers.

The ADR-MC-001 must address:

1. Explicit criteria for when optional executor continuation is permitted after lease expiry
2. What constitutes "local state sufficient to complete the task"
3. Mandatory completion reporting on Brain recovery
4. Reconciliation between executor-reported state and Brain ledger on recovery
5. Handling of conflicting results if multiple executors continued during unavailability

## Current Work State

Status: ADR-MC-001 RATIFIED — ACCEPTED 2026-08-05

Current agent: Hermes

Current task: ADR-MC-001 ratified by architecture review APPROVE. Status changed from DRAFT to ACCEPTED. Implementation remains NOT AUTHORIZED. Sigma gate remains BLOCKED.

## Validation

| Gate | Result | Notes |
|---|---|---|
| CI | PENDING | Documentation branch only; waiting for terminal state |
| Scope check | PASS | Document defines architecture and governance only; no implementation |
| Prohibition check | PASS | No code, no cancellation activation, no command authority, no deployment, no Phase 3B |

## Review Cycle 1 — REQUEST CHANGES (2026-08-05)

Review blockers identified and resolved:

1. **Expired lease authority contradictory** — RESOLVED by introducing a distinct Continuation Capability (Section 2.1.4), separate from the lease token, unusable before lease expiry, and validated by downstream systems.
2. **Duplicate-suppression keys unsafe** — RESOLVED by defining stable external-effect identity `(command_id, operation_id, side_effect_slot)` and treating `continuation_id` as metadata only (Section 2.5).
3. **Replay semantics can duplicate side effects** — RESOLVED by requiring reconciliation before replay, giving replay a new execution identity while preserving original external-effect identities (Section 2.7).
4. **"First completed wins" not a conflict policy** — RESOLVED by separating result selection, effect reconciliation, compensation, and manual review (Section 2.6).
5. **Witness model undefined** — RESOLVED by fully defining independent control-plane witnesses, quorum, self-exclusion, replay resistance, and stale/compromised witness handling (Section 2.2.4).
6. **Clock and time authority missing** — RESOLVED by adding trusted time source, signed anchors, monotonic time, skew tolerance, and rollback handling (Section 2.8).
7. **Policy validity unprovable during outage** — RESOLVED by replacing "policy has not been superseded" with a pinned policy snapshot hash and bounded validity in the capability (Section 2.11).
8. **Revocation/cancellation cache not authoritative** — RESOLVED by adding revocation watermark, cache-age limit, fail-closed rules, and default STOP for high-risk commands (Section 2.10).
9. **Side-effect safety too permissive** — RESOLVED by classifying side effects as Class 0–3 and prohibiting Class 3 (irreversible/high-risk) during continuation (Section 2.9).
10. **Audit-chain truncation mixed into authority** — RESOLVED by clarifying that the authoritative audit ledger is never truncated; only read projections may paginate/truncate (Section 2.13).

## Review Cycle 2 — APPROVE_WITH_CONDITIONS (2026-08-05)

Architecture approved with four conditions. All conditions are documentation-only corrections; no runtime code required.

1. **Capability rotation/supersession** — RESOLVED by adding lease-renewal rules: renewal invalidates prior capability, only latest-lease capability may be exercised, rotation is auditable, revocation applies even with later not_valid_after, downstream rejects superseded capability IDs (Section 2.1.2). Added invariant 3a (Section 7).
2. **Replay identity using root_command_id** — RESOLVED by defining root_command_id as the original command, requiring all replayed operations to derive effect identity from it, never from the replay-attempt command record (Section 2.7). Added replay identity rule to Section 2.5.1 and root_command_id to glossary (Section 8).
3. **Witness fault model and quorum math** — RESOLVED by replacing vague Byzantine claim with explicit fault model: N >= 3f+1, quorum >= 2f+1 for BFT; or N >= 2f+1, quorum >= f+1 for CFT with explicit documentation. Quorum must be strictly less than N in either model (Section 2.2.4).
4. **Time-anchor language for outage expiry** — RESOLVED by clarifying that signed anchor at lease-expiry instant is not required; executor derives expiry from latest pre-outage anchor plus monotonic elapsed time; monotonic discontinuity or excessive drift forces STOP (Section 2.8).

## Ratification (2026-08-05)

Architecture review decision: APPROVE.

- All four review cycle 2 conditions verified as resolved.
- ADR-MC-001 status changed from DRAFT to ACCEPTED.
- Ratified by: Isiah Howard — architecture review APPROVE (PR #259 ratification review).
- Architecture approval opens the implementation-planning gate; it does not unblock the Sigma gate, enable cancellation, enable command authority, authorize deployment, or begin Phase 3B.
- SIGMA_LEASE_EXPIRY_CONTINUATION_GATE remains BLOCKED until implementation is certified.
- Implementation remains NOT AUTHORIZED.

## Changes Completed

- Rewrote docs/mission-control/ADR_MC_001_EXECUTOR_CONTINUATION.md to address all review blockers.
- Updated handoff record with actual HEAD SHA and tree SHA after commit.

## Next Required Action

1. Wait for all CI workflows to reach terminal state.
2. Submit corrected ADR-MC-001 for next review cycle.
3. Do not mark ready for review until review accepts the corrections.

## Handoff Receipt

Outgoing agent: Hermes

Branch: feat/sigma-executor-continuation-adr

Current HEAD: pending ratification commit

Tree SHA: pending ratification commit

Base: 97bd539f82ee9099003b0ba5c3729092bf470604 (main, post-merge)

Baseline tag: mission-control-foundation-v1

ADR draft: docs/mission-control/ADR_MC_001_EXECUTOR_CONTINUATION.md

Sigma gate: BLOCKED

Deployment: NOT AUTHORIZED

Phase 3B: BLOCKED

Implementation: NOT AUTHORIZED

Handoff time: 2026-08-05