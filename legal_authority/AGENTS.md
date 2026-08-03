# legal_authority - Legal Authority and Jurisdiction Rules

## Purpose

Owns the data-backed legal authority, jurisdiction rule, conflict, professional-review, challenge, stale-source, effective-date evaluation, cross-jurisdiction comparison, and UCC filing-assessment framework for fifty-state trust intelligence.

## Ownership

- Pydantic schemas for legal authorities, jurisdiction rules, professional review records, legal challenges, audit events, source refresh results, and conflict records.
- JSON-backed repository loading and governed appends from `data/jurisdictions/`.
- Federal overlay authority package at `data/federal/`, including source limitations and review-gated issue-spotting rules.
- Rule evaluation, supersession, conflict detection, cross-jurisdiction comparison, UCC filing assessment, provenance response shaping, production gate checks, challenge preservation, and manual stale-source metadata comparison.

## Local Contracts

- Legal conclusions must include authority IDs, verification state, human-review state, effective dates, and limitations.
- Unsupported private-law claims may be recorded only as quarantined source material and must not become active or approved rules without source reclassification.
- `PRIMARY_SOURCE_VERIFIED` means source verification only; it is not professional legal approval.
- Missing effective dates, unresolved conflicts, stale-source invalidation, official-code limitations, or unsupported authority chains must require human review.
- Only `LICENSED_ATTORNEY` review records may approve legal rules for production eligibility; `CPA` approval is limited to accounting rules.
- Production eligibility must remain blocked unless primary authority, date, conflict, stale-source, challenge, test, and review gates all pass.
- Source monitoring is manual and non-crawling; external content must be supplied to the service.
- UCC filing assessments are evidence-review workflows; filing-office acceptance must not be represented as proof of attachment, enforceability, ownership, perfection, priority, or collateral validity.

## Work Guidance

- Prefer extending the JSON-backed models instead of adding ad hoc legal assertions to prototype trust modules.
- Keep source classification, authority type, reviewer role, review status, challenge state, and rule category as explicit strings validated against constants.
- Preserve historical rules and challenged snapshots when superseded or corrected; do not delete old reasoning to express a change in law.
- Comparison output must show missing data, review state, limitations, and conflict-of-laws warnings instead of ranking jurisdictions as categorically better.
- Do not represent credential verification as automatic unless a real credential verification integration exists.

## Verification

- Run focused `legal_authority` and portal API tests for schema validation, rule selection, conflict handling, provenance, review workflow, challenge workflow, stale-source behavior, and containment.
- Validate jurisdiction JSON files with `python -m json.tool`.
- Run MyPy with the repository-safe Phase 2A command documented in `artifacts/fifty_state_expansion/MYPY_GATE_ANALYSIS.md`.

## Child DOX Index

*(None - leaf package.)*
