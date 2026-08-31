# Statutory Drift and Stale Source Monitoring

Phase 2A adds a non-destructive source-monitoring foundation. It does not implement an uncontrolled web crawler.

## Authority Metadata

Authority records support:

- `last_checked_at`
- `next_review_at`
- `expected_review_frequency_days`
- `source_availability_status`
- `content_hash`
- `current_hash`
- `change_detected`
- `manual_review_status`
- `supersession_candidate`
- `broken_link_status`

## Manual Refresh

`SourceMonitor.refresh_authority_metadata()` accepts supplied content or a supplied hash and records whether the hash changed, whether the source was available, and whether review is required. If a content hash changes, the authority is marked `HUMAN_REVIEW_REQUIRED` and `INVALIDATED_PENDING_REVIEW` until reviewed.

## API

```text
POST /legal-authorities/{authority_id}/refresh-metadata
```

The endpoint requires reviewer role and identity headers. It creates an immutable audit event and does not fetch external content itself.

## Queue Behavior

Authorities enter stale/review queues when a source is locator-only, unavailable, broken, changed, queued for manual review, or invalidated pending review.
