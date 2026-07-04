# Matter C-0001: UACC/Vroom Auto Loan

**Matter ID:** C-0001
**Category:** Consumer Law — Credit Reporting / Auto Deficiency
**Primary Party:** Isiah Howard
**Opposing Party:** United Auto Credit Corporation (UACC) / Vroom
**Account:** 2015 Ford Taurus — Auto Loan
**Balance Claimed:** $12,517.55 (collections, all 3 bureaus)
**Last Updated:** 2026-06-10

---

## What We Know (Confirmed)

| Fact | Source | Evidence ID |
|------|--------|-------------|
| Account opened March 15, 2021 | `packages/credit_command_center/fixtures/client_0001.json` | F2 |
| CFPB Complaint filed October 11, 2022 (Case #221011-9546852) | `packages/credit_command_center/fixtures/client_0001.json` | F5 |
| UACC responded to CFPB — refuses to delete trade line | `packages/credit_command_center/fixtures/client_0001.json` | E1 |
| Trade line appears on all 3 bureaus at $12,517.55 in collections | Credit report references (no PDFs in evidence) | F1-F3 |

---

## What We Do NOT Know (Marked Clearly)

| Question | Why Unknown | Priority to Resolve |
|----------|-------------|-------------------|
| What does the full credit report actually say? | No tri-merge report obtained yet | 🔴 P1 |
| What was the original contract amount and terms? | No Retail Installment Contract in evidence | 🔴 P1 |
| When was the first missed payment? | No payment ledger | 🔴 P1 |
| Was a repossession notice sent? | No notice in evidence | 🔴 P1 |
| Was a sale notice sent? | No notice in evidence | 🔴 P1 |
| What was the vehicle sold for at auction? | No sale results | 🔴 P1 |
| Is the $12,517.55 balance accurate? | No deficiency calculation | 🔴 P1 |
| Were prior disputes sent to bureaus? | No dispute records in evidence | 🟡 P2 |
| What is the full CFPB case file? | Not downloaded from portal | 🟡 P2 |
| Is there a 1099-C for the charge-off? | Not in evidence | 🟡 P2 |

---

## Current Status

| Metric | Value |
|--------|-------|
| **Scorecard** | 36/70 — WEAK |
| **Readiness** | 0/6 — NOT READY |
| **Evidence Items** | 3 confirmed (all from fixture JSON, no PDFs) |
| **Date Gaps** | 5 critical gaps identified |

**Bottom line:** This matter is in the evidence-gathering phase. No disputes, demands, or filings should be drafted until the evidence packet is complete.

---

## Related Files

| File | Purpose |
|------|---------|
| `evidence_needed.md` | Complete list of missing evidence |
| `next_actions.md` | Priority-ordered action checklist |
| `risk_notes.md` | Risk assessment and readiness analysis |
| `clients/isiah-howard/uacc/README.md` | Original case intake (legacy location) |
| `clients/isiah-howard/uacc/timeline.md` | Case timeline |
| `clients/isiah-howard/uacc/violation_scorecard.md` | Current scorecard |
| `clients/isiah-howard/uacc/next_actions.md` | Original next actions |

---

**Matter opened:** 2026-06-10 (Think Tank Day 1)
**Next review:** After P1 actions are completed