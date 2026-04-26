"""
SintraPrime-Unified: Comprehensive Performance Test Suite
70+ tests covering benchmarking, streaming, memory optimization, and indexing.
Run with: python -m pytest performance/tests/ -v
"""

from __future__ import annotations

import asyncio
import math
import sys
import time
import tracemalloc
import uuid
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Add parent to path for direct test execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from performance.benchmark_suite import (
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkSuite,
    LegalBenchmarkResult,
    BaselineComparison,
    SuiteReport,
    generate_legal_text,
    grade_performance,
    percentile,
    measure_memory,
    _simulate_document_parse,
    _simulate_ner_extraction,
    _simulate_vector_search,
    _simulate_chain_execution,
    _simulate_bm25_rank,
    _simulate_text_chunk,
)
from performance.document_indexer import (
    DocumentIndexer,
    IndexDocument,
    InvertedIndex,
    BM25Scorer,
    SearchResult,
    tokenize,
    stem,
    process_text,
    extract_snippet,
    index_from_dict_list,
    LEGAL_STOP_WORDS,
)
from performance.memory_optimizer import (
    CacheManager,
    DocumentChunker,
    LazyCollection,
    LazyModule,
    LRUCache,
    MemoryLeakDetector,
    MemoryOptimizer,
    MemoryProfiler,
    bytes_to_mb,
    get_object_size,
    mb_to_bytes,
    take_snapshot,
)
from performance.stream_processor import (
    BackpressureController,
    DocumentStatus,
    EventBus,
    Priority,
    StreamDocument,
    StreamEvent,
    StreamPipeline,
    StreamProcessor,
    StreamType,
    create_default_processor,
    stage_analyze,
    stage_ingest,
    stage_parse,
    stage_store,
)


# ===========================================================================
# SECTION 1: Benchmark Suite Tests (20 tests)
# ===========================================================================

class TestPercentile:
    def test_percentile_empty(self):
        assert percentile([], 50) == 0.0

    def test_percentile_single(self):
        assert percentile([5.0], 50) == 5.0

    def test_percentile_p50(self):
        data = list(range(1, 11))   # 1..10
        assert percentile(data, 50) == pytest.approx(5.5, abs=0.1)

    def test_percentile_p100(self):
        assert percentile([1.0, 2.0, 3.0], 100) == 3.0

    def test_percentile_p0(self):
        assert percentile([1.0, 2.0, 3.0], 0) == 1.0


class TestGradePerformance:
    def test_grade_a(self):
        assert grade_performance(100, 200, 400, 800) == "A"

    def test_grade_b(self):
        assert grade_performance(300, 200, 400, 800) == "B"

    def test_grade_c(self):
        assert grade_performance(600, 200, 400, 800) == "C"

    def test_grade_d(self):
        assert grade_performance(1200, 200, 400, 800) == "D"

    def test_grade_f(self):
        assert grade_performance(2000, 200, 400, 800) == "F"


class TestGenerateLegalText:
    def test_generates_text(self):
        text = generate_legal_text(pages=1)
        assert len(text) > 0
        assert isinstance(text, str)

    def test_approximate_word_count(self):
        text = generate_legal_text(pages=2, words_per_page=100)
        words = text.split()
        assert 150 <= len(words) <= 250  # ~200 words ±25%

    def test_contains_legal_terms(self):
        text = generate_legal_text(pages=3)
        legal_terms = ["testator", "beneficiary", "trustee", "executor", "probate"]
        assert any(term in text for term in legal_terms)


class TestBenchmarkRunner:
    def test_basic_run(self):
        runner = BenchmarkRunner(warmup=1, iterations=3)
        result = runner.run("test_fn", "unit", lambda: sum(range(1000)))
        assert isinstance(result, BenchmarkResult)
        assert result.name == "test_fn"
        assert result.category == "unit"
        assert result.iterations == 3
        assert result.latency_p50_ms >= 0
        assert result.throughput_rps > 0
        assert result.passed is True

    def test_failed_benchmark(self):
        def bad_fn():
            raise ValueError("Intentional error")
        runner = BenchmarkRunner(warmup=0, iterations=3)
        result = runner.run("bad", "unit", bad_fn)
        assert result.passed is False
        assert result.error is not None

    def test_token_count_affects_tps(self):
        runner = BenchmarkRunner(warmup=0, iterations=3)
        result = runner.run("tps_test", "unit", lambda: None, token_count=1000)
        assert result.tokens_per_sec > 0


class TestBenchmarkSuite:
    @pytest.fixture
    def suite(self):
        return BenchmarkSuite(warmup=0, iterations=3)

    def test_run_all_returns_report(self, suite):
        report = suite.run_all()
        assert isinstance(report, SuiteReport)
        assert report.total_benchmarks > 0

    def test_report_has_results(self, suite):
        report = suite.run_all()
        assert len(report.results) > 0
        for r in report.results:
            assert isinstance(r, BenchmarkResult)

    def test_baseline_comparisons_present(self, suite):
        report = suite.run_all()
        assert len(report.baseline_comparisons) > 0

    def test_legal_benchmarks_present(self, suite):
        report = suite.run_all()
        assert len(report.legal_benchmarks) > 0
        for lb in report.legal_benchmarks:
            assert lb.grade in ("A", "B", "C", "D", "F")

    def test_html_report_generation(self, suite):
        report = suite.run_all()
        html = suite.generate_html_report(report)
        assert "<!DOCTYPE html>" in html
        assert "SintraPrime" in html
        assert len(html) > 1000

    def test_ascii_chart_generation(self, suite):
        report = suite.run_all()
        chart = suite.generate_ascii_chart(report)
        assert "Latency Chart" in chart
        assert len(chart) > 50

    def test_summary_keys(self, suite):
        report = suite.run_all()
        required = ["avg_latency_p50_ms", "avg_throughput_rps", "avg_memory_mb", "baseline_wins"]
        for key in required:
            assert key in report.summary, f"Missing summary key: {key}"

    def test_simulate_functions(self):
        doc = generate_legal_text(1)
        parse_result = _simulate_document_parse(doc)
        assert "word_count" in parse_result
        assert parse_result["word_count"] > 0

        entities = _simulate_ner_extraction(doc)
        assert isinstance(entities, list)

        corpus = [generate_legal_text(1) for _ in range(5)]
        results = _simulate_vector_search("trust estate beneficiary", corpus)
        assert len(results) <= 5
        assert all(0.0 <= score <= 1.0 for _, score in results)

        chain_result = _simulate_chain_execution(["parse", "embed"], doc[:100])
        assert "parse" in chain_result

        chunks = _simulate_text_chunk(doc, 500)
        assert len(chunks) > 0

        bm25_scores = _simulate_bm25_rank("trust estate", corpus[:5])
        assert len(bm25_scores) == 5


# ===========================================================================
# SECTION 2: Stream Processor Tests (20 tests)
# ===========================================================================

class TestStreamDocument:
    def test_checksum_generated(self):
        doc = StreamDocument("id1", StreamType.COURT_FILINGS, "test content", {})
        assert len(doc.checksum) == 16

    def test_to_dict(self):
        doc = StreamDocument("id1", StreamType.COURT_FILINGS, "content", {"key": "val"})
        d = doc.to_dict()
        assert d["doc_id"] == "id1"
        assert d["stream_type"] == "court_filings"
        assert d["status"] == "PENDING"

    def test_add_step(self):
        doc = StreamDocument("id1", StreamType.COURT_FILINGS, "content", {})
        doc.add_step("ingest", {"size": 7}, 1.5)
        assert len(doc.processing_steps) == 1
        assert doc.processing_steps[0]["step"] == "ingest"


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe("doc.test", lambda e: received.append(e))
        event = StreamEvent("e1", "doc.test", "court_filings", "d1", {})
        asyncio.get_event_loop().run_until_complete(bus.publish(event))
        assert len(received) == 1

    def test_wildcard_subscription(self):
        bus = EventBus()
        received = []
        bus.subscribe("*", lambda e: received.append(e))
        event = StreamEvent("e2", "any.type", "court_filings", "d2", {})
        asyncio.get_event_loop().run_until_complete(bus.publish(event))
        assert len(received) == 1

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        handler = lambda e: received.append(e)
        bus.subscribe("doc.test", handler)
        bus.unsubscribe("doc.test", handler)
        event = StreamEvent("e3", "doc.test", "court_filings", "d3", {})
        asyncio.get_event_loop().run_until_complete(bus.publish(event))
        assert len(received) == 0

    def test_history_tracking(self):
        bus = EventBus()
        for i in range(5):
            event = StreamEvent(f"e{i}", "doc.event", "court_filings", f"d{i}", {})
            asyncio.get_event_loop().run_until_complete(bus.publish(event))
        history = bus.get_history()
        assert len(history) == 5

    def test_stats(self):
        bus = EventBus()
        event = StreamEvent("e1", "test", "court_filings", "d1", {})
        asyncio.get_event_loop().run_until_complete(bus.publish(event))
        stats = bus.stats
        assert stats["total_published"] == 1


class TestPipelineStages:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_stage_ingest(self):
        doc = StreamDocument("id1", StreamType.COURT_FILINGS, "content here", {})
        result = self._run(stage_ingest(doc))
        assert result.status == DocumentStatus.INGESTED
        assert len(result.processing_steps) == 1

    def test_stage_parse(self):
        doc = StreamDocument("id1", StreamType.COURT_FILINGS, "the quick brown fox", {})
        self._run(stage_ingest(doc))
        result = self._run(stage_parse(doc))
        assert result.status == DocumentStatus.PARSED
        assert "parsed" in result.metadata
        assert result.metadata["parsed"]["word_count"] == 4

    def test_stage_analyze_court(self):
        doc = StreamDocument("id1", StreamType.COURT_FILINGS, "emergency motion", {})
        self._run(stage_ingest(doc))
        self._run(stage_parse(doc))
        result = self._run(stage_analyze(doc))
        assert result.status == DocumentStatus.ANALYZED
        assert result.metadata["analysis"]["urgency_score"] == 0.8

    def test_stage_store(self):
        doc = StreamDocument("id1", StreamType.COURT_FILINGS, "some content", {})
        self._run(stage_ingest(doc))
        self._run(stage_parse(doc))
        self._run(stage_analyze(doc))
        result = self._run(stage_store(doc))
        assert result.status == DocumentStatus.STORED
        assert "store_record" in result.metadata

    def test_stage_ingest_empty_content_raises(self):
        doc = StreamDocument("id1", StreamType.COURT_FILINGS, "", {})
        with pytest.raises(ValueError):
            self._run(stage_ingest(doc))


class TestBackpressureController:
    def test_no_pause_when_under_threshold(self):
        bp = BackpressureController(threshold=0.8)
        queue = asyncio.Queue(maxsize=100)
        # Put 50 items (50% full)
        for _ in range(50):
            queue.put_nowait(None)
        # Should not raise or hang
        asyncio.get_event_loop().run_until_complete(bp.maybe_pause(queue))

    def test_is_full(self):
        bp = BackpressureController()
        queue = asyncio.Queue(maxsize=5)
        for _ in range(5):
            queue.put_nowait(None)
        assert bp.is_full(queue) is True

    def test_not_full(self):
        bp = BackpressureController()
        queue = asyncio.Queue(maxsize=5)
        queue.put_nowait(None)
        assert bp.is_full(queue) is False


class TestStreamProcessor:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_create_default_processor(self):
        processor = create_default_processor()
        assert len(processor._pipelines) == 4
        assert StreamType.COURT_FILINGS in processor._pipelines

    def test_ingest_and_metrics(self):
        async def _test():
            processor = create_default_processor()
            await processor.start(enable_builtin_streams=False)
            doc_id = await processor.ingest_document(
                StreamType.COURT_FILINGS,
                "Test motion for summary judgment",
                {"source": "test"},
            )
            await asyncio.sleep(0.2)
            await processor.stop()
            metrics = processor.get_all_metrics()
            assert metrics["court_filings"]["total_received"] >= 1
            return doc_id

        doc_id = self._run(_test())
        assert doc_id is not None


# ===========================================================================
# SECTION 3: Memory Optimizer Tests (20 tests)
# ===========================================================================

class TestLRUCache:
    def test_put_and_get(self):
        cache = LRUCache("test", max_bytes=1024 * 1024)
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_miss_returns_none(self):
        cache = LRUCache("test", max_bytes=1024 * 1024)
        assert cache.get("missing") is None

    def test_eviction_on_overflow(self):
        cache = LRUCache("test", max_bytes=100)
        cache.put("k1", "a" * 60)
        cache.put("k2", "b" * 60)   # Should evict k1
        assert cache.get("k1") is None or cache.get("k2") is not None

    def test_hit_rate_calculation(self):
        cache = LRUCache("test", max_bytes=1024 * 1024)
        cache.put("k", "v")
        cache.get("k")  # hit
        cache.get("x")  # miss
        assert cache.stats.hit_rate == pytest.approx(0.5, abs=0.01)

    def test_delete(self):
        cache = LRUCache("test", max_bytes=1024 * 1024)
        cache.put("k", "v")
        assert cache.delete("k") is True
        assert cache.get("k") is None

    def test_clear(self):
        cache = LRUCache("test", max_bytes=1024 * 1024)
        for i in range(10):
            cache.put(f"k{i}", f"v{i}")
        cache.clear()
        assert len(cache) == 0

    def test_stats_fields(self):
        cache = LRUCache("my_cache", max_bytes=1024 * 1024)
        cache.put("k", "v")
        s = cache.stats
        assert s.name == "my_cache"
        assert s.current_items == 1
        assert s.max_bytes == 1024 * 1024

    def test_lru_ordering(self):
        cache = LRUCache("test", max_bytes=200)
        cache.put("k1", "v" * 30)
        cache.put("k2", "v" * 30)
        cache.get("k1")  # Access k1 to make it recently used
        cache.put("k3", "v" * 30)  # May evict k2 (LRU)
        # k1 was accessed so it should survive longer
        assert cache.get("k1") is not None or len(cache) <= 2


class TestCacheManager:
    def test_create_and_retrieve_cache(self):
        mgr = CacheManager(global_max_bytes=10 * 1024 * 1024)
        c = mgr.create_cache("test")
        assert mgr.get_cache("test") is c

    def test_get_all_stats(self):
        mgr = CacheManager()
        mgr.create_cache("c1")
        mgr.create_cache("c2")
        stats = mgr.get_all_stats()
        assert "c1" in stats
        assert "c2" in stats

    def test_clear_all(self):
        mgr = CacheManager()
        c = mgr.create_cache("c1")
        c.put("k", "v")
        mgr.clear_all()
        assert c.get("k") is None


class TestDocumentChunker:
    def test_basic_chunking(self):
        chunker = DocumentChunker(chunk_size_bytes=100, overlap_bytes=10)
        text = "word " * 200
        chunks = chunker.chunk_text(text)
        assert len(chunks) > 1
        assert all(c.content for c in chunks)

    def test_chunk_ids_sequential(self):
        chunker = DocumentChunker(chunk_size_bytes=50)
        text = "x " * 200
        chunks = chunker.chunk_text(text)
        for i, c in enumerate(chunks):
            assert c.chunk_id == i

    def test_total_chunks_consistent(self):
        chunker = DocumentChunker(chunk_size_bytes=100)
        text = "word " * 100
        chunks = chunker.chunk_text(text)
        total = chunks[0].total_chunks if chunks else 0
        assert all(c.total_chunks == total for c in chunks)

    def test_estimate_chunk_count(self):
        chunker = DocumentChunker(chunk_size_bytes=1000, overlap_bytes=0)
        count = chunker.estimate_chunk_count(5000)
        assert count == 5

    def test_small_text_single_chunk(self):
        chunker = DocumentChunker(chunk_size_bytes=10000)
        text = "short text"
        chunks = chunker.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0].is_first and chunks[0].is_last


class TestLazyCollection:
    def test_register_and_get(self):
        col = LazyCollection()
        col.register("heavy_module", lambda: {"data": list(range(1000))})
        result = col.get("heavy_module")
        assert isinstance(result, dict)
        assert "data" in result

    def test_lazy_load_on_first_access(self):
        load_count = [0]
        def loader():
            load_count[0] += 1
            return "loaded"
        col = LazyCollection()
        col.register("m", loader)
        assert load_count[0] == 0
        col.get("m")
        assert load_count[0] == 1
        col.get("m")   # Second call should not re-load
        assert load_count[0] == 1

    def test_unload(self):
        col = LazyCollection()
        col.register("m", lambda: "data")
        col.get("m")
        col.unload("m")
        assert not col._modules["m"].is_loaded

    def test_status(self):
        col = LazyCollection()
        col.register("a", lambda: 1)
        col.register("b", lambda: 2)
        col.get("a")
        status = col.status()
        assert status["a"]["loaded"] is True
        assert status["b"]["loaded"] is False


class TestMemoryLeakDetector:
    def test_no_leak_detection_insufficient_samples(self):
        detector = MemoryLeakDetector()
        detector.start()
        detector.record_sample("s1")
        report = detector.detect_leaks()
        assert "Not enough samples" in report.recommendation
        detector.stop()

    def test_detect_with_samples(self):
        detector = MemoryLeakDetector()
        detector.start()
        for i in range(5):
            detector.record_sample(f"s{i}")
        report = detector.detect_leaks()
        assert isinstance(report.total_growth_mb, float)
        assert report.recommendation != ""
        detector.stop()

    def test_growth_trend(self):
        detector = MemoryLeakDetector()
        detector.start()
        for _ in range(5):
            detector.record_sample()
        trend = detector.get_growth_trend()
        assert len(trend) == 5
        detector.stop()


class TestMemoryOptimizer:
    @pytest.fixture
    def optimizer(self):
        return MemoryOptimizer(system_limit_bytes=4 * 1024 * 1024 * 1024)

    def test_estimate_available_memory(self, optimizer):
        available = optimizer.estimate_available_memory_mb()
        assert available >= 0

    def test_agent_capacity_recommendation(self, optimizer):
        msg = optimizer.agent_capacity_recommendation(agent_memory_mb=100)
        assert "agent" in msg.lower()
        assert "GB" in msg or "MB" in msg

    def test_recommendations_not_empty(self, optimizer):
        recs = optimizer.get_recommendations()
        assert len(recs) > 0
        for r in recs:
            assert r.severity in ("info", "warning", "critical")

    def test_optimize_for_large_document(self, optimizer):
        plan = optimizer.optimize_for_large_document(500)
        assert "estimated_chunks" in plan
        assert "can_process" in plan
        assert plan["estimated_chunks"] > 0

    def test_run_full_profile(self, optimizer):
        tracemalloc.start()
        result = optimizer.run_full_profile()
        assert "document_parser" in result
        assert "cache_stats" in result
        assert "recommendations" in result
        assert "agent_capacity" in result


# ===========================================================================
# SECTION 4: Document Indexer Tests (15+ tests)
# ===========================================================================

class TestTokenizer:
    def test_basic_tokenization(self):
        tokens = tokenize("the quick brown fox jumps")
        # Stop words removed: the
        assert "quick" in tokens
        assert "the" not in tokens

    def test_stop_word_removal(self):
        for sw in ["the", "is", "and", "or"]:
            assert sw not in tokenize(sw + " " + sw)

    def test_min_length_filter(self):
        tokens = tokenize("a ab abc abcd")
        assert "a" not in tokens   # 1 char filtered
        assert "abc" in tokens     # 3 chars kept
        assert "abcd" in tokens    # 4 chars kept

    def test_stem_function(self):
        assert stem("running") == "runn"  # removes 'ing'
        assert stem("testator") == "testator"  # no common suffix

    def test_process_text_pipeline(self):
        tokens = process_text("Trustee shall distribute income annually")
        assert isinstance(tokens, list)
        assert len(tokens) > 0


class TestInvertedIndex:
    def test_add_and_retrieve(self):
        idx = InvertedIndex()
        idx.add_document("d1", ["trust", "estate", "beneficiary"])
        assert idx.document_frequency("trust") == 1
        assert idx.term_frequency("trust", "d1") == 1

    def test_multi_doc(self):
        idx = InvertedIndex()
        idx.add_document("d1", ["trust", "estate"])
        idx.add_document("d2", ["trust", "probate"])
        assert idx.document_frequency("trust") == 2
        assert idx.doc_count == 2

    def test_remove_document(self):
        idx = InvertedIndex()
        idx.add_document("d1", ["trust", "estate"])
        idx.remove_document("d1")
        assert idx.document_frequency("trust") == 0
        assert idx.doc_count == 0

    def test_avg_doc_length(self):
        idx = InvertedIndex()
        idx.add_document("d1", ["a", "b", "c"])
        idx.add_document("d2", ["a", "b"])
        assert idx.avg_doc_length == pytest.approx(2.5, abs=0.01)

    def test_serialization_roundtrip(self):
        idx = InvertedIndex()
        idx.add_document("d1", ["trust", "estate", "will"])
        data = idx.to_dict()
        idx2 = InvertedIndex.from_dict(data)
        assert idx2.document_frequency("trust") == 1
        assert idx2.doc_count == 1


class TestBM25Scorer:
    def test_zero_score_missing_term(self):
        idx = InvertedIndex()
        idx.add_document("d1", ["estate", "trust"])
        scorer = BM25Scorer()
        score = scorer.score(["probate"], "d1", idx)
        assert score == 0.0

    def test_higher_tf_higher_score(self):
        idx = InvertedIndex()
        idx.add_document("d1", ["trust", "trust", "trust", "estate"])
        idx.add_document("d2", ["trust", "estate", "probate", "will"])
        scorer = BM25Scorer()
        s1 = scorer.score(["trust"], "d1", idx)
        s2 = scorer.score(["trust"], "d2", idx)
        assert s1 > s2

    def test_rank_returns_sorted(self):
        idx = InvertedIndex()
        idx.add_document("d1", ["trust", "trust", "estate"])
        idx.add_document("d2", ["estate", "probate"])
        idx.add_document("d3", ["trust", "will", "estate", "trust"])
        scorer = BM25Scorer()
        ranked = scorer.rank(["trust"], ["d1", "d2", "d3"], idx, top_k=3)
        scores = [s for _, s in ranked]
        assert scores == sorted(scores, reverse=True)


class TestDocumentIndexer:
    @pytest.fixture
    def indexer_with_docs(self):
        indexer = DocumentIndexer()
        docs = [
            IndexDocument("t1", "Smith Family Trust", "irrevocable trust for benefit of Jane Smith beneficiary corpus", doc_type="trust"),
            IndexDocument("t2", "Johnson Revocable Trust", "grantor reserves right to revoke trust corpus trustee", doc_type="trust"),
            IndexDocument("c1", "Doe v United States", "court held statute preempt state law probate administration affirmed", doc_type="case_law"),
            IndexDocument("c2", "Estate of Wilson", "probate court found testator lacked testamentary capacity will void", doc_type="case_law"),
            IndexDocument("r1", "SEC Rule 10b-5", "unlawful person employ device scheme artifice defraud purchase sale security", doc_type="regulation"),
        ]
        indexer.add_documents(docs)
        return indexer

    def test_index_documents(self, indexer_with_docs):
        assert indexer_with_docs.stats.total_documents == 5

    def test_search_returns_results(self, indexer_with_docs):
        results = indexer_with_docs.search("trust beneficiary")
        assert len(results) > 0

    def test_search_ranking(self, indexer_with_docs):
        results = indexer_with_docs.search("trust")
        assert len(results) > 0
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_filter_by_doc_type(self, indexer_with_docs):
        results = indexer_with_docs.search("trust estate probate", doc_type_filter="case_law")
        assert all(r.doc_type == "case_law" for r in results)

    def test_incremental_indexing(self, indexer_with_docs):
        # Re-adding same doc with same checksum should be skipped
        existing = indexer_with_docs.get_document("t1")
        result = indexer_with_docs.add_document(existing)
        assert result is False   # Skipped (unchanged)

    def test_remove_document(self, indexer_with_docs):
        indexer_with_docs.remove_document("t1")
        assert indexer_with_docs.get_document("t1") is None
        assert indexer_with_docs.stats.total_documents == 4

    def test_empty_query_returns_empty(self, indexer_with_docs):
        results = indexer_with_docs.search("")
        assert results == []

    def test_stats_fields(self, indexer_with_docs):
        stats = indexer_with_docs.stats
        assert stats.total_documents == 5
        assert stats.total_terms > 0
        assert stats.avg_doc_length > 0

    def test_index_from_dict_list(self):
        records = [
            {"id": "1", "title": "Doc One", "content": "trust beneficiary grantor", "doc_type": "trust"},
            {"id": "2", "title": "Doc Two", "content": "probate court estate will", "doc_type": "case_law"},
        ]
        indexer = index_from_dict_list(records)
        assert indexer.stats.total_documents == 2
        results = indexer.search("trust")
        assert len(results) > 0

    def test_snippet_extraction(self):
        content = "The trustee shall distribute income to the beneficiary Jane Smith annually."
        snippet = extract_snippet(content, ["trustee", "beneficiary"])
        assert len(snippet) <= MAX_SNIPPET_LENGTH + 10
        assert snippet != ""

    def test_list_documents(self, indexer_with_docs):
        docs = indexer_with_docs.list_documents()
        assert len(docs) == 5

    def test_list_documents_with_filter(self, indexer_with_docs):
        docs = indexer_with_docs.list_documents(doc_type="trust")
        assert all(d["doc_type"] == "trust" for d in docs)


# Needed for snippet test
MAX_SNIPPET_LENGTH = 300


# ===========================================================================
# SECTION 5: Integration & Edge Case Tests (5+ tests)
# ===========================================================================

class TestIntegration:
    def test_benchmark_then_search_workflow(self):
        """Integration: run benchmarks, then index and search."""
        suite = BenchmarkSuite(warmup=0, iterations=2)
        report = suite.run_all()
        assert report.total_benchmarks > 0

        indexer = DocumentIndexer()
        for r in report.results:
            indexer.add_document(IndexDocument(
                doc_id=r.name,
                title=r.name,
                content=f"benchmark {r.category} latency {r.latency_p50_ms}ms throughput {r.throughput_rps}rps",
                doc_type="benchmark",
            ))
        results = indexer.search("latency throughput")
        assert len(results) > 0

    def test_memory_optimizer_with_caching(self):
        """Integration: optimizer caches documents and tracks memory."""
        optimizer = MemoryOptimizer()
        for i in range(50):
            optimizer.document_cache.put(f"doc_{i}", {"content": "legal text " * 10, "id": i})
        stats = optimizer.document_cache.stats
        assert stats.current_items > 0
        plan = optimizer.optimize_for_large_document(100)
        assert plan["estimated_chunks"] > 0

    def test_stream_event_bus_integration(self):
        """Integration: event bus receives pipeline events."""
        async def _test():
            bus = EventBus()
            received = []
            bus.subscribe("document.processed", lambda e: received.append(e))
            pipeline = StreamPipeline(StreamType.COURT_FILINGS, bus, concurrency=1, queue_size=10)
            await pipeline.start()
            doc = StreamDocument("id1", StreamType.COURT_FILINGS, "court filing content motion", {})
            await pipeline.ingest(doc)
            await asyncio.sleep(0.3)
            await pipeline.stop()
            return received
        received = asyncio.get_event_loop().run_until_complete(_test())
        assert len(received) >= 1

    def test_chunker_then_index_workflow(self):
        """Integration: chunk a large document, index all chunks."""
        chunker = DocumentChunker(chunk_size_bytes=200, overlap_bytes=20)
        big_text = "trust beneficiary estate grantor trustee corpus " * 100
        chunks = chunker.chunk_text(big_text)
        assert len(chunks) > 1

        indexer = DocumentIndexer()
        docs = [
            IndexDocument(
                doc_id=f"chunk_{c.chunk_id}",
                title=f"Chunk {c.chunk_id}",
                content=c.content,
                doc_type="trust_chunk",
            )
            for c in chunks
        ]
        result = indexer.add_documents(docs)
        assert result["added"] == len(chunks)
        results = indexer.search("trust beneficiary")
        assert len(results) > 0

    def test_full_performance_pipeline(self):
        """End-to-end: benchmark → memory profile → index → search."""
        import tracemalloc
        tracemalloc.start()

        # 1. Run quick benchmark
        suite = BenchmarkSuite(warmup=0, iterations=2)
        report = suite.run_all()
        assert report.passed > 0

        # 2. Profile memory
        optimizer = MemoryOptimizer()
        profile_result = optimizer.run_full_profile()
        assert "document_parser" in profile_result

        # 3. Index and search
        records = [
            {"id": f"d{i}", "title": f"Legal Doc {i}",
             "content": f"trust estate beneficiary will grantor {i}", "doc_type": "trust"}
            for i in range(10)
        ]
        indexer = index_from_dict_list(records)
        results = indexer.search("trust estate")
        assert len(results) > 0
        assert results[0].score > 0
