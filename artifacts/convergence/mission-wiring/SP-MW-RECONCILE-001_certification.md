# SP-MW-RECONCILE-001 — FINAL CERTIFICATION

**Base:** `f9c7faaec3831c60fd531bfd57a82ecb965a0cc6` (corrected W4-4)
**Commit:** `f0d5a24eb5513f9c261e7b5256604d3b2990d4aa` (15 files, +3089)
**Outcome: PASS**

## Frozen-diff integrity

```text
FROZEN_DIFF_REAPPLIED          = TRUE (fresh worktree r2 @ f9c7faae; 14/14 file-set identical)
frozen hash 5636ac4de22eb184…  = NOT byte-reproducible (recorded pre-lint; ruff --fix
                                  normalization in the W4-4-FIX lane touched 2 files)
DEVIATION CLASSES              = 2 EXPECTED_CONTEXT_DRIFT (cosmetic lint) + 1 UPSTREAM_W4_4_ADAPTATION
UNAUTHORIZED_SCOPE_EXPANSION   = 0
```

## C1–C6 re-certified against f9c7faae

```text
C1 = PASS  vocabulary registry-derived via CapabilityResolver; no private map; no KNOWN_CAPABILITIES fallback
C2 = PASS  envelope + receipt capability identity canonicalized through the W4-4 boundary
C3 = PASS  approval = AuthorityApprovalService binding only; exactly-once consume in runner
C4 = PASS  lazy mechanism: constructor imports nothing, launches nothing; factory post-gate
C5 = PASS  max_actions decremented per gated action; BUDGET_EXHAUSTED on exceed
C6 = PASS  exclusions verified (ZD evidence-lock, duplicate negative_outcome, origin_adapters)
```

## Adversarial approval boundary (new permanent file, 11 tests)

```text
ENVELOPE_APPROVAL_STATE_ONLY = REFUSE      FORGED_APPROVAL_ID = REFUSE
WRONG_MISSION / WRONG_ACTOR / WRONG_TENANT / WRONG_CAPABILITY / WRONG_RESOURCE = REFUSE
EXPIRED_APPROVAL = REFUSE                  REPLAYED_APPROVAL = REFUSE
AUTHORITY_SERVICE_ISSUED_APPROVAL = ACCEPT
VALID_APPROVAL_CONSUMED_ONCE = PASS        SECOND_CONSUMPTION = REFUSE
CARRIER_STATE ≠ AUTHORITY_STATE — enforced, tested, permanent
```

## Test-contract migration (legitimate, no authority weakening)

9 tests migrated from carrier-state approvals to real `AuthorityApprovalService` bindings.
Refusal-class expectations updated where the stronger contract legitimately changes the
failure class (`CAPABILITY_NOT_APPROVED`, `APPROVAL_REQUIRED`) — each annotated in-file.

## Certification matrix (all JUnit-counted)

```text
MISSION_WIRING  = 96/96 (96 passed, 0 failed, 0 errors, 0 skipped)
W4-4 FOCUSED    = 15/15 (dependency gate: RESOLVED_CAPABILITY_SURVIVES_STATUS_GATE PASS,
                         STATUS_GATE_DOES_NOT_REPLACE_CANONICAL_IDENTITY PASS)
AGENT_RUNTIME   = 210/210 (210/0/0/0)
SWARM CANONICAL = 177/177 (177/0/0/0)
PORTAL          = 88 passed / 0 failed / 0 errors / 2 skipped (JUnit 90/0/0/2, exit 0)
DEFAULT         = 563/563 (563/0/0/0)
RUFF            = PASS (agent_runtime + mission_wiring)
```

Swarm lane note: one concurrent-run collision (acceptance_003/004 spawn real git worktree
subprocesses; they collided with the parallel default lane). Classified ENVIRONMENT /
nondeterministic-concurrency per RESILIENCE doctrine; serial + isolated reruns both 177/177.

## Architecture confirmations

```text
SECOND_AUTHORITY_KERNEL                = FALSE (runner is an adapter; approval service = THE validator)
PRIVATE_CAPABILITY_VOCABULARY          = FALSE (registry-derived)
LEGACY_KNOWN_CAPABILITIES_FALLBACK     = FALSE
ENVELOPE_STATE_ACCEPTED_AS_APPROVAL    = FALSE
PRE_GOVERNANCE_EXTERNAL_CONTACT        = FALSE (AST-verified gate-before-mechanism; lazy factory)
FORGED_AUTHORITY_ACCEPTANCE            = 0
BUDGET                                 = action-count decrement per gated action (pre-contact refusals do not spend)
```

## Sealed

```text
RECONCILED_COMMIT_SHA = f0d5a24eb5513f9c261e7b5256604d3b2990d4aa
PARENT                = f9c7faaec3831c60fd531bfd57a82ecb965a0cc6
FILES                 = 15 (6 production + 9 test incl. adversarial matrix)
```

## Promotion rule (adopted per directive)

```text
UNIT_CERTIFIED → INTEGRATION_CERTIFIED → PUBLICATION_CANDIDATE → PUBLISHED → SUPERSEDED
INTEGRATION_PROMOTION_GATE: a component certificate does not become a publication
certificate until its first real downstream consumer passes.
W4-4 = INTEGRATION_CERTIFIED (via mission-wiring consumer); mission_wiring = UNIT_CERTIFIED.
```

## Controlling state

```text
W4-5 = READY_FOR_AUTHORIZATION (the governed browser boundary now exists on the
       current production lineage; publication of mission_wiring is bundled with
       the W4-5 implementation decision)
PUSH / PR / MERGE / DEPLOYMENT = NOT AUTHORIZED
ZD-005 / SP-DEPLOY-TARGET-001 = NOT OPENED
```
