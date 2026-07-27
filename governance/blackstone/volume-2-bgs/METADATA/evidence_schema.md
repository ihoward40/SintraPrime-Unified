# Metadata Schema — Evidence

## Derived From

BGS 1.1, BKGC Article IX, Appendix D.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| eid | string | Unique evidence identifier |
| sid | string | Source identifier |
| version | string | Schema version |
| collected_at | datetime | Collection timestamp |
| collector | string | Identity of collector |
| evidence_type | enum | primary, derivative, ai_output, historical, etc. |
| source_category | enum | From BKR source taxonomy |
| jurisdiction | string | Relevant jurisdiction if any |
| provenance_id | string | Reference to provenance record |
| integrity_hash | string | Hash when applicable |
| confidence_score | enum | A–F |
| status | enum | active, superseded, quarantined, archived |
| related_claims | list | Claim IDs using this evidence |

## Optional Fields

- `retrieved_url`
- `retrieved_date`
- `page_numbers`
- `archive_location`
- `custody_chain_id`

## Validation Rules

- `eid` MUST be globally unique.
- `sid` MUST resolve to a registered source.
- `evidence_type` MUST match BKR taxonomy.
- `confidence_score` MUST be assigned before operational use.
