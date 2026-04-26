# SintraPrime Agent Network — Setup Guide

> **"One for all and all for one"** — the SintraPrime cross-machine collaboration protocol.

Multiple SintraPrime instances can discover each other, share legal knowledge, delegate tasks, and coordinate as a swarm — all with zero central infrastructure required.

---

## Quick Start: Connect Two SintraPrime Instances

### Machine A (first instance)

```bash
SINTRA_AGENT_ID=sintra-alpha \
SINTRA_AGENT_PORT=9876 \
python -m sintra --agent-mode
```

### Machine B (second instance — points at Machine A)

```bash
SINTRA_AGENT_ID=sintra-beta \
SINTRA_AGENT_PORT=9876 \
SINTRA_PEERS=192.168.1.100:9876 \
python -m sintra --agent-mode
```

Both agents will automatically:
1. Exchange `HELLO` messages and register each other as peers
2. Sync shared memory (legal knowledge, case outcomes, trust templates)
3. Be ready to delegate tasks and collaborate on swarm queries

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SINTRA_AGENT_ID` | Unique identifier for this agent instance | `sintra-{hostname}` |
| `SINTRA_AGENT_PORT` | UDP port to listen on | `9876` |
| `SINTRA_PEERS` | Comma-separated list of known peer addresses (`host:port`) | *(empty)* |
| `SINTRA_REGISTRY_URL` | Central registry HTTP URL (optional) | *(empty)* |
| `SINTRA_ENABLE_SWARMS` | Enable swarm coordination | `true` |

---

## Discovery Mechanisms

### 1. UDP Broadcast (LAN — Zero Config)

On startup each agent broadcasts a `HELLO` message on `255.255.255.255:9877`.  
All agents on the same LAN subnet will automatically discover each other.

### 2. Manual Peer List (`SINTRA_PEERS`)

```bash
SINTRA_PEERS=10.0.1.5:9876,10.0.1.6:9876,vpn-server.example.com:9876
```

Use this for cross-subnet communication (VPN, WAN, Docker networks).

### 3. Central Registry (`SINTRA_REGISTRY_URL`)

Deploy a simple HTTP registry and point all agents at it:

```bash
SINTRA_REGISTRY_URL=https://registry.sintra.internal
```

The registry exposes:
- `POST /agents` — register agent
- `GET /agents` — list all registered agents

### 4. mDNS (`_sintra._tcp.local`)

Install `zeroconf` for automatic mDNS discovery:

```bash
pip install zeroconf
```

Agents advertise as `_sintra._tcp.local` and are discovered without any configuration.

---

## Programmatic Usage

### Basic Node

```python
import asyncio
from agent_protocol import AgentNode, AgentNetwork
from agent_protocol.message_types import AgentCapabilities, MessageType, AgentMessage

async def main():
    caps = AgentCapabilities(trust_law=True, legal_intelligence=True)
    node = AgentNode("sintra-alpha", caps)

    # Register a handler for incoming legal queries
    @node.on(MessageType.LEGAL_QUERY)
    async def handle_legal_query(msg: AgentMessage):
        print(f"Legal query from {msg.sender_id}: {msg.payload['question']}")
        reply = msg.make_reply(
            node.agent_id,
            {"answer": "Based on 18 U.S.C. § 1341..."},
            MessageType.LEGAL_RESPONSE,
        )
        await node.send(reply)

    await node.start()
    # Keep running
    await asyncio.sleep(3600)

asyncio.run(main())
```

### High-Level Network Facade

```python
from agent_protocol import AgentNetwork
from agent_protocol.message_types import AgentCapabilities

async def main():
    network = AgentNetwork(
        "sintra-alpha",
        AgentCapabilities(trust_law=True, case_law=True)
    )
    await network.start()

    # Share a case outcome with all peers
    await network.memory.set(
        "case_2024_wire_fraud_outcome",
        {"verdict": "guilty", "statute": "18 U.S.C. § 1343"},
        category="case_outcomes",
    )

    # Spawn a swarm to research a statute
    swarm_id = await network.swarm.spawn_swarm(
        {"type": "legal_research", "statute": "42 U.S.C. § 1983"},
        swarm_size=5,
    )
    result = await network.swarm.wait_for_consensus(swarm_id, timeout=60)
    print("Swarm consensus:", result)

    await network.stop()

asyncio.run(main())
```

### Task Delegation

```python
# Delegate a trust analysis to the best available peer
result = await node.delegate_task(
    {"type": "trust_analysis", "document": trust_deed_text},
    required_capability="trust_law",
)
if result:
    print("Analysis:", result["analysis"])
else:
    print("No capable peer available.")
```

### Knowledge Sharing

```python
# Ask all peers what they know about a topic
responses = await node.request_knowledge("UCC Article 9", timeout=5)
for resp in responses:
    print(resp)
```

---

## Swarm Coordination (Parliament Voting)

Swarms implement a parliament-style voting system:

1. **Orchestrator** broadcasts `SWARM_TASK` to selected peers.
2. Each member works independently and submits a `SWARM_VOTE`.
3. The orchestrator applies **weighted majority** (identical results accumulate weight; ties broken by confidence score).
4. `SWARM_CONSENSUS` is broadcast when majority is reached.

```python
# Spawn 5 agents to analyze a complex contract
swarm_id = await network.swarm.spawn_swarm(
    {
        "type": "contract_analysis",
        "document_url": "s3://sintra/contracts/trust_deed_2024.pdf",
        "aspects": ["validity", "breach_risk", "applicable_law"],
    },
    swarm_size=5,
)

status = await network.swarm.get_swarm_status(swarm_id)
print(f"Swarm members: {status['members']}")
print(f"Votes received: {status['votes_received']}/{status['expected_votes']}")

consensus = await network.swarm.wait_for_consensus(swarm_id, timeout=120)
if consensus:
    print("Contract analysis consensus:", consensus)
```

---

## Shared Memory Categories

| Category | Contents |
|---|---|
| `general` | Miscellaneous shared data |
| `legal_knowledge` | Statutes, regulations, legal principles |
| `case_outcomes` | Historical case results for learning |
| `trust_templates` | Reusable trust document templates |
| `precedents` | Found legal precedents |
| `banking` | Financial / banking knowledge |
| `federal` | Federal agency data |

---

## Security Considerations

- All UDP traffic is **cleartext** — use a VPN (WireGuard, Tailscale) for production deployments across untrusted networks.
- Agents do **not** authenticate each other by default. Add a shared-secret HMAC layer via a custom message handler for environments requiring authentication.
- The `shared_memory.json` file is readable by all local users — restrict filesystem permissions as needed.

---

## Running the Test Suite

```bash
cd /agent/home/SintraPrime-Unified
python -m pytest agent_protocol/tests/ -v
```

All tests use mocked sockets — no network access required.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        AgentNetwork                             │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────┐  │
│  │  AgentNode   │  │  SharedMemory │  │  SwarmOrchestrator  │  │
│  │  (UDP I/O)   │  │  (gossip KV)  │  │  (parliament vote)  │  │
│  └──────┬───────┘  └───────────────┘  └─────────────────────┘  │
│         │          ┌───────────────┐  ┌─────────────────────┐  │
│         │          │  MessageBus   │  │   AgentDiscovery    │  │
│         │          │  (local pub)  │  │  (UDP/mDNS/reg)     │  │
│         │          └───────────────┘  └─────────────────────┘  │
└─────────┼───────────────────────────────────────────────────────┘
          │  UDP 9876
   ┌──────┴──────┐
   │  Network    │  (LAN broadcast, VPN, WAN)
   └──────┬──────┘
          │
   ┌──────┴──────────────────────────────┐
   │         Other SintraPrime Nodes     │
   │  sintra-beta  sintra-gamma  ...     │
   └─────────────────────────────────────┘
```

---

*SintraPrime Agent Protocol v1.0.0 — Sierra-5 Cross-Machine Communication*
