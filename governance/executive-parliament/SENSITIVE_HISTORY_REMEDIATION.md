# Sensitive Git History Remediation Runbook

Status: REQUIRED / DESTRUCTIVE STEPS NOT AUTOMATICALLY AUTHORIZED

## Verified exposure
A non-main branch, `feat/aios-second-brain-upgrade`, currently exposes case/tax and credit-report artifacts through the public repository. Examples verified by repository inspection include IRS-case evidence paths, three Experian credit-report PDFs, and trust directories.

## Immediate containment
1. Treat exposed personal documents as compromised copies.
2. Do not merge the affected branch.
3. Do not copy those artifacts into any new branch or PR.
4. Keep future confidential material outside this public repository.
5. If any exposed file contains credentials, tokens, account access data or reusable secrets, rotate/revoke them immediately; history removal alone is not sufficient.

## Remediation plan
History rewriting is destructive and can disrupt clones, branches and open PRs. It therefore requires a separate Principal authorization and a verified private backup before execution.

After approval:
1. Inventory every sensitive path across all refs, not only the current branch.
2. Create an offline/private backup and record pre-rewrite commit IDs.
3. Use a history-rewrite tool such as `git filter-repo` to remove exact sensitive paths/blobs.
4. Verify sensitive blobs are absent from all rewritten refs.
5. Force-push only the explicitly approved rewritten refs.
6. Invalidate stale clones/caches and require fresh clones.
7. Re-run repository searches and GitHub secret scanning.
8. Preserve a remediation receipt containing hashes and path names only—never the removed contents.

## Non-goals
This runbook does not itself delete branches, rewrite history, force-push, rotate credentials, or claim GitHub caches have been purged.
