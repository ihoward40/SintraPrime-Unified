# Evidence Manifest — C-0001 UACC/Vroom Auto Loan

**Matter:** C-0001 | UACC/Vroom Auto Loan — 2015 Ford Taurus
**Last Updated:** 2026-06-10
**Rule:** Only list documents that have been located and verified. Mark all gaps clearly.

---

## Evidence Inventory

| Exhibit ID | File Name | Source | Date Found | Evidence Category | What It May Prove | Status | Notes |
|------------|-----------|--------|------------|-------------------|-------------------|--------|-------|
| C0001-EX001 | `client_0001.json` (fixture) | `packages/credit_command_center/fixtures/client_0001.json` | Pre-existing | Other | Account opened 2021-03-15, CFPB complaint filed 2022-10-11, UACC response 2022-10-26 | 🟡 REFERENCE ONLY | Structured data — no original documents attached |
| C0001-EX002 | `uacc_vroom_evidence_template.json` | `intake_templates/uacc_vroom_evidence_template.json` | Pre-existing | Other | Evidence intake template for UACC matter | 🟡 TEMPLATE ONLY | Blank template — no data filled in |
| C0001-EX003 | `uacc_vroom_evidence_template.json` | `clients/isiah-howard/uacc/intake/uacc_vroom_evidence_template.json` | Pre-existing | Other | Duplicate of intake template | 🟡 TEMPLATE ONLY | Blank template — no data filled in |
| C0001-EX004 | `howard_template_agent.py` | `agents/howard_template_agent.py` | Pre-existing | Other | Agent configuration referencing UACC case | 🟡 REFERENCE ONLY | Contains case metadata, no evidence documents |
| C0001-EX005 | `Experian.pdf` | `evidence/credit-reports/Experian.pdf` | 2026-06-10 | Credit Reports | Experian credit report Jun 6, 2026 — UACC tradeline confirmed: $10,831, charged off, FCRA dispute completed | ✅ REVIEWED | FICO 534 — UACC tradeline found on page 27 |
| C0001-EX006 | `Experian 5-6-26.pdf` | `evidence/credit-reports/Experian 5-6-26.pdf` | 2026-06-10 | Credit Reports | Experian credit report May 6, 2026 — UACC tradeline: $10,831, charged off | ✅ REVIEWED | FICO 548 — UACC tradeline on page 28 |
| C0001-EX007 | `ExperianMay17.pdf` | `evidence/credit-reports/ExperianMay17.pdf` | 2026-06-10 | Credit Reports | Experian credit report May 17, 2026 — UACC tradeline: $10,831, charged off | ✅ REVIEWED | UACC tradeline on page 28 |

---

## Evidence Gaps (Documents NOT Found)

| # | Document Needed | Why It Matters | Where to Search |
|---|----------------|---------------|-----------------|
| 1 | **Retail Installment Contract** | Original loan terms, APR, total financed | Vroom account online, email archives, personal files |
| 2 | **Payment Ledger** | Default date, payment history, fees | Written request to UACC |
| 3 | **Notice of Repossession (UCC § 9-611)** | Whether proper notice was given | Physical mail, email, USPS Informed Delivery |
| 4 | **Notice of Sale / Disposition (UCC § 9-612/9-613)** | Whether proper sale notice was given | Physical mail, email |
| 5 | **Sale Results / Auction Accounting (UCC § 9-615)** | Whether deficiency balance is accurate | Written request to UACC |
| 6 | **Deficiency Calculation** | Verifies $12,517.55 balance | Written request to UACC |
| 7 | **Full CFPB Case File (#221011-9546852)** | Prior complaint details and UACC's response | CFPB portal download |
| 8 | **Prior Bureau Dispute Letters** | FCRA § 611 reinvestigation history | Personal files, certified mail receipts |
| 9 | **1099-C (if issued)** | Charge-off date and tax implications | IRS records, UACC correspondence |
| 10 | **Vroom Purchase Agreement** | Original purchase price and financing | Vroom account online |
| 11 | **Assignment Chain (Vroom → UACC)** | Whether UACC has standing | UACC records request |
| 12 | **Bank Statements (payment period)** | Cross-reference payment history | Online banking archives |

---

## Evidence Summary

| Category | Located | Not Located | Status |
|----------|---------|-------------|--------|
| Contracts & Loan Terms | 0 | 2 | 🔴 Critical gap |
| Credit Reports | 3 PDFs (not yet reviewed) | 0 | 🟡 Needs review |
| Repossession & Sale | 0 | 3 | 🔴 Critical gap |
| CFPB Records | 0 (reference only) | 1 | 🔴 Critical gap |
| Correspondence | 0 | 2 | 🔴 Critical gap |
| Payment History | 0 | 2 | 🔴 Critical gap |
| Dispute History | 0 | 1 | 🔴 Critical gap |
| Templates/References | 4 | 0 | 🟡 Not evidence |

| **Total evidence items located:** 7 (4 reference files + 3 reviewed credit report PDFs)
**Total evidence items needed:** 19
**Verified evidence (reviewed and cataloged):** 3 credit report PDFs

---

**Last updated:** 2026-06-10
**Next action:** Review credit report PDFs for additional issues (collection accounts, dispute history, personal information) | Obtain Equifax and TransUnion reports