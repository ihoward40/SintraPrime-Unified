# collaboration — Collaborative Agent Fabric

## Purpose

Persistent collaboration spaces where humans and agents share
operational context; agents wake on relevant structured events.
SintraPrime remains the control plane. Agents compute — they do not
create authority.

## Ownership

- `collaboration/` — all models, policies, runtime services, events,
  receipts, APIs, POC, tests
- `docs/collaboration/` and `docs/governance/COLLABORATIVE_AGENT_AUTHORITY.md`
- `artifacts/collaboration/` — evidence packet

## Local Contracts

- Every agent activation is gated by the event policy engine
  (fail closed) and the actor policy engine (allowlist by default
  for sensitive agents).
- Anti-loop: `max_agent_hops = 4`; exceeding → `BLOCKED_LOOP_GUARD`.
- Every event/activation/handoff writes a hash-chained receipt.
- Channel messages are untrusted input — prompt-injection defensive
  separation required in agent-facing prompts.
- No agent may merge, deploy, spend, file, or mutate canonical memory
  without existing SintraPrime governance gates.
- CF-1 persists via JSON (`CollaborationStore`); PostgreSQL models
  are Phase CF-2.

## Work Guidance

*(No specific guidance in this subtree beyond the above.)*
