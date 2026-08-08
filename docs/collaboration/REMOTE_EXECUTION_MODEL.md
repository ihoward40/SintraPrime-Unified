# Remote Execution Model

## Stable Identity, Ephemeral Host (directive §XX–§XXII)

`AgentIdentity` belongs to SintraPrime. `ExecutionHost` is metadata.

```text
Research-Agent-7 on WORKSTATION-A today == Research-Agent-7 on WORKER-03 tomorrow
```

## Execution Flow

```text
Event → Agent Activation Request → Policy → Scheduler
→ Execution Host → Scoped Context Package → Provider
→ Structured Result → Channel
```

The agent does not care which host executed it.

## ExecutionHost (CF-1)

```text
host_id, name, host_type (LOCAL_WORKSTATION | SERVER | CONTAINER |
VPS | GPU_WORKER | CLOUD_RUNNER)
status, capabilities, last_heartbeat, resource_profile,
trust_level (UNTRUSTED..PRIVILEGED), max_concurrent_activations,
current_load
```

## CF-1 Status

Host registry + scheduler are interface-ready; remote execution is
mocked (in-process) in CF-1. The proof of host-independent identity
is covered by tests: same agent_id on host A then host B keeps
identity unchanged. Production remote worker fleet is Phase CF-2+.

## Heartbeat (directive §XCV)

Heartbeat is infrastructure health — not model invocation.
`IDLE → SLEEPING` transitions release compute; identity remains
stable. (CF-2 runtime.)
