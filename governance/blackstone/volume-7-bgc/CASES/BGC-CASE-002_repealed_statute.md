# Case — Repealed Statute

## Case ID

CASE-002

## Title

Repealed Statute

## Scenario

An educational article from 2018 cites a statute that was repealed and replaced by a new statute in 2024. A user asks what the current rule is.

## Inputs

- 2018 educational article.
- Repealed statute (pre-2024).
- Current statute (post-2024).

## Governing Principles and Articles

- BKGC Article XI — Temporal Governance
- BKGC Article VIII — Authority Governance
- BGS 5.2 — Status Downgrade
- BKC § 5.2 — Authority Types

## Evidence Evaluation

| Evidence | Source Category | Weight | Temporal Status |
|----------|-----------------|--------|-----------------|
| 2018 educational article | Educational | Educational | Stale |
| Pre-2024 statute | Government Publication | Was controlling | Repealed |
| Post-2024 statute | Government Publication | Controlling | Current |

## Reasoning

1. The 2018 article accurately described the law when published.
2. The old statute is no longer controlling because it was repealed.
3. The current statute governs.
4. The 2018 article should be cited only as historical context, not as current authority.

## Outcome

- Provide the current statute as the controlling authority.
- Explain that the 2018 article reflects the pre-repeal rule.
- Flag the old statute as stale.
- Preserve the historical article with a temporal note.

## Audit Trail

- Evidence IDs: EID-CASE002-001, EID-CASE002-002, EID-CASE002-003
- Reasoning chain ID: RC-CASE002
- Reviewer: Governance Casebook v1.0.0
- Outcome status: CONTROLLING (for current statute), HISTORICAL (for old statute)

## Lessons Learned

- Educational articles are valuable but must be checked for temporal validity.
- The ecosystem must flag stale authority rather than silently relying on it.
