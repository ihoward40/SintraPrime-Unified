# Post-Merge Governance Correction Record

## Correction ID
GW-215-001

## Discovery date
2026-07-20

## Affected merged PR
#215 — Certification increment: audit correlation and non-HTTP authorization

## Merge commit
a0d9900bc40e01941acfe1f49f6bacad7189aeb7

## Affected document
docs/certification/audit-correlation-non-http/increment-1/rollback.md

## Inaccurate claim
The PR #215 body stated that rollback.md documents "all 19 files to revert." This was inaccurate in two ways:
1. The actual changed-file count is 20, not 19.
2. The rollback.md grouped the 12-file evidence directory as a single line item, listing only 9 items total (8 implementation files + 1 evidence directory line), rather than explicitly enumerating all 20 files.

## Corrected claim
PR #215 changed exactly 20 files: 8 implementation/configuration files and 12 certification-evidence files. The corrected rollback.md explicitly enumerates all 20 file paths and states the total count.

## Functional impact
None. The rollback approach (reverting the commits) was always conceptually complete. However, the former rollback.md used placeholders (`<evidence-commit>`, `<implementation-commit>`) rather than concrete commit SHAs, making the commands non-actionable until filled in. The corrected version provides real SHAs and the `-m 1` flag for merge-commit reversion.

## Security impact
None. No security controls, authentication, authorization, tenant isolation, audit, or correlation behavior was affected.

## Rollback procedure impact
Corrected. The former rollback commands used placeholders and did not include the `-m 1` flag needed to revert a merge commit. The corrected rollback.md provides actionable commands with real commit SHAs and the correct merge-revert syntax.

## Evidence-record accuracy impact
Corrected. The rollback.md now explicitly lists all 20 files with their exact paths and categorization.

## Certification impact
None. The certification conclusion (CERTIFIED FOR THE RECORDED SCOPE) remains accurate. The correction is documentation-only.

## Correction method
A governance-wrap PR (docs/pr215-governance-wrap) updates rollback.md with the complete 20-file inventory and adds this correction record. No runtime code, tests, CI workflows, or evidence content (JSON) were modified.

## Validation performed
- Confirmed 20 changed files via git diff --name-only between baseline and merge commit.
- Confirmed 8 implementation files and 12 evidence files.
- Verified no stale "19 files" claims remain in the maintained evidence files.
- Verified rollback commands now reference real commits (a0d9900b with -m 1, cee14531, f4613e9e) with correct syntax.
- Former rollback.md used placeholders; corrected version provides actionable SHAs.
- Ran validate_repository_claims, ruff full, and git diff --check — all pass.
- No runtime files, test files, or CI workflow files changed.

## Approver/status
Pending review and merge of the governance-wrap PR.