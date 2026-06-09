# intake_templates — Evidence Intake Template Library

## Purpose

Owns the evidence intake template library for the Howard recovery system. These JSON templates define structured evidence forms that the Howard Intake Watch Agent fills and processes. Each template maps a specific creditor, agency, or evidence scenario to a field structure.

## Ownership

- All `.json` template files
- `README_HOW_TO_USE_TEMPLATES.txt`

## Local Contracts

- Every template must contain at minimum: `case_name` (or `case_id`), `evidence_type`, `title`, `source`
- Field names must never be changed — the Howard intake agent reads them by name
- Templates are input-only artifacts: they do not send, file, email, or contact any external system
- Completed templates move to `intake/`; processed ones to `processed/`; failures to `errors/`

## Work Guidance

*(No project-specific standards yet — fill when engineering conventions emerge.)*

## Verification

*(No verification framework documented yet — fill when test/coverage thresholds exist.)*

## Child DOX Index

*(None — all template files are leaf data files.)*
