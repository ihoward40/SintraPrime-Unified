"""
langgraph_engine.py
===================
LangGraph-compatible stateful workflow engine for SintraPrime-Unified.

Provides StateGraph, Node, Edge, ConditionalEdge classes with checkpointing,
async execution, branching logic, loop detection, and built-in legal workflow nodes.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GraphStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


MAX_CYCLE_LIMIT = 50  # Default maximum times any node may execute per run


# ---------------------------------------------------------------------------
# State Container
# ---------------------------------------------------------------------------

class GraphState(dict):
    """
    A typed dict-like container for graph state.
    Tracks changes and supports merge semantics.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._history: List[Dict[str, Any]] = []

    def update_state(self, updates: Dict[str, Any]) -> "GraphState":
        """Apply updates and record snapshot."""
        snapshot = copy.deepcopy(dict(self))
        self._history.append(snapshot)
        self.update(updates)
        return self

    def rollback(self) -> bool:
        """Restore previous state snapshot."""
        if not self._history:
            return False
        prev = self._history.pop()
        self.clear()
        self.update(prev)
        return True

    def snapshot(self) -> Dict[str, Any]:
        """Return a deep copy of current state."""
        return copy.deepcopy(dict(self))

    def history_length(self) -> int:
        return len(self._history)


# ---------------------------------------------------------------------------
# Checkpoint / Persistence
# ---------------------------------------------------------------------------

@dataclass
class Checkpoint:
    """Serializable snapshot of graph execution state."""
    graph_id: str
    run_id: str
    node_name: str
    state: Dict[str, Any]
    visited_counts: Dict[str, int]
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "run_id": self.run_id,
            "node_name": self.node_name,
            "state": self.state,
            "visited_counts": self.visited_counts,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(
            graph_id=data["graph_id"],
            run_id=data["run_id"],
            node_name=data["node_name"],
            state=data["state"],
            visited_counts=data["visited_counts"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )


class InMemoryCheckpointer:
    """In-memory checkpoint store."""

    def __init__(self) -> None:
        self._store: Dict[str, List[Checkpoint]] = defaultdict(list)

    def save(self, checkpoint: Checkpoint) -> None:
        key = f"{checkpoint.graph_id}:{checkpoint.run_id}"
        self._store[key].append(checkpoint)

    def load_latest(self, graph_id: str, run_id: str) -> Optional[Checkpoint]:
        key = f"{graph_id}:{run_id}"
        checkpoints = self._store.get(key, [])
        return checkpoints[-1] if checkpoints else None

    def load_all(self, graph_id: str, run_id: str) -> List[Checkpoint]:
        key = f"{graph_id}:{run_id}"
        return list(self._store.get(key, []))

    def list_runs(self, graph_id: str) -> List[str]:
        runs = []
        for key in self._store:
            g, r = key.split(":", 1)
            if g == graph_id:
                runs.append(r)
        return runs


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

NodeFunc = Callable[[GraphState], Any]
AsyncNodeFunc = Callable[[GraphState], Any]


@dataclass
class Node:
    """A single step in the workflow graph."""
    name: str
    func: Callable
    is_async: bool = False
    retry_limit: int = 0
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """Execute node function, handling sync/async and retries."""
        last_exc: Optional[Exception] = None
        for attempt in range(max(1, self.retry_limit + 1)):
            try:
                if self.is_async:
                    if self.timeout:
                        result = await asyncio.wait_for(self.func(state), timeout=self.timeout)
                    else:
                        result = await self.func(state)
                else:
                    if self.timeout:
                        loop = asyncio.get_event_loop()
                        result = await asyncio.wait_for(
                            loop.run_in_executor(None, self.func, state),
                            timeout=self.timeout,
                        )
                    else:
                        result = self.func(state)
                if result is None:
                    return {}
                if isinstance(result, dict):
                    return result
                return {"result": result}
            except Exception as exc:
                last_exc = exc
                if attempt < self.retry_limit:
                    wait = 2 ** attempt
                    logger.warning("Node %s attempt %d failed, retrying in %ds: %s", self.name, attempt + 1, wait, exc)
                    await asyncio.sleep(wait)
        raise RuntimeError(f"Node {self.name} failed after {self.retry_limit + 1} attempts") from last_exc


# ---------------------------------------------------------------------------
# Edge and Conditional Edge
# ---------------------------------------------------------------------------

@dataclass
class Edge:
    """Directed edge between two nodes."""
    source: str
    target: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConditionalEdge:
    """Edge with routing logic based on state."""
    source: str
    condition_func: Callable[[GraphState], str]
    target_map: Dict[str, str]  # condition return value -> target node name
    default_target: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def resolve(self, state: GraphState) -> Optional[str]:
        result = self.condition_func(state)
        target = self.target_map.get(result, self.default_target)
        return target


# ---------------------------------------------------------------------------
# Built-in Legal Workflow Nodes
# ---------------------------------------------------------------------------

async def _intake_node(state: GraphState) -> Dict[str, Any]:
    """Intake: gather and validate case information."""
    logger.info("Legal Intake: processing case %s", state.get("case_id", "unknown"))
    return {
        "stage": "intake_complete",
        "intake_timestamp": time.time(),
        "validated": True,
    }


async def _research_node(state: GraphState) -> Dict[str, Any]:
    """Research: identify relevant law and precedents."""
    logger.info("Legal Research: researching case %s", state.get("case_id", "unknown"))
    practice_area = state.get("practice_area", "general")
    return {
        "stage": "research_complete",
        "practice_area": practice_area,
        "research_timestamp": time.time(),
        "precedents_found": [],
    }


async def _draft_node(state: GraphState) -> Dict[str, Any]:
    """Draft: prepare legal documents."""
    logger.info("Legal Draft: drafting for case %s", state.get("case_id", "unknown"))
    return {
        "stage": "draft_complete",
        "draft_timestamp": time.time(),
        "document_ready": True,
    }


async def _review_node(state: GraphState) -> Dict[str, Any]:
    """Review: attorney review of drafts."""
    logger.info("Legal Review: reviewing case %s", state.get("case_id", "unknown"))
    return {
        "stage": "review_complete",
        "review_timestamp": time.time(),
        "approved": True,
    }


async def _file_node(state: GraphState) -> Dict[str, Any]:
    """File: submit documents to court or registry."""
    logger.info("Legal File: filing case %s", state.get("case_id", "unknown"))
    return {
        "stage": "filed",
        "file_timestamp": time.time(),
        "filing_reference": f"REF-{uuid.uuid4().hex[:8].upper()}",
    }


async def _trust_branch_node(state: GraphState) -> Dict[str, Any]:
    """Trust Law branch: specialized trust document handling."""
    logger.info("Trust Branch: handling trust law case %s", state.get("case_id", "unknown"))
    return {
        "stage": "trust_branch_complete",
        "trust_type": state.get("trust_type", "revocable"),
        "trust_timestamp": time.time(),
    }


async def _general_legal_node(state: GraphState) -> Dict[str, Any]:
    """General Legal branch for non-trust matters."""
    logger.info("General Legal: handling case %s", state.get("case_id", "unknown"))
    return {
        "stage": "general_legal_complete",
        "general_timestamp": time.time(),
    }


def _route_by_practice_area(state: GraphState) -> str:
    """Conditional routing: trust law vs general legal."""
    practice_area = state.get("practice_area", "general")
    if practice_area in ("trust", "estate", "probate"):
        return "trust"
    return "general"


BUILTIN_NODES: Dict[str, Node] = {
    "intake": Node("intake", _intake_node, is_async=True),
    "research": Node("research", _research_node, is_async=True),
    "draft": Node("draft", _draft_node, is_async=True),
    "review": Node("review", _review_node, is_async=True),
    "file": Node("file", _file_node, is_async=True),
    "trust_branch": Node("trust_branch", _trust_branch_node, is_async=True),
    "general_legal": Node("general_legal", _general_legal_node, is_async=True),
}


# ---------------------------------------------------------------------------
# Execution Result
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    run_id: str
    graph_id: str
    status: GraphStatus
    final_state: Dict[str, Any]
    visited_nodes: List[str]
    error: Optional[str] = None
    duration_seconds: float = 0.0
    checkpoints_saved: int = 0


# ---------------------------------------------------------------------------
# StateGraph
# ---------------------------------------------------------------------------

class StateGraph:
    """
    LangGraph-compatible directed graph for stateful workflow execution.

    Features:
    - Add nodes (sync or async callables)
    - Add edges and conditional edges
    - Set entry and terminal nodes
    - Checkpointing at each node boundary
    - Loop / cycle detection with configurable limit
    - Async execution
    """

    END = "__end__"
    START = "__start__"

    def __init__(
        self,
        graph_id: Optional[str] = None,
        checkpointer: Optional[InMemoryCheckpointer] = None,
        max_cycles: int = MAX_CYCLE_LIMIT,
    ) -> None:
        self.graph_id = graph_id or f"graph_{uuid.uuid4().hex[:8]}"
        self.checkpointer = checkpointer or InMemoryCheckpointer()
        self.max_cycles = max_cycles

        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, List[Edge]] = defaultdict(list)
        self._conditional_edges: Dict[str, ConditionalEdge] = {}
        self._entry_point: Optional[str] = None
        self._terminal_nodes: Set[str] = set()

    # --- Builder API -------------------------------------------------------

    def add_node(
        self,
        name: str,
        func: Callable,
        is_async: bool = False,
        retry_limit: int = 0,
        timeout: Optional[float] = None,
        **metadata: Any,
    ) -> "StateGraph":
        """Register a node with the graph."""
        if name in BUILTIN_NODES and func is None:
            self._nodes[name] = BUILTIN_NODES[name]
        else:
            is_async_func = asyncio.iscoroutinefunction(func)
            self._nodes[name] = Node(
                name=name,
                func=func,
                is_async=is_async or is_async_func,
                retry_limit=retry_limit,
                timeout=timeout,
                metadata=metadata,
            )
        return self

    def add_builtin_node(self, name: str) -> "StateGraph":
        """Add a predefined legal workflow node."""
        if name not in BUILTIN_NODES:
            raise ValueError(f"Unknown builtin node: {name}. Available: {list(BUILTIN_NODES)}")
        self._nodes[name] = BUILTIN_NODES[name]
        return self

    def add_edge(self, source: str, target: str, **metadata: Any) -> "StateGraph":
        """Add a directed edge from source to target."""
        self._edges[source].append(Edge(source=source, target=target, metadata=metadata))
        return self

    def add_conditional_edges(
        self,
        source: str,
        condition_func: Callable[[GraphState], str],
        target_map: Dict[str, str],
        default_target: Optional[str] = None,
    ) -> "StateGraph":
        """Add a conditional edge that routes based on state."""
        self._conditional_edges[source] = ConditionalEdge(
            source=source,
            condition_func=condition_func,
            target_map=target_map,
            default_target=default_target,
        )
        return self

    def set_entry_point(self, node_name: str) -> "StateGraph":
        self._entry_point = node_name
        return self

    def set_finish_point(self, node_name: str) -> "StateGraph":
        self._terminal_nodes.add(node_name)
        return self

    def add_terminal_nodes(self, *names: str) -> "StateGraph":
        self._terminal_nodes.update(names)
        return self

    # --- Legal Workflow Factory --------------------------------------------

    @classmethod
    def legal_workflow(cls, checkpointer: Optional[InMemoryCheckpointer] = None) -> "StateGraph":
        """Build the standard SintraPrime legal workflow graph."""
        g = cls(graph_id="legal_workflow", checkpointer=checkpointer)
        for name in ("intake", "research", "draft", "review", "file", "trust_branch", "general_legal"):
            g.add_builtin_node(name)
        g.set_entry_point("intake")
        g.add_edge("intake", "research")
        g.add_conditional_edges(
            "research",
            _route_by_practice_area,
            {"trust": "trust_branch", "general": "general_legal"},
            default_target="general_legal",
        )
        g.add_edge("trust_branch", "draft")
        g.add_edge("general_legal", "draft")
        g.add_edge("draft", "review")
        g.add_edge("review", "file")
        g.add_terminal_nodes("file")
        return g

    # --- Validation --------------------------------------------------------

    def validate(self) -> List[str]:
        """Validate graph structure, return list of issues."""
        issues = []
        if not self._entry_point:
            issues.append("No entry point set.")
        if self._entry_point and self._entry_point not in self._nodes:
            issues.append(f"Entry point '{self._entry_point}' is not a registered node.")
        all_targets: Set[str] = set()
        for edges in self._edges.values():
            for e in edges:
                all_targets.add(e.target)
        for ce in self._conditional_edges.values():
            all_targets.update(ce.target_map.values())
            if ce.default_target:
                all_targets.add(ce.default_target)
        for t in all_targets:
            if t != self.END and t not in self._nodes:
                issues.append(f"Target node '{t}' is referenced but not registered.")
        return issues

    # --- Cycle detection ---------------------------------------------------

    def _detect_cycles(self) -> List[List[str]]:
        """Return lists of nodes forming cycles (DFS-based)."""
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        path: List[str] = []
        path_set: Set[str] = set()

        def dfs(node: str) -> None:
            if node in path_set:
                idx = path.index(node)
                cycles.append(path[idx:])
                return
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            path_set.add(node)
            nexts = self._next_nodes_static(node)
            for nxt in nexts:
                if nxt != self.END:
                    dfs(nxt)
            path.pop()
            path_set.discard(node)

        for node in self._nodes:
            dfs(node)
        return cycles

    def _next_nodes_static(self, node: str) -> List[str]:
        """Get next node names without state (for static analysis)."""
        targets: List[str] = []
        if node in self._conditional_edges:
            ce = self._conditional_edges[node]
            targets.extend(ce.target_map.values())
            if ce.default_target:
                targets.append(ce.default_target)
        for e in self._edges.get(node, []):
            targets.append(e.target)
        return targets

    # --- Execution ---------------------------------------------------------

    async def _resolve_next(self, current_node: str, state: GraphState) -> Optional[str]:
        """Determine the next node after current_node based on state."""
        if current_node in self._conditional_edges:
            ce = self._conditional_edges[current_node]
            target = ce.resolve(state)
            if target:
                return target
        edges = self._edges.get(current_node, [])
        if edges:
            return edges[0].target  # Take first edge (deterministic)
        return None

    async def run(
        self,
        initial_state: Dict[str, Any],
        run_id: Optional[str] = None,
        resume_from_checkpoint: bool = False,
    ) -> ExecutionResult:
        """Execute the graph from entry point with the given initial state."""
        run_id = run_id or uuid.uuid4().hex
        start_time = time.time()

        issues = self.validate()
        if issues:
            return ExecutionResult(
                run_id=run_id,
                graph_id=self.graph_id,
                status=GraphStatus.FAILED,
                final_state=initial_state,
                visited_nodes=[],
                error=f"Graph validation failed: {issues}",
            )

        state = GraphState(initial_state)
        current_node = self._entry_point
        visited_counts: Dict[str, int] = defaultdict(int)
        visited_order: List[str] = []
        checkpoints_saved = 0

        # Resume from checkpoint if requested
        if resume_from_checkpoint:
            ckpt = self.checkpointer.load_latest(self.graph_id, run_id)
            if ckpt:
                state = GraphState(ckpt.state)
                current_node = ckpt.node_name
                visited_counts = defaultdict(int, ckpt.visited_counts)
                logger.info("Resuming run %s from checkpoint at node %s", run_id, current_node)

        try:
            while current_node and current_node != self.END:
                if current_node not in self._nodes:
                    raise ValueError(f"Node '{current_node}' is not registered in the graph.")

                visited_counts[current_node] += 1
                if visited_counts[current_node] > self.max_cycles:
                    raise RuntimeError(
                        f"Cycle limit exceeded for node '{current_node}' "
                        f"(limit={self.max_cycles})"
                    )

                visited_order.append(current_node)
                node = self._nodes[current_node]

                logger.info("[%s] Executing node: %s", run_id, current_node)
                updates = await node.execute(state)
                state.update_state(updates)

                # Save checkpoint
                ckpt = Checkpoint(
                    graph_id=self.graph_id,
                    run_id=run_id,
                    node_name=current_node,
                    state=state.snapshot(),
                    visited_counts=dict(visited_counts),
                )
                self.checkpointer.save(ckpt)
                checkpoints_saved += 1

                if current_node in self._terminal_nodes:
                    logger.info("[%s] Reached terminal node: %s", run_id, current_node)
                    break

                next_node = await self._resolve_next(current_node, state)
                if next_node == self.END or next_node is None:
                    break
                current_node = next_node

        except Exception as exc:
            logger.exception("Graph run %s failed: %s", run_id, exc)
            return ExecutionResult(
                run_id=run_id,
                graph_id=self.graph_id,
                status=GraphStatus.FAILED,
                final_state=state.snapshot(),
                visited_nodes=visited_order,
                error=str(exc),
                duration_seconds=time.time() - start_time,
                checkpoints_saved=checkpoints_saved,
            )

        return ExecutionResult(
            run_id=run_id,
            graph_id=self.graph_id,
            status=GraphStatus.COMPLETED,
            final_state=state.snapshot(),
            visited_nodes=visited_order,
            duration_seconds=time.time() - start_time,
            checkpoints_saved=checkpoints_saved,
        )

    def compile(self) -> "CompiledGraph":
        """Compile the graph for repeated execution."""
        return CompiledGraph(self)


# ---------------------------------------------------------------------------
# CompiledGraph (convenience wrapper)
# ---------------------------------------------------------------------------

class CompiledGraph:
    """A compiled, validated, ready-to-run StateGraph."""

    def __init__(self, graph: StateGraph) -> None:
        issues = graph.validate()
        if issues:
            raise ValueError(f"Graph compilation failed: {issues}")
        self._graph = graph
        self._cycles = graph._detect_cycles()
        if self._cycles:
            logger.warning("Graph contains cycles (intentional loops): %s", self._cycles)

    async def invoke(
        self,
        state: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """LangGraph-compatible invoke: run graph, return final state."""
        run_id = (config or {}).get("run_id") or uuid.uuid4().hex
        result = await self._graph.run(state, run_id=run_id)
        if result.status == GraphStatus.FAILED:
            raise RuntimeError(result.error)
        return result.final_state

    def get_graph(self) -> StateGraph:
        return self._graph


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def create_legal_graph(checkpointer: Optional[InMemoryCheckpointer] = None) -> CompiledGraph:
    """Factory: build and compile the standard SintraPrime legal workflow."""
    return StateGraph.legal_workflow(checkpointer).compile()
