# Trust Compliance Module — Make.com Automation Blueprint

This document describes the Make.com (formerly Integromat) scenario blueprint
for the Trust Document Compliance Refactor workflow.

**Important:** Live external submissions (letters, filings, agency notices) remain
disabled until Notion/Make receipt logging and destination-context safety gates
are fully implemented and tested.

---

## Scenario 1: Document Intake & Compliance Run

**Trigger:** Typeform / intake form submission (new client upload)

**Steps:**

1. **Watch Typeform submissions**
   - Module: `Typeform → Watch Responses`
   - Filter: field `service_tier` is not empty

2. **Download uploaded document**
   - Module: `HTTP → Get a file` (from Typeform file URL)

3. **Store in Google Drive**
   - Module: `Google Drive → Upload a file`
   - Destination: `Trust Compliance / Intake / {submission_date} — {client_name}`

4. **Create Notion intake record**
   - Module: `Notion → Create a database item`
   - Database: Trust Compliance Runs
   - Fields: Document Title, Run Date (now), Status = `PENDING_REVIEW`, Assigned To = reviewer

5. **Send confirmation email to client**
   - Module: `Gmail → Send an email`
   - Template: "We have received your document. Our compliance review will begin within 1 business day."

6. **Slack notification to team**
   - Module: `Slack → Create a message`
   - Channel: `#trust-compliance-intake`
   - Message: "New intake: {document_title} from {client_name} — {service_tier}"

---

## Scenario 2: Post-Compliance-Run Receipt Logging

**Trigger:** Webhook from `runTrustComplianceMission` completion

**Steps:**

1. **Receive webhook payload**
   - Module: `Webhooks → Custom webhook`
   - Expected fields: `runId`, `documentTitle`, `greenCount`, `yellowCount`, `redCount`, `blockedExports`, `receipt`

2. **Update Notion run record**
   - Module: `Notion → Update a database item`
   - Lookup: Run ID = `{{runId}}`
   - Update: GREEN Count, YELLOW Count, RED Count, Blocked Exports, Status

3. **Set Status logic**
   - If `redCount > 0` → Status = `BLOCKED`, Assigned To = attorney/CPA queue
   - Else if `yellowCount > 0` → Status = `REWRITE_REQUIRED`
   - Else → Status = `COMPLETE`

4. **Upload receipt files to Google Drive**
   - Module: `Google Drive → Upload a file`
   - Files: `run_receipt.json`, `risk_register.json`
   - Destination: `Trust Compliance / {runId} — {documentTitle}`

5. **Conditional: notify reviewer if BLOCKED**
   - Filter: `redCount > 0`
   - Module: `Gmail → Send an email`
   - Template: "BLOCKED run {runId}: {redCount} RED clause(s) require attorney/CPA review before any delivery."

---

## Scenario 3: Stripe Payment → Intake Form Delivery

**Trigger:** Stripe → Payment intent succeeded

**Steps:**

1. **Watch Stripe events**
   - Module: `Stripe → Watch Events`
   - Filter: `event.type = payment_intent.succeeded`

2. **Identify service tier from metadata**
   - Parse `metadata.service_tier` from payment intent:
     - `$97`  → Trust Document Safety Scan
     - `$197` → Bank-Safe Trust Packet Cleanup
     - `$297` → Compliance Rewrite Pack
     - `$497` → Full Trust Compliance Refactor

3. **Send intake form link**
   - Module: `Gmail → Send an email`
   - Template: Tier-specific intake form URL
   - Fields: client name (from Stripe billing details), amount, service description

4. **Create CRM record**
   - Module: `Notion → Create a database item`
   - Database: Clients
   - Fields: Name, Email, Tier, Payment Date, Status = `INTAKE_SENT`

5. **Notify team**
   - Module: `Slack → Create a message`
   - Channel: `#trust-compliance-sales`
   - Message: "New {tier} client: {client_name} — intake form sent."

---

## Scenario 4: Manual Review Gating (Attorney/CPA Queue)

**Trigger:** Notion → Watch Database Items (Status = `BLOCKED`)

**Steps:**

1. **Watch Notion for BLOCKED items**
   - Module: `Notion → Watch Database Items`
   - Filter: Status = `BLOCKED`

2. **Create task in attorney/CPA queue**
   - Module: `Notion → Create a database item`
   - Database: Review Queue
   - Fields: Run ID (linked), Priority = High, Due = 3 business days

3. **Send email to review team**
   - Module: `Gmail → Send an email`
   - To: `compliance-review@yourdomain.com`
   - Template: "BLOCKED compliance run requires attorney/CPA review before any client delivery. Run: {runId}."

---

## Environment Variables Required

| Variable | Description |
|---|---|
| `MAKE_WEBHOOK_URL` | Webhook URL for Scenario 2 (post-run receipt) |
| `NOTION_RUNS_DB_ID` | Notion database ID for Trust Compliance Runs |
| `NOTION_CLIENTS_DB_ID` | Notion database ID for Clients |
| `NOTION_REVIEW_QUEUE_DB_ID` | Notion database ID for Review Queue |
| `GOOGLE_DRIVE_FOLDER_ID` | Root Google Drive folder ID |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `REVIEW_TEAM_EMAIL` | Email address for attorney/CPA review queue |

---

## Notes

- Scenarios 1–4 must be tested in Make.com sandbox mode before activation.
- No external letters, filings, or notices are generated automatically.
- All client deliveries require manual review and approval after the compliance run.
- Reserve exhibits must never be attached to client-facing deliverables without attorney sign-off.
