"""
Distributed Tracing for SintraPrime-Unified
OpenTelemetry-compatible trace/span model (pure Python, no otel deps).
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Status codes
# ---------------------------------------------------------------------------

class SpanStatus(str, Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Span – core tracing unit
# ---------------------------------------------------------------------------

@dataclass
class Span:
    trace_id: str
    span_id: str
    name: str
    start: float
    parent_span_id: Optional[str] = None
    end: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def finish(self, status: SpanStatus = SpanStatus.OK, message: str = "") -> None:
        if self.end is None:
            self.end = time.time()
        self.status = status
        self.status_message = message

    def finish_with_error(self, message: str = "") -> None:
        self.finish(SpanStatus.ERROR, message)

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end is not None:
            return (self.end - self.start) * 1000.0
        return None

    @property
    def is_finished(self) -> bool:
        return self.end is not None

    # ------------------------------------------------------------------
    # Annotation
    # ------------------------------------------------------------------

    def set_tag(self, key: str, value: Any) -> "Span":
        self.tags[key] = value
        return self

    def set_tags(self, tags: Dict[str, Any]) -> "Span":
        self.tags.update(tags)
        return self

    def log(self, message: str, level: str = "info", **fields: Any) -> "Span":
        entry: Dict[str, Any] = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            **fields,
        }
        self.logs.append(entry)
        return self

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "start": self.start,
            "start_iso": datetime.fromtimestamp(self.start, tz=timezone.utc).isoformat(),
            "end": self.end,
            "end_iso": (
                datetime.fromtimestamp(self.end, tz=timezone.utc).isoformat()
                if self.end else None
            ),
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "logs": self.logs,
            "status": self.status.value,
            "status_message": self.status_message,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Span":
        d = dict(d)
        d["status"] = SpanStatus(d.get("status", "unset"))
        for k in ("start_iso", "end_iso", "duration_ms"):
            d.pop(k, None)
        return cls(**d)


# ---------------------------------------------------------------------------
# TraceContext – propagate across agent calls
# ---------------------------------------------------------------------------

@dataclass
class TraceContext:
    trace_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)

    def to_headers(self) -> Dict[str, str]:
        """Serialize to HTTP-header-like dict for propagation."""
        headers = {
            "x-trace-id": self.trace_id,
        }
        if self.parent_span_id:
            headers["x-parent-span-id"] = self.parent_span_id
        if self.baggage:
            headers["x-baggage"] = json.dumps(self.baggage)
        return headers

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> "TraceContext":
        return cls(
            trace_id=headers.get("x-trace-id", str(uuid.uuid4())),
            parent_span_id=headers.get("x-parent-span-id"),
            baggage=json.loads(headers.get("x-baggage", "{}")),
        )

    def child_context(self, child_span_id: str) -> "TraceContext":
        return TraceContext(
            trace_id=self.trace_id,
            parent_span_id=child_span_id,
            baggage=dict(self.baggage),
        )


# ---------------------------------------------------------------------------
# Trace – collection of spans for one request / workflow
# ---------------------------------------------------------------------------

class Trace:
    def __init__(self, trace_id: Optional[str] = None, name: str = "") -> None:
        self.trace_id: str = trace_id or str(uuid.uuid4())
        self.name: str = name
        self._spans: Dict[str, Span] = {}
        self._root_span_id: Optional[str] = None

    def add_span(self, span: Span) -> None:
        self._spans[span.span_id] = span
        if span.parent_span_id is None and self._root_span_id is None:
            self._root_span_id = span.span_id

    def get_span(self, span_id: str) -> Optional[Span]:
        return self._spans.get(span_id)

    def root_span(self) -> Optional[Span]:
        return self._spans.get(self._root_span_id) if self._root_span_id else None

    def children_of(self, span_id: str) -> List[Span]:
        return [s for s in self._spans.values() if s.parent_span_id == span_id]

    def all_spans(self) -> List[Span]:
        return list(self._spans.values())

    def finished_spans(self) -> List[Span]:
        return [s for s in self._spans.values() if s.is_finished]

    def error_spans(self) -> List[Span]:
        return [s for s in self._spans.values() if s.status == SpanStatus.ERROR]

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        spans = self.all_spans()
        finished = self.finished_spans()
        durations = [s.duration_ms for s in finished if s.duration_ms is not None]
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "span_count": len(spans),
            "finished_count": len(finished),
            "error_count": len(self.error_spans()),
            "total_duration_ms": sum(durations) if durations else None,
            "max_duration_ms": max(durations) if durations else None,
            "min_duration_ms": min(durations) if durations else None,
        }

    # ------------------------------------------------------------------
    # Flame graph export (Chrome DevTools trace format)
    # ------------------------------------------------------------------

    def to_flame_graph(self) -> Dict[str, Any]:
        """
        Export as a Chrome DevTools-compatible trace JSON.
        Load in chrome://tracing for visual flame graph.
        """
        events = []
        for span in self._spans.values():
            if span.end is None:
                continue
            start_us = int(span.start * 1_000_000)
            dur_us = int((span.end - span.start) * 1_000_000)
            events.append({
                "name": span.name,
                "ph": "X",          # complete event
                "ts": start_us,
                "dur": dur_us,
                "pid": 1,
                "tid": span.span_id[:8],
                "args": {
                    "span_id": span.span_id,
                    "trace_id": span.trace_id,
                    "status": span.status.value,
                    **span.tags,
                },
            })
        return {"traceEvents": events, "displayTimeUnit": "ms"}

    def to_flame_graph_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_flame_graph(), indent=indent)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "root_span_id": self._root_span_id,
            "spans": [s.to_dict() for s in self._spans.values()],
            "summary": self.summary(),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Trace":
        trace = cls(trace_id=d["trace_id"], name=d.get("name", ""))
        for sd in d.get("spans", []):
            trace.add_span(Span.from_dict(sd))
        return trace


# ---------------------------------------------------------------------------
# Tracer – high-level API
# ---------------------------------------------------------------------------

class Tracer:
    """
    Central tracing service.

    Usage:
        tracer = Tracer(service_name="LegalAgent")
        with tracer.start_trace("review-contract") as (trace, root_span):
            root_span.set_tag("contract_id", "42")
            with tracer.start_span(trace, "extract-clauses", root_span.span_id) as span:
                span.set_tag("clause_count", 12)
    """

    def __init__(self, service_name: str = "sintra-prime") -> None:
        self.service_name = service_name
        self._traces: Dict[str, Trace] = {}

    # ------------------------------------------------------------------
    # Trace management
    # ------------------------------------------------------------------

    def new_trace(self, name: str = "", context: Optional[TraceContext] = None) -> Trace:
        trace_id = context.trace_id if context else str(uuid.uuid4())
        trace = Trace(trace_id=trace_id, name=name)
        self._traces[trace_id] = trace
        return trace

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        return self._traces.get(trace_id)

    def all_traces(self) -> List[Trace]:
        return list(self._traces.values())

    # ------------------------------------------------------------------
    # Span creation
    # ------------------------------------------------------------------

    def create_span(
        self,
        trace: Trace,
        name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Span:
        span = Span(
            trace_id=trace.trace_id,
            span_id=str(uuid.uuid4()),
            name=name,
            start=time.time(),
            parent_span_id=parent_span_id,
            tags={
                "service": self.service_name,
                **(tags or {}),
            },
        )
        trace.add_span(span)
        return span

    @contextmanager
    def start_span(
        self,
        trace: Trace,
        name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Generator[Span, None, None]:
        span = self.create_span(trace, name, parent_span_id=parent_span_id, tags=tags)
        try:
            yield span
            if not span.is_finished:
                span.finish(SpanStatus.OK)
        except Exception as exc:
            span.finish_with_error(str(exc))
            raise

    @contextmanager
    def start_trace(
        self,
        name: str,
        root_span_name: Optional[str] = None,
        context: Optional[TraceContext] = None,
    ) -> Generator[Tuple[Trace, Span], None, None]:
        trace = self.new_trace(name=name, context=context)
        root_name = root_span_name or name
        with self.start_span(trace, root_name) as root_span:
            yield trace, root_span

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate(self) -> Dict[str, Any]:
        traces = self.all_traces()
        total_spans = sum(len(t.all_spans()) for t in traces)
        total_errors = sum(len(t.error_spans()) for t in traces)
        durations = [
            s.duration_ms
            for t in traces
            for s in t.finished_spans()
            if s.duration_ms is not None
        ]
        return {
            "service": self.service_name,
            "trace_count": len(traces),
            "total_spans": total_spans,
            "total_errors": total_errors,
            "avg_span_duration_ms": (
                sum(durations) / len(durations) if durations else None
            ),
            "p99_span_duration_ms": (
                sorted(durations)[int(len(durations) * 0.99)] if durations else None
            ),
        }

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def make_context(self, trace: Trace, span: Span) -> TraceContext:
        return TraceContext(
            trace_id=trace.trace_id,
            parent_span_id=span.span_id,
        )

    def inject_headers(self, trace: Trace, span: Span) -> Dict[str, str]:
        return self.make_context(trace, span).to_headers()

    def extract_context(self, headers: Dict[str, str]) -> TraceContext:
        return TraceContext.from_headers(headers)
