# Violation Scorecard — UACC/Vroom Auto Loan

**Case:** C-0001 | **Client:** Isiah Howard
**Baseline:** 36/70 — WEAK
**Last Updated:** 2026-06-10
**Rule:** Score only from evidence in the manifest. No guessing. No assumed violations.

---

## Scoring Framework

Each category scored /10 based on:
- **Severity** of the apparent issue (weighted by evidence confidence)
- **Completeness** of the evidence packet for that category
- **Actionability** — whether a clear next step exists

**Scale:** 0-3 = 🔴 Critical gap · 4-6 = ⚠️ Needs work · 7-8 = ✅ Manageable · 9-10 = � Strong

---

## Category 1: Credit Reporting — 4/10 ⚠️

**What's wrong:** UACC auto loan trade line at $10,831 in charged-off status on Experian. Without full tri-merge reports (EQ, TU missing), contract, and payment ledger, cannot verify:
- Whether UACC is reporting accurate payment history under FCRA § 623(a)
- Whether bureaus conducted reasonable reinvestigation under FCRA § 611
- Whether the trade line is properly coded
- The $1,686.55 discrepancy between credit report ($10,831) and CFPB response ($12,517.55)

**Evidence:** F3a-c (3 Experian PDFs — UACC tradeline confirmed at $10,831, charged off, prior FCRA dispute completed). E2 (CFPB response reference only).

**Gaps:** No Equifax or TransUnion reports. No contract. No payment ledger. No reinvestigation responses.

**Potential violations (unconfirmed — require evidence):**
- FCRA § 623(a)(1)(A): Duty to provide accurate information
- FCRA § 623(a)(1)(B): Duty to correct and update
- FCRA § 611: Bureau reinvestigation duty
- FCRA § 623(b): Direct dispute rights with furnisher
- FCRA § 623(a)(5): Duty to notify bureaus of disputed status

**Score unchanged from Phase 2A.** The credit reports confirm the tradeline exists and was disputed — this was already known from the fixture. The balance discrepancy is a new lead, not a confirmed violation.

---

## Category 2: Collection Defense — 4/10 ⚠️

**What's wrong:** Account in charged-off status at $10,831 on Experian. Cannot determine:
- Whether a third-party collector was ever involved (triggers FDCPA)
- Whether debt validation was ever requested or provided
- Statute of limitations for auto loan deficiency in the relevant state
- Whether the balance includes improper fees, force-placed insurance, or interest

**Evidence:** F3a-c (Experian reports show charged-off status). E2 (UACC refuses to delete — reference only).

**Gaps:** No validation letter. No collector identity. No SOL analysis. No fee breakdown.

**Score unchanged.** No new repo-side or collection-side documents located.

---

## Category 3: Housing — 7/10 ✅

**Assessment:** No evidence of housing impact from this trade line. No mortgage application denial, rental rejection, or housing-related adverse action identified.

**Score unchanged.**

---

## Category 4: Employment — 8/10 ✅

**Assessment:** No evidence of employment impact. No adverse action flagged.

**Score unchanged.**

---

## Category 5: Documentation — 5/10 ⚠️

**What's wrong:** Of 34 identified documents, 4 are now captured (up from 1). 28 are missing, 1 is requested. The original contract, payment ledger, repossession documents, and dispute records are all absent.

**Key gaps:**
- No Retail Installment Contract → cannot verify balance
- No payment ledger → cannot verify default date or amount
- No repossession documents → cannot evaluate UCC Article 9 compliance
- No dispute records → cannot evaluate FCRA compliance

**Score unchanged.** The 3 new credit report PDFs add detail but do not close any structural gap. The case still cannot verify the balance, default, or repossession without the contract and payment ledger.

---

## Category 6: Evidence — 5/10 ⚠️

**What's wrong:** Evidence is scattered across Gmail, bureau portals, USPS records, and personal files. 4 documents now have confirmed file paths (up from 1). No OCR processing. No chain-of-custody tracking.

**Gaps:**
- No standardized file naming
- No OCR text extraction for search
- No chain-of-custody log
- Equifax and TransUnion reports still missing

**Score unchanged.** Having 3 more PDFs in the folder does not fix the systemic evidence organization gaps.

---

## Category 7: Follow-Up — 3/10 🔴

**What's wrong:** The CFPB complaint (Oct 2022) received a response (Oct 26, 2022) — UACC refused to delete. No follow-up action has been taken in over 3.5 years. No evidence of:
- Dispute letters to bureaus after UACC's refusal
- Escalation within CFPB
- State AG complaint
- SOL tracking
- Timeline management

**Score unchanged.** No follow-up actions have been taken.

---

## Scorecard Summary

| # | Category | Score | Status | Key Action |
|---|---|---|---|---|
| 1 | Credit Reporting | 4/10 | ⚠️ | Pull EQ and TU reports; investigate $1,686.55 discrepancy |
| 2 | Collection Defense | 4/10 | ⚠️ | Request validation / SOL analysis |
| 3 | Housing | 7/10 | ✅ | Monitor if housing application planned |
| 4 | Employment | 8/10 | ✅ | Monitor |
| 5 | Documentation | 5/10 | ⚠️ | Locate RIC, payment ledger, repo docs |
| 6 | Evidence | 5/10 | ⚠️ | Centralize files, OCR, chain-of-custody |
| 7 | Follow-Up | 3/10 | 🔴 | Reopen CFPB, send bureau disputes |
| | **Total** | **36/70** | **WEAK** | |

**Score unchanged from Phase 2A.** The 3 Experian credit report PDFs provide more detail but do not change any category score. The structural gaps remain: no contract, no payment ledger, no repo docs, no dispute records.

---

## Win Condition

Scorecard reaches **50+/70** (MODERATE) with:
- All 6 minimum readiness standards met
- At least 3 categories at 7+ with confirmed evidence
- Follow-Up category at 6+ (actions taken, not just planned)
- No category below 4/10

At that point, the evidence packet is sufficient to support targeted FCRA/FDCPA/UCC Article 9 dispute letters without guessing.