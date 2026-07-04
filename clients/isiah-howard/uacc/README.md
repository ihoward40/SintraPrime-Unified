# Client #0 — UACC/Vroom Auto Loan: Evidence Intake

**Case:** C-0001 | **Client:** Isiah Howard | **Tier:** Audit
**Account:** UACC (United Auto Credit Corporation) / Vroom — 2015 Ford Taurus
**Balance:** $10,831 (Experian) / $12,517.55 (CFPB response) — **$1,686.55 discrepancy under investigation**
**Scorecard Baseline:** 36/70 — WEAK
**Last Updated:** 2026-06-10

---

## Evidence Rule

> A fact is not "confirmed" unless tied to a located file path, email export, credit report line, CFPB record, or source document. Unsourced memory goes in "Suspected / To Verify," not "Confirmed."

---

## Purpose

This is an **evidence-first case file**. No outbound disputes, legal demands, or CFPB filings should be generated until the evidence packet reaches **minimum readiness** (see below).

The leverage in an auto deficiency/repo case lives in the paper trail — not in volume of letters. The money documents are:

- Retail Installment Contract
- Notice of Right to Cure (if applicable)
- Notice of Repossession (UCC § 9-611)
- Notice of Sale / Disposition (UCC § 9-612/9-613)
- Sale results / auction accounting (UCC § 9-615)
- Deficiency calculation
- Full payment ledger
- Credit bureau reporting history
- Prior dispute results

Until these are in the evidence folder, any dispute letter is a paper airplane into a corporate brick wall.

---

## Folder Structure

```
clients/isiah-howard/uacc/
├── intake/              # Raw intake documents (scans, downloads, forwards)
├── credit-reports/      # Bureau reports, tri-merge, monitoring
├── disputes/            # Dispute letters sent and responses received
├── correspondence/      # All communications with UACC, Vroom, CFPB, bureaus
├── evidence/            # Processed, OCR'd, cataloged evidence items
├── output/              # Deliverables: scorecards, reports, dispute packets
├── README.md            # This file
├── evidence_manifest.md # Complete document inventory
├── violation_scorecard.md # 7-category scorecard (current: 36/70)
├── timeline.md          # Confirmed dates only (source-attached)
├── issues_to_verify.md  # Confirmed facts vs suspected issues
├── money_docs_checklist.md # 9 repo money-document tracker
├── document_request_uacc.md # Draft request letter to UACC
├── cfpb_evidence_checklist.md # CFPB complaint evidence prep
└── next_actions.md      # Priority-ordered checklist
```

---

## Minimum Readiness Standard

Before any dispute is drafted, ALL of the following must be satisfied:

| # | Requirement | Status |
|---|---|---|
| 1 | Full tri-merge credit report obtained | ❌ (Experian only) |
| 2 | UACC tradeline details captured from all 3 bureaus | ❌ (Experian only) |
| 3 | Retail installment contract located or requested | ❌ |
| 4 | Repo/sale/deficiency documents located or requested | ❌ |
| 5 | Prior CFPB/bureau dispute records attached | ❌ |
| 6 | Timeline created from contract date through current reporting date | ✅ |

**Current readiness: 1/6 — NOT READY**

---

## Phase 2B Results (2026-06-10)

### Evidence Located
- **3 Experian credit report PDFs** copied into `credit-reports/`
- UACC tradeline confirmed at $10,831, charged off Aug 2022
- Prior FCRA dispute completed — UACC stands by reporting
- Account opened March 22, 2021 (corrected from fixture's March 15)

### Key Finding: Balance Discrepancy
The Experian reports show **$10,831** but the CFPB response shows **$12,517.55**. This $1,686.55 difference is a potential FCRA § 623(a) accuracy issue and must be investigated.

### What Was NOT Found
- No Retail Installment Contract
- No payment ledger
- No repossession or sale notices
- No Equifax or TransUnion reports
- No CFPB case file (reference only)
- No prior dispute letters or reinvestigation responses

### Scorecard
**36/70 — WEAK (unchanged).** The credit reports add detail but do not close any structural gap. Score stays frozen until actual money documents land.

---

## Rules of Engagement

1. **Evidence first.** Every document goes through intake → catalog → OCR before it enters the analysis pipeline.
2. **Score second.** The scorecard is updated after each evidence batch, not before.
3. **Letters third.** No dispute, demand, or filing leaves this folder until the scorecard reflects a complete evidence picture.
4. **No guessing.** If a document doesn't exist, note it as "requested" — don't fabricate or assume its contents.
5. **Chain of custody.** Every evidence item tracks its source, date obtained, and any actions taken on it.
6. **Evidence rule.** A fact is not "confirmed" unless tied to a located source document. Unsourced memory goes in "Suspected / To Verify."