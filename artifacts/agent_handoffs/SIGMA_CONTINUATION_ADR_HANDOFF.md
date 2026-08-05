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
- Do not begin the ADR body until separately authorized

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

Status: ADR-MC-001 DRAFTED — AWAITING REVIEW AND RATIFICATION

Current agent: Hermes

Current task: Draft the ADR-MC-001 body under the authorized scope. The draft is complete and located at docs/mission-control/ADR_MC_001_EXECUTOR_CONTINUATION.md.

## Validation

| Gate | Result | Notes |
|---|---|---|
| CI | N/A | No code changes; documentation branch only |
| Scope check | PASS | Document defines architecture and governance only; no implementation |
| Prohibition check | PASS | No code, no cancellation activation, no command authority, no deployment, no Phase 3B |

## Changes Completed

- Drafted docs/mission-control/ADR_MC_001_EXECUTOR_CONTINUATION.md with:
  - Executor lease lifecycle (acquisition, renewal, expiry)
  - Brain outage detection
  - Continuation eligibility criteria
  - Continuation limits
  - Idempotency requirements
  - Reconciliation protocol
  - Replay semantics
  - Duplicate suppression
  - Completion receipts
  - Split-brain handling
  - Audit chain requirements
  - Tenant isolation guarantees
  - Recovery protocol
  - Sequence diagrams, state-machine diagrams, timing diagrams
  - Failure matrices and threat model
  - Invariants, glossary, implementation prerequisites
  - Explicit non-goals
  - Acceptance criteria

## Next Required Action

1. Submit ADR-MC-001 for Sigma review and owner approval
2. Iterate on review feedback
3. Ratify and merge
4. Open implementation branch (separate authorization) for the components listed in Section 9.1

## Handoff Receipt

Outgoing agent: Hermes

Branch: feat/sigma-executor-continuation-adr

Current HEAD: 2900d3c90a87b850d2c6ce7d1a00ef792a9f99f9

Base: 97bd539f82ee9099003b0ba5c3729092bf470604 (main, post-merge)

Baseline tag: mission-control-foundation-v1

ADR draft: docs/mission-control/ADR_MC_001_EXECUTOR_CONTINUATION.md

Sigma gate: BLOCKED

Deployment: NOT AUTHORIZED

Phase 3B: BLOCKED

Implementation: NOT AUTHORIZED

Handoff time: 2026-08-05