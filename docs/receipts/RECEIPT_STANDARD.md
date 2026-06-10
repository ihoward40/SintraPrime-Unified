# Receipt Standard

## Purpose

Every autonomous workflow **must** leave a receipt. Receipts are the immutable audit trail that proves work was done, what was touched, and whether it passed validation.

Receipts are not optional. If there is no receipt, the work did not happen.

---

## Receipt Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `workflow_id` | UUID v4 | ✅ | Unique identifier for this workflow execution |
| `timestamp` | ISO 8601 | ✅ | When the workflow completed |
| `user_intent` | string | ✅ | What the user asked for (original instruction) |
| `intent_summary` | string | ✅ | One-sentence summary of what was actually done |
| `files_touched` | string[] | ✅ | Full paths of every file created or modified |
| `tools_used` | string[] | ✅ | Tools used (e.g., write_file, terminal, web_search) |
| `sources_reviewed` | string[] | ⬜ | URLs, docs, or references consulted |
| `actions_taken` | string[] | ✅ | List of actions performed |
| `actions_blocked` | string[] | ⬜ | Any actions that were blocked by policy |
| `risk_domain` | string | ✅ | Classification from risk classifier |
| `validation_result` | string | ✅ | `passed`, `partial`, `blocked`, or `failed` |
| `validation_checks` | object[] | ✅ | Each check: name, passed (bool), detail |
| `stop_reason` | string | ⬜ | Why the workflow stopped (if not completed) |
| `next_recommended_action` | string | ⬜ | What should happen next, if anything |
| `agent_role` | string | ✅ | Which agent role executed this workflow |
| `approval_tier` | string | ✅ | T1, T2, or T3 |

---

## Receipt Format

### JSON (machine-readable)

```json
{
  "workflow_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-06-10T14:30:00Z",
  "user_intent": "Review the TransUnion credit report for UCC filings",
  "intent_summary": "Analyzed TransUnion report, found 2 UCC filings, drafted dispute letter",
  "files_touched": [
    "docs/reports/transunion-review-2026-06-10.md",
    "artifacts/receipts/a1b2c3d4-e5f6-7890-abcd-ef1234567890.json"
  ],
  "tools_used": ["read_file", "write_file", "terminal"],
  "sources_reviewed": [
    "docs/second-brain/MASTER_INDEX.md",
    "apps/ike-bot/main/src/services/creditDispute.service.ts"
  ],
  "actions_taken": [
    "Loaded TransUnion report from inbox",
    "Flagged 2 UCC filings for review",
    "Drafted dispute letter draft"
  ],
  "actions_blocked": [],
  "risk_domain": "financial_admin",
  "validation_result": "passed",
  "validation_checks": [
    {"name": "files_exist", "passed": true},
    {"name": "tests_run", "passed": true},
    {"name": "citations_present", "passed": true},
    {"name": "receipt_generated", "passed": true},
    {"name": "no_conflict_markers", "passed": true},
    {"name": "no_secrets_exposed", "passed": true},
    {"name": "no_unresolved_todos", "passed": true}
  ],
  "next_recommended_action": "Review dispute letter draft and approve for mailing",
  "agent_role": "drafting-agent",
  "approval_tier": "T2"
}
```

### Markdown (human-readable)

Receipts should also produce a human-readable summary:

```markdown
## Receipt: a1b2c3d4-e5f6-7890-abcd-ef1234567890

**Workflow:** Review credit report
**Agent:** drafting-agent
**Completed:** 2026-06-10T14:30:00Z
**Status:** ✅ Passed

### What was done
- Loaded TransUnion report from inbox
- Flagged 2 UCC filings for review
- Drafted dispute letter

### Files created/modified
- docs/reports/transunion-review-2026-06-10.md
- artifacts/receipts/a1b2c3d4-....json

### Validation
| Check | Result |
|---|---|
| Files exist | ✅ |
| Tests run | ✅ |
| Citations present | ✅ |
| Receipt generated | ✅ |
| No conflict markers | ✅ |
| No secrets exposed | ✅ |
| No unresolved TODOs | ✅ |

### Next action
Review dispute letter draft and approve for mailing.
```

---

## Storage

- Receipts are stored in `artifacts/receipts/<workflow_id>.json`
- Human-readable summaries go in the same directory as `<workflow_id>.md`
- Receipts are never deleted. Retention is permanent.

---

## Script

To generate a receipt programmatically:

```bash
python scripts/receipts/create_receipt.mjs  # or .py — see scripts/receipts/
```

---

## Enforcement

- QA Agent must verify receipt exists before marking any workflow complete
- Compliance/Safety Agent must reject any workflow without a valid receipt
- Missing receipts are reported in the weekly audit