# Trust Compliance Module — Fulfillment SOP

Standard Operating Procedure for processing Trust Document Compliance
Refactor orders from intake through delivery.

---

## Roles

| Role | Responsibility |
|---|---|
| **Intake Coordinator** | Receives payment notification, sends intake form, creates Notion record |
| **Compliance Analyst** | Runs the compliance engine, reviews outputs |
| **Review Lead** | Reviews any RED-flagged clauses; approves or escalates |
| **Delivery Coordinator** | Assembles final package, sends to client |
| **Attorney/CPA (external)** | Reviews RED clauses on referral; not part of standard flow |

---

## Step 1: Payment Confirmation (Day 0)

1. Stripe sends payment notification (webhook → Make.com Scenario 3).
2. Make.com identifies service tier from payment metadata.
3. Intake form link is emailed to the client automatically.
4. CRM record created in Notion (Status: `INTAKE_SENT`).
5. Slack notification sent to `#trust-compliance-sales`.

**Time target:** Automated — within 5 minutes of payment.

---

## Step 2: Document Receipt (Day 0–1)

1. Client completes the intake form and uploads their document.
2. Make.com downloads the file and stores it in Google Drive:
   `Trust Compliance / Intake / {date} — {client_name}`
3. Notion record updated (Status: `DOCUMENT_RECEIVED`).
4. Slack notification to `#trust-compliance-intake`.

**If no response within 48 hours:** Send one follow-up email.
**If no response within 5 days:** Mark status `INTAKE_STALLED`; notify Intake Coordinator.

---

## Step 3: Compliance Engine Run (Day 1–2)

1. Compliance Analyst retrieves the document from Google Drive.
2. Run `runTrustComplianceMission` with the document text.
3. Engine produces:
   - `run_receipt.json`
   - `risk_register.json`
   - `clause_classification_table.md`
   - `exhibit_index.md`
   - Rewritten clauses (if YELLOW present, Tier 2+)
   - Recommendations (Tier 3+)
4. Make.com webhook posts receipt to Notion; files uploaded to Google Drive.
5. Notion record updated with clause counts and Status.

**If RED clauses detected:**
- Status → `BLOCKED`
- Task created in Review Queue (high priority, 3-day deadline)
- Attorney/CPA review notification sent
- Proceed to Step 3a

**If only GREEN/YELLOW:**
- Status → `REWRITE_REQUIRED` (if YELLOW) or `COMPLETE` (if GREEN only)
- Proceed to Step 4

### Step 3a: Attorney/CPA Review (RED clauses only)

1. Review Lead reviews the blocked clauses.
2. If clauses can be removed or rewritten: proceed to Step 4 with revised document.
3. If clauses cannot be cleared: notify client that those sections cannot be
   included in any deliverable. Provide a partial report with GREEN/YELLOW
   sections only.
4. Document decision in Notion review record.

---

## Step 4: Manual Review Before Delivery (All Tiers)

**Checklist (complete for every order):**

- [ ] Run receipt generated and verified
- [ ] Risk register reviewed — no RED clauses in deliverable
- [ ] Rewritten clauses reviewed for accuracy and safety (Tier 2+)
- [ ] Exhibit index reviewed — reserve exhibits excluded from public deliverable
- [ ] Recommendations reviewed — no blocked actions in client-facing output (Tier 3+)
- [ ] Client name and document title match intake form
- [ ] No personally identifiable information (SSN, account numbers) in deliverable
- [ ] Delivery package assembled per tier specification

**Do not deliver if any of the following are true:**
- Any RED clause is present in the deliverable
- Reserve exhibit is included in the public package
- Run receipt is missing
- Risk register shows `DO_NOT_SEND` tag on any included clause

---

## Step 5: Delivery (Day 1–5 depending on tier)

**Tier 1 ($97):**
- Email: PDF summary + `risk_register.json` + `run_receipt.json`
- No rewritten clauses included

**Tier 2 ($197):**
- Email: PDF summary + rewritten clauses document + public exhibit index
- Attach: `risk_register.json` + `run_receipt.json`

**Tier 3 ($297):**
- Email: Full document package (PDF) + all JSON outputs
- Include: All-context recommendations + reserve exhibit index (labeled internal only)

**Tier 4 ($497):**
- Email: Full package + Notion record link + Google Drive folder link
- Schedule: 30-minute review call within 3 business days of delivery
- Set calendar reminder for 30-day re-scan offer

---

## Step 6: Post-Delivery

1. Update Notion record: Status → `DELIVERED`, Delivery Date = today.
2. File all outputs in Google Drive: `Trust Compliance / Delivered / {date} — {client_name}`
3. Archive intake documents (do not delete — retain for 7 years per records policy).
4. Send follow-up email at Day 7: "Do you have questions about your compliance report?"
5. Tier 4: Send re-scan reminder at Day 30.

---

## Escalation Contacts

| Situation | Contact |
|---|---|
| RED clause requires legal interpretation | Attorney referral list (maintained separately) |
| Tax position or W-8/W-9 issue | CPA referral list (maintained separately) |
| Client disputes the classification | Review Lead → escalate to attorney if unresolved |
| Technical issue with compliance engine | Engineering on-call |

---

## Records Retention

- All compliance runs: retain 7 years minimum
- Run receipts and risk registers: retain permanently (immutable audit record)
- Client documents: retain 7 years; then purge per data retention policy
- Payment records: retain per Stripe and tax requirements (7 years)
