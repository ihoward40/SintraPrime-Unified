# Inspired by vectorize-io/hindsight (MIT License) — https://github.com/vectorize-io/hindsight
#
# This module adapts hindsight's core learning-memory concepts — the
# retain / recall / reflect operations, memory banks, and knowledge pages
# (durable mental models distilled from reflection) — to SintraPrime-Unified's
# existing memory engine. It imports the engine's storage layers and does not
# duplicate them.
"""
Learning memory layer — retain / recall / reflect over the existing
MemoryEngine, with memory banks for domain partitioning and knowledge
pages (mental models) as durable distilled knowledge.

Adapted concepts (original ideas, not copied code):
  - retain / recall / reflect: the three core learning-memory operations.
  - MemoryBank: named banks that partition memory by domain or purpose,
    so different projects, topics, or users stay isolated.
  - KnowledgePage: durable, evidence-backed knowledge distilled from
    reflection over retained memories ("mental models").

All persistence goes through the existing ``MemoryEngine`` layers
(semantic / working memory). Banks and knowledge pages are stored as
tagged semantic entries with structured metadata, so they survive restarts
in the same SQLite backing store as everything else.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Dict, List, Optional

from .memory_engine import MemoryEngine
from .memory_types import MemoryEntry, MemorySearchResult, MemoryType

# Metadata markers used to find learning-layer records in semantic storage.
KNOWLEDGE_PAGE_KIND = "knowledge_page"
LEARNING_LAYER_SOURCE = "learning_layer"

# Tags from auto-tagging / engine routing that never make good theme titles.
_NON_THEME_TAGS = {
    "knowledge_page",
    "working_memory",
    "general",
    "learning",
    "memory",
    "this",
    "that",
    "with",
}


def _slugify(name: str) -> str:
    """Turn a bank name into a stable bank_id (lowercase snake_case)."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "default"


def _bank_tag(bank_id: str) -> str:
    return f"bank:{bank_id}"


@dataclass
class MemoryBank:
    """A named partition of memory, isolating a domain, project, or purpose."""
    bank_id: str
    name: str
    description: str = ""
    purpose: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bank_id": self.bank_id,
            "name": self.name,
            "description": self.description,
            "purpose": self.purpose,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class KnowledgePage:
    """
    A durable distilled knowledge record — a "mental model" in hindsight terms.

    Produced by reflection over a group of related retained memories. Each page
    keeps pointers to the entries that support it so the distillation is
    auditable back to source memories.
    """
    page_id: str
    title: str
    domain: str
    bank_id: Optional[str]
    summary: str
    key_points: List[str] = field(default_factory=list)
    supporting_entry_ids: List[str] = field(default_factory=list)
    confidence: float = 0.8
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "title": self.title,
            "domain": self.domain,
            "bank_id": self.bank_id,
            "summary": self.summary,
            "key_points": self.key_points,
            "supporting_entry_ids": self.supporting_entry_ids,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_metadata_entry(cls, entry: MemoryEntry) -> Optional["KnowledgePage"]:
        """Rebuild a KnowledgePage from its persisted semantic entry."""
        meta = entry.metadata or {}
        if meta.get("kind") != KNOWLEDGE_PAGE_KIND:
            return None
        key_points = meta.get("key_points", [])
        return cls(
            page_id=meta.get("page_id", entry.id),
            title=meta.get("title", ""),
            domain=meta.get("domain", "general"),
            bank_id=meta.get("bank_id"),
            summary=entry.content.replace("[Knowledge Page]", "").strip(),
            key_points=key_points,
            supporting_entry_ids=list(meta.get("supporting_entry_ids", [])),
            confidence=float(meta.get("confidence", 0.8)),
            created_at=entry.created_at,
            updated_at=entry.last_accessed,
        )


@dataclass
class Reflection:
    """The result of a reflect operation: synthesis + distilled pages."""
    query: str
    bank_id: Optional[str]
    summary: str
    key_themes: List[Dict[str, Any]]
    memory_count: int
    knowledge_pages: List[KnowledgePage] = field(default_factory=list)
    reflected_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "bank_id": self.bank_id,
            "summary": self.summary,
            "key_themes": self.key_themes,
            "memory_count": self.memory_count,
            "knowledge_pages": [p.to_dict() for p in self.knowledge_pages],
            "reflected_at": self.reflected_at.isoformat(),
        }


class LearningMemory:
    """
    Learning-memory facade over an existing ``MemoryEngine``.

    Provides the three hindsight-style operations — retain / recall / reflect —
    scoped by memory banks, and maintains knowledge pages (mental models) that
    accumulate durable understanding from reflection. The engine itself is the
    only storage; this class is logic and orchestration on top.
    """

    def __init__(self, engine: MemoryEngine):
        self._engine = engine
        self._banks: Dict[str, MemoryBank] = {}

    # ------------------------------------------------------------------ #
    #  Memory banks                                                         #
    # ------------------------------------------------------------------ #

    def create_bank(self, name: str, description: str = "", purpose: str = "") -> MemoryBank:
        """Create (or return the existing) bank for ``name``."""
        bank_id = _slugify(name)
        if bank_id not in self._banks:
            self._banks[bank_id] = MemoryBank(
                bank_id=bank_id,
                name=name,
                description=description,
                purpose=purpose,
            )
        return self._banks[bank_id]

    def get_bank(self, bank_id: str) -> Optional[MemoryBank]:
        return self._banks.get(_slugify(bank_id))

    def list_banks(self) -> List[MemoryBank]:
        return list(self._banks.values())

    def _require_bank(self, bank_id: str) -> MemoryBank:
        slug = _slugify(bank_id)
        bank = self._banks.get(slug)
        if bank is not None:
            return bank
        # Banks are lightweight in-memory registries, but their contents persist
        # in semantic storage. Recover the bank if its data is present so that
        # recall / reflection keep working after a restart.
        if self._bank_has_persisted_data(slug):
            bank = MemoryBank(
                bank_id=slug,
                name=slug.replace("_", " ").title(),
                description="Recovered from persisted bank data.",
            )
            self._banks[slug] = bank
            return bank
        raise ValueError(
            f"Unknown memory bank '{bank_id}'. Known banks: "
            f"{sorted(self._banks) or ['(none — create one with create_bank)']}."
        )

    def _bank_has_persisted_data(self, bank_id: str) -> bool:
        tag = _bank_tag(bank_id)
        for entry in self._engine.semantic.all_entries():
            if tag in (entry.tags or []):
                return True
            if (entry.metadata or {}).get("bank_id") == bank_id:
                return True
        return False

    # ------------------------------------------------------------------ #
    #  retain                                                               #
    # ------------------------------------------------------------------ #

    def retain(
        self,
        content: str,
        bank_id: Optional[str] = None,
        user_id: Optional[str] = None,
        importance: Optional[float] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
    ) -> MemoryEntry:
        """
        Store a durable, reusable fact — the "retain" operation.

        Routes through the existing engine's ``remember()`` so importance
        scoring, type routing, and working-memory caching all apply, then
        stamps the entry with its bank for scoped recall.
        """
        bank_tag = None
        if bank_id is not None:
            bank = self._require_bank(bank_id)
            bank_tag = _bank_tag(bank.bank_id)

        combined_tags = list(tags) if tags else []
        if bank_tag and bank_tag not in combined_tags:
            combined_tags.append(bank_tag)

        entry = self._engine.remember(
            content=content,
            user_id=user_id,
            memory_type=memory_type,
            tags=combined_tags,
            importance=importance,
        )
        # Stamp bank metadata so pages/filters can find it without the tag.
        entry.metadata.setdefault("source", LEARNING_LAYER_SOURCE)
        if bank_id is not None:
            entry.metadata["bank_id"] = _slugify(bank_id)
        return entry

    # ------------------------------------------------------------------ #
    #  recall                                                               #
    # ------------------------------------------------------------------ #

    def recall(
        self,
        query: str,
        bank_id: Optional[str] = None,
        user_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[MemorySearchResult]:
        """
        Retrieve relevant retained memories — the "recall" operation.

        Uses the engine's unified recall (working + semantic), then scopes to
        the requested bank when ``bank_id`` is given.
        """
        if bank_id is not None:
            self._require_bank(bank_id)

        results = self._engine.recall(
            query=self._expand_query(query),
            user_id=user_id,
            top_k=top_k * 2,  # over-fetch: bank filtering happens below
        )

        if bank_id is not None:
            bank = self._require_bank(bank_id)
            # The engine caches retained content in working memory under
            # "recent:<id>" and its synthetic recall results carry no bank tag,
            # so match working-memory hits back to banked content by fingerprint
            # and stamp them with the bank so scoped results stay consistent.
            bank_contents = {
                e.content[:80].lower()
                for e in self._bank_entries(bank.bank_id, user_id)
            }
            bank_tag = _bank_tag(bank.bank_id)
            scoped: List[MemorySearchResult] = []
            for r in results:
                if self._entry_in_bank(r.entry, bank.bank_id):
                    scoped.append(r)
                elif (
                    r.entry.memory_type == MemoryType.WORKING
                    and r.entry.content[:80].lower() in bank_contents
                ):
                    stamped = replace(
                        r.entry,
                        tags=list(dict.fromkeys(list(r.entry.tags or []) + [bank_tag])),
                        metadata={
                            **(r.entry.metadata or {}),
                            "bank_id": bank.bank_id,
                            "source": LEARNING_LAYER_SOURCE,
                        },
                    )
                    scoped.append(
                        MemorySearchResult(
                            entry=stamped,
                            relevance_score=r.relevance_score,
                            context=r.context,
                        )
                    )
            results = scoped

        # De-duplicate knowledge pages from recall: they are derived knowledge,
        # not raw memories. They are reachable via get_knowledge_pages().
        results = [
            r for r in results
            if r.entry.metadata.get("kind") != KNOWLEDGE_PAGE_KIND
        ]
        return results[:top_k]

    @staticmethod
    def _entry_in_bank(entry: MemoryEntry, bank_id: str) -> bool:
        tag = _bank_tag(bank_id)
        if tag in (entry.tags or []):
            return True
        return (entry.metadata or {}).get("bank_id") == bank_id

    # ------------------------------------------------------------------ #
    #  reflect                                                              #
    # ------------------------------------------------------------------ #

    def reflect(
        self,
        query: str,
        bank_id: Optional[str] = None,
        user_id: Optional[str] = None,
        top_k: int = 10,
        persist_pages: bool = True,
    ) -> Reflection:
        """
        Synthesize reasoning over recalled memories — the "reflect" operation.

        Recalls relevant memories, extracts key themes, and distills them into
        knowledge pages (mental models) that accumulate durable understanding.
        Returns a ``Reflection`` with the synthesis and the pages produced.
        """
        results = self.recall(query=query, bank_id=bank_id, user_id=user_id, top_k=top_k)
        entries = [r.entry for r in results]

        themes = self._extract_themes(entries)
        pages: List[KnowledgePage] = []
        if persist_pages:
            for theme in themes:
                pages.append(
                    self._upsert_knowledge_page(theme, bank_id, user_id)
                )

        summary = self._summarize_reflection(query, entries, themes)
        return Reflection(
            query=query,
            bank_id=_slugify(bank_id) if bank_id else None,
            summary=summary,
            key_themes=themes,
            memory_count=len(entries),
            knowledge_pages=pages,
        )

    def run_learning_cycle(
        self,
        bank_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[KnowledgePage]:
        """
        Periodic consolidation: reflect over everything retained in a bank
        (or all banks when ``bank_id`` is None) and refresh knowledge pages.
        """
        entries: List[MemoryEntry] = []
        if bank_id is not None:
            bank = self._require_bank(bank_id)
            entries = self._bank_entries(bank.bank_id, user_id)
        else:
            for bank in self.list_banks():
                entries.extend(self._bank_entries(bank.bank_id, user_id))

        themes = self._extract_themes(entries)
        return [self._upsert_knowledge_page(t, bank_id, user_id) for t in themes]

    # ------------------------------------------------------------------ #
    #  Knowledge pages (mental models)                                      #
    # ------------------------------------------------------------------ #

    def get_knowledge_pages(
        self,
        bank_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[KnowledgePage]:
        """List persisted knowledge pages, optionally scoped to a bank."""
        if bank_id is not None:
            self._require_bank(bank_id)
        pages: List[KnowledgePage] = []
        for entry in self._engine.semantic.all_entries(user_id=user_id):
            page = KnowledgePage.from_metadata_entry(entry)
            if page is None:
                continue
            if bank_id is not None and page.bank_id != _slugify(bank_id):
                continue
            pages.append(page)
        pages.sort(key=lambda p: (p.confidence, p.updated_at), reverse=True)
        return pages

    def get_knowledge_page(self, page_id: str) -> Optional[KnowledgePage]:
        """Fetch one knowledge page by its page_id."""
        for entry in self._engine.semantic.all_entries():
            page = KnowledgePage.from_metadata_entry(entry)
            if page is not None and page.page_id == page_id:
                return page
        return None

    # ------------------------------------------------------------------ #
    #  Reflection internals                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _expand_query(query: str) -> str:
        """
        Light query expansion for the engine's exact-token TF-IDF scorer.

        Adds naive singular forms ("deadlines" -> "deadline") so natural
        phrasing still matches retained wording. The original query is kept
        first so the engine's own working-memory matching still applies.
        """
        words = re.findall(r"[a-zA-Z]{3,}", query)
        extras: List[str] = []
        for w in words:
            lower = w.lower()
            stem = LearningMemory._singular(lower)
            if stem and stem != lower:
                extras.append(stem)
        expanded = query + (" " + " ".join(dict.fromkeys(extras)) if extras else "")
        return expanded

    @staticmethod
    def _singular(word: str) -> Optional[str]:
        """Naive English plural -> singular, only for words that look plural."""
        if word.endswith("ies") and len(word) > 4:
            return word[:-3] + "y"
        if word.endswith(("sses", "xes", "ches", "shes")) and len(word) > 5:
            return word[:-2]
        if (
            word.endswith("s")
            and not word.endswith("ss")
            and not word.endswith("us")
            and len(word) > 3
        ):
            return word[:-1]
        return None

    def _extract_themes(self, entries: List[MemoryEntry]) -> List[Dict[str, Any]]:
        """
        Group entries into themes by shared tags (ignoring bank/housekeeping
        tags). Each tag shared by >= 2 entries becomes a theme; leftover
        entries roll into a single "general" theme so nothing is lost.
        """
        tag_to_entries: Dict[str, List[MemoryEntry]] = {}
        unthemed: List[MemoryEntry] = []

        for entry in entries:
            tags = [t for t in (entry.tags or []) if self._is_theme_tag(t)]
            if tags:
                for tag in tags:
                    tag_to_entries.setdefault(tag, []).append(entry)
            else:
                unthemed.append(entry)

        themes: List[Dict[str, Any]] = []
        for tag, tagged in sorted(tag_to_entries.items()):
            if len(tagged) >= 2:
                themes.append(self._theme_from(tag, tagged))
            else:
                unthemed.extend(tagged)

        if unthemed:
            themes.append(self._theme_from("general", unthemed))
        return themes

    def _theme_from(self, tag: str, entries: List[MemoryEntry]) -> Dict[str, Any]:
        entry_ids = [e.id for e in entries]
        domains = sorted({e.memory_type.value for e in entries})
        avg_importance = round(sum(e.importance for e in entries) / len(entries), 3)
        return {
            "title": tag.replace("_", " ").capitalize(),
            "tag": tag,
            "domain": domains[0] if domains else "general",
            "entry_ids": entry_ids,
            "entry_count": len(entries),
            "avg_importance": avg_importance,
        }

    @staticmethod
    def _is_theme_tag(tag: str) -> bool:
        lower = tag.lower()
        if lower in _NON_THEME_TAGS or lower.startswith("bank:"):
            return False
        return len(lower) >= 3

    def _summarize_reflection(
        self,
        query: str,
        entries: List[MemoryEntry],
        themes: List[Dict[str, Any]],
    ) -> str:
        if not entries:
            return f"Reflection on '{query}': no relevant memories found."
        lines = [
            f"Reflection on '{query}': synthesized {len(entries)} "
            f"{'memory' if len(entries) == 1 else 'memories'} "
            f"into {len(themes)} {'theme' if len(themes) == 1 else 'themes'}."
        ]
        for theme in themes:
            lines.append(
                f"- {theme['title']} ({theme['entry_count']} memories, "
                f"avg importance {theme['avg_importance']}): "
                f"knowledge distilled into the '{theme['title']}' mental model."
            )
        return "\n".join(lines)

    def _upsert_knowledge_page(
        self,
        theme: Dict[str, Any],
        bank_id: Optional[str],
        user_id: Optional[str],
    ) -> KnowledgePage:
        """Create a page, or merge into the existing one for this theme/bank."""
        slug_bank = _slugify(bank_id) if bank_id else None
        existing = self._find_page(theme["title"], slug_bank)

        supporting_ids = list(dict.fromkeys(theme["entry_ids"]))
        key_points = [
            f"{e_count} supporting {'memory' if theme['entry_count'] == 1 else 'memories'} "
            f"retained (avg importance {theme['avg_importance']})"
            for e_count in [theme["entry_count"]]
        ]

        if existing is None:
            page = KnowledgePage(
                page_id=uuid.uuid4().hex,
                title=theme["title"],
                domain=theme["domain"],
                bank_id=slug_bank,
                summary=(
                    f"Distilled mental model for '{theme['title']}', "
                    f"derived from {theme['entry_count']} retained "
                    f"{'memory' if theme['entry_count'] == 1 else 'memories'}."
                ),
                key_points=key_points,
                supporting_entry_ids=supporting_ids,
                confidence=round(
                    min(1.0, 0.6 + 0.05 * min(theme["entry_count"], 8)), 3
                ),
            )
        else:
            merged_ids = list(dict.fromkeys(existing.supporting_entry_ids + supporting_ids))
            page = KnowledgePage(
                page_id=existing.page_id,
                title=existing.title,
                domain=existing.domain,
                bank_id=existing.bank_id,
                summary=(
                    f"Distilled mental model for '{existing.title}', refined over "
                    f"{len(merged_ids)} retained memories across multiple reflections."
                ),
                key_points=list(dict.fromkeys(existing.key_points + key_points)),
                supporting_entry_ids=merged_ids,
                confidence=round(min(1.0, existing.confidence + 0.05), 3),
                created_at=existing.created_at,
                updated_at=datetime.utcnow(),
            )

        self._persist_page(page, user_id)
        return page

    def _find_page(
        self, title: str, bank_id: Optional[str]
    ) -> Optional[KnowledgePage]:
        for entry in self._engine.semantic.all_entries():
            page = KnowledgePage.from_metadata_entry(entry)
            if (
                page is not None
                and page.title.lower() == title.lower()
                and page.bank_id == bank_id
            ):
                return page
        return None

    def _persist_page(self, page: KnowledgePage, user_id: Optional[str]) -> None:
        """
        Persist a knowledge page as a tagged semantic entry. Replaces any
        prior persisted copy of the same page_id so reflection merges rather
        than duplicates.
        """
        for entry in self._engine.semantic.all_entries(user_id=user_id):
            meta = entry.metadata or {}
            if meta.get("kind") == KNOWLEDGE_PAGE_KIND and meta.get("page_id") == page.page_id:
                self._engine.semantic.forget(entry.id)

        body = f"[Knowledge Page] {page.title}\n\n{page.summary}"
        if page.key_points:
            body += "\n\nKey points:\n" + "\n".join(f"- {kp}" for kp in page.key_points)

        tags = ["knowledge_page"]
        if page.bank_id:
            tags.append(_bank_tag(page.bank_id))

        self._engine.semantic.store(
            content=body,
            tags=tags,
            importance=page.confidence,
            user_id=user_id,
            metadata={
                "kind": KNOWLEDGE_PAGE_KIND,
                "source": LEARNING_LAYER_SOURCE,
                "page_id": page.page_id,
                "title": page.title,
                "domain": page.domain,
                "bank_id": page.bank_id,
                "confidence": page.confidence,
                "key_points": page.key_points,
                "supporting_entry_ids": page.supporting_entry_ids,
                "created_at": page.created_at.isoformat(),
                "updated_at": page.updated_at.isoformat(),
            },
        )

    def _bank_entries(
        self, bank_id: str, user_id: Optional[str]
    ) -> List[MemoryEntry]:
        """All non-knowledge-page entries retained in a bank."""
        entries = []
        for entry in self._engine.semantic.all_entries(user_id=user_id):
            if (entry.metadata or {}).get("kind") == KNOWLEDGE_PAGE_KIND:
                continue
            if self._entry_in_bank(entry, bank_id):
                entries.append(entry)
        return entries
