"""
Comprehensive tests for Claude Code integration.
All Anthropic API calls are mocked to avoid real API usage in tests.
"""
import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from claude_code.engine import ClaudeCodeEngine
from claude_code.legal_code_assistant import LegalCodeAssistant
from claude_code.code_generator import CodeGenerator


# ============ Fixtures ============

@pytest.fixture
def mock_anthropic():
    """Mock the Anthropic client."""
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Mocked Claude response")]
        mock_client.messages.create.return_value = mock_message

        yield mock_client


@pytest.fixture
def engine(mock_anthropic):
    return ClaudeCodeEngine(api_key="test-key")


@pytest.fixture
def legal_assistant(mock_anthropic):
    return LegalCodeAssistant(api_key="test-key")


@pytest.fixture
def generator(mock_anthropic):
    return CodeGenerator(api_key="test-key")


def make_mock_response(text: str):
    """Helper to create a mock Anthropic message response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


# ============ ClaudeCodeEngine Tests ============

class TestClaudeCodeEngine:

    @pytest.mark.asyncio
    async def test_analyze_code_returns_dict(self, engine, mock_anthropic):
        result = await engine.analyze_code("print('hello')", "python")
        assert isinstance(result, dict)
        assert "analysis" in result
        assert "language" in result
        assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_analyze_code_passes_language(self, engine, mock_anthropic):
        await engine.analyze_code("console.log('hi')", "javascript")
        call_args = mock_anthropic.messages.create.call_args
        assert "javascript" in str(call_args)

    @pytest.mark.asyncio
    async def test_analyze_code_default_language(self, engine, mock_anthropic):
        result = await engine.analyze_code("x = 1")
        assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_generate_legal_script_returns_dict(self, engine, mock_anthropic):
        result = await engine.generate_legal_script("Parse trust documents")
        assert isinstance(result, dict)
        assert "code" in result
        assert "description" in result

    @pytest.mark.asyncio
    async def test_generate_legal_script_passes_description(self, engine, mock_anthropic):
        desc = "Extract beneficiaries from trust documents"
        await engine.generate_legal_script(desc)
        call_args = mock_anthropic.messages.create.call_args
        assert desc in str(call_args)

    @pytest.mark.asyncio
    async def test_debug_returns_dict(self, engine, mock_anthropic):
        result = await engine.debug("x = 1/0", "ZeroDivisionError: division by zero")
        assert isinstance(result, dict)
        assert "debug_result" in result
        assert "original_error" in result

    @pytest.mark.asyncio
    async def test_debug_includes_error_in_prompt(self, engine, mock_anthropic):
        error = "NameError: name 'foo' is not defined"
        await engine.debug("foo()", error)
        call_args = mock_anthropic.messages.create.call_args
        assert error in str(call_args)

    @pytest.mark.asyncio
    async def test_generate_api_integration_returns_string(self, engine, mock_anthropic):
        result = await engine.generate_api_integration("GET /users endpoint", "Fetch user list")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_api_integration_passes_task(self, engine, mock_anthropic):
        task = "Integrate with Pacer court system"
        await engine.generate_api_integration("API docs here", task)
        call_args = mock_anthropic.messages.create.call_args
        assert task in str(call_args)

    @pytest.mark.asyncio
    async def test_review_legal_automation_returns_dict(self, engine, mock_anthropic):
        result = await engine.review_legal_automation("def file_motion(): pass")
        assert isinstance(result, dict)
        assert "review" in result
        assert "review_type" in result

    @pytest.mark.asyncio
    async def test_review_legal_automation_type(self, engine, mock_anthropic):
        result = await engine.review_legal_automation("code here")
        assert result["review_type"] == "legal_automation"

    @pytest.mark.asyncio
    async def test_explain_code_returns_string(self, engine, mock_anthropic):
        result = await engine.explain_code("def parse_trust(doc): return doc")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_engine_uses_correct_model(self, engine):
        assert engine.model == "claude-opus-4-5"

    @pytest.mark.asyncio
    async def test_engine_initializes_with_api_key(self, mock_anthropic):
        engine = ClaudeCodeEngine(api_key="my-secret-key")
        assert engine.client is not None


# ============ LegalCodeAssistant Tests ============

class TestLegalCodeAssistant:

    @pytest.mark.asyncio
    async def test_generate_trust_parser_returns_string(self, legal_assistant, mock_anthropic):
        result = await legal_assistant.generate_trust_parser("Sample trust document text")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_trust_parser_passes_sample(self, legal_assistant, mock_anthropic):
        sample = "REVOCABLE LIVING TRUST AGREEMENT..."
        await legal_assistant.generate_trust_parser(sample)
        call_args = mock_anthropic.messages.create.call_args
        assert sample in str(call_args)

    @pytest.mark.asyncio
    async def test_generate_contract_analyzer_nda(self, legal_assistant, mock_anthropic):
        result = await legal_assistant.generate_contract_analyzer("NDA")
        assert isinstance(result, str)
        call_args = mock_anthropic.messages.create.call_args
        assert "NDA" in str(call_args)

    @pytest.mark.asyncio
    async def test_generate_contract_analyzer_trust(self, legal_assistant, mock_anthropic):
        result = await legal_assistant.generate_contract_analyzer("Trust")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_contract_analyzer_unsupported_type(self, legal_assistant, mock_anthropic):
        # Should still work, just with a note
        result = await legal_assistant.generate_contract_analyzer("CustomContract")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_court_filing_script_returns_string(self, legal_assistant, mock_anthropic):
        result = await legal_assistant.generate_court_filing_script("California", "motion")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_court_filing_includes_jurisdiction(self, legal_assistant, mock_anthropic):
        await legal_assistant.generate_court_filing_script("Federal", "brief")
        call_args = mock_anthropic.messages.create.call_args
        assert "Federal" in str(call_args)

    @pytest.mark.asyncio
    async def test_explain_legal_code_returns_string(self, legal_assistant, mock_anthropic):
        result = await legal_assistant.explain_legal_code("def parse(doc): return doc.split()")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_code_review_for_compliance_returns_dict(self, legal_assistant, mock_anthropic):
        result = await legal_assistant.code_review_for_compliance("code here", "California")
        assert isinstance(result, dict)
        assert "review" in result
        assert "jurisdiction" in result
        assert result["jurisdiction"] == "California"

    @pytest.mark.asyncio
    async def test_code_review_includes_jurisdiction_in_prompt(self, legal_assistant, mock_anthropic):
        await legal_assistant.code_review_for_compliance("x = 1", "New York")
        call_args = mock_anthropic.messages.create.call_args
        assert "New York" in str(call_args)

    @pytest.mark.asyncio
    async def test_supported_contract_types(self, legal_assistant):
        assert "NDA" in LegalCodeAssistant.SUPPORTED_CONTRACT_TYPES
        assert "Trust" in LegalCodeAssistant.SUPPORTED_CONTRACT_TYPES
        assert "LLC" in LegalCodeAssistant.SUPPORTED_CONTRACT_TYPES


# ============ CodeGenerator Tests ============

class TestCodeGenerator:

    @pytest.mark.asyncio
    async def test_generate_module_returns_dict(self, generator, mock_anthropic):
        result = await generator.generate_module("UCC filing tracker")
        assert isinstance(result, dict)
        assert "files" in result
        assert "description" in result
        assert "integration_steps" in result

    @pytest.mark.asyncio
    async def test_generate_module_with_valid_json_response(self, generator, mock_anthropic):
        json_response = json.dumps({
            "files": {"ucc_tracker.py": "class UCCTracker: pass"},
            "description": "UCC filing tracker",
            "integration_steps": ["Step 1", "Step 2"]
        })
        mock_anthropic.messages.create.return_value = make_mock_response(json_response)
        result = await generator.generate_module("UCC filing tracker")
        assert result["files"]["ucc_tracker.py"] == "class UCCTracker: pass"

    @pytest.mark.asyncio
    async def test_generate_module_handles_non_json_response(self, generator, mock_anthropic):
        mock_anthropic.messages.create.return_value = make_mock_response("Not JSON at all")
        result = await generator.generate_module("Something")
        assert isinstance(result, dict)
        assert "files" in result

    @pytest.mark.asyncio
    async def test_generate_integration_returns_string(self, generator, mock_anthropic):
        result = await generator.generate_integration("Stripe", "Process trust distributions")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_integration_passes_service(self, generator, mock_anthropic):
        await generator.generate_integration("DocuSign", "E-sign trust documents")
        call_args = mock_anthropic.messages.create.call_args
        assert "DocuSign" in str(call_args)

    @pytest.mark.asyncio
    async def test_generate_test_suite_returns_string(self, generator, mock_anthropic):
        result = await generator.generate_test_suite("def add(a, b): return a + b")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_test_suite_passes_code(self, generator, mock_anthropic):
        code = "class TrustParser:\n    def parse(self): pass"
        await generator.generate_test_suite(code)
        call_args = mock_anthropic.messages.create.call_args
        assert "TrustParser" in str(call_args)

    @pytest.mark.asyncio
    async def test_scaffold_fastapi_endpoint_returns_string(self, generator, mock_anthropic):
        result = await generator.scaffold_fastapi_endpoint("trusts", ["create", "read", "update"])
        assert isinstance(result, str)
