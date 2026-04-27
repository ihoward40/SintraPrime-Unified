"""Phase 17C — LLM Executor Tests (58 tests)."""
import pytest
from unittest.mock import patch, MagicMock
from phase17.llm_wiring.llm_executor import (
    LLMProvider, LLMRequest, LLMResponse, LLMGatewayStats,
    LLMGateway, PARLLLMExecutor, MoELLMExpert,
)


# ─────────────────────────────────────────────────────────────────────────────
# LLMRequest (6 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestLLMRequest:
    def test_prompt_required(self):
        r = LLMRequest(prompt="hello")
        assert r.prompt == "hello"

    def test_default_model(self):
        r = LLMRequest(prompt="hello")
        assert r.model == "gpt-4o-mini"

    def test_default_temperature(self):
        r = LLMRequest(prompt="hello")
        assert r.temperature == pytest.approx(0.3)

    def test_request_id_auto(self):
        r = LLMRequest(prompt="hello")
        assert r.request_id.startswith("req_")

    def test_custom_system_prompt(self):
        r = LLMRequest(prompt="hello", system_prompt="You are a tax expert.")
        assert "tax" in r.system_prompt

    def test_metadata_default_empty(self):
        r = LLMRequest(prompt="hello")
        assert r.metadata == {}


# ─────────────────────────────────────────────────────────────────────────────
# LLMResponse (8 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestLLMResponse:
    def _make(self, **kw):
        defaults = dict(
            request_id="req_test",
            content="Legal analysis complete.",
            model="gpt-4o-mini",
            provider=LLMProvider.MOCK,
            latency_ms=12.5,
        )
        defaults.update(kw)
        return LLMResponse(**defaults)

    def test_content(self):
        r = self._make()
        assert r.content == "Legal analysis complete."

    def test_success_default_true(self):
        r = self._make()
        assert r.success is True

    def test_error_default_none(self):
        r = self._make()
        assert r.error is None

    def test_latency_ms(self):
        r = self._make(latency_ms=42.0)
        assert r.latency_ms == pytest.approx(42.0)

    def test_total_cost_zero_tokens(self):
        r = self._make()
        assert r.total_cost_usd == pytest.approx(0.0)

    def test_total_cost_with_tokens(self):
        r = self._make(prompt_tokens=1000, completion_tokens=500)
        # 1000 * 0.00000015 + 500 * 0.0000006 = 0.00015 + 0.0003 = 0.00045
        assert r.total_cost_usd == pytest.approx(0.00045, rel=1e-3)

    def test_failure_response(self):
        r = self._make(success=False, error="API timeout", content="")
        assert r.success is False
        assert r.error == "API timeout"

    def test_provider_field(self):
        r = self._make(provider=LLMProvider.OPENAI)
        assert r.provider == LLMProvider.OPENAI


# ─────────────────────────────────────────────────────────────────────────────
# LLMGatewayStats (5 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestLLMGatewayStats:
    def test_success_rate_zero_requests(self):
        s = LLMGatewayStats()
        assert s.success_rate == 0.0

    def test_success_rate_all_pass(self):
        s = LLMGatewayStats(total_requests=10, successful_requests=10)
        assert s.success_rate == pytest.approx(1.0)

    def test_success_rate_partial(self):
        s = LLMGatewayStats(total_requests=10, successful_requests=8)
        assert s.success_rate == pytest.approx(0.8)

    def test_default_provider_mock(self):
        s = LLMGatewayStats()
        assert s.provider == LLMProvider.MOCK

    def test_total_cost_accumulates(self):
        s = LLMGatewayStats(total_cost_usd=0.005)
        assert s.total_cost_usd == pytest.approx(0.005)


# ─────────────────────────────────────────────────────────────────────────────
# LLMGateway — mock mode (20 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestLLMGatewayMock:
    @pytest.fixture
    def gw(self):
        return LLMGateway(provider=LLMProvider.MOCK, mock_latency_ms=1.0)

    def test_provider_mock(self, gw):
        assert gw.provider == LLMProvider.MOCK

    def test_complete_returns_response(self, gw):
        r = gw.complete(LLMRequest(prompt="Analyze this contract."))
        assert isinstance(r, LLMResponse)

    def test_complete_success(self, gw):
        r = gw.complete(LLMRequest(prompt="What is an NDA?"))
        assert r.success is True

    def test_complete_has_content(self, gw):
        r = gw.complete(LLMRequest(prompt="Explain employment law."))
        assert len(r.content) > 0

    def test_complete_contract_keyword(self, gw):
        r = gw.complete(LLMRequest(prompt="Review this contract agreement."))
        assert "contract" in r.content.lower() or "clause" in r.content.lower()

    def test_complete_tax_keyword(self, gw):
        r = gw.complete(LLMRequest(prompt="IRS tax deduction question."))
        assert "tax" in r.content.lower()

    def test_complete_employment_keyword(self, gw):
        r = gw.complete(LLMRequest(prompt="Wrongful termination employment case."))
        assert "employment" in r.content.lower() or "termination" in r.content.lower()

    def test_complete_generic_prompt(self, gw):
        r = gw.complete(LLMRequest(prompt="Random legal question."))
        assert r.success is True

    def test_complete_latency_positive(self, gw):
        r = gw.complete(LLMRequest(prompt="Test prompt."))
        assert r.latency_ms > 0

    def test_complete_tokens_positive(self, gw):
        r = gw.complete(LLMRequest(prompt="Test prompt."))
        assert r.total_tokens > 0

    def test_stats_increments(self, gw):
        gw.complete(LLMRequest(prompt="First."))
        gw.complete(LLMRequest(prompt="Second."))
        assert gw.stats().total_requests == 2

    def test_stats_success_rate(self, gw):
        gw.complete(LLMRequest(prompt="Test."))
        assert gw.stats().success_rate == 1.0

    def test_stats_avg_latency(self, gw):
        gw.complete(LLMRequest(prompt="Test."))
        assert gw.stats().avg_latency_ms > 0

    def test_reset_stats(self, gw):
        gw.complete(LLMRequest(prompt="Test."))
        gw.reset_stats()
        assert gw.stats().total_requests == 0

    def test_batch_complete(self, gw):
        reqs = [LLMRequest(prompt=f"Query {i}") for i in range(5)]
        responses = gw.batch_complete(reqs)
        assert len(responses) == 5

    def test_batch_all_success(self, gw):
        reqs = [LLMRequest(prompt=f"Query {i}") for i in range(3)]
        responses = gw.batch_complete(reqs)
        assert all(r.success for r in responses)

    def test_batch_unique_request_ids(self, gw):
        reqs = [LLMRequest(prompt=f"Query {i}") for i in range(3)]
        responses = gw.batch_complete(reqs)
        ids = [r.request_id for r in responses]
        assert len(set(ids)) == 3

    def test_complete_model_field(self, gw):
        r = gw.complete(LLMRequest(prompt="Test."))
        assert "mock" in r.model or "gpt" in r.model

    def test_complete_provider_mock(self, gw):
        r = gw.complete(LLMRequest(prompt="Test."))
        assert r.provider == LLMProvider.MOCK

    def test_stats_total_tokens_accumulate(self, gw):
        gw.complete(LLMRequest(prompt="Test one."))
        gw.complete(LLMRequest(prompt="Test two."))
        assert gw.stats().total_tokens > 0


# ─────────────────────────────────────────────────────────────────────────────
# PARLLLMExecutor (10 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestPARLLLMExecutor:
    @pytest.fixture
    def executor(self):
        gw = LLMGateway(provider=LLMProvider.MOCK, mock_latency_ms=1.0)
        return PARLLLMExecutor(gateway=gw)

    def _make_context(self, task="Analyze contract", agent_id="agent_001", payload=None):
        ctx = MagicMock()
        ctx.task_description = task
        ctx.agent_id = agent_id
        ctx.payload = payload or {}
        return ctx

    def test_executor_callable(self, executor):
        ctx = self._make_context()
        result = executor(ctx)
        assert isinstance(result, dict)

    def test_executor_has_agent_id(self, executor):
        ctx = self._make_context(agent_id="agent_007")
        result = executor(ctx)
        assert result["agent_id"] == "agent_007"

    def test_executor_success(self, executor):
        ctx = self._make_context()
        result = executor(ctx)
        assert result["success"] is True

    def test_executor_has_llm_response(self, executor):
        ctx = self._make_context()
        result = executor(ctx)
        assert "llm_response" in result
        assert len(result["llm_response"]) > 0

    def test_executor_has_latency(self, executor):
        ctx = self._make_context()
        result = executor(ctx)
        assert result["latency_ms"] >= 0

    def test_executor_has_tokens(self, executor):
        ctx = self._make_context()
        result = executor(ctx)
        assert result["tokens"] >= 0

    def test_executor_default_gateway(self):
        exec2 = PARLLLMExecutor()
        assert exec2.gateway is not None

    def test_executor_uses_task_description(self, executor):
        ctx = self._make_context(task="IRS tax deduction question.")
        result = executor(ctx)
        assert result["success"] is True

    def test_executor_multiple_calls(self, executor):
        for i in range(5):
            ctx = self._make_context(agent_id=f"agent_{i}")
            result = executor(ctx)
            assert result["success"] is True

    def test_executor_with_payload(self, executor):
        ctx = self._make_context(payload={"contract_id": "C001", "urgency": "HIGH"})
        result = executor(ctx)
        assert result["success"] is True


# ─────────────────────────────────────────────────────────────────────────────
# MoELLMExpert (9 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestMoELLMExpert:
    @pytest.fixture
    def expert(self):
        gw = LLMGateway(provider=LLMProvider.MOCK, mock_latency_ms=1.0)
        return MoELLMExpert(gateway=gw)

    def test_answer_returns_dict(self, expert):
        result = expert.answer("What is an NDA?")
        assert isinstance(result, dict)

    def test_answer_has_query(self, expert):
        result = expert.answer("Explain employment law.")
        assert result["query"] == "Explain employment law."

    def test_answer_has_expert(self, expert):
        result = expert.answer("Wrongful termination case.")
        assert "expert" in result
        assert isinstance(result["expert"], str)

    def test_answer_has_confidence(self, expert):
        result = expert.answer("Contract review needed.")
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    def test_answer_has_answer(self, expert):
        result = expert.answer("What are my rights?")
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_answer_has_latency(self, expert):
        result = expert.answer("Tax question.")
        assert result["latency_ms"] >= 0

    def test_answer_has_tokens(self, expert):
        result = expert.answer("Legal question.")
        assert result["tokens"] >= 0

    def test_answer_default_gateway(self):
        exp2 = MoELLMExpert()
        assert exp2.gateway is not None

    def test_answer_multiple_queries(self, expert):
        queries = [
            "What is an NDA?",
            "IRS tax question.",
            "Employment discrimination case.",
        ]
        for q in queries:
            result = expert.answer(q)
            assert result["answer"]
