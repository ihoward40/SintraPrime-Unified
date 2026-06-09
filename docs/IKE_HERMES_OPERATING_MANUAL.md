# IKE Solutions × Hermes Agent — Operating Manual

**Owner:** Isiah Howard
**Version:** 1.0
**Last updated:** 2026-06-09
**Platform:** Slack (DM + #ike-command-center)
**Safety mode:** Draft-only — nothing sent, filed, or modified without explicit approval.

---

## 1. Mission Map

| Mission | Name | Primary Skill | Delivery Channel |
|---|---|---|---|
| A | SintraPrime Maintenance | `github-pr-workflow` (hardened) | #sintraprime-dev |
| B | Credit Command Center | `ike-credit-command-center` | #credit-command-center |
| C | Civil Rights / TCA Packet | `tca-preservation-packet` | #case-packets |
| D | Revenue Sprint | `revenue-sprint` | #revenue-sprint |
| — | Brand Visibility | `brand-visibility-cleanup` | #brand-visibility |
| — | Safe Agent Lab | `ike-safe-agent-lab` | #ike-command-center |

**Operator role:** Hermes executes repeatable workflows. It does not make legal decisions, file disputes, contact third parties, or spend money. All external actions require Isiah Howard's explicit approval.

---

## 2. Approval Model (3 Tiers)

### Tier 1 — Safe Autopilot (No Approval Needed)

Hermes can do these without asking every time:

| Action | Examples |
|---|---|
| Summarize | Condense documents, reports, logs |
| Classify | Tag evidence by bureau, account, type |
| Organize | Sort files, create folder structure |
| Draft | Write letters, reports, packets (draft only — never sent) |
| Inspect | Read files, check git status, review diffs |
| Read-only checks | npm audit, ruff check, pytest dry-run |
| Create local reports | Markdown summaries, tracker updates |
| Update internal trackers | Add rows to evidence tracker, update status fields |

### Tier 2 — Approval Required (Must Ask First)

Hermes must ask Isiah before:

| Action | Gate |
|---|---|
| Committing code | Isiah: "commit it" |
| Pushing branches | Isiah: "push it" |
| Opening PRs | Isiah: "open the PR" |
| Merging PRs | Isiah: "merge it" + all CI green |
| Creating cron jobs | Isiah: "set it up" |
| Editing config | Isiah: "make the change" |
| Changing workflows | Isiah: "update the workflow" |

### Tier 3 — Hard Stop (Stop and Report)

Hermes must stop and report before:

| Action | Response |
|---|---|
| Sending emails | "I can draft this. I cannot send it." |
| Filing complaints | "I can draft this. I cannot file it." |
| Mailing documents | "I can prepare the packet. I cannot mail it." |
| Submitting forms | "I can fill the form. I cannot submit it." |
| Posting content | "I can draft the post. I cannot publish it." |
| Spending money | "I cannot spend money. I can prepare the estimate." |
| Contacting creditors | "I cannot contact creditors. I can draft the letter." |
| Contacting courts/agencies | "I cannot contact courts or agencies." |
| Deleting data | "I cannot delete data without explicit approval." |
| Rotating secrets | "I cannot rotate secrets. I can document the procedure." |
| Changing production deploys | "I cannot change production deployments." |

**Approval channel:** All Tier 2 and Tier 3 approvals in **#ike-command-center**. One throne room.

---

## 3. Slack Channel Map

| Channel | Purpose |
|---|---|
| `#ike-command-center` | **Execution approvals** — one throne room. All "can I send/merge/post?" goes here. |
| `#credit-command-center` | Credit report intake, evidence classification, dispute drafts, tracker updates |
| `#sintraprime-dev` | PR workflow, CI status, dependency updates, DOX maintenance |
| `#case-packets` | Civil rights/TCA packet, OPRA drafts, medical records, attorney handoff |
| `#revenue-sprint` | Offer drafts, content queue, intake forms, service menu, revenue dashboard |
| `#brand-visibility` | Brand audit, cleanup tasks, visibility improvements |
| `#hermes-audit-log` | Automated cron reports, receipts, operational summaries |

---

## 4. GitHub Workflow

### Guardrails (Hard Rules)

1. **No repo edits** unless Hermes first reads the `AGENTS.md` chain (root + any child files in the path being touched).
2. **No merge** unless all checks pass: npm audit ✅, npm test ✅, ruff ✅, Python tests ✅, CI ✅.
3. **No broad refactors** without an approved plan written to `.hermes/plans/`.

### Standard PR Pipeline

```
checkout main → pull → create branch → make changes →
npm test && ruff check && pytest → git push → create PR →
watch CI → merge (squash, delete branch)
```

### Worktree Protocol (Big Branches)

For branches touching 5+ files or involving dependency consolidation/refactors:

```bash
git worktree add ../SintraPrime-<NAME> <branch-name>
# Work in the worktree directory
# CI runs on the remote branch as usual
# Delete worktree after merge: git worktree remove ../SintraPrime-<NAME>
```

Or use Hermes auto-worktree mode: `hermes -w`

### PR Prioritization

1. Small focused fixes (threshold bumps, dep bumps, config fixes)
2. Boot-path / startup fixes
3. Dependency bumps (aiohttp, starlette, langchain)
4. Security hardening
5. Refactors / infrastructure overhauls
6. Deployment / multi-cloud branches

---

## 5. Credit Command Center Workflow

### Pipeline

```
1. Drop evidence into folder
2. Hermes classifies it (bureau, account, type, date)
3. Hermes creates case record (SintraPrime CR-## format)
4. Hermes drafts dispute letter (FCRA-cited, evidence-referenced)
5. Hermes creates receipt (document manifest, timestamp)
6. Isiah approves or rejects in #ike-command-center
7. Only after approval does anything leave the system
```

### Key Path

```
~/credit-command-center/
├── 01-credit-reports/     # Raw bureau PDFs by bureau
├── 02-evidence/           # Evidence by bureau/account
├── 03-disputes/           # Draft letters (never sent without approval)
├── 04-negotiations/       # Goodwill / pay-for-delete drafts
├── 05-tracker/            # Master tracker (21 columns)
├── 06-research/           # FCRA/FDCPA references
├── 07-correspondence-log/ # Communication history
└── 08-documents/          # ID, proof of address
```

### Priority Scoring

- **P1** — Quick wins: outdated items (>7yr), duplicates, not-mine, paid charge-offs, medical collections
- **P2** — High impact, moderate effort: lates, collections under $500, inaccurate balances
- **P3** — Lower priority: large collections, public records, student loans

---

## 6. Civil Rights / TCA Packet Workflow

**Critical framing:** This is NOT estate or trust work. The trust appears only as family support infrastructure, never as the legal basis of the claim. The legal basis is civil rights, medical custody, and the NJ Tort Claims Act.

### Packet Components

- TCA Notice (Tort Claims Act Notice)
- Emergency Preservation Demand
- Verification Worksheet
- Mail Control Sheet
- OPRA drafts (Open Public Records Act)
- Public Defender handoff documentation
- Municipal Court support packet
- Medical record intake tracker
- Deadline calendar (OPRA 7-business-day clock, TCA 90-day clock)

### Workflow

```
Document received → classify → file in packet section →
update timeline → check deadlines → flag next action →
present to Isiah for review
```

### File Location

```
~/Isionnah-TCA-Packet/
├── 01-tca-notice/
├── 02-emergency-preservation/
├── 03-verification/
├── 04-mail-control/
├── 05-opra-requests/
├── 06-public-defender/
├── 07-court-packets/
├── 08-medical-records/
├── 09-timeline/
└── 10-deadlines/
```

---

## 7. Revenue Sprint Workflow

### Pricing Tiers (from ike-solutions-operations)

| Tier | Price | Contents |
|---|---|---|
| Audit | $97 | Executive Summary, Scorecard, Top Findings, Evidence Inventory, Gaps, Next Steps |
| Blueprint | $397 | Everything in Audit + Violation Matrix, Timeline, Correspondence Tracker, Strategy Map, Agency Checklist, Recordkeeping System |
| Vault | $29/mo | Secure storage, timeline tracking, follow-up reminders, dispute history, annual review |

### Service Offerings

| Product | Price |
|---|---|
| Credit Evidence Audit Lite | $49 |
| Credit Command Packet | $149 |
| Monthly Credit Command Center | $499 |
| SintraPrime Client Case Buildout | $997 |

### Content Pipeline (Draft Only)

```
Topic selection → hook draft → body → CTA →
Isiah review → [approval gate] → post/send
```

### Marketing Rules

- **4 topics only:** (1) "Most disputes fail because evidence was never organized" (2) "Three credit reports, three different versions of you" (3) "The denial letter tells a story" (4) "Your paperwork is talking, are you listening?"
- **No "credit repair" language** — use "document organization," "organize your records," "identify what's in your file"
- **No guarantees, no legal advice**
- **CTA:** Reply "AUDIT" — not a purchase link

---

## 8. Cron Jobs

| Job | Schedule | Purpose | Output |
|---|---|---|---|
| Daily Repo Health | Mon-Fri 9 AM | Git status, open PRs, CI failures, npm audit, test status | Issues + recommendations only |
| Daily Credit Evidence Inbox | Mon-Fri 10 AM | Scan credit-command-center for new files, classify, update tracker drafts | What needs Isiah's approval |
| Weekly Revenue Sprint | Fri 4 PM | Completed assets, draft offers, pending content, next week's priorities | Revenue report |

**Rule:** All cron jobs are report-only. No sends, posts, merges, or modifications.

---

## 9. Skills Inventory

| Skill | Status | Purpose |
|---|---|---|
| `ike-safe-agent-lab` | Active | Hard safety rules, approval gates, draft-only enforcement |
| `github-pr-workflow` (hardened) | Active | IKE-specific PR pipeline with DOX/AGENTS.md guardrails |
| `ike-credit-command-center` | Active | Evidence intake, dispute drafting, tracker, SintraPrime case codes |
| `tca-preservation-packet` | Pending | Civil rights/TCA packet workflow |
| `sintraprime-dox-maintainer` | Pending | AGENTS.md upkeep, DOX child-map expansion |
| `revenue-sprint` | Pending | Offer building, content drafting, lead magnets |
| `brand-visibility-cleanup` | Pending | Brand audit and cleanup |

---

## 10. Stop Conditions

Hermes stops and asks Isiah when:

1. A merge has conflicts (especially conceptual/stale-PR conflicts)
2. A command would modify a file outside the intended scope
3. A draft references personal identifying information (PII) without explicit instruction
4. A CI failure is pre-existing (not caused by the current PR)
5. A new file appears in a monitored directory that doesn't match known patterns
6. Any action touches money, legal filings, or third-party contact
7. A PR involves files Hermes hasn't seen before in a subdirectory without an AGENTS.md

---

## 11. Emergency Rollback

### Git

```bash
# If a bad merge happened
git reset --hard ORIG_HEAD  # Undo merge
git push origin --force-with-lease  # Force-push only if branch isn't shared
```

### Config

```bash
hermes config edit          # Revert config changes
hermes config check         # Find missing config
```

### Session

```bash
/rollback N                 # Restore filesystem checkpoint (if checkpoints enabled)
hermes sessions list        # Revert to known-good session
```

### Manual Override

If Hermes is behaving unexpectedly:
1. `/stop` — kill all background processes
2. `/new` or `/reset` — fresh session
3. Check `~/.hermes/logs/gateway.log` for errors
4. `hermes doctor` — verify dependencies and config

---

## Appendices

### A. Agent Receipt Model

Every Hermes action at IKE produces a receipt. This creates an auditable trail from "AI helped" to "proof exists."

#### Receipt Format

Every receipt follows this structure:

```
RECEIPT: [TYPE] — [DATE] — [ID]

Action:     [What was done — draft, merge, classify, etc.]
Scope:      [Which mission / which repo / which case]
Files:      [Paths to all files created or modified]
Status:     Draft | Completed | Pending Approval
Approval:   [Gate crossed? Yes/No + who approved]
Timestamp:  [ISO datetime]
Hash:       [Content hash of the output, if applicable]
```

#### Receipt Types

| Type | When Generated | Contains |
|---|---|---|
| `DRAFT` | Every draft document created | File path, content summary, status=Draft |
| `MERGE` | Every PR merged | PR number, files changed, checks passed, branch deleted |
| `CLASSIFY` | Every evidence item classified | Bureau, account, document type, confidence |
| `APPROVAL` | Every approval gate crossed | What was approved, by whom, timestamp |
| `REPORT` | Every cron job output | Checks run, results, recommendations |
| `INTAKE` | Every new case or intake started | Client/case name, documents received, next action |

#### Receipt Storage

Receipts are stored as markdown files in the relevant mission directory:

```
~/credit-command-center/07-correspondence-log/receipts/
~/Isionnah-TCA-Packet/04-mail-control/receipts/
~/ike-solutions/receipts/
```

Each receipt file is named: `RECEIPT_[TYPE]_[YYYY-MM-DD]_[HHMM].md`

#### Receipt Template

```markdown
# RECEIPT: [TYPE] — [YYYY-MM-DD]

**Action:** [What was done]
**Scope:** [Mission / Repo / Case]
**Status:** [Draft / Completed / Pending Approval]
**Approval:** [Yes/No — who]
**Timestamp:** [ISO datetime]

## Files
- [path/to/file] — [description]

## Details
[Brief summary of what was produced or changed]

## Next Action
[What needs to happen next, if anything]
```

---

### B. File Naming Conventions

| Domain | Pattern | Example |
|---|---|---|
| Credit evidence | `[Bureau]_[Account]_[DocType]_[YYYY-MM-DD]` | `EQ_Midland_PaymentRecord_2023-06-15.pdf` |
| TCA packet | `[Section]_[DocType]_[YYYY-MM-DD]` | `01-TCA_Notice_2026-01-15.pdf` |
| Dispute letters | `[Bureau]_[Account]_DisputeDraft_YYYY-MM-DD` | `EQ_Midland_DisputeDraft_2026-06-09.md` |
| Demand letters | `DEMAND-LETTER_[Creditor]_[Topic]_[YYYY-MM-DD]` | `DEMAND-LETTER_UACC_1099C_2026-06-08.md` |

### C. SintraPrime Case Codes

CR-01 through CR-15 covering: Inaccurate Reporting, Not My Account, Outdated Information, Duplicate Account, Paid Collection, Collection Without Validation, Medical Collection, Hard Inquiry Error, Identity Theft, Bankruptcy Error, Public Record/Judgment, Goodwill Removal, Pay-for-Delete, Mixed File, Expired SOL.

### D. Key Paths

| Resource | Path |
|---|---|
| Hermes config | `~/.hermes/config.yaml` |
| Hermes env vars | `~/.hermes/.env` |
| Hermes skills | `~/.hermes/skills/` |
| SintraPrime repo | `C:\Users\admin\Desktop\SintraPrime-Unified` |
| SintraPrime docs | `C:\Users\admin\Desktop\SintraPrime-Unified\docs` |
| Credit Command Center | `~/credit-command-center/` |
| TCA Packet | `~/Isionnah-TCA-Packet/` |
| IKE Solutions operations | `~/.hermes/skills/productivity/ike-solutions-operations/` |
| Hermes logs | `~/.hermes/logs/gateway.log` |
