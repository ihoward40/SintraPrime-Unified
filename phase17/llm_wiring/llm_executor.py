"""Phase 17C — Real LLM Integration Wiring.

Replaces mock subagent executors in the PARL engine with real GPT-4o-mini calls,
wires the MoE router to LLM-powered expert responses, and provides a unified
LLMGateway that all SintraPrime agents can use.
"""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class LLMProvider(str, Enum):
    OPENAI = "openai"
    MOCK = "mock"


@dataclass
class LLMRequest:
    prompt: str
    system_prompt: str = "You are SintraPrime, an expert legal AI assistant."
    model: str = "gpt-4o-mini"
    max_tokens: int = 512
    temperature: float = 0.3
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    request_id: str
    content: str
    model: str
    provider: LLMProvider
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    success: bool = True
    error: Optional[str] = None

    @property
    def total_cost_usd(self) -> float:
        """Approximate cost in USD (gpt-4o-mini pricing)."""
        input_cost = self.prompt_tokens * 0.00000015   # $0.15 / 1M tokens
        output_cost = self.completion_tokens * 0.0000006  # $0.60 / 1M tokens
        return input_cost + output_cost


@dataclass
class LLMGatewayStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    provider: LLMProvider = LLMProvider.MOCK

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


# ─────────────────────────────────────────────────────────────────────────────
# LLM Gateway
# ─────────────────────────────────────────────────────────────────────────────

class LLMGateway:
    """Unified gateway for all LLM calls in SintraPrime.

    Uses real OpenAI API when OPENAI_API_KEY is set, otherwise falls back to
    a deterministic mock that returns structured responses without API calls.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        provider: Optional[LLMProvider] = None,
        mock_latency_ms: float = 5.0,
    ):
        self.model = model
        self.mock_latency_ms = mock_latency_ms
        self._api_key = os.environ.get("OPENAI_API_KEY", "")
        self._api_base = os.environ.get("OPENAI_API_BASE", "")

        if provider is not None:
            self.provider = provider
        else:
            self.provider = LLMProvider.OPENAI if self._api_key else LLMProvider.MOCK

        self._stats = LLMGatewayStats(provider=self.provider)
        self._latencies: List[float] = []

    # ── public API ────────────────────────────────────────────────────────────

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Execute a single LLM completion."""
        t0 = time.perf_counter()
        try:
            if self.provider == LLMProvider.OPENAI and self._api_key:
                response = self._call_openai(request)
            else:
                response = self._mock_response(request)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            response.latency_ms = latency_ms
            self._record_success(response)
            return response
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self._record_failure()
            return LLMResponse(
                request_id=request.request_id,
                content="",
                model=request.model,
                provider=self.provider,
                latency_ms=latency_ms,
                success=False,
                error=str(exc),
            )

    def batch_complete(self, requests: List[LLMRequest]) -> List[LLMResponse]:
        """Execute multiple LLM completions (sequential for rate-limit safety)."""
        return [self.complete(req) for req in requests]

    def stats(self) -> LLMGatewayStats:
        return self._stats

    def reset_stats(self) -> None:
        self._stats = LLMGatewayStats(provider=self.provider)
        self._latencies.clear()

    # ── internal ──────────────────────────────────────────────────────────────

    def _call_openai(self, request: LLMRequest) -> LLMResponse:
        import openai
        kwargs: Dict[str, Any] = {
            "model": request.model,
            "input": request.prompt,
        }
        if self._api_base:
            client = openai.OpenAI(api_key=self._api_key, base_url=self._api_base)
        else:
            client = openai.OpenAI(api_key=self._api_key)

        resp = client.responses.create(**kwargs)
        content = resp.output_text if hasattr(resp, "output_text") else str(resp)
        usage = getattr(resp, "usage", None)
        prompt_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "output_tokens", 0) if usage else 0

        return LLMResponse(
            request_id=request.request_id,
            content=content,
            model=request.model,
            provider=LLMProvider.OPENAI,
            latency_ms=0.0,  # filled by caller
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            success=True,
        )

    def _mock_response(self, request: LLMRequest) -> LLMResponse:
        """Deterministic mock response for testing without API calls."""
        time.sleep(self.mock_latency_ms / 1000.0)
        prompt_lower = request.prompt.lower()

        # Generate a contextually relevant mock response
        if any(w in prompt_lower for w in ["contract", "nda", "agreement"]):
            content = (
                "Contract analysis complete. Key clauses identified: "
                "governing law (New York), non-compete (2 years), IP assignment. "
                "Risk level: MEDIUM. Recommend legal review of non-compete scope."
            )
        elif any(w in prompt_lower for w in ["tax", "irs", "deduction"]):
            content = (
                "Tax analysis: Estimated liability based on provided figures. "
                "Applicable deductions identified. Recommend CPA review for final filing."
            )
        elif any(w in prompt_lower for w in ["employment", "wrongful", "termination"]):
            content = (
                "Employment law analysis: Potential wrongful termination claim identified. "
                "Key factors: at-will employment, documented performance issues, "
                "protected class considerations. Recommend consultation."
            )
        elif any(w in prompt_lower for w in ["summarize", "summary"]):
            content = f"Summary of provided content: {request.prompt[:100]}... [analysis complete]"
        else:
            content = (
                f"SintraPrime analysis complete for: {request.prompt[:80]}. "
                "Relevant legal considerations identified. Please consult an attorney."
            )

        mock_tokens = len(request.prompt.split()) + len(content.split())
        return LLMResponse(
            request_id=request.request_id,
            content=content,
            model=f"mock-{request.model}",
            provider=LLMProvider.MOCK,
            latency_ms=0.0,
            prompt_tokens=len(request.prompt.split()),
            completion_tokens=len(content.split()),
            total_tokens=mock_tokens,
            success=True,
        )

    def _record_success(self, response: LLMResponse) -> None:
        self._stats.total_requests += 1
        self._stats.successful_requests += 1
        self._stats.total_tokens += response.total_tokens
        self._stats.total_cost_usd += response.total_cost_usd
        self._latencies.append(response.latency_ms)
        self._stats.avg_latency_ms = sum(self._latencies) / len(self._latencies)

    def _record_failure(self) -> None:
        self._stats.total_requests += 1
        self._stats.failed_requests += 1


# ─────────────────────────────────────────────────────────────────────────────
# PARL LLM Executor — replaces mock subagent executor
# ─────────────────────────────────────────────────────────────────────────────

class PARLLLMExecutor:
    """Wraps LLMGateway as a PARL subagent executor.

    Usage:
        executor = PARLLLMExecutor(gateway)
        engine.run_parallel(task, specs, executor_fn=executor)
    """

    def __init__(self, gateway: Optional[LLMGateway] = None):
        self.gateway = gateway or LLMGateway()

    def __call__(self, context: Any) -> Dict[str, Any]:
        """Called by PARLEngine for each subagent."""
        # context is a SubagentContext from phase16.parl_core
        task = getattr(context, "task_description", "")
        payload = getattr(context, "payload", {})
        agent_id = getattr(context, "agent_id", "unknown")

        prompt = f"Task: {task}\nAgent: {agent_id}\nContext: {payload}"
        request = LLMRequest(prompt=prompt, model=self.gateway.model)
        response = self.gateway.complete(request)

        return {
            "agent_id": agent_id,
            "llm_response": response.content,
            "success": response.success,
            "latency_ms": response.latency_ms,
            "tokens": response.total_tokens,
        }


# ─────────────────────────────────────────────────────────────────────────────
# MoE LLM Expert — wires MoE router to LLM responses
# ─────────────────────────────────────────────────────────────────────────────

class MoELLMExpert:
    """Routes legal queries through MoE router then generates LLM responses."""

    def __init__(self, gateway: Optional[LLMGateway] = None):
        self.gateway = gateway or LLMGateway()

    def answer(self, query: str) -> Dict[str, Any]:
        """Route query and generate an expert LLM response."""
        from phase16.moe_router.router import MoERouter
        from phase16.moe_router.models import RoutingRequest

        router = MoERouter()
        req = RoutingRequest(request_id=f"moe_{uuid.uuid4().hex[:6]}", text=query)
        route = router.route(req)

        expert_type = route.primary_expert.value
        system_prompt = (
            f"You are SintraPrime's {expert_type} law expert. "
            "Provide concise, accurate legal guidance. Always recommend consulting an attorney."
        )
        llm_req = LLMRequest(
            prompt=query,
            system_prompt=system_prompt,
            model=self.gateway.model,
        )
        response = self.gateway.complete(llm_req)

        return {
            "query": query,
            "expert": expert_type,
            "confidence": route.confidence_scores[0].score if route.confidence_scores else 0.0,
            "answer": response.content,
            "latency_ms": response.latency_ms,
            "tokens": response.total_tokens,
        }
