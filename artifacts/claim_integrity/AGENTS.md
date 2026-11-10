# artifacts/claim_integrity — Claim-Integrity Evidence

## Purpose

Owns durable evidence and certification receipts for claim-integrity benchmark work.

## Ownership

- CI certification receipts tied to exact implementation SHAs and workflow run IDs.
- Authorization-boundary records distinguishing verification from merge, deployment, legal-rule admission, and consequential action authority.

## Local Contracts

- Every receipt must identify the exact certified implementation SHA.
- A receipt must distinguish the certified implementation SHA from the later commit that adds the receipt itself.
- CI verification must never be represented as merge authorization, deployment authorization, professional legal approval, or legal-rule production admission.
- Workflow and job outcomes must be recorded from observed GitHub Actions results; do not infer missing checks.
- Later merge or deployment decisions require separate receipts tied to the resulting commit or deployment artifact.

## Work Guidance

- Prefer immutable, project-specific receipt filenames.
- Record workflow run IDs, run numbers, job IDs when available, and explicit PASS/FAIL states.
- Preserve prior failure/correction traces when they materially explain the certification result.

## Verification

- Re-check the cited commit SHA against GitHub Actions before creating or updating a certification receipt.
- Confirm the PR merge/deployment state separately from CI results.

## Child DOX Index

*(None - leaf artifact boundary.)*
