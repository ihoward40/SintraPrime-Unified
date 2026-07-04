# Next Actions — UACC/Vroom Auto Loan

**Case:** C-0001 | **Client:** Isiah Howard
**Scorecard Baseline:** 36/70 — WEAK
**Last Updated:** 2026-06-09

---

## How to Use This Checklist

1. Complete actions in priority order (P1 → P2 → P3)
2. Check off each item only when the document is **in the evidence folder**
3. After each batch of 2-3 actions, update the scorecard
4. Do not draft dispute letters until minimum readiness is met

---

## Priority 1: Immediate (This Week)

- [ ] **P1.1** Pull full tri-merge credit reports from AnnualCreditReport.com
  - *Why:* Without full reports, cannot verify UACC's reporting accuracy or file FCRA disputes
  - *Output:* PDFs → `credit-reports/`
  - *Updates scorecard:* Credit Reporting, Documentation

- [ ] **P1.2** Search Gmail for all UACC/Vroom correspondence
  - *Search terms:* "UACC", "United Auto Credit", "Vroom", "auto loan", "2015 Ford Taurus"
  - *Look for:* Contract, payment confirmations, dispute emails, repossession notices
  - *Output:* PDFs → `correspondence/`
  - *Updates scorecard:* Documentation, Evidence

- [ ] **P1.3** Locate and scan the original Retail Installment Contract
  - *Check:* Vroom account online, email archives, personal files
  - *Why:* Without the RIC, the claimed $12,517.55 balance cannot be independently verified
  - *Output:* PDF → `intake/`
  - *Updates scorecard:* Documentation, Credit Reporting

- [ ] **P1.4** Request full payment ledger from UACC
  - *Method:* Written request under FCRA § 623 (Hermes to draft)
  - *Why:* Establishes default date, charge-off date, payment history
  - *Output:* Response → `correspondence/`
  - *Updates scorecard:* Documentation, Credit Reporting

- [ ] **P1.5** Locate any repossession notices (mail, email, USPS Informed Delivery)
  - *Check:* Physical mail files, email archives, USPS Informed Delivery history
  - *Look for:* Notice of Right to Cure, Notice of Repossession, Notice of Sale
  - *Output:* PDFs → `intake/`
  - *Updates scorecard:* Collection Defense, Documentation

---

## Priority 2: Short-Term (Next Two Weeks)

- [ ] **P2.1** Download full CFPB complaint record (Case 221011-9546852)
  - *Method:* CFPB portal — request complete case file
  - *Why:* Establishes exact allegations, relief sought, and CFPB's disposition
  - *Output:* PDF → `correspondence/`

- [ ] **P2.2** Search for prior dispute letters sent to bureaus
  - *Check:* Personal files, email, certified mail receipts
  - *Why:* Proves FCRA § 611 reinvestigation requests were made
  - *Output:* PDFs → `disputes/`

- [ ] **P2.3** Locate bank statements for the payment period (March 2021 — default date)
  - *Check:* Online banking archives, paper statements
  - *Why:* Cross-reference against UACC's claimed payment history
  - *Output:* PDFs → `intake/`

- [ ] **P2.4** Request deficiency calculation from UACC
  - *Method:* Written request
  - *Why:* Verify the $12,517.55 balance includes proper credits for sale proceeds
  - *Output:* Response → `correspondence/`

- [ ] **P2.5** Create case timeline from contract date through current reporting date
  - *Data sources:* All documents collected in P1
  - *Format:* Chronological list with key dates (contract, payments, default, repo, CFPB, disputes)
  - *Output:* `output/timeline.md`

---

## Priority 3: Medium-Term (Within 30 Days)

- [ ] **P3.1** Request historical credit reports (2021-2024) from personal archive
- [ ] **P3.2** Search for debt validation letter from any third-party collector
- [ ] **P3.3** Locate Vroom purchase agreement and delivery documents
- [ ] **P3.4** Check State AG database for any UACC complaints
- [ ] **P3.5** Compile certified mail receipts for all prior dispute letters
- [ ] **P3.6** Set up standardized evidence folder structure per `helpers.py` naming convention

---

## Readiness Gate

Before any dispute letter is drafted, ALL of the following must be checked off:

- [ ] **Gate 1:** Full tri-merge credit report obtained
- [ ] **Gate 2:** UACC tradeline details captured from all 3 bureaus
- [ ] **Gate 3:** Retail installment contract located or requested
- [ ] **Gate 4:** Repo/sale/deficiency documents located or requested
- [ ] **Gate 5:** Prior CFPB/bureau dispute records attached
- [ ] **Gate 6:** Timeline created from contract date through current reporting date

**Current readiness: 1/6 — DO NOT DRAFT DISPUTES**

---

## Scorecard Update Triggers

Update the scorecard after each of these milestones:

| Milestone | Categories Affected |
|---|---|
| Credit reports obtained | Credit Reporting (+1-3), Documentation (+1) |
| RIC located | Documentation (+2), Credit Reporting (+1) |
| Repo docs located | Collection Defense (+2), Documentation (+1) |
| Payment ledger obtained | Documentation (+1), Credit Reporting (+1) |
| Dispute records attached | Follow-Up (+2), Credit Reporting (+1) |
| Timeline created | Follow-Up (+1), Evidence (+1) |
| Evidence centralized + OCR'd | Evidence (+2) |
| CFPB reopened | Follow-Up (+2) |

**Target:** 50+/70 before drafting any dispute.