# Issues to Verify — UACC/Vroom Auto Loan

**Case:** C-0001 | **Client:** Isiah Howard
**Evidence Rule:** A fact is not "confirmed" unless tied to a located file path, email export, credit report line, CFPB record, or source document. Unsourced memory goes in "Suspected / To Verify," not "Confirmed."
**Last Updated:** 2026-06-10

---

## 1. Confirmed Facts

Each fact below is tied to a located source document in the evidence manifest:

| # | Fact | Source File | Evidence ID |
|---|---|---|---|
| F1 | UACC auto loan trade line exists on Experian at $10,831, charged off, prior FCRA dispute completed | `credit-reports/Experian.pdf` (p.27) | F3a |
| F2 | Account opened March 22, 2021 (corrected from fixture's March 15) | `credit-reports/Experian.pdf` (p.27) | F3a |
| F3 | Original balance: $12,751 | `credit-reports/Experian.pdf` (p.27) | F3a |
| F4 | Written off amount: $11,614 | `credit-reports/Experian.pdf` (p.27) | F3a |
| F5 | Current balance: $10,831 (discrepancy with previously recorded $12,517.55) | `credit-reports/Experian.pdf` (p.27) | F3a |
| F6 | Account charged off since August 2022 | `credit-reports/Experian.pdf` (payment history) | F3a |
| F7 | Payment history: 30-day late May 2021, 60-day Jun 2021, 90-day Jul 2021, CO from Aug 2022 | `credit-reports/Experian.pdf` (payment history) | F3a |
| F8 | Furnisher: UNITED AUTO CREDIT CO, 1071 Camelback St Ste 10, Newport Beach, CA 92660 | `credit-reports/Experian.pdf` (p.27) | F3a |
| F9 | Prior FCRA dispute completed — "Completed investigation of FCRA dispute - consumer disagrees" | `credit-reports/Experian.pdf` (comments) | F3a |
| F10 | CFPB Complaint No. 221011-9546852 was filed October 11, 2022 | `packages/credit_command_center/fixtures/client_0001.json` | F5 (reference only) |
| F11 | UACC responded to CFPB on October 26, 2022, refusing to delete the trade line | `packages/credit_command_center/fixtures/client_0001.json` | E1 (reference only) |
| F12 | Vehicle: 2015 Ford Taurus, VIN ending FG124116 | `intake_templates/uacc_vroom_evidence_template.json` | account_identifier field |

---

## 2. Suspected Issues

These are plausible based on confirmed facts but **require additional source documents to verify**:

| # | Suspected Issue | Why Suspected | What Source Document Is Needed |
|---|---|---|---|
| S1 | **Balance discrepancy** — Reported balance ($10,831) differs from previously recorded amount ($12,517.55) by $1,686.55 | Credit report shows $10,831; CFPB response shows $12,517.55. One of these is wrong. | Retail Installment Contract, full payment ledger, CFPB case file |
| S2 | UACC may be reporting inaccurate payment history under FCRA § 623(a) | Trade line in collections/charge-off. Payment history shows rapid delinquency (30→60→90→CO in 4 months). | Full payment ledger from UACC, bank statements |
| S3 | Repossession may have occurred without proper UCC Article 9 notice | Account charged off with deficiency balance — repossession is typical for auto loans. No repo notices in evidence. | Notice of Repossession (UCC § 9-611), Notice of Sale (UCC § 9-612/9-613) |
| S4 | Deficiency calculation may include improper fees or charges | $10,831 balance cannot be verified without original contract and payment history. Written off amount ($11,614) exceeds current balance ($10,831). | Retail Installment Contract, full payment ledger, post-sale accounting |
| S5 | Bureaus may not have conducted reasonable reinvestigation under FCRA § 611 | Experian shows dispute completed but consumer disagrees. No reinvestigation responses in evidence. | Bureau reinvestigation responses, prior dispute letters |
| S6 | Statute of limitations may have expired for collection/deficiency | Account opened March 2021 — SOL depends on state law and default date. | Default date from payment ledger, state SOL statute |
| S7 | UACC may have failed to report account as disputed under FCRA § 623(a)(5) | CFPB complaint filed Oct 2022 — if UACC was notified of dispute, they must report status to bureaus | CFPB complaint full record, bureau credit reports showing dispute flags |
| S8 | Account may be reported as individual liability when it was a trust obligation | Experian shows "Responsibility: Individual." If account was secured by trust assets, reporting as individual may be inaccurate. | Trust documentation, UCC-1 filing, certification of trust |

---

## 3. Missing Proof (Source Documents Needed)

| # | Missing Source Document | Which Issue It Proves | Priority |
|---|---|---|---|
| M1 | Full tri-merge credit reports (EQ, TU, EX) — PDF from AnnualCreditReport.com | S1, S2, S5, S7 | P1 |
| M2 | Retail Installment Contract — PDF from Vroom account or email | S1, S4 | P1 |
| M3 | Full payment ledger from UACC — written response to FCRA § 623 request | S1, S2, S4, S6 | P1 |
| M4 | Notice of Repossession (UCC § 9-611) — mail or email copy | S3 | P1 |
| M5 | Notice of Sale / Disposition (UCC § 9-612/9-613) — mail or email copy | S3 | P1 |
| M6 | Post-sale accounting / auction results (UCC § 9-615) — mail or email copy | S3, S4 | P1 |
| M7 | Deficiency calculation letter — mail or email copy | S1, S4 | P1 |
| M8 | Prior dispute letters sent to bureaus — personal records or email | S5 | P1 |
| M9 | Bureau reinvestigation responses — mail or bureau portal download | S5 | P1 |
| M10 | CFPB complaint full record (Case 221011-9546852) — CFPB portal download | S1, S7 | P2 |
| M11 | Historical credit reports (2021-2024) — personal archive | S1, S6 | P2 |
| M12 | Debt validation letter (if any collector involved) — mail or email copy | S6 | P2 |
| M13 | Trust documentation / UCC-1 filing | S8 | P2 |

---

## 4. Questions for Creditor / Furnisher (UACC)

To be asked in a FCRA § 623 direct dispute letter **(do not send until evidence packet is ready)** :

1. Please provide a complete payment history from account opening (March 22, 2021) through charge-off, including all payments received, late fees assessed, and the date of last payment.
2. Please provide the date and method of default determination.
3. Was the vehicle repossessed? If so, please provide:
   - Date of repossession
   - Copy of any notice of repossession sent to the consumer
   - Copy of any notice of sale/disposition sent to the consumer
   - Date and method of sale (public/private auction)
   - Sale proceeds and how they were applied to the balance
   - Complete deficiency calculation
4. Please provide a copy of the original Retail Installment Contract.
5. Please identify all dates on which the account was reported to each credit bureau and the specific information furnished on each date.
6. Was this account ever referred to a third-party collection agency? If so, please identify the agency and dates of referral.
7. Please provide the date of charge-off and the amount charged off.
8. Was a 1099-C issued for this account? If so, please provide a copy.
9. **Please explain the discrepancy:** The Experian credit report shows a balance of $10,831, but your CFPB response (October 26, 2022) stated the balance was $12,517.55. What accounts for this $1,686.55 difference?

---

## 5. Questions for Bureaus (Equifax, TransUnion, Experian)

To be asked in FCRA § 611 reinvestigation requests **(do not send until evidence packet is ready)** :

1. Please provide the complete furnisher-reported data for the UACC trade line, including all monthly status fields, payment history, and account condition codes.
2. On what date was this trade line first reported by UACC?
3. Has this trade line been previously disputed? If so, please provide:
   - Date of each dispute
   - Method of dispute submission
   - Reinvestigation results
   - Furnisher verification response
4. Please provide the Automated Consumer Dispute Verification (ACDV) records for any prior disputes.
5. Is this trade line currently coded as disputed by the consumer? If not, why not?
6. Please provide the name, address, and phone number of the data furnisher (UACC) as recorded in your files.
7. **For Equifax and TransUnion:** Please provide full credit reports. Only Experian reports are currently in evidence.

---

## 6. Questions for CFPB

To be asked when reopening Case No. 221011-9546852:

1. What was the disposition of Complaint No. 221011-9546852?
2. Did the CFPB take any enforcement or supervisory action against UACC as a result of this complaint?
3. What is the current status of the complaint?
4. Can the complaint be reopened or escalated?
5. Are there any other complaints against UACC on file that may indicate a pattern of behavior?
6. Please provide the complete case file, including UACC's full written response and any documents they submitted.