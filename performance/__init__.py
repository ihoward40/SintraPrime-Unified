"""
SintraPrime-Unified Performance Layer
"""

from .benchmark_suite import BenchmarkSuite, BenchmarkResult, SuiteReport
from .stream_processor import StreamProcessor, StreamDocument, StreamType, EventBus, create_default_processor
from .memory_optimizer import MemoryOptimizer, LRUCache, CacheManager, DocumentChunker
from .document_indexer import DocumentIndexer, IndexDocument, SearchResult

__all__ = [
    "BenchmarkSuite",
    "BenchmarkResult",
    "SuiteReport",
    "StreamProcessor",
    "StreamDocument",
    "StreamType",
    "EventBus",
    "create_default_processor",
    "MemoryOptimizer",
    "LRUCache",
    "CacheManager",
    "DocumentChunker",
    "DocumentIndexer",
    "IndexDocument",
    "SearchResult",
]
