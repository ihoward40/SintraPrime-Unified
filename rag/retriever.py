"""
Legal-domain retriever with hybrid search and re-ranking.

Combines:
- Semantic search (cosine similarity on embeddings)
- Keyword search (BM25-style term frequency scoring)
- Domain-aware re-ranking (jurisdiction boost, recency, source authority)
"""

import asyncio
import math
import re
from typing import Optional

from .embedder import EmbeddingProvider
from .vector_store import VectorStore, VectorEntry


class LegalRetriever:
    """
    Retrieves relevant legal passages for a user query.

    Hybrid search strategy:
      final_score = α * semantic_score + (1-α) * bm25_score + boosts
    where boosts include jurisdiction match and source authority.
    """

    ALPHA = 0.7          # weight for semantic vs keyword
    BM25_K1 = 1.5        # BM25 saturation parameter
    BM25_B = 0.75        # BM25 length normalisation

    # Authority scores by source category
    AUTHORITY_SCORES = {
        "case_law": 0.15,
        "trust_law": 0.12,
        "legal_intelligence": 0.10,
        "federal_agencies": 0.10,
        "pdf_document": 0.05,
        "user_document": 0.03,
    }

    # Jurisdiction boost when query matches doc jurisdiction
    JURISDICTION_BOOST = 0.10

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: EmbeddingProvider,
        alpha: float = ALPHA,
    ):
        self.store = vector_store
        self.embedder = embedder
        self.alpha = alpha
        self._corpus_tf: list[dict[str, float]] = []   # per-doc term frequencies
        self._avg_doc_len: float = 0.0
        self._built = False

    # ------------------------------------------------------------------ #
    #  Index building (BM25 prep)                                         #
    # ------------------------------------------------------------------ #

    def build_bm25_index(self) -> None:
        """Pre-compute BM25 index over the current vector store contents."""
        entries = self.store.entries
        if not entries:
            self._built = True
            return

        self._corpus_tf = []
        total_len = 0
        for entry in entries:
            tokens = self._tokenize(entry.content)
            total_len += len(tokens)
            tf: dict[str, float] = {}
            for tok in tokens:
                tf[tok] = tf.get(tok, 0.0) + 1.0
            self._corpus_tf.append(tf)

        self._avg_doc_len = total_len / len(entries) if entries else 1.0
        self._built = True

    # ------------------------------------------------------------------ #
    #  Main retrieval API                                                  #
    # ------------------------------------------------------------------ #

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        jurisdiction: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        """
        Retrieve top_k relevant passages using hybrid search + re-ranking.

        Args:
            query:        Natural-language legal query.
            top_k:        Number of results to return.
            jurisdiction: Optional jurisdiction filter (e.g. 'federal', 'california').
            category:     Optional category filter (e.g. 'trust_law').

        Returns:
            List of dicts with keys: content, score, source, metadata.
        """
        if not self.store.entries:
            return []

        # Build BM25 index if needed
        if not self._built:
            self.build_bm25_index()

        # Metadata filter
        filter_meta = {}
        if jurisdiction:
            filter_meta["jurisdiction"] = jurisdiction
        if category:
            filter_meta["category"] = category

        # Semantic retrieval — get top_k * 3 candidates for re-ranking
        query_embedding = await self.embedder.embed(query)
        semantic_results = self.store.search(
            query_embedding,
            top_k=min(top_k * 3, len(self.store.entries)),
            filter_metadata=filter_meta if filter_meta else None,
        )

        # BM25 scoring for the candidates
        query_tokens = self._tokenize(query)
        entries = self.store.entries
        entry_index = {e.id: i for i, e in enumerate(entries)}

        results: list[dict] = []
        for entry, sem_score in semantic_results:
            idx = entry_index.get(entry.id)
            bm25 = self._bm25_score(query_tokens, idx) if idx is not None else 0.0

            # Hybrid score
            hybrid = self.alpha * sem_score + (1 - self.alpha) * bm25

            # Authority boost
            cat = entry.metadata.get("category", "")
            authority = self.AUTHORITY_SCORES.get(cat, 0.0)

            # Jurisdiction boost
            jur_boost = 0.0
            if jurisdiction and entry.metadata.get("jurisdiction") == jurisdiction:
                jur_boost = self.JURISDICTION_BOOST

            final_score = min(1.0, hybrid + authority + jur_boost)

            results.append(
                {
                    "content": entry.content,
                    "score": round(final_score, 4),
                    "semantic_score": round(float(sem_score), 4),
                    "bm25_score": round(bm25, 4),
                    "source": entry.metadata.get("source", "unknown"),
                    "metadata": entry.metadata,
                    "entry_id": entry.id,
                }
            )

        # Re-rank and deduplicate
        results.sort(key=lambda r: r["score"], reverse=True)
        seen_ids: set[str] = set()
        deduplicated: list[dict] = []
        for r in results:
            if r["entry_id"] not in seen_ids:
                seen_ids.add(r["entry_id"])
                deduplicated.append(r)
            if len(deduplicated) >= top_k:
                break

        return deduplicated

    # ------------------------------------------------------------------ #
    #  Specialised retrievers                                              #
    # ------------------------------------------------------------------ #

    async def retrieve_for_trust_law(self, question: str) -> list[dict]:
        """
        Specialised retrieval for trust law questions.
        Boosts trust_law and fiduciary-related results.
        """
        # Augment the query with trust-law domain terms
        augmented_query = (
            f"{question} trust fiduciary beneficiary trustee estate grantor"
        )
        results = await self.retrieve(
            augmented_query,
            top_k=10,
            category="trust_law",
        )
        # Fallback to general if no trust-specific results
        if len(results) < 3:
            general = await self.retrieve(augmented_query, top_k=10)
            seen = {r["entry_id"] for r in results}
            for r in general:
                if r["entry_id"] not in seen:
                    results.append(r)
                if len(results) >= 10:
                    break
        return results

    async def retrieve_precedents(self, case_facts: str) -> list[dict]:
        """
        Find relevant case law precedents for given facts.
        Retrieves from case_law category with legal-reasoning augmentation.
        """
        augmented = (
            f"{case_facts} precedent ruling decision court held affirmed reversed"
        )
        results = await self.retrieve(
            augmented,
            top_k=10,
            category="case_law",
        )
        # Also check general store if case_law is sparse
        if len(results) < 3:
            general = await self.retrieve(augmented, top_k=10)
            seen = {r["entry_id"] for r in results}
            for r in general:
                if r["entry_id"] not in seen and r["metadata"].get("category") == "case_law":
                    results.append(r)
        return results[:10]

    # ------------------------------------------------------------------ #
    #  BM25 helpers                                                        #
    # ------------------------------------------------------------------ #

    def _bm25_score(self, query_tokens: list[str], doc_idx: int) -> float:
        """Compute BM25 score for one document."""
        if not self._corpus_tf or doc_idx is None or doc_idx >= len(self._corpus_tf):
            return 0.0

        doc_tf = self._corpus_tf[doc_idx]
        doc_len = sum(doc_tf.values())
        N = len(self._corpus_tf)
        score = 0.0

        for tok in query_tokens:
            df = sum(1 for tf in self._corpus_tf if tok in tf)
            if df == 0:
                continue
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            tf_val = doc_tf.get(tok, 0.0)
            numerator = tf_val * (self.BM25_K1 + 1)
            denominator = tf_val + self.BM25_K1 * (
                1 - self.BM25_B + self.BM25_B * doc_len / self._avg_doc_len
            )
            score += idf * numerator / denominator

        # Normalise to [0, 1]
        max_possible = len(query_tokens) * math.log(N + 1)
        return score / (max_possible + 1e-10)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace + punctuation tokeniser."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return [t for t in text.split() if len(t) >= 2]
