# IKE Agent Mesh Ledger

**Purpose:** Durable, append-only audit trail for all IKE Agent Mesh messages. It is the source of truth for who assigned what, when, why a task was blocked, and what the owner decided.

## Layout

```text
.mesh/
  ledger/
    README.md
    2026-07.jsonl
    2026-08.jsonl
    ...
```

- One file per calendar month in `YYYY-MM.jsonl` format.
- Each line is one JSON object matching the schema defined in `ops/IKE_AGENT_MESH.md`.
- Lines are written in chronological order.

## Rules

1. **Append-only.** Never edit, delete, or reorder existing lines.
2. **No secrets.** Never include tokens, passwords, API keys, PII, or attorney-client privileged material.
3. **One message per line.** Every status change is a new line.
4. **Validate on write.** A new line must conform to the schema before it is appended. If a mistake is made, append a correcting follow-up message (`REJECTED` or `CLOSED`) rather than editing the original line.
5. **Thread replay.** All messages for a single `task_id` across monthly files constitute the complete history of that workstream.

## How to audit a decision

```bash
# All messages for one task
cat .mesh/ledger/2026-07.jsonl | jq 'select(.task_id == "SPU-20260708-001")'

# All BLOCKED messages
cat .mesh/ledger/2026-07.jsonl | jq 'select(.status == "BLOCKED")'

# All messages requiring owner decision
cat .mesh/ledger/2026-07.jsonl | jq 'select(.owner_decision_required == true)'

# All messages in a Slack thread
cat .mesh/ledger/2026-07.jsonl | jq 'select(.thread_id == "1783545490.531799")'
```

## Retention

Keep ledger files in the repo indefinitely. They are small text files and provide the only durable record of agent coordination decisions.

## Adding a new entry

1. Generate a UUID4 for `mesh_id`.
2. Copy the `thread_id` from the Slack thread or GitHub issue/PR.
3. Set `from_agent`, `to_agent`, `task_id`, `status`, `priority`, and `objective`.
4. Fill `evidence` with links or file paths. Leave empty only for pure coordination pings.
5. Set `blocker` to a string when `status == BLOCKED`; otherwise `null`.
6. Set `owner_decision_required: true` when human approval is needed.
7. Use ISO8601 UTC for `timestamp`.
8. Keep `notes` neutral and factual.
9. Append the JSON line to the current month file.
10. Commit the file as part of the normal PR/merge flow.
