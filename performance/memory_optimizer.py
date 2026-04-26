"""
SintraPrime-Unified: Memory Optimizer
Profile, optimize, and detect memory issues across all SintraPrime modules.
Features: LRU cache, lazy loading, large document chunking, leak detector.
"""

from __future__ import annotations

import gc
import math
import sys
import time
import tracemalloc
import weakref
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Generator, Generic, Iterable, Iterator, List, Optional, Tuple, TypeVar

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CACHE_MAX_BYTES = 512 * 1024 * 1024   # 512 MB
DEFAULT_CHUNK_SIZE_BYTES = 50 * 1024          # 50 KB per chunk
DEFAULT_SYSTEM_LIMIT_BYTES = 8 * 1024 * 1024 * 1024  # 8 GB
LEAK_HISTORY_SIZE = 200
SAMPLE_INTERVAL_S = 0.1


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MemorySnapshot:
    timestamp: float
    rss_mb: float
    tracemalloc_current_mb: float
    tracemalloc_peak_mb: float
    gc_counts: Tuple[int, int, int]
    label: str = ""


@dataclass
class ModuleMemoryProfile:
    module_name: str
    baseline_mb: float
    peak_mb: float
    delta_mb: float
    top_allocations: List[Tuple[str, int]]  # (location, bytes)
    duration_s: float
    recommendation: str


@dataclass
class CacheStats:
    name: str
    hits: int
    misses: int
    evictions: int
    current_items: int
    current_bytes: int
    max_bytes: int
    hit_rate: float


@dataclass
class MemoryRecommendation:
    severity: str   # info / warning / critical
    message: str
    action: str
    estimated_savings_mb: float


@dataclass
class LeakReport:
    suspected_leaks: List[Dict[str, Any]]
    total_growth_mb: float
    sampling_duration_s: float
    recommendation: str


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def get_object_size(obj: Any, seen: Optional[set] = None) -> int:
    """Recursively estimate object size in bytes."""
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        size += sum(get_object_size(k, seen) + get_object_size(v, seen) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set, frozenset)):
        size += sum(get_object_size(item, seen) for item in obj)
    return size


def bytes_to_mb(b: int) -> float:
    return b / (1024 * 1024)


def mb_to_bytes(mb: float) -> int:
    return int(mb * 1024 * 1024)


def get_tracemalloc_stats() -> Tuple[float, float]:
    """Return (current_mb, peak_mb) from tracemalloc if running."""
    try:
        current, peak = tracemalloc.get_traced_memory()
        return bytes_to_mb(current), bytes_to_mb(peak)
    except Exception:
        return 0.0, 0.0


def take_snapshot(label: str = "") -> MemorySnapshot:
    """Capture a memory snapshot."""
    current_mb, peak_mb = get_tracemalloc_stats()
    # Estimate RSS via sys modules (no psutil needed)
    try:
        import resource
        rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On Linux, maxrss is in KB; on macOS, in bytes
        if sys.platform == "linux":
            rss_mb = rss_bytes / 1024
        else:
            rss_mb = rss_bytes / (1024 * 1024)
    except Exception:
        rss_mb = 0.0
    return MemorySnapshot(
        timestamp=time.time(),
        rss_mb=rss_mb,
        tracemalloc_current_mb=current_mb,
        tracemalloc_peak_mb=peak_mb,
        gc_counts=tuple(gc.get_count()),  # type: ignore[arg-type]
        label=label,
    )


# ---------------------------------------------------------------------------
# LRU Cache Manager
# ---------------------------------------------------------------------------

class LRUCacheEntry:
    __slots__ = ("key", "value", "size_bytes", "hits", "created_at", "accessed_at")

    def __init__(self, key: Any, value: Any, size_bytes: int):
        self.key = key
        self.value = value
        self.size_bytes = size_bytes
        self.hits = 0
        self.created_at = time.time()
        self.accessed_at = time.time()


class LRUCache(Generic[T]):
    """
    LRU cache with byte-level size management.
    Evicts least-recently-used entries when max_bytes exceeded.
    """

    def __init__(self, name: str, max_bytes: int = DEFAULT_CACHE_MAX_BYTES):
        self.name = name
        self.max_bytes = max_bytes
        self._store: OrderedDict[Any, LRUCacheEntry] = OrderedDict()
        self._current_bytes = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _estimate_size(self, value: Any) -> int:
        try:
            return get_object_size(value)
        except Exception:
            return sys.getsizeof(value)

    def get(self, key: Any) -> Optional[T]:
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        self._hits += 1
        entry.hits += 1
        entry.accessed_at = time.time()
        self._store.move_to_end(key)
        return entry.value

    def put(self, key: Any, value: T) -> bool:
        """Store a value. Returns False if item is too large to fit."""
        size = self._estimate_size(value)
        if size > self.max_bytes:
            return False

        # Remove existing entry if present
        if key in self._store:
            self._current_bytes -= self._store[key].size_bytes
            del self._store[key]

        # Evict until there is space
        while self._current_bytes + size > self.max_bytes and self._store:
            evict_key, evict_entry = self._store.popitem(last=False)
            self._current_bytes -= evict_entry.size_bytes
            self._evictions += 1

        entry = LRUCacheEntry(key=key, value=value, size_bytes=size)
        self._store[key] = entry
        self._current_bytes += size
        return True

    def delete(self, key: Any) -> bool:
        entry = self._store.pop(key, None)
        if entry:
            self._current_bytes -= entry.size_bytes
            return True
        return False

    def clear(self):
        self._store.clear()
        self._current_bytes = 0

    def __contains__(self, key: Any) -> bool:
        return key in self._store

    def __len__(self) -> int:
        return len(self._store)

    @property
    def stats(self) -> CacheStats:
        total_lookups = self._hits + self._misses
        return CacheStats(
            name=self.name,
            hits=self._hits,
            misses=self._misses,
            evictions=self._evictions,
            current_items=len(self._store),
            current_bytes=self._current_bytes,
            max_bytes=self.max_bytes,
            hit_rate=self._hits / total_lookups if total_lookups > 0 else 0.0,
        )


class CacheManager:
    """Manages multiple named LRU caches with global byte budget."""

    def __init__(self, global_max_bytes: int = DEFAULT_CACHE_MAX_BYTES):
        self.global_max_bytes = global_max_bytes
        self._caches: Dict[str, LRUCache] = {}

    def create_cache(self, name: str, max_bytes: Optional[int] = None) -> LRUCache:
        if max_bytes is None:
            max_bytes = self.global_max_bytes // max(len(self._caches) + 1, 1)
        cache = LRUCache(name=name, max_bytes=max_bytes)
        self._caches[name] = cache
        return cache

    def get_cache(self, name: str) -> Optional[LRUCache]:
        return self._caches.get(name)

    def get_all_stats(self) -> Dict[str, CacheStats]:
        return {name: c.stats for name, c in self._caches.items()}

    def total_bytes_used(self) -> int:
        return sum(c._current_bytes for c in self._caches.values())

    def clear_all(self):
        for c in self._caches.values():
            c.clear()


# ---------------------------------------------------------------------------
# Large Document Chunker
# ---------------------------------------------------------------------------

@dataclass
class DocumentChunk:
    chunk_id: int
    total_chunks: int
    content: str
    byte_offset: int
    byte_length: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def is_first(self) -> bool:
        return self.chunk_id == 0

    @property
    def is_last(self) -> bool:
        return self.chunk_id == self.total_chunks - 1


class DocumentChunker:
    """
    Chunks large documents for processing without OOM.
    Supports byte-based and word-based chunking with overlap.
    """

    def __init__(
        self,
        chunk_size_bytes: int = DEFAULT_CHUNK_SIZE_BYTES,
        overlap_bytes: int = 512,
    ):
        self.chunk_size_bytes = chunk_size_bytes
        self.overlap_bytes = overlap_bytes

    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[DocumentChunk]:
        """Split text into chunks by byte size with overlap."""
        encoded = text.encode("utf-8")
        total_bytes = len(encoded)
        chunks = []
        offset = 0
        chunk_id = 0

        # First pass: determine boundaries
        boundaries = []
        while offset < total_bytes:
            end = min(offset + self.chunk_size_bytes, total_bytes)
            # Snap to word boundary
            if end < total_bytes:
                snap = encoded.rfind(b" ", offset, end)
                if snap > offset:
                    end = snap
            boundaries.append((offset, end))
            offset = max(end - self.overlap_bytes, end if end >= total_bytes else offset + 1)
            if offset >= total_bytes:
                break

        total_chunks = len(boundaries)
        for chunk_id, (start, end) in enumerate(boundaries):
            chunk_bytes = encoded[start:end]
            content = chunk_bytes.decode("utf-8", errors="replace")
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                total_chunks=total_chunks,
                content=content,
                byte_offset=start,
                byte_length=end - start,
                metadata=metadata or {},
            ))

        return chunks

    def chunk_file_stream(self, file_path: str) -> Generator[DocumentChunk, None, None]:
        """Stream-chunk a file without loading it all into memory."""
        with open(file_path, "rb") as fh:
            offset = 0
            chunk_id = 0
            buffer = b""
            while True:
                data = fh.read(self.chunk_size_bytes)
                if not data:
                    if buffer:
                        content = buffer.decode("utf-8", errors="replace")
                        yield DocumentChunk(
                            chunk_id=chunk_id,
                            total_chunks=-1,   # Unknown until EOF
                            content=content,
                            byte_offset=offset - len(buffer),
                            byte_length=len(buffer),
                        )
                    break
                buffer += data
                if len(buffer) >= self.chunk_size_bytes:
                    snap = buffer.rfind(b" ", 0, self.chunk_size_bytes)
                    cut = snap if snap > 0 else self.chunk_size_bytes
                    content = buffer[:cut].decode("utf-8", errors="replace")
                    yield DocumentChunk(
                        chunk_id=chunk_id,
                        total_chunks=-1,
                        content=content,
                        byte_offset=offset,
                        byte_length=cut,
                    )
                    buffer = buffer[cut - self.overlap_bytes:] if self.overlap_bytes else buffer[cut:]
                    offset += cut
                    chunk_id += 1

    def estimate_chunk_count(self, text_length_bytes: int) -> int:
        effective_chunk = self.chunk_size_bytes - self.overlap_bytes
        return math.ceil(text_length_bytes / max(effective_chunk, 1))


# ---------------------------------------------------------------------------
# Lazy Loader
# ---------------------------------------------------------------------------

class LazyModule(Generic[T]):
    """
    Lazy-loads a large module/collection on first access.
    Prevents loading everything at startup.
    """

    def __init__(self, loader: Callable[[], T], name: str = ""):
        self._loader = loader
        self._value: Optional[T] = None
        self._loaded = False
        self._load_time_s: float = 0.0
        self.name = name

    def get(self) -> T:
        if not self._loaded:
            t0 = time.perf_counter()
            self._value = self._loader()
            self._load_time_s = time.perf_counter() - t0
            self._loaded = True
        return self._value  # type: ignore[return-value]

    def unload(self):
        self._value = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_time_ms(self) -> float:
        return self._load_time_s * 1000


class LazyCollection:
    """Manages a collection of lazy-loaded modules."""

    def __init__(self):
        self._modules: Dict[str, LazyModule] = {}

    def register(self, name: str, loader: Callable, load_on_register: bool = False):
        module = LazyModule(loader=loader, name=name)
        self._modules[name] = module
        if load_on_register:
            module.get()

    def get(self, name: str) -> Any:
        module = self._modules.get(name)
        if not module:
            raise KeyError(f"Module '{name}' not registered")
        return module.get()

    def unload(self, name: str):
        module = self._modules.get(name)
        if module:
            module.unload()

    def unload_all(self):
        for m in self._modules.values():
            m.unload()
        gc.collect()

    def status(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "loaded": m.is_loaded,
                "load_time_ms": round(m.load_time_ms, 2),
            }
            for name, m in self._modules.items()
        }


# ---------------------------------------------------------------------------
# Memory Leak Detector
# ---------------------------------------------------------------------------

class MemoryLeakDetector:
    """
    Tracks memory allocations over time and flags suspicious growth patterns.
    Uses tracemalloc for allocation tracking.
    """

    def __init__(self, history_size: int = LEAK_HISTORY_SIZE):
        self._history: deque = deque(maxlen=history_size)
        self._allocation_snapshots: List[tracemalloc.Snapshot] = []
        self._running = False
        self.history_size = history_size

    def start(self):
        if not tracemalloc.is_tracing():
            tracemalloc.start(10)   # 10 frames
        self._running = True

    def stop(self):
        self._running = False

    def record_sample(self, label: str = ""):
        snap = take_snapshot(label=label)
        self._history.append(snap)
        if tracemalloc.is_tracing():
            self._allocation_snapshots.append(tracemalloc.take_snapshot())
            if len(self._allocation_snapshots) > 10:
                self._allocation_snapshots.pop(0)

    def get_growth_trend(self) -> List[float]:
        return [s.tracemalloc_current_mb for s in self._history]

    def detect_leaks(self) -> LeakReport:
        trend = self.get_growth_trend()
        if len(trend) < 3:
            return LeakReport(
                suspected_leaks=[],
                total_growth_mb=0.0,
                sampling_duration_s=0.0,
                recommendation="Not enough samples. Call record_sample() more times.",
            )

        total_growth = trend[-1] - trend[0]
        duration_s = (self._history[-1].timestamp - self._history[0].timestamp) if len(self._history) >= 2 else 0.0

        # Linear regression to detect monotonic growth
        n = len(trend)
        x_mean = (n - 1) / 2
        y_mean = sum(trend) / n
        num = sum((i - x_mean) * (trend[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0.0

        suspected: List[Dict[str, Any]] = []

        if slope > 0.01:   # Growing > 0.01 MB per sample
            # Compare tracemalloc snapshots
            if len(self._allocation_snapshots) >= 2:
                old_snap = self._allocation_snapshots[0]
                new_snap = self._allocation_snapshots[-1]
                try:
                    stats = new_snap.compare_to(old_snap, "lineno")
                    for stat in stats[:5]:
                        if stat.size_diff > 0:
                            suspected.append({
                                "location": str(stat.traceback),
                                "size_diff_kb": round(stat.size_diff / 1024, 2),
                                "count_diff": stat.count_diff,
                            })
                except Exception:
                    pass

            if not suspected:
                suspected.append({
                    "location": "unknown (enable tracemalloc for details)",
                    "size_diff_kb": round(total_growth * 1024, 2),
                    "count_diff": -1,
                })

        growth_rate_mb_per_s = slope / SAMPLE_INTERVAL_S if duration_s > 0 else 0.0

        if slope > 0.1:
            recommendation = f"CRITICAL: Memory growing at ~{growth_rate_mb_per_s:.2f} MB/s. Check for unbounded caches or retained references."
        elif slope > 0.01:
            recommendation = f"WARNING: Slow memory growth detected ({slope:.4f} MB/sample). Review recent allocation hotspots."
        else:
            recommendation = "OK: No significant memory leak detected."

        return LeakReport(
            suspected_leaks=suspected,
            total_growth_mb=round(total_growth, 4),
            sampling_duration_s=round(duration_s, 2),
            recommendation=recommendation,
        )

    def clear(self):
        self._history.clear()
        self._allocation_snapshots.clear()


# ---------------------------------------------------------------------------
# Memory Profiler
# ---------------------------------------------------------------------------

class MemoryProfiler:
    """Profile memory usage of callable operations."""

    def __init__(self):
        self._profiles: List[ModuleMemoryProfile] = []

    def profile(self, module_name: str, fn: Callable, *args, **kwargs) -> ModuleMemoryProfile:
        """Run fn and measure its memory impact."""
        gc.collect()
        if not tracemalloc.is_tracing():
            tracemalloc.start(5)

        tracemalloc.clear_traces()
        before_current, before_peak = tracemalloc.get_traced_memory()

        t0 = time.perf_counter()
        try:
            fn(*args, **kwargs)
        except Exception:
            pass
        elapsed = time.perf_counter() - t0

        after_current, after_peak = tracemalloc.get_traced_memory()

        # Get top allocations
        snapshot = tracemalloc.take_snapshot()
        top_allocs = []
        try:
            stats = snapshot.statistics("lineno")[:5]
            top_allocs = [(str(s.traceback), s.size) for s in stats]
        except Exception:
            pass

        baseline_mb = bytes_to_mb(before_current)
        peak_mb = bytes_to_mb(after_peak)
        delta_mb = bytes_to_mb(after_current - before_current)

        if delta_mb > 100:
            recommendation = f"High memory usage ({delta_mb:.1f} MB). Consider chunking large inputs."
        elif delta_mb > 50:
            recommendation = f"Moderate memory usage ({delta_mb:.1f} MB). Acceptable for this workload."
        else:
            recommendation = f"Good memory efficiency ({delta_mb:.1f} MB delta)."

        profile = ModuleMemoryProfile(
            module_name=module_name,
            baseline_mb=round(baseline_mb, 4),
            peak_mb=round(peak_mb, 4),
            delta_mb=round(delta_mb, 4),
            top_allocations=top_allocs,
            duration_s=round(elapsed, 4),
            recommendation=recommendation,
        )
        self._profiles.append(profile)
        return profile

    def get_profiles(self) -> List[ModuleMemoryProfile]:
        return list(self._profiles)


# ---------------------------------------------------------------------------
# Main MemoryOptimizer
# ---------------------------------------------------------------------------

class MemoryOptimizer:
    """
    Unified memory management for SintraPrime-Unified.
    Profiles, optimizes, detects leaks, and gives capacity recommendations.
    """

    def __init__(
        self,
        system_limit_bytes: int = DEFAULT_SYSTEM_LIMIT_BYTES,
        cache_budget_bytes: int = DEFAULT_CACHE_MAX_BYTES,
    ):
        self.system_limit_bytes = system_limit_bytes
        self.cache_budget_bytes = cache_budget_bytes

        self.cache_manager = CacheManager(global_max_bytes=cache_budget_bytes)
        self.chunker = DocumentChunker()
        self.lazy_collection = LazyCollection()
        self.leak_detector = MemoryLeakDetector()
        self.profiler = MemoryProfiler()

        # Built-in caches
        self._doc_cache = self.cache_manager.create_cache("documents", max_bytes=128 * 1024 * 1024)
        self._analysis_cache = self.cache_manager.create_cache("analysis", max_bytes=64 * 1024 * 1024)
        self._search_cache = self.cache_manager.create_cache("search", max_bytes=32 * 1024 * 1024)

    @property
    def document_cache(self) -> LRUCache:
        return self._doc_cache

    @property
    def analysis_cache(self) -> LRUCache:
        return self._analysis_cache

    @property
    def search_cache(self) -> LRUCache:
        return self._search_cache

    def estimate_available_memory_mb(self) -> float:
        """Estimate remaining memory before hitting system limit."""
        current_mb, _ = get_tracemalloc_stats()
        system_limit_mb = bytes_to_mb(self.system_limit_bytes)
        cache_used_mb = bytes_to_mb(self.cache_manager.total_bytes_used())
        used_mb = current_mb + cache_used_mb
        return max(system_limit_mb - used_mb, 0.0)

    def agent_capacity_recommendation(self, agent_memory_mb: float = 200.0) -> str:
        """
        Tell the user how many more agents can be spawned.
        Example: "You can run 3 more agents before hitting 8GB limit"
        """
        available_mb = self.estimate_available_memory_mb()
        if agent_memory_mb <= 0:
            return "Cannot estimate: invalid agent_memory_mb."
        max_agents = int(available_mb / agent_memory_mb)
        limit_gb = bytes_to_mb(self.system_limit_bytes) / 1024
        return (
            f"You can run {max_agents} more agent(s) before hitting {limit_gb:.0f}GB limit "
            f"(~{available_mb:.0f}MB available, ~{agent_memory_mb:.0f}MB per agent)."
        )

    def get_recommendations(self) -> List[MemoryRecommendation]:
        """Generate actionable memory recommendations."""
        recs: List[MemoryRecommendation] = []
        available_mb = self.estimate_available_memory_mb()
        limit_mb = bytes_to_mb(self.system_limit_bytes)

        usage_pct = 1 - (available_mb / limit_mb) if limit_mb > 0 else 0

        if usage_pct > 0.9:
            recs.append(MemoryRecommendation(
                severity="critical",
                message=f"Memory at {usage_pct * 100:.0f}% of limit.",
                action="Immediately clear caches and unload unused modules.",
                estimated_savings_mb=bytes_to_mb(self.cache_manager.total_bytes_used()),
            ))
        elif usage_pct > 0.7:
            recs.append(MemoryRecommendation(
                severity="warning",
                message=f"Memory at {usage_pct * 100:.0f}% of limit.",
                action="Consider clearing analysis_cache and reducing chunk sizes.",
                estimated_savings_mb=self._analysis_cache.stats.current_bytes / (1024 * 1024),
            ))

        for name, stats in self.cache_manager.get_all_stats().items():
            if stats.hit_rate < 0.2 and stats.current_items > 10:
                recs.append(MemoryRecommendation(
                    severity="warning",
                    message=f"Cache '{name}' has low hit rate ({stats.hit_rate:.1%}).",
                    action=f"Reduce '{name}' cache size or adjust eviction policy.",
                    estimated_savings_mb=bytes_to_mb(stats.current_bytes) * 0.5,
                ))

        if not recs:
            recs.append(MemoryRecommendation(
                severity="info",
                message=f"Memory usage healthy ({usage_pct * 100:.0f}% used).",
                action="No action required.",
                estimated_savings_mb=0.0,
            ))

        return recs

    def optimize_for_large_document(self, estimated_pages: int, words_per_page: int = 400) -> Dict[str, Any]:
        """Recommend settings for processing a large document."""
        estimated_bytes = estimated_pages * words_per_page * 6   # avg 6 bytes/word
        chunks = self.chunker.estimate_chunk_count(estimated_bytes)
        memory_per_chunk_mb = bytes_to_mb(self.chunker.chunk_size_bytes) * 3  # 3x for processing overhead
        available_mb = self.estimate_available_memory_mb()

        return {
            "document_estimated_mb": round(bytes_to_mb(estimated_bytes), 2),
            "recommended_chunk_size_bytes": self.chunker.chunk_size_bytes,
            "estimated_chunks": chunks,
            "memory_per_chunk_mb": round(memory_per_chunk_mb, 2),
            "can_process": available_mb > memory_per_chunk_mb,
            "available_memory_mb": round(available_mb, 2),
            "strategy": "streaming_chunks" if estimated_pages > 100 else "batch",
        }

    def run_full_profile(self) -> Dict[str, Any]:
        """Profile memory across simulated SintraPrime operations."""
        results = {}

        # Profile document parsing
        def _parse_sim():
            text = " ".join(["word"] * 10000)
            return text.split()

        profile = self.profiler.profile("document_parser", _parse_sim)
        results["document_parser"] = {
            "delta_mb": profile.delta_mb,
            "recommendation": profile.recommendation,
        }

        # Profile chunking
        def _chunk_sim():
            big_text = "legal document content. " * 5000
            return self.chunker.chunk_text(big_text)

        profile2 = self.profiler.profile("document_chunker", _chunk_sim)
        results["document_chunker"] = {
            "delta_mb": profile2.delta_mb,
            "recommendation": profile2.recommendation,
        }

        # Profile cache operations
        def _cache_sim():
            for i in range(200):
                self._doc_cache.put(f"doc_{i}", {"content": "x" * 1000, "id": i})
            return [self._doc_cache.get(f"doc_{i}") for i in range(100)]

        profile3 = self.profiler.profile("cache_operations", _cache_sim)
        results["cache_operations"] = {
            "delta_mb": profile3.delta_mb,
            "recommendation": profile3.recommendation,
        }

        results["cache_stats"] = {k: {
            "hit_rate": round(s.hit_rate, 3),
            "current_mb": round(bytes_to_mb(s.current_bytes), 4),
        } for k, s in self.cache_manager.get_all_stats().items()}

        results["recommendations"] = [
            {"severity": r.severity, "message": r.message, "action": r.action}
            for r in self.get_recommendations()
        ]

        results["agent_capacity"] = self.agent_capacity_recommendation()
        return results


# ---------------------------------------------------------------------------
# Decorator: memory-profile a function
# ---------------------------------------------------------------------------

def memory_profile(label: Optional[str] = None):
    """Decorator that prints memory usage of a function."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            name = label or fn.__name__
            if not tracemalloc.is_tracing():
                tracemalloc.start()
            tracemalloc.clear_traces()
            t0 = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed = (time.perf_counter() - t0) * 1000
            current, peak = tracemalloc.get_traced_memory()
            print(f"[memory_profile] {name}: current={bytes_to_mb(current):.3f}MB "
                  f"peak={bytes_to_mb(peak):.3f}MB elapsed={elapsed:.1f}ms")
            return result
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tracemalloc.start()
    optimizer = MemoryOptimizer(system_limit_bytes=8 * 1024 * 1024 * 1024)
    print("Running full memory profile...")
    results = optimizer.run_full_profile()
    import json
    print(json.dumps(results, indent=2, default=str))
    print("\n" + optimizer.agent_capacity_recommendation(agent_memory_mb=150))
    print("\nLarge document recommendations:")
    print(json.dumps(optimizer.optimize_for_large_document(500), indent=2))
