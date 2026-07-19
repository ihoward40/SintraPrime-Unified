# Open PR Disposition Registry

Authoritative as of commit 10cad07f046b5675ed10a1fba1aa4a955636f739 (main). Dispositions use the governed vocabulary.
This registry does NOT change any PR state.

| # | Title | Base | Head | Age (created) | Mergeable | Files | Overlap w/ main | Risk | Recommendation | Dependency | Merge now? |
|---|-------|------|------|---------------|-----------|------|-----------------|------|----------------|------------|-----------|
| 206 | Observatory G4.7 centralized execution guard | main | feat/observatory-g4.7-execution-guard | 2026-07-16 | CONFLICTING | 72 / +46704 | High (predates merged Mission Control) | HIGH | HOLD FOR DEPENDENCY (rebase + reconcile) | Convergence authority protocol | NO |
| 205 | Observatory G4.6 run-scoped event chains | main | feat/observatory-g4.6 | 2026-07-16 | MERGEABLE | 31 / +35355 | Medium (event model) | MED | HOLD FOR DEPENDENCY | Mission Control event authority | NO |
| 204 | Freeze Gate 3 evidence | main | feat/observatory-phase1 | 2026-07-15 | MERGEABLE | 14 / +26902 | Low (docs) | LOW | REVIEW (governance) | None | REVIEW ONLY |
| 192 | Monetization security + evidence integrity | audit/ecc-mvp-and-pr0006-verification | fix/monetization-security-ledger-integrity | 2026-07-12 | MERGEABLE | 62 / +8232 | Med (visual checkpoint 0aaffdc on head) | MED | REBASE AND RE-REVIEW | Base must move to main (#134 chain) | NO |
| 189 | eslint no-explicit-any warn | main | chore/eslint-no-explicit-any | 2026-07-09 | MERGEABLE | 9 / +36 | None | LOW | MERGE CANDIDATE | None | YES (low risk) |
| 181 | bump pip 26.1.1->26.1.2 | main | dependabot/pip-26.1.2 | 2026-07-08 | MERGEABLE | 1 / +1 | None | LOW | MERGE CANDIDATE | None | YES (low risk) |
| 166 | align pytest testpaths / scheduler arming | main | fix/97-ci-test-scope-alignment | 2026-07-06 | CONFLICTING | 2 / +122 | Low | LOW | REBASE AND RE-REVIEW | None | NO (rebase first) |
| 142 | AIOS second-brain upgrade | main | feat/aios-second-brain-upgrade | 2026-06-19 | CONFLICTING | 229 / +26958 | High (history: DO NOT MERGE) | HIGH | SPLIT REQUIRED | Triage | NO |
| 134 | Durable Checkpointer Compat Fix | main | audit/ecc-mvp-and-pr0006-verification | 2026-06-15 | CONFLICTING | 170 / +26597 | High (base of #192) | MED | SUPERSEDED / NEEDS INVESTIGATION | Convergence | NO |
| 133 | ollama health/slack schema | main | copilot/hermes-development-plan | 2026-06-14 | CONFLICTING | 8 / +208 | Low | LOW | REBASE AND RE-REVIEW | None | NO (rebase first) |

## Summary
- MERGE CANDIDATE: #189, #181.
- REBASE AND RE-REVIEW: #166, #133.
- HOLD FOR DEPENDENCY: #206, #205.
- SPLIT REQUIRED: #142.
- SUPERSEDED / NEEDS INVESTIGATION: #134.
- REVIEW (governance): #204.
- REBASE AND RE-REVIEW (base wrong): #192.

