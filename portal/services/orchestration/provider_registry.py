"""Provider registry with deterministic Milestone One mock providers."""

from __future__ import annotations

from .schemas import ProviderCapability, Sensitivity, TaskType


def mock_provider_registry() -> list[ProviderCapability]:
    """Return declared mock-provider capabilities; no external providers are connected."""
    base_policy = {"external": False, "paid": False, "retention": "none", "mock_only": True}
    return [
        ProviderCapability(
            provider_id="reasoning_model",
            model_id="mock-reasoning-v1",
            supported_task_types=[TaskType.OPERATIONS, TaskType.MIXED, TaskType.DOCUMENT_GENERATION, TaskType.MARKETING],
            context_window=32000,
            structured_output=True,
            tool_support=[],
            coding_strength=0.4,
            reasoning_strength=0.9,
            research_strength=0.5,
            verification_strength=0.5,
            latency_class="fast",
            input_cost=0.0,
            output_cost=0.0,
            availability="available",
            data_policy=base_policy,
            allowed_sensitivity=list(Sensitivity),
        ),
        ProviderCapability(
            provider_id="coding_model",
            model_id="mock-coding-v1",
            supported_task_types=[TaskType.CODING, TaskType.SECURITY, TaskType.MIXED],
            context_window=24000,
            structured_output=True,
            tool_support=["tests"],
            coding_strength=0.9,
            reasoning_strength=0.6,
            research_strength=0.2,
            verification_strength=0.4,
            latency_class="fast",
            input_cost=0.0,
            output_cost=0.0,
            availability="available",
            data_policy=base_policy,
            allowed_sensitivity=[Sensitivity.PUBLIC, Sensitivity.INTERNAL, Sensitivity.CONFIDENTIAL],
        ),
        ProviderCapability(
            provider_id="research_model",
            model_id="mock-research-v1",
            supported_task_types=[TaskType.RESEARCH, TaskType.LEGAL_INFORMATION, TaskType.FINANCIAL_ANALYSIS, TaskType.MIXED],
            context_window=64000,
            structured_output=True,
            tool_support=["citations"],
            coding_strength=0.1,
            reasoning_strength=0.6,
            research_strength=0.9,
            verification_strength=0.5,
            latency_class="standard",
            input_cost=0.0,
            output_cost=0.0,
            availability="available",
            data_policy=base_policy,
            allowed_sensitivity=[Sensitivity.PUBLIC, Sensitivity.INTERNAL, Sensitivity.CONFIDENTIAL],
        ),
        ProviderCapability(
            provider_id="checker_model",
            model_id="mock-checker-v1",
            supported_task_types=list(TaskType),
            context_window=32000,
            structured_output=True,
            tool_support=["verification"],
            coding_strength=0.5,
            reasoning_strength=0.7,
            research_strength=0.6,
            verification_strength=0.95,
            latency_class="fast",
            input_cost=0.0,
            output_cost=0.0,
            availability="available",
            data_policy=base_policy,
            allowed_sensitivity=list(Sensitivity),
        ),
        ProviderCapability(
            provider_id="security_model",
            model_id="mock-security-v1",
            supported_task_types=[TaskType.SECURITY, TaskType.CODING, TaskType.OPERATIONS, TaskType.MIXED],
            context_window=16000,
            structured_output=True,
            tool_support=["security_review"],
            coding_strength=0.6,
            reasoning_strength=0.7,
            research_strength=0.3,
            verification_strength=0.85,
            latency_class="fast",
            input_cost=0.0,
            output_cost=0.0,
            availability="available",
            data_policy=base_policy,
            allowed_sensitivity=list(Sensitivity),
        ),
    ]


def provider_by_id(provider_id: str, providers: list[ProviderCapability] | None = None) -> ProviderCapability | None:
    for provider in providers or mock_provider_registry():
        if provider.provider_id == provider_id:
            return provider
    return None
