# P0B Legacy / Docs Public Repo Scrub Receipt

## Status
:green_circle: **Approved and complete** — legacy/docs surface only, targeted scope.

## Scope
| File | Result |
|------|--------|
| `docs/PHASE_26PLUS_DEMO_SCRIPT.md` | Scrubbed |
| `docs/PHASE_26PLUS_DEMO_SCENARIO.md` | Scrubbed |
| `docs/CLAIMS.md` | Scrubbed |
| `docs/api/api_index.md` | Scrubbed |
| `docs/PHASE_26PLUS_PITCH_DECK.md` | Already neutral from PR #156, no change |
| `docs/governance/VR-001-S5-GOVERNANCE-DECISION.md` | Governance — preserved |
| `docs/governance/GI-B-2026-001-CLOSURE.md` | Governance — preserved |
| `docs/planning/M3_DOCUMENT_VAULT_ADR.md` | Governance — preserved |

## What Was Scrubbed
| Original | Replacement |
|----------|-------------|
| `admin@sintraprime.dev / demo123` | `admin@example.dev / DemoPass123!` |
| `jane@acmecorp.com` | `client@example.dev` |
| `Jane Smith` / `Rick Smith` / `Alex` / `Sam` | `Alex Taylor` / `Jordan Taylor` / `Morgan Taylor` / `Riley Taylor` |
| `123 Oak St, CA` | `123 Sample St, CA` |
| `Fidelity account` | `Sample brokerage account` |
| `Bank of America checking` | `Sample bank checking` |
| `Jane Smith` (Claims demo) | `Demo Grantor` |
| `Smith Family Living Trust` / `John Smith` / `Jane Smith` / `Alice Smith` | `Sample Family Living Trust` / `Demo Grantor` / `Demo Trustee` / `Demo Beneficiary` |

## What Was Preserved (Governance Signatures)
The following documents contain `Isiah Howard` as Project Owner, Decision Authority, or approval signature. They were **intentionally preserved** because they document decision authority and approval history. These are not demo/mock identifiers.

| File | Line | Context |
|------|------|---------|
| `docs/IKE_HERMES_OPERATING_MANUAL.md` | 3, 22 | Owner; operator-role approval authority |
| `docs/governance/VR-001-S5-GOVERNANCE-DECISION.md` | 47, 55 | Decision Authority; Project Owner acceptance signature |
| `docs/governance/GI-B-2026-001-CLOSURE.md` | 6, 83 | Resolved By / reviewed by; Project Owner acceptance signature |
| `docs/planning/M3_DOCUMENT_VAULT_ADR.md` | 179 | Project Owner approval |

## Verification
Grep scan for public personal identifiers in `docs/` after scrub:
- Emails: only neutral `example.com` / `example.dev` addresses remain.
- Phone numbers: none found.
- SSN/EIN patterns: none found.
- Address ZIP `07114`: none found.
- `Marcus A. Sintra` / `Sintra Family Trust`: none found in docs.
- `908-365-4234`: none found.
- `howardisiah`: none found.

Remaining `Isiah Howard` matches are confined to the four governance/operating documents listed above and are preserved under the governance signature policy.

## Known Limitations
- Public app URLs (`sintraprime-unified-*.run.app/health`) remain in governance docs. These are infrastructure endpoints, not personal identifiers.
- This P0B pass does not touch active M3 files already covered by PR #156.
- No TypeScript, ESLint, dependency, or feature changes were made in this branch.

## Follow-Up Issue
If privacy risk remains for the preserved governance signatures, create/update:
- **Private Governance Archive / Public Redaction Policy** — decide whether to move governance docs to a private archive or publish redacted versions with a generic "Project Owner" placeholder while retaining signed originals in a non-public location.

## Commit
- Branch: `chore/p0b-legacy-docs-scrub`
- Files changed: `docs/PHASE_26PLUS_DEMO_SCRIPT.md`, `docs/PHASE_26PLUS_DEMO_SCENARIO.md`
