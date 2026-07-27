# Registry — Lifecycle Stages

## Authority

This registry is authoritative for knowledge object lifecycle stage codes.

## Derived From

BKGC Article VI; BKC § 2; BKC `TAXONOMIES/lifecycle_stages.md`.

## Stages

| Code | Stage | Description |
|------|-------|-------------|
| IDEA | Idea | Initial thought or observation |
| HYPOTHESIS | Hypothesis | Testable proposition |
| RESEARCH | Research | Evidence collection in progress |
| CORROBORATED | Corroborated | Multiple sources align |
| VERIFIED | Verified | Independent verification completed |
| OPERATIONAL | Operational | Approved for operational use |
| LITIGATION_READY | Litigation Ready | Audit trail and custody complete |
| ARCHIVE | Historical Archive | Preserved for reference |

## Allowed Transitions

```text
IDEA → HYPOTHESIS → RESEARCH → CORROBORATED → VERIFIED → OPERATIONAL → LITIGATION_READY → ARCHIVE
```

Backward transitions are permitted only as corrections or reversions, recorded as revisions.

## Change Control

Stage additions or transition changes require a CDR and upstream update.
