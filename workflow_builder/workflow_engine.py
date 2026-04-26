"""
SintraPrime-Unified Workflow Engine
Provides WorkflowNode, WorkflowEdge, WorkflowGraph, WorkflowSerializer,
and 20+ built-in legal workflow templates.
"""

from __future__ import annotations

import json
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    START = "START"
    END = "END"
    ACTION = "ACTION"
    DECISION = "DECISION"
    PARALLEL = "PARALLEL"
    WAIT = "WAIT"
    AGENT_CALL = "AGENT_CALL"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class EdgeCondition(str, Enum):
    ALWAYS = "always"
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"
    ON_YES = "on_yes"
    ON_NO = "on_no"
    ON_COMPLETE = "on_complete"
    CUSTOM = "custom"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Core Data Classes
# ---------------------------------------------------------------------------

@dataclass
class WorkflowNode:
    """Represents a single node in a workflow graph."""
    id: str
    node_type: NodeType
    label: str
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    metadata: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    is_required: bool = True

    @classmethod
    def create(
        cls,
        node_type: NodeType,
        label: str,
        description: str = "",
        config: Optional[Dict[str, Any]] = None,
        position: Optional[Dict[str, float]] = None,
    ) -> "WorkflowNode":
        return cls(
            id=str(uuid.uuid4()),
            node_type=node_type,
            label=label,
            description=description,
            config=config or {},
            position=position or {"x": 0.0, "y": 0.0},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "label": self.label,
            "description": self.description,
            "config": self.config,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "position": self.position,
            "metadata": self.metadata,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "is_required": self.is_required,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowNode":
        return cls(
            id=data["id"],
            node_type=NodeType(data["node_type"]),
            label=data["label"],
            description=data.get("description", ""),
            config=data.get("config", {}),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            position=data.get("position", {"x": 0.0, "y": 0.0}),
            metadata=data.get("metadata", {}),
            timeout_seconds=data.get("timeout_seconds"),
            retry_count=data.get("retry_count", 0),
            is_required=data.get("is_required", True),
        )


@dataclass
class WorkflowEdge:
    """Represents a directed edge between two workflow nodes."""
    id: str
    source_id: str
    target_id: str
    condition: EdgeCondition = EdgeCondition.ALWAYS
    condition_expression: str = ""
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source_id: str,
        target_id: str,
        condition: EdgeCondition = EdgeCondition.ALWAYS,
        label: str = "",
    ) -> "WorkflowEdge":
        return cls(
            id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            condition=condition,
            label=label,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "condition": self.condition.value,
            "condition_expression": self.condition_expression,
            "label": self.label,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowEdge":
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            condition=EdgeCondition(data.get("condition", "always")),
            condition_expression=data.get("condition_expression", ""),
            label=data.get("label", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class WorkflowExecutionState:
    """Tracks the state of a workflow execution."""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.DRAFT
    current_node_id: Optional[str] = None
    completed_nodes: List[str] = field(default_factory=list)
    failed_nodes: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    logs: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Workflow Graph
# ---------------------------------------------------------------------------

class WorkflowGraph:
    """
    Directed Acyclic Graph (DAG) representing a workflow.
    Supports add/remove of nodes and edges, cycle detection, and validation.
    """

    def __init__(self, workflow_id: str, name: str, description: str = ""):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: Dict[str, WorkflowEdge] = {}
        self.status = WorkflowStatus.DRAFT
        self.tags: List[str] = []
        self.version: str = "1.0.0"
        self.author: str = ""
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None

    # --- Node operations ---

    def add_node(self, node: WorkflowNode) -> None:
        """Add a node to the graph."""
        if node.id in self.nodes:
            raise ValueError(f"Node with id '{node.id}' already exists.")
        self.nodes[node.id] = node

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its connected edges."""
        if node_id not in self.nodes:
            raise KeyError(f"Node '{node_id}' not found.")
        del self.nodes[node_id]
        edges_to_remove = [
            eid for eid, e in self.edges.items()
            if e.source_id == node_id or e.target_id == node_id
        ]
        for eid in edges_to_remove:
            del self.edges[eid]

    def get_node(self, node_id: str) -> WorkflowNode:
        """Retrieve a node by ID."""
        if node_id not in self.nodes:
            raise KeyError(f"Node '{node_id}' not found.")
        return self.nodes[node_id]

    def update_node(self, node_id: str, updates: Dict[str, Any]) -> None:
        """Update node attributes."""
        node = self.get_node(node_id)
        for key, value in updates.items():
            if hasattr(node, key):
                setattr(node, key, value)

    # --- Edge operations ---

    def add_edge(self, edge: WorkflowEdge) -> None:
        """Add an edge, checking that both nodes exist."""
        if edge.source_id not in self.nodes:
            raise KeyError(f"Source node '{edge.source_id}' not found.")
        if edge.target_id not in self.nodes:
            raise KeyError(f"Target node '{edge.target_id}' not found.")
        if edge.id in self.edges:
            raise ValueError(f"Edge with id '{edge.id}' already exists.")
        self.edges[edge.id] = edge

    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge by ID."""
        if edge_id not in self.edges:
            raise KeyError(f"Edge '{edge_id}' not found.")
        del self.edges[edge_id]

    def get_edges_from(self, node_id: str) -> List[WorkflowEdge]:
        """Return all edges emanating from a node."""
        return [e for e in self.edges.values() if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> List[WorkflowEdge]:
        """Return all edges pointing to a node."""
        return [e for e in self.edges.values() if e.target_id == node_id]

    # --- Graph algorithms ---

    def get_start_nodes(self) -> List[WorkflowNode]:
        """Return nodes with NodeType.START or no incoming edges."""
        start_nodes = [n for n in self.nodes.values() if n.node_type == NodeType.START]
        if start_nodes:
            return start_nodes
        target_ids: Set[str] = {e.target_id for e in self.edges.values()}
        return [n for nid, n in self.nodes.items() if nid not in target_ids]

    def get_end_nodes(self) -> List[WorkflowNode]:
        """Return nodes with NodeType.END or no outgoing edges."""
        end_nodes = [n for n in self.nodes.values() if n.node_type == NodeType.END]
        if end_nodes:
            return end_nodes
        source_ids: Set[str] = {e.source_id for e in self.edges.values()}
        return [n for nid, n in self.nodes.items() if nid not in source_ids]

    def has_cycle(self) -> bool:
        """Detect cycles using DFS. Returns True if a cycle exists."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {nid: WHITE for nid in self.nodes}

        def dfs(node_id: str) -> bool:
            color[node_id] = GRAY
            for edge in self.get_edges_from(node_id):
                neighbor = edge.target_id
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    return True
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            color[node_id] = BLACK
            return False

        for nid in self.nodes:
            if color[nid] == WHITE:
                if dfs(nid):
                    return True
        return False

    def topological_sort(self) -> List[str]:
        """Return nodes in topological order. Raises if cycle detected."""
        if self.has_cycle():
            raise ValueError("Workflow graph contains a cycle — not a valid DAG.")
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        for edge in self.edges.values():
            in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        result: List[str] = []
        while queue:
            nid = queue.popleft()
            result.append(nid)
            for edge in self.get_edges_from(nid):
                in_degree[edge.target_id] -= 1
                if in_degree[edge.target_id] == 0:
                    queue.append(edge.target_id)
        return result

    def validate(self) -> List[str]:
        """
        Validate the workflow graph.
        Returns a list of validation error messages (empty = valid).
        """
        errors: List[str] = []

        if not self.nodes:
            errors.append("Workflow has no nodes.")
            return errors

        start_nodes = [n for n in self.nodes.values() if n.node_type == NodeType.START]
        if len(start_nodes) == 0:
            errors.append("Workflow must have at least one START node.")
        if len(start_nodes) > 1:
            errors.append("Workflow must have exactly one START node.")

        end_nodes = [n for n in self.nodes.values() if n.node_type == NodeType.END]
        if len(end_nodes) == 0:
            errors.append("Workflow must have at least one END node.")

        if self.has_cycle():
            errors.append("Workflow graph contains a cycle.")

        for nid, node in self.nodes.items():
            if node.node_type not in (NodeType.START, NodeType.END):
                incoming = self.get_edges_to(nid)
                if not incoming:
                    errors.append(f"Node '{node.label}' ({nid}) has no incoming edges.")
            if node.node_type not in (NodeType.END,):
                outgoing = self.get_edges_from(nid)
                if not outgoing:
                    errors.append(f"Node '{node.label}' ({nid}) has no outgoing edges.")

        return errors

    def get_statistics(self) -> Dict[str, Any]:
        """Return statistics about the workflow graph."""
        type_counts: Dict[str, int] = {}
        for node in self.nodes.values():
            type_counts[node.node_type.value] = type_counts.get(node.node_type.value, 0) + 1
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": type_counts,
            "has_cycle": self.has_cycle(),
            "validation_errors": self.validate(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "status": self.status.value,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowGraph":
        graph = cls(
            workflow_id=data["workflow_id"],
            name=data["name"],
            description=data.get("description", ""),
        )
        graph.version = data.get("version", "1.0.0")
        graph.author = data.get("author", "")
        graph.status = WorkflowStatus(data.get("status", "draft"))
        graph.tags = data.get("tags", [])
        graph.created_at = data.get("created_at")
        graph.updated_at = data.get("updated_at")
        for nd in data.get("nodes", []):
            graph.nodes[nd["id"]] = WorkflowNode.from_dict(nd)
        for ed in data.get("edges", []):
            graph.edges[ed["id"]] = WorkflowEdge.from_dict(ed)
        return graph


# ---------------------------------------------------------------------------
# Workflow Serializer
# ---------------------------------------------------------------------------

class WorkflowSerializer:
    """Save and load WorkflowGraph to/from JSON."""

    @staticmethod
    def to_json(graph: WorkflowGraph, indent: int = 2) -> str:
        return json.dumps(graph.to_dict(), indent=indent)

    @staticmethod
    def from_json(json_str: str) -> WorkflowGraph:
        data = json.loads(json_str)
        return WorkflowGraph.from_dict(data)

    @staticmethod
    def save_to_file(graph: WorkflowGraph, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(WorkflowSerializer.to_json(graph))

    @staticmethod
    def load_from_file(filepath: str) -> WorkflowGraph:
        with open(filepath, "r", encoding="utf-8") as fh:
            return WorkflowSerializer.from_json(fh.read())


# ---------------------------------------------------------------------------
# Built-in Legal Workflow Templates (20+)
# ---------------------------------------------------------------------------

class WorkflowTemplateRegistry:
    """Registry of built-in legal workflow templates."""

    _templates: Dict[str, "WorkflowGraph"] = {}

    @classmethod
    def register(cls, graph: WorkflowGraph) -> None:
        cls._templates[graph.workflow_id] = graph

    @classmethod
    def get(cls, template_id: str) -> Optional[WorkflowGraph]:
        return cls._templates.get(template_id)

    @classmethod
    def list_templates(cls) -> List[Dict[str, str]]:
        return [
            {
                "id": g.workflow_id,
                "name": g.name,
                "description": g.description,
                "tags": g.tags,
            }
            for g in cls._templates.values()
        ]


def _build_template(
    template_id: str,
    name: str,
    description: str,
    tags: List[str],
    steps: List[Dict[str, Any]],
    connections: List[tuple],
) -> WorkflowGraph:
    """Helper to build a workflow graph from a simple step list."""
    graph = WorkflowGraph(workflow_id=template_id, name=name, description=description)
    graph.tags = tags

    node_map: Dict[str, WorkflowNode] = {}
    y = 0.0
    for i, step in enumerate(steps):
        node = WorkflowNode.create(
            node_type=NodeType(step["type"]),
            label=step["label"],
            description=step.get("description", ""),
            config=step.get("config", {}),
            position={"x": 300.0, "y": y},
        )
        node_map[step["key"]] = node
        graph.add_node(node)
        y += 120.0

    for src_key, tgt_key, condition_str in connections:
        edge = WorkflowEdge.create(
            source_id=node_map[src_key].id,
            target_id=node_map[tgt_key].id,
            condition=EdgeCondition(condition_str),
        )
        graph.add_edge(edge)

    return graph


def _register_all_templates() -> None:
    # 1. Trust Creation Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_trust_creation",
        "Trust Creation Workflow",
        "End-to-end workflow for creating a legal trust document.",
        ["trust", "estate"],
        [
            {"key": "start", "type": "START", "label": "Initiate Trust Creation"},
            {"key": "collect_info", "type": "ACTION", "label": "Collect Grantor Information"},
            {"key": "select_type", "type": "DECISION", "label": "Select Trust Type"},
            {"key": "revocable", "type": "ACTION", "label": "Draft Revocable Trust"},
            {"key": "irrevocable", "type": "ACTION", "label": "Draft Irrevocable Trust"},
            {"key": "review", "type": "HUMAN_REVIEW", "label": "Attorney Review"},
            {"key": "sign", "type": "ACTION", "label": "Execute & Sign Documents"},
            {"key": "fund", "type": "ACTION", "label": "Fund Trust Assets"},
            {"key": "end", "type": "END", "label": "Trust Created"},
        ],
        [
            ("start", "collect_info", "always"),
            ("collect_info", "select_type", "on_success"),
            ("select_type", "revocable", "on_yes"),
            ("select_type", "irrevocable", "on_no"),
            ("revocable", "review", "always"),
            ("irrevocable", "review", "always"),
            ("review", "sign", "on_success"),
            ("sign", "fund", "on_success"),
            ("fund", "end", "on_success"),
        ],
    ))

    # 2. Estate Planning Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_estate_planning",
        "Estate Planning Workflow",
        "Comprehensive estate planning from asset inventory to document execution.",
        ["estate", "planning"],
        [
            {"key": "start", "type": "START", "label": "Begin Estate Planning"},
            {"key": "intake", "type": "ACTION", "label": "Client Intake & Assessment"},
            {"key": "inventory", "type": "ACTION", "label": "Asset Inventory"},
            {"key": "ai_analysis", "type": "AGENT_CALL", "label": "AI Estate Analysis"},
            {"key": "draft_will", "type": "PARALLEL", "label": "Draft Will & POA"},
            {"key": "review", "type": "HUMAN_REVIEW", "label": "Attorney Review Documents"},
            {"key": "revision", "type": "DECISION", "label": "Revisions Needed?"},
            {"key": "revise", "type": "ACTION", "label": "Apply Revisions"},
            {"key": "finalize", "type": "ACTION", "label": "Finalize Documents"},
            {"key": "sign", "type": "ACTION", "label": "Notarize & Execute"},
            {"key": "store", "type": "ACTION", "label": "Secure Document Storage"},
            {"key": "end", "type": "END", "label": "Estate Plan Complete"},
        ],
        [
            ("start", "intake", "always"),
            ("intake", "inventory", "on_success"),
            ("inventory", "ai_analysis", "on_success"),
            ("ai_analysis", "draft_will", "on_success"),
            ("draft_will", "review", "on_complete"),
            ("review", "revision", "on_complete"),
            ("revision", "revise", "on_yes"),
            ("revision", "finalize", "on_no"),
            ("revise", "finalize", "always"),
            ("finalize", "sign", "on_success"),
            ("sign", "store", "on_success"),
            ("store", "end", "on_success"),
        ],
    ))

    # 3. Debt Negotiation Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_debt_negotiation",
        "Debt Negotiation Workflow",
        "Structured workflow for negotiating debt settlements.",
        ["debt", "negotiation", "financial"],
        [
            {"key": "start", "type": "START", "label": "Initiate Debt Negotiation"},
            {"key": "gather", "type": "ACTION", "label": "Gather Debt Information"},
            {"key": "analyze", "type": "AGENT_CALL", "label": "AI Debt Analysis"},
            {"key": "strategy", "type": "DECISION", "label": "Select Negotiation Strategy"},
            {"key": "settlement", "type": "ACTION", "label": "Prepare Settlement Offer"},
            {"key": "hardship", "type": "ACTION", "label": "Hardship Letter"},
            {"key": "negotiate", "type": "HUMAN_REVIEW", "label": "Negotiate with Creditor"},
            {"key": "accepted", "type": "DECISION", "label": "Offer Accepted?"},
            {"key": "counter", "type": "ACTION", "label": "Counter Offer"},
            {"key": "agreement", "type": "ACTION", "label": "Draft Settlement Agreement"},
            {"key": "payment", "type": "ACTION", "label": "Payment Arrangement"},
            {"key": "end", "type": "END", "label": "Debt Negotiation Complete"},
        ],
        [
            ("start", "gather", "always"),
            ("gather", "analyze", "on_success"),
            ("analyze", "strategy", "on_success"),
            ("strategy", "settlement", "on_yes"),
            ("strategy", "hardship", "on_no"),
            ("settlement", "negotiate", "always"),
            ("hardship", "negotiate", "always"),
            ("negotiate", "accepted", "on_complete"),
            ("accepted", "agreement", "on_yes"),
            ("accepted", "counter", "on_no"),
            ("counter", "agreement", "always"),
            ("agreement", "payment", "on_success"),
            ("payment", "end", "on_success"),
        ],
    ))

    # 4. Business Formation Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_business_formation",
        "Business Formation Workflow",
        "Step-by-step workflow for forming a new business entity.",
        ["business", "formation", "corporate"],
        [
            {"key": "start", "type": "START", "label": "Begin Business Formation"},
            {"key": "consult", "type": "ACTION", "label": "Initial Consultation"},
            {"key": "entity_type", "type": "DECISION", "label": "Select Entity Type"},
            {"key": "llc", "type": "ACTION", "label": "Prepare LLC Articles"},
            {"key": "corp", "type": "ACTION", "label": "Prepare Corp Articles"},
            {"key": "name_search", "type": "ACTION", "label": "Name Availability Search"},
            {"key": "file_state", "type": "ACTION", "label": "File with Secretary of State"},
            {"key": "ein", "type": "ACTION", "label": "Obtain EIN from IRS"},
            {"key": "operating_agreement", "type": "ACTION", "label": "Draft Operating Agreement"},
            {"key": "bank_account", "type": "ACTION", "label": "Open Business Bank Account"},
            {"key": "licenses", "type": "ACTION", "label": "Obtain Business Licenses"},
            {"key": "end", "type": "END", "label": "Business Formation Complete"},
        ],
        [
            ("start", "consult", "always"),
            ("consult", "entity_type", "on_success"),
            ("entity_type", "llc", "on_yes"),
            ("entity_type", "corp", "on_no"),
            ("llc", "name_search", "always"),
            ("corp", "name_search", "always"),
            ("name_search", "file_state", "on_success"),
            ("file_state", "ein", "on_success"),
            ("ein", "operating_agreement", "on_success"),
            ("operating_agreement", "bank_account", "on_success"),
            ("bank_account", "licenses", "on_success"),
            ("licenses", "end", "on_success"),
        ],
    ))

    # 5. Court Filing Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_court_filing",
        "Court Filing Workflow",
        "Automated workflow for preparing and filing court documents.",
        ["court", "filing", "litigation"],
        [
            {"key": "start", "type": "START", "label": "Begin Court Filing"},
            {"key": "case_info", "type": "ACTION", "label": "Gather Case Information"},
            {"key": "doc_prep", "type": "AGENT_CALL", "label": "AI Document Preparation"},
            {"key": "review", "type": "HUMAN_REVIEW", "label": "Attorney Review"},
            {"key": "efiling", "type": "DECISION", "label": "E-Filing Available?"},
            {"key": "efile", "type": "ACTION", "label": "Electronic Filing"},
            {"key": "physical", "type": "ACTION", "label": "Physical Filing"},
            {"key": "confirm", "type": "WAIT", "label": "Await Filing Confirmation"},
            {"key": "serve", "type": "ACTION", "label": "Serve Opposing Parties"},
            {"key": "calendar", "type": "ACTION", "label": "Calendar Deadlines"},
            {"key": "end", "type": "END", "label": "Filing Complete"},
        ],
        [
            ("start", "case_info", "always"),
            ("case_info", "doc_prep", "on_success"),
            ("doc_prep", "review", "on_success"),
            ("review", "efiling", "on_success"),
            ("efiling", "efile", "on_yes"),
            ("efiling", "physical", "on_no"),
            ("efile", "confirm", "on_success"),
            ("physical", "confirm", "always"),
            ("confirm", "serve", "on_complete"),
            ("serve", "calendar", "on_success"),
            ("calendar", "end", "on_success"),
        ],
    ))

    # 6. Contract Review Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_contract_review",
        "Contract Review Workflow",
        "AI-assisted contract review and negotiation workflow.",
        ["contract", "review", "negotiation"],
        [
            {"key": "start", "type": "START", "label": "Receive Contract"},
            {"key": "extract", "type": "ACTION", "label": "Extract Key Terms"},
            {"key": "ai_review", "type": "AGENT_CALL", "label": "AI Risk Analysis"},
            {"key": "red_flags", "type": "DECISION", "label": "Red Flags Found?"},
            {"key": "flag_report", "type": "ACTION", "label": "Generate Flag Report"},
            {"key": "attorney_review", "type": "HUMAN_REVIEW", "label": "Attorney Review"},
            {"key": "negotiate", "type": "DECISION", "label": "Negotiation Required?"},
            {"key": "redline", "type": "ACTION", "label": "Prepare Redlines"},
            {"key": "approve", "type": "ACTION", "label": "Approve Contract"},
            {"key": "sign", "type": "ACTION", "label": "Execute Contract"},
            {"key": "end", "type": "END", "label": "Contract Review Complete"},
        ],
        [
            ("start", "extract", "always"),
            ("extract", "ai_review", "on_success"),
            ("ai_review", "red_flags", "on_success"),
            ("red_flags", "flag_report", "on_yes"),
            ("red_flags", "attorney_review", "on_no"),
            ("flag_report", "attorney_review", "always"),
            ("attorney_review", "negotiate", "on_complete"),
            ("negotiate", "redline", "on_yes"),
            ("negotiate", "approve", "on_no"),
            ("redline", "approve", "always"),
            ("approve", "sign", "on_success"),
            ("sign", "end", "on_success"),
        ],
    ))

    # 7. Bankruptcy Filing Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_bankruptcy_filing",
        "Bankruptcy Filing Workflow",
        "Workflow for Chapter 7 and Chapter 13 bankruptcy filings.",
        ["bankruptcy", "filing", "financial"],
        [
            {"key": "start", "type": "START", "label": "Initiate Bankruptcy Filing"},
            {"key": "means_test", "type": "ACTION", "label": "Means Test Analysis"},
            {"key": "chapter_select", "type": "DECISION", "label": "Chapter 7 or 13?"},
            {"key": "ch7_petition", "type": "ACTION", "label": "Prepare Chapter 7 Petition"},
            {"key": "ch13_plan", "type": "ACTION", "label": "Prepare Chapter 13 Plan"},
            {"key": "credit_counseling", "type": "ACTION", "label": "Credit Counseling"},
            {"key": "file_petition", "type": "ACTION", "label": "File Petition with Court"},
            {"key": "automatic_stay", "type": "ACTION", "label": "Automatic Stay Notice"},
            {"key": "trustee_meeting", "type": "WAIT", "label": "341 Meeting of Creditors"},
            {"key": "discharge", "type": "ACTION", "label": "Obtain Discharge Order"},
            {"key": "end", "type": "END", "label": "Bankruptcy Complete"},
        ],
        [
            ("start", "means_test", "always"),
            ("means_test", "chapter_select", "on_success"),
            ("chapter_select", "ch7_petition", "on_yes"),
            ("chapter_select", "ch13_plan", "on_no"),
            ("ch7_petition", "credit_counseling", "always"),
            ("ch13_plan", "credit_counseling", "always"),
            ("credit_counseling", "file_petition", "on_success"),
            ("file_petition", "automatic_stay", "on_success"),
            ("automatic_stay", "trustee_meeting", "on_success"),
            ("trustee_meeting", "discharge", "on_complete"),
            ("discharge", "end", "on_success"),
        ],
    ))

    # 8. Real Estate Closing Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_real_estate_closing",
        "Real Estate Closing Workflow",
        "Complete workflow for residential real estate closing.",
        ["real-estate", "closing"],
        [
            {"key": "start", "type": "START", "label": "Initiate Closing Process"},
            {"key": "title_search", "type": "ACTION", "label": "Title Search"},
            {"key": "title_clear", "type": "DECISION", "label": "Title Clear?"},
            {"key": "title_issues", "type": "HUMAN_REVIEW", "label": "Resolve Title Issues"},
            {"key": "insurance", "type": "ACTION", "label": "Title Insurance"},
            {"key": "final_walkthrough", "type": "ACTION", "label": "Final Walkthrough"},
            {"key": "closing_disclosure", "type": "ACTION", "label": "Closing Disclosure Review"},
            {"key": "sign_docs", "type": "ACTION", "label": "Sign Closing Documents"},
            {"key": "fund", "type": "ACTION", "label": "Fund Transaction"},
            {"key": "record", "type": "ACTION", "label": "Record Deed"},
            {"key": "end", "type": "END", "label": "Closing Complete"},
        ],
        [
            ("start", "title_search", "always"),
            ("title_search", "title_clear", "on_success"),
            ("title_clear", "insurance", "on_yes"),
            ("title_clear", "title_issues", "on_no"),
            ("title_issues", "insurance", "on_success"),
            ("insurance", "final_walkthrough", "on_success"),
            ("final_walkthrough", "closing_disclosure", "on_success"),
            ("closing_disclosure", "sign_docs", "on_success"),
            ("sign_docs", "fund", "on_success"),
            ("fund", "record", "on_success"),
            ("record", "end", "on_success"),
        ],
    ))

    # 9. Immigration Application Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_immigration",
        "Immigration Application Workflow",
        "Visa and immigration application processing workflow.",
        ["immigration", "visa"],
        [
            {"key": "start", "type": "START", "label": "Begin Immigration Application"},
            {"key": "eligibility", "type": "AGENT_CALL", "label": "Check Eligibility"},
            {"key": "gather_docs", "type": "ACTION", "label": "Gather Documents"},
            {"key": "prepare", "type": "ACTION", "label": "Prepare Application"},
            {"key": "review", "type": "HUMAN_REVIEW", "label": "Attorney Review"},
            {"key": "file", "type": "ACTION", "label": "File Application"},
            {"key": "biometrics", "type": "WAIT", "label": "Biometrics Appointment"},
            {"key": "interview", "type": "WAIT", "label": "Interview Scheduled"},
            {"key": "decision", "type": "DECISION", "label": "Application Approved?"},
            {"key": "approved", "type": "ACTION", "label": "Issue Status Documents"},
            {"key": "denied", "type": "ACTION", "label": "File Appeal"},
            {"key": "end", "type": "END", "label": "Immigration Process Complete"},
        ],
        [
            ("start", "eligibility", "always"),
            ("eligibility", "gather_docs", "on_success"),
            ("gather_docs", "prepare", "on_success"),
            ("prepare", "review", "on_success"),
            ("review", "file", "on_success"),
            ("file", "biometrics", "on_success"),
            ("biometrics", "interview", "on_complete"),
            ("interview", "decision", "on_complete"),
            ("decision", "approved", "on_yes"),
            ("decision", "denied", "on_no"),
            ("approved", "end", "on_success"),
            ("denied", "end", "on_success"),
        ],
    ))

    # 10. Employment Dispute Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_employment_dispute",
        "Employment Dispute Workflow",
        "Workflow for handling employment discrimination and wrongful termination claims.",
        ["employment", "dispute", "litigation"],
        [
            {"key": "start", "type": "START", "label": "Report Employment Dispute"},
            {"key": "intake", "type": "ACTION", "label": "Client Intake"},
            {"key": "analyze", "type": "AGENT_CALL", "label": "AI Case Analysis"},
            {"key": "eeoc_file", "type": "ACTION", "label": "File EEOC Charge"},
            {"key": "mediation", "type": "WAIT", "label": "EEOC Mediation"},
            {"key": "settlement", "type": "DECISION", "label": "Settlement Reached?"},
            {"key": "right_to_sue", "type": "ACTION", "label": "Request Right to Sue"},
            {"key": "file_lawsuit", "type": "ACTION", "label": "File Lawsuit"},
            {"key": "discovery", "type": "ACTION", "label": "Discovery Phase"},
            {"key": "trial_prep", "type": "ACTION", "label": "Trial Preparation"},
            {"key": "end", "type": "END", "label": "Dispute Resolved"},
        ],
        [
            ("start", "intake", "always"),
            ("intake", "analyze", "on_success"),
            ("analyze", "eeoc_file", "on_success"),
            ("eeoc_file", "mediation", "on_success"),
            ("mediation", "settlement", "on_complete"),
            ("settlement", "end", "on_yes"),
            ("settlement", "right_to_sue", "on_no"),
            ("right_to_sue", "file_lawsuit", "on_success"),
            ("file_lawsuit", "discovery", "on_success"),
            ("discovery", "trial_prep", "on_success"),
            ("trial_prep", "end", "on_success"),
        ],
    ))

    # 11. Intellectual Property Filing
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_ip_filing",
        "Intellectual Property Filing Workflow",
        "Patent, trademark, and copyright filing workflow.",
        ["ip", "patent", "trademark"],
        [
            {"key": "start", "type": "START", "label": "Begin IP Filing"},
            {"key": "ip_type", "type": "DECISION", "label": "Select IP Type"},
            {"key": "patent_search", "type": "AGENT_CALL", "label": "Prior Art Search"},
            {"key": "trademark_search", "type": "ACTION", "label": "Trademark Search"},
            {"key": "prepare_app", "type": "ACTION", "label": "Prepare Application"},
            {"key": "review", "type": "HUMAN_REVIEW", "label": "Attorney Review"},
            {"key": "file_uspto", "type": "ACTION", "label": "File with USPTO"},
            {"key": "office_action", "type": "WAIT", "label": "Await Office Action"},
            {"key": "respond", "type": "ACTION", "label": "Respond to Office Action"},
            {"key": "approval", "type": "DECISION", "label": "Approved?"},
            {"key": "issue_fee", "type": "ACTION", "label": "Pay Issue Fee"},
            {"key": "end", "type": "END", "label": "IP Filing Complete"},
        ],
        [
            ("start", "ip_type", "always"),
            ("ip_type", "patent_search", "on_yes"),
            ("ip_type", "trademark_search", "on_no"),
            ("patent_search", "prepare_app", "on_success"),
            ("trademark_search", "prepare_app", "always"),
            ("prepare_app", "review", "on_success"),
            ("review", "file_uspto", "on_success"),
            ("file_uspto", "office_action", "on_success"),
            ("office_action", "respond", "on_complete"),
            ("respond", "approval", "on_success"),
            ("approval", "issue_fee", "on_yes"),
            ("approval", "end", "on_no"),
            ("issue_fee", "end", "on_success"),
        ],
    ))

    # 12. Divorce Proceedings Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_divorce",
        "Divorce Proceedings Workflow",
        "Contested and uncontested divorce proceedings workflow.",
        ["family-law", "divorce"],
        [
            {"key": "start", "type": "START", "label": "Initiate Divorce Proceedings"},
            {"key": "contested", "type": "DECISION", "label": "Contested Divorce?"},
            {"key": "petition", "type": "ACTION", "label": "File Divorce Petition"},
            {"key": "serve", "type": "ACTION", "label": "Serve Spouse"},
            {"key": "response", "type": "WAIT", "label": "Await Response"},
            {"key": "mediation", "type": "ACTION", "label": "Mediation"},
            {"key": "asset_division", "type": "ACTION", "label": "Asset Division Agreement"},
            {"key": "custody", "type": "DECISION", "label": "Child Custody Issue?"},
            {"key": "custody_plan", "type": "HUMAN_REVIEW", "label": "Custody Plan Review"},
            {"key": "final_decree", "type": "ACTION", "label": "File Final Decree"},
            {"key": "end", "type": "END", "label": "Divorce Finalized"},
        ],
        [
            ("start", "contested", "always"),
            ("contested", "petition", "always"),
            ("petition", "serve", "on_success"),
            ("serve", "response", "on_success"),
            ("response", "mediation", "on_complete"),
            ("mediation", "asset_division", "on_success"),
            ("asset_division", "custody", "on_success"),
            ("custody", "custody_plan", "on_yes"),
            ("custody", "final_decree", "on_no"),
            ("custody_plan", "final_decree", "on_success"),
            ("final_decree", "end", "on_success"),
        ],
    ))

    # 13. Personal Injury Claim Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_personal_injury",
        "Personal Injury Claim Workflow",
        "End-to-end personal injury claim and litigation workflow.",
        ["personal-injury", "litigation"],
        [
            {"key": "start", "type": "START", "label": "Open PI Claim"},
            {"key": "intake", "type": "ACTION", "label": "Client Intake & Medical Records"},
            {"key": "liability", "type": "AGENT_CALL", "label": "Liability Analysis"},
            {"key": "demand", "type": "ACTION", "label": "Prepare Demand Letter"},
            {"key": "negotiate", "type": "HUMAN_REVIEW", "label": "Negotiate with Insurer"},
            {"key": "settled", "type": "DECISION", "label": "Settlement Accepted?"},
            {"key": "lawsuit", "type": "ACTION", "label": "File Lawsuit"},
            {"key": "discovery", "type": "ACTION", "label": "Discovery"},
            {"key": "mediate", "type": "ACTION", "label": "Mediation"},
            {"key": "verdict", "type": "ACTION", "label": "Trial / Verdict"},
            {"key": "end", "type": "END", "label": "PI Case Resolved"},
        ],
        [
            ("start", "intake", "always"),
            ("intake", "liability", "on_success"),
            ("liability", "demand", "on_success"),
            ("demand", "negotiate", "on_success"),
            ("negotiate", "settled", "on_complete"),
            ("settled", "end", "on_yes"),
            ("settled", "lawsuit", "on_no"),
            ("lawsuit", "discovery", "on_success"),
            ("discovery", "mediate", "on_success"),
            ("mediate", "verdict", "always"),
            ("verdict", "end", "on_success"),
        ],
    ))

    # 14. Criminal Defense Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_criminal_defense",
        "Criminal Defense Workflow",
        "Workflow for criminal defense case management.",
        ["criminal", "defense"],
        [
            {"key": "start", "type": "START", "label": "Open Criminal Defense Case"},
            {"key": "arrest_info", "type": "ACTION", "label": "Gather Arrest Information"},
            {"key": "bail", "type": "ACTION", "label": "Bail Hearing Preparation"},
            {"key": "arraignment", "type": "WAIT", "label": "Arraignment"},
            {"key": "evidence", "type": "ACTION", "label": "Evidence Review"},
            {"key": "motions", "type": "ACTION", "label": "File Pre-trial Motions"},
            {"key": "plea", "type": "DECISION", "label": "Plea Deal Available?"},
            {"key": "negotiate_plea", "type": "HUMAN_REVIEW", "label": "Negotiate Plea"},
            {"key": "trial_prep", "type": "ACTION", "label": "Trial Preparation"},
            {"key": "trial", "type": "ACTION", "label": "Trial"},
            {"key": "end", "type": "END", "label": "Criminal Case Resolved"},
        ],
        [
            ("start", "arrest_info", "always"),
            ("arrest_info", "bail", "on_success"),
            ("bail", "arraignment", "on_success"),
            ("arraignment", "evidence", "on_complete"),
            ("evidence", "motions", "on_success"),
            ("motions", "plea", "on_success"),
            ("plea", "negotiate_plea", "on_yes"),
            ("plea", "trial_prep", "on_no"),
            ("negotiate_plea", "end", "on_success"),
            ("trial_prep", "trial", "on_success"),
            ("trial", "end", "on_success"),
        ],
    ))

    # 15. Power of Attorney Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_power_of_attorney",
        "Power of Attorney Workflow",
        "Workflow for creating and executing Power of Attorney documents.",
        ["estate", "poa"],
        [
            {"key": "start", "type": "START", "label": "Begin POA Process"},
            {"key": "assess", "type": "ACTION", "label": "Assess Client Needs"},
            {"key": "poa_type", "type": "DECISION", "label": "General or Durable POA?"},
            {"key": "general", "type": "ACTION", "label": "Draft General POA"},
            {"key": "durable", "type": "ACTION", "label": "Draft Durable POA"},
            {"key": "review", "type": "HUMAN_REVIEW", "label": "Review with Client"},
            {"key": "notarize", "type": "ACTION", "label": "Notarize Document"},
            {"key": "record", "type": "ACTION", "label": "Record if Required"},
            {"key": "distribute", "type": "ACTION", "label": "Distribute Copies"},
            {"key": "end", "type": "END", "label": "POA Complete"},
        ],
        [
            ("start", "assess", "always"),
            ("assess", "poa_type", "on_success"),
            ("poa_type", "general", "on_yes"),
            ("poa_type", "durable", "on_no"),
            ("general", "review", "always"),
            ("durable", "review", "always"),
            ("review", "notarize", "on_success"),
            ("notarize", "record", "on_success"),
            ("record", "distribute", "on_success"),
            ("distribute", "end", "on_success"),
        ],
    ))

    # 16. Landlord-Tenant Dispute Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_landlord_tenant",
        "Landlord-Tenant Dispute Workflow",
        "Workflow for handling landlord-tenant disputes and evictions.",
        ["landlord-tenant", "real-estate"],
        [
            {"key": "start", "type": "START", "label": "Open Dispute"},
            {"key": "assess", "type": "ACTION", "label": "Assess Dispute Type"},
            {"key": "notice", "type": "ACTION", "label": "Issue Cure or Quit Notice"},
            {"key": "response", "type": "WAIT", "label": "Await Tenant Response"},
            {"key": "resolved", "type": "DECISION", "label": "Issue Resolved?"},
            {"key": "mediation", "type": "ACTION", "label": "Mediation"},
            {"key": "eviction_file", "type": "ACTION", "label": "File Eviction Complaint"},
            {"key": "hearing", "type": "WAIT", "label": "Eviction Hearing"},
            {"key": "judgment", "type": "ACTION", "label": "Obtain Judgment"},
            {"key": "enforce", "type": "ACTION", "label": "Enforce Judgment"},
            {"key": "end", "type": "END", "label": "Dispute Resolved"},
        ],
        [
            ("start", "assess", "always"),
            ("assess", "notice", "on_success"),
            ("notice", "response", "on_success"),
            ("response", "resolved", "on_complete"),
            ("resolved", "end", "on_yes"),
            ("resolved", "mediation", "on_no"),
            ("mediation", "eviction_file", "on_complete"),
            ("eviction_file", "hearing", "on_success"),
            ("hearing", "judgment", "on_complete"),
            ("judgment", "enforce", "on_success"),
            ("enforce", "end", "on_success"),
        ],
    ))

    # 17. Non-Profit Formation Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_nonprofit_formation",
        "Non-Profit Formation Workflow",
        "Workflow for forming a 501(c)(3) non-profit organization.",
        ["nonprofit", "corporate", "tax"],
        [
            {"key": "start", "type": "START", "label": "Begin Non-Profit Formation"},
            {"key": "mission", "type": "ACTION", "label": "Define Mission & Purpose"},
            {"key": "board", "type": "ACTION", "label": "Recruit Board Members"},
            {"key": "incorporate", "type": "ACTION", "label": "Incorporate in State"},
            {"key": "bylaws", "type": "ACTION", "label": "Draft Bylaws"},
            {"key": "ein", "type": "ACTION", "label": "Obtain EIN"},
            {"key": "form_1023", "type": "AGENT_CALL", "label": "Prepare Form 1023"},
            {"key": "irs_review", "type": "WAIT", "label": "IRS Review Period"},
            {"key": "determination", "type": "DECISION", "label": "501(c)(3) Granted?"},
            {"key": "state_exemption", "type": "ACTION", "label": "Apply for State Exemption"},
            {"key": "register", "type": "ACTION", "label": "Register for Charitable Solicitation"},
            {"key": "end", "type": "END", "label": "Non-Profit Formation Complete"},
        ],
        [
            ("start", "mission", "always"),
            ("mission", "board", "on_success"),
            ("board", "incorporate", "on_success"),
            ("incorporate", "bylaws", "on_success"),
            ("bylaws", "ein", "on_success"),
            ("ein", "form_1023", "on_success"),
            ("form_1023", "irs_review", "on_success"),
            ("irs_review", "determination", "on_complete"),
            ("determination", "state_exemption", "on_yes"),
            ("determination", "end", "on_no"),
            ("state_exemption", "register", "on_success"),
            ("register", "end", "on_success"),
        ],
    ))

    # 18. Guardianship Petition Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_guardianship",
        "Guardianship Petition Workflow",
        "Workflow for filing and processing guardianship petitions.",
        ["family-law", "guardianship"],
        [
            {"key": "start", "type": "START", "label": "Initiate Guardianship Petition"},
            {"key": "capacity_eval", "type": "ACTION", "label": "Capacity Evaluation"},
            {"key": "petition_prep", "type": "ACTION", "label": "Prepare Petition"},
            {"key": "file_court", "type": "ACTION", "label": "File with Court"},
            {"key": "notice", "type": "ACTION", "label": "Serve Notice"},
            {"key": "investigation", "type": "WAIT", "label": "Court Investigation"},
            {"key": "hearing", "type": "WAIT", "label": "Guardianship Hearing"},
            {"key": "granted", "type": "DECISION", "label": "Guardianship Granted?"},
            {"key": "letters", "type": "ACTION", "label": "Issue Letters of Guardianship"},
            {"key": "bond", "type": "ACTION", "label": "Post Guardianship Bond"},
            {"key": "end", "type": "END", "label": "Guardianship Established"},
        ],
        [
            ("start", "capacity_eval", "always"),
            ("capacity_eval", "petition_prep", "on_success"),
            ("petition_prep", "file_court", "on_success"),
            ("file_court", "notice", "on_success"),
            ("notice", "investigation", "on_success"),
            ("investigation", "hearing", "on_complete"),
            ("hearing", "granted", "on_complete"),
            ("granted", "letters", "on_yes"),
            ("granted", "end", "on_no"),
            ("letters", "bond", "on_success"),
            ("bond", "end", "on_success"),
        ],
    ))

    # 19. Tax Dispute Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_tax_dispute",
        "Tax Dispute Workflow",
        "IRS audit and tax dispute resolution workflow.",
        ["tax", "irs", "dispute"],
        [
            {"key": "start", "type": "START", "label": "Receive IRS Notice"},
            {"key": "classify", "type": "AGENT_CALL", "label": "Classify Notice Type"},
            {"key": "gather", "type": "ACTION", "label": "Gather Tax Documents"},
            {"key": "respond", "type": "ACTION", "label": "Prepare Response"},
            {"key": "submit", "type": "ACTION", "label": "Submit to IRS"},
            {"key": "audit", "type": "DECISION", "label": "Full Audit Required?"},
            {"key": "audit_prep", "type": "ACTION", "label": "Audit Preparation"},
            {"key": "irs_meeting", "type": "HUMAN_REVIEW", "label": "IRS Meeting"},
            {"key": "appeal", "type": "DECISION", "label": "Appeal Decision?"},
            {"key": "tax_court", "type": "ACTION", "label": "File in Tax Court"},
            {"key": "resolve", "type": "ACTION", "label": "Resolve Tax Liability"},
            {"key": "end", "type": "END", "label": "Tax Dispute Resolved"},
        ],
        [
            ("start", "classify", "always"),
            ("classify", "gather", "on_success"),
            ("gather", "respond", "on_success"),
            ("respond", "submit", "on_success"),
            ("submit", "audit", "on_success"),
            ("audit", "audit_prep", "on_yes"),
            ("audit", "resolve", "on_no"),
            ("audit_prep", "irs_meeting", "on_success"),
            ("irs_meeting", "appeal", "on_complete"),
            ("appeal", "tax_court", "on_yes"),
            ("appeal", "resolve", "on_no"),
            ("tax_court", "resolve", "on_success"),
            ("resolve", "end", "on_success"),
        ],
    ))

    # 20. Mergers & Acquisitions Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_mergers_acquisitions",
        "Mergers & Acquisitions Workflow",
        "Due diligence and M&A transaction workflow.",
        ["corporate", "ma", "transactions"],
        [
            {"key": "start", "type": "START", "label": "Initiate M&A Process"},
            {"key": "nda", "type": "ACTION", "label": "Execute NDA"},
            {"key": "loi", "type": "ACTION", "label": "Letter of Intent"},
            {"key": "due_diligence", "type": "PARALLEL", "label": "Due Diligence"},
            {"key": "legal_dd", "type": "ACTION", "label": "Legal Due Diligence"},
            {"key": "financial_dd", "type": "ACTION", "label": "Financial Due Diligence"},
            {"key": "valuation", "type": "AGENT_CALL", "label": "AI Valuation Analysis"},
            {"key": "negotiate", "type": "HUMAN_REVIEW", "label": "Negotiate Deal Terms"},
            {"key": "definitive_agreement", "type": "ACTION", "label": "Draft Definitive Agreement"},
            {"key": "regulatory", "type": "WAIT", "label": "Regulatory Approval"},
            {"key": "closing", "type": "ACTION", "label": "Closing"},
            {"key": "end", "type": "END", "label": "M&A Complete"},
        ],
        [
            ("start", "nda", "always"),
            ("nda", "loi", "on_success"),
            ("loi", "due_diligence", "on_success"),
            ("due_diligence", "legal_dd", "always"),
            ("due_diligence", "financial_dd", "always"),
            ("legal_dd", "valuation", "on_success"),
            ("financial_dd", "valuation", "on_success"),
            ("valuation", "negotiate", "on_success"),
            ("negotiate", "definitive_agreement", "on_success"),
            ("definitive_agreement", "regulatory", "on_success"),
            ("regulatory", "closing", "on_complete"),
            ("closing", "end", "on_success"),
        ],
    ))

    # 21. Compliance Audit Workflow
    WorkflowTemplateRegistry.register(_build_template(
        "tpl_compliance_audit",
        "Compliance Audit Workflow",
        "Regulatory compliance audit and remediation workflow.",
        ["compliance", "audit", "regulatory"],
        [
            {"key": "start", "type": "START", "label": "Begin Compliance Audit"},
            {"key": "scope", "type": "ACTION", "label": "Define Audit Scope"},
            {"key": "data_collect", "type": "ACTION", "label": "Collect Compliance Data"},
            {"key": "ai_assess", "type": "AGENT_CALL", "label": "AI Risk Assessment"},
            {"key": "gaps", "type": "DECISION", "label": "Compliance Gaps Found?"},
            {"key": "remediation_plan", "type": "ACTION", "label": "Create Remediation Plan"},
            {"key": "implement", "type": "ACTION", "label": "Implement Remediation"},
            {"key": "verify", "type": "ACTION", "label": "Verify Compliance"},
            {"key": "report", "type": "HUMAN_REVIEW", "label": "Audit Report Review"},
            {"key": "submit", "type": "ACTION", "label": "Submit Audit Report"},
            {"key": "end", "type": "END", "label": "Compliance Audit Complete"},
        ],
        [
            ("start", "scope", "always"),
            ("scope", "data_collect", "on_success"),
            ("data_collect", "ai_assess", "on_success"),
            ("ai_assess", "gaps", "on_success"),
            ("gaps", "remediation_plan", "on_yes"),
            ("gaps", "report", "on_no"),
            ("remediation_plan", "implement", "on_success"),
            ("implement", "verify", "on_success"),
            ("verify", "report", "on_success"),
            ("report", "submit", "on_success"),
            ("submit", "end", "on_success"),
        ],
    ))


# Run registrations on import
_register_all_templates()


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def create_workflow(name: str, description: str = "") -> WorkflowGraph:
    """Create a new empty workflow graph."""
    return WorkflowGraph(
        workflow_id=str(uuid.uuid4()),
        name=name,
        description=description,
    )


def get_template(template_id: str) -> Optional[WorkflowGraph]:
    """Retrieve a registered template by ID."""
    return WorkflowTemplateRegistry.get(template_id)


def list_templates() -> List[Dict[str, str]]:
    """List all registered workflow templates."""
    return WorkflowTemplateRegistry.list_templates()
