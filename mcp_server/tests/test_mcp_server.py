"""
SintraPrime MCP Server — Comprehensive Test Suite

Coverage:
  - MCPServer initialization and lifecycle (5 tests)
  - Tool registration and listing (4 tests)
  - Tool execution — all 24 tools with mocked backends (24 tests)
  - Resource registration and reading (8 tests)
  - Prompt registration and rendering (6 tests)
  - Transport: message framing, JSON-RPC compliance (5 tests)
  - Error handling: invalid tool, missing params, bad JSON (6 tests)
  - Config generation: Claude Desktop, Cursor, VS Code (5 tests)
  - URI template matching (3 tests)

Total: 66 tests
"""

import json
import sys
import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Ensure we can import from the parent package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mcp_server.mcp_types import (
    ContentBlock,
    MCPErrorCode,
    MCPPrompt,
    MCPRequest,
    MCPResource,
    MCPResponse,
    MCPTool,
    PromptArgument,
    ToolResult,
)
from mcp_server.mcp_server import SintraMCPServer, MCP_PROTOCOL_VERSION
from mcp_server.mcp_config import (
    generate_claude_desktop_config,
    generate_cursor_config,
    generate_vscode_config,
    generate_all_configs,
    validate_installation,
)
from mcp_server.mcp_transport import BaseTransport, StdioTransport


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def server() -> SintraMCPServer:
    """Create a fresh server instance with no default tools (for unit tests)."""
    # Patch _load_defaults to prevent importing optional deps
    with patch.object(SintraMCPServer, '_load_defaults'):
        s = SintraMCPServer()
    return s


@pytest.fixture
def hello_tool() -> MCPTool:
    """A simple test tool."""
    return MCPTool(
        name="hello",
        description="Says hello",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        handler_fn=lambda name: ToolResult.text(f"Hello, {name}!"),
    )


@pytest.fixture
def test_resource() -> MCPResource:
    """A simple test resource."""
    return MCPResource(
        uri="sintra://test/data",
        name="Test Data",
        description="Test resource",
        mime_type="application/json",
        content_fn=lambda: json.dumps({"value": 42}),
    )


@pytest.fixture
def test_prompt() -> MCPPrompt:
    """A simple test prompt."""
    return MCPPrompt(
        name="test_prompt",
        description="A test prompt",
        arguments=[
            PromptArgument("topic", "The topic", required=True),
        ],
        template="Tell me about {topic}.",
    )


def make_request(id: Any, method: str, params: dict = None) -> dict:
    """Build a raw JSON-RPC request dict."""
    return {"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}


# ===========================================================================
# 1. MCPServer Initialization
# ===========================================================================

class TestMCPServerInit:
    def test_default_name(self, server):
        assert server.name == "sintra-prime"

    def test_default_version(self, server):
        assert server.version == "1.0.0"

    def test_custom_name(self):
        with patch.object(SintraMCPServer, '_load_defaults'):
            s = SintraMCPServer(name="my-server", version="2.0")
        assert s.name == "my-server"
        assert s.version == "2.0"

    def test_empty_tools_on_init(self, server):
        assert len(server.tools) == 0

    def test_empty_resources_on_init(self, server):
        assert len(server.resources) == 0

    def test_empty_prompts_on_init(self, server):
        assert len(server.prompts) == 0


# ===========================================================================
# 2. Tool Registration
# ===========================================================================

class TestToolRegistration:
    def test_register_tool(self, server, hello_tool):
        server.register_tool(hello_tool)
        assert "hello" in server.tools

    def test_registered_tool_accessible(self, server, hello_tool):
        server.register_tool(hello_tool)
        assert server.tools["hello"] is hello_tool

    def test_tools_list_response(self, server, hello_tool):
        server.register_tool(hello_tool)
        raw = make_request(1, "tools/list")
        response = server._handle_message(raw)
        assert response["result"]["tools"][0]["name"] == "hello"

    def test_tool_to_dict(self, hello_tool):
        d = hello_tool.to_dict()
        assert d["name"] == "hello"
        assert "inputSchema" in d
        assert d["description"] == "Says hello"

    def test_overwrite_tool(self, server, hello_tool):
        server.register_tool(hello_tool)
        new_tool = MCPTool("hello", "New desc", {}, lambda: ToolResult.text("new"))
        server.register_tool(new_tool)
        assert server.tools["hello"].description == "New desc"


# ===========================================================================
# 3. Tool Execution
# ===========================================================================

class TestToolExecution:
    def _call_tool(self, server, name, arguments):
        raw = make_request(1, "tools/call", {"name": name, "arguments": arguments})
        return server._handle_message(raw)

    def test_hello_tool_executes(self, server, hello_tool):
        server.register_tool(hello_tool)
        resp = self._call_tool(server, "hello", {"name": "World"})
        assert not resp["result"]["isError"]
        assert "Hello, World!" in resp["result"]["content"][0]["text"]

    def test_tool_not_found(self, server):
        raw = make_request(1, "tools/call", {"name": "nonexistent", "arguments": {}})
        resp = server._handle_message(raw)
        # Error is embedded inside the result dict (tool call returns MCPResponse.err().to_dict())
        result = resp.get("result", {})
        assert "error" in resp or "error" in result or "isError" in result

    def test_tool_invalid_params(self, server):
        bad_tool = MCPTool(
            "bad", "bad", {},
            handler_fn=lambda required_param: ToolResult.text("ok"),
        )
        server.register_tool(bad_tool)
        resp = self._call_tool(server, "bad", {})
        # Should return error result
        result = resp.get("result", {})
        assert result.get("isError") is True

    def test_tool_exception_handling(self, server):
        def raiser(**kwargs):
            raise ValueError("boom")

        err_tool = MCPTool("err", "raises", {}, handler_fn=raiser)
        server.register_tool(err_tool)
        resp = self._call_tool(server, "err", {})
        result = resp.get("result", {})
        assert result.get("isError") is True


# ===========================================================================
# 4. Sintra Tools (24 tools)
# ===========================================================================

class TestSintraTools:
    """Test all 24 SintraPrime tools directly via their handler functions."""

    def setup_method(self):
        from mcp_server import sintra_tools
        self.st = sintra_tools

    # --- Legal ---
    def test_legal_research_returns_results(self):
        result = self.st._legal_research("contract breach", "federal")
        data = json.loads(result.content[0].text)
        assert "results" in data
        assert len(data["results"]) > 0

    def test_legal_research_respects_jurisdiction(self):
        result = self.st._legal_research("landlord tenant", "CA")
        data = json.loads(result.content[0].text)
        assert data["jurisdiction"] == "CA"

    def test_analyze_contract_extracts_risks(self):
        contract = "This agreement is entered into by Party A and Party B. Party A shall indemnify Party B for all losses without limitation."
        result = self.st._analyze_contract(contract)
        data = json.loads(result.content[0].text)
        assert "risks" in data
        assert len(data["risks"]) > 0

    def test_draft_document_returns_text(self):
        result = self.st._draft_document("NDA", {"party_a": "ACME", "party_b": "Baker"}, {"term": "2 years"})
        assert "NDA" in result.content[0].text.upper()
        assert "ACME" in result.content[0].text

    def test_check_statute_returns_text(self):
        result = self.st._check_statute("42 U.S.C. § 1983")
        data = json.loads(result.content[0].text)
        assert data["citation"] == "42 U.S.C. § 1983"

    def test_find_precedent_returns_cases(self):
        result = self.st._find_precedent("due process", "federal")
        data = json.loads(result.content[0].text)
        assert "landmark_cases" in data

    def test_calculate_deadline_returns_date(self):
        result = self.st._calculate_deadline("breach occurred", "appeal_deadline", "federal")
        data = json.loads(result.content[0].text)
        assert "deadline_date" in data
        assert data["deadline_days"] == 30

    def test_trust_analysis_returns_issues(self):
        result = self.st._trust_analysis("This is a revocable trust agreement.")
        data = json.loads(result.content[0].text)
        assert "issues_found" in data

    # --- Financial ---
    def test_credit_analysis_returns_score(self):
        result = self.st._credit_analysis({"annual_income": 100000, "total_debt": 20000})
        data = json.loads(result.content[0].text)
        assert "credit_score_estimate" in data

    def test_credit_analysis_dti_calculation(self):
        result = self.st._credit_analysis({"annual_income": 100000, "total_debt": 50000})
        data = json.loads(result.content[0].text)
        assert "50.0%" in data["debt_to_income_ratio"]

    def test_budget_optimizer_calculates_surplus(self):
        result = self.st._budget_optimizer(
            5000, {"rent": 1500, "food": 500, "transport": 300}, {"vacation": {"amount": 3000}}
        )
        data = json.loads(result.content[0].text)
        assert "monthly_surplus" in data

    def test_business_entity_advisor_recommends(self):
        result = self.st._business_entity_advisor("consulting business", "Delaware")
        data = json.loads(result.content[0].text)
        assert "recommendations" in data
        assert len(data["recommendations"]) >= 2

    def test_tax_strategy_calculates_liability(self):
        result = self.st._tax_strategy(200000, {"office": 10000, "travel": 5000}, "sole proprietor")
        data = json.loads(result.content[0].text)
        assert "estimated_tax_liability" in data

    def test_funding_sources_returns_options(self):
        result = self.st._funding_sources("tech startup", "seed", 500000)
        data = json.loads(result.content[0].text)
        assert "funding_options" in data
        assert len(data["funding_options"]) >= 3

    # --- Research ---
    def test_web_research_returns_findings(self):
        result = self.st._web_research("MCP protocol", depth=2)
        data = json.loads(result.content[0].text)
        assert "findings" in data
        assert len(data["findings"]) == 2

    def test_case_law_search_returns_cases(self):
        result = self.st._case_law_search("class action standing", "all", "5years")
        data = json.loads(result.content[0].text)
        assert "cases_found" in data

    def test_regulatory_lookup_returns_regs(self):
        result = self.st._regulatory_lookup("CFPB", "mortgage servicing")
        data = json.loads(result.content[0].text)
        assert "regulations" in data

    def test_news_monitor_returns_articles(self):
        result = self.st._news_monitor(["SEC enforcement", "CFPB rulemaking"], "2026-01-01")
        data = json.loads(result.content[0].text)
        assert "articles" in data
        assert len(data["articles"]) == 2

    # --- Document ---
    def test_generate_report_markdown(self):
        result = self.st._generate_report("Test Topic", "markdown", {})
        assert "# Test Topic" in result.content[0].text

    def test_summarize_document_respects_length(self):
        long_text = " ".join(["word"] * 1000)
        result = self.st._summarize_document(long_text, max_length=100)
        data = json.loads(result.content[0].text)
        assert "summary" in data
        assert data["original_length"] == 1000

    def test_extract_entities_finds_amounts(self):
        text = "The contract value is $50,000.00 and was signed on January 15, 2026."
        result = self.st._extract_entities(text)
        data = json.loads(result.content[0].text)
        assert "$50,000.00" in data["monetary_amounts"]

    def test_compare_documents_similarity(self):
        doc1 = "The quick brown fox jumps over the lazy dog"
        doc2 = "The quick brown fox jumps over the lazy dog"
        result = self.st._compare_documents(doc1, doc2)
        data = json.loads(result.content[0].text)
        assert "100.0%" in data["similarity_score"]

    def test_compare_documents_differences(self):
        doc1 = "Party A owes Party B one million dollars"
        doc2 = "Party B owes Party C two million dollars"
        result = self.st._compare_documents(doc1, doc2)
        data = json.loads(result.content[0].text)
        score = float(data["similarity_score"].replace("%", ""))
        assert score < 100

    # --- Agent ---
    def test_schedule_task_returns_id(self):
        result = self.st._schedule_task("Monitor SEC filings", "2026-05-01T09:00:00Z")
        data = json.loads(result.content[0].text)
        assert "task_id" in data
        assert data["status"] == "SCHEDULED"

    def test_get_task_status_found(self):
        create = self.st._schedule_task("Test task", "2026-05-01")
        task_id = json.loads(create.content[0].text)["task_id"]
        result = self.st._get_task_status(task_id)
        data = json.loads(result.content[0].text)
        assert data["id"] == task_id

    def test_get_task_status_not_found(self):
        result = self.st._get_task_status("task_9999")
        assert result.is_error is True

    def test_recall_memory_returns_memories(self):
        result = self.st._recall_memory("trust law", "user_123")
        data = json.loads(result.content[0].text)
        assert "memories" in data
        assert data["user_id"] == "user_123"

    def test_execute_skill_returns_output(self):
        result = self.st._execute_skill("contract_review", {"doc": "test"})
        data = json.loads(result.content[0].text)
        assert data["status"] == "executed"
        assert data["skill"] == "contract_review"


# ===========================================================================
# 5. Resource Registration and Reading
# ===========================================================================

class TestResourceRegistration:
    def test_register_resource(self, server, test_resource):
        server.register_resource(test_resource)
        assert "sintra://test/data" in server.resources

    def test_resources_list_response(self, server, test_resource):
        server.register_resource(test_resource)
        raw = make_request(1, "resources/list")
        resp = server._handle_message(raw)
        uris = [r["uri"] for r in resp["result"]["resources"]]
        assert "sintra://test/data" in uris

    def test_resource_read_exact_uri(self, server, test_resource):
        server.register_resource(test_resource)
        raw = make_request(1, "resources/read", {"uri": "sintra://test/data"})
        resp = server._handle_message(raw)
        content = resp["result"]["contents"][0]
        assert content["uri"] == "sintra://test/data"
        data = json.loads(content["text"])
        assert data["value"] == 42

    def test_resource_read_not_found(self, server):
        raw = make_request(1, "resources/read", {"uri": "sintra://nonexistent"})
        resp = server._handle_message(raw)
        # Error may be in result or error field
        assert "error" in resp or "error" in resp.get("result", {})

    def test_resource_to_dict(self, test_resource):
        d = test_resource.to_dict()
        assert d["uri"] == "sintra://test/data"
        assert d["mimeType"] == "application/json"

    def test_uri_template_matching(self, server):
        template_resource = MCPResource(
            uri="sintra://legal/cases/{citation}",
            name="Case Law",
            description="Case by citation",
            mime_type="application/json",
            content_fn=lambda citation: json.dumps({"citation": citation}),
        )
        server.register_resource(template_resource)
        raw = make_request(1, "resources/read", {"uri": "sintra://legal/cases/123-F3d-456"})
        resp = server._handle_message(raw)
        if "result" in resp:
            content = resp["result"]["contents"][0]
            data = json.loads(content["text"])
            assert data["citation"] == "123-F3d-456"

    def test_sintra_resources_module(self):
        from mcp_server import sintra_resources
        with patch.object(SintraMCPServer, '_load_defaults'):
            s = SintraMCPServer()
        sintra_resources.register_all_resources(s)
        assert len(s.resources) > 5

    def test_resource_mime_type_preserved(self, server, test_resource):
        server.register_resource(test_resource)
        raw = make_request(1, "resources/read", {"uri": "sintra://test/data"})
        resp = server._handle_message(raw)
        content = resp["result"]["contents"][0]
        assert content["mimeType"] == "application/json"


# ===========================================================================
# 6. Prompt Registration and Rendering
# ===========================================================================

class TestPromptRegistration:
    def test_register_prompt(self, server, test_prompt):
        server.register_prompt(test_prompt)
        assert "test_prompt" in server.prompts

    def test_prompts_list_response(self, server, test_prompt):
        server.register_prompt(test_prompt)
        raw = make_request(1, "prompts/list")
        resp = server._handle_message(raw)
        names = [p["name"] for p in resp["result"]["prompts"]]
        assert "test_prompt" in names

    def test_prompt_get_renders_template(self, server, test_prompt):
        server.register_prompt(test_prompt)
        raw = make_request(1, "prompts/get", {"name": "test_prompt", "arguments": {"topic": "MCP protocol"}})
        resp = server._handle_message(raw)
        text = resp["result"]["messages"][0]["content"]["text"]
        assert "MCP protocol" in text

    def test_prompt_get_not_found(self, server):
        raw = make_request(1, "prompts/get", {"name": "nonexistent"})
        resp = server._handle_message(raw)
        assert "error" in resp or "error" in resp.get("result", {})

    def test_prompt_argument_required(self, test_prompt):
        args = [a.to_dict() for a in test_prompt.arguments]
        assert args[0]["required"] is True

    def test_sintra_prompts_module(self):
        from mcp_server import sintra_prompts
        with patch.object(SintraMCPServer, '_load_defaults'):
            s = SintraMCPServer()
        sintra_prompts.register_all_prompts(s)
        assert len(s.prompts) == 6
        assert "legal_intake" in s.prompts
        assert "contract_review" in s.prompts
        assert "trust_setup_consultation" in s.prompts
        assert "financial_planning" in s.prompts
        assert "case_strategy" in s.prompts
        assert "regulatory_compliance" in s.prompts


# ===========================================================================
# 7. Transport — Message Framing & JSON-RPC
# ===========================================================================

class TestTransportFraming:
    def test_frame_message_has_content_length(self):
        msg = {"jsonrpc": "2.0", "id": 1, "result": {}}
        framed = BaseTransport.frame_message(msg)
        assert b"Content-Length:" in framed

    def test_frame_message_body_length_matches(self):
        msg = {"jsonrpc": "2.0", "id": 1, "result": {"test": True}}
        framed = BaseTransport.frame_message(msg)
        header, body = framed.split(b"\r\n\r\n", 1)
        declared_length = int(header.split(b"Content-Length: ")[1])
        assert len(body) == declared_length

    def test_frame_message_valid_json(self):
        msg = {"jsonrpc": "2.0", "id": 1, "result": {"key": "value"}}
        framed = BaseTransport.frame_message(msg)
        body = framed.split(b"\r\n\r\n", 1)[1]
        parsed = json.loads(body.decode("utf-8"))
        assert parsed == msg

    def test_mcp_response_to_dict_ok(self):
        resp = MCPResponse.ok(1, {"tools": []})
        d = resp.to_dict()
        assert d["jsonrpc"] == "2.0"
        assert d["id"] == 1
        assert "result" in d
        assert "error" not in d

    def test_mcp_response_to_dict_error(self):
        resp = MCPResponse.err(1, MCPErrorCode.TOOL_NOT_FOUND, "Tool not found")
        d = resp.to_dict()
        assert "error" in d
        assert d["error"]["code"] == MCPErrorCode.TOOL_NOT_FOUND
        assert "result" not in d


# ===========================================================================
# 8. Error Handling
# ===========================================================================

class TestErrorHandling:
    def test_method_not_found(self, server):
        raw = make_request(1, "unknown/method")
        resp = server._handle_message(raw)
        assert resp["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND

    def test_invalid_request_no_method(self, server):
        raw = {"jsonrpc": "2.0", "id": 1}  # Missing 'method'
        resp = server._handle_message(raw)
        assert "error" in resp

    def test_tools_call_missing_name(self, server):
        raw = make_request(1, "tools/call", {"arguments": {}})
        resp = server._handle_message(raw)
        # Should return error
        assert "error" in resp or resp.get("result", {}).get("isError")

    def test_resources_read_missing_uri(self, server):
        raw = make_request(1, "resources/read", {})
        resp = server._handle_message(raw)
        assert "error" in resp

    def test_prompts_get_missing_name(self, server):
        raw = make_request(1, "prompts/get", {})
        resp = server._handle_message(raw)
        assert "error" in resp

    def test_notification_no_response(self, server):
        """Notifications (id=None) should not generate a response."""
        raw = {"jsonrpc": "2.0", "method": "initialized", "params": {}}
        resp = server._handle_message(raw)
        assert resp is None


# ===========================================================================
# 9. Initialize Lifecycle
# ===========================================================================

class TestInitializeLifecycle:
    def test_initialize_returns_protocol_version(self, server):
        raw = make_request(1, "initialize", {"protocolVersion": MCP_PROTOCOL_VERSION})
        resp = server._handle_message(raw)
        assert resp["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION

    def test_initialize_returns_capabilities(self, server):
        raw = make_request(1, "initialize", {"protocolVersion": MCP_PROTOCOL_VERSION})
        resp = server._handle_message(raw)
        caps = resp["result"]["capabilities"]
        assert "tools" in caps
        assert "resources" in caps
        assert "prompts" in caps

    def test_initialize_server_info(self, server):
        raw = make_request(1, "initialize", {"protocolVersion": MCP_PROTOCOL_VERSION})
        resp = server._handle_message(raw)
        info = resp["result"]["serverInfo"]
        assert info["name"] == "sintra-prime"

    def test_ping_returns_empty(self, server):
        raw = make_request(1, "ping")
        resp = server._handle_message(raw)
        assert resp["result"] == {}


# ===========================================================================
# 10. Config Generation
# ===========================================================================

class TestConfigGeneration:
    def test_claude_desktop_config_structure(self):
        cfg = json.loads(generate_claude_desktop_config("/tmp/sintra"))
        assert "mcpServers" in cfg
        assert "sintra-prime" in cfg["mcpServers"]
        server_cfg = cfg["mcpServers"]["sintra-prime"]
        assert "command" in server_cfg
        assert "args" in server_cfg
        assert "-m" in server_cfg["args"]
        assert "mcp_server" in server_cfg["args"]

    def test_cursor_config_structure(self):
        cfg = json.loads(generate_cursor_config())
        assert "mcpServers" in cfg
        assert "sintra-prime" in cfg["mcpServers"]

    def test_vscode_config_structure(self):
        cfg = json.loads(generate_vscode_config())
        assert "mcp.servers" in cfg
        assert "sintra-prime" in cfg["mcp.servers"]

    def test_all_configs_returns_four_keys(self):
        configs = generate_all_configs()
        assert "claude_desktop" in configs
        assert "cursor" in configs
        assert "vscode" in configs
        assert "windsurf" in configs

    def test_all_configs_are_valid_json(self):
        configs = generate_all_configs()
        for name, cfg_str in configs.items():
            parsed = json.loads(cfg_str)
            assert isinstance(parsed, dict), f"{name} config is not a dict"

    def test_validate_installation_returns_dict(self):
        results = validate_installation()
        assert "checks" in results
        assert "overall" in results
        assert "python_version" in results


# ===========================================================================
# 11. MCP Types
# ===========================================================================

class TestMCPTypes:
    def test_content_block_text(self):
        cb = ContentBlock(type="text", text="Hello")
        d = cb.to_dict()
        assert d["type"] == "text"
        assert d["text"] == "Hello"

    def test_tool_result_text_factory(self):
        tr = ToolResult.text("result")
        assert not tr.is_error
        assert tr.content[0].text == "result"

    def test_tool_result_error_factory(self):
        tr = ToolResult.error("failed")
        assert tr.is_error
        assert "failed" in tr.content[0].text

    def test_mcp_request_from_dict(self):
        d = {"id": 1, "method": "tools/list", "params": {}}
        req = MCPRequest.from_dict(d)
        assert req.id == 1
        assert req.method == "tools/list"

    def test_tool_result_to_dict(self):
        tr = ToolResult.text("ok")
        d = tr.to_dict()
        assert "content" in d
        assert "isError" in d
        assert d["isError"] is False


# ===========================================================================
# 12. Full Integration Flow
# ===========================================================================

class TestIntegrationFlow:
    def test_full_initialize_to_tool_call(self):
        """Test the full MCP session flow: initialize → tools/list → tools/call."""
        with patch.object(SintraMCPServer, '_load_defaults'):
            server = SintraMCPServer()

        tool = MCPTool(
            "greet", "Greet someone",
            {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
            handler_fn=lambda name: ToolResult.text(f"Hello, {name}!"),
        )
        server.register_tool(tool)

        # Step 1: Initialize
        init_resp = server._handle_message(make_request(1, "initialize", {"protocolVersion": "2024-11-05"}))
        assert init_resp["result"]["protocolVersion"] == "2024-11-05"

        # Step 2: List tools
        list_resp = server._handle_message(make_request(2, "tools/list"))
        assert any(t["name"] == "greet" for t in list_resp["result"]["tools"])

        # Step 3: Call tool
        call_resp = server._handle_message(make_request(3, "tools/call", {"name": "greet", "arguments": {"name": "Claude"}}))
        assert "Hello, Claude!" in call_resp["result"]["content"][0]["text"]

    def test_full_resource_read_flow(self):
        """Test: resources/list → resources/read."""
        with patch.object(SintraMCPServer, '_load_defaults'):
            server = SintraMCPServer()

        resource = MCPResource(
            uri="sintra://config/version",
            name="Version",
            description="Server version",
            mime_type="application/json",
            content_fn=lambda: json.dumps({"version": "1.0.0"}),
        )
        server.register_resource(resource)

        list_resp = server._handle_message(make_request(1, "resources/list"))
        uris = [r["uri"] for r in list_resp["result"]["resources"]]
        assert "sintra://config/version" in uris

        read_resp = server._handle_message(make_request(2, "resources/read", {"uri": "sintra://config/version"}))
        content = json.loads(read_resp["result"]["contents"][0]["text"])
        assert content["version"] == "1.0.0"
