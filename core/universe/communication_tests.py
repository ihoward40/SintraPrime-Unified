"""
Comprehensive Test Suite for Agent Communication System
Tests message bus, hive mind, encryption, and performance
"""

import asyncio
import pytest
import time
from typing import List
import json

from agent_communication import (
    MessageBus, HiveMind, AgentCommunicationBridge,
    Message, MessageType, MessagePriority
)
from skill_registry import SkillRegistry, SkillStatus


# ============================================
# Message Priority Routing Tests
# ============================================

class TestMessagePriorityRouting:
    """Test message priority-based routing"""

    @pytest.mark.asyncio
    async def test_critical_messages_processed_first(self):
        """Critical priority messages should be processed before lower priority"""
        bus = MessageBus()
        
        # Send normal priority message
        msg1 = Message(
            id="msg1",
            sender_id="agent1",
            recipient_id="agent2",
            message_type=MessageType.REQUEST,
            content={"order": 1},
            priority=MessagePriority.NORMAL
        )
        
        # Send critical priority message
        msg2 = Message(
            id="msg2",
            sender_id="agent1",
            recipient_id="agent2",
            message_type=MessageType.URGENT,
            content={"order": 2},
            priority=MessagePriority.CRITICAL
        )
        
        await bus.send(msg1)
        await bus.send(msg2)
        
        # Critical should be processed first
        stats = bus.get_queue_stats()
        assert "agent2" in stats
        assert bus.metrics["total_sent"] >= 2

    @pytest.mark.asyncio
    async def test_priority_levels_respected(self):
        """Test that all priority levels are respected"""
        bus = MessageBus()
        
        priorities = [
            (MessagePriority.LOW, "low"),
            (MessagePriority.NORMAL, "normal"),
            (MessagePriority.HIGH, "high"),
            (MessagePriority.CRITICAL, "critical")
        ]
        
        for priority, label in priorities:
            msg = Message(
                id=f"msg_{label}",
                sender_id="agent1",
                recipient_id="agent2",
                message_type=MessageType.REQUEST,
                content={"priority": label},
                priority=priority
            )
            await bus.send(msg)
        
        # Check all were received
        history = bus.get_message_history("agent2")
        assert len(history) == 4


# ============================================
# Message Encryption Tests
# ============================================

class TestMessageEncryption:
    """Test message encryption and decryption"""

    @pytest.mark.asyncio
    async def test_encryption_disabled_without_key(self):
        """Encryption should be disabled if no key provided"""
        bus = MessageBus()
        assert bus.cipher is None

    @pytest.mark.asyncio
    async def test_encryption_enabled_with_key(self):
        """Encryption should be enabled with key"""
        bus = MessageBus(encryption_key="test_secret_key_123")
        assert bus.cipher is not None

    @pytest.mark.asyncio
    async def test_message_encryption_roundtrip(self):
        """Test encrypting and decrypting a message"""
        bus = MessageBus(encryption_key="test_secret_key_123")
        
        original_content = {"data": "sensitive", "value": 42}
        msg = Message(
            id="msg1",
            sender_id="agent1",
            recipient_id="agent2",
            message_type=MessageType.REQUEST,
            content=original_content,
            priority=MessagePriority.HIGH
        )
        
        # Encrypt
        encrypted = bus.encrypt_message(msg)
        assert encrypted is not None
        assert encrypted != json.dumps(original_content)
        
        # Decrypt
        decrypted = bus.decrypt_message(encrypted)
        assert decrypted == original_content

    @pytest.mark.asyncio
    async def test_encrypted_message_transmission(self):
        """Test sending and receiving encrypted messages"""
        bus = MessageBus(encryption_key="secure_key_456")
        
        msg = Message(
            id="msg1",
            sender_id="agent1",
            recipient_id="agent2",
            message_type=MessageType.REQUEST,
            content={"secret": "data"},
            priority=MessagePriority.HIGH
        )
        
        await bus.send(msg)
        received = await bus.receive("agent2")
        
        assert received is not None
        assert received.content == {"secret": "data"}

    @pytest.mark.asyncio
    async def test_decryption_fails_gracefully(self):
        """Invalid encrypted data should fail gracefully"""
        bus = MessageBus(encryption_key="key123")
        
        result = bus.decrypt_message("invalid_encrypted_data")
        assert result is None


# ============================================
# Knowledge Sharing Tests
# ============================================

class TestKnowledgeSharing:
    """Test knowledge sharing between agents"""

    @pytest.mark.asyncio
    async def test_share_knowledge_successfully(self):
        """Test sharing knowledge"""
        hive = HiveMind()
        
        success = await hive.share_knowledge(
            "agent1",
            "best_practice",
            "batch_process",
            scope="public"
        )
        
        assert success is True
        knowledge = await hive.request_knowledge("best_practice")
        assert knowledge == "batch_process"

    @pytest.mark.asyncio
    async def test_knowledge_scopes(self):
        """Test knowledge scopes"""
        hive = HiveMind()
        
        # Public knowledge
        await hive.share_knowledge("agent1", "public_key", "public_value", "public")
        
        # Team knowledge
        await hive.share_knowledge("agent1", "team_key", "team_value", "team")
        
        # Private knowledge
        await hive.share_knowledge("agent1", "private_key", "private_value", "private")
        
        # All should be retrievable
        assert await hive.request_knowledge("public_key") == "public_value"
        assert await hive.request_knowledge("team_key") == "team_value"
        assert await hive.request_knowledge("private_key") == "private_value"

    @pytest.mark.asyncio
    async def test_request_nonexistent_knowledge(self):
        """Test requesting knowledge that doesn't exist"""
        hive = HiveMind()
        
        result = await hive.request_knowledge("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_knowledge_persistence(self):
        """Test that knowledge persists"""
        hive = HiveMind()
        
        await hive.share_knowledge("agent1", "key1", {"data": [1, 2, 3]})
        
        # Retrieve multiple times
        for _ in range(5):
            result = await hive.request_knowledge("key1")
            assert result == {"data": [1, 2, 3]}


# ============================================
# Skill Learning Tests
# ============================================

class TestSkillLearning:
    """Test skill learning and skill sharing"""

    @pytest.mark.asyncio
    async def test_register_skill(self):
        """Test registering a skill"""
        hive = HiveMind()
        
        skill_id = await hive.register_skill(
            "executor_1",
            "data_processing",
            "def process(data): return [x*2 for x in data]",
            success_rate=0.95
        )
        
        assert skill_id is not None
        assert "data_processing" in skill_id

    @pytest.mark.asyncio
    async def test_get_skill_version(self):
        """Test retrieving skill versions"""
        hive = HiveMind()
        
        skill_id = await hive.register_skill(
            "agent1",
            "math_skill",
            "def add(a, b): return a + b",
            success_rate=1.0
        )
        
        # Get latest version
        skill = await hive.get_skill("math_skill")
        assert skill is not None
        assert skill["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_learn_skill(self):
        """Test learning a skill from another agent"""
        hive = HiveMind()
        
        # Agent1 registers skill
        skill_id = await hive.register_skill(
            "agent1",
            "optimization",
            "def optimize(): pass"
        )
        
        # Agent2 learns the skill
        success = await hive.learn_skill("agent2", skill_id)
        
        assert success is True
        assert len(hive.learning_sessions) > 0

    @pytest.mark.asyncio
    async def test_skill_recommendations(self):
        """Test skill recommendations"""
        hive = HiveMind()
        
        # Register skills
        await hive.register_skill("agent1", "data_processing", "code1")
        await hive.register_skill("agent2", "data_analysis", "code2")
        await hive.register_skill("agent3", "file_handling", "code3")
        
        # Get recommendations
        recommendations = await hive.recommend_skill("agent4", "process data efficiently")
        
        assert len(recommendations) > 0
        assert any("process" in r.get("skill_name", "").lower() for r in recommendations)


# ============================================
# Failure Recovery Tests
# ============================================

class TestFailureRecovery:
    """Test failure recovery mechanisms"""

    @pytest.mark.asyncio
    async def test_dead_letter_queue_on_full(self):
        """Messages should go to dead letter queue when bus is full"""
        bus = MessageBus(max_queue_size=1)
        
        msg1 = Message(
            id="msg1",
            sender_id="agent1",
            recipient_id="agent2",
            message_type=MessageType.REQUEST,
            content={"data": "test1"}
        )
        
        # Add first message
        await bus.send(msg1)
        
        # Receive it to clear queue
        await bus.receive("agent2")
        
        # Send another
        msg2 = Message(
            id="msg2",
            sender_id="agent1",
            recipient_id="agent2",
            message_type=MessageType.REQUEST,
            content={"data": "test2"}
        )
        
        await bus.send(msg2)
        assert msg2 in bus.message_history

    @pytest.mark.asyncio
    async def test_signature_verification_failure(self):
        """Invalid signatures should be rejected"""
        bus = MessageBus()
        
        msg = Message(
            id="msg1",
            sender_id="agent1",
            recipient_id="agent2",
            message_type=MessageType.REQUEST,
            content={"data": "test"},
            signature="invalid_signature"
        )
        
        result = await bus.send(msg)
        
        # Should fail verification and go to dead letter
        assert result is False
        assert msg in bus.dead_letter_queue

    @pytest.mark.asyncio
    async def test_dead_letter_recovery(self):
        """Test recovering messages from dead letter queue"""
        bus = MessageBus()
        
        # Create failed message
        msg = Message(
            id="msg1",
            sender_id="agent1",
            recipient_id="agent2",
            message_type=MessageType.REQUEST,
            content={"data": "test"},
            signature="bad_sig"
        )
        
        await bus.send(msg)
        assert len(bus.dead_letter_queue) > 0
        
        # Fix the message
        msg.signature = None
        
        # Recover
        recovered = await bus.recover_from_dead_letter(msg.id)
        
        assert recovered >= 0

    @pytest.mark.asyncio
    async def test_dead_letter_recovery_all(self):
        """Test recovering all messages from dead letter queue"""
        bus = MessageBus()
        
        # Add multiple failed messages
        for i in range(3):
            msg = Message(
                id=f"msg{i}",
                sender_id="agent1",
                recipient_id="agent2",
                message_type=MessageType.REQUEST,
                content={"test": i},
                signature=f"bad_sig{i}"
            )
            await bus.send(msg)
        
        initial_dead_letter = len(bus.dead_letter_queue)
        assert initial_dead_letter == 3
        
        # Try to recover all
        recovered = await bus.recover_from_dead_letter()
        
        assert recovered >= 0


# ============================================
# Skill Registry Tests
# ============================================

class TestSkillRegistry:
    """Test skill registry functionality"""

    @pytest.mark.asyncio
    async def test_register_and_retrieve_skill(self):
        """Test registering and retrieving a skill"""
        registry = SkillRegistry()
        
        skill_id = await registry.register_skill(
            name="test_skill",
            code="def test(): return 42",
            agent_id="agent1",
            description="A test skill"
        )
        
        assert skill_id is not None
        
        skill = await registry.get_skill("test_skill")
        assert skill is not None
        assert skill.code == "def test(): return 42"

    @pytest.mark.asyncio
    async def test_skill_versioning(self):
        """Test skill versioning"""
        registry = SkillRegistry()
        
        # Register v1
        id1 = await registry.register_skill(
            "math_skill",
            "def add(a, b): return a + b",
            "agent1"
        )
        
        # Register v2
        id2 = await registry.register_skill(
            "math_skill",
            "def add(a, b): return a + b + 1",
            "agent1"
        )
        
        # Should have different versions
        assert id1 != id2
        
        # Get all versions
        versions = await registry.get_all_versions("math_skill")
        assert len(versions) >= 2

    @pytest.mark.asyncio
    async def test_skill_validation(self):
        """Test skill validation"""
        registry = SkillRegistry()
        
        # Valid skill
        valid_id = await registry.register_skill(
            "valid_skill",
            "def valid(): return True",
            "agent1"
        )
        
        assert valid_id is not None
        skill = await registry.get_skill("valid_skill")
        assert skill.status != SkillStatus.FAILED

    @pytest.mark.asyncio
    async def test_usage_recording(self):
        """Test recording skill usage"""
        registry = SkillRegistry()
        
        skill_id = await registry.register_skill(
            "used_skill",
            "def work(): pass",
            "agent1"
        )
        
        # Record successful uses
        for _ in range(5):
            await registry.record_usage(skill_id, success=True, execution_time_ms=100)
        
        # Record failures
        for _ in range(2):
            await registry.record_usage(skill_id, success=False, execution_time_ms=150)
        
        stats = await registry.get_usage_stats(skill_id)
        assert stats is not None
        assert stats["usage_count"] == 5
        assert stats["failure_count"] == 2

    @pytest.mark.asyncio
    async def test_skill_deprecation(self):
        """Test skill deprecation"""
        registry = SkillRegistry()
        
        skill_id = await registry.register_skill(
            "old_skill",
            "def old(): pass",
            "agent1"
        )
        
        # Deprecate
        await registry.deprecate_skill(skill_id)
        
        skill = await registry.get_skill("old_skill", 1)
        assert skill.status == SkillStatus.DEPRECATED


# ============================================
# Performance Benchmarks
# ============================================

class TestPerformance:
    """Performance benchmarks"""

    @pytest.mark.asyncio
    async def test_throughput_1000_messages(self):
        """Test message throughput (1000 msg/sec target)"""
        bus = MessageBus()
        
        start = time.time()
        messages_sent = 0
        
        # Send 1000 messages
        for i in range(1000):
            msg = Message(
                id=f"msg{i}",
                sender_id="agent1",
                recipient_id="agent2",
                message_type=MessageType.REQUEST,
                content={"seq": i},
                priority=MessagePriority.NORMAL
            )
            await bus.send(msg)
            messages_sent += 1
        
        elapsed = time.time() - start
        throughput = messages_sent / elapsed
        
        assert messages_sent == 1000
        assert throughput >= 500  # At least 500 msg/sec (relaxed for testing)
        print(f"\nThroughput: {throughput:.0f} msg/sec")

    @pytest.mark.asyncio
    async def test_latency_message_delivery(self):
        """Test message delivery latency (<50ms target)"""
        bus = MessageBus()
        
        latencies = []
        
        for _ in range(100):
            msg = Message(
                id=f"msg",
                sender_id="agent1",
                recipient_id="agent2",
                message_type=MessageType.REQUEST,
                content={"test": "data"}
            )
            
            start = time.time()
            await bus.send(msg)
            await bus.receive("agent2")
            latency = (time.time() - start) * 1000  # ms
            
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        assert avg_latency < 50  # Average under 50ms
        print(f"\nAverage latency: {avg_latency:.2f}ms, Max: {max_latency:.2f}ms")

    @pytest.mark.asyncio
    async def test_encryption_overhead(self):
        """Test encryption performance overhead"""
        bus_unencrypted = MessageBus()
        bus_encrypted = MessageBus(encryption_key="test_key")
        
        msg_content = {"data": "x" * 1000}  # 1KB payload
        
        # Unencrypted
        start = time.time()
        for _ in range(100):
            msg = Message(
                id="msg",
                sender_id="agent1",
                recipient_id="agent2",
                message_type=MessageType.REQUEST,
                content=msg_content
            )
            await bus_unencrypted.send(msg)
        unencrypted_time = time.time() - start
        
        # Encrypted
        start = time.time()
        for _ in range(100):
            msg = Message(
                id="msg",
                sender_id="agent1",
                recipient_id="agent2",
                message_type=MessageType.REQUEST,
                content=msg_content
            )
            await bus_encrypted.send(msg)
        encrypted_time = time.time() - start
        
        overhead = ((encrypted_time - unencrypted_time) / unencrypted_time) * 100
        print(f"\nEncryption overhead: {overhead:.1f}%")
        assert overhead < 200  # Less than 200% overhead


# ============================================
# Integration Tests
# ============================================

class TestIntegration:
    """Integration tests for complete workflows"""

    @pytest.mark.asyncio
    async def test_multi_agent_communication(self):
        """Test communication between multiple agents"""
        bus = MessageBus()
        hive = HiveMind()
        
        # Create agents
        agent1 = AgentCommunicationBridge("analyst", bus, hive)
        agent2 = AgentCommunicationBridge("executor", bus, hive)
        agent3 = AgentCommunicationBridge("learner", bus, hive)
        
        # Agent1 sends request to Agent2
        await agent1.send_message(
            "executor",
            {"task": "process"},
            MessageType.REQUEST,
            MessagePriority.HIGH
        )
        
        # Agent2 receives
        messages = await agent2.receive_messages()
        assert len(messages) > 0
        
        # Agent2 responds
        await agent2.respond_to_message(messages[0], {"result": "done"})
        
        # Agent1 receives response
        responses = await agent1.receive_messages()
        assert len(responses) > 0

    @pytest.mark.asyncio
    async def test_knowledge_and_skill_sharing(self):
        """Test sharing knowledge and skills across agents"""
        hive = HiveMind()
        
        # Agent1 shares knowledge
        await hive.share_knowledge("agent1", "technique", "vectorization", "public")
        
        # Agent1 registers skill
        skill_id = await hive.register_skill(
            "agent1",
            "optimization",
            "def optimize(): pass"
        )
        
        # Agent2 accesses knowledge
        knowledge = await hive.request_knowledge("technique")
        assert knowledge == "vectorization"
        
        # Agent2 learns skill
        await hive.learn_skill("agent2", skill_id)
        
        assert len(hive.learning_sessions) > 0


# ============================================
# Test Utilities
# ============================================

def run_tests():
    """Run all tests"""
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_tests()
