"""
SintraPrime-Unified: Real-Time Stream Processing Engine
Handles document streams with async pipelines, backpressure, and event bus.
Built-in streams: court_filings, federal_register, case_law_updates, financial_data
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, AsyncIterator, Callable, Coroutine, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations & Constants
# ---------------------------------------------------------------------------

class StreamType(Enum):
    COURT_FILINGS = "court_filings"
    FEDERAL_REGISTER = "federal_register"
    CASE_LAW_UPDATES = "case_law_updates"
    FINANCIAL_DATA = "financial_data"
    CUSTOM = "custom"


class DocumentStatus(Enum):
    PENDING = auto()
    INGESTED = auto()
    PARSED = auto()
    ANALYZED = auto()
    STORED = auto()
    NOTIFIED = auto()
    FAILED = auto()
    DROPPED = auto()   # backpressure


class Priority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


MAX_QUEUE_SIZE = 500
DEFAULT_BACKPRESSURE_THRESHOLD = 0.8   # 80% full → slow producer
WORKER_CONCURRENCY = 4


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class StreamDocument:
    doc_id: str
    stream_type: StreamType
    content: str
    metadata: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    status: DocumentStatus = DocumentStatus.PENDING
    created_at: float = field(default_factory=time.time)
    processed_at: Optional[float] = None
    processing_steps: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = hashlib.sha256(self.content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["stream_type"] = self.stream_type.value
        d["priority"] = self.priority.name
        d["status"] = self.status.name
        return d

    def add_step(self, step: str, result: Any, elapsed_ms: float):
        self.processing_steps.append({
            "step": step,
            "result_summary": str(result)[:200],
            "elapsed_ms": round(elapsed_ms, 3),
            "timestamp": time.time(),
        })


@dataclass
class StreamMetrics:
    stream_type: str
    total_received: int = 0
    total_processed: int = 0
    total_dropped: int = 0
    total_failed: int = 0
    avg_processing_ms: float = 0.0
    current_queue_depth: int = 0
    backpressure_events: int = 0
    bytes_processed: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class StreamEvent:
    event_id: str
    event_type: str          # document.ingested / document.processed / pipeline.error / etc.
    stream_type: str
    doc_id: Optional[str]
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

async def stage_ingest(doc: StreamDocument) -> StreamDocument:
    """Validate and fingerprint incoming document."""
    t0 = time.perf_counter()
    if not doc.content:
        raise ValueError("Empty document content")
    if not doc.doc_id:
        doc.doc_id = str(uuid.uuid4())
    # Simulate light I/O
    await asyncio.sleep(0)
    doc.status = DocumentStatus.INGESTED
    doc.add_step("ingest", {"size": len(doc.content), "checksum": doc.checksum},
                 (time.perf_counter() - t0) * 1000)
    return doc


async def stage_parse(doc: StreamDocument) -> StreamDocument:
    """Parse document content into structured form."""
    t0 = time.perf_counter()
    await asyncio.sleep(0)
    words = doc.content.split()
    sentences = doc.content.count(".") + doc.content.count("?") + doc.content.count("!")
    parsed = {
        "word_count": len(words),
        "sentence_count": sentences,
        "avg_word_length": sum(len(w) for w in words) / max(len(words), 1),
        "has_legal_terms": any(term in doc.content.lower() for term in
                               ["whereas", "hereby", "pursuant", "hereinafter", "notwithstanding"]),
    }
    doc.metadata["parsed"] = parsed
    doc.status = DocumentStatus.PARSED
    doc.add_step("parse", parsed, (time.perf_counter() - t0) * 1000)
    return doc


async def stage_analyze(doc: StreamDocument) -> StreamDocument:
    """Extract insights and entities."""
    t0 = time.perf_counter()
    await asyncio.sleep(0)
    content_lower = doc.content.lower()
    analysis = {
        "stream_type": doc.stream_type.value,
        "entities": [],
        "topics": [],
        "urgency_score": 0.0,
    }

    # Stream-specific analysis
    if doc.stream_type == StreamType.COURT_FILINGS:
        analysis["topics"] = ["litigation", "civil_procedure"]
        analysis["urgency_score"] = 0.8 if "emergency" in content_lower else 0.4
        analysis["entities"] = [w for w in doc.content.split() if w[0].isupper()][:5]
    elif doc.stream_type == StreamType.FEDERAL_REGISTER:
        analysis["topics"] = ["regulation", "federal_law"]
        analysis["urgency_score"] = 0.6 if "effective immediately" in content_lower else 0.3
    elif doc.stream_type == StreamType.CASE_LAW_UPDATES:
        analysis["topics"] = ["precedent", "case_law"]
        analysis["urgency_score"] = 0.5
    elif doc.stream_type == StreamType.FINANCIAL_DATA:
        analysis["topics"] = ["finance", "compliance"]
        analysis["urgency_score"] = 0.7 if "material" in content_lower else 0.2

    doc.metadata["analysis"] = analysis
    doc.status = DocumentStatus.ANALYZED
    doc.add_step("analyze", analysis, (time.perf_counter() - t0) * 1000)
    return doc


async def stage_store(doc: StreamDocument) -> StreamDocument:
    """Persist document (simulated)."""
    t0 = time.perf_counter()
    await asyncio.sleep(0)
    store_record = {
        "stored_id": doc.doc_id,
        "index_key": f"{doc.stream_type.value}:{doc.checksum}",
        "size_bytes": len(doc.content.encode()),
    }
    doc.metadata["store_record"] = store_record
    doc.status = DocumentStatus.STORED
    doc.add_step("store", store_record, (time.perf_counter() - t0) * 1000)
    return doc


async def stage_notify(doc: StreamDocument, subscribers: List[Callable]) -> StreamDocument:
    """Notify all event subscribers."""
    t0 = time.perf_counter()
    event = StreamEvent(
        event_id=str(uuid.uuid4()),
        event_type="document.processed",
        stream_type=doc.stream_type.value,
        doc_id=doc.doc_id,
        payload={"status": doc.status.name, "metadata_keys": list(doc.metadata.keys())},
    )
    for sub in subscribers:
        try:
            if asyncio.iscoroutinefunction(sub):
                await sub(event)
            else:
                sub(event)
        except Exception as exc:
            logger.warning("Subscriber error: %s", exc)
    doc.status = DocumentStatus.NOTIFIED
    doc.processed_at = time.time()
    doc.add_step("notify", {"subscribers_notified": len(subscribers)},
                 (time.perf_counter() - t0) * 1000)
    return doc


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------

class EventBus:
    """
    Publish-subscribe event bus for document stream events.
    Supports sync and async subscribers, topic filtering.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: deque = deque(maxlen=1000)
        self._lock = asyncio.Lock()
        self._publish_count = 0

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to an event type. Use '*' for all events."""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: StreamEvent):
        """Publish an event to all matching subscribers."""
        self._history.append(event)
        self._publish_count += 1

        targets = set(self._subscribers.get(event.event_type, []))
        targets |= set(self._subscribers.get("*", []))

        for handler in targets:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.warning("EventBus handler error (%s): %s", event.event_type, exc)

    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[StreamEvent]:
        events = list(self._history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_published": self._publish_count,
            "history_size": len(self._history),
            "subscriber_counts": {k: len(v) for k, v in self._subscribers.items()},
        }


# ---------------------------------------------------------------------------
# Backpressure Controller
# ---------------------------------------------------------------------------

class BackpressureController:
    """
    Monitors queue depth and applies backpressure when queues fill up.
    Uses an exponential backoff delay on producers.
    """

    def __init__(self, threshold: float = DEFAULT_BACKPRESSURE_THRESHOLD):
        self.threshold = threshold
        self.backpressure_events = 0
        self._max_delay_s = 0.5

    async def maybe_pause(self, queue: asyncio.Queue):
        """If queue is above threshold, wait proportionally."""
        if queue.maxsize == 0:
            return
        fill_ratio = queue.qsize() / queue.maxsize
        if fill_ratio >= self.threshold:
            delay = self._max_delay_s * (fill_ratio - self.threshold) / (1 - self.threshold)
            self.backpressure_events += 1
            logger.debug("Backpressure: queue %.0f%% full, pausing %.3fs", fill_ratio * 100, delay)
            await asyncio.sleep(delay)

    def is_full(self, queue: asyncio.Queue) -> bool:
        return queue.maxsize > 0 and queue.qsize() >= queue.maxsize


# ---------------------------------------------------------------------------
# Stream Pipeline
# ---------------------------------------------------------------------------

class StreamPipeline:
    """
    Async pipeline: ingest → parse → analyze → store → notify
    Supports concurrent workers and backpressure.
    """

    def __init__(
        self,
        stream_type: StreamType,
        event_bus: EventBus,
        concurrency: int = WORKER_CONCURRENCY,
        queue_size: int = MAX_QUEUE_SIZE,
    ):
        self.stream_type = stream_type
        self.event_bus = event_bus
        self.concurrency = concurrency
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._backpressure = BackpressureController()
        self._metrics = StreamMetrics(stream_type=stream_type.value)
        self._subscribers: List[Callable] = []
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._processing_times: deque = deque(maxlen=500)

    def add_subscriber(self, handler: Callable):
        self._subscribers.append(handler)

    async def ingest(self, doc: StreamDocument) -> bool:
        """Submit document to pipeline. Returns False if dropped (full queue)."""
        await self._backpressure.maybe_pause(self._queue)
        if self._backpressure.is_full(self._queue):
            doc.status = DocumentStatus.DROPPED
            self._metrics.total_dropped += 1
            await self.event_bus.publish(StreamEvent(
                event_id=str(uuid.uuid4()),
                event_type="document.dropped",
                stream_type=self.stream_type.value,
                doc_id=doc.doc_id,
                payload={"reason": "queue_full"},
            ))
            return False

        await self._queue.put(doc)
        self._metrics.total_received += 1
        self._metrics.current_queue_depth = self._queue.qsize()
        return True

    async def _process_document(self, doc: StreamDocument):
        t0 = time.perf_counter()
        try:
            doc = await stage_ingest(doc)
            doc = await stage_parse(doc)
            doc = await stage_analyze(doc)
            doc = await stage_store(doc)
            doc = await stage_notify(doc, self._subscribers)

            elapsed_ms = (time.perf_counter() - t0) * 1000
            self._processing_times.append(elapsed_ms)
            self._metrics.total_processed += 1
            self._metrics.bytes_processed += len(doc.content.encode())
            if self._processing_times:
                self._metrics.avg_processing_ms = sum(self._processing_times) / len(self._processing_times)

            await self.event_bus.publish(StreamEvent(
                event_id=str(uuid.uuid4()),
                event_type="document.processed",
                stream_type=self.stream_type.value,
                doc_id=doc.doc_id,
                payload={"elapsed_ms": elapsed_ms, "steps": len(doc.processing_steps)},
            ))
        except Exception as exc:
            doc.status = DocumentStatus.FAILED
            doc.error = str(exc)
            self._metrics.total_failed += 1
            logger.error("Pipeline error for %s: %s", doc.doc_id, exc)
            await self.event_bus.publish(StreamEvent(
                event_id=str(uuid.uuid4()),
                event_type="pipeline.error",
                stream_type=self.stream_type.value,
                doc_id=doc.doc_id,
                payload={"error": str(exc)},
            ))

    async def _worker(self):
        while self._running or not self._queue.empty():
            try:
                doc = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                self._metrics.current_queue_depth = self._queue.qsize()
                await self._process_document(doc)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.error("Worker exception: %s", exc)

    async def start(self):
        """Start pipeline workers."""
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(), name=f"worker_{self.stream_type.value}_{i}")
            for i in range(self.concurrency)
        ]

    async def stop(self, wait: bool = True):
        """Gracefully stop workers."""
        self._running = False
        if wait:
            await self._queue.join()
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

    @property
    def metrics(self) -> StreamMetrics:
        self._metrics.backpressure_events = self._backpressure.backpressure_events
        return self._metrics


# ---------------------------------------------------------------------------
# Built-in Stream Generators
# ---------------------------------------------------------------------------

COURT_FILING_TEMPLATES = [
    "MOTION TO {action} in the matter of {party} v. {party2}, Case No. {case_no}. "
    "Plaintiff hereby moves pursuant to Rule {rule} of the Federal Rules of Civil Procedure.",
    "ORDER GRANTING {action}. The Court, having considered the motion filed by {party}, "
    "hereby ORDERS as follows: 1. {action} is GRANTED. 2. {party2} shall comply within {days} days.",
    "COMPLAINT for {claim} against {party}. Plaintiff {party2} brings this action pursuant to "
    "28 U.S.C. § {statute}. This Court has jurisdiction pursuant to Article III.",
]

FEDERAL_REGISTER_TEMPLATES = [
    "AGENCY: {agency}. ACTION: Final Rule. SUMMARY: This rule amends {cfr} to {action}. "
    "EFFECTIVE DATE: {date}. FOR FURTHER INFORMATION CONTACT: {contact}.",
    "PROPOSED RULE: The {agency} proposes to amend {cfr}. This proposed rule would {action}. "
    "Comments must be received on or before {date}.",
]

CASE_LAW_TEMPLATES = [
    "HOLDING: The {court} held that {holding}. FACTS: {party} brought suit against {party2} "
    "alleging {claim}. The district court ruled in favor of {party}. We AFFIRM.",
    "REVERSED. The lower court erred in finding {claim}. Under {statute}, {holding}. "
    "We remand for further proceedings consistent with this opinion.",
]

FINANCIAL_DATA_TEMPLATES = [
    "MATERIAL EVENT: {company} reports {event} with financial impact of ${amount}M. "
    "This event constitutes a material change pursuant to SEC Rule 10b-5.",
    "QUARTERLY DISCLOSURE: {company} Q{quarter} revenue: ${amount}M. Net income: ${net}M. "
    "EPS: ${eps}. Guidance raised for FY{year}.",
]


def _random_val(template: str) -> str:
    replacements = {
        "{action}": random.choice(["DISMISS", "SUMMARY JUDGMENT", "INJUNCTION", "STAY", "COMPEL ARBITRATION"]),
        "{party}": random.choice(["Smith Corp.", "Johnson Trust", "ABC Holdings", "First National Bank"]),
        "{party2}": random.choice(["United States", "State of California", "Doe Enterprises", "XYZ LLC"]),
        "{case_no}": f"{random.randint(20, 25)}-cv-{random.randint(10000, 99999)}",
        "{rule}": str(random.choice([12, 26, 34, 56, 65])),
        "{days}": str(random.choice([14, 21, 30, 60])),
        "{claim}": random.choice(["breach of contract", "fraud", "negligence", "copyright infringement"]),
        "{statute}": str(random.choice([1331, 1332, 1367, 1441])),
        "{agency}": random.choice(["SEC", "FTC", "EPA", "CFPB", "DOJ"]),
        "{cfr}": f"{random.randint(1, 50)} CFR Part {random.randint(1, 999)}",
        "{date}": f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        "{contact}": "contact@agency.gov, (202) 555-0100",
        "{court}": random.choice(["Ninth Circuit", "Second Circuit", "SCOTUS", "D.C. Circuit"]),
        "{holding}": random.choice(["the statute does not preempt state law",
                                    "the evidence was insufficient",
                                    "the regulation exceeds agency authority"]),
        "{company}": random.choice(["Acme Corp", "TechGiant Inc", "LegalTech LLC", "Prime Finance"]),
        "{event}": random.choice(["merger completion", "revenue restatement", "executive departure"]),
        "{amount}": str(random.randint(10, 9000)),
        "{quarter}": str(random.randint(1, 4)),
        "{net}": str(random.randint(1, 500)),
        "{eps}": f"{random.uniform(0.1, 10.0):.2f}",
        "{year}": "2026",
    }
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


async def court_filings_generator(interval_s: float = 0.05) -> AsyncIterator[StreamDocument]:
    """Yield synthetic court filing documents."""
    while True:
        tmpl = random.choice(COURT_FILING_TEMPLATES)
        content = _random_val(tmpl)
        yield StreamDocument(
            doc_id=str(uuid.uuid4()),
            stream_type=StreamType.COURT_FILINGS,
            content=content,
            metadata={"source": "PACER", "jurisdiction": random.choice(["federal", "state"])},
            priority=random.choice(list(Priority)),
        )
        await asyncio.sleep(interval_s)


async def federal_register_generator(interval_s: float = 0.1) -> AsyncIterator[StreamDocument]:
    """Yield synthetic Federal Register entries."""
    while True:
        tmpl = random.choice(FEDERAL_REGISTER_TEMPLATES)
        content = _random_val(tmpl)
        yield StreamDocument(
            doc_id=str(uuid.uuid4()),
            stream_type=StreamType.FEDERAL_REGISTER,
            content=content,
            metadata={"source": "federalregister.gov", "volume": random.randint(80, 91)},
            priority=Priority.NORMAL,
        )
        await asyncio.sleep(interval_s)


async def case_law_generator(interval_s: float = 0.08) -> AsyncIterator[StreamDocument]:
    """Yield synthetic case law updates."""
    while True:
        tmpl = random.choice(CASE_LAW_TEMPLATES)
        content = _random_val(tmpl)
        yield StreamDocument(
            doc_id=str(uuid.uuid4()),
            stream_type=StreamType.CASE_LAW_UPDATES,
            content=content,
            metadata={"source": "CourtListener", "precedential": random.choice([True, False])},
            priority=Priority.HIGH,
        )
        await asyncio.sleep(interval_s)


async def financial_data_generator(interval_s: float = 0.03) -> AsyncIterator[StreamDocument]:
    """Yield synthetic financial disclosure data."""
    while True:
        tmpl = random.choice(FINANCIAL_DATA_TEMPLATES)
        content = _random_val(tmpl)
        yield StreamDocument(
            doc_id=str(uuid.uuid4()),
            stream_type=StreamType.FINANCIAL_DATA,
            content=content,
            metadata={"source": "SEC EDGAR", "form_type": random.choice(["8-K", "10-Q", "10-K"])},
            priority=Priority.HIGH,
        )
        await asyncio.sleep(interval_s)


# ---------------------------------------------------------------------------
# Stream Processor (orchestrator)
# ---------------------------------------------------------------------------

class StreamProcessor:
    """
    High-level orchestrator that manages multiple stream pipelines.
    Connects generators to pipelines with backpressure and event bus.
    """

    def __init__(self, concurrency: int = WORKER_CONCURRENCY):
        self.concurrency = concurrency
        self.event_bus = EventBus()
        self._pipelines: Dict[StreamType, StreamPipeline] = {}
        self._generator_tasks: List[asyncio.Task] = []
        self._running = False
        self._global_event_log: deque = deque(maxlen=2000)

        # Log all events to global log
        self.event_bus.subscribe("*", self._log_event)

    def _log_event(self, event: StreamEvent):
        self._global_event_log.append(event)

    def register_stream(self, stream_type: StreamType, queue_size: int = MAX_QUEUE_SIZE):
        """Register a new stream pipeline."""
        pipeline = StreamPipeline(
            stream_type=stream_type,
            event_bus=self.event_bus,
            concurrency=self.concurrency,
            queue_size=queue_size,
        )
        self._pipelines[stream_type] = pipeline
        return pipeline

    async def _run_generator(self, stream_type: StreamType, gen: AsyncIterator[StreamDocument], max_docs: Optional[int] = None):
        pipeline = self._pipelines.get(stream_type)
        if not pipeline:
            return
        count = 0
        async for doc in gen:
            if not self._running:
                break
            await pipeline.ingest(doc)
            count += 1
            if max_docs and count >= max_docs:
                break

    async def start(self, enable_builtin_streams: bool = True, max_docs_per_stream: Optional[int] = None):
        """Start all registered pipelines and optionally built-in generators."""
        self._running = True

        # Start pipelines
        for pipeline in self._pipelines.values():
            await pipeline.start()

        # Start built-in generators
        if enable_builtin_streams:
            builtin_generators = {
                StreamType.COURT_FILINGS: court_filings_generator(),
                StreamType.FEDERAL_REGISTER: federal_register_generator(),
                StreamType.CASE_LAW_UPDATES: case_law_generator(),
                StreamType.FINANCIAL_DATA: financial_data_generator(),
            }
            for stream_type, gen in builtin_generators.items():
                if stream_type in self._pipelines:
                    task = asyncio.create_task(
                        self._run_generator(stream_type, gen, max_docs_per_stream),
                        name=f"gen_{stream_type.value}",
                    )
                    self._generator_tasks.append(task)

    async def stop(self):
        """Gracefully stop all generators and pipelines."""
        self._running = False
        for task in self._generator_tasks:
            task.cancel()
        await asyncio.gather(*self._generator_tasks, return_exceptions=True)
        self._generator_tasks = []

        for pipeline in self._pipelines.values():
            await pipeline.stop(wait=True)

    async def ingest_document(self, stream_type: StreamType, content: str, metadata: Optional[Dict] = None, priority: Priority = Priority.NORMAL) -> Optional[str]:
        """Manually ingest a single document into a stream."""
        pipeline = self._pipelines.get(stream_type)
        if not pipeline:
            raise ValueError(f"Stream not registered: {stream_type.value}")
        doc = StreamDocument(
            doc_id=str(uuid.uuid4()),
            stream_type=stream_type,
            content=content,
            metadata=metadata or {},
            priority=priority,
        )
        accepted = await pipeline.ingest(doc)
        return doc.doc_id if accepted else None

    def get_all_metrics(self) -> Dict[str, Any]:
        return {
            stream_type.value: {
                "total_received": m.total_received,
                "total_processed": m.total_processed,
                "total_dropped": m.total_dropped,
                "total_failed": m.total_failed,
                "avg_processing_ms": round(m.avg_processing_ms, 3),
                "current_queue_depth": m.current_queue_depth,
                "backpressure_events": m.backpressure_events,
                "bytes_processed": m.bytes_processed,
            }
            for stream_type, pipeline in self._pipelines.items()
            if (m := pipeline.metrics)
        }

    def get_event_history(self, event_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        events = list(self._global_event_log)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [asdict(e) for e in events[-limit:]]

    @property
    def is_running(self) -> bool:
        return self._running


# ---------------------------------------------------------------------------
# Quick setup helper
# ---------------------------------------------------------------------------

def create_default_processor() -> StreamProcessor:
    """Create a processor with all built-in streams pre-registered."""
    processor = StreamProcessor()
    for stream_type in [
        StreamType.COURT_FILINGS,
        StreamType.FEDERAL_REGISTER,
        StreamType.CASE_LAW_UPDATES,
        StreamType.FINANCIAL_DATA,
    ]:
        processor.register_stream(stream_type)
    return processor


async def run_demo(duration_s: float = 2.0, max_docs: int = 10):
    """Quick demo: process documents for a short duration."""
    processor = create_default_processor()
    received_events: List[StreamEvent] = []

    def on_event(event: StreamEvent):
        received_events.append(event)

    processor.event_bus.subscribe("document.processed", on_event)
    await processor.start(enable_builtin_streams=True, max_docs_per_stream=max_docs)
    await asyncio.sleep(duration_s)
    await processor.stop()

    metrics = processor.get_all_metrics()
    return {"metrics": metrics, "events_received": len(received_events)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    async def _main():
        print("🌊 SintraPrime Stream Processor Demo")
        result = await run_demo(duration_s=1.5, max_docs=5)
        print(json.dumps(result, indent=2))

    asyncio.run(_main())
    sys.exit(0)
