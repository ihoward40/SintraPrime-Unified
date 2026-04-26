"""Standard message types for agent-to-agent communication."""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional
import uuid
import time
import json


class MessageType(Enum):
    # Discovery
    HELLO = "hello"                          # Agent announces itself
    GOODBYE = "goodbye"                      # Agent leaving network
    PING = "ping"
    PONG = "pong"

    # Knowledge sharing
    SHARE_KNOWLEDGE = "share_knowledge"      # Share learned information
    REQUEST_KNOWLEDGE = "request_knowledge"  # Ask for knowledge
    KNOWLEDGE_RESPONSE = "knowledge_response"

    # Task delegation
    DELEGATE_TASK = "delegate_task"          # Assign task to another agent
    TASK_ACCEPTED = "task_accepted"
    TASK_RESULT = "task_result"
    TASK_FAILED = "task_failed"

    # Legal domain
    LEGAL_QUERY = "legal_query"              # Ask another agent a legal question
    LEGAL_RESPONSE = "legal_response"
    CASE_SHARE = "case_share"                # Share case outcome for learning
    PRECEDENT_FOUND = "precedent_found"      # Share found precedent

    # Swarm coordination
    SWARM_JOIN = "swarm_join"
    SWARM_LEAVE = "swarm_leave"
    SWARM_TASK = "swarm_task"
    SWARM_VOTE = "swarm_vote"                # Parliament voting
    SWARM_CONSENSUS = "swarm_consensus"


@dataclass
class AgentMessage:
    """A single message transmitted between agent nodes."""

    type: MessageType
    sender_id: str
    payload: dict
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    target_id: Optional[str] = None   # None = broadcast
    reply_to: Optional[str] = None
    ttl: int = 30                      # seconds before message expires

    def to_json(self) -> str:
        """Serialize to JSON string."""
        d = asdict(self)
        d["type"] = self.type.value
        return json.dumps(d)

    @classmethod
    def from_json(cls, data: str) -> "AgentMessage":
        """Deserialize from JSON string."""
        d = json.loads(data)
        d["type"] = MessageType(d["type"])
        return cls(**d)

    def is_expired(self) -> bool:
        """Return True if this message has exceeded its TTL."""
        return (time.time() - self.timestamp) > self.ttl

    def make_reply(self, sender_id: str, payload: dict,
                   msg_type: MessageType) -> "AgentMessage":
        """Create a reply message to this message."""
        return AgentMessage(
            type=msg_type,
            sender_id=sender_id,
            payload=payload,
            target_id=self.sender_id,
            reply_to=self.message_id,
        )

    def __repr__(self) -> str:
        return (
            f"AgentMessage(id={self.message_id[:8]}, type={self.type.value}, "
            f"from={self.sender_id}, to={self.target_id or 'broadcast'})"
        )


@dataclass
class AgentCapabilities:
    """Declares what a SintraPrime instance can do."""

    trust_law: bool = False
    legal_intelligence: bool = False
    case_law: bool = False
    banking: bool = False
    voice: bool = False
    prediction: bool = False
    federal_agencies: bool = False
    local_llm: bool = False
    rag: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AgentCapabilities":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def has(self, capability: str) -> bool:
        """Check whether this agent has a named capability."""
        return bool(getattr(self, capability, False))

    def list_active(self) -> list[str]:
        """Return a list of all enabled capability names."""
        return [k for k, v in asdict(self).items() if v]
