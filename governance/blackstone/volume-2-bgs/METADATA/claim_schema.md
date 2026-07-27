# Metadata Schema — Claim

## Derived From

BGS 5, BKGC Article XV, Article XVI.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| cid | string | Unique claim identifier |
| version | string | Schema version |
| created_at | datetime | Creation timestamp |
| created_by | string | Agent or human identity |
| text | string | Claim statement |
| status | enum | From claim status taxonomy |
| confidence_score | enum | A–F |
| jurisdiction | string | Governing jurisdiction if any |
| evidence_ids | list | Supporting evidence EIDs |
| counter_evidence_ids | list | Challenging evidence EIDs |
| reasoning_chain_id | string | Reference to reasoning record |
| review_id | string | Latest review record |

## Optional Fields

- `superseded_by`
- `related_claims`
- `subject_area`
- `effective_date`
- `review_date`

## Validation Rules

- A claim MUST have at least one supporting evidence item OR be marked `unverified`.
- `counter_evidence_ids` MUST be populated when material counter-evidence exists.
- `review_id` MUST be populated before status becomes `operational`.
