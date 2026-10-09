---
id: ARTIFACT-0-PROVENANCE-FREEZE
task_id: SP-SYSTEM-ONE-DECISION-FABRIC-001-R1-RECOVERY-GOVERNED
created_utc: "2026-10-09T00:00:00Z"
agent: "HERMES@admin (on-host recovery implementer, per 09-22 routing precedent)"
type: provenance-freeze
status: open
authority_delta: 0
---

# ARTIFACT 0 — Provenance Freeze (R1 governed recovery)

Per control-state addendum (agent-note-control-state-confirmed-directive-frozen-aead.md,
ARTIFACT 0 binding rule): recorded BEFORE any `decision/` is created. Implementation
begins only from this frozen provenance point.

## Chosen worktree (frozen provenance point)
- PATH: `C:/Users/howar/SintraPrime-Unified-r1-recovery-clean`
- BRANCH: `feat/sp-system-one-decision-fabric-001-r1-recovery-governed`
- STARTING_COMMIT: `be6f07cf6c6ed0f9e0596aac548d7d1e7f74ca3b`
  ("G0-R4.1: execution-safety unblocking (ER-001/002/003)")
- DIRTY_STATUS: CLEAN (`git status --porcelain` empty at creation)
- UPSTREAM: none (local branch, not yet pushed)
- BASELINE_VERIFIED: `git cat-file -t be6f07cf` == `commit` (present in shared SintraPrime-Unified object DB)

## Isolation rationale
This worktree is deliberately isolated from dirty / divergent lanes:
- `rc/g0r3-collection` (main worktree at `b0f1d271`) — excluded; unrelated in-flight work.
- `SintraPrime-EXEC001-*` worktrees — excluded; separate execution-cert effort at `be6f07cf`, different task scope.
- The 9 prior recovery worktrees under `SintraPrime-Unified-decision-fabric-r1-recovery/{worktree,worktree-*}`
  — EXCLUDED as a source: all 9 fail their own TRANSFER_MANIFEST 32/32 integrity
  (best = 30/32; `decision/tests/test_r1_conformance.py` + `decision/ledger/ledger.py` mutated post-freeze;
  no clean frozen copy exists anywhere locally — 20 R1-RECOVERY dirs scanned 2026-10-09).

## Controlling source artifacts (frozen — reconciled by hash = PASS)
Transferred by hash, NOT reconstructed. These are the authoritative R1 spec.
1. `R1-DIRECTIVE-FROZEN.md`  (copy of `fabric/agent-decision-sp-system-one-decision-fabric-001-r1-dir-aa82.md`)
   SHA-256: `12de45a93e0e9efe9fd65e584a8ada07947b6ca790394879a59e0d17e4b5e6bc`  size 3449 B
2. `R1-CONTROL-STATE-ADDENDUM-FROZEN.md` (copy of `fabric/agent-note-control-state-confirmed-directive-frozen-aead.md`)
   SHA-256: `5bac511f0d208536a35e53b01439a1105797df85253ac188c744dabdee46081f`  size 2056 B
   Both recomputed and MATCH on this host (reconciliation PASS, 2026-10-09).

## Prior state this recovery supersedes
- 09-22 NOT_PROVEN receipt: admin-lane implementation worktree (`C:/Users/admin/...`) does not exist on this host -> phantom lane.
- 09-26 CONFIRMED_PRESENT: recovery delivery located on this host, but TRANSFER_MANIFEST integrity FAILS
  (no 32/32 copy anywhere; 20 R1-RECOVERY dirs scanned 2026-10-09).
- Resolution: fresh R1 recovery on the real howar host from a clean governed worktree based on `be6f07cf`,
  per the 09-22 contingency. NO reconstruction from pasted text; build from the two frozen source artifacts above.

## Reality gate
R1 status: BLOCKED (provenance not yet reconciled to a clean frozen code delivery). This ARTIFACT 0 is the
authorized starting point. `decision/` implementation begins only after this freeze is accepted.

AUTHORITY_DELTA = 0 (governed setup; no claims of implementation completion).
