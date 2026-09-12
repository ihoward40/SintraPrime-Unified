"""Scoped context packages for governed SintraPrime agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .memory_engine import MemoryEngine


@dataclass(frozen=True)
class ContextScope:
    agent_id: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    matter_id: Optional[str] = None
    tenant_id: Optional[str] = None
    max_items: int = 8
    allow_legacy_user_scoped: bool = True


@dataclass
class ContextItem:
    memory_id: str
    content: str
    relevance_score: float
    importance: float
    tags: List[str]
    provenance: Dict[str, Any]
    scope: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "relevance_score": self.relevance_score,
            "importance": self.importance,
            "tags": list(self.tags),
            "provenance": dict(self.provenance),
            "scope": dict(self.scope),
        }


@dataclass
class ContextPackage:
    query: str
    scope: ContextScope
    items: List[ContextItem] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "scope": {
                "agent_id": self.scope.agent_id,
                "user_id": self.scope.user_id,
                "project_id": self.scope.project_id,
                "matter_id": self.scope.matter_id,
                "tenant_id": self.scope.tenant_id,
            },
            "created_at": self.created_at,
            "items": [item.to_dict() for item in self.items],
        }


class ContextPackageBuilder:
    """Build scope-filtered memory payloads before agent exposure."""

    def __init__(self, engine: Optional[MemoryEngine] = None):
        self.engine = engine or MemoryEngine()

    def build(self, query: str, scope: ContextScope) -> ContextPackage:
        # Query only semantic memory to avoid anonymous synthetic working-memory
        # entries from being treated as durable cross-agent context.
        results = self.engine.semantic.recall(
            query=query,
            top_k=max(scope.max_items * 4, scope.max_items),
            user_id=scope.user_id,
        )
        items: List[ContextItem] = []
        for result in results:
            entry = result.entry
            if not self._allowed(entry.user_id, entry.metadata, scope):
                continue
            metadata = dict(entry.metadata or {})
            items.append(
                ContextItem(
                    memory_id=entry.id,
                    content=entry.content,
                    relevance_score=result.relevance_score,
                    importance=entry.importance,
                    tags=list(entry.tags),
                    provenance={
                        "memory_id": entry.id,
                        "source": metadata.get("source", "unknown"),
                        "source_id": metadata.get("source_id"),
                        "source_uri": metadata.get("source_uri"),
                        "created_at": entry.created_at.isoformat(),
                    },
                    scope={
                        "user_id": entry.user_id,
                        "project_id": metadata.get("project_id"),
                        "matter_id": metadata.get("matter_id"),
                        "tenant_id": metadata.get("tenant_id"),
                        "agent_ids": metadata.get("agent_ids", []),
                        "legacy_unscoped": not any(
                            metadata.get(key)
                            for key in ("project_id", "matter_id", "tenant_id", "agent_ids")
                        ),
                    },
                )
            )
            if len(items) >= scope.max_items:
                break
        return ContextPackage(query=query, scope=scope, items=items)

    @staticmethod
    def _allowed(entry_user_id: Optional[str], metadata: Dict[str, Any], scope: ContextScope) -> bool:
        agent_ids = metadata.get("agent_ids") or []
        if agent_ids and scope.agent_id not in agent_ids:
            return False
        for key, requested in (
            ("project_id", scope.project_id),
            ("matter_id", scope.matter_id),
            ("tenant_id", scope.tenant_id),
        ):
            stored = metadata.get(key)
            if stored is not None and requested != stored:
                return False
        explicitly_global = metadata.get("visibility") == "global"
        explicitly_scoped = bool(agent_ids) or any(
            metadata.get(key) is not None for key in ("project_id", "matter_id", "tenant_id")
        )
        if entry_user_id is None and not explicitly_global and not explicitly_scoped:
            return False
        if entry_user_id is not None and scope.user_id != entry_user_id:
            return False
        if not explicitly_scoped and not explicitly_global:
            return bool(scope.allow_legacy_user_scoped and scope.user_id and entry_user_id == scope.user_id)
        return True
