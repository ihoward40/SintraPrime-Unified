"""
Test suite for the SintraPrime Agent Communication Protocol.

30+ tests covering:
- Message serialization / deserialization
- AgentNode creation and handler registration
- SharedMemory CRUD and conflict resolution
- SwarmOrchestrator creation and consensus
- AgentDiscovery peer-env parsing
- MessageBus pub/sub
- AgentNetwork facade

All tests use mocked sockets — no actual network required.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Allow running from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agent_protocol.message_types import (
    AgentCapabilities,
    AgentMessage,
    MessageType,
)
from agent_protocol.agent_node import AgentNode
from agent_protocol.shared_memory import SharedMemory
from agent_protocol.swarm_orchestrator import SwarmOrchestrator, SwarmStatus
from agent_protocol.agent_discovery import AgentDiscovery
from agent_protocol.message_bus import MessageBus
from agent_protocol import AgentNetwork


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_caps(**kwargs) -> AgentCapabilities:
    return AgentCapabilities(**kwargs)


def make_node(agent_id: str = "test-node", **cap_kwargs) -> AgentNode:
    caps = make_caps(**cap_kwargs)
    node = AgentNode(agent_id, caps)
    # Inject a mock transport so send() doesn't need a real socket
    node._udp_transport = MagicMock()
    node._udp_transport.sendto = MagicMock()
    node.running = True
    return node


def run(coro):
    """Run a coroutine in a temporary event loop."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# 1. Message Types
# ---------------------------------------------------------------------------

class TestMessageType(unittest.TestCase):

    def test_all_message_types_have_values(self):
        for mt in MessageType:
            self.assertIsInstance(mt.value, str)

    def test_hello_value(self):
        self.assertEqual(MessageType.HELLO.value, "hello")

    def test_legal_query_value(self):
        self.assertEqual(MessageType.LEGAL_QUERY.value, "legal_query")

    def test_swarm_vote_value(self):
        self.assertEqual(MessageType.SWARM_VOTE.value, "swarm_vote")


# ---------------------------------------------------------------------------
# 2. AgentMessage Serialization
# ---------------------------------------------------------------------------

class TestAgentMessageSerialization(unittest.TestCase):

    def _make_msg(self, **kwargs) -> AgentMessage:
        return AgentMessage(
            type=MessageType.HELLO,
            sender_id="sintra-alpha",
            payload={"port": 9876, "capabilities": {}},
            **kwargs,
        )

    def test_to_json_returns_string(self):
        msg = self._make_msg()
        self.assertIsInstance(msg.to_json(), str)

    def test_to_json_contains_type(self):
        msg = self._make_msg()
        d = json.loads(msg.to_json())
        self.assertEqual(d["type"], "hello")

    def test_from_json_round_trip(self):
        msg = self._make_msg()
        restored = AgentMessage.from_json(msg.to_json())
        self.assertEqual(restored.type, msg.type)
        self.assertEqual(restored.sender_id, msg.sender_id)
        self.assertEqual(restored.message_id, msg.message_id)
        self.assertAlmostEqual(restored.timestamp, msg.timestamp, places=3)

    def test_from_json_payload_preserved(self):
        msg = self._make_msg()
        restored = AgentMessage.from_json(msg.to_json())
        self.assertEqual(restored.payload["port"], 9876)

    def test_target_id_serialization(self):
        msg = self._make_msg(target_id="sintra-beta")
        restored = AgentMessage.from_json(msg.to_json())
        self.assertEqual(restored.target_id, "sintra-beta")

    def test_is_expired_false_for_fresh(self):
        msg = self._make_msg()
        self.assertFalse(msg.is_expired())

    def test_is_expired_true_for_old(self):
        msg = self._make_msg()
        msg.timestamp = time.time() - 60
        msg.ttl = 30
        self.assertTrue(msg.is_expired())

    def test_make_reply(self):
        original = self._make_msg()
        reply = original.make_reply("sintra-beta", {"answer": "yes"}, MessageType.LEGAL_RESPONSE)
        self.assertEqual(reply.sender_id, "sintra-beta")
        self.assertEqual(reply.target_id, "sintra-alpha")
        self.assertEqual(reply.reply_to, original.message_id)
        self.assertEqual(reply.type, MessageType.LEGAL_RESPONSE)

    def test_repr_contains_type(self):
        msg = self._make_msg()
        self.assertIn("hello", repr(msg))

    def test_unique_message_ids(self):
        ids = {AgentMessage(type=MessageType.PING, sender_id="x", payload={}).message_id
               for _ in range(100)}
        self.assertEqual(len(ids), 100)


# ---------------------------------------------------------------------------
# 3. AgentCapabilities
# ---------------------------------------------------------------------------

class TestAgentCapabilities(unittest.TestCase):

    def test_default_all_false(self):
        caps = AgentCapabilities()
        self.assertFalse(caps.trust_law)
        self.assertFalse(caps.legal_intelligence)

    def test_has_capability(self):
        caps = AgentCapabilities(trust_law=True)
        self.assertTrue(caps.has("trust_law"))
        self.assertFalse(caps.has("banking"))

    def test_list_active(self):
        caps = AgentCapabilities(trust_law=True, voice=True)
        active = caps.list_active()
        self.assertIn("trust_law", active)
        self.assertIn("voice", active)
        self.assertNotIn("banking", active)

    def test_to_dict_and_from_dict(self):
        caps = AgentCapabilities(rag=True, local_llm=True)
        d = caps.to_dict()
        restored = AgentCapabilities.from_dict(d)
        self.assertTrue(restored.rag)
        self.assertTrue(restored.local_llm)
        self.assertFalse(restored.trust_law)

    def test_from_dict_ignores_unknown_keys(self):
        caps = AgentCapabilities.from_dict({"trust_law": True, "unknown_key": True})
        self.assertTrue(caps.trust_law)


# ---------------------------------------------------------------------------
# 4. AgentNode
# ---------------------------------------------------------------------------

class TestAgentNode(unittest.TestCase):

    def test_node_creation(self):
        node = make_node("alpha")
        self.assertEqual(node.agent_id, "alpha")
        self.assertEqual(node.port, AgentNode.DEFAULT_PORT)

    def test_custom_port(self):
        caps = make_caps()
        node = AgentNode("beta", caps, port=12345)
        self.assertEqual(node.port, 12345)

    def test_handler_registration_via_decorator(self):
        node = make_node()

        @node.on(MessageType.LEGAL_QUERY)
        async def handler(msg):
            pass

        self.assertIn(MessageType.LEGAL_QUERY, node.handlers)
        self.assertIn(handler, node.handlers[MessageType.LEGAL_QUERY])

    def test_multiple_handlers_same_type(self):
        node = make_node()

        @node.on(MessageType.PING)
        async def h1(msg):
            pass

        @node.on(MessageType.PING)
        async def h2(msg):
            pass

        self.assertEqual(len(node.handlers[MessageType.PING]), 2)

    def test_get_best_peer_for_no_peers(self):
        node = make_node()
        self.assertIsNone(node.get_best_peer_for("trust_law"))

    def test_get_best_peer_for_with_matching_peer(self):
        node = make_node()
        node.peers["peer-beta"] = {
            "addr": "10.0.0.2",
            "port": 9876,
            "capabilities": {"trust_law": True},
            "last_seen": time.time(),
        }
        result = node.get_best_peer_for("trust_law")
        self.assertEqual(result, "peer-beta")

    def test_get_best_peer_for_no_matching_capability(self):
        node = make_node()
        node.peers["peer-gamma"] = {
            "capabilities": {"banking": True},
            "last_seen": time.time(),
        }
        self.assertIsNone(node.get_best_peer_for("trust_law"))

    def test_known_peers_empty(self):
        node = make_node()
        self.assertEqual(node.known_peers(), [])

    def test_known_peers_with_peers(self):
        node = make_node()
        node.peers["alpha"] = {}
        node.peers["beta"] = {}
        self.assertCountEqual(node.known_peers(), ["alpha", "beta"])

    def test_send_broadcasts_without_target(self):
        node = make_node()
        msg = AgentMessage(
            type=MessageType.PING,
            sender_id=node.agent_id,
            payload={},
        )
        run(node.send(msg))
        node._udp_transport.sendto.assert_called()

    def test_send_unicast_to_known_peer(self):
        node = make_node()
        node.peers["peer-x"] = {"addr": "192.168.1.5", "port": 9876}
        msg = AgentMessage(
            type=MessageType.PING,
            sender_id=node.agent_id,
            payload={},
            target_id="peer-x",
        )
        run(node.send(msg))
        call_args = node._udp_transport.sendto.call_args
        self.assertIn(("192.168.1.5", 9876), call_args[0])


# ---------------------------------------------------------------------------
# 5. SharedMemory
# ---------------------------------------------------------------------------

class TestSharedMemory(unittest.TestCase):

    def setUp(self):
        # Patch disk I/O
        self.patcher = patch.object(SharedMemory, "_save_to_disk", return_value=None)
        self.patcher.start()
        self.patcher2 = patch.object(SharedMemory, "_load_from_disk", return_value=None)
        self.patcher2.start()
        self.mem = SharedMemory("test-node")

    def tearDown(self):
        self.patcher.stop()
        self.patcher2.stop()

    def test_set_and_get(self):
        run(self.mem.set("foo", "bar"))
        result = run(self.mem.get("foo"))
        self.assertEqual(result, "bar")

    def test_get_missing_key(self):
        result = run(self.mem.get("nonexistent"))
        self.assertIsNone(result)

    def test_set_updates_existing(self):
        run(self.mem.set("x", 1))
        run(self.mem.set("x", 2))
        result = run(self.mem.get("x"))
        self.assertEqual(result, 2)

    def test_get_category(self):
        run(self.mem.set("k1", "v1", category="legal_knowledge"))
        run(self.mem.set("k2", "v2", category="case_outcomes"))
        legal = run(self.mem.get_category("legal_knowledge"))
        self.assertIn("k1", legal)
        self.assertNotIn("k2", legal)

    def test_delete_existing_key(self):
        run(self.mem.set("del_me", 42))
        deleted = run(self.mem.delete("del_me"))
        self.assertTrue(deleted)
        self.assertIsNone(run(self.mem.get("del_me")))

    def test_delete_nonexistent_key(self):
        deleted = run(self.mem.delete("not_here"))
        self.assertFalse(deleted)

    def test_keys(self):
        run(self.mem.set("a", 1))
        run(self.mem.set("b", 2))
        keys = run(self.mem.keys())
        self.assertCountEqual(keys, ["a", "b"])

    def test_len(self):
        run(self.mem.set("p", 1))
        run(self.mem.set("q", 2))
        self.assertEqual(len(self.mem), 2)

    def test_contains(self):
        run(self.mem.set("z", 99))
        self.assertIn("z", self.mem)
        self.assertNotIn("nope", self.mem)

    def test_sync_with_peer_imports_new_keys(self):
        peer_store = {
            "remote_key": {
                "value": "remote_value",
                "category": "general",
                "author": "peer",
                "ts": time.time(),
                "version": 1,
            }
        }
        updated = run(self.mem.sync_with_peer("peer-1", peer_store))
        self.assertEqual(updated, 1)
        self.assertEqual(run(self.mem.get("remote_key")), "remote_value")

    def test_sync_with_peer_last_write_wins(self):
        """Local value should NOT be overwritten if it is newer."""
        run(self.mem.set("shared", "local_value"))
        peer_store = {
            "shared": {
                "value": "old_peer_value",
                "category": "general",
                "author": "peer",
                "ts": time.time() - 100,  # older
                "version": 1,
            }
        }
        run(self.mem.sync_with_peer("peer-1", peer_store))
        self.assertEqual(run(self.mem.get("shared")), "local_value")

    def test_snapshot_returns_copy(self):
        run(self.mem.set("snap", "shot"))
        snap = self.mem.snapshot()
        self.assertIn("snap", snap)

    def test_unknown_category_defaults_to_general(self):
        run(self.mem.set("k", "v", category="unknown_category"))
        result = run(self.mem.get_category("general"))
        self.assertIn("k", result)


# ---------------------------------------------------------------------------
# 6. SwarmOrchestrator
# ---------------------------------------------------------------------------

class TestSwarmOrchestrator(unittest.TestCase):

    def setUp(self):
        self.node = make_node("orchestrator-node")
        self.orch = SwarmOrchestrator(self.node)

    def test_spawn_swarm_returns_id(self):
        swarm_id = run(self.orch.spawn_swarm({"type": "legal_research"}, swarm_size=1))
        self.assertIsInstance(swarm_id, str)
        self.assertIn(swarm_id, self.orch._swarms)

    def test_swarm_initial_status_active(self):
        swarm_id = run(self.orch.spawn_swarm({"type": "doc_review"}, swarm_size=1))
        status = run(self.orch.get_swarm_status(swarm_id))
        self.assertEqual(status["status"], "active")

    def test_get_swarm_status_unknown(self):
        status = run(self.orch.get_swarm_status("nonexistent-swarm"))
        self.assertIn("error", status)

    def test_consensus_with_single_member(self):
        swarm_id = run(self.orch.spawn_swarm({"type": "test"}, swarm_size=1))
        # Submit our own vote
        run(self.orch.submit_vote(swarm_id, {"conclusion": "valid", "confidence": 0.9}))
        swarm = self.orch._swarms[swarm_id]
        self.assertIsNotNone(swarm.consensus_result)
        self.assertEqual(swarm.status, SwarmStatus.CONSENSUS)

    def test_consensus_majority_wins(self):
        """Two identical votes should beat one different vote."""
        swarm_id = run(self.orch.spawn_swarm({"type": "vote_test"}, swarm_size=1))
        swarm = self.orch._swarms[swarm_id]
        # Manually add extra members
        from agent_protocol.swarm_orchestrator import SwarmMember
        swarm.members["peer-a"] = SwarmMember("peer-a")
        swarm.members["peer-b"] = SwarmMember("peer-b")
        swarm.members["peer-c"] = SwarmMember("peer-c")

        # 2 votes for "valid", 1 for "invalid"
        swarm.votes.append({"agent_id": "peer-a", "result": {"conclusion": "valid", "confidence": 0.9}})
        swarm.votes.append({"agent_id": "peer-b", "result": {"conclusion": "valid", "confidence": 0.8}})
        swarm.votes.append({"agent_id": "peer-c", "result": {"conclusion": "invalid", "confidence": 0.5}})

        self.orch._try_resolve_consensus(swarm_id)
        self.assertEqual(swarm.consensus_result["conclusion"], "valid")

    def test_dissolve_swarm(self):
        swarm_id = run(self.orch.spawn_swarm({"type": "test"}, swarm_size=1))
        run(self.orch.dissolve_swarm(swarm_id))
        swarm = self.orch._swarms[swarm_id]
        self.assertEqual(swarm.status, SwarmStatus.DISSOLVED)

    def test_swarm_handlers_registered(self):
        """Handlers must be registered on the node for swarm messages."""
        from agent_protocol.message_types import MessageType
        self.assertIn(MessageType.SWARM_TASK, self.node.handlers)
        self.assertIn(MessageType.SWARM_VOTE, self.node.handlers)
        self.assertIn(MessageType.SWARM_CONSENSUS, self.node.handlers)


# ---------------------------------------------------------------------------
# 7. AgentDiscovery
# ---------------------------------------------------------------------------

class TestAgentDiscovery(unittest.TestCase):

    def setUp(self):
        caps = AgentCapabilities(trust_law=True)
        self.disc = AgentDiscovery("sintra-test", caps, port=9876)

    def test_parse_peer_env_empty(self):
        with patch.dict("os.environ", {"SINTRA_PEERS": ""}):
            result = self.disc.parse_peer_env()
        self.assertEqual(result, [])

    def test_parse_peer_env_single(self):
        with patch.dict("os.environ", {"SINTRA_PEERS": "192.168.1.10:9876"}):
            result = self.disc.parse_peer_env()
        self.assertEqual(result, [("192.168.1.10", 9876)])

    def test_parse_peer_env_multiple(self):
        with patch.dict("os.environ", {"SINTRA_PEERS": "10.0.0.1:9876,10.0.0.2:9877"}):
            result = self.disc.parse_peer_env()
        self.assertEqual(len(result), 2)
        self.assertIn(("10.0.0.1", 9876), result)
        self.assertIn(("10.0.0.2", 9877), result)

    def test_parse_peer_env_no_port(self):
        with patch.dict("os.environ", {"SINTRA_PEERS": "myhost"}):
            result = self.disc.parse_peer_env()
        self.assertEqual(result, [("myhost", 9876)])

    def test_parse_peer_env_invalid_port(self):
        with patch.dict("os.environ", {"SINTRA_PEERS": "host:abc"}):
            result = self.disc.parse_peer_env()
        self.assertEqual(result, [])

    def test_parse_peer_env_whitespace_handling(self):
        with patch.dict("os.environ", {"SINTRA_PEERS": " 10.0.0.5 : 9900 "}):
            result = self.disc.parse_peer_env()
        self.assertEqual(result, [("10.0.0.5", 9900)])


# ---------------------------------------------------------------------------
# 8. MessageBus
# ---------------------------------------------------------------------------

class TestMessageBus(unittest.TestCase):

    def setUp(self):
        self.bus = MessageBus()

    def _make_msg(self, msg_type: MessageType) -> AgentMessage:
        return AgentMessage(type=msg_type, sender_id="test", payload={})

    def test_subscribe_and_publish(self):
        received = []

        @self.bus.subscribe(MessageType.PING)
        async def handler(msg):
            received.append(msg)

        run(self.bus.publish(self._make_msg(MessageType.PING)))
        self.assertEqual(len(received), 1)

    def test_wildcard_subscriber_receives_all(self):
        received = []

        @self.bus.subscribe()
        async def handler(msg):
            received.append(msg.type)

        run(self.bus.publish(self._make_msg(MessageType.PING)))
        run(self.bus.publish(self._make_msg(MessageType.HELLO)))
        self.assertIn(MessageType.PING, received)
        self.assertIn(MessageType.HELLO, received)

    def test_subscriber_count(self):
        @self.bus.subscribe(MessageType.PING)
        async def h1(msg): pass

        @self.bus.subscribe(MessageType.PING)
        async def h2(msg): pass

        self.assertEqual(self.bus.subscriber_count(MessageType.PING), 2)

    def test_unsubscribe(self):
        calls = []

        async def handler(msg):
            calls.append(1)

        self.bus.subscribe(MessageType.PONG)(handler)
        run(self.bus.publish(self._make_msg(MessageType.PONG)))
        self.assertEqual(len(calls), 1)

        self.bus.unsubscribe(handler, MessageType.PONG)
        run(self.bus.publish(self._make_msg(MessageType.PONG)))
        self.assertEqual(len(calls), 1)   # no new calls

    def test_clear(self):
        @self.bus.subscribe(MessageType.PING)
        async def h(msg): pass

        self.bus.clear()
        self.assertEqual(self.bus.subscriber_count(), 0)

    def test_no_handler_does_not_raise(self):
        """Publishing to a type with no subscribers should not raise."""
        run(self.bus.publish(self._make_msg(MessageType.LEGAL_QUERY)))


# ---------------------------------------------------------------------------
# 9. AgentNetwork facade
# ---------------------------------------------------------------------------

class TestAgentNetwork(unittest.TestCase):

    def test_network_creation(self):
        caps = AgentCapabilities(trust_law=True)
        net = AgentNetwork("net-alpha", caps)
        self.assertEqual(net.agent_id, "net-alpha")
        self.assertIsInstance(net.node, AgentNode)
        self.assertIsInstance(net.bus, MessageBus)
        self.assertIsInstance(net.memory, SharedMemory)
        self.assertIsInstance(net.discovery, AgentDiscovery)
        self.assertIsInstance(net.swarm, SwarmOrchestrator)

    def test_network_node_capabilities_match(self):
        caps = AgentCapabilities(rag=True, local_llm=True)
        net = AgentNetwork("net-beta", caps)
        self.assertTrue(net.node.capabilities.rag)
        self.assertTrue(net.node.capabilities.local_llm)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
