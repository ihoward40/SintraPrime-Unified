"""
SintraPrime Agent Protocol
==========================

Cross-machine agent communication protocol enabling multiple SintraPrime
instances to communicate, share knowledge, and collaborate — the
"one for all and all for one" network.

Quick start
-----------
::

    from agent_protocol import AgentNode, AgentNetwork, MessageBus
    from agent_protocol import SharedMemory, AgentDiscovery, SwarmOrchestrator
    from agent_protocol.message_types import AgentCapabilities, MessageType

    caps = AgentCapabilities(trust_law=True, legal_intelligence=True)
    node = AgentNode("sintra-alpha", caps)

    @node.on(MessageType.LEGAL_QUERY)
    async def handle_legal_query(msg):
        ...

    import asyncio
    asyncio.run(node.start())
"""

from .agent_node import AgentNode
from .agent_discovery import AgentDiscovery
from .message_bus import MessageBus
from .message_types import (
    AgentCapabilities,
    AgentMessage,
    MessageType,
)
from .shared_memory import SharedMemory
from .swarm_orchestrator import SwarmOrchestrator


class AgentNetwork:
    """
    High-level facade that wires together all protocol components.

    Typical usage
    -------------
    ::

        network = AgentNetwork("sintra-alpha",
                               AgentCapabilities(trust_law=True))
        await network.start()

        # Share knowledge
        await network.memory.set("latest_case", {...}, category="case_outcomes")

        # Delegate a task
        result = await network.node.delegate_task(
            {"type": "precedent_search", "statute": "18 U.S.C. § 1341"},
            required_capability="case_law",
        )

        # Spawn a research swarm
        swarm_id = await network.swarm.spawn_swarm(
            {"type": "legal_research", "topic": "wire fraud elements"},
            swarm_size=5,
        )
        consensus = await network.swarm.wait_for_consensus(swarm_id)
    """

    def __init__(
        self,
        agent_id: str,
        capabilities: AgentCapabilities,
        port: int = AgentNode.DEFAULT_PORT,
        host: str = "0.0.0.0",
    ) -> None:
        self.agent_id = agent_id
        self.node = AgentNode(agent_id, capabilities, port=port, host=host)
        self.bus = MessageBus()
        self.memory = SharedMemory(agent_id)
        self.discovery = AgentDiscovery(agent_id, capabilities, port=port)
        self.swarm = SwarmOrchestrator(self.node)

    async def start(self) -> None:
        """Start all components."""
        await self.bus.start()
        await self.node.start()
        # Discover and connect to known peers
        peers = await self.discovery.discover_all()
        for peer in peers:
            if peer.get("addr") and peer.get("port"):
                # Trigger a direct HELLO to the discovered peer
                from .message_types import AgentMessage, MessageType
                msg = AgentMessage(
                    type=MessageType.HELLO,
                    sender_id=self.agent_id,
                    payload={
                        "port": self.node.port,
                        "capabilities": self.node.capabilities.to_dict(),
                    },
                )
                await self.node.send(msg, (peer["addr"], peer["port"]))

    async def stop(self) -> None:
        """Stop all components."""
        await self.node.stop()
        await self.bus.stop()


__all__ = [
    "AgentNode",
    "AgentNetwork",
    "MessageBus",
    "SharedMemory",
    "AgentDiscovery",
    "SwarmOrchestrator",
    "AgentCapabilities",
    "AgentMessage",
    "MessageType",
]

__version__ = "1.0.0"
__author__ = "SintraPrime Team"
