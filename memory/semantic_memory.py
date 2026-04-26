"""
Semantic Memory — Long-term knowledge store with SQLite backend.
Inspired by Hermes Agent's semantic memory layer.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .memory_types import MemoryEntry, MemorySearchResult, MemoryType

# Legal concept keywords for auto-indexing
LEGAL_KEYWORDS = [
    "plaintiff", "defendant", "statute", "ordinance", "regulation",
    "jurisdiction", "injunction", "affidavit", "deposition", "discovery",
    "pleading", "complaint", "motion", "brief", "appeal", "verdict",
    "settlement", "damages", "liability", "negligence", "contract",
    "tort", "habeas corpus", "subpoena", "warrant", "indictment",
    "arraignment", "bail", "probation", "parole", "custody",
]


class SemanticMemory:
    """
    Long-term knowledge store using SQLite with TF-IDF similarity search.
    Stores facts, concepts, and domain knowledge persistently across sessions.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_dir = Path.home() / ".sintra" / "memory"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "semantic.db")
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT DEFAULT 'semantic',
                    tags TEXT DEFAULT '[]',
                    importance REAL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    embedding_vector TEXT,
                    user_id TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS legal_index (
                    memory_id TEXT NOT NULL,
                    concept TEXT NOT NULL,
                    FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_legal_concept ON legal_index(concept)
            """)
            conn.commit()

    # ------------------------------------------------------------------ #
    #  Tokenization & TF-IDF helpers                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        text = text.lower()
        tokens = re.findall(r"[a-z0-9]+", text)
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "shall", "should", "may", "might", "must", "can", "could",
            "of", "in", "on", "at", "to", "for", "with", "by", "from",
            "and", "or", "not", "that", "this", "it", "its",
        }
        return [t for t in tokens if t not in stopwords and len(t) > 1]

    def _build_tf(self, tokens: List[str]) -> Dict[str, float]:
        counts = Counter(tokens)
        total = max(len(tokens), 1)
        return {word: count / total for word, count in counts.items()}

    def _cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        shared = set(vec_a) & set(vec_b)
        if not shared:
            return 0.0
        dot = sum(vec_a[w] * vec_b[w] for w in shared)
        mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def _score(self, query: str, content: str, tags: List[str]) -> float:
        q_tokens = self._tokenize(query)
        c_tokens = self._tokenize(content + " " + " ".join(tags))
        q_tf = self._build_tf(q_tokens)
        c_tf = self._build_tf(c_tokens)
        return self._cosine_similarity(q_tf, c_tf)

    # ------------------------------------------------------------------ #
    #  Legal auto-indexing                                                  #
    # ------------------------------------------------------------------ #

    def _extract_legal_concepts(self, content: str) -> List[str]:
        lower = content.lower()
        found = []
        for kw in LEGAL_KEYWORDS:
            if kw in lower:
                found.append(kw)
        # Extract case numbers like "2024-CV-1234" or "Case No. 1234"
        case_nums = re.findall(r"\b\d{4}-[A-Z]+-\d+\b|\bcase\s+no\.?\s*\d+\b", lower)
        found.extend(case_nums)
        # Extract statute references like "18 U.S.C. § 1234"
        statutes = re.findall(r"\d+\s+u\.s\.c\.?\s+§?\s*\d+", lower)
        found.extend(statutes)
        return list(set(found))

    def _index_legal(self, memory_id: str, content: str) -> None:
        concepts = self._extract_legal_concepts(content)
        if not concepts:
            return
        with self._get_conn() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO legal_index(memory_id, concept) VALUES (?, ?)",
                [(memory_id, c) for c in concepts],
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def store(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """Save a fact, concept, or piece of knowledge."""
        if tags is None:
            tags = []
        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.SEMANTIC,
            tags=tags,
            importance=max(0.0, min(1.0, importance)),
            user_id=user_id,
            metadata=metadata or {},
        )
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO memories
                    (id, content, memory_type, tags, importance, created_at,
                     last_accessed, access_count, embedding_vector, user_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.content,
                    entry.memory_type.value,
                    json.dumps(entry.tags),
                    entry.importance,
                    now,
                    now,
                    0,
                    json.dumps(entry.embedding_vector) if entry.embedding_vector else None,
                    entry.user_id,
                    json.dumps(entry.metadata),
                ),
            )
            conn.commit()
        self._index_legal(entry.id, content)
        return entry

    def recall(
        self,
        query: str,
        top_k: int = 10,
        user_id: Optional[str] = None,
        min_importance: float = 0.0,
    ) -> List[MemorySearchResult]:
        """Retrieve semantically similar memories using TF-IDF cosine similarity."""
        with self._get_conn() as conn:
            if user_id:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE user_id = ? AND importance >= ? ORDER BY importance DESC",
                    (user_id, min_importance),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE importance >= ? ORDER BY importance DESC",
                    (min_importance,),
                ).fetchall()

        results: List[MemorySearchResult] = []
        for row in rows:
            tags = json.loads(row["tags"])
            score = self._score(query, row["content"], tags)
            if score > 0:
                entry = MemoryEntry(
                    id=row["id"],
                    content=row["content"],
                    memory_type=MemoryType(row["memory_type"]),
                    tags=tags,
                    importance=row["importance"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    last_accessed=datetime.fromisoformat(row["last_accessed"]),
                    access_count=row["access_count"],
                    embedding_vector=json.loads(row["embedding_vector"]) if row["embedding_vector"] else None,
                    user_id=row["user_id"],
                    metadata=json.loads(row["metadata"]),
                )
                results.append(MemorySearchResult(entry=entry, relevance_score=score, context=query))

        # Sort by combined relevance + importance score
        results.sort(key=lambda r: r.relevance_score * 0.7 + r.entry.importance * 0.3, reverse=True)
        top = results[:top_k]

        # Update access metadata for returned entries
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            for r in top:
                conn.execute(
                    "UPDATE memories SET last_accessed=?, access_count=access_count+1 WHERE id=?",
                    (now, r.entry.id),
                )
            conn.commit()

        return top

    def forget(self, entry_id: str) -> bool:
        """Remove a memory by ID."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id=?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def consolidate(self) -> Dict[str, int]:
        """
        Merge near-duplicate memories and promote frequently-accessed ones.
        Returns stats on consolidation actions.
        """
        stats = {"merged": 0, "promoted": 0}
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY created_at ASC"
            ).fetchall()

        # Find duplicates using cosine similarity > 0.95
        entries: List[Tuple] = [(r["id"], r["content"], json.loads(r["tags"]), r["importance"]) for r in rows]
        to_delete: List[str] = []
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                if entries[j][0] in to_delete:
                    continue
                score = self._score(entries[i][1], entries[j][1], entries[j][2])
                if score > 0.95:
                    # Keep higher importance one
                    if entries[i][3] >= entries[j][3]:
                        to_delete.append(entries[j][0])
                    else:
                        to_delete.append(entries[i][0])
                    stats["merged"] += 1

        # Promote frequently accessed memories
        with self._get_conn() as conn:
            for del_id in to_delete:
                conn.execute("DELETE FROM memories WHERE id=?", (del_id,))
            # Boost importance for entries accessed >5 times
            conn.execute(
                """
                UPDATE memories SET importance = MIN(1.0, importance + 0.1)
                WHERE access_count > 5 AND importance < 1.0
                """
            )
            stats["promoted"] = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE access_count > 5"
            ).fetchone()[0]
            conn.commit()

        return stats

    def get_by_id(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a specific memory entry by ID."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id=?", (entry_id,)).fetchone()
        if not row:
            return None
        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            tags=json.loads(row["tags"]),
            importance=row["importance"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]),
            access_count=row["access_count"],
            embedding_vector=json.loads(row["embedding_vector"]) if row["embedding_vector"] else None,
            user_id=row["user_id"],
            metadata=json.loads(row["metadata"]),
        )

    def forget_user(self, user_id: str) -> int:
        """Delete all memories for a user (GDPR compliance)."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE user_id=?", (user_id,))
            conn.commit()
            return cursor.rowcount

    def export_to_json(self, path: str, user_id: Optional[str] = None) -> int:
        """Export memories to a JSON file. Returns number of entries exported."""
        with self._get_conn() as conn:
            if user_id:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE user_id=?", (user_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM memories").fetchall()

        entries = []
        for row in rows:
            entries.append({
                "id": row["id"],
                "content": row["content"],
                "memory_type": row["memory_type"],
                "tags": json.loads(row["tags"]),
                "importance": row["importance"],
                "created_at": row["created_at"],
                "last_accessed": row["last_accessed"],
                "access_count": row["access_count"],
                "user_id": row["user_id"],
                "metadata": json.loads(row["metadata"]),
            })

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
        return len(entries)

    def import_from_json(self, path: str) -> int:
        """Import memories from a JSON file. Returns number imported."""
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)

        imported = 0
        with self._get_conn() as conn:
            for data in entries:
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO memories
                            (id, content, memory_type, tags, importance, created_at,
                             last_accessed, access_count, user_id, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            data.get("id", str(uuid.uuid4())),
                            data["content"],
                            data.get("memory_type", "semantic"),
                            json.dumps(data.get("tags", [])),
                            data.get("importance", 0.5),
                            data.get("created_at", datetime.utcnow().isoformat()),
                            data.get("last_accessed", datetime.utcnow().isoformat()),
                            data.get("access_count", 0),
                            data.get("user_id"),
                            json.dumps(data.get("metadata", {})),
                        ),
                    )
                    imported += 1
                except Exception:
                    continue
            conn.commit()
        return imported

    def count(self, user_id: Optional[str] = None) -> int:
        """Return total memory count."""
        with self._get_conn() as conn:
            if user_id:
                return conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE user_id=?", (user_id,)
                ).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    def all_entries(self, user_id: Optional[str] = None) -> List[MemoryEntry]:
        """Return all stored entries."""
        with self._get_conn() as conn:
            if user_id:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE user_id=?", (user_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM memories").fetchall()
        return [
            MemoryEntry(
                id=r["id"],
                content=r["content"],
                memory_type=MemoryType(r["memory_type"]),
                tags=json.loads(r["tags"]),
                importance=r["importance"],
                created_at=datetime.fromisoformat(r["created_at"]),
                last_accessed=datetime.fromisoformat(r["last_accessed"]),
                access_count=r["access_count"],
                user_id=r["user_id"],
                metadata=json.loads(r["metadata"]),
            )
            for r in rows
        ]
