# P0 Active Surface Scrub Receipt

## Status
:green_circle: **Approved and complete** — active M3 surface only.

## Approved Scope
| File | Result |
|------|--------|
| `web/src/store/appStore.ts` | Scrubbed |
| `web/src/store/legalStore.ts` | Scrubbed |
| `web/src/pages/DocumentVault.tsx` | Scrubbed |
| `web/src/pages/LegalHub.tsx` | Scrubbed |
| `web/src/pages/EntityGovernance.tsx` | Scrubbed |
| `web/src/pages/TrustLaw.tsx` | Scrubbed |
| `docs/PHASE_26PLUS_PITCH_DECK.md` | Scrubbed |
| `docs/plans/M3_LOGIN_PAGE_PLAN.md` | Scrubbed |

## What Was Replaced
| Original | Replacement |
|----------|-------------|
| `Marcus A. Sintra` | Context-appropriate demo placeholders: `Demo Attorney`, `Demo Principal`, `J. Doe, Esq.`, `Demo Plaintiff`, `Demo Settlor`, `Demo Debtor` |
| `Sintra Family Trust` | `Sample Family Trust` |
| `SintraPrime Law & Financial Group` and other `Sintra`-prefixed demo entities | `Sample Law & Financial Group`, `Sample Holdings LLC`, `Sample Consulting LLC`, `Sample Real Estate Corp`, `Sample Charitable Foundation`, `Sample Family Irrevocable Trust` |
| `isiahh@ikesolutions.org \| +190****4234` | `contact@example.com \| +1**********` |

## Verification
- **Active-path grep scan**: PASS. Zero matches in the approved target paths for:
  - `Marcus A. Sintra`
  - `Sintra Family Trust`
  - `Isiah Howard`
  - `howardisiah`
  - `isiahh@ikesolutions`
  - `92-6080121`
  - `87-1798434`
  - `908-365-4234`
  - `07114`
- **No real Isiah Howard PII** was found in the active `portal/` or `web/src/` surface.

## Churn / Line-Ending Explanation
The PR diff reports approximately 1,531 additions and 1,475 deletions across 9 files. This is **not** from large code changes. It is an artifact of how the patch tool applied replacements:

- `docs/PHASE_26PLUS_PITCH_DECK.md`: originally LF; was briefly converted to CRLF, then restored to LF with only the contact-line replacement. Final diff: 1 line changed.
- The `.ts`/`.tsx` files: already CRLF in the repo. The patch tool replaced contiguous blocks around each changed string, causing git to count those whole blocks as removed and re-added even though most lines are identical. The actual semantic changes are small mock-name substitutions.
- `git diff --check` reports "trailing whitespace" on CRLF files because Git interprets the `\r` character as trailing whitespace when diffing against an LF baseline. This is a line-ending artifact, not actual trailing spaces. The `lint` CI check passes, confirming no real whitespace lint violations.

## Known Limitations (not caused by this scrub)
- `npm run type-check` fails due to pre-existing baseline TypeScript errors in `src/api/caselaw.ts`, `src/components/governance/EntityManager.tsx`, `src/components/layout/ThemeToggle.tsx`, `src/hooks/useAPI.ts`, `src/pages/DocumentVault.tsx`, and `src/pages/Settings.tsx`.
- `npm run build` fails for the same pre-existing baseline TypeScript errors.
- `npm run lint` is unavailable locally because `web/` has no ESLint configuration file; however, the GitHub Actions `lint` job passes.
- Remaining matches for `Isiah Howard` exist in docs outside the approved scope (`docs/IKE_HERMES_OPERATING_MANUAL.md`, `docs/governance/*`, `docs/planning/M3_DOCUMENT_VAULT_ADR.md`). These were intentionally not modified in this pass.

## Deferred Issues
- **P0B — Legacy / Docs Public Repo Scrub**: full historical repo and governance document scrub.
- **TypeScript baseline repair**: unrelated pre-existing type errors.
- **ESLint config restoration/addition**: re-enable local linting in `web/`.

## Commit
- Branch: `chore/p0-active-surface-scrub`
- Commit: `a45b378`
- Message: `chore: scrub active M3 surface demo identity data`

## Scope Boundary
This receipt covers only the active M3 frontend surface. It does **not** claim a full-repo scrub is complete, and no unrelated TypeScript repairs were performed in this branch.
