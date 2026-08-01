# Product Artifact Inventory — IKE Solutions Consumer Evidence Line

Mission: SP-TKM-001
Owner: Revenue Architect
Status: Internal production-ready drafts — no checkout, payment, or public launch

## Product Ladder

| Level | Product | Validation Price | Status | Artifact Path |
|---|---|---|---|---|
| 0 | Consumer Evidence Case Starter Sheet | Free | Draft complete | `offers/consumer-evidence/FREE_STARTER_SHEET.md` |
| 1 | Consumer Evidence Intake Pack | $9 | Outline complete; full draft in progress | `offers/consumer-evidence/INTAKE_PACK/` |
| 2 | Consumer Evidence Starter Kit | $49 | Draft in progress | `offers/consumer-evidence/STARTER_KIT/` |
| 3 | Build Your Consumer Evidence File Workshop | $79 | Agenda + workbook draft in progress | `offers/consumer-evidence/WORKSHOP/` |

## 1. Consumer Evidence Case Starter Sheet

### Purpose
Free lead magnet that captures email and teaches the basic case-organization method.

### Deliverable
`offers/consumer-evidence/FREE_STARTER_SHEET.md` (printable PDF-ready markdown)

### Sections
1. Case Summary
2. Party List
3. Timeline
4. Document Inventory
5. Communication Log
6. Deadlines
7. Desired Resolution
8. Missing Evidence
9. Questions Requiring Professional Review
10. Redaction Reminder
11. Disclaimer

### Acceptance Criteria
- [x] All sections present
- [x] No request for SSN, account numbers, or payment data
- [x] Educational disclaimer included
- [x] Redaction guidance included
- [ ] Visual PDF layout approved
- [ ] UTM link inserted for digital version

## 2. Consumer Evidence Intake Pack

### Purpose
$9 entry product that gives a guided, organized start to a consumer case file.

### Deliverable
`offers/consumer-evidence/INTAKE_PACK/INTAKE_PACK_OUTLINE.md`

### Full Draft File Structure
```
INTAKE_PACK/
├── README_FIRST.pdf
├── 01_CASE_STARTER_SHEET.pdf
├── 02_PARTY_LIST.pdf
├── 03_TIMELINE.pdf
├── 04_DOCUMENT_INVENTORY.pdf
├── 05_COMMUNICATION_LOG.pdf
├── 06_DEADLINES_TRACKER.pdf
├── 07_REDACTION_GUIDE.pdf
├── 08_QUICK_START.pdf
├── 09_GLOSSARY.pdf
├── 10_RESOURCE_DIRECTORY.pdf
└── editable/
    ├── party_list.txt
    ├── timeline.csv
    ├── document_inventory.csv
    └── communication_log.csv
```

### Acceptance Criteria
- [x] Outline complete
- [ ] All ten PDF templates drafted
- [ ] Editable files drafted
- [ ] README_FIRST drafted
- [ ] Terms/disclaimer page drafted
- [ ] Delivery manifest complete
- [ ] Zip file manifest tested
- [ ] Mobile-readable PDF layout verified

## 3. Consumer Evidence Starter Kit

### Purpose
$49 core product with expanded templates, checklists, sample dispute letters, and exhibit index guidance.

### Deliverable
`offers/consumer-evidence/STARTER_KIT/STARTER_KIT_OUTLINE.md`

### Proposed Contents
1. Everything in the Intake Pack
2. Sample dispute letters (debt, credit bureau, collector)
3. Request-for-production checklist
4. Affidavit review checklist
5. Assignment chain checklist
6. Exhibit index template
7. Hearing/deadline tracker
8. State statute-of-limitations reference table (disclaimer: verify current law)
9. Redaction guide (advanced)
10. Attorney consultation prep sheet
11. Workshop discount code

### Acceptance Criteria
- [ ] Outline complete
- [ ] All templates drafted
- [ ] Sample letters reviewed for jurisdiction-neutral language
- [ ] Disclaimer and scope limits included
- [ ] File manifest complete

## 4. Build Your Consumer Evidence File Workshop

### Purpose
$79 live or recorded workshop that walks participants through building a complete case file.

### Deliverable
`offers/consumer-evidence/WORKSHOP/`

### Contents
- `WORKSHOP_CURRICULUM.md`
- `PARTICIPANT_WORKBOOK.md`
- `FACILITATOR_GUIDE.md`
- `SLIDES/` (placeholder)
- `RECORDING_POLICY.md`

### Curriculum Outline (90 minutes)
1. Welcome and disclaimer (5 min)
2. Define the issue (10 min)
3. Identify every party (10 min)
4. Build the timeline (15 min)
5. Inventory the documents (15 min)
6. Redact safely (10 min)
7. Compare claims against evidence (15 min)
8. Identify missing documents and next steps (10 min)
9. Q&A and next offers (10 min)

### Acceptance Criteria
- [ ] Curriculum drafted
- [ ] Participant workbook drafted
- [ ] Facilitator guide drafted
- [ ] Recording and replay policy drafted
- [ ] Refund policy drafted
- [ ] Terms/disclaimer included

## 5. Product Terms and Educational Disclaimer

### Deliverable
`offers/consumer-evidence/TERMS_AND_DISCLAIMER.md`

### Required Statements
1. All products provide general consumer education and organizational tools.
2. IKE Solutions is not a law firm and does not provide legal representation.
3. Products do not create an attorney-client relationship.
4. Outcomes depend on individual facts, jurisdiction, and evidence.
5. No guaranteed outcome, dispute result, record removal, or credit improvement.
6. Users should consult a qualified professional for individualized advice.
7. Products are for personal, non-commercial use unless licensed otherwise.
8. Unauthorized resale or redistribution is prohibited.

## 6. Refund Policy Recommendation

### Deliverable
`offers/consumer-evidence/REFUND_POLICY.md`

### Recommended Policy
- **Digital products:** 14-day money-back guarantee if the buyer has not downloaded the files or if the files are materially defective. Once downloaded and opened, refunds are at IKE Solutions' discretion.
- **Workshops:** Full refund up to 48 hours before the event. No refund within 48 hours unless the event is cancelled by IKE Solutions. Replay access may be offered instead.
- **Process:** Buyer emails ISIAHH@ikesolutions.org with order information and reason. Refunds processed within 5–10 business days.

### Rationale
Low-price digital products with 14-day refund window reduce purchase friction and support validation without creating high fraud risk.

## 7. Delivery File Manifest

### Deliverable
`offers/consumer-evidence/DELIVERY_MANIFEST.md`

### Standard Delivery Method
- Files delivered as a single ZIP download after email verification.
- No physical shipping.
- No recurring billing.
- Access link expires after 30 days; reissue available on request.

### Per-Product Manifest

#### Starter Sheet (Free)
- Single PDF
- No checkout required
- Email capture required
- UTM attribution captured

#### Intake Pack ($9)
- ZIP with 10 PDFs + editable folder
- Email capture + waitlist confirmation
- No active checkout in Phase Two; placeholder price shown
- Delivery email with download link

#### Starter Kit ($49)
- ZIP with expanded PDFs + editable folder + sample letters
- Email capture + purchase confirmation
- No active checkout in Phase Two
- Delivery email with download link + workshop discount

#### Workshop ($79)
- Registration form (name, email, topic of interest)
- Confirmation email with calendar invite and access link
- Participant workbook PDF delivered 24 hours before event
- Recording link delivered within 48 hours after event

## 8. Next Steps

1. Convert Starter Sheet to styled PDF.
2. Draft all Intake Pack PDF templates.
3. Complete Starter Kit outline and templates.
4. Finalize workshop curriculum, workbook, and facilitator guide.
5. Review all terms, disclaimer, and refund policy with Sentinel.
6. Build delivery automation spec (no payment in Phase Two).
