# Client #0 — UACC/Vroom Auto Loan: Evidence Intake Map & Violation Scorecard

**Case:** C-0001 | **Client:** Isiah Howard | **Tier:** Audit | **Status:** Intake
**Account:** UACC (United Auto Credit Corporation) / Vroom — 2015 Ford Taurus
**Balance:** $12,517.55 (collections, all 3 bureaus)
**Prepared:** 2026-06-09

---

## 1. Known Evidence Inventory

Documents already identified and cataloged in the fixture (`client_0001.json`):

| # | Document | Source | Date | Status |
|---|---|---|---|---|
| E1 | CFPB Complaint Response Letter — UACC Refuses to Delete | UACC Compliance Dept. | 2022-10-26 | ✅ Captured |
| E2 | Credit Report — Equifax (trade line: UACC auto loan) | Bureau | ~2022 | ✅ Captured |
| E3 | Credit Report — TransUnion (trade line: UACC auto loan) | Bureau | ~2022 | ✅ Captured |
| E4 | Credit Report — Experian (trade line: UACC auto loan) | Bureau | ~2022 | ✅ Captured |
| E5 | CFPB Complaint Filing (Case No. 221011-9546852) | CFPB Portal | 2022-10-11 | ⚠️ Referenced, full record needed |

---

## 2. Missing Evidence / Required Data Fields

Documents that must be located or requested to complete the intake. These are **gaps** — Phase 2 intake fields should be designed around them.

### Contract & Purchase Documents

| Missing Document | Why It Matters | Where to Find |
|---|---|---|
| Retail Installment Contract (RIC) | Establishes original terms, APR, total sale price, payment schedule. Without it, cannot verify balance or default date. | Vroom account online / email records |
| Vroom Purchase Agreement | Proves vehicle, price, down payment, trade-in, fees. Needed to establish chain from Vroom to UACC. | Vroom account online |
| Truth in Lending Act (TILA) disclosure | APR, finance charge, total of payments. Verify TILA compliance. | Original closing docs |

### Payment & Account History

| Missing Document | Why It Matters | Where to Find |
|---|---|---|
| Full payment history from opening (March 2021) to default | Establishes default date, charge-off date, payment amounts, any late fees. Needed for FCRA accuracy disputes. | UACC request / bank statements |
| Bank statements showing payments made | Cross-reference against UACC records. Prove timely payments if disputing default. | Bank records |

### Repossession & Deficiency (if applicable)

| Missing Document | Why It Matters | Where to Find |
|---|---|---|
| Repossession notice (UCC § 9-611) | UCC Article 9 requires *reasonable notification* of repossession. Missing or defective notice = FDCPA/UCC violation. | UACC / repossession agent |
| Notice of sale of collateral (UCC § 9-612/9-613) | Required before disposition. Must state time, place, method. Deficiency may be barred if notice defective. | UACC |
| Post-repossession accounting (UCC § 9-615) | Shows sale proceeds, application to balance, deficiency claimed. Must be commercially reasonable. | UACC |
| Deficiency balance letter | If UACC claims a deficiency beyond the $12,517.55. Must verify calculation. | UACC |

### Dispute & Validation Records

| Missing Document | Why It Matters | Where to Find |
|---|---|---|
| Debt validation letter (FDCPA § 809) | If UACC or a third-party collector sent one. Must include amount, creditor name, validation rights. | Mail / email |
| Dispute letters sent to bureaus (Equifax, TransUnion, Experian) | Proves FCRA § 611 reinvestigation request was made. Needed to claim failure-to-investigate. | Personal records |
| Bureau reinvestigation responses | Shows whether bureaus properly investigated. If they didn't, FCRA § 611 violation. | Mail / bureau portals |
| UACC direct dispute response | If disputed directly with UACC under FCRA § 623, their response (or lack thereof) matters. | Mail / email |

### Communications

| Missing Document | Why It Matters | Where to Find |
|---|---|---|
| Complete email thread with UACC Compliance | Only the CFPB response is captured. Pre-complaint and post-response emails establish the full timeline. | Gmail (UACC domain) |
| Vroom correspondence (purchase, delivery, issues) | Establishes the dealer relationship. Vroom may have made representations about financing. | Vroom account / email |
| Certified mail receipts | Proof of delivery for any dispute letters sent. Needed to prove receipt for FCRA/FDCPA claims. | USPS records |

### Credit Reports

| Missing Document | Why It Matters | Where to Find |
|---|---|---|
| Full tri-merge credit report (not just summaries) | Needed to see all trade lines, inquiry history, public records, and furnisher identifiers for all 3 bureaus. | AnnualCreditReport.com / myFICO |
| Historical credit reports from 2021-2024 | Establishes trade line timeline — when it first appeared, status changes, dispute history. | Personal archive |

---

## 3. Violation Scorecard Draft

Scored across 7 categories (each /10, total /70). Based on **currently known evidence only**. Scores will change as missing documents are located.

### Category 1: Credit Reporting (Score: **4/10**)

**What's wrong:** UACC auto loan trade line appears identically at $12,517.55 in "collections" status on all three bureaus. The account has been in collections since at least October 2022. No indication of whether UACC has reported accurate payment history, charge-off date, or current status in a format compliant with FCRA § 623(a).

**Evidence:** Fixture E2-E4 (credit report references). CFPB response (E1) confirms UACC refuses to delete the trade line.

**What's missing:**
- Full credit reports to verify accuracy of furnisher-reported data
- Dispute history and bureau reinvestigation responses
- Evidence of any FCRA § 611 reinvestigation by bureaus

**Potential violations:**
- FCRA § 623(a)(1)(A): Furnisher must provide accurate information
- FCRA § 623(a)(1)(B): Furnisher must correct and update
- FCRA § 611: Bureaus must conduct reasonable reinvestigation
- FCRA § 623(b): Direct dispute rights with furnisher

### Category 2: Collection Defense (Score: **4/10**)

**What's wrong:** Account is in collections at $12,517.55 across all bureaus. It's unclear whether:
- The amount includes improper fees, interest, or insurance products
- The debt was validated under FDCPA § 809 (if a third-party collector is/was involved)
- The statute of limitations on collection has been considered

**Evidence:** Fixture E5 (CFPB complaint filed Oct 2022). E1 (UACC refuses to delete).

**What's missing:**
- Debt validation letter (if any)
- Collector identity (UACC itself or a third-party agency)
- Any collection call logs or communications
- State SOL calculation for auto loan deficiency

**Potential violations:**
- FDCPA § 809(a): Validation notice requirements (if third-party collector)
- FDCPA § 807: False or misleading representations
- FCRA § 623(a)(5): Duty to notify of disputed status

### Category 3: Housing (Score: **7/10**)

**What's wrong:** (Not directly applicable to an auto loan case — scored neutral/positive because no housing-related credit damage from this account has been identified.)

**Assessment:** No evidence of housing impact from this trade line. Score reflects absence of negative housing indicators rather than strength.

### Category 4: Employment (Score: **8/10**)

**What's wrong:** (Not directly applicable — scored neutral/positive.)

**Assessment:** No evidence of employment impact. Credit check for employment could surface the collections status but no adverse action flagged yet.

### Category 5: Documentation (Score: **5/10**)

**What's wrong:** Of the estimated 25+ documents needed for a complete case file, only 4 are confirmed captured (the CFPB response and 3 credit report references). The CFPB complaint filing itself is referenced but its full record is not in the evidence file. No contract, payment history, repossession documents, or dispute records are confirmed.

**Evidence:** E1-E5 partially captured. ~20+ documents flagged as missing in Section 2 above.

**What's missing:** Nearly all primary documents — contract, payment history, repossession/ deficiency records, full dispute trail, certified mail receipts.

**Assessment:** This is the weakest category. Without the original contract and payment history, the balance cannot be independently verified. Without repossession documentation, UCC Article 9 claims cannot be evaluated.

### Category 6: Evidence (Score: **5/10**)

**What's wrong:** Evidence is scattered across Gmail, bureau portals, USPS records, and personal files. No centralized evidence folder exists with consistent naming, OCR, or chain-of-custody tracking. The CFPB response is the only document with a detailed outcome description.

**Evidence:** E1 has high-confidence outcome notes. E2-E4 are referenced but actual report PDFs are not in the evidence file.

**What's missing:**
- Scanned/original PDFs of all credit reports
- OCR-processed text for search and analysis
- Standardized file naming and folder structure
- Chain-of-custody log for each evidence item

### Category 7: Follow-Up (Score: **3/10**)

**What's wrong:** The CFPB complaint (Oct 2022) received a response (Oct 26, 2022) — UACC refused to delete. There is no evidence of:
- Any follow-up action after the CFPB response
- Dispute letters to bureaus after UACC's refusal
- Escalation within CFPB or to state AG
- Timeline tracking for SOL or FCRA reinvestigation deadlines

**Assessment:** The case appears to have gone dormant after the CFPB response. This is the most actionable category — several follow-up steps are immediately available.

---

## 4. Summary Scorecard

| Category | Score | Status |
|---|---|---|
| 1. Credit Reporting | 4/10 | ⚠️ Needs bureau disputes and reinvestigation history |
| 2. Collection Defense | 4/10 | ⚠️ Needs validation records and SOL analysis |
| 3. Housing | 7/10 | ✅ No negative impact identified |
| 4. Employment | 8/10 | ✅ No adverse action flagged |
| 5. Documentation | 5/10 | ⚠️ ~20+ key documents missing |
| 6. Evidence | 5/10 | ⚠️ Scattered, not centralized or OCR'd |
| 7. Follow-Up | 3/10 | 🔴 Case dormant since Oct 2022 |
| **Total** | **36/70** | **WEAK** |

---

## 5. Findings (Vicktor-Gated — 3 Questions Each)

### Finding 1: Stale CFPB Complaint — No Follow-Up

- **Q1 — What is wrong?** The CFPB complaint (Case 221011-9546852) was filed October 2022. UACC responded on October 26, 2022, refusing to delete the trade line. No follow-up action has been taken in over 3.5 years.
- **Q2 — What evidence supports it?** E1 (CFPB Response Letter, Oct 26, 2022). E5 (CFPB Complaint reference). No subsequent evidence items exist beyond October 2022.
- **Q3 — What should happen next?** Reopen the CFPB complaint or file a new one. Request UACC's written verification of the debt under FCRA § 623. Send fresh dispute letters to all three bureaus citing the CFPB response as evidence of disputed status.

### Finding 2: Missing Repossession Documentation

- **Q1 — What is wrong?** If the vehicle was repossessed, UCC Article 9 requires specific notices before and after repossession. These documents are not in the evidence file, and their absence prevents evaluation of whether repossession and deficiency were handled properly.
- **Q2 — What evidence supports it?** The account status is "collections" with a balance of $12,517.55 — consistent with a deficiency after repossession and sale. No repossession notices are in evidence.
- **Q3 — What should happen next?** Request from UACC: (1) notice of repossession (UCC § 9-611), (2) notice of sale (UCC § 9-612/9-613), (3) post-sale accounting (UCC § 9-615), (4) deficiency calculation. If notices were defective or missing, the deficiency may be barred.

### Finding 3: Incomplete Credit Reporting

- **Q1 — What is wrong?** The $12,517.55 trade line appears identically on all three bureaus in "collections" status. Without full credit reports and dispute history, it's impossible to verify whether UACC is reporting accurately under FCRA § 623(a).
- **Q2 — What evidence supports it?** E2-E4 (credit report references). The CFPB response confirms UACC stands by its reporting.
- **Q3 — What should happen next?** Pull full tri-merge credit reports. Send FCRA § 623 direct dispute to UACC. Send FCRA § 611 reinvestigation requests to all three bureaus. Document all responses.

### Finding 4: Contract & Payment History Gap

- **Q1 — What is wrong?** The original Retail Installment Contract and full payment history are not in the evidence file. Without them, the claimed $12,517.55 balance cannot be independently verified.
- **Q2 — What evidence supports it?** The balance is self-reported by UACC. No independent documentation of the original loan amount, payments made, or how the deficiency was calculated exists.
- **Q3 — What should happen next?** Request the original contract and complete payment history from UACC under FCRA § 623. Request bank statements for the payment period. Compare payment records against UACC's balance claim.

---

## 6. Recommended Phase 2 Intake Fields

Based on gaps identified above, the intake module should capture these fields (in addition to what `EvidenceItem` currently supports):

**Document-level fields to add:**
- `document_type` — enum: contract, credit_report, dispute_letter, cfpb_complaint, repossession_notice, deficiency_letter, payment_record, correspondence, court_filing
- `date_received` — date document was obtained
- `original_source` — enum: bureau, creditor, cfpb, usps, email, personal_record, court
- `ocr_text_path` — path to OCR-processed text file
- `certified_mail_tracking` — USPS tracking number (for dispute letters)
- `chain_of_custody` — list of actions taken on the document

**Case-level fields to add:**
- `statute_of_limitations_date` — SOL for collection/deficiency
- `last_activity_date` — last action taken on the case
- `next_action_date` — next scheduled action
- `cfbp_case_numbers` — list of CFPB complaint IDs
- `furnisher_list` — list of data furnishers (creditors reporting to bureaus)

---

## 7. Immediate Next Steps (Priority Order)

| Priority | Action | Owner |
|---|---|---|
| P1 | Pull full tri-merge credit reports from AnnualCreditReport.com | Isiah |
| P2 | Search Gmail for all UACC/Vroom correspondence (contract, payment confirmations, dispute emails) | Isiah |
| P3 | Locate and scan the original Retail Installment Contract | Isiah |
| P4 | Request payment history from UACC (FCRA § 623 direct dispute) | Hermes to draft |
| P5 | Locate any repossession notices (mail, email, USPS informed delivery) | Isiah |
| P6 | File new CFPB complaint or reopen existing case 221011-9546852 | Hermes to draft |
| P7 | Send FCRA § 611 reinvestigation letters to Equifax, TransUnion, Experian | Hermes to draft |
| P8 | Set up standardized evidence folder structure per `helpers.py` naming convention | Hermes |

**Rule:** No dispute letters or legal demand letters until all P1-P5 evidence is collected and the scorecard is updated. Evidence first, score second, letters third.