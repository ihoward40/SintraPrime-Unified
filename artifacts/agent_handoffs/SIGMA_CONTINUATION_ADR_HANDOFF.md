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

Status: BRANCH CREATED — AWAITING AUTHORIZATION TO DRAFT ADR BODY

Current agent: Hermes

Current task: Create the initial handoff record only. Do not draft the ADR body until separately authorized.

## Validation

| Gate | Result | Notes |
|---|---|---|
| CI | N/A | No code changes; documentation branch only |

## Next Required Action

1. Receive authorization to draft the ADR-MC-001 body
2. Draft the ADR under the authorized scope above
3. Submit for Sigma review and owner approval
4. Ratify and merge
5. Implement the ratified criteria (separate branch, separate authorization)

## Handoff Receipt

Outgoing agent: Hermes

Branch: feat/sigma-executor-continuation-adr

Base: 97bd539f82ee9099003b0ba5c3729092bf470604 (main, post-merge)

Baseline tag: mission-control-foundation-v1

Sigma gate: BLOCKED

Deployment: NOT AUTHORIZED

Phase 3B: BLOCKED

Handoff time: 2026-08-05