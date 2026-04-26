"""Coordinate multiple agents working on a shared task."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .message_types import AgentMessage, MessageType


class SwarmStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    VOTING = "voting"
    CONSENSUS = "consensus"
    FAILED = "failed"
    DISSOLVED = "dissolved"


@dataclass
class SwarmMember:
    agent_id: str
    joined_at: float = field(default_factory=time.time)
    vote: Optional[dict] = None
    result: Optional[dict] = None
    status: str = "active"


@dataclass
class Swarm:
    swarm_id: str
    task: dict
    members: dict[str, SwarmMember] = field(default_factory=dict)
    status: SwarmStatus = SwarmStatus.PENDING
    created_at: float = field(default_factory=time.time)
    consensus_result: Optional[dict] = None
    votes: list[dict] = field(default_factory=list)


class SwarmOrchestrator:
    """
    Spawns and coordinates agent swarms for complex tasks.
    Implements the parliament voting system for consensus.

    Use cases
    ---------
    - Complex legal research (multiple agents, each researching different aspects)
    - Document review (agents split the work)
    - Case strategy (agents propose and vote on strategy)
    - Financial analysis (parallel analysis of different accounts)

    Voting / consensus
    ------------------
    Each swarm member submits a ``SWARM_VOTE`` message with a result payload.
    The orchestrator collects votes and applies a **weighted majority** algorithm:

    1. Identical payloads accumulate weight.
    2. The payload with the highest total weight is chosen.
    3. Ties are broken by the average confidence score in the payload.

    Example
    -------
    ::

        orch = SwarmOrchestrator(node)

        swarm_id = await orch.spawn_swarm(
            task={"type": "legal_research", "statute": "42 U.S.C. § 1983"},
            swarm_size=3,
        )
        result = await orch.wait_for_consensus(swarm_id, timeout=60)
        print(result)
    """

    def __init__(self, node: Any) -> None:
        """
        Parameters
        ----------
        node:
            The :class:`AgentNode` that this orchestrator belongs to.
        """
        self.node = node
        self._swarms: dict[str, Swarm] = {}
        self._consensus_futures: dict[str, asyncio.Future] = {}
        self.logger = logging.getLogger(f"SwarmOrchestrator:{node.agent_id}")
        self._register_handlers()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def spawn_swarm(
        self, task: dict, swarm_size: int = 5
    ) -> str:
        """
        Spawn a swarm of agents for a task.

        Sends SWARM_TASK to the *swarm_size* most-capable peers and creates a
        local tracking record.

        Returns
        -------
        str
            Unique swarm ID for use with :meth:`wait_for_consensus`.
        """
        swarm_id = str(uuid.uuid4())
        swarm = Swarm(swarm_id=swarm_id, task=task)
        swarm.status = SwarmStatus.ACTIVE
        self._swarms[swarm_id] = swarm

        # Pick peers (up to swarm_size - 1; we ourselves participate too)
        peers = list(self.node.peers.keys())[: max(1, swarm_size - 1)]

        # Add ourselves as a member
        swarm.members[self.node.agent_id] = SwarmMember(
            agent_id=self.node.agent_id
        )

        for peer_id in peers:
            swarm.members[peer_id] = SwarmMember(agent_id=peer_id)
            msg = AgentMessage(
                type=MessageType.SWARM_TASK,
                sender_id=self.node.agent_id,
                payload={
                    "swarm_id": swarm_id,
                    "task": task,
                    "expected_members": len(peers) + 1,
                },
                target_id=peer_id,
            )
            await self.node.send(msg)

        self.logger.info(
            "Spawned swarm %s with %d member(s) for task type '%s'.",
            swarm_id,
            len(swarm.members),
            task.get("type", "unknown"),
        )
        return swarm_id

    async def submit_vote(self, swarm_id: str, result: dict) -> None:
        """Submit this agent's vote / result for a swarm task."""
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            self.logger.warning("Unknown swarm: %s", swarm_id)
            return

        vote_msg = AgentMessage(
            type=MessageType.SWARM_VOTE,
            sender_id=self.node.agent_id,
            payload={"swarm_id": swarm_id, "result": result},
        )
        await self.node.send(vote_msg)
        swarm.votes.append({"agent_id": self.node.agent_id, "result": result})

        # Check if we have enough votes locally
        self._try_resolve_consensus(swarm_id)

    async def wait_for_consensus(
        self, swarm_id: str, timeout: int = 60
    ) -> Optional[dict]:
        """
        Block until the swarm reaches consensus, then return the result.

        Returns *None* on timeout or failure.
        """
        if swarm_id not in self._swarms:
            return None

        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._consensus_futures[swarm_id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self.logger.warning(
                "Swarm %s consensus timed out after %ds.", swarm_id, timeout
            )
            swarm = self._swarms.get(swarm_id)
            if swarm:
                swarm.status = SwarmStatus.FAILED
            return None
        finally:
            self._consensus_futures.pop(swarm_id, None)

    async def get_swarm_status(self, swarm_id: str) -> dict:
        """Return a status dictionary for a running swarm."""
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return {"error": "unknown_swarm", "swarm_id": swarm_id}

        return {
            "swarm_id": swarm_id,
            "status": swarm.status.value,
            "task_type": swarm.task.get("type", "unknown"),
            "members": list(swarm.members.keys()),
            "votes_received": len(swarm.votes),
            "expected_votes": len(swarm.members),
            "consensus_result": swarm.consensus_result,
            "age_seconds": time.time() - swarm.created_at,
        }

    async def dissolve_swarm(self, swarm_id: str) -> None:
        """Cleanly shut down a swarm by notifying all members."""
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return

        swarm.status = SwarmStatus.DISSOLVED

        for peer_id in swarm.members:
            if peer_id == self.node.agent_id:
                continue
            msg = AgentMessage(
                type=MessageType.SWARM_LEAVE,
                sender_id=self.node.agent_id,
                payload={"swarm_id": swarm_id, "reason": "orchestrator_dissolved"},
                target_id=peer_id,
            )
            await self.node.send(msg)

        self.logger.info("Dissolved swarm %s.", swarm_id)

    # ------------------------------------------------------------------
    # Consensus algorithm
    # ------------------------------------------------------------------

    def _try_resolve_consensus(self, swarm_id: str) -> None:
        """Attempt to resolve consensus if enough votes have arrived."""
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return

        expected = len(swarm.members)
        received = len(swarm.votes)

        # Require simple majority
        if received < max(1, (expected + 1) // 2):
            return

        # Weighted majority: group identical results
        tally: dict[str, dict] = {}  # canonical_key -> {count, result, confidence}
        for vote in swarm.votes:
            result = vote.get("result", {})
            # Use sorted JSON as grouping key (ignore field order)
            import json
            key = json.dumps(result, sort_keys=True)
            if key not in tally:
                tally[key] = {"count": 0, "result": result, "confidence": 0.0}
            tally[key]["count"] += 1
            tally[key]["confidence"] += result.get("confidence", 1.0)

        # Pick winner
        winner = max(tally.values(), key=lambda x: (x["count"], x["confidence"]))
        consensus = {
            **winner["result"],
            "_swarm_id": swarm_id,
            "_votes": received,
            "_consensus_count": winner["count"],
            "_avg_confidence": winner["confidence"] / winner["count"],
        }

        swarm.consensus_result = consensus
        swarm.status = SwarmStatus.CONSENSUS
        self.logger.info(
            "Swarm %s reached consensus (%d/%d votes).", swarm_id, winner["count"], received
        )

        # Resolve waiting future
        fut = self._consensus_futures.get(swarm_id)
        if fut and not fut.done():
            fut.set_result(consensus)

        # Broadcast SWARM_CONSENSUS
        asyncio.ensure_future(self._broadcast_consensus(swarm_id, consensus))

    async def _broadcast_consensus(self, swarm_id: str, consensus: dict) -> None:
        msg = AgentMessage(
            type=MessageType.SWARM_CONSENSUS,
            sender_id=self.node.agent_id,
            payload={"swarm_id": swarm_id, "consensus": consensus},
        )
        await self.node.send(msg)

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    def _register_handlers(self) -> None:
        """Register swarm-related message handlers on the node."""

        async def on_swarm_task(msg: AgentMessage) -> None:
            swarm_id = msg.payload.get("swarm_id")
            task = msg.payload.get("task", {})
            if not swarm_id:
                return

            if swarm_id not in self._swarms:
                swarm = Swarm(swarm_id=swarm_id, task=task)
                swarm.status = SwarmStatus.ACTIVE
                self._swarms[swarm_id] = swarm

            # Send join confirmation
            join_msg = msg.make_reply(
                self.node.agent_id,
                {"swarm_id": swarm_id, "status": "joined"},
                MessageType.SWARM_JOIN,
            )
            await self.node.send(join_msg)
            self.logger.info("Joined swarm %s.", swarm_id)

        async def on_swarm_vote(msg: AgentMessage) -> None:
            swarm_id = msg.payload.get("swarm_id")
            result = msg.payload.get("result", {})
            swarm = self._swarms.get(swarm_id)
            if not swarm:
                return
            # Record the vote
            if not any(v["agent_id"] == msg.sender_id for v in swarm.votes):
                swarm.votes.append({"agent_id": msg.sender_id, "result": result})
                if msg.sender_id in swarm.members:
                    swarm.members[msg.sender_id].vote = result
                self._try_resolve_consensus(swarm_id)

        async def on_swarm_consensus(msg: AgentMessage) -> None:
            swarm_id = msg.payload.get("swarm_id")
            consensus = msg.payload.get("consensus", {})
            swarm = self._swarms.get(swarm_id)
            if swarm:
                swarm.consensus_result = consensus
                swarm.status = SwarmStatus.CONSENSUS
            fut = self._consensus_futures.get(swarm_id)
            if fut and not fut.done():
                fut.set_result(consensus)

        async def on_swarm_leave(msg: AgentMessage) -> None:
            swarm_id = msg.payload.get("swarm_id")
            swarm = self._swarms.get(swarm_id)
            if swarm and msg.sender_id in swarm.members:
                swarm.members[msg.sender_id].status = "left"
                self.logger.info(
                    "Peer %s left swarm %s.", msg.sender_id, swarm_id
                )

        self.node.handlers.setdefault(MessageType.SWARM_TASK, []).append(on_swarm_task)
        self.node.handlers.setdefault(MessageType.SWARM_VOTE, []).append(on_swarm_vote)
        self.node.handlers.setdefault(MessageType.SWARM_CONSENSUS, []).append(on_swarm_consensus)
        self.node.handlers.setdefault(MessageType.SWARM_LEAVE, []).append(on_swarm_leave)
