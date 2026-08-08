# Assumption and Uncertainty Model

## Uncertainty Registry (§66)

```text
UncertaintyItem:
  id, uncertainty_type, description, source
  created_at, resolved, resolved_at, resolution
```

Types:

```text
UNKNOWN
ASSUMPTION
DISPUTED_FACT
MISSING_EVIDENCE
UNVERIFIED_DEPENDENCY
IMPLEMENTATION_RISK
```

Persisted until resolved. `list_open()` surfaces open items for
Mission Control. Proof: `test_register_and_resolve`.

## Assumption Ledger (§67)

```text
Assumption:
  id, assumption, source, owner
  status (ACTIVE | CONFIRMED | INVALIDATED | SUPERSEDED)
  dependencies, created_at
```

Lifecycle: register → confirm/invalidate; supersession replaces
without silent deletion. Proof: `test_assumption_lifecycle`.

## Confidence Separation (§65)

The architecture stores `decision_confidence` and
`evidence_confidence` separately; `EvidenceScorer` (lineage module)
quantifies evidence, while decision confidence stays with the agent.
Mission Control surfaces the mismatch (CF-2 UI).

## Contradictions and Dissent (§70–71)

ContradictionRecord and dissent preservation are deferred to CF-2
(council surface); the UncertaintyItem DISPUTED_FACT type and the
assumption ledger provide the persistence substrate now.
