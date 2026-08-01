# Consumer Evidence Landing Page — Internal Implementation

Mission: SP-TKM-001
Owner: Revenue Architect
Status: Internal preview only — not deployed to production

## Files

- `index.html` — responsive static landing-page preview
- `sp_tkm_001.py` — FastAPI router stub under `portal/routers/`
- `README.md` — this file

## Public Route

Preferred public slug: `/consumer-evidence`
Preferred public URL: `https://ops.ikesolutions.org/consumer-evidence`

## Internal Route

If the SintraPrime application architecture requires a different internal path, preserve the public-facing slug `consumer-evidence` and document the internal implementation path here.

## Current Implementation

The router stub registers:

- `GET /consumer-evidence` — serves the static HTML preview
- `POST /api/v1/consumer-evidence/interest` — placeholder lead-capture endpoint
- `POST /api/v1/consumer-evidence/event` — placeholder analytics-event endpoint

## Phase Two Constraints

- No active checkout
- No payment processor
- No subscription or recurring billing
- No public deployment
- No production domain required
- No full SSN, account numbers, payment card numbers, or document uploads accepted

## UTM Capture

The landing page reads `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` from the query string and stores them with the lead record.

## Analytics Events

The page sends the following events to `/api/v1/consumer-evidence/event`:

- `tiktok_profile_visit`
- `starter_sheet_view`
- `email_capture_complete`
- `intake_pack_interest`
- `workshop_interest`

No event captures full documents, Social Security numbers, account numbers, or sensitive narrative details.

## Next Steps

1. Integrate router into `portal/main.py` behind a feature flag for internal testing.
2. Connect lead-capture endpoint to a waitlist table.
3. Implement email verification and Starter Sheet delivery.
4. Add automated tests for the endpoints.
5. Obtain deployment approval before production release.
