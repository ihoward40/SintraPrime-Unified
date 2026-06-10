# Permission Layer

> Prompts are not permission layers. Real control comes from what the agent can physically access.

## Core Principle

A permission model built on prompt instructions alone is **not a security boundary**. If an agent *can* read a file, write to a path, or call an API, a sufficiently capable agent will do so regardless of what its system prompt says. The only reliable permission layer is the set of **physical access controls** enforced by the operating system, filesystem permissions, network rules, and tool-level gating.

This document defines the SintraPrime permission model — not as a prompt-level suggestion, but as a **contract** that must be enforced by the runtime environment, tool implementations, and verification scripts.

---

## Permission Definitions

### 1. `read_only`

| Field | Value |
|---|---|
| **Default** | `true` (always on) |
| **Effect** | Agent may read files and directories but may not create, modify, or delete any content. |
| **When it applies** | Always, unless explicitly overridden. This is the baseline safety mode. |
| **How to escalate** | Issue `confirm_write` command, or escalate to `write_local_only` via profile override. |

### 2. `draft_only`

| Field | Value |
|---|---|
| **Default** | `false` |
| **Effect** | Agent may create new files only in designated `draft/` or `tmp/` directories. No edits to existing production files. |
| **When it applies** | When the user issues `draft: <path>` or the working directory contains `draft` or `tmp`. |
| **How to escalate** | Issue `write_local` to move to full local write access. |

### 3. `write_local_only`

| Field | Value |
|---|---|
| **Default** | `false` |
| **Effect** | Agent may create and modify files within the local repository only. No writes to system paths, user home outside repo, or network mounts. |
| **When it applies** | When the user issues `write_local` or the target path is under the repository root. |
| **How to escalate** | No further escalation — this is the maximum write scope for local operations. System-level writes require separate infrastructure. |

### 4. `external_send_requires_confirmation`

| Field | Value |
|---|---|
| **Default** | `true` (always on) |
| **Effect** | Any outbound communication (email, API call, webhook, Slack message) requires explicit user confirmation before being sent. |
| **When it applies** | Always, unless the user issues `confirm_send` for a specific message or a pre-approved cadence window is active. |
| **How to escalate** | Issue `confirm_send` with the message identifier. |

### 5. `destructive_action_blocked`

| Field | Value |
|---|---|
| **Default** | `true` (always on) |
| **Effect** | Actions that delete, overwrite, or irreversibly transform data are blocked unless explicitly approved. Includes file deletion, database truncation, and bulk rename. |
| **When it applies** | Always. Override is single-use and expires after 5 minutes. |
| **How to escalate** | Issue `allow_destructive` with a specific scope. |

### 6. `legal_output_requires_review`

| Field | Value |
|---|---|
| **Default** | `true` (always on) |
| **Effect** | Any output intended for legal proceedings, court filings, or regulatory submissions must be flagged for human review before delivery. |
| **When it applies** | When the output targets a `matters/court-legal/` or `matters/regulatory/` path, or contains legal citations. |
| **How to escalate** | Issue `review_approved` with the explicit version hash, or store written legal sign-off in `matters/<case>/approvals/`. |

### 7. `financial_output_requires_review`

| Field | Value |
|---|---|
| **Default** | `true` (always on) |
| **Effect** | Any output containing financial figures, monetary demands, settlement amounts, or payment instructions must be reviewed by a human before release. |
| **When it applies** | When the output contains currency amounts, financial calculations, or targets a `business-revenue/` or `matters/` path with financial content. |
| **How to escalate** | Issue `finance_reviewed` with explicit figure confirmation. |

### 8. `identity_data_requires_redaction`

| Field | Value |
|---|---|
| **Default** | `true` (always on) |
| **Effect** | Any output containing PII (names, SSNs, DOBs, addresses, account numbers) must be redacted or flagged before external delivery. |
| **When it applies** | Always for external-facing output. Internal-only output within the repository is exempt. |
| **How to escalate** | Issue `redaction_confirmed` after verifying all PII is removed. |

---

## Enforcement

Permissions are enforced at three layers:

| Layer | Mechanism | Bypassable by prompt? |
|---|---|---|
| **Filesystem** | OS-level read/write/execute permissions on files and directories | No |
| **Tool gate** | Tool implementations check permission state before acting | No (if implemented correctly) |
| **Verification** | `verify_aios_output.py` and `repo_truth_check.py` validate permission compliance | No (post-hoc) |
| **Prompt** | System prompt describes permission rules | **Yes — not a real control** |

Only the first three layers constitute real permission enforcement. The prompt layer is documentation, not security.

---

## Escalation Flow

```
read_only (default)
    │
    ├── confirm_write ──► draft_only
    │                        │
    │                        └── write_local ──► write_local_only
    │
    ├── confirm_send ──► external_send_requires_confirmation (lifted for message)
    │
    ├── allow_destructive ──► destructive_action_blocked (lifted for scope, 5min TTL)
    │
    ├── review_approved ──► legal_output_requires_review (lifted for version)
    │
    ├── finance_reviewed ──► financial_output_requires_review (lifted for output)
    │
    └── redaction_confirmed ──► identity_data_requires_redaction (lifted for output)
```

All escalations are **temporary and scoped** unless otherwise specified. No permission override persists across sessions.