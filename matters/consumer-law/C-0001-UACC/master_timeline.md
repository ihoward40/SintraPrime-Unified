# Master Timeline — C-0001 UACC/Vroom Auto Loan

**Matter:** C-0001 | UACC/Vroom Auto Loan — 2015 Ford Taurus
**Last Updated:** 2026-06-10
**Rule:** A fact is not "confirmed" unless tied to a located source document. Unsourced information goes in "Suspected / To Verify."

---

## Confirmed Dates

| Date | Event | Source Document | Evidence Status | Notes |
|------|-------|----------------|-----------------|-------|
| 2021-03-22 | Account opened (UACC auto loan, 2015 Ford Taurus) | `evidence/credit-reports/Experian.pdf` (p.27) | ✅ CONFIRMED | Date differs from fixture (Mar 15 vs Mar 22) — credit report is primary source |
| UNKNOWN | First late payment (30 days) | `evidence/credit-reports/Experian.pdf` (payment history) | ✅ CONFIRMED | Payment history shows 30-day late in May 2021 |
| UNKNOWN | Account 60 days late | `evidence/credit-reports/Experian.pdf` (payment history) | ✅ CONFIRMED | Payment history shows 60-day late in Jun 2021 |
| UNKNOWN | Account 90 days late | `evidence/credit-reports/Experian.pdf` (payment history) | ✅ CONFIRMED | Payment history shows 90-day late in Jul 2021 |
| ~Aug 2022 | Account charged off | `evidence/credit-reports/Experian.pdf` (payment history) | ✅ CONFIRMED | Payment history shows CO (charge-off) status from Aug 2022 |
| 2022-10-11 | CFPB Complaint filed (Case No. 221011-9546852) | `packages/credit_command_center/fixtures/client_0001.json` | 🟡 REFERENCE ONLY | Full case file not downloaded |
| 2022-10-26 | CFPB Response received — UACC refuses to delete trade line | `packages/credit_command_center/fixtures/client_0001.json` | 🟡 REFERENCE ONLY | UACC stands by reporting |
| UNKNOWN | FCRA dispute investigation completed — UACC stands by reporting | `evidence/credit-reports/Experian.pdf` (comments) | ✅ CONFIRMED | "Completed investigation of FCRA dispute - consumer disagrees" on all 3 reports |

---

## Unconfirmed / Suspected Dates

| Date | Event | Evidence Status | Notes |
|------|-------|-----------------|-------|
| UNKNOWN | First payment due date | EVIDENCE GAP | No contract located |
| UNKNOWN | First missed payment | EVIDENCE GAP | No payment ledger |
| ~2021-2022 | Default date | EVIDENCE GAP | No default notice or payment ledger |
| UNKNOWN | Repossession date | EVIDENCE GAP | No repossession notice located |
| UNKNOWN | Charge-off date | EVIDENCE GAP | No charge-off notice or 1099-C |
| UNKNOWN | Vehicle sale date | EVIDENCE GAP | No sale notice or auction results |
| UNKNOWN | Deficiency balance calculated | EVIDENCE GAP | No deficiency calculation |
| 2022-10-26 to Present | No documented follow-up activity | EVIDENCE GAP | 3.5+ years of no action |

---

## Date Gaps (Critical)

| Gap | Impact | What Document Would Fill It |
|-----|--------|----------------------------|
| Contract date (2021-03-15) → Default date (UNKNOWN) | Cannot calculate cure period, default timeline, or SOL start date | Payment ledger from UACC |
| Default date (UNKNOWN) → Repossession date (UNKNOWN) | Cannot evaluate UCC § 9-611 notice timing | Notice of Repossession |
| Repossession date (UNKNOWN) → Sale date (UNKNOWN) | Cannot evaluate UCC § 9-612/9-613 commercial reasonableness | Notice of Sale / Disposition |
| Sale date (UNKNOWN) → Deficiency claim (UNKNOWN) | Cannot verify deficiency calculation or accounting | Post-sale accounting / auction results |
| CFPB response (2022-10-26) → Present (3.5+ years) | No follow-up activity documented | Bureau dispute records, CFPB case status |

---

## Timeline Summary

| Period | Duration | Events | Evidence Coverage |
|--------|----------|--------|-------------------|
| 2021-03-15 to ~2021-2022 | ~1-2 years | Account active, payments made (presumed) | 🔴 No evidence |
| ~2021-2022 to UNKNOWN | Unknown | Default, repossession, sale | 🔴 No evidence |
| 2022-10-11 to 2022-10-26 | 15 days | CFPB complaint filed and responded | 🟡 Reference only |
| 2022-10-26 to Present | 3.5+ years | No documented activity | 🔴 No evidence |

---

**Last updated:** 2026-06-10
**Next action:** Obtain credit reports and search email for contract and notices