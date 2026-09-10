# W4-1 — SEQUENCING FINDING (recorded before execution continues)

**Date:** 2026-09-09 · **Status:** PAUSED AT FIRST CHECK — finding material to the lane definition

## Discovery

The W4-1 worktree was created correctly from main @ `32b5f4a9` (`feat/wave4-w1-registry-install`, branch pre-created by the timed-out first attempt and verified present in `git worktree list`).

The first validation step then found: **`agent_runtime/` does not exist on main @ `32b5f4a9`.**

## Why

The frozen sequencing held correctly: Wave-3 was **locally certified but never published** (its branch `feat/sp-converge-wave3-agent-runtime` is not even pushed to the remote). Main therefore contains the Wave-2 foundation (merged via PR #302) but NOT the Wave-3 agent runtime that:

- defines `KNOWN_CAPABILITIES` (the 33-ID manifest vocabulary, incl. the 10 `computer.browser.*` IDs added in ZD-001),
- contains `AgentManifest`/delegation/registry/certify — the components the capability registry is designed to interoperate with,
- is the declared dependency lineage for Wave-4 (certification lineage chain: Wave-3 → ZD-001 → ... → Wave-4).

## Implication for the frozen sequencing record

The W4-1 acceptance gate includes `WAVE3_MANIFEST_IDS_UNALIASED = []` — i.e. every production manifest ID must be covered by an alias. That check requires the production `agent_runtime/manifest.py` to exist in the lane's tree. On main @ `32b5f4a9` there is no manifest file at all, so W4-1 cannot be completed *on top of main* without either:

(a) publishing Wave-3 first (the lineage chain has always shown Wave-3 certificate → ... → Wave-4), or
(b) running W4-1 against the Wave-3 overlay (as all ZD lanes did) — which contradicts "branch/worktree from main @ 32b5f4a9".

The sealed sequencing record (`wave4_sequencing_and_invariants_record.md`) itself lists the lineage as Wave-3 certificate → ZD-001 → ZD-002 → ZD-003 → ZD-004 → Wave-4. That chain implies Wave-3 publication precedes Wave-4 implementation — a precondition the CI recovery + publication of Wave-2 did not satisfy for Wave-3.

## What remains valid in this lane (already executed)

- Worktree created at `32b5f4a9` ✓
- Governed path identified: `registry/capabilities/` (existing `registry/` domain structure; agents/ and cdr/ are siblings) ✓
- The three ZD-002 artifacts copied **byte-identical** (SHA-256 verified source == installed) ✓
- Registry artifact validation executed against the artifact set itself:
  `REGISTRY_SCHEMA_VALID = TRUE` · 42 canonical IDs · 23 aliases · 0 unknown · 0 ambiguous · 0 collisions · EC/IR⇒ALWAYS_REQUIRED invariant holds ✓

## Held for Principal decision

Option A: **Publish Wave-3 first** (branch exists locally, certified, never pushed) → then W4-1 on main.
Option B: **Re-scope W4-1 to install on the Wave-3 lineage** (worktree from Wave-3 branch + ZD-001 overlay, as in ZD lanes), with main-publication of Wave-3 deferred.
Option C: Proceed with artifact installation on main as-is (no agent_runtime present) — registry would be pure vocabulary/policy metadata with no manifest counterpart; the W4-1 gate's alias-completeness check would be recorded as N/A-not-pass.

No further W4-1 steps executed pending the choice. No production files touched. The installed artifacts sit uncommitted in the new worktree.


## RULING (2026-09-09): W4-1 = BLOCKED_BY_DEPENDENCY_PUBLICATION

```
W4-1 = BLOCKED_BY_DEPENDENCY_PUBLICATION
BLOCKER = WAVE3_NOT_PRESENT_ON_CURRENT_MAIN
ARTIFACT_VALIDATION = PASS (42 canonical / 23 aliases / 0 unknown / 0 ambiguous / byte-identical install)
RUNTIME_DEPENDENCY_VALIDATION = NOT_YET_APPLICABLE
INSTALLED ARTIFACTS = UNCOMMITTED / HOLD (registry/capabilities/ in this worktree)
RESOLUTION LANE = SP-W3-PUBLISH-001 (reconcile + recertify Wave 3 on main @ 32b5f4a9)
```

Option A selected: publish Wave-3 first. The alias-completeness gate is NOT marked N/A — it is
blocked pending dependency publication, preserving its full strength.
