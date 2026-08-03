# legal_authority - Legal Authority and Jurisdiction Rules

## Purpose

Owns the data-backed legal authority, jurisdiction rule, conflict, and effective-date evaluation framework for fifty-state trust intelligence.

## Ownership

- Pydantic schemas for legal authorities, jurisdiction rules, review records, and conflict records.
- JSON-backed repository loading from `data/jurisdictions/`.
- Read-only rule evaluation, supersession, conflict detection, and provenance response shaping.

## Local Contracts

- Legal conclusions must include authority IDs, verification state, human-review state, effective dates, and limitations.
- Unsupported private-law claims may be recorded only as quarantined source material and must not become active rules.
- `PRIMARY_SOURCE_VERIFIED` means source verification only; it is not professional legal approval.
- Missing effective dates, unresolved conflicts, or unsupported authority chains must require human review.

## Work Guidance

- Prefer extending the JSON-backed Phase 1 models instead of adding ad hoc legal assertions to prototype trust modules.
- Keep source classification and authority type as explicit strings validated against constants.
- Preserve historical rules when superseded; do not delete old rules to express a change in law.

## Verification

- Run focused `legal_authority` and portal API tests for schema validation, rule selection, conflict handling, and provenance.
- Validate jurisdiction JSON files with `python -m json.tool`.

## Child DOX Index

*(None - leaf package.)*
