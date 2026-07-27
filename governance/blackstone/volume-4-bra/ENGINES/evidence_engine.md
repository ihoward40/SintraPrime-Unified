# Engine Specification — Evidence Engine

## Responsibility

Intake, validate, classify, store, and retrieve evidence.

## Derived From

BRA § 2.1, BGS 1, BKC § 4.

## Capabilities

1. Accept evidence via API, file upload, URL retrieval, or agent submission.
2. Validate metadata completeness against `BGS/METADATA/evidence_schema.md`.
3. Compute integrity hash for fixed-format evidence.
4. Assign evidence type and source category using BKR taxonomies.
5. Register provenance via the Provenance Engine.
6. Link evidence to claims.
7. Enforce AI-output classification and independent-verification requirement.

## API Surface

| Operation | Description |
|-----------|-------------|
| `intake` | Register new evidence |
| `validate` | Check schema and provenance completeness |
| `classify` | Assign type, category, jurisdiction |
| `retrieve` | Fetch evidence by EID |
| `link_claim` | Associate evidence with a claim |
| `quarantine` | Suspend evidence pending review |

## Failure Modes

- Missing provenance → quarantine
- Unidentifiable source → reject
- Duplicate EID → reject and alert
- AI output not flagged → reject
