# `.mesh/` — Agent Mesh Coordination

**Purpose:** Durable, human-auditable coordination surface for the IKE Agent Mesh.

**Scope:**
- Agent Mesh protocol messages and schema
- Append-only ledger entries (`.mesh/ledger/YYYY-MM.jsonl`)
- Agent transport registry (`.mesh/AGENT_MESH_REGISTRY.md`)

## Local Contracts

1. **Append-only ledger.** Never edit, delete, or reorder existing lines. Correct mistakes by appending a follow-up message.
2. **No secrets in ledger or registry.** Never include tokens, API keys, passwords, PII, or attorney-client privileged material.
3. **Verified claims only.** The registry marks Slack send/read access as `Unverified` unless it has been demonstrated in the current session or documented with evidence.
4. **Official statuses only.** Agent work communication must use `ASSIGNED | ACK | IN_PROGRESS | RESULT | BLOCKED | CLOSED`.
5. **Human owner retains veto/decision gate.** No automated commits, PRs, merges, deployments, charges, or issue modifications without explicit owner approval.

## Work Guidance

- Add new ledger entries as single JSON lines to the current month file.
- Update the registry when an agent's transport status changes.
- Keep the registry honest: distinguish verified direct access, gateway relay, human relay, paused, and unknown.

## Verification

- `git diff -- .mesh/ledger/YYYY-MM.jsonl` should show only appended lines.
- `git status --short .mesh/` should show no unexpected code changes.
- Registry must not contain bare `| Yes | Yes |` Slack send/read claims unless verified.

## Child DOX Index

None.
