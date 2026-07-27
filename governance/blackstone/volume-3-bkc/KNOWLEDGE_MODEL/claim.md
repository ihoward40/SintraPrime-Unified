# Knowledge Model — Claim Object

## Derived From

BKC § 3, BGS `METADATA/claim_schema.md`.

## Model

```yaml
Claim:
  cid: string
  version: semantic_version
  created_at: datetime
  created_by: identity
  text: string
  status: claim_status
  confidence_score: confidence_score
  jurisdiction: optional jurisdiction
  evidence_ids: [eid]
  counter_evidence_ids: [eid]
  reasoning_chain_id: string
  review_history: [review_id]
  superseded_by: optional cid
  related_claims: [cid]
  depends_on: [cid]
  lifecycle_stage: lifecycle_stage
  metadata: ClaimMetadata

ClaimMetadata:
  subject_area: string
  effective_date: optional date
  review_date: optional date
  notes: string
```

## Invariants

1. A claim MUST have at least one supporting evidence item OR status `UNVERIFIED`.
2. If `status` is `OPERATIONAL` or higher, `review_id` MUST be populated.
3. If counter-evidence exists, `counter_evidence_ids` MUST be non-empty.
4. A superseded claim MUST reference its successor.
