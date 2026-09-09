"""Agent runtime contracts (Wave 3, SP-CONVERGE-001).

Canonical typed agent runtime: manifests, registry, delegation, context,
budgets, receipts. Converges with existing substrates:
  - portal/services/orchestration (Role, ProviderCapability, budget_policy)
  - swarm_runtime/capability_lease (scoped, expiring, deny-by-default leases)
  - agents/nova/approval_gateway (approval tiers)
"""
