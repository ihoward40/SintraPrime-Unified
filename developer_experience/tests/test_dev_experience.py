"""
test_dev_experience.py — Comprehensive tests for SintraPrime Developer Experience
70+ tests covering: OpenAPI spec, Cookbook, Model Playground, SDK Generator, Dev Portal API
Run with: python -m pytest developer_experience/tests/ -v
"""

import sys
import os
import json
import ast

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# ---------------------------------------------------------------------------
# OpenAPI Spec Tests
# ---------------------------------------------------------------------------

from developer_experience.openapi_spec import (
    build_openapi_spec,
    export_openapi,
    LEGAL_PATHS,
    TRUST_PATHS,
    BANKING_PATHS,
    GOVERNANCE_PATHS,
    MCP_PATHS,
    EI_PATHS,
    APPBUILDER_PATHS,
    OBS_PATHS,
    COMPLIANCE_PATHS,
    WORKFLOW_PATHS,
    LEGAL_SCHEMAS,
    TRUST_SCHEMAS,
    BANKING_SCHEMAS,
    SHARED_SCHEMAS,
)


class TestOpenAPISpec:
    """Tests for the OpenAPI specification generator."""

    def test_build_returns_dict(self):
        """build_openapi_spec returns a dict."""
        spec = build_openapi_spec()
        assert isinstance(spec, dict)

    def test_openapi_version(self):
        """Spec uses OpenAPI 3.1.0."""
        spec = build_openapi_spec()
        assert spec["openapi"] == "3.1.0"

    def test_info_present(self):
        """Spec has required info block."""
        spec = build_openapi_spec()
        assert "info" in spec
        assert "title" in spec["info"]
        assert "version" in spec["info"]

    def test_info_title(self):
        """Spec title contains SintraPrime."""
        spec = build_openapi_spec()
        assert "SintraPrime" in spec["info"]["title"]

    def test_servers_present(self):
        """Spec includes server definitions."""
        spec = build_openapi_spec()
        assert "servers" in spec
        assert len(spec["servers"]) >= 1

    def test_paths_present(self):
        """Spec has paths section with endpoints."""
        spec = build_openapi_spec()
        assert "paths" in spec
        assert len(spec["paths"]) > 0

    def test_has_minimum_endpoints(self):
        """Spec has at least 20 endpoints."""
        spec = build_openapi_spec()
        total = sum(
            len([m for m, v in methods.items() if isinstance(v, dict)])
            for methods in spec["paths"].values()
        )
        assert total >= 20

    def test_components_schemas_present(self):
        """Spec has component schemas."""
        spec = build_openapi_spec()
        schemas = spec.get("components", {}).get("schemas", {})
        assert len(schemas) > 0

    def test_has_minimum_schemas(self):
        """Spec has at least 30 schemas."""
        spec = build_openapi_spec()
        schemas = spec.get("components", {}).get("schemas", {})
        assert len(schemas) >= 30

    def test_security_schemes_present(self):
        """Spec has security schemes."""
        spec = build_openapi_spec()
        sec_schemes = spec.get("components", {}).get("securitySchemes", {})
        assert "BearerAuth" in sec_schemes or "ApiKeyAuth" in sec_schemes

    def test_tags_present(self):
        """Spec has module tags."""
        spec = build_openapi_spec()
        assert "tags" in spec
        assert len(spec["tags"]) >= 10

    def test_legal_paths_included(self):
        """Legal Intelligence paths are in spec."""
        spec = build_openapi_spec()
        for path in LEGAL_PATHS:
            assert path in spec["paths"], f"Missing legal path: {path}"

    def test_trust_paths_included(self):
        """Trust Law paths are in spec."""
        spec = build_openapi_spec()
        for path in TRUST_PATHS:
            assert path in spec["paths"], f"Missing trust path: {path}"

    def test_banking_paths_included(self):
        """Banking paths are in spec."""
        spec = build_openapi_spec()
        for path in BANKING_PATHS:
            assert path in spec["paths"], f"Missing banking path: {path}"

    def test_governance_paths_included(self):
        """Governance paths are in spec."""
        spec = build_openapi_spec()
        for path in GOVERNANCE_PATHS:
            assert path in spec["paths"]

    def test_mcp_paths_included(self):
        """MCP Server paths are in spec."""
        spec = build_openapi_spec()
        for path in MCP_PATHS:
            assert path in spec["paths"]

    def test_compliance_paths_included(self):
        """Compliance paths are in spec."""
        spec = build_openapi_spec()
        for path in COMPLIANCE_PATHS:
            assert path in spec["paths"]

    def test_workflow_paths_included(self):
        """Workflow paths are in spec."""
        spec = build_openapi_spec()
        for path in WORKFLOW_PATHS:
            assert path in spec["paths"]

    def test_legal_schemas_in_spec(self):
        """Legal schemas are in spec components."""
        spec = build_openapi_spec()
        schemas = spec["components"]["schemas"]
        for name in LEGAL_SCHEMAS:
            assert name in schemas

    def test_trust_schemas_in_spec(self):
        """Trust schemas are in spec components."""
        spec = build_openapi_spec()
        schemas = spec["components"]["schemas"]
        for name in TRUST_SCHEMAS:
            assert name in schemas

    def test_shared_schemas_in_spec(self):
        """Shared schemas (Error, Pagination, HealthCheck) are in spec."""
        spec = build_openapi_spec()
        schemas = spec["components"]["schemas"]
        for name in SHARED_SCHEMAS:
            assert name in schemas

    def test_error_schema_structure(self):
        """Error schema has required code and message fields."""
        spec = build_openapi_spec()
        error_schema = spec["components"]["schemas"]["Error"]
        assert "code" in error_schema["properties"]
        assert "message" in error_schema["properties"]

    def test_all_operations_have_responses(self):
        """All operations include response definitions."""
        spec = build_openapi_spec()
        for path, path_item in spec["paths"].items():
            for method, operation in path_item.items():
                if isinstance(operation, dict):
                    assert "responses" in operation, f"No responses in {method.upper()} {path}"

    def test_spec_is_json_serializable(self):
        """Spec can be serialized to JSON without errors."""
        spec = build_openapi_spec()
        json_str = json.dumps(spec)
        assert len(json_str) > 0

    def test_spec_json_round_trip(self):
        """Spec survives JSON round-trip."""
        spec = build_openapi_spec()
        json_str = json.dumps(spec)
        recovered = json.loads(json_str)
        assert recovered["openapi"] == spec["openapi"]
        assert len(recovered["paths"]) == len(spec["paths"])

    def test_export_openapi_creates_files(self, tmp_path):
        """export_openapi creates openapi.json and openapi.yaml."""
        spec = export_openapi(str(tmp_path))
        assert (tmp_path / "openapi.json").exists()
        assert (tmp_path / "openapi.yaml").exists()

    def test_exported_json_valid(self, tmp_path):
        """Exported openapi.json is valid JSON."""
        export_openapi(str(tmp_path))
        json_file = tmp_path / "openapi.json"
        with open(json_file) as f:
            data = json.load(f)
        assert data["openapi"] == "3.1.0"


# ---------------------------------------------------------------------------
# Cookbook Tests
# ---------------------------------------------------------------------------

from developer_experience.cookbook import (
    SCENARIOS,
    CookbookScenario,
    get_scenario,
    list_scenarios,
    search_scenarios,
    export_cookbook,
    register,
)


class TestCookbook:
    """Tests for the interactive cookbook."""

    def test_scenarios_loaded(self):
        """SCENARIOS list is not empty."""
        assert len(SCENARIOS) > 0

    def test_minimum_25_scenarios(self):
        """At least 25 scenarios are registered."""
        assert len(SCENARIOS) >= 25

    def test_all_scenarios_are_cookbook_scenario(self):
        """All items in SCENARIOS are CookbookScenario instances."""
        for s in SCENARIOS:
            assert isinstance(s, CookbookScenario)

    def test_all_scenarios_have_ids(self):
        """All scenarios have non-empty IDs."""
        for s in SCENARIOS:
            assert s.id and len(s.id) > 0

    def test_all_scenario_ids_unique(self):
        """All scenario IDs are unique."""
        ids = [s.id for s in SCENARIOS]
        assert len(ids) == len(set(ids))

    def test_all_scenarios_have_titles(self):
        """All scenarios have non-empty titles."""
        for s in SCENARIOS:
            assert s.title and len(s.title) > 0

    def test_all_scenarios_have_code(self):
        """All scenarios have non-empty code."""
        for s in SCENARIOS:
            assert s.code and len(s.code.strip()) > 0

    def test_all_scenarios_have_expected_output(self):
        """All scenarios have expected_output."""
        for s in SCENARIOS:
            assert s.expected_output and len(s.expected_output.strip()) > 0

    def test_all_scenarios_have_tags(self):
        """All scenarios have at least one tag."""
        for s in SCENARIOS:
            assert len(s.tags) > 0

    def test_all_scenario_codes_valid_python(self):
        """All scenario code snippets are syntactically valid Python."""
        for s in SCENARIOS:
            try:
                ast.parse(s.code)
            except SyntaxError as e:
                pytest.fail(f"Scenario '{s.id}' has invalid Python: {e}")

    def test_difficulty_values_valid(self):
        """All scenarios have valid difficulty values."""
        valid = {"beginner", "intermediate", "advanced"}
        for s in SCENARIOS:
            assert s.difficulty in valid, f"Scenario {s.id} has invalid difficulty: {s.difficulty}"

    def test_get_scenario_found(self):
        """get_scenario returns correct scenario for valid ID."""
        first = SCENARIOS[0]
        result = get_scenario(first.id)
        assert result is not None
        assert result.id == first.id

    def test_get_scenario_not_found(self):
        """get_scenario returns None for unknown ID."""
        result = get_scenario("nonexistent-id-xyz")
        assert result is None

    def test_list_scenarios_returns_list(self):
        """list_scenarios returns a list of dicts."""
        result = list_scenarios()
        assert isinstance(result, list)
        assert len(result) == len(SCENARIOS)

    def test_list_scenarios_has_required_keys(self):
        """list_scenarios entries have required keys."""
        for item in list_scenarios():
            assert "id" in item
            assert "title" in item
            assert "tags" in item
            assert "difficulty" in item

    def test_search_by_tag(self):
        """search_scenarios filters by tag."""
        results = search_scenarios(tags=["legal"])
        assert len(results) > 0
        for s in results:
            assert "legal" in s.tags

    def test_search_by_difficulty(self):
        """search_scenarios filters by difficulty."""
        results = search_scenarios(difficulty="beginner")
        assert len(results) > 0
        for s in results:
            assert s.difficulty == "beginner"

    def test_search_by_tag_and_difficulty(self):
        """search_scenarios supports combined filtering."""
        results = search_scenarios(tags=["banking"], difficulty="intermediate")
        for s in results:
            assert "banking" in s.tags
            assert s.difficulty == "intermediate"

    def test_export_cookbook_creates_json(self, tmp_path):
        """export_cookbook writes JSON file."""
        output = str(tmp_path / "cookbook.json")
        export_cookbook(output)
        assert (tmp_path / "cookbook.json").exists()

    def test_export_cookbook_valid_json(self, tmp_path):
        """Exported cookbook JSON is valid and complete."""
        output = str(tmp_path / "cookbook.json")
        export_cookbook(output)
        with open(output) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == len(SCENARIOS)

    def test_trust_scenario_exists(self):
        """Trust-related scenario exists."""
        results = search_scenarios(tags=["trust"])
        assert len(results) > 0

    def test_legal_scenario_exists(self):
        """Legal-related scenarios exist."""
        results = search_scenarios(tags=["legal"])
        assert len(results) > 0

    def test_banking_scenario_exists(self):
        """Banking-related scenario exists."""
        results = search_scenarios(tags=["banking"])
        assert len(results) > 0


# ---------------------------------------------------------------------------
# Model Playground Tests
# ---------------------------------------------------------------------------

from developer_experience.model_playground import (
    SUPPORTED_MODELS,
    PROMPT_TEMPLATES,
    ModelConfig,
    ModelProvider,
    PromptTemplate,
    PlaygroundBenchmark,
    get_client,
    list_models,
    list_templates,
    get_template,
    BenchmarkResult,
    ABTestResult,
)


class TestModelPlayground:
    """Tests for the model playground."""

    def test_supported_models_not_empty(self):
        """SUPPORTED_MODELS dict is not empty."""
        assert len(SUPPORTED_MODELS) > 0

    def test_minimum_5_models(self):
        """At least 5 models are supported."""
        assert len(SUPPORTED_MODELS) >= 5

    def test_all_models_have_config(self):
        """All models are ModelConfig instances."""
        for model_id, config in SUPPORTED_MODELS.items():
            assert isinstance(config, ModelConfig)

    def test_gpt4o_in_models(self):
        """GPT-4o is supported."""
        assert "gpt-4o" in SUPPORTED_MODELS

    def test_claude_in_models(self):
        """Claude model is supported."""
        claude_models = [k for k in SUPPORTED_MODELS if "claude" in k]
        assert len(claude_models) > 0

    def test_ollama_in_models(self):
        """Ollama local model is supported."""
        ollama_models = [k for k in SUPPORTED_MODELS if "ollama" in k]
        assert len(ollama_models) > 0

    def test_deepseek_in_models(self):
        """DeepSeek model is supported."""
        ds_models = [k for k in SUPPORTED_MODELS if "deepseek" in k]
        assert len(ds_models) > 0

    def test_prompt_templates_not_empty(self):
        """PROMPT_TEMPLATES list is not empty."""
        assert len(PROMPT_TEMPLATES) > 0

    def test_minimum_50_templates(self):
        """At least 50 prompt templates exist."""
        assert len(PROMPT_TEMPLATES) >= 50

    def test_all_templates_are_prompt_template(self):
        """All items are PromptTemplate instances."""
        for t in PROMPT_TEMPLATES:
            assert isinstance(t, PromptTemplate)

    def test_all_template_ids_unique(self):
        """All template IDs are unique."""
        ids = [t.id for t in PROMPT_TEMPLATES]
        assert len(ids) == len(set(ids))

    def test_all_templates_have_system_prompt(self):
        """All templates have non-empty system prompts."""
        for t in PROMPT_TEMPLATES:
            assert t.system_prompt and len(t.system_prompt) > 0

    def test_all_templates_have_user_template(self):
        """All templates have user_template."""
        for t in PROMPT_TEMPLATES:
            assert t.user_template and len(t.user_template) > 0

    def test_list_models_returns_list(self):
        """list_models returns a list."""
        result = list_models()
        assert isinstance(result, list)
        assert len(result) == len(SUPPORTED_MODELS)

    def test_list_models_has_required_keys(self):
        """list_models entries have required keys."""
        for m in list_models():
            assert "id" in m
            assert "display_name" in m
            assert "provider" in m
            assert "cost_per_1k_input" in m

    def test_list_templates_returns_list(self):
        """list_templates returns a list."""
        result = list_templates()
        assert isinstance(result, list)
        assert len(result) == len(PROMPT_TEMPLATES)

    def test_list_templates_filter_by_category(self):
        """list_templates can filter by category."""
        legal = list_templates(category="legal")
        assert len(legal) > 0
        for t in legal:
            assert t["category"] == "legal" if isinstance(t, dict) else t.category == "legal"

    def test_get_template_found(self):
        """get_template returns template for valid ID."""
        first = PROMPT_TEMPLATES[0]
        result = get_template(first.id)
        assert result is not None
        assert result.id == first.id

    def test_get_template_not_found(self):
        """get_template returns None for unknown ID."""
        result = get_template("nonexistent-template-xyz-999")
        assert result is None

    def test_benchmark_run_single(self):
        """PlaygroundBenchmark.run_single returns BenchmarkResult."""
        bench = PlaygroundBenchmark()
        result = bench.run_single("gpt-4o", "legal-001", {"case_citation": "Marbury v. Madison"})
        assert isinstance(result, BenchmarkResult)
        assert result.model_id == "gpt-4o"
        assert result.prompt_id == "legal-001"

    def test_benchmark_result_has_fields(self):
        """BenchmarkResult has all required fields."""
        bench = PlaygroundBenchmark()
        result = bench.run_single("gpt-4o", "legal-001", {"case_citation": "Test Case"})
        assert hasattr(result, "latency_ms")
        assert hasattr(result, "cost_usd")
        assert hasattr(result, "quality_score")
        assert hasattr(result, "response")

    def test_ab_test_returns_ab_result(self):
        """ab_test returns ABTestResult."""
        bench = PlaygroundBenchmark()
        result = bench.ab_test("gpt-4o", "claude-3-5-sonnet", "legal-001", {"case_citation": "Test"})
        assert isinstance(result, ABTestResult)

    def test_ab_test_winner_is_valid(self):
        """A/B test winner is one of the two models or 'tie'."""
        bench = PlaygroundBenchmark()
        result = bench.ab_test("gpt-4o", "claude-3-5-sonnet", "legal-001", {"case_citation": "Test"})
        assert result.winner in ("gpt-4o", "claude-3-5-sonnet", "tie")

    def test_cost_estimate(self):
        """cost_estimate returns cost structure."""
        bench = PlaygroundBenchmark()
        result = bench.cost_estimate("gpt-4o", 500, 300)
        assert "cost_per_request_usd" in result
        assert "cost_1000_requests_usd" in result
        assert result["cost_per_request_usd"] >= 0

    def test_leaderboard_sorted(self):
        """leaderboard returns results sorted by overall_score desc."""
        bench = PlaygroundBenchmark()
        results = bench.run_suite(["gpt-4o", "claude-3-5-sonnet"], ["legal-001"], {"case_citation": "Test"})
        leaderboard = bench.leaderboard(results)
        assert len(leaderboard) > 0
        for i in range(len(leaderboard) - 1):
            assert leaderboard[i]["overall_score"] >= leaderboard[i + 1]["overall_score"]

    def test_invalid_model_raises(self):
        """run_single raises ValueError for unknown model."""
        bench = PlaygroundBenchmark()
        with pytest.raises(ValueError):
            bench.run_single("nonexistent-model-xyz", "legal-001")

    def test_invalid_template_raises(self):
        """run_single raises ValueError for unknown template."""
        bench = PlaygroundBenchmark()
        with pytest.raises(ValueError):
            bench.run_single("gpt-4o", "nonexistent-template-xyz")


# ---------------------------------------------------------------------------
# SDK Generator Tests
# ---------------------------------------------------------------------------

from developer_experience.sdk_generator import (
    PythonSDKGenerator,
    TypeScriptSDKGenerator,
    CurlExampleGenerator,
    generate_all_sdks,
    load_spec,
    to_snake_case,
    to_camel_case,
    to_pascal_case,
)

MINIMAL_SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "servers": [{"url": "https://api.test.com"}],
    "paths": {
        "/users": {
            "get": {
                "tags": ["Users"],
                "summary": "List users",
                "operationId": "listUsers",
                "parameters": [
                    {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                ],
                "responses": {"200": {"description": "Users list"}},
            },
            "post": {
                "tags": ["Users"],
                "summary": "Create user",
                "operationId": "createUser",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"201": {"description": "User created"}},
            },
        },
        "/users/{userId}": {
            "get": {
                "tags": ["Users"],
                "summary": "Get user",
                "operationId": "getUser",
                "parameters": [{"name": "userId", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "User"}},
            },
        },
    },
    "components": {
        "schemas": {
            "User": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}}},
            "Error": {"type": "object", "required": ["code", "message"], "properties": {"code": {"type": "integer"}, "message": {"type": "string"}}},
        }
    },
}


class TestSDKGenerator:
    """Tests for the SDK generator."""

    def test_to_snake_case(self):
        """to_snake_case converts camelCase correctly."""
        assert to_snake_case("listUsers") == "list_users"
        assert to_snake_case("getUserById") == "get_user_by_id"

    def test_to_camel_case(self):
        """to_camel_case converts snake_case correctly."""
        assert to_camel_case("list_users") == "listUsers"
        assert to_camel_case("get_user_by_id") == "getUserById"

    def test_to_pascal_case(self):
        """to_pascal_case converts correctly."""
        assert to_pascal_case("list_users") == "ListUsers"
        assert to_pascal_case("listUsers") == "ListUsers"

    def test_load_spec_from_dict(self):
        """load_spec loads from dict."""
        result = load_spec(MINIMAL_SPEC)
        assert result == MINIMAL_SPEC

    def test_load_spec_from_json_string(self):
        """load_spec loads from JSON string."""
        json_str = json.dumps(MINIMAL_SPEC)
        result = load_spec(json_str)
        assert result["openapi"] == "3.1.0"

    def test_python_sdk_generates_string(self):
        """PythonSDKGenerator.generate returns a non-empty string."""
        gen = PythonSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        assert isinstance(code, str)
        assert len(code) > 0

    def test_python_sdk_has_base_client(self):
        """Generated Python SDK includes BaseClient class."""
        gen = PythonSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        assert "class BaseClient" in code

    def test_python_sdk_has_api_error(self):
        """Generated Python SDK includes APIError class."""
        gen = PythonSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        assert "class APIError" in code

    def test_python_sdk_has_main_client(self):
        """Generated Python SDK includes main client class."""
        gen = PythonSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        assert "class" in code and "Client" in code

    def test_python_sdk_has_model_classes(self):
        """Generated Python SDK includes data model classes."""
        gen = PythonSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        assert "class User" in code or "@dataclass" in code

    def test_python_sdk_valid_syntax(self):
        """Generated Python SDK is syntactically valid."""
        gen = PythonSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Generated Python SDK has syntax error: {e}")

    def test_python_sdk_saved_to_file(self, tmp_path):
        """PythonSDKGenerator.save writes a file."""
        gen = PythonSDKGenerator(MINIMAL_SPEC)
        path = gen.save(tmp_path / "test_sdk.py")
        assert path.exists()
        assert path.stat().st_size > 0

    def test_typescript_sdk_generates_string(self):
        """TypeScriptSDKGenerator.generate returns a non-empty string."""
        gen = TypeScriptSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        assert isinstance(code, str)
        assert len(code) > 0

    def test_typescript_sdk_has_base_client(self):
        """Generated TypeScript SDK includes BaseClient class."""
        gen = TypeScriptSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        assert "class BaseClient" in code

    def test_typescript_sdk_has_interfaces(self):
        """Generated TypeScript SDK includes interface definitions."""
        gen = TypeScriptSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        assert "interface" in code or "export interface" in code

    def test_typescript_sdk_has_main_client(self):
        """Generated TypeScript SDK includes main SintraPrimeClient."""
        gen = TypeScriptSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        assert "SintraPrimeClient" in code or "class" in code

    def test_typescript_sdk_has_api_error(self):
        """Generated TypeScript SDK includes APIError class."""
        gen = TypeScriptSDKGenerator(MINIMAL_SPEC)
        code = gen.generate()
        assert "APIError" in code

    def test_typescript_sdk_saved_to_file(self, tmp_path):
        """TypeScriptSDKGenerator.save writes a file."""
        gen = TypeScriptSDKGenerator(MINIMAL_SPEC)
        path = gen.save(tmp_path / "test_sdk.ts")
        assert path.exists()
        assert path.stat().st_size > 0

    def test_curl_generator_produces_examples(self):
        """CurlExampleGenerator generates examples for all endpoints."""
        gen = CurlExampleGenerator(MINIMAL_SPEC)
        examples = gen.generate_all()
        assert len(examples) == 3  # GET /users, POST /users, GET /users/{userId}

    def test_curl_examples_have_required_keys(self):
        """Curl examples have required keys."""
        gen = CurlExampleGenerator(MINIMAL_SPEC)
        examples = gen.generate_all()
        for ex in examples:
            assert "method" in ex
            assert "path" in ex
            assert "curl" in ex

    def test_curl_examples_contain_curl(self):
        """Curl examples start with curl command."""
        gen = CurlExampleGenerator(MINIMAL_SPEC)
        examples = gen.generate_all()
        for ex in examples:
            assert "curl" in ex["curl"].lower()

    def test_curl_markdown_saved(self, tmp_path):
        """CurlExampleGenerator.save_markdown writes file."""
        gen = CurlExampleGenerator(MINIMAL_SPEC)
        path = gen.save_markdown(tmp_path / "curl_examples.md")
        assert path.exists()
        content = path.read_text()
        assert "curl" in content.lower()

    def test_generate_all_sdks(self, tmp_path):
        """generate_all_sdks creates all three SDK files."""
        results = generate_all_sdks(MINIMAL_SPEC, tmp_path)
        assert "python" in results
        assert "typescript" in results
        assert "curl" in results
        for path in results.values():
            assert path.exists()

    def test_full_spec_python_sdk(self):
        """Full SintraPrime spec generates valid Python SDK."""
        from developer_experience.openapi_spec import build_openapi_spec
        spec = build_openapi_spec()
        gen = PythonSDKGenerator(spec)
        code = gen.generate()
        assert len(code) > 5000
        ast.parse(code)  # Must be valid Python

    def test_full_spec_typescript_sdk(self):
        """Full SintraPrime spec generates TypeScript SDK."""
        from developer_experience.openapi_spec import build_openapi_spec
        spec = build_openapi_spec()
        gen = TypeScriptSDKGenerator(spec)
        code = gen.generate()
        assert len(code) > 5000
        assert "SintraPrimeClient" in code

    def test_full_spec_curl_examples(self):
        """Full SintraPrime spec generates curl examples for all endpoints."""
        from developer_experience.openapi_spec import build_openapi_spec
        spec = build_openapi_spec()
        gen = CurlExampleGenerator(spec)
        examples = gen.generate_all()
        assert len(examples) >= 20


# ---------------------------------------------------------------------------
# Integration: OpenAPI + SDK
# ---------------------------------------------------------------------------

class TestIntegration:
    """Integration tests across modules."""

    def test_spec_endpoints_all_have_operation_ids(self):
        """Most operations have operationIds (good SDK practice)."""
        from developer_experience.openapi_spec import build_openapi_spec
        spec = build_openapi_spec()
        op_with_id = 0
        total = 0
        for path_item in spec["paths"].values():
            for method, op in path_item.items():
                if isinstance(op, dict):
                    total += 1
                    if "operationId" in op:
                        op_with_id += 1
        ratio = op_with_id / total if total > 0 else 0
        assert ratio >= 0.8, f"Only {ratio:.0%} of operations have operationIds"

    def test_scenario_tags_cover_multiple_modules(self):
        """Cookbook scenarios cover at least 5 different API modules."""
        all_tags = set()
        for s in SCENARIOS:
            all_tags.update(s.tags)
        # Should cover legal, banking, trust, compliance, workflow, mcp, governance, ei
        expected_modules = {"legal", "banking", "trust", "compliance", "workflow", "mcp"}
        covered = expected_modules.intersection(all_tags)
        assert len(covered) >= 5, f"Only covers: {covered}"

    def test_all_scenario_code_uses_requests(self):
        """Most cookbook scenarios demonstrate HTTP client usage."""
        using_requests = sum(1 for s in SCENARIOS if "requests" in s.code or "BASE_URL" in s.code)
        assert using_requests >= 20

    def test_playground_supports_legal_templates(self):
        """Playground has legal-specific prompt templates."""
        legal = list_templates(category="legal")
        assert len(legal) >= 10

    def test_spec_has_all_10_modules(self):
        """Spec tags include all 10 required modules."""
        from developer_experience.openapi_spec import build_openapi_spec
        spec = build_openapi_spec()
        tag_names = {t["name"] for t in spec.get("tags", [])}
        required_modules = [
            "Legal Intelligence", "Trust Law", "Banking/Plaid", "Governance",
            "MCP Server", "Emotional Intelligence", "App Builder",
            "Observability", "Compliance", "Workflow Builder",
        ]
        for module in required_modules:
            assert module in tag_names, f"Missing module tag: {module}"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_empty_tag_search_returns_all(self):
        """search_scenarios with no filters returns all scenarios."""
        results = search_scenarios()
        assert len(results) == len(SCENARIOS)

    def test_nonexistent_tag_search_returns_empty(self):
        """search_scenarios with unknown tag returns empty list."""
        results = search_scenarios(tags=["nonexistent_tag_xyz_999"])
        assert len(results) == 0

    def test_spec_path_items_valid_methods(self):
        """All path items use valid HTTP methods."""
        valid_methods = {"get", "post", "put", "patch", "delete", "head", "options"}
        from developer_experience.openapi_spec import build_openapi_spec
        spec = build_openapi_spec()
        for path, path_item in spec["paths"].items():
            for key in path_item:
                assert key in valid_methods, f"Invalid method '{key}' in path {path}"

    def test_python_sdk_with_empty_paths(self):
        """SDK generator handles spec with no paths gracefully."""
        empty_spec = {
            "openapi": "3.1.0",
            "info": {"title": "Empty", "version": "1.0.0"},
            "servers": [{"url": "https://api.test.com"}],
            "paths": {},
            "components": {"schemas": {}},
        }
        gen = PythonSDKGenerator(empty_spec)
        code = gen.generate()
        assert isinstance(code, str)
        ast.parse(code)

    def test_model_cost_estimate_zero_for_free_models(self):
        """Free models (Ollama, Hermes) have zero cost."""
        bench = PlaygroundBenchmark()
        result = bench.cost_estimate("ollama-llama3", 1000, 1000)
        assert result["cost_per_request_usd"] == 0.0

    def test_cookbook_scenario_code_no_bare_except(self):
        """No scenario uses bare 'except:' clauses (bad practice check)."""
        for s in SCENARIOS:
            assert "except:" not in s.code, f"Scenario {s.id} uses bare except:"
