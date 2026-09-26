# ARTIFACT 0 — RECOVERY PROVENANCE FREEZE

TASK_ID: SP-SYSTEM-ONE-DECISION-FABRIC-001-R1-RECOVERY
ARTIFACT: Recovery Artifact 0 (worktree/baseline provenance freeze)
CREATED_UTC: 2026-09-26T15:21:06Z (authoritative — measured at first hash)
AUTHOR: Hermes (GLM, Nous) executing on the real host — "admin lane" authority realized locally per Principal recovery directive
STATUS: BINDING — implementation begins only after this file is hashed

## SUPERSEDED PRIOR LANE (PHANTOM)

- PRIOR_LANE = SUPERSEDED / NOT_PROVEN
- Prior claimed worktree C:\Users\admin\SintraPrime-Unified-decision-fabric-r1-r2 = NOT FOUND (host does not exist)
- Prior claimed Artifact 0 hash 61fc40b5255a83f5dcfc6ba3dab078252a973f2c5eb33330f729efce0e513855 = NOT INHERITED; historical reference to an unproven claim ONLY
- Prior claimed test result 29/29 x 3 = NOT INHERITED
- Provenance reconciliation receipt: fabric agent-resolution-r1-provenance-reconciliation-implementat-f8fd (howar machine, C:\Users\howar\fabric\)
- No prior source code was reconstructed from chat. Recovery starts fresh.

## MEASURED ENVIRONMENT (live, this session)

- HOST: IKESOLUTIONS
- USER: howar
- OS: Windows 11, build 26200.9457 (10.0.26200.9457)
- Repository root (governing): C:\Users\howar\SintraPrime-Unified
- Governing repo state at recovery start: branch rc/g0r3-collection @ be6f07cf, dirty (4 modified files, unrelated to this lane — see ISOLATION)

## BASELINE VERIFICATION (directive section 5)

- be6f07cf exists locally: TRUE (git cat-file -t => commit)
- be6f07cf message: "G0-R4.1: execution-safety unblocking (ER-001/002/003)"
- Full SHA: be6f07cf6c6ed0f9e0596aac548d7d1e7f74ca3b
- Governed test infrastructure present at baseline:
  - conftest.py (root, Tier-1 lane collection, sys.path policy) — PRESENT
  - scripts/certify.py (deterministic certification runner, repo-owned temp policy) — PRESENT
  - SINTRAPRIME_TEST_LANES lane machinery — PRESENT at baseline
- Suitability: SUITABLE (clean commit, governed infra intact)

## RECOVERY WORKTREE (directive section 6)

- Absolute recovery worktree path: C:\Users\howar\SintraPrime-Unified-decision-fabric-r1-recovery\worktree
- Branch created for recovery: feat/sp-system-one-decision-fabric-001-r1-recovery
- Created from: be6f07cf (git worktree add -b ... be6f07cf)
- STARTING_COMMIT_SHA: be6f07cf6c6ed0f9e0596aac548d7d1e7f74ca3b
- MERGE_BASE_WITH_be6f07cf: be6f07cf6c6ed0f9e0596aac548d7d1e7f74ca3b (identical — worktree IS the baseline)
- BASELINE_IS_EXACT: TRUE (no substitution)
- git status --short at freeze: (empty — clean)
- git status --branch: On branch feat/sp-system-one-decision-fabric-001-r1-recovery; nothing to commit, working tree clean
- Staged state: EMPTY. Modified state: EMPTY. Untracked state: EMPTY (except files created under transfer-env/, see below)
- Upstream/tracking: NONE (local branch, no remote tracking — intentional; no push authorized)
- decision/ exists before implementation: FALSE (verified: ls decision => No such file)
- artifacts/SP-SYSTEM-ONE-DECISION-FABRIC-001/R1-RECOVERY exists before this artifact: FALSE

## ISOLATION RATIONALE (directive sections 4/6)

- Dirty rc/g0r3-collection work in C:\Users\howar\SintraPrime-Unified (agent_runtime/tests/test_capability_resolver.py, test_w43_consumer_migration.py, app_builder/app_builder.py, backend/stripe-payments/tests/test_stripe.py) is EXCLUDED — recovery does not touch that worktree.
- EXEC001 worktrees (SintraPrime-EXEC001-CERT-R2, -DIAG, -W1, -WAVE2-QUARANTINE, SintraPrime-Unified-sp-exec001-repair) are EXCLUDED — detached-HEAD forensic/quarantine lanes, not implementation surfaces.
- .codex worktrees and pr310-verify are unrelated and EXCLUDED.
- One-writer rule: this recovery lane is the ONLY writer to the recovery worktree.
- Python environment: dedicated venv .venv-r1 (Python 3.11.16, pytest 9.1.1, pyyaml 6.0.3), outside the repo tree. No global mutation.

## RUNTIME SAFETY DEFAULTS (frozen; re-asserted)

- SINTRAPRIME_DECISION_PROVIDER default = mock
- SINTRAPRIME_DECISION_SHADOW_ONLY default = 1
- No missing environment variable may enable live Jev routing.
- JEV_BASE_URL default = documented Vercel AI Gateway endpoint; any override is provenance-bearing.

## EVIDENCE DIRECTORIES

- RECOVERY_EVIDENCE_WORKING_DIR: artifacts/SP-SYSTEM-ONE-DECISION-FABRIC-001/R1-RECOVERY/ (this file's directory)
- FINAL_R1_EVIDENCE_DIR: artifacts/SP-SYSTEM-ONE-DECISION-FABRIC-001/R1/ — NOT created in R1-RECOVERY; promotion (copy/freeze) is a separate later step requiring its own verification. No aliasing, no silent overwrite.
