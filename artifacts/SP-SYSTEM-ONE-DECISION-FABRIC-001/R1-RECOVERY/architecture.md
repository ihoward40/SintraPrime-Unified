# R1-RECOVERY — Architecture Note

SP-SYSTEM-ONE-DECISION-FABRIC-001 — R1 recovery implementation.

## What exists (post-recovery)

```
decision/
├── AGENTS.md                    subsystem DOX contract
├── canonical/jcs.py             RFC 8785/JCS-class canonicalization + state hashing
├── contracts/contracts.py       semantic contract normalization + semantic hashing
├── engine/types.py              canonical primitives, result kinds, answers, results
├── engine/engine.py             DecisionEngine facade (provider -> policy -> ledger)
├── providers/base.py            DecisionProvider protocol (only extension point)
├── providers/mock.py            MockDecisionProvider (deterministic, fault-injectable)
├── providers/config.py          safe defaults + provenance-bearing overrides
├── providers/jev/provider.py    Jev adapter (Noul contained here; fail-closed)
├── policy/policy.py             SHADOW_ONLY default; mechanics only; fail-closed
├── ledger/ledger.py             hash-chained append-only receipts
├── security/untrusted.py        trust-segmented state; bidi/control sanitization
└── tests/test_r1_conformance.py 49 deterministic conformance tests
```

## Data flow

```
caller -> DecisionEngine.evaluate(state, contract)
        -> provider.evaluate(state, contract)     # protocol seam
             -> DecisionResult(DECISION|ABSTAIN|ERROR|UNAVAILABLE)
        -> apply_policy(result, shadow_only=True) # R1 default: SHADOW_ONLY
             any non-DECISION -> FALLBACK_HERMES  # fail-closed, never execute
        -> build_receipt(...)                     # hashes: state + contract
        -> Ledger.append                          # hash-chained, tamper-evident
```

## Key invariants (all under test)

1. Canonical vocabulary is `choice | score | boolean`; Jev "Noul" exists only
   inside `providers/jev/` (enforced by a source-scan test on core modules).
2. `state_sha256` = SHA-256 of JCS-canonical `{"canonical_version": ...,
   "state": ...}` bytes; number formatting pinned (0/-0/0.1/exponents/int-float
   equivalence); keys sorted in UTF-16 order.
3. `contract_sha256` = SHA-256 of the normalized semantic contract; comments,
   whitespace, quoting, and key order cannot move it; any choice/threshold/
   risk/question change does.
4. Full distributions persist with top-1, top-2, margin (= top1 - top2), and a
   separate provider confidence. Argmax alone never authorizes anything.
5. ABSTAIN is a first-class result; policy maps it (and every provider failure
   mode: timeout/DNS/connection/429/5xx/malformed/unknown-primitive/missing
   fields/schema-contract mismatch) to FALLBACK_HERMES. No fail-open path.
6. Untrusted content is sanitized (control + bidi overrides stripped) and
   segmented (`SYSTEM_CONTEXT | TRUSTED_METADATA | UNTRUSTED_CONTENT |
   DERIVED_FEATURES`); it never reaches contract/schema/policy/authority.
7. Safe defaults: `PROVIDER=mock`, `SHADOW_ONLY=1`. Unknown provider values
   fall back to mock. Live Jev requires explicit env config; `JEV_BASE_URL`
   override produces a provenance event; default is the documented Gateway.

## R1 boundaries honored

No live steering, no production routing, no promoted thresholds (policy
mechanics exist but are unreachable under shadow default), no autonomous
execution, no SP-DEC-013..020.

## Deferred by design

- Persistent external ledger storage (R1 uses the in-memory reference chain;
  production persistence is a later governed increment).
- Live Jev HTTP e2e (adapter transport is injectable; live calls require
  credentials and explicit authorization — neither exists in R1).
- R2 shadow dataset/calibration (separate release per frozen directive).
