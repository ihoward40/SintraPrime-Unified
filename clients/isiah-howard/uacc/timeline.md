# Case Timeline — UACC/Vroom Auto Loan

**Case:** C-0001 | **Client:** Isiah Howard
**Evidence Rule:** A fact is not "confirmed" unless tied to a located file path, email export, credit report line, CFPB record, or source document. Unsourced memory goes in "Suspected / To Verify," not "Confirmed."
**Last Updated:** 2026-06-10

---

## Confirmed Dates

| Date | Event | Source File | Evidence ID |
|---|---|---|---|
| 2021-03-22 | Account opened (UACC auto loan, 2015 Ford Taurus) | `credit-reports/Experian.pdf` (p.27) | F3a |
| ~May 2021 | First late payment (30 days) | `credit-reports/Experian.pdf` (payment history) | F3a |
| ~Jun 2021 | Account 60 days late | `credit-reports/Experian.pdf` (payment history) | F3a |
| ~Jul 2021 | Account 90 days late | `credit-reports/Experian.pdf` (payment history) | F3a |
| ~Aug 2022 | Account charged off | `credit-reports/Experian.pdf` (payment history) | F3a |
| 2022-10-11 | CFPB Complaint filed (Case No. 221011-9546852) | `packages/credit_command_center/fixtures/client_0001.json` | F5 (reference only) |
| 2022-10-26 | CFPB Response received — UACC refuses to delete trade line | `packages/credit_command_center/fixtures/client_0001.json` | E1 (reference only) |
| UNKNOWN | FCRA dispute investigation completed — UACC stands by reporting | `credit-reports/Experian.pdf` (comments) | F3a |

---

## Unconfirmed / Suspected Dates

These are plausible but **not tied to any located source document**. They belong in "Suspected / To Verify":

| Date | Event | Why Not Confirmed |
|---|---|---|
| UNKNOWN | First payment due date | No contract located |
| UNKNOWN | First missed payment | No payment ledger |
| ~2021-2022 | Default date | No default notice or payment ledger |
| UNKNOWN | Repossession date | No repossession notice located |
| UNKNOWN | Charge-off date (exact) | Credit report shows Aug 2022 as month only — no specific date |
| UNKNOWN | Vehicle sale date | No sale notice or auction results |
| UNKNOWN | Deficiency balance calculated | No deficiency calculation |
| 2022-10-26 to Present | No documented follow-up activity | 3.5+ years of no action |

---

## Date Gaps (Critical)

| Gap | Impact | What Document Would Fill It |
|---|---|---|
| Contract date (2021-03-22) → Default date (UNKNOWN) | Cannot calculate cure period, default timeline, or SOL start date | Payment ledger from UACC |
| Default date (UNKNOWN) → Repossession date (UNKNOWN) | Cannot evaluate UCC § 9-611 notice timing | Notice of Repossession |
| Repossession date (UNKNOWN) → Sale date (UNKNOWN) | Cannot evaluate UCC § 9-612/9-613 commercial reasonableness | Notice of Sale / Disposition |
| Sale date (UNKNOWN) → Deficiency claim (UNKNOWN) | Cannot verify deficiency calculation or accounting | Post-sale accounting / auction results |
| CFPB response (2022-10-26) → Present (3.5+ years) | No follow-up activity documented | Bureau dispute records, CFPB case status |

---

## Key Correction from Phase 2B

The credit reports reveal that the account opened **March 22, 2021** (not March 15 as previously recorded in the fixture). The fixture date was off by 7 days. The credit report is the primary source and takes precedence.

The balance reported to Experian is **$10,831** (not $12,517.55 as previously recorded). This $1,686.55 discrepancy is significant and must be investigated.