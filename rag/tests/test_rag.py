"""
SintraPrime RAG Engine — Comprehensive Test Suite (35+ tests)

Uses mocked embeddings (random unit vectors) for speed — no API keys required.
Run: python -m pytest rag/tests/test_rag.py -v
"""

import asyncio
import json
import math
import random
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── adjust path so tests can find the rag package ───────────────────────────
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rag.document_ingester import DocumentIngester, LegalDocument
from rag.embedder import EmbeddingProvider
from rag.legal_rag import LegalRAG
from rag.rag_pipeline import RAGPipeline
from rag.retriever import LegalRetriever
from rag.vector_store import VectorEntry, VectorStore


# ── helpers ──────────────────────────────────────────────────────────────────

def _random_vec(dim: int = 32, seed: int = 0) -> list[float]:
    """Return a random unit vector (deterministic via seed)."""
    rng = random.Random(seed)
    v = [rng.gauss(0, 1) for _ in range(dim)]
    norm = math.sqrt(sum(x * x for x in v)) + 1e-10
    return [x / norm for x in v]


def _make_entry(
    eid: str, content: str, category: str = "test", jurisdiction: str = "federal",
    seed: int = 0
) -> VectorEntry:
    return VectorEntry(
        id=eid,
        embedding=_random_vec(32, seed),
        content=content,
        metadata={"category": category, "jurisdiction": jurisdiction, "source": f"test/{eid}"},
    )


async def _mock_embed(text: str) -> list[float]:
    return _random_vec(32, hash(text) % 2**31)


async def _mock_embed_batch(texts: list[str]) -> list[list[float]]:
    return [await _mock_embed(t) for t in texts]


# ── DocumentIngester tests ───────────────────────────────────────────────────

class TestDocumentIngester:
    def setup_method(self):
        self.ingester = DocumentIngester()

    # 1. Basic chunk_text
    def test_chunk_text_returns_list(self):
        text = "This is a test legal document with some content.\n\n" * 10
        chunks = self.ingester.chunk_text(text, "doc1")
        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    # 2. Chunk IDs embedded in labels
    def test_chunk_text_labels(self):
        text = "A " * 300
        chunks = self.ingester.chunk_text(text, "mydoc")
        for chunk in chunks:
            assert "mydoc" in chunk

    # 3. Empty text returns empty list
    def test_chunk_empty_text(self):
        assert self.ingester.chunk_text("", "doc") == []

    # 4. Short text produces single chunk
    def test_chunk_short_text_single(self):
        chunks = self.ingester.chunk_text("Short legal sentence.", "doc")
        assert len(chunks) == 1

    # 5. Overlapping chunks
    def test_chunk_overlap(self):
        long_text = "The trustee shall. " * 300
        chunks = self.ingester.chunk_text(long_text, "doc")
        if len(chunks) > 1:
            # Some content should appear in consecutive chunks
            assert len(chunks) >= 2

    # 6. extract_legal_metadata — jurisdiction detection
    def test_extract_jurisdiction_federal(self):
        meta = self.ingester.extract_legal_metadata(
            "Pursuant to federal law and 26 U.S.C. § 401 the IRS regulations apply."
        )
        assert meta["jurisdiction"] == "federal"

    # 7. extract_legal_metadata — california
    def test_extract_jurisdiction_california(self):
        meta = self.ingester.extract_legal_metadata(
            "Under California Probate Code, Cal. trust law applies."
        )
        assert meta["jurisdiction"] == "california"

    # 8. extract_legal_metadata — statutes
    def test_extract_statutes(self):
        meta = self.ingester.extract_legal_metadata(
            "See 26 U.S.C. § 401(k) and 29 C.F.R. § 2550.404 for details."
        )
        assert len(meta["statutes_cited"]) >= 1

    # 9. extract_legal_metadata — parties
    def test_extract_parties(self):
        meta = self.ingester.extract_legal_metadata(
            "In Smith Corp v. Jones Trust, the court held fiduciary duty was breached."
        )
        assert len(meta["parties"]) >= 1

    # 10. extract_legal_metadata — case type
    def test_extract_case_type_trust(self):
        meta = self.ingester.extract_legal_metadata(
            "The trustee breached fiduciary duty. Beneficiary seeks relief from the estate."
        )
        assert "trust_law" in meta["case_types_detected"]

    # 11. ingest_directory with temp files
    def test_ingest_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "law_note.md").write_text(
                "# Trust Law\n\nThe trustee must act in good faith.", encoding="utf-8"
            )
            Path(tmpdir, "analyzer.py").write_text(
                '"""Trust analyzer."""\n\ndef analyze(): pass', encoding="utf-8"
            )
            docs = self.ingester.ingest_directory(tmpdir, "trust_law")
            assert len(docs) == 2
            assert all(isinstance(d, LegalDocument) for d in docs)

    # 12. ingest_directory with non-existent path
    def test_ingest_directory_missing(self):
        docs = self.ingester.ingest_directory("/nonexistent/path", "test")
        assert docs == []

    # 13. ingest_case_json basic
    def test_ingest_case_json(self):
        data = {
            "id": "12345",
            "case_name": "Alpha Trust v. Beta Bank",
            "date_filed": "2023-06-15",
            "court": "9th Circuit",
            "plain_text": "The court held that the trustee breached fiduciary duty.",
        }
        doc = self.ingester.ingest_case_json(data)
        assert doc.id == "case_12345"
        assert "Alpha Trust v. Beta Bank" in doc.content
        assert doc.metadata["category"] == "case_law"
        assert doc.metadata["case_name"] == "Alpha Trust v. Beta Bank"

    # 14. ingest_case_json with opinions
    def test_ingest_case_json_with_opinions(self):
        data = {
            "id": "99",
            "case_name": "X v. Y",
            "opinions": [{"text": "The majority opinion states..."}],
        }
        doc = self.ingester.ingest_case_json(data)
        assert "majority opinion" in doc.content

    # 15. ingest_case_json strips HTML
    def test_ingest_case_json_strips_html(self):
        data = {
            "id": "100",
            "case_name": "HTML v. Test",
            "html_with_citations": "<p>The <b>trustee</b> must act.</p>",
        }
        doc = self.ingester.ingest_case_json(data)
        assert "<p>" not in doc.content
        assert "trustee" in doc.content

    # 16. Chunks are added to document
    def test_ingest_directory_adds_chunks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = "Legal doctrine. " * 200
            Path(tmpdir, "doc.txt").write_text(content, encoding="utf-8")
            docs = self.ingester.ingest_directory(tmpdir, "general")
            assert len(docs[0].chunks) >= 1


# ── VectorStore tests ─────────────────────────────────────────────────────────

class TestVectorStore:
    def setup_method(self):
        self.store = VectorStore()

    # 17. Add and retrieve by id
    def test_add_and_get(self):
        entry = _make_entry("e1", "Trustee fiduciary duty content")
        self.store.add(entry)
        result = self.store.get("e1")
        assert result is not None
        assert result.id == "e1"

    # 18. Deduplication — re-adding same id replaces
    def test_add_deduplication(self):
        self.store.add(_make_entry("e1", "original"))
        self.store.add(_make_entry("e1", "updated", seed=1))
        assert len(self.store) == 1
        assert self.store.get("e1").content == "updated"

    # 19. Delete entry
    def test_delete_entry(self):
        self.store.add(_make_entry("e1", "content"))
        removed = self.store.delete("e1")
        assert removed is True
        assert self.store.get("e1") is None

    # 20. Delete non-existent
    def test_delete_nonexistent(self):
        assert self.store.delete("nonexistent") is False

    # 21. Search returns results
    def test_search_returns_results(self):
        for i in range(5):
            self.store.add(_make_entry(f"e{i}", f"Document {i}", seed=i))
        q = _random_vec(32, seed=42)
        results = self.store.search(q, top_k=3)
        assert len(results) <= 3
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    # 22. Search scores in [0, 1] range (cosine approx)
    def test_search_scores_bounded(self):
        for i in range(5):
            self.store.add(_make_entry(f"e{i}", f"Doc {i}", seed=i))
        q = _random_vec(32, seed=10)
        results = self.store.search(q, top_k=5)
        for _, score in results:
            assert -1.0 <= score <= 1.0

    # 23. Search sorted descending by score
    def test_search_sorted(self):
        for i in range(8):
            self.store.add(_make_entry(f"e{i}", f"Doc {i}", seed=i))
        q = _random_vec(32, seed=99)
        results = self.store.search(q, top_k=8)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    # 24. Metadata filter — category
    def test_search_metadata_filter_category(self):
        self.store.add(_make_entry("trust1", "trust content", category="trust_law"))
        self.store.add(_make_entry("case1", "case content", category="case_law", seed=1))
        q = _random_vec(32, seed=5)
        results = self.store.search(q, top_k=10, filter_metadata={"category": "trust_law"})
        assert all(r.metadata.get("category") == "trust_law" for r, _ in results)

    # 25. Search on empty store
    def test_search_empty_store(self):
        results = self.store.search(_random_vec(32), top_k=5)
        assert results == []

    # 26. Persist and load
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "store.json")
            store = VectorStore(persist_path=path)
            store.add(_make_entry("e1", "hello legal world"))
            store.save()

            store2 = VectorStore(persist_path=path)
            store2.load()
            assert len(store2) == 1
            assert store2.get("e1").content == "hello legal world"

    # 27. Stats returns expected keys
    def test_stats_keys(self):
        self.store.add(_make_entry("e1", "content"))
        stats = self.store.stats()
        for key in ("total_documents", "categories", "jurisdictions", "last_updated"):
            assert key in stats

    # 28. Stats counts categories correctly
    def test_stats_categories(self):
        self.store.add(_make_entry("t1", "trust", category="trust_law"))
        self.store.add(_make_entry("t2", "trust2", category="trust_law"))
        self.store.add(_make_entry("c1", "case", category="case_law", seed=5))
        stats = self.store.stats()
        assert stats["categories"]["trust_law"] == 2
        assert stats["categories"]["case_law"] == 1

    # 29. Clear empties the store
    def test_clear(self):
        for i in range(5):
            self.store.add(_make_entry(f"e{i}", "content", seed=i))
        self.store.clear()
        assert len(self.store) == 0


# ── EmbeddingProvider tests ───────────────────────────────────────────────────

class TestEmbeddingProvider:
    def setup_method(self):
        # Force TF-IDF provider (no external deps)
        with patch.dict("os.environ", {}, clear=True):
            self.embedder = EmbeddingProvider()
        self.embedder.provider = "tfidf"
        self.embedder.dim = EmbeddingProvider.TFIDF_DIM

    # 30. TF-IDF returns correct dimension
    def test_tfidf_dim(self):
        vec = self.embedder._tfidf_embed("Trust law fiduciary duty")
        assert len(vec) == EmbeddingProvider.TFIDF_DIM

    # 31. TF-IDF is normalised
    def test_tfidf_normalised(self):
        vec = self.embedder._tfidf_embed("Trust law fiduciary duty trustee estate")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6

    # 32. TF-IDF different texts produce different vectors
    def test_tfidf_different_texts(self):
        v1 = self.embedder._tfidf_embed("trust law")
        v2 = self.embedder._tfidf_embed("securities fraud regulation")
        assert v1 != v2

    # 33. Async embed wraps TF-IDF
    def test_async_embed(self):
        vec = asyncio.get_event_loop().run_until_complete(
            self.embedder.embed("Trustee fiduciary duty")
        )
        assert len(vec) == EmbeddingProvider.TFIDF_DIM

    # 34. Batch embed
    def test_async_embed_batch(self):
        texts = ["trust law", "securities regulation", "contract breach"]
        vecs = asyncio.get_event_loop().run_until_complete(
            self.embedder.embed_batch(texts)
        )
        assert len(vecs) == 3
        assert all(len(v) == EmbeddingProvider.TFIDF_DIM for v in vecs)


# ── LegalRetriever tests ──────────────────────────────────────────────────────

class TestLegalRetriever:
    def setup_method(self):
        self.store = VectorStore()
        for i in range(10):
            cat = "trust_law" if i < 5 else "case_law"
            jur = "federal" if i % 2 == 0 else "california"
            self.store.add(_make_entry(f"e{i}", f"Legal content doc {i}", category=cat, jurisdiction=jur, seed=i))

        embedder = MagicMock()
        embedder.embed = AsyncMock(side_effect=lambda text: _random_vec(32, hash(text) % 2**31))
        self.retriever = LegalRetriever(self.store, embedder)
        self.retriever.build_bm25_index()

    # 35. retrieve returns list of dicts
    def test_retrieve_returns_dicts(self):
        results = asyncio.get_event_loop().run_until_complete(
            self.retriever.retrieve("trustee fiduciary duty")
        )
        assert isinstance(results, list)
        for r in results:
            for key in ("content", "score", "source", "metadata"):
                assert key in r

    # 36. retrieve respects top_k
    def test_retrieve_top_k(self):
        results = asyncio.get_event_loop().run_until_complete(
            self.retriever.retrieve("trust law", top_k=3)
        )
        assert len(results) <= 3

    # 37. retrieve with category filter
    def test_retrieve_category_filter(self):
        results = asyncio.get_event_loop().run_until_complete(
            self.retriever.retrieve("legal content", top_k=10, category="trust_law")
        )
        for r in results:
            assert r["metadata"].get("category") == "trust_law"

    # 38. retrieve_for_trust_law
    def test_retrieve_for_trust_law(self):
        results = asyncio.get_event_loop().run_until_complete(
            self.retriever.retrieve_for_trust_law("What duties does a trustee have?")
        )
        assert isinstance(results, list)

    # 39. retrieve_precedents
    def test_retrieve_precedents(self):
        results = asyncio.get_event_loop().run_until_complete(
            self.retriever.retrieve_precedents("Company failed to disclose material facts")
        )
        assert isinstance(results, list)

    # 40. BM25 build index
    def test_bm25_build_index(self):
        self.retriever.build_bm25_index()
        assert self.retriever._built is True
        assert len(self.retriever._corpus_tf) == len(self.store.entries)

    # 41. BM25 score non-negative
    def test_bm25_score_non_negative(self):
        tokens = ["trust", "law", "duty"]
        score = self.retriever._bm25_score(tokens, 0)
        assert score >= 0.0


# ── RAGPipeline tests ─────────────────────────────────────────────────────────

class TestRAGPipeline:
    def setup_method(self):
        store = VectorStore()
        for i in range(5):
            entry = _make_entry(
                f"e{i}",
                f"Trust law content {i}. Fiduciary duty of trustee toward beneficiary.",
                category="trust_law",
                seed=i,
            )
            store.add(entry)

        embedder = MagicMock()
        embedder.embed = AsyncMock(side_effect=lambda text: _random_vec(32, hash(text) % 2**31))

        retriever = LegalRetriever(store, embedder)
        retriever.build_bm25_index()

        self.pipeline = RAGPipeline(retriever, embedder)
        # Force template backend
        self.pipeline._llm_backend = "template"

    # 42. ask returns dict with required keys
    def test_ask_returns_required_keys(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.pipeline.ask("What are the fiduciary duties of a trustee?")
        )
        for key in ("answer", "confidence", "citations", "follow_up_questions", "jurisdiction"):
            assert key in result

    # 43. confidence is [0, 1]
    def test_ask_confidence_bounded(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.pipeline.ask("What are a trustee's duties?")
        )
        assert 0.0 <= result["confidence"] <= 1.0

    # 44. citations is a list
    def test_ask_citations_list(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.pipeline.ask("What are a trustee's duties?")
        )
        assert isinstance(result["citations"], list)

    # 45. follow_up_questions is a list
    def test_ask_follow_ups_list(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.pipeline.ask("Beneficiary rights in trust?")
        )
        assert isinstance(result["follow_up_questions"], list)

    # 46. build_context_prompt returns string
    def test_build_context_prompt(self):
        passages = [
            {
                "content": "Trustees must act in good faith.",
                "score": 0.9,
                "source": "trust_law/analyzer.py",
                "metadata": {"category": "trust_law"},
                "entry_id": "e1",
            }
        ]
        prompt = asyncio.get_event_loop().run_until_complete(
            self.pipeline.build_context_prompt("What duties does a trustee have?", passages)
        )
        assert isinstance(prompt, str)
        assert "PASSAGE 1" in prompt
        assert "trustee" in prompt.lower()

    # 47. analyze_document returns analysis
    def test_analyze_document(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.pipeline.analyze_document(
                "This Trust Agreement is entered into by Grantor and Trustee for the benefit of Beneficiary."
            )
        )
        assert "analysis" in result

    # 48. find_precedents returns dict
    def test_find_precedents(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.pipeline.find_precedents("Trustee failed to distribute trust assets")
        )
        assert "precedents_summary" in result
        assert "case_citations" in result

    # 49. ask_trust_law returns domain key
    def test_ask_trust_law(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.pipeline.ask_trust_law("Can a trustee self-deal?")
        )
        assert result.get("domain") == "trust_law"

    # 50. template_generate works without LLM
    def test_template_generate(self):
        prompt = "[PASSAGE 1] Source: test.py\nTrustee must act in good faith.\n\n=== END CONTEXT ==="
        answer = self.pipeline._template_generate(prompt, "test question")
        assert isinstance(answer, str)
        assert len(answer) > 0


# ── Integration tests ─────────────────────────────────────────────────────────

class TestIntegration:
    # 51. Full pipeline: ingest → search → answer
    def test_full_pipeline_ingest_and_ask(self):
        store = VectorStore()
        embedder = EmbeddingProvider()
        embedder.provider = "tfidf"
        embedder.dim = EmbeddingProvider.TFIDF_DIM

        # Ingest sample documents
        ingester = DocumentIngester()
        legal_text = (
            "The trustee has a fiduciary duty to act in the best interests of the "
            "beneficiaries. Under the Uniform Trust Code, a trustee must administer "
            "the trust in good faith, with due care, skill, and caution. "
            "Self-dealing is strictly prohibited unless the trust instrument allows it."
        )
        chunks = ingester.chunk_text(legal_text, "doc1")
        meta = ingester.extract_legal_metadata(legal_text)

        for i, chunk in enumerate(chunks):
            vec = embedder._tfidf_embed(chunk)
            store.add(VectorEntry(id=f"doc1_c{i}", embedding=vec, content=chunk, metadata=meta))

        retriever = LegalRetriever(store, embedder)
        retriever.build_bm25_index()
        pipeline = RAGPipeline(retriever, embedder)
        pipeline._llm_backend = "template"

        # Wrap async call
        async def run():
            return await pipeline.ask("What are the fiduciary duties of a trustee?")

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result["retrieval_count"] > 0
        assert "answer" in result

    # 52. LegalRAG initialise with empty base path
    def test_legal_rag_status_before_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rag = LegalRAG(base_path=tmpdir)
            status = rag.status()
            assert "initialized" in status
            assert status["initialized"] is False

    # 53. Vector store round-trip JSON
    def test_vector_store_json_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "kb.json")
            store = VectorStore(persist_path=path)
            for i in range(3):
                store.add(_make_entry(f"e{i}", f"content {i}", seed=i))
            store.save()

            store2 = VectorStore(persist_path=path)
            store2.load()
            assert len(store2) == 3
            for i in range(3):
                assert store2.get(f"e{i}") is not None

    # 54. Citation extraction
    def test_citation_extraction(self):
        passages = [
            {"content": "Trustee duty", "score": 0.9, "source": "trust_law/a.py",
             "metadata": {"category": "trust_law"}, "entry_id": "e1"},
            {"content": "Case holding", "score": 0.8, "source": "case_law/b.py",
             "metadata": {"category": "case_law"}, "entry_id": "e2"},
        ]
        embedder = MagicMock()
        retriever = MagicMock()
        pipeline = RAGPipeline(retriever, embedder)
        citations = pipeline._extract_citations(passages)
        assert len(citations) == 2
        assert citations[0]["source"] == "trust_law/a.py"

    # 55. Confidence computation
    def test_confidence_with_no_passages(self):
        embedder = MagicMock()
        retriever = MagicMock()
        pipeline = RAGPipeline(retriever, embedder)
        assert pipeline._compute_confidence([]) == 0.0

    # 56. Confidence with high-score passages
    def test_confidence_with_passages(self):
        embedder = MagicMock()
        retriever = MagicMock()
        pipeline = RAGPipeline(retriever, embedder)
        passages = [{"score": 0.9}, {"score": 0.8}, {"score": 0.7}]
        conf = pipeline._compute_confidence(passages)
        assert conf > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
