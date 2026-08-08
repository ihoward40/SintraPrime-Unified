# collaboration/governance — Collaborative Agent Governance Foundation

## Purpose

Machine-enforceable constitutional invariants, failure recovery
(dead-letter queue, poison quarantine), agent quarantine, ephemeral
capability leases, trust/lineage tracking, assumption/uncertainty
registers, governance linter, causal explanation, effect receipts,
budget governor, and outbound DLP. Extends the collaborative agent
fabric with governance controls that no agent, workflow, prompt, or
plugin can override.

## Ownership

- `collaboration/governance/` — all governance expansion modules
- `collaboration/tests/test_governance.py` — 72 governance tests
- `artifacts/collaboration-governance/` — evidence packet

## Local Contracts

- Every event dispatch passes through `InvariantEngine` (step 3b) and
  `AgentQuarantineService` (step 3a) before any model call.
- A quarantined agent receives no new activations, regardless of
  subscription.
- Effect receipts are idempotent: same idempotency_key → same receipt.
- Budget governor hard-blocks at limit; no PAUSED_BUDGET for refused
  spends.
- The governance linter rejects unbounded loops, missing budgets,
  self-certification, and privileged public agents in static
  inspection.
- This evidence packet is implementer-produced; independent
  certification requires a separate session (§73, §132).

## Work Guidance

*(No specific guidance in this subtree beyond the above.)*
