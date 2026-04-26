"""
SintraPrime-Unified Workflow Builder Tests
70+ tests covering workflow engine, schema, and API components.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List

import pytest


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def simple_graph():
    """Create a minimal valid workflow graph (START → ACTION → END)."""
    from workflow_builder.workflow_engine import (
        EdgeCondition, NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
    )
    graph = WorkflowGraph("test-001", "Test Workflow", "A simple test workflow")
    start = WorkflowNode.create(NodeType.START, "Start Node")
    action = WorkflowNode.create(NodeType.ACTION, "Do Something")
    end = WorkflowNode.create(NodeType.END, "End Node")
    graph.add_node(start)
    graph.add_node(action)
    graph.add_node(end)
    graph.add_edge(WorkflowEdge.create(start.id, action.id))
    graph.add_edge(WorkflowEdge.create(action.id, end.id))
    return graph, start, action, end


@pytest.fixture
def complex_graph():
    """Create a complex workflow with DECISION and PARALLEL nodes."""
    from workflow_builder.workflow_engine import (
        EdgeCondition, NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
    )
    g = WorkflowGraph("test-complex", "Complex Workflow")
    nodes = {
        "start": WorkflowNode.create(NodeType.START, "Start"),
        "action1": WorkflowNode.create(NodeType.ACTION, "Step 1"),
        "decision": WorkflowNode.create(NodeType.DECISION, "Check Condition"),
        "yes_branch": WorkflowNode.create(NodeType.ACTION, "Yes Path"),
        "no_branch": WorkflowNode.create(NodeType.ACTION, "No Path"),
        "merge": WorkflowNode.create(NodeType.ACTION, "Merge"),
        "end": WorkflowNode.create(NodeType.END, "End"),
    }
    for node in nodes.values():
        g.add_node(node)
    g.add_edge(WorkflowEdge.create(nodes["start"].id, nodes["action1"].id))
    g.add_edge(WorkflowEdge.create(nodes["action1"].id, nodes["decision"].id))
    g.add_edge(WorkflowEdge.create(nodes["decision"].id, nodes["yes_branch"].id, EdgeCondition.ON_YES))
    g.add_edge(WorkflowEdge.create(nodes["decision"].id, nodes["no_branch"].id, EdgeCondition.ON_NO))
    g.add_edge(WorkflowEdge.create(nodes["yes_branch"].id, nodes["merge"].id))
    g.add_edge(WorkflowEdge.create(nodes["no_branch"].id, nodes["merge"].id))
    g.add_edge(WorkflowEdge.create(nodes["merge"].id, nodes["end"].id))
    return g, nodes


# ===========================================================================
# WorkflowNode Tests
# ===========================================================================

class TestWorkflowNode:
    def test_node_creation_with_factory(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowNode
        node = WorkflowNode.create(NodeType.ACTION, "My Action")
        assert node.label == "My Action"
        assert node.node_type == NodeType.ACTION
        assert isinstance(node.id, str) and len(node.id) > 0

    def test_node_id_is_unique(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowNode
        n1 = WorkflowNode.create(NodeType.ACTION, "Node 1")
        n2 = WorkflowNode.create(NodeType.ACTION, "Node 2")
        assert n1.id != n2.id

    def test_node_to_dict(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowNode
        node = WorkflowNode.create(NodeType.DECISION, "Branch", "A decision node", {"key": "val"})
        d = node.to_dict()
        assert d["label"] == "Branch"
        assert d["node_type"] == "DECISION"
        assert d["description"] == "A decision node"
        assert d["config"] == {"key": "val"}

    def test_node_from_dict(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowNode
        node = WorkflowNode.create(NodeType.AGENT_CALL, "AI Agent", "Calls AI")
        d = node.to_dict()
        restored = WorkflowNode.from_dict(d)
        assert restored.id == node.id
        assert restored.label == node.label
        assert restored.node_type == NodeType.AGENT_CALL

    def test_all_node_types_creatable(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowNode
        for nt in NodeType:
            node = WorkflowNode.create(nt, f"Node {nt.value}")
            assert node.node_type == nt

    def test_node_default_position(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowNode
        node = WorkflowNode.create(NodeType.ACTION, "Test")
        assert node.position == {"x": 0.0, "y": 0.0}

    def test_node_custom_position(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowNode
        node = WorkflowNode.create(NodeType.ACTION, "Test", position={"x": 100.0, "y": 200.0})
        assert node.position["x"] == 100.0
        assert node.position["y"] == 200.0

    def test_node_config_stored(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowNode
        cfg = {"timeout": 30, "agent_id": "agt_001"}
        node = WorkflowNode.create(NodeType.AGENT_CALL, "Call Agent", config=cfg)
        assert node.config == cfg

    def test_node_retry_count(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowNode
        node = WorkflowNode.create(NodeType.ACTION, "Retryable")
        node.retry_count = 3
        d = node.to_dict()
        restored = WorkflowNode.from_dict(d)
        assert restored.retry_count == 3


# ===========================================================================
# WorkflowEdge Tests
# ===========================================================================

class TestWorkflowEdge:
    def test_edge_creation(self):
        from workflow_builder.workflow_engine import EdgeCondition, WorkflowEdge
        src_id = str(uuid.uuid4())
        tgt_id = str(uuid.uuid4())
        edge = WorkflowEdge.create(src_id, tgt_id)
        assert edge.source_id == src_id
        assert edge.target_id == tgt_id
        assert edge.condition == EdgeCondition.ALWAYS

    def test_edge_with_condition(self):
        from workflow_builder.workflow_engine import EdgeCondition, WorkflowEdge
        edge = WorkflowEdge.create("a", "b", EdgeCondition.ON_YES, "Yes path")
        assert edge.condition == EdgeCondition.ON_YES
        assert edge.label == "Yes path"

    def test_edge_to_dict(self):
        from workflow_builder.workflow_engine import EdgeCondition, WorkflowEdge
        edge = WorkflowEdge.create("src", "tgt", EdgeCondition.ON_SUCCESS)
        d = edge.to_dict()
        assert d["source_id"] == "src"
        assert d["target_id"] == "tgt"
        assert d["condition"] == "on_success"

    def test_edge_from_dict(self):
        from workflow_builder.workflow_engine import EdgeCondition, WorkflowEdge
        edge = WorkflowEdge.create("src", "tgt", EdgeCondition.ON_FAILURE)
        d = edge.to_dict()
        restored = WorkflowEdge.from_dict(d)
        assert restored.source_id == "src"
        assert restored.condition == EdgeCondition.ON_FAILURE

    def test_all_edge_conditions(self):
        from workflow_builder.workflow_engine import EdgeCondition, WorkflowEdge
        for cond in EdgeCondition:
            edge = WorkflowEdge.create("a", "b", cond)
            assert edge.condition == cond


# ===========================================================================
# WorkflowGraph Tests
# ===========================================================================

class TestWorkflowGraph:
    def test_create_graph(self):
        from workflow_builder.workflow_engine import WorkflowGraph
        g = WorkflowGraph("wf-001", "My Workflow")
        assert g.workflow_id == "wf-001"
        assert g.name == "My Workflow"
        assert len(g.nodes) == 0
        assert len(g.edges) == 0

    def test_add_and_get_node(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowGraph, WorkflowNode
        g = WorkflowGraph("wf-002", "Test")
        node = WorkflowNode.create(NodeType.ACTION, "My Node")
        g.add_node(node)
        assert len(g.nodes) == 1
        retrieved = g.get_node(node.id)
        assert retrieved.label == "My Node"

    def test_add_duplicate_node_raises(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowGraph, WorkflowNode
        g = WorkflowGraph("wf-003", "Test")
        node = WorkflowNode.create(NodeType.ACTION, "Node")
        g.add_node(node)
        with pytest.raises(ValueError):
            g.add_node(node)

    def test_remove_node(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowGraph, WorkflowNode
        g = WorkflowGraph("wf-004", "Test")
        node = WorkflowNode.create(NodeType.ACTION, "Node")
        g.add_node(node)
        g.remove_node(node.id)
        assert len(g.nodes) == 0

    def test_remove_node_removes_edges(self, simple_graph):
        g, start, action, end = simple_graph
        assert len(g.edges) == 2
        g.remove_node(action.id)
        assert len(g.edges) == 0

    def test_remove_nonexistent_node_raises(self):
        from workflow_builder.workflow_engine import WorkflowGraph
        g = WorkflowGraph("wf-005", "Test")
        with pytest.raises(KeyError):
            g.remove_node("nonexistent")

    def test_add_edge_requires_existing_nodes(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
        g = WorkflowGraph("wf-006", "Test")
        node = WorkflowNode.create(NodeType.ACTION, "Node")
        g.add_node(node)
        edge = WorkflowEdge.create(node.id, "nonexistent")
        with pytest.raises(KeyError):
            g.add_edge(edge)

    def test_remove_edge(self, simple_graph):
        g, start, action, end = simple_graph
        edge_id = list(g.edges.keys())[0]
        g.remove_edge(edge_id)
        assert edge_id not in g.edges

    def test_get_edges_from(self, simple_graph):
        g, start, action, end = simple_graph
        edges_from_start = g.get_edges_from(start.id)
        assert len(edges_from_start) == 1
        assert edges_from_start[0].target_id == action.id

    def test_get_edges_to(self, simple_graph):
        g, start, action, end = simple_graph
        edges_to_end = g.get_edges_to(end.id)
        assert len(edges_to_end) == 1
        assert edges_to_end[0].source_id == action.id

    def test_get_start_nodes(self, simple_graph):
        g, start, action, end = simple_graph
        start_nodes = g.get_start_nodes()
        assert len(start_nodes) == 1
        assert start_nodes[0].id == start.id

    def test_get_end_nodes(self, simple_graph):
        g, start, action, end = simple_graph
        end_nodes = g.get_end_nodes()
        assert len(end_nodes) == 1
        assert end_nodes[0].id == end.id

    def test_no_cycle_in_valid_graph(self, simple_graph):
        g, start, action, end = simple_graph
        assert not g.has_cycle()

    def test_cycle_detection(self):
        from workflow_builder.workflow_engine import (
            NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
        )
        g = WorkflowGraph("wf-cycle", "Cycle Test")
        a = WorkflowNode.create(NodeType.ACTION, "A")
        b = WorkflowNode.create(NodeType.ACTION, "B")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(WorkflowEdge.create(a.id, b.id))
        g.add_edge(WorkflowEdge.create(b.id, a.id))
        assert g.has_cycle()

    def test_topological_sort(self, simple_graph):
        g, start, action, end = simple_graph
        order = g.topological_sort()
        assert len(order) == 3
        assert order.index(start.id) < order.index(action.id)
        assert order.index(action.id) < order.index(end.id)

    def test_topological_sort_raises_on_cycle(self):
        from workflow_builder.workflow_engine import (
            NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
        )
        g = WorkflowGraph("wf-cycle2", "Cycle")
        a = WorkflowNode.create(NodeType.ACTION, "A")
        b = WorkflowNode.create(NodeType.ACTION, "B")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(WorkflowEdge.create(a.id, b.id))
        g.add_edge(WorkflowEdge.create(b.id, a.id))
        with pytest.raises(ValueError):
            g.topological_sort()

    def test_validate_valid_graph(self, simple_graph):
        g, *_ = simple_graph
        errors = g.validate()
        assert errors == []

    def test_validate_no_nodes(self):
        from workflow_builder.workflow_engine import WorkflowGraph
        g = WorkflowGraph("empty", "Empty")
        errors = g.validate()
        assert any("no nodes" in e.lower() for e in errors)

    def test_validate_missing_start(self):
        from workflow_builder.workflow_engine import (
            NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
        )
        g = WorkflowGraph("no-start", "No Start")
        action = WorkflowNode.create(NodeType.ACTION, "Action")
        end = WorkflowNode.create(NodeType.END, "End")
        g.add_node(action)
        g.add_node(end)
        g.add_edge(WorkflowEdge.create(action.id, end.id))
        errors = g.validate()
        assert any("start" in e.lower() for e in errors)

    def test_validate_missing_end(self):
        from workflow_builder.workflow_engine import (
            NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
        )
        g = WorkflowGraph("no-end", "No End")
        start = WorkflowNode.create(NodeType.START, "Start")
        action = WorkflowNode.create(NodeType.ACTION, "Action")
        g.add_node(start)
        g.add_node(action)
        g.add_edge(WorkflowEdge.create(start.id, action.id))
        errors = g.validate()
        assert any("end" in e.lower() for e in errors)

    def test_graph_statistics(self, simple_graph):
        g, *_ = simple_graph
        stats = g.get_statistics()
        assert stats["total_nodes"] == 3
        assert stats["total_edges"] == 2
        assert not stats["has_cycle"]

    def test_graph_to_dict(self, simple_graph):
        g, *_ = simple_graph
        d = g.to_dict()
        assert d["workflow_id"] == "test-001"
        assert d["name"] == "Test Workflow"
        assert len(d["nodes"]) == 3
        assert len(d["edges"]) == 2

    def test_graph_from_dict(self, simple_graph):
        from workflow_builder.workflow_engine import WorkflowGraph
        g, *_ = simple_graph
        d = g.to_dict()
        restored = WorkflowGraph.from_dict(d)
        assert restored.workflow_id == g.workflow_id
        assert len(restored.nodes) == 3
        assert len(restored.edges) == 2

    def test_update_node(self, simple_graph):
        from workflow_builder.workflow_engine import WorkflowGraph
        g, start, action, end = simple_graph
        g.update_node(action.id, {"label": "Updated Label"})
        assert g.get_node(action.id).label == "Updated Label"

    def test_complex_graph_valid(self, complex_graph):
        g, nodes = complex_graph
        errors = g.validate()
        assert errors == []

    def test_complex_graph_no_cycle(self, complex_graph):
        g, nodes = complex_graph
        assert not g.has_cycle()

    def test_complex_topological_sort(self, complex_graph):
        g, nodes = complex_graph
        order = g.topological_sort()
        assert order.index(nodes["start"].id) < order.index(nodes["decision"].id)
        assert order.index(nodes["decision"].id) < order.index(nodes["yes_branch"].id)


# ===========================================================================
# WorkflowSerializer Tests
# ===========================================================================

class TestWorkflowSerializer:
    def test_serialize_to_json(self, simple_graph):
        from workflow_builder.workflow_engine import WorkflowSerializer
        g, *_ = simple_graph
        json_str = WorkflowSerializer.to_json(g)
        data = json.loads(json_str)
        assert data["workflow_id"] == g.workflow_id
        assert len(data["nodes"]) == 3

    def test_deserialize_from_json(self, simple_graph):
        from workflow_builder.workflow_engine import WorkflowSerializer
        g, *_ = simple_graph
        json_str = WorkflowSerializer.to_json(g)
        restored = WorkflowSerializer.from_json(json_str)
        assert restored.workflow_id == g.workflow_id
        assert len(restored.nodes) == 3
        assert len(restored.edges) == 2

    def test_round_trip_preserves_data(self, simple_graph):
        from workflow_builder.workflow_engine import WorkflowSerializer
        g, start, action, end = simple_graph
        json_str = WorkflowSerializer.to_json(g)
        restored = WorkflowSerializer.from_json(json_str)
        assert start.id in restored.nodes
        assert restored.nodes[start.id].label == "Start Node"

    def test_save_and_load_file(self, simple_graph, tmp_path):
        from workflow_builder.workflow_engine import WorkflowSerializer
        g, *_ = simple_graph
        filepath = str(tmp_path / "test_workflow.json")
        WorkflowSerializer.save_to_file(g, filepath)
        loaded = WorkflowSerializer.load_from_file(filepath)
        assert loaded.workflow_id == g.workflow_id
        assert len(loaded.nodes) == 3


# ===========================================================================
# WorkflowTemplateRegistry Tests
# ===========================================================================

class TestWorkflowTemplateRegistry:
    def test_templates_registered(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        templates = WorkflowTemplateRegistry.list_templates()
        assert len(templates) >= 20

    def test_get_trust_template(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        template = WorkflowTemplateRegistry.get("tpl_trust_creation")
        assert template is not None
        assert "Trust" in template.name

    def test_get_estate_template(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        template = WorkflowTemplateRegistry.get("tpl_estate_planning")
        assert template is not None

    def test_get_debt_template(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        template = WorkflowTemplateRegistry.get("tpl_debt_negotiation")
        assert template is not None

    def test_get_business_template(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        template = WorkflowTemplateRegistry.get("tpl_business_formation")
        assert template is not None

    def test_get_court_template(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        template = WorkflowTemplateRegistry.get("tpl_court_filing")
        assert template is not None

    def test_get_contract_template(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        template = WorkflowTemplateRegistry.get("tpl_contract_review")
        assert template is not None

    def test_get_nonexistent_template(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        result = WorkflowTemplateRegistry.get("nonexistent_template")
        assert result is None

    def test_all_templates_have_start_and_end(self):
        from workflow_builder.workflow_engine import NodeType, WorkflowTemplateRegistry
        templates = WorkflowTemplateRegistry.list_templates()
        for t in templates:
            template = WorkflowTemplateRegistry.get(t["id"])
            start_nodes = [n for n in template.nodes.values() if n.node_type == NodeType.START]
            end_nodes = [n for n in template.nodes.values() if n.node_type == NodeType.END]
            assert len(start_nodes) >= 1, f"{t['id']} missing START node"
            assert len(end_nodes) >= 1, f"{t['id']} missing END node"

    def test_all_templates_are_valid_dags(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        templates = WorkflowTemplateRegistry.list_templates()
        for t in templates:
            template = WorkflowTemplateRegistry.get(t["id"])
            assert not template.has_cycle(), f"{t['id']} has a cycle"

    def test_templates_have_tags(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        templates = WorkflowTemplateRegistry.list_templates()
        for t in templates:
            assert len(t["tags"]) > 0, f"{t['id']} has no tags"

    def test_list_templates_returns_metadata(self):
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        templates = WorkflowTemplateRegistry.list_templates()
        for t in templates:
            assert "id" in t
            assert "name" in t
            assert "description" in t


# ===========================================================================
# Convenience Functions Tests
# ===========================================================================

class TestConvenienceFunctions:
    def test_create_workflow(self):
        from workflow_builder.workflow_engine import create_workflow
        wf = create_workflow("My Legal Workflow", "A test")
        assert wf.name == "My Legal Workflow"
        assert wf.description == "A test"
        assert len(wf.workflow_id) > 0

    def test_get_template(self):
        from workflow_builder.workflow_engine import get_template
        t = get_template("tpl_trust_creation")
        assert t is not None

    def test_list_templates(self):
        from workflow_builder.workflow_engine import list_templates
        templates = list_templates()
        assert len(templates) >= 20


# ===========================================================================
# WorkflowSchema Tests
# ===========================================================================

class TestWorkflowSchema:
    def test_export_to_react_flow(self, simple_graph):
        from workflow_builder.workflow_schema import ReactFlowConverter
        g, *_ = simple_graph
        rf = ReactFlowConverter.graph_to_react_flow(g)
        assert rf["id"] == g.workflow_id
        assert rf["name"] == g.name
        assert len(rf["nodes"]) == 3
        assert len(rf["edges"]) == 2

    def test_react_flow_node_format(self, simple_graph):
        from workflow_builder.workflow_schema import ReactFlowConverter
        g, start, *_ = simple_graph
        rf = ReactFlowConverter.graph_to_react_flow(g)
        rf_node = rf["nodes"][0]
        assert "id" in rf_node
        assert "type" in rf_node
        assert "position" in rf_node
        assert "data" in rf_node
        assert "label" in rf_node["data"]

    def test_react_flow_edge_format(self, simple_graph):
        from workflow_builder.workflow_schema import ReactFlowConverter
        g, *_ = simple_graph
        rf = ReactFlowConverter.graph_to_react_flow(g)
        rf_edge = rf["edges"][0]
        assert "id" in rf_edge
        assert "source" in rf_edge
        assert "target" in rf_edge

    def test_import_from_react_flow(self, simple_graph):
        from workflow_builder.workflow_schema import ReactFlowConverter
        g, *_ = simple_graph
        rf = ReactFlowConverter.graph_to_react_flow(g)
        restored = ReactFlowConverter.react_flow_to_graph(rf)
        assert restored.workflow_id == g.workflow_id
        assert len(restored.nodes) == 3

    def test_round_trip_react_flow(self, simple_graph):
        from workflow_builder.workflow_schema import ReactFlowConverter
        g, start, action, end = simple_graph
        rf = ReactFlowConverter.graph_to_react_flow(g)
        restored = ReactFlowConverter.react_flow_to_graph(rf)
        assert start.id in restored.nodes
        assert action.id in restored.nodes
        assert end.id in restored.nodes

    def test_validate_valid_react_flow(self, simple_graph):
        from workflow_builder.workflow_schema import ReactFlowConverter, WorkflowSchemaValidator
        g, *_ = simple_graph
        rf = ReactFlowConverter.graph_to_react_flow(g)
        errors = WorkflowSchemaValidator.validate_react_flow_json(rf)
        assert errors == []

    def test_validate_missing_required_field(self):
        from workflow_builder.workflow_schema import WorkflowSchemaValidator
        data = {"name": "No ID or nodes"}
        errors = WorkflowSchemaValidator.validate_react_flow_json(data)
        assert len(errors) > 0

    def test_validate_invalid_node_type(self):
        from workflow_builder.workflow_schema import WorkflowSchemaValidator
        data = {
            "id": "test", "name": "Test",
            "nodes": [{"id": "n1", "type": "INVALID_TYPE", "position": {"x": 0, "y": 0}, "data": {"label": "X"}}],
            "edges": []
        }
        errors = WorkflowSchemaValidator.validate_react_flow_json(data)
        assert any("invalid type" in e.lower() for e in errors)

    def test_get_json_schema(self):
        from workflow_builder.workflow_schema import WorkflowSchemaValidator
        schema = WorkflowSchemaValidator.get_json_schema()
        assert "$schema" in schema
        assert "properties" in schema

    def test_node_styles_available(self):
        from workflow_builder.workflow_schema import get_node_styles
        styles = get_node_styles()
        assert "START" in styles
        assert "END" in styles
        assert "ACTION" in styles

    def test_export_to_python_code(self, simple_graph):
        from workflow_builder.workflow_schema import WorkflowCodeGenerator
        g, *_ = simple_graph
        code = WorkflowCodeGenerator.generate(g)
        assert "async def" in code
        assert "import asyncio" in code
        assert "async def run_" in code

    def test_convenience_export_react_flow(self, simple_graph):
        from workflow_builder.workflow_schema import export_workflow_to_react_flow
        g, *_ = simple_graph
        json_str = export_workflow_to_react_flow(g)
        data = json.loads(json_str)
        assert data["name"] == g.name

    def test_convenience_import_react_flow(self, simple_graph):
        from workflow_builder.workflow_schema import (
            export_workflow_to_react_flow, import_workflow_from_react_flow
        )
        g, *_ = simple_graph
        json_str = export_workflow_to_react_flow(g)
        restored = import_workflow_from_react_flow(json_str)
        assert restored.workflow_id == g.workflow_id

    def test_import_invalid_json_raises(self):
        from workflow_builder.workflow_schema import import_workflow_from_react_flow
        with pytest.raises((ValueError, Exception)):
            import_workflow_from_react_flow('{"invalid": true}')


# ===========================================================================
# ANSI / TUI Tests
# ===========================================================================

class TestWebTUI:
    def test_ansi_constants_exist(self):
        from workflow_builder.web_tui import ANSI
        assert ANSI.RESET
        assert ANSI.BOLD
        assert ANSI.FG_GREEN
        assert ANSI.BG_BLUE
        assert ANSI.CLEAR_SCREEN

    def test_colorize_function(self):
        from workflow_builder.web_tui import ANSI, colorize
        result = colorize("hello", ANSI.FG_GREEN)
        assert "hello" in result
        assert ANSI.RESET in result

    def test_colorize_bold(self):
        from workflow_builder.web_tui import ANSI, colorize
        result = colorize("bold text", bold=True)
        assert ANSI.BOLD in result

    def test_colorize_no_codes(self):
        from workflow_builder.web_tui import colorize
        result = colorize("plain")
        assert result == "plain"

    def test_commands_registered(self):
        from workflow_builder.web_tui import COMMANDS
        assert "help" in COMMANDS
        assert "workflow" in COMMANDS
        assert "agent" in COMMANDS
        assert "logs" in COMMANDS
        assert "status" in COMMANDS

    def test_commands_have_descriptions(self):
        from workflow_builder.web_tui import COMMANDS
        for name, info in COMMANDS.items():
            assert "description" in info
            assert len(info["description"]) > 0

    @pytest.mark.asyncio
    async def test_terminal_session_creation(self):
        from workflow_builder.web_tui import TerminalSession
        messages = []
        async def send_fn(text):
            messages.append(text)

        session = TerminalSession("test-session", send_fn)
        assert session.session_id == "test-session"
        assert session.running is True

    @pytest.mark.asyncio
    async def test_terminal_session_write(self):
        from workflow_builder.web_tui import TerminalSession
        messages = []
        async def send_fn(text):
            messages.append(text)

        session = TerminalSession("s1", send_fn)
        await session.write("Hello World")
        assert "Hello World" in messages

    @pytest.mark.asyncio
    async def test_terminal_session_history(self):
        from workflow_builder.web_tui import TerminalSession
        async def send_fn(text): pass
        session = TerminalSession("s2", send_fn)
        session.add_to_history("workflow list")
        session.add_to_history("status")
        assert "workflow list" in session.history
        assert "status" in session.history

    def test_tab_completion(self):
        from workflow_builder.web_tui import TerminalSession
        import asyncio
        async def send_fn(text): pass
        session = TerminalSession("s3", send_fn)
        completions = session.get_tab_completions("wor")
        assert "workflow" in completions

    def test_tab_completion_empty(self):
        from workflow_builder.web_tui import TerminalSession
        async def send_fn(text): pass
        session = TerminalSession("s4", send_fn)
        completions = session.get_tab_completions("zzz")
        assert completions == []

    @pytest.mark.asyncio
    async def test_help_command(self):
        from workflow_builder.web_tui import COMMANDS, TerminalSession
        messages = []
        async def send_fn(text):
            messages.append(text)
        session = TerminalSession("s5", send_fn)
        await COMMANDS["help"]["fn"](session, [])
        combined = "".join(messages)
        assert "workflow" in combined.lower()

    @pytest.mark.asyncio
    async def test_version_command(self):
        from workflow_builder.web_tui import COMMANDS, TerminalSession
        messages = []
        async def send_fn(text):
            messages.append(text)
        session = TerminalSession("s6", send_fn)
        await COMMANDS["version"]["fn"](session, [])
        combined = "".join(messages)
        assert "SintraPrime" in combined

    @pytest.mark.asyncio
    async def test_echo_command(self):
        from workflow_builder.web_tui import COMMANDS, TerminalSession
        messages = []
        async def send_fn(text):
            messages.append(text)
        session = TerminalSession("s7", send_fn)
        await COMMANDS["echo"]["fn"](session, ["Hello", "World"])
        combined = "".join(messages)
        assert "Hello World" in combined

    @pytest.mark.asyncio
    async def test_exit_command(self):
        from workflow_builder.web_tui import COMMANDS, TerminalSession
        async def send_fn(text): pass
        session = TerminalSession("s8", send_fn)
        assert session.running is True
        await COMMANDS["exit"]["fn"](session, [])
        assert session.running is False


# ===========================================================================
# Additional edge case tests
# ===========================================================================

class TestEdgeCases:
    def test_workflow_with_many_nodes(self):
        from workflow_builder.workflow_engine import (
            EdgeCondition, NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
        )
        g = WorkflowGraph("large", "Large Workflow")
        prev = WorkflowNode.create(NodeType.START, "Start")
        g.add_node(prev)
        for i in range(20):
            node = WorkflowNode.create(NodeType.ACTION, f"Step {i+1}")
            g.add_node(node)
            g.add_edge(WorkflowEdge.create(prev.id, node.id))
            prev = node
        end = WorkflowNode.create(NodeType.END, "End")
        g.add_node(end)
        g.add_edge(WorkflowEdge.create(prev.id, end.id))
        assert not g.has_cycle()
        assert len(g.nodes) == 22

    def test_parallel_branches_merge(self):
        from workflow_builder.workflow_engine import (
            NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
        )
        g = WorkflowGraph("parallel", "Parallel Workflow")
        start = WorkflowNode.create(NodeType.START, "Start")
        split = WorkflowNode.create(NodeType.PARALLEL, "Split")
        b1 = WorkflowNode.create(NodeType.ACTION, "Branch 1")
        b2 = WorkflowNode.create(NodeType.ACTION, "Branch 2")
        b3 = WorkflowNode.create(NodeType.ACTION, "Branch 3")
        join = WorkflowNode.create(NodeType.ACTION, "Join")
        end = WorkflowNode.create(NodeType.END, "End")
        for n in [start, split, b1, b2, b3, join, end]:
            g.add_node(n)
        g.add_edge(WorkflowEdge.create(start.id, split.id))
        g.add_edge(WorkflowEdge.create(split.id, b1.id))
        g.add_edge(WorkflowEdge.create(split.id, b2.id))
        g.add_edge(WorkflowEdge.create(split.id, b3.id))
        g.add_edge(WorkflowEdge.create(b1.id, join.id))
        g.add_edge(WorkflowEdge.create(b2.id, join.id))
        g.add_edge(WorkflowEdge.create(b3.id, join.id))
        g.add_edge(WorkflowEdge.create(join.id, end.id))
        assert not g.has_cycle()
        errors = g.validate()
        assert errors == []

    def test_workflow_serialization_with_metadata(self):
        from workflow_builder.workflow_engine import (
            NodeType, WorkflowGraph, WorkflowNode, WorkflowSerializer
        )
        g = WorkflowGraph("meta-test", "Metadata Test")
        g.tags = ["legal", "estate"]
        g.author = "Test Author"
        g.version = "2.0.0"
        node = WorkflowNode.create(NodeType.ACTION, "Node", config={"key": "value"})
        node.metadata = {"priority": "high"}
        g.add_node(node)
        json_str = WorkflowSerializer.to_json(g)
        restored = WorkflowSerializer.from_json(json_str)
        assert restored.tags == ["legal", "estate"]
        assert restored.author == "Test Author"
        assert restored.nodes[node.id].config == {"key": "value"}

    def test_multiple_start_nodes_invalid(self):
        from workflow_builder.workflow_engine import (
            NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
        )
        g = WorkflowGraph("multi-start", "Multi Start")
        s1 = WorkflowNode.create(NodeType.START, "Start 1")
        s2 = WorkflowNode.create(NodeType.START, "Start 2")
        end = WorkflowNode.create(NodeType.END, "End")
        g.add_node(s1)
        g.add_node(s2)
        g.add_node(end)
        g.add_edge(WorkflowEdge.create(s1.id, end.id))
        g.add_edge(WorkflowEdge.create(s2.id, end.id))
        errors = g.validate()
        assert any("start" in e.lower() for e in errors)

    def test_human_review_node_workflow(self):
        from workflow_builder.workflow_engine import (
            NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
        )
        g = WorkflowGraph("hr-test", "Human Review Test")
        start = WorkflowNode.create(NodeType.START, "Start")
        hr = WorkflowNode.create(NodeType.HUMAN_REVIEW, "Attorney Review",
                                  config={"assignee": "attorney@firm.com"})
        end = WorkflowNode.create(NodeType.END, "End")
        g.add_node(start)
        g.add_node(hr)
        g.add_node(end)
        g.add_edge(WorkflowEdge.create(start.id, hr.id))
        g.add_edge(WorkflowEdge.create(hr.id, end.id))
        errors = g.validate()
        assert errors == []
        assert g.nodes[hr.id].config["assignee"] == "attorney@firm.com"

    def test_wait_node_with_timeout(self):
        from workflow_builder.workflow_engine import (
            NodeType, WorkflowEdge, WorkflowGraph, WorkflowNode
        )
        g = WorkflowGraph("wait-test", "Wait Test")
        start = WorkflowNode.create(NodeType.START, "Start")
        wait = WorkflowNode.create(NodeType.WAIT, "Waiting Period")
        wait.timeout_seconds = 3600
        end = WorkflowNode.create(NodeType.END, "End")
        for n in [start, wait, end]:
            g.add_node(n)
        g.add_edge(WorkflowEdge.create(start.id, wait.id))
        g.add_edge(WorkflowEdge.create(wait.id, end.id))
        d = g.to_dict()
        restored = WorkflowGraph.from_dict(d)
        assert restored.nodes[wait.id].timeout_seconds == 3600
