# IKE Agent Mesh — Command Protocol

**Status:** Draft v0.1  
**Scope:** Communication contract and durable audit ledger for coordinating autonomous agents across the IKE/SintraPrime ecosystem.  
**Binding rule:** No agent may silently assume ownership of a task, merge code, dispatch external action, or escalate without a ledger entry.

---

## Purpose

Multiple agents (Hermes, ChatGPT, Tasklet, Manus, Viktor, Watchtower, and future agent workers) currently operate in separate contexts. The IKE Agent Mesh is a lightweight command protocol that lets them:

1. Hand work to one another with a clear objective and owner.
2. Acknowledge acceptance, report progress, and surface blockers.
3. Preserve an append-only audit trail in the repo so decisions can be replayed.

It does **not** replace existing `agent_protocol` or `orchestration` modules. It is a **Slack-visible, repo-durable coordination layer** on top of them.

---

## Agent Roles

| Agent | Responsibility | May decide | May not decide |
|---|---|---|---|
| `isiah` | Human owner and final authority | Everything | — |
| `chatgpt` | External reviewer, second opinion | Recommend, question | Merge, deploy, dispatch |
| `hermes` | Orchestrator, repo/CLI operator, evidence gatherer | Execute verified commands, open PRs, report blockers | Merge without explicit owner approval, dispatch external actions |
| `tasklet` | Recurring checks, triage, summaries | Post summaries, label issues, ask for decisions | Merge, execute unverified code |
| `manus` | Implementation, refactoring, docs, tests | Work on feature branches, open PRs | Merge to `main`, execute arbitrary code |
| `viktor` | Infrastructure, deployment, security posture | Recommend infra changes, prepare deploy artifacts | Deploy to production without owner approval |
| `watchtower` | Uptime, alerts, anomaly detection | Report alerts, open issues | Take autonomous remedial action |

---

## Message Lifecycle

Every unit of work moves through one or more of these states. Each state change is a ledger entry.

| Status | Meaning | Required next step |
|---|---|---|
| `ASSIGNED` | Work handed from one agent to another | Receiving agent must `ACK` or `REJECT` |
| `ACK` | Receiving agent accepts ownership; may include ETA | Work proceeds to `IN_PROGRESS` or `BLOCKED` |
| `IN_PROGRESS` | Active work reported | Continues until `RESULT`, `BLOCKED`, or `REJECTED` |
| `BLOCKED` | Cannot proceed without input/decision | Blocker field must be filled; owner must respond |
| `RESULT` | Deliverable, evidence, and recommended next action | Owner reviews and `CLOSES` or reassigns |
| `REJECTED` | Agent declines or cannot perform; reason required | Reassign or close |
| `CLOSED` | Owner reviewed and accepted; work is complete | None |

---

## Required Message Fields

```json
{
  "mesh_id": "uuid4",
  "thread_id": "slack-thread-ts-or-github-issue-pr",
  "from_agent": "isiah|chatgpt|hermes|tasklet|manus|viktor|watchtower",
  "to_agent": "isiah|chatgpt|hermes|tasklet|manus|viktor|watchtower",
  "task_id": "SPU-YYYYMMDD-###",
  "status": "ASSIGNED|ACK|IN_PROGRESS|BLOCKED|RESULT|REJECTED|CLOSED",
  "priority": "P0|P1|P2",
  "objective": "short task objective",
  "evidence": ["slack_url_or_github_url_or_file_path"],
  "blocker": null,
  "owner_decision_required": false,
  "timestamp": "ISO8601",
  "notes": "short neutral note"
}
```

### Field rules

- `mesh_id` — globally unique per message (UUID4).
- `thread_id` — ties the message to a Slack thread or GitHub issue/PR for replay.
- `from_agent` / `to_agent` — must be from the role list above.
- `task_id` — stable identifier for the workstream (`SPU-YYYYMMDD-###`).
- `status` — exactly one lifecycle value.
- `priority` — `P0` blocks other work; `P1` planned; `P2` opportunistic.
- `objective` — one-sentence description of what the message is about.
- `evidence` — URLs, file paths, commit SHAs, PR numbers. Never empty for `RESULT` or `BLOCKED`.
- `blocker` — required and non-null when `status == BLOCKED`; otherwise `null`.
- `owner_decision_required` — `true` when human approval is needed.
- `timestamp` — ISO8601 UTC.
- `notes` — neutral, factual context. No assumptions or conclusions.

---

## Slack Posting Format

Slack is the **visible command layer**. When an agent posts to Slack, it should use this compact block format so humans can scan quickly:

```text
[IKE Mesh | hermes → isiah | SPU-20260708-001 | RESULT | P0]
Objective: Verify and merge PR #180 packaging cleanup
Evidence: https://github.com/ihoward40/SintraPrime-Unified/pull/180
- GitHub CI: all green
- Local project venv pytest: 100% pass
- Hermes venv pydantic_core: repaired, pytest 100% pass
Notes: Supported-lane contract reconciled. Recommending merge.
Owner decision required: true
```

Rules:
- One message per status change.
- Use the same `task_id` in every message for the same workstream.
- When `BLOCKED`, the first line after `Blocker:` must state exactly what is needed.
- No code blocks or secrets in the Slack summary; link to repo files or GitHub for details.

---

## Ledger JSONL Format

The repo ledger is the **durable audit layer**. Each line is a single JSON object matching the schema above.

### File layout

```text
.mesh/
  ledger/
    README.md
    2026-07.jsonl
    2026-08.jsonl
    ...
```

- One file per calendar month.
- Append-only. Never edit or delete existing lines.
- Every line must validate against the schema. Invalid lines must be corrected by appending a `REJECTED`/`CLOSED` follow-up, not by editing.
- No secrets, tokens, PII, or attorney-client privileged material.

### How to replay/audit a decision

```bash
# Find all messages for a task
cat .mesh/ledger/2026-07.jsonl | jq 'select(.task_id == "SPU-20260708-001")'

# Find all BLOCKED messages
cat .mesh/ledger/2026-07.jsonl | jq 'select(.status == "BLOCKED")'

# Find all owner decisions required
cat .mesh/ledger/2026-07.jsonl | jq 'select(.owner_decision_required == true)'
```

---

## Blocker Escalation Rule

1. When an agent posts `BLOCKED`, it must:
   - State the exact blocker.
   - Name the owner who can resolve it.
   - Set `owner_decision_required: true`.
2. The owner must respond with `ACK` (received), a new `ASSIGNED` to another agent, or a `CLOSED` decision.
3. If a `BLOCKED` message is not resolved within the SLA, the agent may post a daily reminder but may **not** act unilaterally.

| Priority | SLA for owner response |
|---|---|
| P0 | 4 hours during active window |
| P1 | 24 hours |
| P2 | 72 hours |

---

## Owner-Decision Rule

The following actions require `owner_decision_required: true` in the message:

- Merge to `main`.
- Deploy to production or staging.
- Dispatch any legal, financial, tax, court, banking, or government communication.
- Execute dynamically generated code.
- Re-prioritize a deferred workstream.
- Add new runtime services or external integrations.

---

## No-Silent-Assumption Rule

An agent must not:

- Assume another agent has seen or accepted a task without an `ACK`.
- Assume a green CI means merge approval.
- Assume a previous owner direction still applies without confirmation.
- Assume a deferred task is now active unless the owner explicitly reactivates it.

Every assumption must be surfaced as a `BLOCKED` message or confirmed in a `RESULT`.

---

## Examples

### Example 1: PR verification and merge

Ledger entries:

```json
{"mesh_id":"a1b2c3d4","thread_id":"1783545490.531799","from_agent":"isiah","to_agent":"hermes","task_id":"SPU-20260708-001","status":"ASSIGNED","priority":"P0","objective":"Verify PR #180 packaging cleanup and report whether it is safe to merge","evidence":["https://github.com/ihoward40/SintraPrime-Unified/pull/180"],"blocker":null,"owner_decision_required":false,"timestamp":"2026-07-08T20:00:00Z","notes":"Hold at verification gate until supported-lane contract is reconciled."}
{"mesh_id":"e5f6g7h8","thread_id":"1783545490.531799","from_agent":"hermes","to_agent":"isiah","task_id":"SPU-20260708-001","status":"RESULT","priority":"P0","objective":"Report PR #180 verification status","evidence":["https://github.com/ihoward40/SintraPrime-Unified/pull/180","/tmp/sintraprime_main_pytest.log"],"blocker":null,"owner_decision_required":true,"timestamp":"2026-07-08T21:00:00Z","notes":"GitHub CI green; project venv and Hermes venv default pytest lanes both pass 100%. Recommending merge."}
{"mesh_id":"i9j0k1l2","thread_id":"1783545490.531799","from_agent":"isiah","to_agent":"hermes","task_id":"SPU-20260708-001","status":"ASSIGNED","priority":"P0","objective":"Merge PR #180 now","evidence":["https://github.com/ihoward40/SintraPrime-Unified/pull/180"],"blocker":null,"owner_decision_required":false,"timestamp":"2026-07-08T21:30:00Z","notes":"Approved. Proceed with merge."}
{"mesh_id":"m3n4o5p6","thread_id":"1783545490.531799","from_agent":"hermes","to_agent":"isiah","task_id":"SPU-20260708-001","status":"RESULT","priority":"P0","objective":"Confirm PR #180 merged and local main synced","evidence":["https://github.com/ihoward40/SintraPrime-Unified/pull/180","ad7a738fa82e2f3565ff45b61301100e10fd26a5"],"blocker":null,"owner_decision_required":false,"timestamp":"2026-07-08T21:35:00Z","notes":"Merge complete; local main fast-forwarded to ad7a738f."}
```

### Example 2: Blocked on human outreach

```json
{"mesh_id":"q7r8s9t0","thread_id":"1783000000.000000","from_agent":"hermes","to_agent":"isiah","task_id":"SPU-20260708-002","status":"BLOCKED","priority":"P0","objective":"Obtain IRS 3176C bank statements for 1040-X filing","evidence":[],"blocker":"Owner must provide bank statements or authorize Hermes to fetch them from the designated source.","owner_decision_required":true,"timestamp":"2026-07-08T20:15:00Z","notes":"IRS CNC workstream paused at human outreach gate per Evidence Operations Mode."}
```

---

## Future Additions (Deferred)

The following are intentionally out of scope until the manual protocol proves reliable:

- Automated cron summaries.
- Autonomous blocker escalation.
- Runtime service or Slack slash-command integration.
- Schema validation CI gate.

When added, each must be proposed as a separate task and approved by `isiah`.

---

## References

- `agent_protocol/` — existing in-process/network agent primitives.
- `orchestration/` — existing durable execution and A2A protocol.
- `ops/AGENT_CONTRACT.md` — earlier P0 agent contract (legacy branch).
- `.mesh/ledger/` — this protocol’s audit trail.
