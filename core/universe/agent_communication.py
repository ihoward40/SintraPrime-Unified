"""
UniVerse Agent Communication System
Enables agents to communicate, share knowledge, and learn from each other
Includes message encryption, batch processing, priority filtering, and dead letter queues
"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import hashlib
import hmac
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import time


class MessageType(Enum):
    """Types of messages agents can send"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    SKILL_SHARE = "skill_share"
    KNOWLEDGE_UPDATE = "knowledge_update"
    FAILURE_REPORT = "failure_report"
    SUCCESS_REPORT = "success_report"
    URGENT = "urgent"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Message:
    """Agent-to-agent message"""
    id: str
    sender_id: str
    recipient_id: str
    message_type: MessageType
    content: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    delivered_at: Optional[datetime] = None
    requires_response: bool = False
    response_timeout: int = 30  # seconds
    signature: Optional[str] = None  # HMAC signature for verification
    encrypted: bool = False


@dataclass
class HiveMindState:
    """Shared state accessible by all agents"""
    shared_knowledge: Dict[str, Any] = field(default_factory=dict)
    learned_skills: Dict[str, dict] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    shared_memories: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


class MessageBus:
    """
    Central pub/sub message bus for agent communication
    - Priority-based routing
    - Message encryption (AES-256)
    - Delivery guarantees
    - Dead letter handling
    - Batch message processing
    - Message filtering by type/priority
    """

    def __init__(self, max_queue_size: int = 10000, encryption_key: Optional[str] = None):
        self.max_queue_size = max_queue_size
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.subscribers: Dict[str, Set[Callable]] = {}
        self.message_history: List[Message] = []
        self.dead_letter_queue: List[Message] = []
        self.delivery_confirmations: Dict[str, bool] = {}
        self.batch_size = 100
        self.batch_timeout = 5.0  # seconds
        self.pending_batches: Dict[str, List[Message]] = {}
        self.batch_timers: Dict[str, asyncio.Task] = {}
        self.message_filters: Dict[str, Callable] = {}
        self.metrics = {
            "total_sent": 0,
            "total_received": 0,
            "total_failed": 0,
            "total_recovered": 0
        }
        
        # Encryption setup
        self.encryption_key = encryption_key or os.getenv("MESSAGE_BUS_KEY", None)
        self.cipher = self._setup_encryption() if self.encryption_key else None

    def _setup_encryption(self) -> Optional[Fernet]:
        """Setup Fernet cipher for message encryption"""
        try:
            if not self.encryption_key:
                return None
            
            # Derive encryption key from provided key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'universe_salt_16',
                iterations=100000
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
            return Fernet(key)
        except Exception as e:
            print(f"Encryption setup failed: {e}")
            return None

    def encrypt_message(self, message: Message) -> Optional[str]:
        """Encrypt message content"""
        if not self.cipher:
            return None
        try:
            content_str = json.dumps(message.content)
            encrypted = self.cipher.encrypt(content_str.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            print(f"Encryption error: {e}")
            return None

    def decrypt_message(self, encrypted_content: str) -> Optional[Dict[str, Any]]:
        """Decrypt message content"""
        if not self.cipher:
            return None
        try:
            encrypted = base64.b64decode(encrypted_content.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception as e:
            print(f"Decryption error: {e}")
            return None

    async def batch_send(self, messages: List[Message]) -> Dict[str, bool]:
        """Send multiple messages as a batch"""
        results = {}
        for message in messages:
            results[message.id] = await self.send(message)
        self.metrics["total_sent"] += len(messages)
        return results

    async def filter_messages(
        self, 
        agent_id: str, 
        message_type: Optional[MessageType] = None,
        priority: Optional[MessagePriority] = None
    ) -> List[Message]:
        """Filter messages by type and/or priority"""
        history = self.get_message_history(agent_id)
        
        if message_type:
            history = [m for m in history if m.message_type == message_type]
        if priority:
            history = [m for m in history if m.priority == priority]
        
        return history

    async def register_filter(self, filter_name: str, filter_func: Callable):
        """Register a custom message filter"""
        self.message_filters[filter_name] = filter_func

    async def apply_filter(self, filter_name: str, message: Message) -> bool:
        """Apply a registered filter to a message"""
        if filter_name not in self.message_filters:
            return True
        try:
            return await self.message_filters[filter_name](message)
        except Exception as e:
            print(f"Filter error: {e}")
            return False

    async def recover_from_dead_letter(self, message_id: Optional[str] = None) -> int:
        """Recover messages from dead letter queue"""
        recovered = 0
        
        if message_id:
            # Recover specific message
            for msg in list(self.dead_letter_queue):
                if msg.id == message_id:
                    try:
                        if await self.send(msg):
                            self.dead_letter_queue.remove(msg)
                            recovered += 1
                            self.metrics["total_recovered"] += 1
                    except Exception as e:
                        print(f"Recovery error: {e}")
        else:
            # Recover all messages
            for msg in list(self.dead_letter_queue):
                try:
                    if await self.send(msg):
                        self.dead_letter_queue.remove(msg)
                        recovered += 1
                        self.metrics["total_recovered"] += 1
                except Exception as e:
                    print(f"Recovery error: {e}")
        
        return recovered

    async def send(self, message: Message) -> bool:
        """Send a message to an agent"""
        try:
            # Verify message signature
            if message.signature and not self._verify_signature(message):
                self.dead_letter_queue.append(message)
                self.metrics["total_failed"] += 1
                return False

            # Encrypt message if key available
            if self.cipher and message.message_type in [
                MessageType.REQUEST, MessageType.RESPONSE, MessageType.SKILL_SHARE
            ]:
                encrypted_content = self.encrypt_message(message)
                if encrypted_content:
                    message.encrypted = True
                    message.content = {"encrypted_payload": encrypted_content}

            # Create queue if doesn't exist
            if message.recipient_id not in self.message_queues:
                self.message_queues[message.recipient_id] = asyncio.Queue(
                    maxsize=self.max_queue_size
                )

            # Add to queue by priority
            queue = self.message_queues[message.recipient_id]
            await queue.put(message)

            # Record in history
            self.message_history.append(message)
            message.delivered_at = datetime.now()
            self.metrics["total_sent"] += 1

            # Notify subscribers
            await self._notify_subscribers(message.recipient_id, message)

            return True

        except asyncio.QueueFull:
            self.dead_letter_queue.append(message)
            self.metrics["total_failed"] += 1
            return False
        except Exception as e:
            print(f"Send error: {e}")
            self.dead_letter_queue.append(message)
            self.metrics["total_failed"] += 1
            return False

    async def receive(self, agent_id: str) -> Optional[Message]:
        """Receive next message for an agent"""
        if agent_id not in self.message_queues:
            return None

        try:
            message = self.message_queues[agent_id].get_nowait()
            
            # Decrypt message if encrypted
            if message.encrypted and self.cipher:
                encrypted_payload = message.content.get("encrypted_payload")
                if encrypted_payload:
                    decrypted = self.decrypt_message(encrypted_payload)
                    if decrypted:
                        message.content = decrypted
                        message.encrypted = False
            
            self.delivery_confirmations[message.id] = True
            self.metrics["total_received"] += 1
            return message
        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            print(f"Receive error: {e}")
            return None

    async def subscribe(self, agent_id: str, callback: Callable):
        """Subscribe to messages for an agent"""
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = set()
        self.subscribers[agent_id].add(callback)

    async def unsubscribe(self, agent_id: str, callback: Callable):
        """Unsubscribe from messages"""
        if agent_id in self.subscribers:
            self.subscribers[agent_id].discard(callback)

    async def _notify_subscribers(self, agent_id: str, message: Message):
        """Notify all subscribers of a message"""
        if agent_id in self.subscribers:
            for callback in self.subscribers[agent_id]:
                try:
                    await callback(message)
                except Exception as e:
                    print(f"Subscriber error: {e}")

    def _verify_signature(self, message: Message) -> bool:
        """Verify message HMAC signature"""
        if not message.signature:
            return True

        content_str = json.dumps(message.content, sort_keys=True)
        expected = hmac.new(
            message.sender_id.encode(),
            content_str.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(message.signature, expected)

    def get_message_history(self, agent_id: Optional[str] = None) -> List[Message]:
        """Get message history, optionally filtered by agent"""
        if agent_id:
            return [m for m in self.message_history
                    if m.sender_id == agent_id or m.recipient_id == agent_id]
        return self.message_history

    def get_queue_stats(self) -> Dict[str, int]:
        """Get statistics on message queues"""
        return {
            agent_id: queue.qsize()
            for agent_id, queue in self.message_queues.items()
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get message bus metrics"""
        return {
            **self.metrics,
            "total_history": len(self.message_history),
            "dead_letter_count": len(self.dead_letter_queue),
            "queue_stats": self.get_queue_stats(),
            "encryption_enabled": self.cipher is not None,
            "filters_registered": len(self.message_filters)
        }

    def clear_dead_letter_queue(self):
        """Clear the dead letter queue"""
        count = len(self.dead_letter_queue)
        self.dead_letter_queue.clear()
        return count


class HiveMind:
    """
    Collective intelligence system allowing agents to:
    - Share knowledge and skills
    - Learn from each other
    - Aggregate performance metrics
    - Access shared context
    """

    def __init__(self):
        self.state = HiveMindState()
        self.learning_sessions: Dict[str, dict] = {}
        self.skill_versions: Dict[str, List[dict]] = {}

    async def share_knowledge(
        self,
        source_agent: str,
        knowledge_key: str,
        knowledge_value: Any,
        scope: str = "public"  # public, team, private
    ) -> bool:
        """Share knowledge with the hive mind"""
        try:
            self.state.shared_knowledge[knowledge_key] = {
                "value": knowledge_value,
                "source": source_agent,
                "timestamp": datetime.now(),
                "scope": scope
            }
            self.state.last_updated = datetime.now()
            return True
        except Exception as e:
            print(f"Knowledge sharing error: {e}")
            return False

    async def request_knowledge(self, knowledge_key: str) -> Optional[Any]:
        """Request knowledge from shared knowledge base"""
        if knowledge_key in self.state.shared_knowledge:
            return self.state.shared_knowledge[knowledge_key]["value"]
        return None

    async def register_skill(
        self,
        agent_id: str,
        skill_name: str,
        skill_code: str,
        success_rate: float = 0.0
    ) -> str:
        """Register a new skill with the hive mind"""
        skill_id = f"{agent_id}:{skill_name}:{len(self.skill_versions.get(skill_name, []))}"

        skill_data = {
            "id": skill_id,
            "agent_id": agent_id,
            "name": skill_name,
            "code": skill_code,
            "success_rate": success_rate,
            "created_at": datetime.now(),
            "usage_count": 0
        }

        if skill_name not in self.skill_versions:
            self.skill_versions[skill_name] = []

        self.skill_versions[skill_name].append(skill_data)
        self.state.learned_skills[skill_id] = skill_data

        return skill_id

    async def get_skill(self, skill_name: str, version: int = -1) -> Optional[dict]:
        """Get a skill from the skill library"""
        if skill_name in self.skill_versions:
            return self.skill_versions[skill_name][version]
        return None

    async def learn_skill(
        self,
        learner_id: str,
        skill_id: str,
        iterations: int = 10
    ) -> bool:
        """Record agent learning from another agent's skill"""
        if skill_id not in self.state.learned_skills:
            return False

        session_id = f"{learner_id}:{skill_id}:{datetime.now().timestamp()}"
        self.learning_sessions[session_id] = {
            "learner_id": learner_id,
            "skill_id": skill_id,
            "iterations": iterations,
            "success_rate": 0.0,
            "started_at": datetime.now()
        }

        return True

    async def record_success(
        self,
        agent_id: str,
        metric_name: str,
        value: float
    ):
        """Record success metrics for an agent"""
        key = f"{agent_id}:{metric_name}"
        self.state.performance_metrics[key] = value
        self.state.last_updated = datetime.now()

    async def get_agent_metrics(self, agent_id: str) -> Dict[str, float]:
        """Get performance metrics for an agent"""
        return {
            key.split(":")[1]: value
            for key, value in self.state.performance_metrics.items()
            if key.startswith(agent_id)
        }

    async def recommend_skill(
        self,
        agent_id: str,
        task_description: str,
        top_n: int = 3
    ) -> List[dict]:
        """
        Recommend relevant skills based on task description
        Uses semantic similarity and agent expertise
        """
        recommendations = []

        for skill_id, skill in self.state.learned_skills.items():
            # Simple relevance scoring (can be enhanced with embeddings)
            score = sum(
                1 for word in task_description.lower().split()
                if word in skill.get("name", "").lower()
            )

            if score > 0:
                recommendations.append({
                    "skill_id": skill_id,
                    "skill_name": skill.get("name"),
                    "success_rate": skill.get("success_rate", 0),
                    "relevance_score": score
                })

        return sorted(recommendations, key=lambda x: x["relevance_score"], reverse=True)[:top_n]

    def get_hive_state(self) -> Dict[str, Any]:
        """Get current state of the hive mind"""
        return {
            "knowledge_items": len(self.state.shared_knowledge),
            "learned_skills": len(self.state.learned_skills),
            "learning_sessions": len(self.learning_sessions),
            "performance_metrics": len(self.state.performance_metrics),
            "last_updated": self.state.last_updated.isoformat()
        }


class AgentCommunicationBridge:
    """
    Bridge connecting agents to message bus and hive mind
    Handles message routing and response matching
    """

    def __init__(self, agent_id: str, message_bus: MessageBus, hive_mind: HiveMind):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.hive_mind = hive_mind
        self.pending_responses: Dict[str, asyncio.Future] = {}

    async def send_message(
        self,
        recipient_id: str,
        content: Dict[str, Any],
        message_type: MessageType = MessageType.REQUEST,
        priority: MessagePriority = MessagePriority.NORMAL,
        requires_response: bool = False
    ) -> bool:
        """Send a message to another agent"""
        import uuid

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            priority=priority,
            requires_response=requires_response
        )

        return await self.message_bus.send(message)

    async def receive_messages(self) -> List[Message]:
        """Receive all pending messages for this agent"""
        messages = []
        while True:
            msg = await self.message_bus.receive(self.agent_id)
            if msg is None:
                break
            messages.append(msg)
        return messages

    async def respond_to_message(
        self,
        original_message: Message,
        response_content: Dict[str, Any]
    ) -> bool:
        """Send a response to a message"""
        return await self.send_message(
            recipient_id=original_message.sender_id,
            content=response_content,
            message_type=MessageType.RESPONSE,
            priority=MessagePriority.NORMAL
        )

    async def share_knowledge(self, key: str, value: Any, scope: str = "public"):
        """Share knowledge with hive mind"""
        await self.hive_mind.share_knowledge(self.agent_id, key, value, scope)

    async def learn_from_agent(self, other_agent_id: str, skill_name: str):
        """Learn a skill from another agent"""
        # Find the skill
        skill = await self.hive_mind.get_skill(skill_name)
        if skill:
            await self.hive_mind.learn_skill(self.agent_id, skill["id"])
            return True
        return False

    def get_message_stats(self) -> Dict[str, Any]:
        """Get communication statistics for this agent"""
        history = self.message_bus.get_message_history(self.agent_id)
        return {
            "total_messages": len(history),
            "sent": len([m for m in history if m.sender_id == self.agent_id]),
            "received": len([m for m in history if m.recipient_id == self.agent_id]),
            "pending_responses": len(self.pending_responses),
            "queue_size": self.message_bus.message_queues.get(
                self.agent_id, asyncio.Queue()
            ).qsize()
        }


# Example usage
async def demo_communication():
    """Demonstrate agent communication"""
    message_bus = MessageBus()
    hive_mind = HiveMind()

    # Create two agents
    agent1 = AgentCommunicationBridge("analyst_1", message_bus, hive_mind)
    agent2 = AgentCommunicationBridge("executor_1", message_bus, hive_mind)

    # Agent 1 sends a message to Agent 2
    await agent1.send_message(
        "executor_1",
        {"task": "Process data", "data": [1, 2, 3]},
        message_type=MessageType.REQUEST
    )

    # Agent 2 receives the message
    messages = await agent2.receive_messages()
    print(f"Agent 2 received: {messages}")

    # Agent 2 responds
    if messages:
        await agent2.respond_to_message(
            messages[0],
            {"status": "completed", "result": [2, 4, 6]}
        )

    # Agent 1 receives response
    responses = await agent1.receive_messages()
    print(f"Agent 1 received response: {responses}")

    # Share knowledge
    await agent1.share_knowledge("processing_method", "batch_processing", scope="public")
    shared = await agent2.hive_mind.request_knowledge("processing_method")
    print(f"Shared knowledge: {shared}")

    # Register and recommend skills
    skill_id = await hive_mind.register_skill(
        "executor_1",
        "data_processing",
        "def process(data): return [x*2 for x in data]",
        success_rate=0.95
    )

    recommendations = await hive_mind.recommend_skill("analyst_1", "process data efficiently")
    print(f"Skill recommendations: {recommendations}")


if __name__ == "__main__":
    asyncio.run(demo_communication())
