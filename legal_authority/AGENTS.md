# legal_authority - Legal Authority and Jurisdiction Rules

## Purpose

Owns the data-backed legal authority, jurisdiction rule, conflict, professional-review, challenge, stale-source, effective-date evaluation, cross-jurisdiction comparison, UCC filing-assessment, and claim-integrity benchmark framework for fifty-state trust intelligence.

## Ownership

- Pydantic schemas for legal authorities, jurisdiction rules, professional review records, legal challenges, audit events, source refresh results, conflict records, and claim-integrity decisions.
- JSON-backed repository loading and governed appends from `data/jurisdictions/`.
- Federal overlay authority package at `data/federal/`, including source limitations and review-gated issue-spotting rules.
- Claim-integrity benchmark data at `data/benchmarks/` for adversarial source/entailment/scope/remedy/harm testing.
- Rule evaluation, supersession, conflict detection, cross-jurisdiction comparison, UCC filing assessment, provenance response shaping, production gate checks, challenge preservation, manual stale-source metadata comparison, and claim-integrity evaluation.

## Local Contracts

- Legal conclusions must include authority IDs, verification state, human-review state, effective dates, and limitations.
- Unsupported private-law claims may be recorded only as quarantined source material and must not become active or approved rules without source reclassification.
- `PRIMARY_SOURCE_VERIFIED` means source verification only; it is not professional legal approval.
- Claim-integrity evaluation must distinguish source existence from claim entailment, source scope, current-jurisdiction applicability, remedy authority, and real-world harm.
- Never infer a universal legal status from a definition, maxim, historical usage, or statutory term until source scope and applicability to the current jurisdiction and facts are verified.
- Missing effective dates, unresolved conflicts, stale-source invalidation, official-code limitations, unsupported authority chains, unresolved entailment, or unverified remedy chains must require human review or remain research-only.
- Claim-integrity evaluation must fail closed for critical operational risk and must never self-approve an actionable legal claim.
- Only `LICENSED_ATTORNEY` review records may approve legal rules for production eligibility; `CPA` approval is limited to accounting rules.
- Production eligibility must remain blocked unless primary authority, date, conflict, stale-source, challenge, test, and review gates all pass.
- Source monitoring is manual and non-crawling; external content must be supplied to the service.
- UCC filing assessments are evidence-review workflows; filing-office acceptance must not be represented as proof of attachment, enforceability, ownership, perfection, priority, or collateral validity.

## Work Guidance

- Prefer extending the JSON-backed models instead of adding ad hoc legal assertions to prototype trust modules.
- Keep source classification, authority type, reviewer role, review status, challenge state, rule category, entailment state, failure mode, deployment status, and risk category as explicit validated values.
- Preserve historical rules and challenged snapshots when superseded or corrected; do not delete old reasoning to express a change in law.
- Comparison output must show missing data, review state, limitations, and conflict-of-laws warnings instead of ranking jurisdictions as categorically better.
- Claim-integrity benchmark cases should preserve the original failure pattern without treating benchmark text as verified law.
- Do not represent credential verification as automatic unless a real credential verification integration exists.

## Verification

- Run focused `legal_authority` and portal API tests for schema validation, rule selection, conflict handling, provenance, review workflow, challenge workflow, stale-source behavior, containment, and claim-integrity gating.
- Validate jurisdiction and benchmark JSON files with `python -m json.tool`.
- Run MyPy with the repository-safe Phase 2A command documented in `artifacts/fifty_state_expansion/MYPY_GATE_ANALYSIS.md`.

## Child DOX Index

*(None - leaf package.)*
