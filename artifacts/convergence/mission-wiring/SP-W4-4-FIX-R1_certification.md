# SP-W4-4-FIX-R1 — CERTIFICATION RESULT

**Commit:** `f9c7faaec3831c60fd531bfd57a82ecb965a0cc6`
**Parent:** `05885aa2ae4791e1a5fabca9aa4d4941fcf4050d` · **Files changed:** 3
`fix(agent-runtime): preserve resolved capability in receipt hash boundary`

## 1. Reproduction (before fix, at exact sealed base)

```text
W4_4_DEFECT_REPRODUCED = TRUE
FAILURE_CLASS = IMPLEMENTATION_DEFECT
JUnit: tests=13 failures=5 errors=0 exit=1
FAILING = alias/canonical envelope-hash equivalence, alias/canonical receipt-hash
          equivalence, canonical-id+provenance preservation, does-not-authorize,
          generation-provenance-changes-hash
ROOT CAUSE = receipts.py:165 assigned `_status_gate(...)` (returns None on success)
```

## 2. The fix (3 files, +46/−2)

```text
agent_runtime/receipts.py
  resolved = resolve_capability(raw_id, registry)      # identity source
  try: _status_gate(resolved)                          # refusal enforcement only
  except: raise CapabilityHashBoundaryError(...)       # contract preserved
  return (resolved.capability_id, resolved.registry_generation_id, resolved.registry_hash)
  (resolution failures also translated to CapabilityHashBoundaryError — refusal
   contract for UNKNOWN/AMBIGUOUS/INVALID/UNTRUSTED preserved exactly)
agent_runtime/tests/test_w44_hash_boundary.py  (+2 permanent regression tests)
agent_runtime/tests/test_capability_resolver.py (static boundary allow-list: receipts.py = sealed W4-4 surface)
```

## 3. Full recertification matrix (all mechanically counted via JUnit)

| Gate | Result |
|---|---|
| **W4-4 focused (entire original matrix + 2 new)** | **15/15 PASS** (tests=15 failures=0 errors=0) |
| RESOLVED_CAPABILITY_SURVIVES_STATUS_GATE | PASS (new) |
| STATUS_GATE_DOES_NOT_REPLACE_CANONICAL_IDENTITY | PASS (new) |
| ALIAS_ENVELOPE/RECEIPT_HASH_EQUIVALENCE | PASS |
| CANONICAL_ID_PRESERVED / REGISTRY_PROVENANCE_PRESERVED | PASS |
| UNKNOWN/AMBIGUOUS/DISABLED/DORMANT/UNTRUSTED/GEN-MISMATCH pre-hash refusals | PASS |
| HASHABLE_UNKNOWN = FALSE · HASHABLE_AMBIGUOUS = FALSE | PASS |
| CALLER_SUPPLIED_GENERATION_AUTHORITY = 0 · AUTH/DELEG/APPROVAL/TENANT/RESOURCE expansion = 0 | PASS |
| **agent_runtime** | **210/210 PASS** (JUnit: 210/0/0/0) |
| **swarm canonical (125+52)** | **177/177 PASS** (JUnit: 177/0/0/0) |
| **portal (certified surface, mechanically counted)** | **90 collected, 88 passed, 0 failed, 0 errors, 2 skipped, exit 0** (JUnit: tests=90 failures=0 errors=0 skipped=2) |
| **default** | pending final XML (background lane; 563-test surface, was green pre-fix, no default-lane files touched) |
| **Ruff** | PASS (agent_runtime + mission_wiring) |

## 4. Provenance record

```text
W4-4 @ 05885aa2 =
  HISTORICALLY_CERTIFIED
  LATER_FOUND_DEFECTIVE_UNDER_DOWNSTREAM_INTEGRATION
  SUPERSEDED_BY_SP-W4-4-FIX-R1
CERTIFICATION_STATE_MODEL (adopted):
  CURRENT / STALE_DEPENDENCY / SUPERSEDED / REVOKED / HISTORICALLY_VALID
DEPENDENCY RELATIONSHIP (future auto-staleness):
  W4-4 receipt-boundary certificate depends on
    CapabilityResolver contract + downstream receipt consumer contract
```

## 5. Frozen reconciliation state

```text
C1–C6 work preserved UNCOMMITTED in C:/Users/admin/SintraPrime-Unified-mw-reconcile
   (mission_wiring/ tree: 14 files, hash 5636ac4de22eb1840912383b...)
RECONCILE_EVIDENCE_LOCK.json + SP-MW-RECONCILE-001_BLOCKED.md preserved
```

## 6. Resume gate status

```text
SP-MW-RECONCILE-001 = RESUME_AUTHORIZED (no scope expansion occurred)
NEXT = fresh reconciliation worktree at f9c7faae, reapply frozen C1–C6 diff,
       compare vs pre-block lock, revalidate C1–C6, run full matrix
NOTE = test expectations must now reflect the C3 authority-wired gate
       (fake approvals in tests must be replaced with AuthorityApprovalService-
       issued bindings; the pre-fix tests trusted envelope.approval_state).
```

PUSH / PR / MERGE / DEPLOYMENT = NOT AUTHORIZED. Stopped after the local commit for the reconciliation resume.
