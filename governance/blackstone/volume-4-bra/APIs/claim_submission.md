# API Contract — Governed Claim Submission

## Derived From

BRA § 3, BKC `KNOWLEDGE_MODEL/claim.md`.

## Endpoint

`POST /v1/governance/claims`

## Request Body

```json
{
  "cid": "claim-unique-id",
  "text": "The statute of limitations for breach of contract in Delaware is three years.",
  "jurisdiction": "US-DE",
  "evidence_ids": ["evid-001"],
  "counter_evidence_ids": [],
  "reasoning_chain_id": "rcid-001",
  "lifecycle_stage": "OPERATIONAL",
  "metadata": {
    "subject_area": "contract_law",
    "effective_date": "2026-07-27",
    "review_date": "2027-07-27"
  }
}
```

## Response

```json
{
  "cid": "claim-unique-id",
  "status": "CONTROLLING",
  "confidence_score": "B",
  "review_id": "review-001",
  "uri": "/v1/governance/claims/claim-unique-id"
}
```

## Validation Rules

1. `cid` MUST be unique.
2. `text` MUST be non-empty.
3. At least one `evidence_ids` entry MUST resolve OR status MUST be `UNVERIFIED`.
4. `lifecycle_stage` MUST be a valid BKR lifecycle stage.
5. If `lifecycle_stage` is `OPERATIONAL` or higher, `review_id` MUST be populated.
