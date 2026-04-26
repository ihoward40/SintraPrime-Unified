"""
Vector Store — In-memory + persistent vector store.
Uses numpy cosine similarity. Falls back to pure-python if numpy unavailable.
Optionally integrates ChromaDB when available.
Persists to JSON for portability.
"""

import json
import math
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

DEFAULT_PERSIST_PATH = str(
    Path(__file__).parent / "knowledge_base.json"
)


@dataclass
class VectorEntry:
    """A single vector entry in the store."""
    id: str
    embedding: list[float]
    content: str
    metadata: dict


class VectorStore:
    """
    Lightweight vector store — minimal external dependencies.

    Search strategy (in priority order):
    1. ChromaDB (if available and use_chroma=True)
    2. numpy cosine similarity matrix
    3. Pure-python cosine similarity (always available)

    Persistence: JSON file at persist_path.
    """

    def __init__(
        self,
        persist_path: Optional[str] = None,
        use_chroma: bool = False,
    ):
        self.entries: list[VectorEntry] = []
        self.persist_path = persist_path or DEFAULT_PERSIST_PATH
        self.use_chroma = use_chroma
        self._matrix = None          # numpy matrix cache (n × d)
        self._chroma_collection = None
        self._last_updated: Optional[str] = None

        # Try to init ChromaDB
        if use_chroma:
            self._init_chroma()

    # ------------------------------------------------------------------ #
    #  ChromaDB integration                                               #
    # ------------------------------------------------------------------ #

    def _init_chroma(self) -> None:
        try:
            import chromadb  # type: ignore

            client = chromadb.PersistentClient(
                path=str(Path(self.persist_path).parent / "chroma_db")
            )
            self._chroma_collection = client.get_or_create_collection(
                name="sintra_legal",
                metadata={"hnsw:space": "cosine"},
            )
        except ImportError:
            self.use_chroma = False
        except Exception as exc:
            print(f"[VectorStore] ChromaDB init failed: {exc}. Falling back to numpy.")
            self.use_chroma = False

    # ------------------------------------------------------------------ #
    #  Core CRUD                                                           #
    # ------------------------------------------------------------------ #

    def add(self, entry: VectorEntry) -> None:
        """Add a document embedding. Deduplicates by id."""
        # Remove existing entry with same id
        self.entries = [e for e in self.entries if e.id != entry.id]
        self.entries.append(entry)
        self._matrix = None  # invalidate cache
        self._last_updated = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if self.use_chroma and self._chroma_collection is not None:
            try:
                self._chroma_collection.upsert(
                    ids=[entry.id],
                    embeddings=[entry.embedding],
                    documents=[entry.content],
                    metadatas=[entry.metadata],
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[VectorStore] ChromaDB upsert failed: {exc}")

    def add_batch(self, entries: list[VectorEntry]) -> None:
        """Batch add for efficiency."""
        for entry in entries:
            self.add(entry)

    def get(self, entry_id: str) -> Optional[VectorEntry]:
        """Retrieve a single entry by id."""
        for e in self.entries:
            if e.id == entry_id:
                return e
        return None

    def delete(self, entry_id: str) -> bool:
        """Remove an entry by id. Returns True if removed."""
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.id != entry_id]
        self._matrix = None
        removed = len(self.entries) < before
        if removed and self.use_chroma and self._chroma_collection is not None:
            try:
                self._chroma_collection.delete(ids=[entry_id])
            except Exception:
                pass
        return removed

    def clear(self) -> None:
        """Remove all entries."""
        self.entries.clear()
        self._matrix = None

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> list[tuple[VectorEntry, float]]:
        """
        Cosine similarity search with optional metadata filtering.

        Args:
            query_embedding:  The query vector.
            top_k:            Maximum number of results to return.
            filter_metadata:  Key-value pairs that must match entry metadata
                              (substring match for strings, exact for others).

        Returns:
            List of (VectorEntry, score) sorted descending by cosine similarity.
        """
        if not self.entries:
            return []

        # Apply metadata filter first
        candidates = self._filter_entries(filter_metadata)
        if not candidates:
            return []

        # ChromaDB path
        if self.use_chroma and self._chroma_collection is not None and not filter_metadata:
            return self._chroma_search(query_embedding, top_k)

        # numpy path
        try:
            import numpy as np  # type: ignore

            return self._numpy_search(query_embedding, candidates, top_k, np)
        except ImportError:
            return self._python_search(query_embedding, candidates, top_k)

    def _filter_entries(self, filter_metadata: Optional[dict]) -> list[VectorEntry]:
        if not filter_metadata:
            return list(self.entries)
        result = []
        for entry in self.entries:
            match = True
            for key, val in filter_metadata.items():
                entry_val = entry.metadata.get(key)
                if entry_val is None:
                    match = False
                    break
                if isinstance(val, str) and isinstance(entry_val, str):
                    if val.lower() not in entry_val.lower():
                        match = False
                        break
                elif entry_val != val:
                    match = False
                    break
            if match:
                result.append(entry)
        return result

    def _numpy_search(
        self, query: list[float], candidates: list[VectorEntry], top_k: int, np
    ) -> list[tuple[VectorEntry, float]]:
        matrix = np.array([e.embedding for e in candidates], dtype=np.float32)
        q = np.array(query, dtype=np.float32)

        # Cosine similarity
        norm_matrix = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
        norm_q = np.linalg.norm(q) + 1e-10
        scores = (matrix / norm_matrix) @ (q / norm_q)

        top_indices = np.argsort(-scores)[:top_k]
        return [(candidates[i], float(scores[i])) for i in top_indices]

    def _python_search(
        self, query: list[float], candidates: list[VectorEntry], top_k: int
    ) -> list[tuple[VectorEntry, float]]:
        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a)) + 1e-10
            norm_b = math.sqrt(sum(y * y for y in b)) + 1e-10
            return dot / (norm_a * norm_b)

        scored = [(e, cosine(query, e.embedding)) for e in candidates]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:top_k]

    def _chroma_search(
        self, query: list[float], top_k: int
    ) -> list[tuple[VectorEntry, float]]:
        try:
            results = self._chroma_collection.query(
                query_embeddings=[query],
                n_results=min(top_k, self._chroma_collection.count()),
            )
            entries = []
            ids = results["ids"][0]
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]
            for eid, doc, meta, dist in zip(ids, docs, metas, dists):
                entry = VectorEntry(
                    id=eid,
                    embedding=[],
                    content=doc,
                    metadata=meta,
                )
                score = 1.0 - dist  # ChromaDB returns distance for cosine
                entries.append((entry, score))
            return entries
        except Exception as exc:
            print(f"[VectorStore] ChromaDB search error: {exc}")
            return []

    # ------------------------------------------------------------------ #
    #  Persistence                                                         #
    # ------------------------------------------------------------------ #

    def save(self) -> None:
        """Persist all entries to JSON file."""
        path = Path(self.persist_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0",
            "last_updated": self._last_updated,
            "entries": [asdict(e) for e in self.entries],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[VectorStore] Saved {len(self.entries)} entries to {path}")

    def load(self) -> None:
        """Load entries from JSON file."""
        path = Path(self.persist_path)
        if not path.exists():
            print(f"[VectorStore] No persisted store found at {path}")
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        self._last_updated = payload.get("last_updated")
        self.entries = [
            VectorEntry(**entry) for entry in payload.get("entries", [])
        ]
        self._matrix = None
        print(f"[VectorStore] Loaded {len(self.entries)} entries from {path}")

    # ------------------------------------------------------------------ #
    #  Stats                                                               #
    # ------------------------------------------------------------------ #

    def stats(self) -> dict:
        """Return store statistics."""
        categories: dict[str, int] = {}
        jurisdictions: dict[str, int] = {}
        for entry in self.entries:
            cat = entry.metadata.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
            jur = entry.metadata.get("jurisdiction", "unknown")
            jurisdictions[jur] = jurisdictions.get(jur, 0) + 1

        return {
            "total_documents": len(self.entries),
            "categories": categories,
            "jurisdictions": jurisdictions,
            "last_updated": self._last_updated,
            "persist_path": self.persist_path,
            "use_chroma": self.use_chroma,
        }

    def __len__(self) -> int:
        return len(self.entries)

    def __repr__(self) -> str:
        return f"<VectorStore entries={len(self.entries)} path={self.persist_path}>"
