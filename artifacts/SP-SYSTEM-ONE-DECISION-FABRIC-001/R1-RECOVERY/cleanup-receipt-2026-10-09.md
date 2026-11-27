---
id: CLEANUP-RECEIPT-2026-10-09
task_id: SP-SYSTEM-ONE-DECISION-FABRIC-001-R1-RECOVERY-GOVERNED
created_utc: "2026-10-09T12:15:00Z"
agent: "HERMES@admin (on-host recovery implementer)"
type: cleanup-receipt
authority_delta: 0
---

# Cleanup Receipt — redundant R1 recovery worktree sprawl pruned

## What was removed (read-only-safe git worktree removal; branches/commits preserved in shared repo)
All 9 worktrees under `C:/Users/howar/SintraPrime-Unified-decision-fabric-r1-recovery/` were removed via
`git worktree remove --force` + `git worktree prune`. Their branches remain in the shared SintraPrime-Unified repo.

| Removed worktree | Branch (preserved) |
|---|---|
| worktree              | feat/sp-system-one-decision-fabric-001-r1-recovery |
| worktree-agent0       | fix/agent0-ci-baseline-recovery |
| worktree-god0         | feat/sp-god0-mission-control-001 |
| worktree-god1         | feat/sp-god1x-os-network-sandbox-001 |
| worktree-integration  | feat/sp-system-one-decision-fabric-001-integration |
| worktree-omnibrain    | feat/sp-omnibrain-governed-runtime-001 |
| worktree-r1x          | fix/sp-system-one-decision-fabric-001-r1-confidence |
| worktree-r2           | feat/sp-system-one-decision-fabric-001-r2-shadow |
| worktree-r2s          | feat/sp-system-one-decision-fabric-001-r2-superseding |

Also removed: `SintraPrime-Unified-decision-fabric-r1-recovery/.venv-r1` (recreatable virtualenv, tied to the abandoned recovery).

## Rationale
- Every one of the 9 worktrees FAILS its own TRANSFER_MANIFEST 32/32 integrity (best = 30/32; the conformance test
  `decision/tests/test_r1_conformance.py` is mutated in all 9; `ledger.py` mutated in the canonical one). No clean
  frozen copy exists anywhere locally (20 R1-RECOVERY dirs scanned).
- They are redundant duplicates of one abandoned recovery attempt, explicitly EXCLUDED as a source in ARTIFACT 0.
- Superseded by the single clean governed worktree `SintraPrime-Unified-r1-recovery-clean` (baseline `be6f07cf`).

## Verified after removal
- `git worktree list | grep r1-recovery` -> only `SintraPrime-Unified-r1-recovery-clean` remains.
- Clean worktree HEAD == be6f07cf; ARTIFACT 0 + 2 frozen source artifacts present.
- Registered worktree count: ~37 -> 28.

## Outstanding
- `SintraPrime-Unified-decision-fabric-r1-recovery/swarm-004-real-worktrees` remains; pending inspection to confirm
  it is orphaned swarm output (not a registered worktree of any live repo) before removal.

AUTHORITY_DELTA = 0 (cleanup/prune only; no implementation claimed).
