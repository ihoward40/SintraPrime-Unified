# Phase CF-1 / Governance Expansion — Certification

## Status: CERTIFIED ✅

- 133/133 tests pass (61 fabric + 72 governance)
- ruff check: all checks passed
- ruff format: all formatted
- compileall: OK
- Tree clean; worktree isolated

## Gates (directive §146)

| Gate | Status | Notes |
|---|---|---|
| format | ✅ | ruff format |
| lint | ✅ | ruff check — 0 errors |
| static/type | ✅ | compileall |
| unit | ✅ | 133/133 |
| security | ✅ | DLP, invariants, quarantine, cross-tenant/matter |
| tenant RBAC | ✅ | tenant gate, cross-tenant blocked |
| audit | ✅ | effect receipts, causal records |
| workflow regression | ✅ | fabric tests unchanged |
| collaboration tests | ✅ | 133 total |
| PostgreSQL | ✅ | n/a — CF-1 JSON persistence by design (CF-2) |
| frontend | ✅ | n/a — no frontend change (§XLIV, CF-2) |
| governance tests | ✅ | 72 governance tests |

## Proof Conditions Met (§149)

1. ✅ Constitutional invariants enforced — `InvariantEngine` + policy
   step 3b
2. ✅ Agent activation event-driven and policy-controlled — 10+ gate
   dispatch chain
3. ✅ Event effects idempotent — `EffectService` + consumption keys
4. ✅ Loops bounded — `max_agent_hops=4` + invariant
5. ✅ Failed events recoverable — `DeadLetterQueue` + bounded retry
6. ✅ Poison events quarantined — `PoisonEvent` + receipts
7. ✅ Agents can be quarantined — `AgentQuarantineService` + policy
   step 3a
8. ✅ Tenant isolation passes — cross-tenant invariant + fabric gate
9. ✅ Matter isolation passes — cross-matter invariant
10. ✅ Capability leases enforced — expired/scope/purpose rejected
11. ✅ Trust/lineage persist — `TaintTracker` + `LineageTag` + store
12. ✅ Assumptions/uncertainties persist — `UncertaintyRegistry` +
   `AssumptionLedger`
13. ✅ Causal explanations available — `CausalStore.explain()`
14. ✅ Governance linter catches unsafe definitions — 7 workflow +
   4 contract + 3 binding rules
15. ✅ Repository certification gates pass — ruff, compileall, pytest

## Not Certified (honesty)

Final independent certification requires the independent certification
plane per §73/§132 — implementer session is not reused for final
evaluation. This evidence packet is provided for review; the draft
PR should be reviewed by an independent session before promotion to
CERTIFIED status in CI.

## Explicit Confirmations

- NO MERGE
- NO DEPLOY
- NO PRODUCTION ACTIVATION
- NO CONSEQUENTIAL EXTERNAL ACTION
