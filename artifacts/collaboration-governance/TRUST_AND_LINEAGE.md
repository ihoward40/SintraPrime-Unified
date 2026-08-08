# Trust and Lineage Model

## Lineage Classes (§63)

```text
USER_ASSERTED        SYSTEM_OBSERVED      PRIMARY_SOURCE
SECONDARY_SOURCE     EXTERNAL_UNVERIFIED  AGENT_INFERRED
VERIFIED             CERTIFIED            DISPUTED
SUPERSEDED
```

`LineageTag` attaches: artifact_id, lineage_class, source_refs,
provenance, tenant_id, matter_id.

## Authority Taint (§62)

Location does not upgrade provenance.

```text
EXTERNAL_UNVERIFIED copied into a T4 channel
  → remains EXTERNAL_UNVERIFIED
  unless independently verified
```

`TaintTracker.combine()` computes the **weakest** lineage among
inputs; `propagate()` tags derived artifacts. Proven test:
`test_external_unverified_persists`,
`test_combine_weakest` (EXTERNAL_UNVERIFIED + VERIFIED →
EXTERNAL_UNVERIFIED).

## Evidence Quality (§64)

`EvidenceScorer` evaluates: source count, source diversity, primary
source presence, evidence score. Model confidence is stored
separately from evidence quality (§65) — `decision_confidence` vs
`evidence_confidence` are distinct concepts in the architecture;
Mission Control surfaces the mismatch (Phase CF-2 UI).

## Security Compartments (§7)

PUBLIC / BUSINESS / LEGAL / FINANCIAL / PERSONAL / SECRET are the
classification vocabulary for bindings and contracts (fabric
`AgentBehaviorContract.security_compartments`). Trust zones
(T0–T4, fabric `TrustZone`) are channel-level policy inputs.

## Purpose Limitation (§8)

`CapabilityLease` binds capability + scope + purpose + expiry.
Wrong purpose or scope is rejected (`test_wrong_purpose_rejected`,
`test_wrong_scope_rejected`). Purpose is persisted in access receipts
via `CausalRecord.capability_lease_id` and lease records.
