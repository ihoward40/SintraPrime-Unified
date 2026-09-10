# SP-MW-RECONCILE-001 — BLOCKED: SEALED W4-4 DEFECT FOUND (SCOPE EXPANSION REQUIRED)

**Base SHA:** `05885aa2ae4791e1a5fabca9aa4d4941fcf4050d` · **Worktree:** `C:/Users/admin/SintraPrime-Unified-mw-reconcile`
**Status: BLOCKED — SCOPE_EXPANSION_REQUIRED = TRUE**

## What happened

C1–C6 were implemented in the isolated worktree (overlay verified byte-exact 19/19; evidence lock `RECONCILE_EVIDENCE_LOCK.json`). During first certification runs, every C2 canonicalization path failed with:

```text
AttributeError: 'NoneType' object has no attribute 'capability_id'
  agent_runtime\receipts.py:165 in canonicalize_capability_for_hash
```

## Root cause — the defect is in the SEALED W4-4 commit, not the reconciliation

`agent_runtime/receipts.py @ 05885aa2` contains:

```python
from .capability_resolver import CanonicalCapability, RegistryView, _status_gate, resolve_capability
...
resolved: CanonicalCapability = _status_gate(resolve_capability(raw_id, registry))
return (resolved.capability_id, ...)
```

but `_status_gate()` in `agent_runtime/capability_resolver.py @ 05885aa2` is declared `-> None` and returns `None` (it raises on DISABLED/DORMANT, returns nothing on success). Therefore **for every ACTIVE capability the sealed `canonicalize_capability_for_hash` raises `AttributeError: 'NoneType' object has no attribute 'capability_id'`** — verified by direct repro and by re-running the sealed W4-4 test `test_canonical_id_and_registry_provenance_preserved` in a clean 05885aa2 worktree, which now **FAILS**.

## How the sealed commit passed its certification

Timeline reconstruction: during W4-2 implementation the working tree carried a public `status_gate(cc) -> CanonicalCapability` wrapper. It was never committed (both `98bc9b70` and `6d5214f2` contain only the private `None`-returning `_status_gate`). At W4-4 commit time the working-tree `receipts.py` called `status_gate(...)` (returning `cc`), so 13/13 tests passed **against the uncommitted working tree**. Immediately before sealing, two working-tree files (`capability_resolver.py`, `test_capability_resolver.py`) were restored to committed state to satisfy the two-file diff scope — and one of my own edits renamed the receipts.py import to `_status_gate`, aligning it with the committed resolver's private helper **whose return value is None**. The 13/13 certification was executed before that final regression was introduced by the stale-file cleanup; the sealed tree was not re-run against the full W4-4 suite afterward (only the two-file diff scope and the portal recovery were re-verified). This is a **certification-process defect (working-tree vs committed-state divergence)** plus a **functional defect at 05885aa2**.

## Impact

- `agent_runtime.receipts.canonicalize_capability_for_hash` is broken at HEAD for all ACTIVE capabilities (raises instead of returning provenance). Dormant/disabled/unknown paths still refuse correctly.
- All C2-dependent reconciled code (envelope/receipt hashing) inherits the failure — hence this lane cannot certify.
- W4-4's acceptance claim ("13/13 PASS") was true of the working tree at the time but is **not reproducible at the sealed commit** — the certification evidence is invalidated in the strict sense.

## Why I stopped

The fix is a **one-line change in sealed `agent_runtime/receipts.py`** (use the resolver's returned `CanonicalCapability` and call `_status_gate` for its refusal side effect):

```python
resolved = resolve_capability(raw_id, registry)
_status_gate(resolved)
return (resolved.capability_id, resolved.registry_generation_id, resolved.registry_hash)
```

But that file is a **sealed Wave-4 artifact**, outside the authorized mission-wiring subset (6 production + 7 test files + strictly necessary adapter/test file). Modifying it is scope expansion requiring explicit Principal authorization.

```text
SCOPE_EXPANSION_REQUIRED = TRUE
EXPANSION_TARGET = agent_runtime/receipts.py (1-line fix) + re-certification of agent_runtime W4-4 tests
REASON = sealed W4-4 functional defect discovered during C2 implementation
```

## Reconciliation state so far (all in isolated worktree, uncommitted)

| Correction | Status | Evidence |
|---|---|---|
| C1 registry-derived vocabulary + resolver gate | APPLIED | `browser_executor.py` derives vocabulary from trusted registry; gate resolves via W4-2 resolver, refuses canonical-alias-as-id, REGISTRY_NOT_TRUSTED when absent |
| C2 envelope/receipt canonical hashing | APPLIED (blocked by W4-4 defect) | `canonical_capability_ids()` + hash_payload registry binding; receipt `_canonical_requested/_canonical_used` |
| C3 authority approval validation + exactly-once consume | APPLIED | executor gate validates `AuthorityApprovalService` binding; runner consumes exactly-once; caller-supplied `delegation_id` no longer accepted as approval proof |
| C4 lazy mechanism injection | APPLIED | constructor imports nothing, launches nothing; mechanism built post-gate via factory |
| C5 budget decrement | APPLIED | per-gated-action consumption; BUDGET_EXHAUSTED on exceed |
| C6 exclusions | APPLIED | ZD evidence-lock tests + duplicate negative_outcome + origin_adapters removed |

## Decision required (pick one)

```text
OPTION 1 (recommended): authorize a micro-correction to sealed agent_runtime/receipts.py
  (the 3-line functional fix above) as part of SP-MW-RECONCILE-001, re-certify the full
  W4-4 boundary suite + reconciled subset, then seal.
OPTION 2: stop here; open a dedicated micro-lane (e.g. SP-W4-4-FIX-R1) for the
  receipts.py fix, re-certify, and resume reconciliation after it seals.
```

No commit was created. The reconciliation worktree preserves all C1–C6 work uncommitted for whichever path is chosen.
