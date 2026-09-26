# Cross-process agent messaging

SintraPrime-Unified provides two A2A transports:

- **Memory (default):** `orchestration.a2a_protocol.A2AProtocol`, for embedded agents in one Python process and unit tests.
- **Redis:** `orchestration.redis_a2a.RedisA2ATransport`, for agents running in separate processes or containers.

## Enable Redis delivery

Set the following environment variables for the orchestration API and every agent client:

```bash
export A2A_BACKEND=redis
export REDIS_URL=redis://localhost:6379/0
# Optional; use a distinct value per environment/tenant boundary.
export A2A_REDIS_NAMESPACE=sintraprime:a2a
```

The API exposes:

- `POST /orchestration/agents/message` — enqueue a direct message.
- `GET /orchestration/agents/{agent_id}/messages/receive?timeout=5` — long-poll one message (0–30 seconds).
- `GET /orchestration/agents/registry` — inspect agents registered in the in-process registry.

Example:

```bash
curl -X POST http://localhost:8000/orchestration/agents/message \
  -H 'Content-Type: application/json' \
  -d '{
    "from_agent": "research",
    "to_agent": "drafting",
    "message_type": "DELEGATION",
    "payload": {"case_id": "C-001", "task": "draft_trust_memo"},
    "priority": "HIGH",
    "ttl": 300,
    "headers": {"trace_id": "run-123"}
  }'

curl 'http://localhost:8000/orchestration/agents/drafting/messages/receive?timeout=10'
```

Every message includes a unique `message_id`, a `correlation_id` for request/response pairing, sender and recipient IDs, priority, optional TTL, and extensible headers. Expired messages are discarded on receive.

## Agent-side usage

For a Python agent, use the transport directly:

```python
from orchestration.a2a_protocol import Message, MessageType
from orchestration.redis_a2a import RedisA2ATransport

transport = RedisA2ATransport()
await transport.send(Message(
    from_agent="research",
    to_agent="drafting",
    message_type=MessageType.REQUEST,
    payload={"question": "..."},
))
message = await transport.receive("research", timeout=10)
```

Redis lists provide at-least-once queue delivery. Consumers should make handlers idempotent using `message_id` or an application-level idempotency key. The HTTP endpoint should be placed behind the project’s existing authentication and tenant boundary before exposing it outside a trusted internal network.
