# Open PR Disposition Registry

Authoritative as of commit `48e2caa759661cc75617cc752bcc26eaad666647` (main, tree `9ee6d193dd7f607cd59487df9ef26d46b9593803`).
Dispositions use the governed vocabulary. This registry does NOT change any PR state.

## Disposition vocabulary
`REVIEW` — examine and decide merge or close.
`REASSESS` — evaluate against current main; may need clean successor.
`MERGE CANDIDATE` — low risk, current or near-current, may merge after verification.
`CLOSE AS SUPERSEDED` — scope absorbed or obsoleted by merged work; preserve context.
`REPLACE WITH CLEAN SUCCESSOR` — do not rebase; rebuild against current main.
`SPLIT REQUIRED` — scope too broad; recreate as smaller PRs.
`HOLD FOR ARCHITECTURAL RECONCILIATION` — blocked on shared execution protocol.

## Open PR inventory

| # | Title | Base | Head | Head SHA | Behind | Ahead | Mergeable | Merge state | Files | Scope overlap w/ main | Architectural conflict | Recommendation | Rationale |
|---|-------|------|------|----------|--------|-------|-----------|-------------|-------|----------------------|----------------------|----------------|-----------|
| 206 | Observatory G4.7: centralized execution guard | main | feat/observatory-g4.7-execution-guard | `ed0ca7a` | 39 | 6 | CONFLICTING | DIRTY | 72 | High — predates merged Mission Control, auth, audit, correlation certifications | YES — introduces third execution-control surface alongside Mission Control and `secure_execution/` | CLOSE AS SUPERSEDED | 39 commits behind; +46,704 lines; predates PR #213–217 security certifications; would create competing execution authority; extract useful concepts into shared execution protocol instead |
| 205 | Observatory G4.6: harden run-scoped event chains | main | feat/observatory-g4.6 | `bcf008b` | 39 | 2 | MERGEABLE | UNSTABLE | 31 | Medium — event model predates audit correlation certification | Potential — event model may conflict with `portal/auth/audit_envelope.py` | REPLACE WITH CLEAN SUCCESSOR | 39 commits behind; +35,355 lines; predates PR #215 audit correlation; provenance complications; rebuild against current main rather than rebasing |
| 204 | docs(observatory): freeze Gate 3 evidence with amendment controls | main | feat/observatory-phase1 | `1c4fdb6` | 39 | 1 | MERGEABLE | UNSTABLE | 14 | Low — docs only | None | REVIEW | 39 commits behind; governance docs only; low runtime risk; merge as historical governance or close as superseded; compare freeze semantics against newer certification conventions |
| 192 | Security hardening for monetization case start and evidence integrity | audit/ecc-mvp-and-pr0006-verification | fix/monetization-security-ledger-integrity | `24fbb86` | 132 | 38 | MERGEABLE | UNSTABLE | 62 | Medium — payment event validation, case state, ledger, schema, UI | None direct; scope too broad for single PR | SPLIT REQUIRED | Base is PR #134 head (not main); 132 commits behind; scope spans payment, case state machine, ledger, schema, route, UI; recreate as 4 smaller PRs: (1) payment-event/replay-security, (2) case-generation state machine, (3) evidence-ledger integrity, (4) UI integration |
| 189 | chore(web): enable @typescript-eslint/no-explicit-any as warn and fix all 9 occurrences | main | chore/eslint-no-explicit-any | `dc2f7e6` | 43 | 1 | MERGEABLE | CLEAN | 9 | Low — frontend lint rule | None | REASSESS | 43 commits behind; low risk but built before recent UI and Mission Control merges; run current lint, count explicit any occurrences, enable rule in a new small increment; do not merge stale branch |
| 181 | build(deps): bump pip from 26.1.1 to 26.1.2 | main | dependabot/pip/pip-26.1.2 | `30e0e46` | 47 | 1 | MERGEABLE | CLEAN | 1 | None | None | REASSESS | 47 commits behind; dependabot bump; assess whether bump is still needed or superseded by newer pip releases |
| 166 | chore: align pytest testpaths and mark scheduler arming tests as experimental | main | fix/97-ci-test-scope-alignment | `67a845b` | 66 | 1 | CONFLICTING | DIRTY | 2 | Low — CI test scope | None | CLOSE AS SUPERSEDED | 66 commits behind; conflicting; scope likely absorbed by CI changes in PR #213–217 |
| 142 | feat: AIOS second-brain upgrade and persistent portal messaging | main | feat/aios-second-brain-upgrade | `0428674` | 111 | 8 | CONFLICTING | DIRTY | 229 | High — 229 files, history contamination risk | None direct | CLOSE AS SUPERSEDED | 111 commits behind; 229 files; too stale to rebase; extract useful concepts if any |
| 134 | PR-0006B: Durable Checkpointer Compatibility Fix and Verification Evidence | main | audit/ecc-mvp-and-pr0006-verification | `27fbafa` | 132 | 36 | CONFLICTING | DIRTY | 170 | High — base of #192 chain | None direct | CLOSE AS SUPERSEDED | 132 commits behind; 170 files; base of PR #192 chain; too stale; scope likely absorbed or superseded |
| 133 | fix: ollama health/slack schema/listener/web_tui/workflow router | main | copilot/hermes-development-plan | `753d2f8` | 111 | 2 | CONFLICTING | DIRTY | 8 | Low — 8 files | None | CLOSE AS SUPERSEDED | 111 commits behind; conflicting; rebase not worthwhile; recreate if any fix is still needed |

## Summary
- CLOSE AS SUPERSEDED: #206, #166, #142, #134, #133.
- REPLACE WITH CLEAN SUCCESSOR: #205.
- SPLIT REQUIRED: #192.
- REVIEW: #204.
- REASSESS: #189, #181.
- No PR is recommended for direct merge.
- No MERGE CANDIDATE or HOLD FOR ARCHITECTURAL RECONCILIATION in current inventory.

> No PR state changes are authorized by this registry. Recommendations are
> governance proposals only. Mergeability from GitHub does NOT imply merge
> readiness — behind count, architectural conflict, and scope must all be
> evaluated.