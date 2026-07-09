# IKE Agent Mesh Registry

**Status:** Proposal — pending Agent Hub / owner review.  
**Purpose:** Document how each agent receives and sends official Agent Mesh messages, so the protocol does not depend on ad-hoc forwarding.

## Legend

- `can_send_to_slack` — agent can post directly to a Slack channel or thread.
- `can_read_from_slack` — agent can read assignments from Slack without human paste.
- `requires_human_relay` — a human or another agent must copy/paste messages for this agent.
- `requires_api_key_or_webhook` — Slack app token / webhook / Socket Mode still needed.
- `current_status` — Active, Paused, Unknown, or Not connected.
- `next_setup_step` — concrete action to move the agent to direct transport.

## Official communication rule

No agent may use casual chat as official work. Every official agent action must use one status:

`ASSIGNED | ACK | IN_PROGRESS | RESULT | BLOCKED | CLOSED`

## Registry

| agent_name | role | slack_channel_or_dm | can_send_to_slack | can_read_from_slack | requires_human_relay | requires_api_key_or_webhook | current_status | next_setup_step |
|---|---|---|---|---|---|---|---|---|
| Agent Hub | Coordinator / dispatcher | `#ike-command-center` | **Unverified** — claimed direct Slack send in prior session, but *cannot post directly into Slack from this session* | **Unverified** | No | Maybe — confirm token scope | Active | Verify direct Slack send/read or document current relay path; create `#ike-command-center` only after verification. |
| Hermes | Verifier / evidence operator | `#ike-command-center` or this DM thread | **Unverified in this session** — Hermes receives prompts in this Slack DM (read works) but cannot post outbound to Slack from this session | **Read works via this Slack DM**; full channel read unverified | Yes until verified — gateway may support outbound, but not confirmed in this session | Gateway config exists but outbound send not tested here | Active | Hermes to verify outbound Slack post capability in `#ike-command-center` or document relay requirement. |
| Manus | Executor / build agent | Unknown | Unknown | Unknown | Yes until confirmed | Yes until confirmed | Unknown | Agent Hub to query Manus for Slack/webhook capability and update this row. |
| Tasklet | Automation / scheduled tasks | Unknown | Unknown | Unknown | Yes until confirmed | Yes until confirmed | Unknown | Agent Hub to query Tasklet for Slack/webhook capability and update this row. |
| Viktor | Strategy / build agent | Paused | No | No | Yes | Yes | Paused | Restore credits/access first, then add Slack/webhook transport. |
| ChatGPT | Architect / auditor | API / manual | Limited | Yes | Human relay | API if automated | Active (manual relay) | Keep as auditor/drafter; do not impersonate other agents. |

## Command center channel proposal

Create **#ike-command-center** as the primary visible coordination surface.

- All official `ASSIGNED`, `ACK`, `IN_PROGRESS`, `RESULT`, `BLOCKED`, `CLOSED` messages should flow there.
- Human owner retains veto/decision gate.
- Durable record still lives in `.mesh/ledger/YYYY-MM.jsonl`.

## Transport levels

```
Level 1 — Human-mediated
  You paste Agent Hub commands into Slack.
  Hermes / other agents respond when prompted.
  Works now.

Level 2 — Semi-automated
  Agent Hub posts structured ASSIGNED messages.
  Hermes, Manus, Tasklet, etc. respond in the same thread when invoked.
  Mostly ready.

Level 3 — Fully automated
  Each agent has Slack API access or a webhook relay.
  Agents post ACK, IN_PROGRESS, RESULT, BLOCKED, CLOSED automatically.
  Requires setup per agent.
```

## Evidence already collected

- Live Agent Mesh transport test completed in `.mesh/ledger/2026-07.jsonl`.
- Task ID: `SPU-AGENT-MESH-TRANSPORT-001`.
- Lifecycle: `ASSIGNED → ACK → IN_PROGRESS → RESULT → CLOSED`.
- This proves the **protocol/language layer works**.
- Remaining work is the **transport layer** for each agent.

## Owner decision required

1. Approve creating `#ike-command-center`?
2. Confirm Agent Hub can post and monitor there?
3. Authorize Hermes to post official ACK/RESULT messages there?
4. Assign Agent Hub to query Manus, Tasklet, Viktor transport capability?

## Constraints

- No production code changes.
- No new secrets stored outside existing `.env`/gateway config.
- No new API connections until separately approved.
- This file is a proposal only; merge only after owner review.
