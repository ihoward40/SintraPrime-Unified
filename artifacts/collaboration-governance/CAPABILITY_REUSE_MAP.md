# Capability Reuse Map

Reconnaissance classification for every governance-expansion component
(directive §3). No duplicates introduced.

## Existing Infrastructure Inspected

| Component | Location | Status |
|---|---|---|
| Mission Control | `portal/` | REUSE (unchanged) |
| Governance engine | `governance/governance_engine.py` | REUSE — invariants extend the same plane |
| Approval gate | `governance/approval_gate.py` | REUSE (unchanged) |
| Audit trail | `governance/audit_trail.py` | REUSE (unchanged) |
| Risk assessor | `governance/risk_assessor.py` | REUSE (unchanged) |
| Compliance monitor | `governance/compliance_monitor.py` | REUSE (unchanged) |
| Intervention controller | `governance/intervention_controller.py` | REUSE (unchanged) |
| Receipt hash-chain pattern | `portal/services/mission_control_command_service.py` | REUSE — pattern applied in effect receipts |
| JSON persistence | `workflow_runtime/checkpoint.py`, `collaboration/services/store.py` | REUSE |
| Fabric foundation | `collaboration/` (PR #276) | REUSE — extended |
| Workflow runtime | `workflow_runtime/` (PR #275) | DEFER (separate PR) |
| OmniBrain | `portal/omnibrain*` / Phase 9 | DEFER (CF-4) |
| PostgreSQL migrations | `portal/` migrations | DEFER (CF-2) |
| Frontend | `apps/sintraprime/` | DEFER (§XLIV, CF-2) |

## New Components (not previously present anywhere)

| Component | Classification | Why NEW |
|---|---|---|
| Constitutional invariant engine | NEW | no invariant enforcement existed |
| Dead-letter queue | NEW | no DLQ/outbox found |
| Poison-event quarantine | NEW | no quarantine existed |
| Agent quarantine service | NEW | no agent-level quarantine existed |
| Capability leases | NEW | no lease primitive existed |
| Lineage/taint tracker | NEW | no taint model existed |
| Uncertainty registry | NEW | no uncertainty model existed |
| Assumption ledger | NEW | no assumption ledger existed |
| Effect receipts | NEW | only event/activation receipts existed (fabric) |
| Budget governor | NEW | hard budget enforcement absent in fabric |
| Causal store | NEW | no Why-Did-This-Happen API existed |
| Governance linter | NEW | no linter found in repo |
| Architecture linter | NEW | no architecture linter found |
| Goal-drift detector | NEW | no drift detection existed |
| Scope-creep detector | NEW | no creep detection existed |
| Outbound DLP scanner | NEW | no DLP existed |

## Avoided Duplication

- Did **not** create a second governance engine — reused `governance/`
  plane and only added orthogonal primitives.
- Did **not** re-implement event/activation receipts — fabric already
  has them; this PR adds the missing **effect** receipt (§117).
- Did **not** re-implement dedup/anti-loop — fabric has them; the
  invariant engine references the same loop-bounding semantics.
- Did **not** touch Phase 5A runtime or Phase 9 OmniBrain.
