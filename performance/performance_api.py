"""
SintraPrime-Unified: Performance API
FastAPI router exposing benchmarking, memory, indexing, and streaming endpoints.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Stub classes so module is importable without FastAPI
    class BaseModel:  # type: ignore[no-redef]
        pass
    def Field(*args, **kwargs):  # type: ignore[misc]
        return None
    class APIRouter:  # type: ignore[no-redef]
        def __init__(self, *a, **kw):
            pass
        def post(self, *a, **kw):
            def dec(fn): return fn
            return dec
        def get(self, *a, **kw):
            def dec(fn): return fn
            return dec
        def websocket(self, *a, **kw):
            def dec(fn): return fn
            return dec


from .benchmark_suite import BenchmarkSuite, SuiteReport
from .document_indexer import DocumentIndexer, IndexDocument, index_from_dict_list
from .memory_optimizer import MemoryOptimizer
from .stream_processor import (
    EventBus, StreamDocument, StreamProcessor, StreamType, Priority,
    create_default_processor,
)

import hashlib

# ---------------------------------------------------------------------------
# Shared state (singleton-ish per process)
# ---------------------------------------------------------------------------

_benchmark_suite: Optional[BenchmarkSuite] = None
_last_report: Optional[Dict[str, Any]] = None
_indexer: Optional[DocumentIndexer] = None
_memory_optimizer: Optional[MemoryOptimizer] = None
_stream_processor: Optional[StreamProcessor] = None
_websocket_clients: List[WebSocket] = []


def _get_benchmark_suite() -> BenchmarkSuite:
    global _benchmark_suite
    if _benchmark_suite is None:
        _benchmark_suite = BenchmarkSuite(warmup=1, iterations=5)
    return _benchmark_suite


def _get_indexer() -> DocumentIndexer:
    global _indexer
    if _indexer is None:
        _indexer = DocumentIndexer()
    return _indexer


def _get_memory_optimizer() -> MemoryOptimizer:
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer()
    return _memory_optimizer


async def _get_stream_processor() -> StreamProcessor:
    global _stream_processor
    if _stream_processor is None:
        _stream_processor = create_default_processor()
        await _stream_processor.start(enable_builtin_streams=False)
    return _stream_processor


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class BenchmarkRequest(BaseModel):
    warmup: int = Field(default=1, ge=0, le=5, description="Warmup iterations")
    iterations: int = Field(default=5, ge=1, le=20, description="Benchmark iterations")
    categories: Optional[List[str]] = Field(default=None, description="Categories to run (None = all)")


class BenchmarkResponse(BaseModel):
    status: str
    total_benchmarks: int
    passed: int
    failed: int
    avg_latency_p50_ms: float
    avg_throughput_rps: float
    baseline_wins: int
    baseline_total: int
    report_timestamp: float


class MemoryResponse(BaseModel):
    available_mb: float
    cache_bytes_used: int
    agent_capacity: str
    recommendations: List[Dict[str, Any]]
    cache_stats: Dict[str, Any]


class IndexRequest(BaseModel):
    documents: List[Dict[str, Any]] = Field(description="List of document dicts with id, title, content, doc_type")


class IndexResponse(BaseModel):
    added: int
    skipped: int
    total: int
    total_indexed: int
    total_terms: int


class SearchRequest(BaseModel):
    query: str = Field(description="Search query")
    top_k: int = Field(default=10, ge=1, le=100)
    doc_type: Optional[str] = None
    jurisdiction: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results_count: int
    results: List[Dict[str, Any]]
    search_time_ms: float


class IngestRequest(BaseModel):
    stream_type: str = Field(description="court_filings / federal_register / case_law_updates / financial_data")
    content: str
    metadata: Optional[Dict[str, Any]] = None
    priority: str = Field(default="NORMAL", description="LOW / NORMAL / HIGH / CRITICAL")


class IngestResponse(BaseModel):
    doc_id: Optional[str]
    accepted: bool
    stream_type: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/performance", tags=["performance"])


@router.post("/benchmark", response_model=BenchmarkResponse, summary="Run benchmark suite")
async def run_benchmark(request: BenchmarkRequest = None):
    """
    Run the SintraPrime benchmark suite across all modules.
    Returns latency percentiles, throughput, memory, and baseline comparisons.
    """
    global _last_report
    req = request or BenchmarkRequest()
    suite = BenchmarkSuite(warmup=req.warmup, iterations=req.iterations)
    report: SuiteReport = suite.run_all()
    _last_report = {
        "suite_name": report.suite_name,
        "timestamp": report.timestamp,
        "total_benchmarks": report.total_benchmarks,
        "passed": report.passed,
        "failed": report.failed,
        "summary": report.summary,
        "results": [r.to_dict() for r in report.results],
        "baseline_comparisons": [
            {"framework": c.framework, "operation": c.operation,
             "sintra_ms": c.sintra_ms, "baseline_ms": c.baseline_ms,
             "speedup": c.speedup, "winner": c.winner}
            for c in report.baseline_comparisons
        ],
        "legal_benchmarks": [
            {"scenario": lr.scenario, "description": lr.description,
             "time_ms": lr.time_ms, "grade": lr.grade}
            for lr in report.legal_benchmarks
        ],
    }
    s = report.summary
    return BenchmarkResponse(
        status="complete",
        total_benchmarks=report.total_benchmarks,
        passed=report.passed,
        failed=report.failed,
        avg_latency_p50_ms=s.get("avg_latency_p50_ms", 0.0),
        avg_throughput_rps=s.get("avg_throughput_rps", 0.0),
        baseline_wins=s.get("baseline_wins", 0),
        baseline_total=s.get("baseline_total", 0),
        report_timestamp=report.timestamp,
    )


@router.get("/report", summary="Get latest benchmark report")
async def get_report():
    """Return the most recent benchmark report as JSON."""
    if _last_report is None:
        raise HTTPException(status_code=404, detail="No benchmark report available. Run POST /performance/benchmark first.")
    return _last_report


@router.get("/memory", response_model=MemoryResponse, summary="Current memory usage")
async def get_memory():
    """Return current memory usage, cache stats, and recommendations."""
    optimizer = _get_memory_optimizer()
    available_mb = optimizer.estimate_available_memory_mb()
    cache_bytes = optimizer.cache_manager.total_bytes_used()
    capacity_msg = optimizer.agent_capacity_recommendation()
    recs = [
        {"severity": r.severity, "message": r.message, "action": r.action,
         "estimated_savings_mb": r.estimated_savings_mb}
        for r in optimizer.get_recommendations()
    ]
    cache_stats = {
        name: {
            "hits": s.hits, "misses": s.misses, "evictions": s.evictions,
            "current_items": s.current_items,
            "current_bytes": s.current_bytes,
            "hit_rate": round(s.hit_rate, 4),
        }
        for name, s in optimizer.cache_manager.get_all_stats().items()
    }
    return MemoryResponse(
        available_mb=round(available_mb, 2),
        cache_bytes_used=cache_bytes,
        agent_capacity=capacity_msg,
        recommendations=recs,
        cache_stats=cache_stats,
    )


@router.post("/index", response_model=IndexResponse, summary="Index document collection")
async def index_documents(request: IndexRequest):
    """
    Index a collection of legal documents for full-text search.
    Supports incremental indexing (unchanged docs are skipped).
    """
    indexer = _get_indexer()
    result = indexer.add_documents([
        IndexDocument(
            doc_id=doc.get("id", hashlib.sha256(doc.get("content", "").encode()).hexdigest()[:12]),
            title=doc.get("title", "Untitled"),
            content=doc.get("content", ""),
            doc_type=doc.get("doc_type", "generic"),
            jurisdiction=doc.get("jurisdiction", ""),
            date=doc.get("date", ""),
            source=doc.get("source", ""),
            metadata=doc.get("metadata", {}),
        )
        for doc in request.documents
    ])
    stats = indexer.stats
    return IndexResponse(
        added=result["added"],
        skipped=result["skipped"],
        total=result["total"],
        total_indexed=stats.total_documents,
        total_terms=stats.total_terms,
    )


@router.get("/search", response_model=SearchResponse, summary="Search indexed documents")
async def search_documents(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(default=10, ge=1, le=100),
    doc_type: Optional[str] = Query(default=None),
    jurisdiction: Optional[str] = Query(default=None),
):
    """
    BM25-ranked full-text search over indexed legal documents.
    """
    indexer = _get_indexer()
    t0 = time.perf_counter()
    results = indexer.search(query=q, top_k=top_k, doc_type_filter=doc_type, jurisdiction_filter=jurisdiction)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return SearchResponse(
        query=q,
        results_count=len(results),
        search_time_ms=round(elapsed_ms, 3),
        results=[
            {
                "rank": r.rank,
                "doc_id": r.doc_id,
                "title": r.title,
                "doc_type": r.doc_type,
                "score": r.score,
                "snippet": r.snippet,
                "matched_terms": r.matched_terms,
            }
            for r in results
        ],
    )


@router.post("/ingest", response_model=IngestResponse, summary="Ingest document to stream")
async def ingest_to_stream(request: IngestRequest):
    """Manually ingest a document into a named stream pipeline."""
    try:
        st = StreamType(request.stream_type)
    except ValueError:
        valid = [s.value for s in StreamType]
        raise HTTPException(status_code=400, detail=f"Invalid stream_type. Valid: {valid}")

    try:
        prio = Priority[request.priority.upper()]
    except KeyError:
        prio = Priority.NORMAL

    processor = await _get_stream_processor()

    if st not in processor._pipelines:
        processor.register_stream(st)

    doc_id = await processor.ingest_document(
        stream_type=st,
        content=request.content,
        metadata=request.metadata or {},
        priority=prio,
    )
    return IngestResponse(
        doc_id=doc_id,
        accepted=doc_id is not None,
        stream_type=request.stream_type,
    )


@router.get("/stream/metrics", summary="Get stream processing metrics")
async def get_stream_metrics():
    """Return metrics for all active stream pipelines."""
    processor = await _get_stream_processor()
    return processor.get_all_metrics()


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time document stream events.
    Clients receive JSON events as documents are processed.
    """
    await websocket.accept()
    _websocket_clients.append(websocket)

    processor = await _get_stream_processor()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    async def on_event(event):
        try:
            queue.put_nowait(event.to_json() if hasattr(event, "to_json") else json.dumps({"event": str(event)}))
        except asyncio.QueueFull:
            pass

    processor.event_bus.subscribe("*", on_event)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(msg)
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_text(json.dumps({"type": "ping", "timestamp": time.time()}))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        processor.event_bus.unsubscribe("*", on_event)
        if websocket in _websocket_clients:
            _websocket_clients.remove(websocket)


# ---------------------------------------------------------------------------
# App factory (optional standalone)
# ---------------------------------------------------------------------------

def create_app():
    """Create a standalone FastAPI app with the performance router."""
    if not FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI not installed. Run: pip install fastapi uvicorn")
    from fastapi import FastAPI
    app = FastAPI(
        title="SintraPrime Performance API",
        description="Benchmarking, memory, indexing, and streaming for SintraPrime-Unified",
        version="1.0.0",
    )
    app.include_router(router)
    return app


if __name__ == "__main__":
    import sys
    if not FASTAPI_AVAILABLE:
        print("FastAPI not available. Install with: pip install fastapi uvicorn")
        sys.exit(1)
    try:
        import uvicorn
        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=8080)
    except ImportError:
        print("uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)
