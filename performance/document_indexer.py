"""
SintraPrime-Unified: Fast Legal Document Indexer
Full-text search with BM25 ranking, inverted index, and incremental indexing.
Pure Python, no Elasticsearch required.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants & Stop Words
# ---------------------------------------------------------------------------

LEGAL_STOP_WORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "shall", "should", "may", "might", "can", "could", "it", "its",
    "this", "that", "these", "those", "not", "no", "nor", "so", "yet",
    "both", "either", "neither", "such", "than", "then", "too", "very",
    "herein", "hereof", "hereto", "hereby", "therein", "thereof", "thereto",
    "hereunder", "thereunder",
}

DEFAULT_K1 = 1.5
DEFAULT_B = 0.75
DEFAULT_TOP_K = 10
MAX_SNIPPET_LENGTH = 300
MIN_TERM_LENGTH = 2


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IndexDocument:
    doc_id: str
    title: str
    content: str
    doc_type: str = "generic"       # trust / case_law / contract / regulation / etc.
    jurisdiction: str = ""
    date: str = ""
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: str = ""
    indexed_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.checksum:
            self.checksum = hashlib.sha256(self.content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("content")   # Don't serialize full content in listings
        return d


@dataclass
class SearchResult:
    doc_id: str
    title: str
    doc_type: str
    score: float
    snippet: str
    matched_terms: List[str]
    rank: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexStats:
    total_documents: int
    total_terms: int
    total_postings: int
    avg_doc_length: float
    index_size_bytes: int
    last_updated: float


# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-']*[a-zA-Z0-9]|[a-zA-Z]")


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase tokens, removing stop words."""
    return [
        tok.lower()
        for tok in _TOKEN_RE.findall(text)
        if len(tok) >= MIN_TERM_LENGTH and tok.lower() not in LEGAL_STOP_WORDS
    ]


def stem(token: str) -> str:
    """
    Lightweight suffix-stripping stemmer (no NLTK required).
    Handles common English suffixes.
    """
    if len(token) <= 4:
        return token
    for suffix, replacement in [
        ("ization", "ize"), ("isation", "ize"), ("ations", "ate"),
        ("ation", "ate"), ("ities", "ity"), ("iness", "y"),
        ("ment", ""), ("ness", ""), ("ting", "t"), ("ing", ""),
        ("tion", "t"), ("ions", "ion"), ("ies", "y"),
        ("ed", ""), ("er", ""), ("ly", ""), ("al", ""), ("est", ""),
    ]:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[:-len(suffix)] + replacement
    return token


def process_text(text: str) -> List[str]:
    """Full text processing pipeline: tokenize + stem."""
    return [stem(t) for t in tokenize(text)]


def extract_snippet(content: str, query_terms: List[str], max_len: int = MAX_SNIPPET_LENGTH) -> str:
    """Extract a relevant snippet from content around matched terms."""
    content_lower = content.lower()
    best_pos = -1
    for term in query_terms:
        pos = content_lower.find(term.lower())
        if pos >= 0:
            best_pos = pos
            break

    if best_pos < 0:
        snippet = content[:max_len]
    else:
        start = max(0, best_pos - 50)
        end = min(len(content), start + max_len)
        snippet = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")

    return snippet.replace("\n", " ").strip()


# ---------------------------------------------------------------------------
# Inverted Index
# ---------------------------------------------------------------------------

class InvertedIndex:
    """
    Core inverted index data structure.
    Stores: term → {doc_id → [positions]}
    """

    def __init__(self):
        # term → {doc_id: [positions]}
        self._index: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))
        self._doc_lengths: Dict[str, int] = {}
        self._total_terms = 0

    def add_document(self, doc_id: str, terms: List[str]):
        """Index terms for a document (positional)."""
        if doc_id in self._doc_lengths:
            self.remove_document(doc_id)

        for pos, term in enumerate(terms):
            self._index[term][doc_id].append(pos)
        self._doc_lengths[doc_id] = len(terms)
        self._total_terms += len(terms)

    def remove_document(self, doc_id: str):
        """Remove a document from the index."""
        terms_to_clean = []
        for term, postings in self._index.items():
            if doc_id in postings:
                del postings[doc_id]
                if not postings:
                    terms_to_clean.append(term)
        for term in terms_to_clean:
            del self._index[term]

        old_len = self._doc_lengths.pop(doc_id, 0)
        self._total_terms -= old_len

    def get_postings(self, term: str) -> Dict[str, List[int]]:
        return dict(self._index.get(term, {}))

    def document_frequency(self, term: str) -> int:
        return len(self._index.get(term, {}))

    def term_frequency(self, term: str, doc_id: str) -> int:
        return len(self._index.get(term, {}).get(doc_id, []))

    @property
    def doc_count(self) -> int:
        return len(self._doc_lengths)

    @property
    def avg_doc_length(self) -> float:
        if not self._doc_lengths:
            return 0.0
        return sum(self._doc_lengths.values()) / len(self._doc_lengths)

    def get_doc_length(self, doc_id: str) -> int:
        return self._doc_lengths.get(doc_id, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": {term: dict(postings) for term, postings in self._index.items()},
            "doc_lengths": dict(self._doc_lengths),
            "total_terms": self._total_terms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvertedIndex":
        idx = cls()
        for term, postings in data.get("index", {}).items():
            for doc_id, positions in postings.items():
                idx._index[term][doc_id] = positions
        idx._doc_lengths = data.get("doc_lengths", {})
        idx._total_terms = data.get("total_terms", 0)
        return idx


# ---------------------------------------------------------------------------
# BM25 Scorer
# ---------------------------------------------------------------------------

class BM25Scorer:
    """BM25 relevance scorer for ranked retrieval."""

    def __init__(self, k1: float = DEFAULT_K1, b: float = DEFAULT_B):
        self.k1 = k1
        self.b = b

    def score(
        self,
        query_terms: List[str],
        doc_id: str,
        index: InvertedIndex,
    ) -> float:
        n = index.doc_count
        if n == 0:
            return 0.0

        avg_dl = index.avg_doc_length
        dl = index.get_doc_length(doc_id)

        total_score = 0.0
        for term in query_terms:
            tf = index.term_frequency(term, doc_id)
            df = index.document_frequency(term)
            if tf == 0 or df == 0:
                continue
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
            tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * dl / max(avg_dl, 1)))
            total_score += idf * tf_norm

        return total_score

    def rank(
        self,
        query_terms: List[str],
        candidate_doc_ids: Iterable[str],
        index: InvertedIndex,
        top_k: int = DEFAULT_TOP_K,
    ) -> List[Tuple[str, float]]:
        """Return top_k (doc_id, score) pairs sorted by score descending."""
        scores = [(doc_id, self.score(query_terms, doc_id, index)) for doc_id in candidate_doc_ids]
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]


# ---------------------------------------------------------------------------
# Main DocumentIndexer
# ---------------------------------------------------------------------------

class DocumentIndexer:
    """
    Fast full-text search indexer for legal document collections.
    Features: BM25 ranking, incremental updates, compression, persistence.
    """

    def __init__(
        self,
        index_path: Optional[str] = None,
        k1: float = DEFAULT_K1,
        b: float = DEFAULT_B,
    ):
        self.index_path = Path(index_path) if index_path else None
        self._index = InvertedIndex()
        self._docs: Dict[str, IndexDocument] = {}
        self._scorer = BM25Scorer(k1=k1, b=b)
        self._dirty = False
        self._last_saved: float = 0.0
        self._indexed_checksums: Dict[str, str] = {}  # doc_id → checksum
        self._operation_log: List[Dict[str, Any]] = []

    def add_document(self, doc: IndexDocument) -> bool:
        """
        Add or update a document. Returns True if indexed (False if unchanged).
        Supports incremental indexing: skips unchanged documents.
        """
        existing_checksum = self._indexed_checksums.get(doc.doc_id)
        if existing_checksum == doc.checksum:
            return False   # Unchanged, skip

        # Remove old index entries if re-indexing
        if doc.doc_id in self._docs:
            self._index.remove_document(doc.doc_id)

        # Process and index
        full_text = f"{doc.title} {doc.content} {doc.doc_type} {doc.jurisdiction}"
        terms = process_text(full_text)
        self._index.add_document(doc.doc_id, terms)
        self._docs[doc.doc_id] = doc
        self._indexed_checksums[doc.doc_id] = doc.checksum
        self._dirty = True
        self._operation_log.append({
            "op": "add",
            "doc_id": doc.doc_id,
            "timestamp": time.time(),
        })
        return True

    def add_documents(self, docs: Iterable[IndexDocument]) -> Dict[str, int]:
        """Bulk add documents. Returns {added, skipped, total}."""
        added = skipped = 0
        for doc in docs:
            if self.add_document(doc):
                added += 1
            else:
                skipped += 1
        return {"added": added, "skipped": skipped, "total": added + skipped}

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the index."""
        if doc_id not in self._docs:
            return False
        self._index.remove_document(doc_id)
        del self._docs[doc_id]
        self._indexed_checksums.pop(doc_id, None)
        self._dirty = True
        self._operation_log.append({"op": "remove", "doc_id": doc_id, "timestamp": time.time()})
        return True

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        doc_type_filter: Optional[str] = None,
        jurisdiction_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Full-text search with BM25 ranking.
        Returns up to top_k results with snippet and matched terms.
        """
        if not query.strip():
            return []

        query_tokens = tokenize(query)
        query_terms = [stem(t) for t in query_tokens]

        if not query_terms:
            return []

        # Find candidate docs (union of postings lists)
        candidate_ids: Set[str] = set()
        matched_terms_per_doc: Dict[str, List[str]] = defaultdict(list)
        for term in query_terms:
            postings = self._index.get_postings(term)
            for doc_id in postings:
                candidate_ids.add(doc_id)
                matched_terms_per_doc[doc_id].append(term)

        # Apply filters
        if doc_type_filter:
            candidate_ids = {d for d in candidate_ids
                             if self._docs.get(d, IndexDocument("", "", "", "")).doc_type == doc_type_filter}
        if jurisdiction_filter:
            candidate_ids = {d for d in candidate_ids
                             if self._docs.get(d, IndexDocument("", "", "", "")).jurisdiction == jurisdiction_filter}

        if not candidate_ids:
            return []

        # BM25 rank
        ranked = self._scorer.rank(query_terms, candidate_ids, self._index, top_k=top_k)

        results = []
        for rank, (doc_id, score) in enumerate(ranked, start=1):
            doc = self._docs.get(doc_id)
            if doc is None:
                continue
            results.append(SearchResult(
                doc_id=doc_id,
                title=doc.title,
                doc_type=doc.doc_type,
                score=round(score, 4),
                snippet=extract_snippet(doc.content, query_tokens),
                matched_terms=list(set(matched_terms_per_doc[doc_id])),
                rank=rank,
                metadata=doc.metadata,
            ))

        return results

    def get_document(self, doc_id: str) -> Optional[IndexDocument]:
        return self._docs.get(doc_id)

    def list_documents(self, doc_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        docs = list(self._docs.values())
        if doc_type:
            docs = [d for d in docs if d.doc_type == doc_type]
        return [d.to_dict() for d in docs[:limit]]

    @property
    def stats(self) -> IndexStats:
        index_dict = self._index.to_dict()
        size = sum(sys.getsizeof(v) for v in index_dict.values()) if index_dict else 0
        return IndexStats(
            total_documents=len(self._docs),
            total_terms=len(self._index._index),
            total_postings=sum(len(p) for p in self._index._index.values()),
            avg_doc_length=round(self._index.avg_doc_length, 2),
            index_size_bytes=size,
            last_updated=self._last_saved or time.time(),
        )

    # ------------------------------------------------------------------
    # Persistence with compression
    # ------------------------------------------------------------------

    def save(self, path: Optional[str] = None, compress: bool = True):
        """Save index to disk with optional gzip compression."""
        save_path = Path(path) if path else self.index_path
        if save_path is None:
            raise ValueError("No index_path configured")
        save_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "saved_at": time.time(),
            "index": self._index.to_dict(),
            "docs": {doc_id: asdict(doc) for doc_id, doc in self._docs.items()},
            "checksums": self._indexed_checksums,
        }
        payload = json.dumps(data, default=str).encode("utf-8")

        if compress:
            with gzip.open(str(save_path) + ".gz", "wb") as f:
                f.write(payload)
        else:
            save_path.write_bytes(payload)

        self._dirty = False
        self._last_saved = time.time()

    def load(self, path: Optional[str] = None, compressed: bool = True):
        """Load index from disk."""
        load_path = Path(path) if path else self.index_path
        if load_path is None:
            raise ValueError("No index_path configured")

        if compressed:
            gz_path = str(load_path) + ".gz"
            with gzip.open(gz_path, "rb") as f:
                payload = f.read()
        else:
            payload = load_path.read_bytes()

        data = json.loads(payload.decode("utf-8"))
        self._index = InvertedIndex.from_dict(data["index"])
        self._docs = {}
        for doc_id, doc_data in data.get("docs", {}).items():
            self._docs[doc_id] = IndexDocument(**{k: v for k, v in doc_data.items()
                                                   if k in IndexDocument.__dataclass_fields__})
        self._indexed_checksums = data.get("checksums", {})
        self._dirty = False
        self._last_saved = data.get("saved_at", 0.0)

    def export_json(self) -> str:
        """Export the full index to JSON string."""
        return json.dumps({
            "stats": asdict(self.stats),
            "documents": self.list_documents(limit=10000),
        }, default=str, indent=2)


# ---------------------------------------------------------------------------
# Batch indexing helpers
# ---------------------------------------------------------------------------

def index_from_dict_list(records: List[Dict[str, Any]]) -> DocumentIndexer:
    """Create and populate an indexer from a list of dicts."""
    indexer = DocumentIndexer()
    docs = []
    for rec in records:
        docs.append(IndexDocument(
            doc_id=rec.get("id", hashlib.sha256(rec.get("content", "").encode()).hexdigest()[:12]),
            title=rec.get("title", "Untitled"),
            content=rec.get("content", ""),
            doc_type=rec.get("doc_type", "generic"),
            jurisdiction=rec.get("jurisdiction", ""),
            date=rec.get("date", ""),
            source=rec.get("source", ""),
            metadata=rec.get("metadata", {}),
        ))
    indexer.add_documents(docs)
    return indexer


# Needed for stats property
import sys


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🔍 SintraPrime Document Indexer Demo")
    records = [
        {"id": "t1", "title": "Smith Family Trust", "content": "This irrevocable trust is established for the benefit of Jane Smith. The trustee shall distribute income annually. The grantor hereby transfers all assets.", "doc_type": "trust"},
        {"id": "t2", "title": "Johnson Revocable Trust", "content": "The grantor reserves the right to revoke this trust at any time. The trustee shall manage the corpus prudently.", "doc_type": "trust"},
        {"id": "c1", "title": "Doe v. United States", "content": "The court held that the statute does not preempt state law in matters of probate and estate administration. Affirmed.", "doc_type": "case_law"},
        {"id": "c2", "title": "Estate of Wilson", "content": "The probate court found the testator lacked testamentary capacity at the time of execution. The will is hereby declared void.", "doc_type": "case_law"},
        {"id": "r1", "title": "SEC Rule 10b-5", "content": "It shall be unlawful for any person to employ any device, scheme, or artifice to defraud in connection with the purchase or sale of any security.", "doc_type": "regulation"},
    ]

    indexer = index_from_dict_list(records)
    print(f"Indexed {indexer.stats.total_documents} documents, {indexer.stats.total_terms} terms")

    results = indexer.search("trust beneficiary estate")
    print(f"\nSearch 'trust beneficiary estate' → {len(results)} results:")
    for r in results:
        print(f"  [{r.rank}] {r.title} (score={r.score}) — {r.snippet[:80]}...")
