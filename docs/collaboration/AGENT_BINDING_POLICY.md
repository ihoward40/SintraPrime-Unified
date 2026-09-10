# Agent Binding Policy

## AgentChannelBinding (directive §VI)

```text
id, tenant_id, channel_id, agent_id, status
response_mode, allowed_event_types, actor_allowlist
max_parallelism, queue_depth, rate_limit_per_hour
execution_profile, memory_mode
provider_profile, model_profile
budget
```

## Response Modes

| Mode | Meaning | Default |
|---|---|---|
| MENTION_ONLY | wake only on explicit mention | ✅ default |
| OWNER_ONLY | wake only for channel owner | |
| ALLOWLIST | wake only for allowlisted actors | (sensitive agents) |
| EVENT_TRIGGERED | wake on subscribed event types | |
| PASSIVE | observe, never auto-respond | |
| ALL_MESSAGES | wake on all messages — requires explicit authorization | |

## Actor Trigger Policies (directive §XII)

`ANY_AUTHENTICATED_MEMBER`, `CHANNEL_OWNER`, `CHANNEL_ADMINS`,
`ALLOWLIST`, `SYSTEM_ONLY`, `PRINCIPAL_ONLY`.

Sensitive agents default to `ALLOWLIST`. Example:

```text
LegalResearchAgent:   ALLOWLIST
BuildAgent:           PRINCIPAL_ONLY (or engineering operator)
PublicEducationAgent: CHANNEL_ADMINS
```

## Memory Modes (directive §XXXV)

- `NONE` — no memory write
- `SESSION` — temporary activation memory only (default)
- `CHANNEL` — structured channel-local facts (CF-2)
- `OMNIBRAIN_CANDIDATE` — propose durable memory through governance
  (CF-2, interface only in CF-1)

No silent memory mutation. Candidates require provenance +
classification + validator + commit.

## Hard Scope (directive §XIII)

Every persistent agent carries an `AgentBehaviorContract`:
mission, allowed/forbidden capabilities, accepted event types,
output schema, token/time/parallelism bounds, authority class,
versioned + hashed. Enforced structurally, not via prompts.
