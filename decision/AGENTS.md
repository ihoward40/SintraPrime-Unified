# decision/ — SP-SYSTEM-ONE-DECISION-FABRIC-001 (R1)

Vendor-neutral Decision Fabric. Jev (`typesafe-ai/jev`) is the first provider, never a dependency.

## Constitution
> Probability may select a workflow. Probability may not create authority.

## Layout
- `canonical/jcs.py` — RFC 8785/JCS-class canonicalization + `state_sha256`
- `contracts/contracts.py` — semantic contract normalization + `semantic_contract_sha256`
- `engine/types.py` — `Primitive` (choice|score|boolean), `ResultKind`, `Answer`, `DecisionResult`, `DecisionContract`
- `engine/engine.py` — `DecisionEngine` facade (provider → policy → ledger)
- `providers/base.py` — `DecisionProvider` Protocol (only extension point)
- `providers/mock.py` — `MockDecisionProvider` (deterministic, fault-injectable)
- `providers/jev/provider.py` — `JevDecisionProvider` (Noul contained here; fail-closed)
- `providers/config.py` — safe defaults + provenance-bearing overrides
- `policy/policy.py` — `SHADOW_ONLY` default; fail-closed
- `ledger/ledger.py` — hash-chained append-only receipts
- `security/untrusted.py` — trust-segmented state; bidi/control sanitization

## Invariants (all under test)
1. Canonical vocabulary `choice|score|boolean`; Jev `Noul` exists only inside `providers/jev/`.
2. `state_sha256` = SHA-256 of JCS-canonical `{"canonical_version":"sp-decision-state-v1","state":{...}}`.
3. `semantic_contract_sha256` insensitive to formatting/comments/quoting/key order; sensitive to choice/threshold/risk/question changes.
4. Full distributions persist with top-1, top-2, margin (=top1−top2), and a separate provider confidence.
5. ABSTAIN is first-class; every provider failure mode → `FALLBACK_HERMES`. No fail-open path.
6. Untrusted content sanitized (control + bidi stripped) and segmented; never reaches contract/schema/policy/authority.
7. Safe defaults: `PROVIDER=mock`, `SHADOW_ONLY=1`. Unknown provider → mock. Live Jev requires explicit config.

## R1 boundaries honored
No live steering, no production routing, no promoted thresholds, no autonomous execution.
