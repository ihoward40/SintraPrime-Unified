# Knowledge Model — Evidence Object

## Derived From

BKC § 4, BGS `METADATA/evidence_schema.md`.

## Model

```yaml
Evidence:
  eid: string
  version: semantic_version
  collected_at: datetime
  collector: identity
  source_id: sid
  content: ContentReference
  provenance_id: string
  integrity_hash: optional string
  confidence_score: confidence_score
  evidence_type: evidence_type
  source_category: source_category
  jurisdiction: optional jurisdiction
  status: evidence_status
  derived_from: optional eid
  corroborates: [eid]
  contradicts: [eid]
  related_claims: [cid]
  lifecycle_stage: lifecycle_stage

ContentReference:
  type: text | file | url | ai_output
  value: string
  retrieval_date: optional datetime
```

## Invariants

1. `source_id` MUST resolve to a registered source.
2. `provenance_id` MUST be populated.
3. AI-generated evidence MUST be classified as `ai_output` and require independent verification.
4. `integrity_hash` is REQUIRED when the evidence is fixed-format (file, document).
