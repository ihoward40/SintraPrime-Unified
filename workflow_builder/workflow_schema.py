"""
SintraPrime-Unified Workflow Schema
Provides JSON schema for React Flow / LangFlow compatible format,
plus export to Python executable workflow and import from visual editor JSON.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from workflow_builder.workflow_engine import (
    EdgeCondition,
    NodeType,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
    WorkflowSerializer,
)


# ---------------------------------------------------------------------------
# React Flow / LangFlow compatible JSON schema
# ---------------------------------------------------------------------------

# JSON Schema definition (meta-schema)
WORKFLOW_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://sintraprime.ai/schemas/workflow.json",
    "title": "SintraPrime Workflow",
    "type": "object",
    "required": ["id", "name", "nodes", "edges"],
    "properties": {
        "id": {"type": "string", "description": "Unique workflow identifier"},
        "name": {"type": "string", "description": "Human-readable workflow name"},
        "description": {"type": "string"},
        "version": {"type": "string", "default": "1.0.0"},
        "author": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "nodes": {
            "type": "array",
            "items": {"$ref": "#/$defs/Node"},
            "minItems": 1,
        },
        "edges": {
            "type": "array",
            "items": {"$ref": "#/$defs/Edge"},
        },
        "viewport": {
            "type": "object",
            "properties": {
                "x": {"type": "number"},
                "y": {"type": "number"},
                "zoom": {"type": "number", "default": 1.0},
            },
        },
    },
    "$defs": {
        "Node": {
            "type": "object",
            "required": ["id", "type", "position", "data"],
            "properties": {
                "id": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": [t.value for t in NodeType],
                },
                "position": {
                    "type": "object",
                    "required": ["x", "y"],
                    "properties": {
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                    },
                },
                "data": {"$ref": "#/$defs/NodeData"},
                "width": {"type": "number"},
                "height": {"type": "number"},
                "selected": {"type": "boolean", "default": False},
                "dragging": {"type": "boolean", "default": False},
            },
        },
        "NodeData": {
            "type": "object",
            "required": ["label"],
            "properties": {
                "label": {"type": "string"},
                "description": {"type": "string"},
                "config": {
                    "type": "object",
                    "additionalProperties": True,
                },
                "inputs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                            "type": {"type": "string"},
                            "required": {"type": "boolean"},
                        },
                    },
                },
                "outputs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                            "type": {"type": "string"},
                        },
                    },
                },
                "timeout_seconds": {"type": ["integer", "null"]},
                "retry_count": {"type": "integer", "default": 0},
                "is_required": {"type": "boolean", "default": True},
                "metadata": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
        },
        "Edge": {
            "type": "object",
            "required": ["id", "source", "target"],
            "properties": {
                "id": {"type": "string"},
                "source": {"type": "string"},
                "target": {"type": "string"},
                "sourceHandle": {"type": ["string", "null"]},
                "targetHandle": {"type": ["string", "null"]},
                "condition": {
                    "type": "string",
                    "enum": [c.value for c in EdgeCondition],
                    "default": "always",
                },
                "condition_expression": {"type": "string"},
                "label": {"type": "string"},
                "animated": {"type": "boolean", "default": False},
                "style": {
                    "type": "object",
                    "additionalProperties": True,
                },
                "metadata": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Node visual styles by type (for React Flow rendering)
# ---------------------------------------------------------------------------

NODE_STYLES: Dict[str, Dict[str, Any]] = {
    NodeType.START.value: {
        "backgroundColor": "#22c55e",
        "color": "#ffffff",
        "borderRadius": "50%",
        "border": "2px solid #16a34a",
        "icon": "▶",
    },
    NodeType.END.value: {
        "backgroundColor": "#ef4444",
        "color": "#ffffff",
        "borderRadius": "50%",
        "border": "2px solid #dc2626",
        "icon": "⏹",
    },
    NodeType.ACTION.value: {
        "backgroundColor": "#3b82f6",
        "color": "#ffffff",
        "borderRadius": "8px",
        "border": "2px solid #2563eb",
        "icon": "⚡",
    },
    NodeType.DECISION.value: {
        "backgroundColor": "#f59e0b",
        "color": "#ffffff",
        "borderRadius": "4px",
        "border": "2px solid #d97706",
        "icon": "◆",
        "shape": "diamond",
    },
    NodeType.PARALLEL.value: {
        "backgroundColor": "#8b5cf6",
        "color": "#ffffff",
        "borderRadius": "8px",
        "border": "2px solid #7c3aed",
        "icon": "⫶",
    },
    NodeType.WAIT.value: {
        "backgroundColor": "#6b7280",
        "color": "#ffffff",
        "borderRadius": "8px",
        "border": "2px solid #4b5563",
        "icon": "⏳",
    },
    NodeType.AGENT_CALL.value: {
        "backgroundColor": "#06b6d4",
        "color": "#ffffff",
        "borderRadius": "8px",
        "border": "2px solid #0891b2",
        "icon": "🤖",
    },
    NodeType.HUMAN_REVIEW.value: {
        "backgroundColor": "#ec4899",
        "color": "#ffffff",
        "borderRadius": "8px",
        "border": "2px solid #db2777",
        "icon": "👤",
    },
}


# ---------------------------------------------------------------------------
# React Flow JSON Converter
# ---------------------------------------------------------------------------

@dataclass
class ReactFlowNode:
    """A node in React Flow format."""
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]
    width: float = 200.0
    height: float = 60.0
    selected: bool = False
    dragging: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "position": self.position,
            "data": self.data,
            "width": self.width,
            "height": self.height,
            "selected": self.selected,
            "dragging": self.dragging,
            "style": NODE_STYLES.get(self.type, {}),
        }


@dataclass
class ReactFlowEdge:
    """An edge in React Flow format."""
    id: str
    source: str
    target: str
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    condition: str = "always"
    condition_expression: str = ""
    label: str = ""
    animated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "condition": self.condition,
            "animated": self.animated,
            "label": self.label,
        }
        if self.source_handle:
            d["sourceHandle"] = self.source_handle
        if self.target_handle:
            d["targetHandle"] = self.target_handle
        if self.condition_expression:
            d["condition_expression"] = self.condition_expression
        if self.metadata:
            d["metadata"] = self.metadata
        return d


class ReactFlowConverter:
    """Convert between WorkflowGraph and React Flow JSON format."""

    @staticmethod
    def graph_to_react_flow(graph: WorkflowGraph) -> Dict[str, Any]:
        """Export a WorkflowGraph as React Flow JSON."""
        rf_nodes = []
        for node in graph.nodes.values():
            rf_node = ReactFlowNode(
                id=node.id,
                type=node.node_type.value,
                position=node.position,
                data={
                    "label": node.label,
                    "description": node.description,
                    "config": node.config,
                    "inputs": node.inputs,
                    "outputs": node.outputs,
                    "timeout_seconds": node.timeout_seconds,
                    "retry_count": node.retry_count,
                    "is_required": node.is_required,
                    "metadata": node.metadata,
                },
            )
            rf_nodes.append(rf_node.to_dict())

        rf_edges = []
        for edge in graph.edges.values():
            rf_edge = ReactFlowEdge(
                id=edge.id,
                source=edge.source_id,
                target=edge.target_id,
                condition=edge.condition.value,
                condition_expression=edge.condition_expression,
                label=edge.label,
                metadata=edge.metadata,
            )
            rf_edges.append(rf_edge.to_dict())

        return {
            "id": graph.workflow_id,
            "name": graph.name,
            "description": graph.description,
            "version": graph.version,
            "author": graph.author,
            "tags": graph.tags,
            "nodes": rf_nodes,
            "edges": rf_edges,
            "viewport": {"x": 0, "y": 0, "zoom": 1.0},
        }

    @staticmethod
    def react_flow_to_graph(data: Dict[str, Any]) -> WorkflowGraph:
        """Import a WorkflowGraph from React Flow JSON."""
        graph = WorkflowGraph(
            workflow_id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Imported Workflow"),
            description=data.get("description", ""),
        )
        graph.version = data.get("version", "1.0.0")
        graph.author = data.get("author", "")
        graph.tags = data.get("tags", [])

        for nd in data.get("nodes", []):
            node_data = nd.get("data", {})
            node = WorkflowNode(
                id=nd["id"],
                node_type=NodeType(nd["type"]),
                label=node_data.get("label", ""),
                description=node_data.get("description", ""),
                config=node_data.get("config", {}),
                inputs=node_data.get("inputs", []),
                outputs=node_data.get("outputs", []),
                position=nd.get("position", {"x": 0.0, "y": 0.0}),
                metadata=node_data.get("metadata", {}),
                timeout_seconds=node_data.get("timeout_seconds"),
                retry_count=node_data.get("retry_count", 0),
                is_required=node_data.get("is_required", True),
            )
            graph.add_node(node)

        for ed in data.get("edges", []):
            edge = WorkflowEdge(
                id=ed.get("id", str(uuid.uuid4())),
                source_id=ed["source"],
                target_id=ed["target"],
                condition=EdgeCondition(ed.get("condition", "always")),
                condition_expression=ed.get("condition_expression", ""),
                label=ed.get("label", ""),
                metadata=ed.get("metadata", {}),
            )
            graph.add_edge(edge)

        return graph


# ---------------------------------------------------------------------------
# Python Code Generator
# ---------------------------------------------------------------------------

class WorkflowCodeGenerator:
    """Generate Python executable workflow code from a WorkflowGraph."""

    @staticmethod
    def generate(graph: WorkflowGraph) -> str:
        """Generate Python code that executes the workflow."""
        lines: List[str] = []
        fn_name = graph.name.lower().replace(" ", "_").replace("-", "_")

        lines.append('"""')
        lines.append(f"Auto-generated workflow: {graph.name}")
        lines.append(f"Description: {graph.description}")
        lines.append(f"Version: {graph.version}")
        lines.append('"""')
        lines.append("")
        lines.append("from __future__ import annotations")
        lines.append("import asyncio")
        lines.append("import logging")
        lines.append("from typing import Any, Dict, Optional")
        lines.append("")
        lines.append("logger = logging.getLogger(__name__)")
        lines.append("")

        # Generate node handler stubs
        for node in graph.nodes.values():
            safe_label = node.label.lower().replace(" ", "_").replace("-", "_")
            safe_label = "".join(c if c.isalnum() or c == "_" else "" for c in safe_label)
            lines.append("")
            lines.append(f"async def handle_{safe_label}(context: Dict[str, Any]) -> Dict[str, Any]:")
            lines.append(f'    """Handler for node: {node.label} ({node.node_type.value})"""')
            lines.append(f'    logger.info("Executing: {node.label}")')
            if node.config:
                lines.append(f"    config = {json.dumps(node.config, indent=4)}")
            lines.append('    # TODO: Implement handler logic')
            lines.append("    return {\"status\": \"success\", **context}")

        # Generate main workflow function
        lines.append("")
        lines.append("")
        lines.append(f"async def run_{fn_name}(initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:")
        lines.append(f'    """Execute the {graph.name} workflow."""')
        lines.append("    context: Dict[str, Any] = initial_context or {}")
        lines.append(f'    logger.info("Starting workflow: {graph.name}")')
        lines.append("")

        # Build execution order using topological sort (if possible)
        try:
            topo_order = graph.topological_sort()
            for node_id in topo_order:
                node = graph.nodes[node_id]
                safe_label = node.label.lower().replace(" ", "_").replace("-", "_")
                safe_label = "".join(c if c.isalnum() or c == "_" else "" for c in safe_label)
                lines.append(f"    # Node: {node.label} [{node.node_type.value}]")
                lines.append(f"    context = await handle_{safe_label}(context)")
        except ValueError:
            lines.append("    # NOTE: Cycle detected - manual execution order required")
            for node in graph.nodes.values():
                safe_label = node.label.lower().replace(" ", "_").replace("-", "_")
                safe_label = "".join(c if c.isalnum() or c == "_" else "" for c in safe_label)
                lines.append(f"    context = await handle_{safe_label}(context)")

        lines.append("")
        lines.append(f'    logger.info("Workflow complete: {graph.name}")')
        lines.append("    return context")
        lines.append("")
        lines.append("")
        lines.append('if __name__ == "__main__":')
        lines.append("    import asyncio")
        lines.append(f"    result = asyncio.run(run_{fn_name}())")
        lines.append('    print("Workflow result:", result)')

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Schema Validator
# ---------------------------------------------------------------------------

class WorkflowSchemaValidator:
    """Validate workflow JSON against the schema."""

    @staticmethod
    def validate_react_flow_json(data: Dict[str, Any]) -> List[str]:
        """
        Validate React Flow JSON data.
        Returns list of error strings (empty = valid).
        """
        errors: List[str] = []

        if not isinstance(data, dict):
            errors.append("Workflow data must be a JSON object.")
            return errors

        for req_field in ["id", "name", "nodes"]:
            if req_field not in data:
                errors.append(f"Missing required field: '{req_field}'")

        if "nodes" in data:
            if not isinstance(data["nodes"], list):
                errors.append("'nodes' must be an array.")
            else:
                for i, nd in enumerate(data["nodes"]):
                    if "id" not in nd:
                        errors.append(f"Node[{i}] missing 'id'.")
                    if "type" not in nd:
                        errors.append(f"Node[{i}] missing 'type'.")
                    elif nd["type"] not in [t.value for t in NodeType]:
                        errors.append(f"Node[{i}] has invalid type: '{nd['type']}'.")
                    if "position" not in nd:
                        errors.append(f"Node[{i}] missing 'position'.")
                    if "data" not in nd:
                        errors.append(f"Node[{i}] missing 'data'.")
                    elif "label" not in nd.get("data", {}):
                        errors.append(f"Node[{i}] data missing 'label'.")

        if "edges" in data:
            if not isinstance(data["edges"], list):
                errors.append("'edges' must be an array.")
            else:
                node_ids = {nd.get("id") for nd in data.get("nodes", [])}
                for i, ed in enumerate(data["edges"]):
                    if "id" not in ed:
                        errors.append(f"Edge[{i}] missing 'id'.")
                    if "source" not in ed:
                        errors.append(f"Edge[{i}] missing 'source'.")
                    elif ed["source"] not in node_ids:
                        errors.append(f"Edge[{i}] source '{ed['source']}' not found in nodes.")
                    if "target" not in ed:
                        errors.append(f"Edge[{i}] missing 'target'.")
                    elif ed["target"] not in node_ids:
                        errors.append(f"Edge[{i}] target '{ed['target']}' not found in nodes.")

        return errors

    @staticmethod
    def get_json_schema() -> Dict[str, Any]:
        """Return the JSON Schema for workflow validation."""
        return WORKFLOW_JSON_SCHEMA


# ---------------------------------------------------------------------------
# High-level convenience functions
# ---------------------------------------------------------------------------

def export_workflow_to_react_flow(graph: WorkflowGraph) -> str:
    """Export WorkflowGraph to React Flow JSON string."""
    rf_data = ReactFlowConverter.graph_to_react_flow(graph)
    return json.dumps(rf_data, indent=2)


def import_workflow_from_react_flow(json_str: str) -> WorkflowGraph:
    """Import WorkflowGraph from React Flow JSON string."""
    data = json.loads(json_str)
    errors = WorkflowSchemaValidator.validate_react_flow_json(data)
    if errors:
        raise ValueError(f"Invalid workflow JSON: {'; '.join(errors)}")
    return ReactFlowConverter.react_flow_to_graph(data)


def export_workflow_to_python(graph: WorkflowGraph) -> str:
    """Generate Python executable code for a workflow."""
    return WorkflowCodeGenerator.generate(graph)


def get_node_styles() -> Dict[str, Dict[str, Any]]:
    """Return the node visual styles for frontend rendering."""
    return NODE_STYLES


def get_workflow_json_schema() -> Dict[str, Any]:
    """Return the JSON Schema definition for workflows."""
    return WORKFLOW_JSON_SCHEMA
