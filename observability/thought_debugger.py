"""
Thought Debugger for SintraPrime-Unified
Captures, replays, and visualizes agent reasoning chains.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Iterator


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class ThoughtStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ThoughtStep:
    """A single reasoning step captured from an agent."""
    step_id: str
    agent_name: str
    thought: str
    action: str
    observation: str
    timestamp: float
    parent_step_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ThoughtStatus = ThoughtStatus.COMPLETE
    duration_ms: float = 0.0
    tags: List[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        agent_name: str,
        thought: str,
        action: str,
        observation: str,
        parent_step_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> "ThoughtStep":
        return cls(
            step_id=str(uuid.uuid4()),
            agent_name=agent_name,
            thought=thought,
            action=action,
            observation=observation,
            timestamp=time.time(),
            parent_step_id=parent_step_id,
            metadata=metadata or {},
            tags=tags or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["timestamp_iso"] = datetime.fromtimestamp(
            self.timestamp, tz=timezone.utc
        ).isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ThoughtStep":
        d = dict(d)
        d["status"] = ThoughtStatus(d.get("status", "complete"))
        d.pop("timestamp_iso", None)
        return cls(**d)


# ---------------------------------------------------------------------------
# ThoughtTrace – stores full chain for a session
# ---------------------------------------------------------------------------

class ThoughtTrace:
    """Stores and manages the complete chain of thoughts for a session."""

    def __init__(self, session_id: Optional[str] = None, session_name: str = "") -> None:
        self.session_id: str = session_id or str(uuid.uuid4())
        self.session_name: str = session_name
        self.created_at: float = time.time()
        self._steps: List[ThoughtStep] = []
        self._step_index: Dict[str, ThoughtStep] = {}
        self._parliament_hooks: List[Callable[[ThoughtStep], None]] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_step(self, step: ThoughtStep) -> None:
        """Append a reasoning step to the trace."""
        self._steps.append(step)
        self._step_index[step.step_id] = step
        self._fire_hooks(step)

    def record(
        self,
        agent_name: str,
        thought: str,
        action: str,
        observation: str,
        parent_step_id: Optional[str] = None,
        **kwargs: Any,
    ) -> ThoughtStep:
        """Convenience method: create and add a step, return it."""
        step = ThoughtStep.create(
            agent_name=agent_name,
            thought=thought,
            action=action,
            observation=observation,
            parent_step_id=parent_step_id,
            **kwargs,
        )
        self.add_step(step)
        return step

    # ------------------------------------------------------------------
    # Parliament hooks
    # ------------------------------------------------------------------

    def register_parliament_hook(self, hook: Callable[[ThoughtStep], None]) -> None:
        """Register a callback invoked whenever a new step is recorded."""
        self._parliament_hooks.append(hook)

    def _fire_hooks(self, step: ThoughtStep) -> None:
        for hook in self._parliament_hooks:
            try:
                hook(step)
            except Exception:
                pass  # hooks must not crash the trace

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_step(self, step_id: str) -> Optional[ThoughtStep]:
        return self._step_index.get(step_id)

    def steps_for_agent(self, agent_name: str) -> List[ThoughtStep]:
        return [s for s in self._steps if s.agent_name == agent_name]

    def children_of(self, step_id: str) -> List[ThoughtStep]:
        return [s for s in self._steps if s.parent_step_id == step_id]

    def root_steps(self) -> List[ThoughtStep]:
        return [s for s in self._steps if s.parent_step_id is None]

    def all_steps(self) -> List[ThoughtStep]:
        return list(self._steps)

    def __len__(self) -> int:
        return len(self._steps)

    # ------------------------------------------------------------------
    # ASCII tree renderer
    # ------------------------------------------------------------------

    def render_tree(self, max_width: int = 120) -> str:
        """Render the reasoning chain as an ASCII tree."""
        lines: List[str] = [
            f"ThoughtTrace [{self.session_name or self.session_id}]",
            f"  Session : {self.session_id}",
            f"  Created : {datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()}",
            f"  Steps   : {len(self._steps)}",
            "",
        ]

        def _render_node(step: ThoughtStep, prefix: str, is_last: bool) -> None:
            connector = "└── " if is_last else "├── "
            agent_tag = f"[{step.agent_name}]"
            thought_short = step.thought[:60] + "…" if len(step.thought) > 60 else step.thought
            lines.append(f"{prefix}{connector}{agent_tag} {thought_short}")

            child_prefix = prefix + ("    " if is_last else "│   ")
            action_short = step.action[:55] + "…" if len(step.action) > 55 else step.action
            obs_short = step.observation[:55] + "…" if len(step.observation) > 55 else step.observation
            lines.append(f"{child_prefix}  ▶ action: {action_short}")
            lines.append(f"{child_prefix}  ◀ obs   : {obs_short}")
            ts = datetime.fromtimestamp(step.timestamp, tz=timezone.utc).strftime("%H:%M:%S")
            lines.append(f"{child_prefix}  ⏱ {ts}  id={step.step_id[:8]}")

            children = self.children_of(step.step_id)
            for i, child in enumerate(children):
                _render_node(child, child_prefix, i == len(children) - 1)

        roots = self.root_steps()
        for i, root in enumerate(roots):
            _render_node(root, "", i == len(roots) - 1)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    def replay(self, delay_s: float = 0.0) -> Iterator[ThoughtStep]:
        """Yield steps in chronological order, optionally with delay."""
        for step in sorted(self._steps, key=lambda s: s.timestamp):
            if delay_s > 0:
                time.sleep(delay_s)
            yield step

    def replay_from(self, step_id: str, delay_s: float = 0.0) -> Iterator[ThoughtStep]:
        """Replay from a specific step onward."""
        start_ts = self._step_index[step_id].timestamp if step_id in self._step_index else 0.0
        for step in sorted(self._steps, key=lambda s: s.timestamp):
            if step.timestamp >= start_ts:
                if delay_s > 0:
                    time.sleep(delay_s)
                yield step

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "created_at": self.created_at,
            "created_at_iso": datetime.fromtimestamp(
                self.created_at, tz=timezone.utc
            ).isoformat(),
            "step_count": len(self._steps),
            "steps": [s.to_dict() for s in self._steps],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        lines: List[str] = [
            f"# Thought Trace: {self.session_name or self.session_id}",
            "",
            f"**Session ID:** `{self.session_id}`",
            f"**Created:** {datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()}",
            f"**Total Steps:** {len(self._steps)}",
            "",
            "---",
            "",
        ]
        for i, step in enumerate(self._steps, 1):
            ts = datetime.fromtimestamp(step.timestamp, tz=timezone.utc).isoformat()
            lines += [
                f"## Step {i}: `{step.step_id[:8]}` — {step.agent_name}",
                "",
                f"**Timestamp:** {ts}",
                f"**Status:** {step.status.value}",
                f"**Tags:** {', '.join(step.tags) if step.tags else '—'}",
                "",
                f"### 💭 Thought",
                f"> {step.thought}",
                "",
                f"### ▶ Action",
                f"```\n{step.action}\n```",
                "",
                f"### ◀ Observation",
                f"```\n{step.observation}\n```",
                "",
                "---",
                "",
            ]
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ThoughtTrace":
        trace = cls(session_id=d["session_id"], session_name=d.get("session_name", ""))
        trace.created_at = d["created_at"]
        for sd in d.get("steps", []):
            trace.add_step(ThoughtStep.from_dict(sd))
        return trace

    @classmethod
    def from_json(cls, json_str: str) -> "ThoughtTrace":
        return cls.from_dict(json.loads(json_str))


# ---------------------------------------------------------------------------
# ThoughtDebugger – context manager + helpers
# ---------------------------------------------------------------------------

class ThoughtDebugger:
    """
    High-level interface for debugging agent reasoning.

    Usage:
        debugger = ThoughtDebugger()
        with debugger.session("my-session") as trace:
            step = trace.record("AgentA", "I should search", "search(q)", "results...")
    """

    def __init__(self) -> None:
        self._active_traces: Dict[str, ThoughtTrace] = {}

    def session(self, name: str = "") -> "ThoughtDebugger._SessionCtx":
        return self._SessionCtx(self, name)

    def create_trace(self, name: str = "") -> ThoughtTrace:
        trace = ThoughtTrace(session_name=name)
        self._active_traces[trace.session_id] = trace
        return trace

    def get_trace(self, session_id: str) -> Optional[ThoughtTrace]:
        return self._active_traces.get(session_id)

    def all_traces(self) -> List[ThoughtTrace]:
        return list(self._active_traces.values())

    def remove_trace(self, session_id: str) -> None:
        self._active_traces.pop(session_id, None)

    class _SessionCtx:
        def __init__(self, debugger: "ThoughtDebugger", name: str) -> None:
            self._debugger = debugger
            self._name = name
            self._trace: Optional[ThoughtTrace] = None

        def __enter__(self) -> ThoughtTrace:
            self._trace = self._debugger.create_trace(self._name)
            return self._trace

        def __exit__(self, *args: Any) -> None:
            pass  # trace persists; caller decides when to remove


# ---------------------------------------------------------------------------
# Parliament Integration Hooks
# ---------------------------------------------------------------------------

class ParliamentHook:
    """Ready-made hook that broadcasts steps to SintraPrime's parliament system."""

    def __init__(self, parliament_endpoint: Optional[str] = None) -> None:
        self.parliament_endpoint = parliament_endpoint
        self.received: List[ThoughtStep] = []

    def __call__(self, step: ThoughtStep) -> None:
        self.received.append(step)
        # In production, POST to parliament_endpoint here.

    def get_agent_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for step in self.received:
            summary[step.agent_name] = summary.get(step.agent_name, 0) + 1
        return summary
