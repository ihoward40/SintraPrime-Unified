"""
Local Models API — SintraPrime-Unified local_models
FastAPI router exposing model availability, completion, Ollama
management, memory checks, and offline mode controls.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/models", tags=["local-models"])

# ---------------------------------------------------------------------------
# Dependency: lazy-load singletons
# ---------------------------------------------------------------------------

_ollama_client = None
_deepseek_client = None
_model_router = None
_quant_manager = None
_offline_manager = None


def get_ollama():
    global _ollama_client
    if _ollama_client is None:
        from local_models.ollama_client import OllamaClient
        _ollama_client = OllamaClient(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434")
        )
    return _ollama_client


def get_model_router():
    global _model_router
    if _model_router is None:
        from local_models.model_router import ModelRouter
        _model_router = ModelRouter(
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
    return _model_router


def get_quant_manager():
    global _quant_manager
    if _quant_manager is None:
        from local_models.quantization_manager import QuantizationManager
        _quant_manager = QuantizationManager()
    return _quant_manager


def get_offline_manager():
    global _offline_manager
    if _offline_manager is None:
        from local_models.offline_manager import OfflineMode
        _offline_manager = OfflineMode()
    return _offline_manager


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CompleteRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to complete.")
    model: str = Field("auto", description="Model name or 'auto' for automatic selection.")
    task: str = Field("general", description="Task type for routing (e.g. legal_research, chat).")
    system: Optional[str] = Field(None, description="Optional system prompt.")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature.")
    max_tokens: int = Field(2048, ge=1, le=32768, description="Max tokens to generate.")


class CompleteResponse(BaseModel):
    content: str
    provider: str
    model: str
    task_type: str
    latency_s: float
    cost_usd: float = 0.0
    thinking: Optional[str] = None
    error: Optional[str] = None


class OllamaPullRequest(BaseModel):
    model: str = Field(..., description="Ollama model name to pull (e.g. 'llama3', 'mistral').")


class AirGapRequest(BaseModel):
    enabled: bool = Field(..., description="True to enable air-gap mode, False to disable.")


class ModelAvailableResponse(BaseModel):
    ollama_available: bool
    deepseek_configured: bool
    openai_configured: bool
    anthropic_configured: bool
    local_models: List[str]
    providers: Dict[str, bool]
    recommended_models: List[str]


class MemoryCheckResponse(BaseModel):
    available_ram_gb: float
    can_run: Dict[str, List[str]]
    recommendations: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/available",
    response_model=ModelAvailableResponse,
    summary="List all available models and providers",
)
async def get_available_models():
    """
    Return information about all available local and cloud models,
    including Ollama status, API key availability, and local model list.
    """
    ollama = get_ollama()
    mr = get_model_router()

    ollama_ok = ollama.is_available()
    local_models: List[str] = []
    if ollama_ok:
        try:
            models_data = ollama.list_models()
            local_models = [m.get("name", "") for m in models_data]
        except Exception:
            pass

    status_info = mr.status()

    from local_models.ollama_client import LEGAL_RECOMMENDED_MODELS
    return ModelAvailableResponse(
        ollama_available=ollama_ok,
        deepseek_configured=bool(os.getenv("DEEPSEEK_API_KEY")),
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        anthropic_configured=bool(os.getenv("ANTHROPIC_API_KEY")),
        local_models=local_models,
        providers=status_info.get("providers", {}),
        recommended_models=LEGAL_RECOMMENDED_MODELS,
    )


@router.post(
    "/complete",
    response_model=CompleteResponse,
    summary="Run a completion with automatic model routing",
)
async def complete(request: CompleteRequest):
    """
    Generate a completion using the best available model.
    Automatically selects provider (Ollama → DeepSeek → OpenAI → Anthropic)
    based on task type and availability.
    """
    mr = get_model_router()
    offline = get_offline_manager()

    # Block external calls in air-gap mode
    if offline.air_gap_enabled:
        # Force Ollama-only
        from local_models.model_router import TaskType, Provider
        task_type = mr._resolve_task_type(request.task)
        if not mr._is_available(Provider.OLLAMA):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Air-gap mode enabled and Ollama is not available.",
            )

    try:
        result = mr.complete(
            prompt=request.prompt,
            model=request.model,
            task=request.task,
            system=request.system,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as exc:
        logger.error("Completion error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return CompleteResponse(
        content=result.content,
        provider=result.provider.value,
        model=result.model,
        task_type=result.task_type.value,
        latency_s=result.latency_s,
        cost_usd=result.cost_usd,
        thinking=result.thinking,
        error=result.error,
    )


@router.get(
    "/ollama/status",
    summary="Check Ollama daemon health",
)
async def ollama_status():
    """Return health and status of the local Ollama instance."""
    ollama = get_ollama()
    try:
        health = ollama.health_check()
        capability = ollama.capability_report()
        return {
            "health": health,
            "capabilities": capability,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama not reachable: {exc}",
        )


@router.post(
    "/ollama/pull",
    summary="Pull a new model into Ollama",
)
async def ollama_pull(request: OllamaPullRequest, background_tasks: BackgroundTasks):
    """
    Trigger a model pull from the Ollama registry.
    The pull runs in the background; use /ollama/status to monitor.
    """
    ollama = get_ollama()
    if not ollama.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama is not running. Start with: ollama serve",
        )

    def _pull():
        logger.info("Pulling model: %s", request.model)
        for chunk in ollama.pull_model(request.model):
            logger.debug("Pull progress: %s", chunk.get("status"))
        logger.info("Model pull complete: %s", request.model)

    background_tasks.add_task(_pull)
    return {
        "message": f"Pull of '{request.model}' started in background.",
        "model": request.model,
    }


@router.get(
    "/memory-check",
    response_model=MemoryCheckResponse,
    summary="Show what models can run on this hardware",
)
async def memory_check(
    ram_gb: Optional[float] = Query(None, description="Override RAM amount (GB).")
):
    """
    Calculate which models and quantizations fit in available RAM.
    Returns a recommendation list sorted by quality/speed balance.
    """
    qm = get_quant_manager()
    effective_ram = ram_gb or qm.available_ram_gb
    can_run = qm.what_can_i_run(ram_gb=effective_ram)

    # Build recommendations for common models
    recs = []
    for model in ["llama3", "mistral", "deepseek-r1", "hermes3"]:
        rec_list = qm.recommend_quantization(model)
        for r in rec_list[:3]:  # top 3 per model
            if r.suitable:
                recs.append({
                    "model": model,
                    "quant": r.quant,
                    "size_gb": r.size_gb,
                    "quality": r.quality,
                    "speed": r.speed,
                    "notes": r.notes,
                })

    return MemoryCheckResponse(
        available_ram_gb=effective_ram,
        can_run=can_run,
        recommendations=recs,
    )


@router.post(
    "/offline/enable",
    summary="Enable or disable air-gap mode",
)
async def set_offline_mode(request: AirGapRequest):
    """
    Enable air-gap mode to block all external API calls,
    or disable it to restore normal operation.
    """
    offline = get_offline_manager()
    if request.enabled:
        offline.enable_air_gap()
        return {
            "air_gap_enabled": True,
            "message": "Air-gap mode ON — all external APIs are now blocked.",
        }
    else:
        offline.disable_air_gap()
        return {
            "air_gap_enabled": False,
            "message": "Air-gap mode OFF — external APIs are allowed.",
        }


@router.get(
    "/offline/status",
    summary="Check offline mode and connectivity status",
)
async def offline_status():
    """Return offline/online status and capability report."""
    offline = get_offline_manager()
    return {
        "status": offline.status(),
        "capability_report": offline.capability_report(),
        "available_templates": offline.list_templates(),
    }


@router.get(
    "/routing-plan",
    summary="Show routing plan for a task without executing",
)
async def routing_plan(
    task: str = Query("general", description="Task type (e.g. legal_research, chat)")
):
    """Return which provider and model would be selected for the given task."""
    mr = get_model_router()
    return mr.routing_plan(task)
