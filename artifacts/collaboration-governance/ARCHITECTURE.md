# Phase CF-1 / Governance Expansion — Architecture

## Place in the Hierarchy

```text
PRINCIPAL
  ↓
MISSION CONTROL
  ↓
GOVERNANCE / POLICY ENGINE            ← this increment extends (REUSE governance/)
  ↓
GOVERNED ORCHESTRATOR
  ↓
COLLABORATIVE AGENT FABRIC            ← fabric foundation (PR #276) + governance expansion (this PR)
  ↓
GOVERNED WORKFLOW RUNTIME             ← Phase 5A (PR #275)
  ↓
AGENT / MODEL / TOOL EXECUTION
```

OmniBrain sits beside the execution plane as governed memory
(Phase CF-4).

## Layers (directive §4)

- **Layer A — Mission Control:** human surface; existing portal.
- **Layer B — Governance Plane:** extended with machine-enforceable
  constitutional invariants, governance linter, goal-drift detector.
- **Layer C — Collaborative Agent Fabric:** fabric foundation plus
  quarantine, dead-letter, capability leases, effect receipts,
  causal records, DLP.
- **Layer D — Governed Workflow Runtime:** Phase 5A (separate PR).
- **Layer E — OmniBrain:** Phase CF-4.

## New Modules (`collaboration/governance/`)

| Module | Directive | Responsibility |
|---|---|---|
| `invariants.py` | §2, §20 | 20 machine-enforceable constitutional invariants + static workflow checks |
| `dead_letter.py` | §22–23 | DeadLetterEvent, bounded retry, poison-event quarantine |
| `quarantine.py` | §47 | AgentQuarantineRecord; no new activations; diagnostic-only |
| `capability_lease.py` | §108 | CapabilityLease; purpose/scope/expiry enforced |
| `lineage.py` | §62–64 | LineageClass tags, taint propagation, evidence scorer |
| `uncertainty.py` | §66–67 | UncertaintyItem registry + AssumptionLedger |
| `effect_receipts.py` | §20, §117 | Immutable effect receipts, idempotency keys |
| `budget_governor.py` | §34 | Hard token/call/cost limits → BLOCKED_BUDGET |
| `causal.py` | §89–90 | Why-Did-This-Happen causal records |
| `linter.py` | §86–87 | GovernanceLinter + ArchitectureLinter |
| `goal_drift.py` | §93–94 | GoalDriftDetector + ScopeCreepDetector |
| `dlp.py` | §111 | Outbound DLP: secrets, wrong tenant/matter |

## Wired into the Fabric

- `EventPolicyEngine` gains optional `quarantine_service` and
  `invariant_engine` gates (3a/3b in the deterministic chain).
- `EventDispatchStatus` gains `SKIPPED_QUARANTINE` and
  `BLOCKED_INVARIANT`.
- `EventDispatcher` maps quarantine/invariant skips to the new
  statuses.
- Existing fabric gates (tenant, event type, loop guard, dedup,
  rate limit, concurrency, kill switch) are untouched.

## Tests

133 total (61 fabric + 72 governance), all passing.
