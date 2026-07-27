# GBC-1 — Ratification Checklist

## Pre-PR Checks

- [x] Dedicated governance branch created.
- [x] Payment branch untouched.
- [x] `git status --porcelain=v1` shows only intended governance files.
- [x] `GOVERNANCE_CHARTER.md` authored.
- [x] `GBC-1-CONTRACT.md` authored.
- [x] BKGC contains Constitutional Supremacy Clause.
- [x] BKGC contains Version Policy table.
- [x] BKGC contains Interoperability Charter.
- [x] Every section marked `(Normative)` or `(Informative)` in all volumes.
- [x] Requirement identifiers assigned across all volumes.
- [x] BKC designated as canonical semantic authority.
- [x] Governance Maturity Levels (G0–G7) defined.
- [x] CDR-0001 through CDR-0005 authored.
- [x] BGC expanded to 10 cases across legal, AI, engineering, governance categories.
- [x] Governance validation audit shows no critical findings.
- [x] `GBC-1-STATUS.md` reads READY FOR RATIFICATION.
- [x] Ratification package complete: Completion Report, Evidence Log, Manifest, Changelog, Checklist.

## Approval Required

- [ ] Governance Steward review.
- [ ] Ratification authority signature.
- [ ] PR opened from `governance/gbc-1-blackstone-library` to `main`.
- [ ] CI passes (no product code changes expected; markdown-only PR).
- [ ] PR merged.

## Post-Merge

- [ ] Tag `governance-baseline-1`.
- [ ] Update project documentation child DOX index to include `governance/blackstone/AGENTS.md`.
- [ ] Open GBC-2 planning item for validator script and agent certification.
