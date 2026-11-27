# Collaboration Event Model

## Canonical Envelope (directive §VIII)

```json
{
  "event_id": "evt_...",
  "event_type": "CHANNEL_MESSAGE_CREATED",
  "tenant_id": "...",
  "channel_id": "...",
  "actor": {"type": "human", "id": "..."},
  "timestamp": "...",
  "correlation_id": "...",
  "payload": {},
  "provenance": {},
  "security_classification": "internal"
}
```

Plus anti-loop fields: `origin_type`, `origin_id`, `causal_chain`,
`hop_count`, `workflow_run_id`.

## Initial Event Types (CF-1)

- `channel_message_created`
- `channel_member_joined`
- `channel_member_left`
- `agent_mentioned`
- `workflow_started`
- `workflow_completed`
- `workflow_failed`
- `approval_requested`
- `approval_resolved`
- `artifact_created`
- `reaction_added`
- `command_created`
- `command_blocked`
- `handoff_created`
- `handoff_completed`
- `handoff_failed`
- `agent_added_to_channel`

## Dispatch Pipeline (directive §LX)

```
event → validate envelope
      → binding exists?
      → tenant matches?
      → event type allowed by binding?
      → actor authorized (allowlist/roles)?
      → loop guard (hop ≤ 4)?
      → dedup (not consumed)?
      → rate limit OK?
      → concurrency slot available?
      → kill switch NOT active?
      → ACTIVATE (else QUEUED/SKIPPED + reason)
```

Fail closed at every gate. No model invocation until all
deterministic filters pass.

## Event Receipt (directive §XLIX)

Records: event emitted, subscriptions matched, agents evaluated,
agents activated, agents skipped + reason for each skip.
