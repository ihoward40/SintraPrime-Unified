# SintraPrime Unified Agent Contract

## Purpose

This repository uses external AI agents, including Tasklet AI and Manus AI, to assist with safe development, documentation, security remediation, and automation.

## Roles

### SintraPrime Commander
Defines mission scope, validates legal/security posture, reviews agent outputs, and approves merges.

### Tasklet AI
Handles recurring automation, monitoring, reminders, issue triage, CI summaries, and structured handoffs.

### Manus AI
Handles implementation planning, code patches, refactors, documentation, UI drafts, and test generation.

## Source of Truth

GitHub is the source of truth.

- GitHub Issues are the mission queue.
- Branches are work isolation.
- Pull Requests are the review gate.
- Receipts are mandatory for auditability.

## Non-Negotiable Rules

1. No direct commits to `main`.
2. No real secrets in prompts, files, screenshots, logs, or issues.
3. No arbitrary generated code execution.
4. No external legal, financial, tax, court, banking, or government action without explicit human approval.
5. Every agent action must produce a receipt.
6. Every pull request must include files changed, commands run, tests run, risks, and next steps.
7. Security checks must fail closed.
8. Human review is required before merge.

## Required Receipt Format

Each agent must report:

- Agent name
- Task ID
- Branch
- Files touched
- Commands run
- Test results
- Security scan results
- Risks/blockers
- Recommended next action
- Timestamp
