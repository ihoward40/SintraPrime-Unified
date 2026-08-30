"""Provider-neutral capability contracts.

These interfaces deliberately separate reading, retrieval, memory, and browser
mutation.  Adapters may call third-party or self-hosted tools, but SintraPrime
retains policy authority and audit responsibility.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence


class CapabilityError(RuntimeError):
    """Raised when a capability adapter cannot safely complete its operation."""


@dataclass(frozen=True)
class Citation:
    source_id: str
    locator: str
    excerpt: str | None = None


@dataclass(frozen=True)
class WebDocument:
    url: str
    content: str
    title: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    retrieved_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    tenant_id: str
    subject_id: str
    text: str
    tags: tuple[str, ...] = ()
    sensitivity: str = "internal"
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    content: str
    score: float
    citations: tuple[Citation, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrowserAction:
    action: str
    target: str
    value: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ActionDecision(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class WebReader(ABC):
    """Read-only website ingestion (Firecrawl/Crawl4AI-style capability)."""

    @abstractmethod
    async def read(self, url: str, *, tenant_id: str) -> WebDocument:
        raise NotImplementedError


class BrowserActor(ABC):
    """State-changing browser operation (browser-use-style capability)."""

    @abstractmethod
    async def act(
        self,
        action: BrowserAction,
        *,
        tenant_id: str,
        actor_id: str,
        approval_id: str | None = None,
    ) -> Mapping[str, Any]:
        raise NotImplementedError


class MemoryStore(ABC):
    """Durable, tenant-scoped agent memory."""

    @abstractmethod
    async def put(self, record: MemoryRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        query: str,
        limit: int = 5,
    ) -> Sequence[MemoryRecord]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, *, tenant_id: str, memory_id: str) -> bool:
        raise NotImplementedError


class KnowledgeRetriever(ABC):
    """Citation-bearing retrieval over private knowledge."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        *,
        tenant_id: str,
        limit: int = 5,
    ) -> Sequence[RetrievalResult]:
        raise NotImplementedError


class ActionPolicy(ABC):
    """SintraPrime-owned authority gate for external browser adapters."""

    @abstractmethod
    def decide(
        self,
        action: BrowserAction,
        *,
        tenant_id: str,
        actor_id: str,
    ) -> ActionDecision:
        raise NotImplementedError
