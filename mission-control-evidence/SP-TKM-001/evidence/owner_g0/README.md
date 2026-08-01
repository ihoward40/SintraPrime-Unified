# Owner G-0 Evidence Folder

Mission: SP-TKM-001
Gate: G-0 — Account and Eligibility Audit
Owner: Isiah Tarik Howard
Prepared By: Hermes

## Purpose

This folder stores privacy-minimized owner-provided evidence used to verify the TikTok account and monetization eligibility for SP-TKM-001.

## Rules

1. Do not store passwords, recovery codes, tokens, session cookies, full tax IDs, full payment account numbers, unredacted identity documents, or home addresses.
2. Original screenshots must not be altered. Store redacted working copies separately with a reference back to the original.
3. Every submitted screenshot receives an Evidence ID and is recorded in `EVIDENCE_INDEX.json`.
4. Acceptance statuses are: ACCEPTED, ACCEPTED_WITH_LIMITATIONS, REDACTION_REQUIRED, INSUFFICIENT, REJECTED.
5. If a feature does not appear in a screenshot, record `NOT SHOWN IN PROVIDED EVIDENCE`. Do not record `INELIGIBLE` automatically.
6. Identity, tax, and payout setup may be recorded only as COMPLETE, INCOMPLETE, NOT REQUIRED, or UNVERIFIED.

## Folder Layout

```
evidence/owner_g0/
├── README.md
├── EVIDENCE_INDEX.json
├── REDACTION_CHECKLIST.md
├── G0_FINDINGS.md
├── original/          # unmodified owner screenshots
└── redacted/          # working copies with sensitive data covered
```

## Submission Process

1. Owner uploads redacted screenshots to `original/` or shares them during a live owner-guided inspection.
2. Hermes assigns an Evidence ID and records metadata in `EVIDENCE_INDEX.json`.
3. Sensitive-data review is performed.
4. If accepted, the verified fact is transferred to `G0_FINDINGS.md` and `SP-TKM-001_ACCOUNT_ELIGIBILITY_AUDIT.md`.
5. If the screenshot is insufficient or needs more redaction, owner is asked to resubmit.
