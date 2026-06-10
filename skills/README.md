# Skills — Reusable Task Definitions

## What Is a Skill?

A **skill** is a repeatable task definition that agents can load and execute. Skills encapsulate:

- **Purpose** — what the skill accomplishes
- **Inputs** — what data/files the skill needs
- **Outputs** — what the skill produces
- **Steps** — the execution sequence
- **Verification** — how to confirm the skill ran correctly

Skills live in `skills/<name>/SKILL.md` and are registered in `skills/registry.json`.

---

## Registered Skills

| Skill | Purpose | Status |
|---|---|---|
| `credit-report-review` | Analyze credit reports for errors, UCC filings, and furnisher violations | Planned |
| `affidavit-builder` | Draft sworn affidavits for UCC disputes and court filings | Planned |
| `court-packet-builder` | Assemble court filing packets with exhibits and certificates of service | Planned |
| `email-intake-triage` | Classify and route incoming email by case, urgency, and action needed | Planned |
| `evidence-manifest-builder` | Create evidence manifests with chain-of-custody tracking | Planned |
| `social-post-repurposer` | Repurpose content across platforms with platform-specific formatting | Planned |
| `music-release-planner` | Plan music releases with distribution, metadata, and promotion checklist | Planned |
| `trust-admin-checklist` | Run trust administration checklists for beneficiary actions and reporting | Planned |
| `repo-review` | Review repository health: git status, CI status, dependency audits | Planned |
| `smoke-runner` | Execute smoke tests and report pass/fail with receipt trail | Planned |

---

## Skill Lifecycle

1. **Planned** — Identified but not yet authored
2. **Authored** — SKILL.md exists in `skills/<name>/`
3. **Tested** — Verified against real inputs
4. **Active** — Registered and available for agent dispatch
5. **Deprecated** — Superseded or no longer needed

---

## Creating a New Skill

1. Create `skills/<name>/SKILL.md` with frontmatter (name, description, version, inputs, outputs)
2. Add entry to `skills/registry.json`
3. Test with a representative input
4. Update this README if adding a new category