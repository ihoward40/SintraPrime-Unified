# ARTIFACT 0 — R1.1 REMEDIATION PROVENANCE FREEZE

TASK_ID: SP-SYSTEM-ONE-DECISION-FABRIC-001-R1.1 (R1-DEFECT-001 remediation)
ARTIFACT: R1.1 Artifact 0 — remediation provenance freeze
CREATED_UTC: 2026-09-26 (authoritative mtime)
STATUS: BINDING — source mutation begins only after this file is hashed

## DEFECT

- DEFECT_ID: R1-DEFECT-001
- CLASS: PROVIDER CONTRACT VIOLATION / CRASH SURFACE (no routing bypass observed)
- BEHAVIOR: malformed non-numeric confidence (e.g. "abc", "high", {}, []) raises
  unhandled ValueError from BOTH MockDecisionProvider and JevDecisionProvider
  instead of returning a first-class ERROR result — violates the R1 provider
  contract "never raise for provider-side failure"
- DISCOVERED_BY: SP-SYSTEM-ONE-DECISION-FABRIC-001-R2 (36 cases / 35 matched / 1 defect — case H01-confidence-malformed)
- SAFETY_CHARACTERIZATION: CRASH SURFACE only; no unsafe decision possible

## LINEAGE

- PARENT_R1: 002273bf2c9843ec62a0367a909641ee0b6a8d88 (verified R1 provenance root)
- R1_TREE: dfcd8ec794416421d997702c119dae45c605afd5
- SOURCE_BRANCH: fix/sp-system-one-decision-fabric-001-r1-confidence (local only)
- DERIVATION: git worktree add from exactly 002273bf; HEAD verified == parent at creation
- WORKTREE: C:\Users\howar\SintraPrime-Unified-decision-fabric-r1-recovery\worktree-r1x
- HOST/USER: IKESOLUTIONS / howar
- Frozen R1 branch (feat/…-r1-recovery) and its remote ref: UNTOUCHED
- R2 worktree (worktree-r2) and R2 evidence: UNTOUCHED

## RUNTIME SAFETY STATE

- SHADOW_ONLY = 1 (default, verified)
- DEFAULT PROVIDER = mock (verified)
- PRODUCTION ROUTING = DISABLED
- No dependencies updated; no Dependabot work in this lane

## REMEDIATION CONTRACT (per directive)

- Malformed/non-coercible confidence → first-class ERROR result (no raise)
- None-confidence behavior: UNCHANGED per provider (mock rejects→ERROR; jev records null→policy threshold-failure) — no cross-provider normalization
- Narrow exception handling only (convert expected conversion failures; no broad except-Exception swallowing of programmer defects)
- Both providers covered; shared semantics preferred
- Policy must consume the ERROR fail-closed (existing behavior)
- Ledger/canonicalization/semantic-hash/Noul/defaults: UNTOUCHED
- No commit/push/PR/merge; R2 recalibration (full 36-case rerun) follows after targeted re-verification, per Principal sequencing
