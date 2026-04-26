"""
Memory type definitions and data models for SintraPrime-Unified Memory Engine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryType(Enum):
    """Categories of memory storage."""
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    WORKING = "working"
    PROCEDURAL = "procedural"
    PREFERENCE = "preference"


@dataclass
class MemoryEntry:
    """A single unit of stored memory."""
    content: str
    memory_type: MemoryType
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    embedding_vector: Optional[List[float]] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "tags": self.tags,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "embedding_vector": self.embedding_vector,
            "user_id": self.user_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        entry = cls(
            id=data["id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            tags=data.get("tags", []),
            importance=data.get("importance", 0.5),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=data.get("access_count", 0),
            embedding_vector=data.get("embedding_vector"),
            user_id=data.get("user_id"),
            metadata=data.get("metadata", {}),
        )
        return entry


@dataclass
class MemorySearchResult:
    """Result from a memory search query."""
    entry: MemoryEntry
    relevance_score: float
    context: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry": self.entry.to_dict(),
            "relevance_score": self.relevance_score,
            "context": self.context,
        }


@dataclass
class UserProfile:
    """Persistent user profile for personalized AI interactions."""
    user_id: str
    name: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    communication_style: str = "neutral"  # formal, casual, technical, neutral
    expertise_level: Dict[str, str] = field(default_factory=dict)  # domain -> level
    goals: List[str] = field(default_factory=list)
    trusted_contacts: List[Dict[str, str]] = field(default_factory=list)
    legal_matters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    interaction_count: int = 0
    topics_of_interest: List[str] = field(default_factory=list)
    language: str = "en"
    timezone: str = "UTC"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "preferences": self.preferences,
            "communication_style": self.communication_style,
            "expertise_level": self.expertise_level,
            "goals": self.goals,
            "trusted_contacts": self.trusted_contacts,
            "legal_matters": self.legal_matters,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "interaction_count": self.interaction_count,
            "topics_of_interest": self.topics_of_interest,
            "language": self.language,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        profile = cls(
            user_id=data["user_id"],
            name=data["name"],
            preferences=data.get("preferences", {}),
            communication_style=data.get("communication_style", "neutral"),
            expertise_level=data.get("expertise_level", {}),
            goals=data.get("goals", []),
            trusted_contacts=data.get("trusted_contacts", []),
            legal_matters=data.get("legal_matters", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
            interaction_count=data.get("interaction_count", 0),
            topics_of_interest=data.get("topics_of_interest", []),
            language=data.get("language", "en"),
            timezone=data.get("timezone", "UTC"),
        )
        return profile


@dataclass
class SkillRecord:
    """A learned procedure or skill."""
    name: str
    description: str
    steps: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    last_used: Optional[datetime] = None
    improvement_notes: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    usage_count: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "success_rate": self.success_rate,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "improvement_notes": self.improvement_notes,
            "created_at": self.created_at.isoformat(),
            "usage_count": self.usage_count,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillRecord":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            description=data["description"],
            steps=data.get("steps", []),
            success_rate=data.get("success_rate", 0.0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            improvement_notes=data.get("improvement_notes", []),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            usage_count=data.get("usage_count", 0),
            tags=data.get("tags", []),
        )


@dataclass
class Session:
    """A recorded conversation session."""
    session_id: str
    user_id: str
    messages: List[Dict[str, str]]
    outcomes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    summary: Optional[str] = None
    learnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "messages": self.messages,
            "outcomes": self.outcomes,
            "metadata": self.metadata,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "summary": self.summary,
            "learnings": self.learnings,
        }


@dataclass
class Episode:
    """A summarized episode from episodic memory."""
    session_id: str
    user_id: str
    summary: str
    key_topics: List[str] = field(default_factory=list)
    outcomes: List[str] = field(default_factory=list)
    date: datetime = field(default_factory=datetime.utcnow)
    importance: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "summary": self.summary,
            "key_topics": self.key_topics,
            "outcomes": self.outcomes,
            "date": self.date.isoformat(),
            "importance": self.importance,
        }


@dataclass
class Learning:
    """A lesson extracted from an episode."""
    content: str
    source_session: str
    confidence: float = 0.8
    domain: str = "general"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source_session": self.source_session,
            "confidence": self.confidence,
            "domain": self.domain,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Task:
    """Current task being worked on in working memory."""
    name: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    priority: int = 5  # 1-10
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
        }
