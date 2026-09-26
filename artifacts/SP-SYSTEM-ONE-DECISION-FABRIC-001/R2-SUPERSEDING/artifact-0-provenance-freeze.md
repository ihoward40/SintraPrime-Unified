# ARTIFACT 0 — R2-SUPERSEDING CALIBRATION PROVENANCE FREEZE

TASK_ID: SP-SYSTEM-ONE-DECISION-FABRIC-001-R2S
ARTIFACT: R2S Artifact 0 (superseding calibration provenance freeze)
CREATED_UTC: 2026-09-26 (authoritative mtime)
STATUS: BINDING — calibration mutations begin only after this file is hashed

## LINEAGE

- BASE_COMMIT: fcf2be19ce3a3742184921f895ace3f797510bb7 (R1.1 remediation commit, remote-frozen)
- BASE_TREE: 4e04a0da817aeb12836d38f8630c14d537e41d8f
- R1_PROVENANCE_ROOT: 002273bf2c9843ec62a0367a909641ee0b6a8d88 (R1, remote-frozen)
- PREDECESSOR_R2_RECORD: original R2 calibration 35/36 (CALIBRATION_COMPLETE_WITH_FINDINGS) — IMMUTABLE historical discovery evidence; discovered R1-DEFECT-001
- DISCOVERED_DEFECT: R1-DEFECT-001 (malformed confidence ValueError escape)
- REMEDIATION_COMMIT: fcf2be19ce3a3742184921f895ace3f797510bb7 (R1.1)
- CHAIN: be6f07cf -> 002273bf (R1) -> fcf2be19 (R1.1) -> this calibration

## WORKTREE / BRANCH

- WORKTREE: C:\Users\howar\SintraPrime-Unified-decision-fabric-r1-recovery\worktree-r2s
- BRANCH: feat/sp-system-one-decision-fabric-001-r2-superseding (local only; push NOT authorized)
- HEAD at freeze: fcf2be19ce3a3742184921f895ace3f797510bb7 (EXACT — verified)
- TREE at freeze: 4e04a0da817aeb12836d38f8630c14d537e41d8f (EXACT)
- WORKTREE STATE: clean at creation (0 entries)
- HOST/USER: IKESOLUTIONS / howar
- PYTHON: 3.11.16 via shared .venv-r1 (pytest 9.1.1, pyyaml 6.0.3)

## RUNTIME SAFETY STATE (verified)

- SHADOW_ONLY = 1 (compiled-in default; no override present)
- DEFAULT_PROVIDER = mock (unknown values coerce to mock)
- PRODUCTION_ROUTING = DISABLED
- EXTERNAL_EFFECT_AUTHORITY = NONE
- LIVE_SIDE_EFFECTS = PROHIBITED

## DATASET / GROUND TRUTH

- Same 36-case semantic calibration universe as the original R2 (categories A–P), reused WITHOUT modification of expectations
- Ground truth source: R1-FROZEN-CONTRACT (verified conformance semantics), registry version R2-REGISTRY-1 carried forward
- GROUND_TRUTH_DRIFT check: the R2S test run asserts the same expected classes as the original registry; any drift is a STOP condition

## IMMUTABILITY

- ORIGINAL R2 EVIDENCE (worktree-r2 artifacts/…/R2/): UNTOUCHED — read-only source for the harness code only
- R1.1 SOURCE FILES: must remain unmodified by calibration (frozen bytes under test)
- R1 evidence (worktree artifacts/…/R1-RECOVERY/): untouched

## EVIDENCE DIRECTORY

- artifacts/SP-SYSTEM-ONE-DECISION-FABRIC-001/R2-SUPERSEDING/ (this file's directory)
