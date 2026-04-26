"""
Observability Dashboard API for SintraPrime-Unified
FastAPI router exposing traces, thoughts, snapshots, rewind, and metrics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, HTTPException
    from fastapi.responses import PlainTextResponse
    from pydantic import BaseModel
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    # Stub classes so the module can be imported without FastAPI installed
    class APIRouter:  # type: ignore
        def get(self, *a, **kw):
            def decorator(fn):
                return fn
            return decorator
        def post(self, *a, **kw):
            def decorator(fn):
                return fn
            return decorator

    class HTTPException(Exception):  # type: ignore
        def __init__(self, status_code: int, detail: str = ""):
            self.status_code = status_code
            self.detail = detail

    class PlainTextResponse:  # type: ignore
        pass

    class BaseModel:  # type: ignore
        pass

from .thought_debugger import ThoughtDebugger, ThoughtTrace
from .time_travel import TimeTravelDebugger, Snapshot
from .tracer import Tracer, Trace
from .metrics import SintraMetrics


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class RewindRequest(BaseModel):
    snapshot_id: str


class CheckpointRequest(BaseModel):
    session_id: str
    agent_name: str
    state: Dict[str, Any]
    label: Optional[str] = ""
    tags: Optional[List[str]] = None


class RecordThoughtRequest(BaseModel):
    session_id: str
    agent_name: str
    thought: str
    action: str
    observation: str
    parent_step_id: Optional[str] = None


class DiffRequest(BaseModel):
    snapshot_id_a: str
    snapshot_id_b: str


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------

def create_observability_router(
    thought_debugger: Optional[ThoughtDebugger] = None,
    time_travel: Optional[TimeTravelDebugger] = None,
    tracer: Optional[Tracer] = None,
    metrics: Optional[SintraMetrics] = None,
) -> "APIRouter":
    """
    Build and return the observability FastAPI router.

    The caller is responsible for wiring the shared component instances.
    """
    thought_debugger = thought_debugger or ThoughtDebugger()
    time_travel = time_travel or TimeTravelDebugger()
    tracer = tracer or Tracer()
    metrics = metrics or SintraMetrics()

    router = APIRouter(prefix="/observability", tags=["observability"])

    # ------------------------------------------------------------------
    # Traces
    # ------------------------------------------------------------------

    @router.get("/traces")
    async def list_traces() -> Dict[str, Any]:
        """List all traces with summaries."""
        traces = tracer.all_traces()
        return {
            "count": len(traces),
            "traces": [t.summary() for t in traces],
            "aggregation": tracer.aggregate(),
        }

    @router.get("/traces/{trace_id}")
    async def get_trace(trace_id: str) -> Dict[str, Any]:
        """Return full trace tree for a given trace_id."""
        trace = tracer.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
        return trace.to_dict()

    @router.get("/traces/{trace_id}/flame")
    async def get_flame_graph(trace_id: str) -> Dict[str, Any]:
        """Return Chrome DevTools compatible flame graph JSON."""
        trace = tracer.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
        return trace.to_flame_graph()

    # ------------------------------------------------------------------
    # Thoughts
    # ------------------------------------------------------------------

    @router.get("/thoughts")
    async def list_thought_sessions() -> Dict[str, Any]:
        """List all active thought tracing sessions."""
        traces = thought_debugger.all_traces()
        return {
            "count": len(traces),
            "sessions": [
                {
                    "session_id": t.session_id,
                    "session_name": t.session_name,
                    "step_count": len(t),
                }
                for t in traces
            ],
        }

    @router.get("/thoughts/{session_id}")
    async def get_thought_chain(session_id: str, fmt: str = "json") -> Any:
        """Return the full thought chain for a session."""
        trace = thought_debugger.get_trace(session_id)
        if trace is None:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        if fmt == "markdown":
            return PlainTextResponse(trace.to_markdown(), media_type="text/markdown")
        if fmt == "tree":
            return PlainTextResponse(trace.render_tree(), media_type="text/plain")
        return trace.to_dict()

    @router.post("/thoughts/record")
    async def record_thought(req: RecordThoughtRequest) -> Dict[str, Any]:
        """Record a thought step in an existing or new session."""
        trace = thought_debugger.get_trace(req.session_id)
        if trace is None:
            trace = ThoughtTrace(session_id=req.session_id)
            thought_debugger._active_traces[req.session_id] = trace
        step = trace.record(
            agent_name=req.agent_name,
            thought=req.thought,
            action=req.action,
            observation=req.observation,
            parent_step_id=req.parent_step_id,
        )
        metrics.thought_steps_total.inc()
        return {"step_id": step.step_id, "session_id": req.session_id}

    # ------------------------------------------------------------------
    # Snapshots / Time-Travel
    # ------------------------------------------------------------------

    @router.get("/snapshots")
    async def list_snapshots(limit: int = 100) -> Dict[str, Any]:
        """List all available time-travel snapshots."""
        snaps = time_travel.list_all_snapshots(limit=limit)
        return {
            "count": len(snaps),
            "snapshots": [
                {
                    "snapshot_id": s.snapshot_id,
                    "session_id": s.session_id,
                    "agent_name": s.agent_name,
                    "label": s.label,
                    "branch_name": s.branch_name,
                    "timestamp": s.timestamp,
                    "tags": s.tags,
                }
                for s in snaps
            ],
        }

    @router.post("/debug/checkpoint")
    async def create_checkpoint(req: CheckpointRequest) -> Dict[str, Any]:
        """Create a state snapshot at the current decision point."""
        snap = time_travel.checkpoint(
            session_id=req.session_id,
            agent_name=req.agent_name,
            state=req.state,
            label=req.label or "",
            tags=req.tags,
        )
        metrics.snapshots_total.inc()
        return {"snapshot_id": snap.snapshot_id, "label": snap.label}

    @router.post("/debug/rewind")
    async def rewind_to_snapshot(req: RewindRequest) -> Dict[str, Any]:
        """Rewind agent state to a specific snapshot."""
        try:
            state = time_travel.rewind(req.snapshot_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return {"snapshot_id": req.snapshot_id, "state": state}

    @router.post("/debug/diff")
    async def diff_snapshots_endpoint(req: DiffRequest) -> Dict[str, Any]:
        """Diff two snapshots to see what changed."""
        try:
            result = time_travel.diff(req.snapshot_id_a, req.snapshot_id_b)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return result

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @router.get("/metrics")
    async def get_metrics() -> Any:
        """Return Prometheus-compatible metrics text."""
        text = metrics.prometheus_output()
        if _FASTAPI_AVAILABLE:
            return PlainTextResponse(text, media_type="text/plain; version=0.0.4")
        return text

    @router.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok", "service": "sintra-prime-observability"}

    return router


# ---------------------------------------------------------------------------
# Standalone app (for development / testing)
# ---------------------------------------------------------------------------

def create_app():
    """Create a standalone FastAPI application with observability routes."""
    if not _FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI is required: pip install fastapi uvicorn")

    from fastapi import FastAPI  # noqa: PLC0415

    app = FastAPI(
        title="SintraPrime Observability Dashboard",
        version="1.0.0",
        description="Observability layer: traces, thoughts, snapshots, metrics",
    )

    router = create_observability_router()
    app.include_router(router)
    return app
