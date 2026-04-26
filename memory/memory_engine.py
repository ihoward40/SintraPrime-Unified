"""
Memory Engine — Master orchestrator for all memory layers.
Inspired by Hermes Agent's unified memory architecture.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .episodic_memory import EpisodicMemory
from .memory_types import MemoryEntry, MemorySearchResult, MemoryType
from .semantic_memory import SemanticMemory
from .user_profile import UserProfileManager
from .working_memory import WorkingMemory


# Keywords that indicate high-importance memories
HIGH_IMPORTANCE_KEYWORDS = [
    "critical", "urgent", "important", "deadline", "legal", "court", "lawsuit",
    "contract", "never", "always", "key", "vital", "essential", "must", "required",
    "statute", "regulation", "compliance", "privacy", "security", "confidential",
]
LOW_IMPORTANCE_KEYWORDS = [
    "maybe", "perhaps", "possibly", "trivial", "minor", "small", "unimportant",
    "anyway", "whatever", "random", "casual",
]


class MemoryEngine:
    """
    Unified memory orchestrator that coordinates semantic, episodic,
    working memory, and user profiles into a coherent context system.
    """

    def __init__(
        self,
        semantic_db_path: Optional[str] = None,
        episodic_db_path: Optional[str] = None,
        profiles_dir: Optional[str] = None,
    ):
        self.semantic = SemanticMemory(db_path=semantic_db_path)
        self.episodic = EpisodicMemory(db_path=episodic_db_path)
        self.working = WorkingMemory()
        self.profiles = UserProfileManager(profiles_dir=profiles_dir)

    # ------------------------------------------------------------------ #
    #  Core memory operations                                               #
    # ------------------------------------------------------------------ #

    def remember(
        self,
        content: str,
        context: Optional[str] = None,
        user_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        importance: Optional[float] = None,
    ) -> MemoryEntry:
        """
        Store a piece of information, routing it to the correct memory layer.
        Auto-computes importance if not provided.
        """
        if importance is None:
            importance = self.importance_score(content)
        if tags is None:
            tags = self._auto_tag(content)
        if memory_type is None:
            memory_type = self._route_memory_type(content, context)

        # Always store in semantic memory for long-term retrieval
        entry = self.semantic.store(
            content=content,
            tags=tags,
            importance=importance,
            user_id=user_id,
            metadata={"context": context or "", "source": "memory_engine"},
        )

        # Also cache in working memory for immediate access
        self.working.set_context(f"recent:{entry.id[:8]}", content, ttl_seconds=7200)

        return entry

    def recall(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        user_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[MemorySearchResult]:
        """
        Unified recall across all memory layers.
        Merges and re-ranks results by relevance.
        """
        results: List[MemorySearchResult] = []

        # Check working memory first (fastest)
        wm_context = self.working.get_all_context()
        wm_query_lower = query.lower()
        for key, value in wm_context.items():
            if isinstance(value, str) and wm_query_lower in value.lower():
                synthetic = MemoryEntry(
                    content=value,
                    memory_type=MemoryType.WORKING,
                    tags=["working_memory"],
                    importance=0.9,  # working memory is highly relevant
                    user_id=user_id,
                )
                results.append(MemorySearchResult(
                    entry=synthetic,
                    relevance_score=0.9,
                    context=f"working memory key: {key}",
                ))

        # Semantic memory search
        if memory_types is None or MemoryType.SEMANTIC in memory_types:
            semantic_results = self.semantic.recall(query=query, top_k=top_k, user_id=user_id)
            results.extend(semantic_results)

        # Deduplicate by content similarity and re-rank
        seen_content: set = set()
        deduped: List[MemorySearchResult] = []
        for r in sorted(results, key=lambda x: x.relevance_score, reverse=True):
            key = r.entry.content[:80].lower()
            if key not in seen_content:
                seen_content.add(key)
                deduped.append(r)

        return deduped[:top_k]

    # ------------------------------------------------------------------ #
    #  Context building for LLM prompts                                     #
    # ------------------------------------------------------------------ #

    def get_relevant_context(
        self,
        query: str,
        user_id: Optional[str] = None,
        max_tokens: int = 4000,
    ) -> str:
        """
        Build a context string suitable for injecting into an LLM prompt.
        Pulls from semantic + working memory + user profile.
        """
        sections: List[str] = []
        estimated_tokens = 0
        tokens_per_char = 0.25  # rough estimate

        # User profile context
        if user_id:
            profile_summary = self.profiles.summarize_profile(user_id)
            if profile_summary:
                profile_block = f"## User Profile\n{profile_summary}"
                t = int(len(profile_block) * tokens_per_char)
                if estimated_tokens + t < max_tokens:
                    sections.append(profile_block)
                    estimated_tokens += t

        # Recent working memory context
        wm_data = self.working.get_all_context()
        if wm_data:
            wm_items = []
            for k, v in list(wm_data.items())[:5]:
                if isinstance(v, str):
                    wm_items.append(f"- {k}: {v[:200]}")
            if wm_items:
                wm_block = "## Active Context\n" + "\n".join(wm_items)
                t = int(len(wm_block) * tokens_per_char)
                if estimated_tokens + t < max_tokens:
                    sections.append(wm_block)
                    estimated_tokens += t

        # Current task
        task = self.working.get_current_task()
        if task:
            task_block = f"## Current Task\n{task.name}: {task.description} (status: {task.status})"
            t = int(len(task_block) * tokens_per_char)
            if estimated_tokens + t < max_tokens:
                sections.append(task_block)
                estimated_tokens += t

        # Semantic memory recall
        memories = self.semantic.recall(query=query, top_k=8, user_id=user_id)
        if memories:
            mem_items = []
            for r in memories:
                snippet = f"- [{r.entry.importance:.1f}] {r.entry.content[:300]}"
                t = int(len(snippet) * tokens_per_char)
                if estimated_tokens + t > max_tokens:
                    break
                mem_items.append(snippet)
                estimated_tokens += t
            if mem_items:
                sections.append("## Relevant Knowledge\n" + "\n".join(mem_items))

        # Attention focus
        focus = self.working.get_attention_focus()
        if focus:
            focus_block = f"## Attention Focus\nCurrently relevant: {', '.join(focus)}"
            t = int(len(focus_block) * tokens_per_char)
            if estimated_tokens + t < max_tokens:
                sections.append(focus_block)

        return "\n\n".join(sections) if sections else "No relevant context found."

    # ------------------------------------------------------------------ #
    #  Importance scoring                                                   #
    # ------------------------------------------------------------------ #

    def importance_score(self, content: str) -> float:
        """
        Rate the importance of a memory on a 0.0–1.0 scale.
        Uses keyword signals, content length, and structural cues.
        """
        lower = content.lower()
        score = 0.5  # baseline

        high_hits = sum(1 for kw in HIGH_IMPORTANCE_KEYWORDS if kw in lower)
        low_hits = sum(1 for kw in LOW_IMPORTANCE_KEYWORDS if kw in lower)

        score += min(0.3, high_hits * 0.06)
        score -= min(0.2, low_hits * 0.05)

        # Longer content with structure is more important
        if len(content) > 500:
            score += 0.05
        if any(c in content for c in ["•", "1.", "-", "*"]):
            score += 0.03

        # Numbers (dates, case numbers, amounts) indicate specificity
        num_count = len(re.findall(r"\d+", content))
        score += min(0.1, num_count * 0.01)

        return max(0.0, min(1.0, round(score, 3)))

    # ------------------------------------------------------------------ #
    #  GDPR & data export                                                   #
    # ------------------------------------------------------------------ #

    def forget_all(self, user_id: str) -> Dict[str, int]:
        """Delete all data for a user across all memory layers (GDPR)."""
        stats = {
            "semantic_deleted": self.semantic.forget_user(user_id),
            "episodic_deleted": self.episodic.forget_user(user_id),
            "profile_deleted": 1 if self.profiles.delete_profile(user_id) else 0,
        }
        return stats

    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Full data export for a user (GDPR portability)."""
        return {
            "user_id": user_id,
            "exported_at": datetime.utcnow().isoformat(),
            "profile": self.profiles.export_profile(user_id),
            "semantic_memories": [
                e.to_dict() for e in self.semantic.all_entries(user_id=user_id)
            ],
            "episodic_sessions": self.episodic.export_user_data(user_id),
        }

    # ------------------------------------------------------------------ #
    #  Stats & diagnostics                                                  #
    # ------------------------------------------------------------------ #

    def memory_stats(self) -> Dict[str, Any]:
        """Return storage usage and entry counts across memory layers."""
        wm_stats = self.working.stats()
        return {
            "semantic": {
                "total_entries": self.semantic.count(),
            },
            "episodic": {
                "total_sessions": self.episodic.count_sessions(),
            },
            "working": wm_stats,
            "profiles": {
                "total_profiles": len(self.profiles.list_profiles()),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------ #
    #  Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _route_memory_type(self, content: str, context: Optional[str]) -> MemoryType:
        """Determine which memory type best fits this content."""
        lower = content.lower()
        if any(kw in lower for kw in ["prefer", "like", "dislike", "always", "never", "style"]):
            return MemoryType.PREFERENCE
        if any(kw in lower for kw in ["step", "procedure", "process", "how to", "workflow", "steps"]):
            return MemoryType.PROCEDURAL
        return MemoryType.SEMANTIC

    def _auto_tag(self, content: str) -> List[str]:
        """Generate tags automatically from content."""
        words = re.findall(r"[a-zA-Z]{4,}", content.lower())
        stopwords = {
            "that", "this", "with", "from", "have", "will", "your", "they",
            "them", "when", "where", "which", "been", "were", "then", "than",
        }
        filtered = [w for w in words if w not in stopwords]
        freq: Dict[str, int] = {}
        for w in filtered:
            freq[w] = freq.get(w, 0) + 1
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return [w for w, _ in top]
