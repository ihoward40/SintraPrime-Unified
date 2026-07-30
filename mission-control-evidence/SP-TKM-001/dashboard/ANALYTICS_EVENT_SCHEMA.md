# Analytics Event Schema — SP-TKM-001

Mission: SP-TKM-001
Owner: Observatory
Status: Phase Two schema draft

## Principles

1. No event may capture full documents, Social Security numbers, account numbers, payment card numbers, or sensitive narrative details.
2. Events are tied to a session or anonymous visitor ID, not to a named individual unless the individual voluntarily provides an email through a form.
3. UTM parameters are captured from the query string and attached to lead events.
4. Event names use lowercase snake_case and are dashboard-ready.

## Dashboard-Ready Event Names

| Event Name | Trigger | Required Payload | Optional Payload |
|---|---|---|---|
| `tiktok_profile_visit` | Landing page loads from TikTok referrer or with `utm_source=tiktok` | `event_name`, `url`, `timestamp` | `referrer`, `utm_*` |
| `starter_sheet_view` | Starter Sheet section scrolled into view or landing page loads | `event_name`, `url`, `timestamp` | `utm_*` |
| `starter_sheet_download` | Starter Sheet PDF download initiated or download link clicked | `event_name`, `url`, `timestamp` | `utm_*` |
| `email_capture_start` | Email input field receives focus | `event_name`, `url`, `timestamp` | `utm_*` |
| `email_capture_complete` | Interest form submitted successfully | `event_name`, `email`, `url`, `timestamp` | `first_name`, `topic`, `utm_*` |
| `intake_pack_interest` | Intake Pack waitlist button clicked | `event_name`, `url`, `timestamp` | `utm_*` |
| `workshop_interest` | Workshop waitlist button clicked | `event_name`, `url`, `timestamp` | `utm_*` |
| `affiliate_click` | TikTok Shop affiliate link clicked | `event_name`, `url`, `timestamp`, `product_id` | `utm_content`, `affiliate_url` |
| `sponsor_inquiry` | Sponsor inquiry email link clicked | `event_name`, `url`, `timestamp` | `utm_*` |

## Common Payload Schema

```json
{
  "event_name": "email_capture_complete",
  "session_id": "anon_<uuid>",
  "url": "https://ops.ikesolutions.org/consumer-evidence?utm_source=tiktok&utm_medium=organic&utm_campaign=consumer_evidence&utm_content=UCC001",
  "referrer": "https://www.tiktok.com/",
  "timestamp": "2026-07-27T12:34:56Z",
  "utm_source": "tiktok",
  "utm_medium": "organic",
  "utm_campaign": "consumer_evidence",
  "utm_content": "UCC001"
}
```

## Lead-Capture Event Payload

```json
{
  "event_name": "email_capture_complete",
  "session_id": "anon_<uuid>",
  "email": "user@example.com",
  "first_name": "Jordan",
  "topic": "debt",
  "url": "https://ops.ikesolutions.org/consumer-evidence",
  "timestamp": "2026-07-27T12:34:56Z",
  "utm_source": "tiktok",
  "utm_medium": "organic",
  "utm_campaign": "consumer_evidence",
  "utm_content": "UCC001"
}
```

## Prohibited Fields

The following fields are never collected through these events:

- Full Social Security number
- Full account numbers
- Full payment card or bank numbers
- Unredacted documents or document contents
- Passwords or authentication tokens
- Home addresses
- Dates of birth
- Sensitive narrative details about a consumer's case

## Storage and Retention

- Events are stored in an analytics table or log sink.
- Lead records are linked to email capture events.
- UTM attribution is retained with the lead record.
- Raw IP addresses are not retained for analytics purposes unless required for fraud detection and with appropriate notice.

## Endpoint

```
POST /api/v1/consumer-evidence/event
```

Request body must conform to the AnalyticsEvent schema in `portal/routers/sp_tkm_001.py`.

## Next Steps

1. Create analytics table schema.
2. Wire endpoint to analytics store.
3. Build dashboard queries for each event.
4. Add bot filtering and basic rate limiting.
5. Verify no PII beyond email/first name/topic is captured.
