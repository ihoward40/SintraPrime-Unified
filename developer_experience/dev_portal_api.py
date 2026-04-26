"""
dev_portal_api.py — Developer Portal FastAPI Router
Serves OpenAPI specs, cookbook scenarios, model playground, and SDKs.
"""

from __future__ import annotations
import json
import io
from pathlib import Path
from typing import Any, Optional

try:
    from fastapi import APIRouter, HTTPException, Query
    from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse, Response
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Stubs for when FastAPI is not installed
    class APIRouter:
        def get(self, *a, **kw): return lambda f: f
        def post(self, *a, **kw): return lambda f: f
    class BaseModel: pass
    class HTTPException(Exception):
        def __init__(self, status_code, detail): pass

from .openapi_spec import build_openapi_spec
from .cookbook import SCENARIOS, get_scenario, list_scenarios, search_scenarios
from .model_playground import (
    PlaygroundBenchmark, SUPPORTED_MODELS, PROMPT_TEMPLATES,
    list_models, list_templates, get_template,
)
from .sdk_generator import PythonSDKGenerator, TypeScriptSDKGenerator, CurlExampleGenerator

router = APIRouter(prefix="/docs", tags=["Developer Portal"])
playground_router = APIRouter(prefix="/playground", tags=["Model Playground"])
cookbook_router = APIRouter(prefix="/cookbook", tags=["Cookbook"])
sdk_router = APIRouter(prefix="/sdk", tags=["SDK"])


# ---------------------------------------------------------------------------
# Pydantic models for request bodies
# ---------------------------------------------------------------------------

class PlaygroundRunRequest(BaseModel):
    model_a: str
    model_b: Optional[str] = None
    template_id: str
    variables: Optional[dict[str, str]] = None
    api_keys: Optional[dict[str, str]] = None


class PlaygroundBenchmarkRequest(BaseModel):
    model_ids: list[str]
    template_ids: list[str]
    variables: Optional[dict[str, str]] = None
    api_keys: Optional[dict[str, str]] = None


# ---------------------------------------------------------------------------
# OpenAPI spec endpoints
# ---------------------------------------------------------------------------

@router.get("/openapi.json", summary="Download OpenAPI spec (JSON)")
async def get_openapi_json():
    """
    Returns the complete SintraPrime-Unified OpenAPI 3.1 specification in JSON format.
    Covers all 10 modules: Legal, Trust, Banking, Governance, MCP, EI, App Builder,
    Observability, Compliance, and Workflow Builder.
    """
    spec = build_openapi_spec()
    return JSONResponse(content=spec)


@router.get("/openapi.yaml", summary="Download OpenAPI spec (YAML)")
async def get_openapi_yaml():
    """
    Returns the complete OpenAPI 3.1 specification in YAML format.
    """
    try:
        import yaml
        spec = build_openapi_spec()
        yaml_content = yaml.dump(spec, sort_keys=False, allow_unicode=True)
        return PlainTextResponse(content=yaml_content, media_type="application/x-yaml")
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="PyYAML not installed. Install with: pip install pyyaml"
        )


@router.get("/endpoints", summary="List all API endpoints summary")
async def list_endpoints():
    """Returns a structured summary of all available API endpoints."""
    spec = build_openapi_spec()
    endpoints = []
    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            endpoints.append({
                "method": method.upper(),
                "path": path,
                "operation_id": operation.get("operationId"),
                "summary": operation.get("summary"),
                "tags": operation.get("tags", []),
            })
    return {
        "total": len(endpoints),
        "endpoints": sorted(endpoints, key=lambda x: (x["tags"][0] if x["tags"] else "", x["path"])),
    }


@router.get("/schemas", summary="List all API schemas")
async def list_schemas():
    """Returns all component schemas from the OpenAPI spec."""
    spec = build_openapi_spec()
    schemas = spec.get("components", {}).get("schemas", {})
    return {
        "total": len(schemas),
        "schemas": list(schemas.keys()),
        "definitions": schemas,
    }


# ---------------------------------------------------------------------------
# Cookbook endpoints
# ---------------------------------------------------------------------------

@cookbook_router.get("", summary="List all cookbook scenarios")
async def list_cookbook():
    """
    Returns all 25+ cookbook scenarios with title, tags, difficulty, and description.
    """
    return {
        "total": len(SCENARIOS),
        "scenarios": list_scenarios(),
    }


@cookbook_router.get("/search", summary="Search cookbook scenarios")
async def search_cookbook(
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    difficulty: Optional[str] = Query(None, enum=["beginner", "intermediate", "advanced"]),
):
    """Search scenarios by tags and/or difficulty level."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    results = search_scenarios(tags=tag_list, difficulty=difficulty)
    return {
        "total": len(results),
        "scenarios": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "tags": s.tags,
                "difficulty": s.difficulty,
            }
            for s in results
        ],
    }


@cookbook_router.get("/{scenario_id}", summary="Get cookbook scenario with code")
async def get_cookbook_scenario(scenario_id: str):
    """
    Returns a specific cookbook scenario including the full runnable code,
    expected output, and metadata.
    """
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return {
        "id": scenario.id,
        "title": scenario.title,
        "description": scenario.description,
        "code": scenario.code.strip(),
        "expected_output": scenario.expected_output.strip(),
        "tags": scenario.tags,
        "difficulty": scenario.difficulty,
    }


# ---------------------------------------------------------------------------
# Model Playground endpoints
# ---------------------------------------------------------------------------

@playground_router.get("/models", summary="List supported LLM models")
async def list_playground_models():
    """Returns all supported LLM backends with pricing and capabilities."""
    return {
        "total": len(SUPPORTED_MODELS),
        "models": list_models(),
    }


@playground_router.get("/templates", summary="List prompt templates")
async def list_prompt_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
):
    """Returns the library of 50+ legal/financial prompt templates."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    return {
        "total": len(PROMPT_TEMPLATES),
        "templates": list_templates(category=category, tags=tag_list),
    }


@playground_router.get("/templates/{template_id}", summary="Get prompt template detail")
async def get_prompt_template(template_id: str):
    """Returns a specific prompt template with system prompt and variable schema."""
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return {
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "system_prompt": template.system_prompt,
        "user_template": template.user_template,
        "variables": template.variables,
        "tags": template.tags,
    }


@playground_router.post("/run", summary="Run model comparison or benchmark")
async def run_playground(request: PlaygroundRunRequest):
    """
    Run a model comparison:
    - If model_b is provided: A/B test between model_a and model_b
    - If only model_a: Single model inference

    Requires valid template_id and optional variable substitutions.
    API keys can be passed per-provider in the api_keys dict.
    """
    bench = PlaygroundBenchmark(api_keys=request.api_keys or {})

    if request.model_b:
        # A/B test
        try:
            result = bench.ab_test(
                request.model_a,
                request.model_b,
                request.template_id,
                request.variables,
            )
            return {
                "mode": "ab_test",
                "winner": result.winner,
                "summary": result.comparison_summary,
                "result_a": {
                    "model": result.model_a,
                    "latency_ms": result.result_a.latency_ms,
                    "quality_score": result.result_a.quality_score,
                    "cost_usd": result.result_a.cost_usd,
                    "response_preview": result.result_a.response[:300] + "..." if len(result.result_a.response) > 300 else result.result_a.response,
                },
                "result_b": {
                    "model": result.model_b,
                    "latency_ms": result.result_b.latency_ms,
                    "quality_score": result.result_b.quality_score,
                    "cost_usd": result.result_b.cost_usd,
                    "response_preview": result.result_b.response[:300] + "..." if len(result.result_b.response) > 300 else result.result_b.response,
                },
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Single model
        try:
            result = bench.run_single(request.model_a, request.template_id, request.variables)
            return {
                "mode": "single",
                "model": result.model_id,
                "latency_ms": result.latency_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd,
                "quality_score": result.quality_score,
                "response": result.response,
                "error": result.error,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@playground_router.post("/benchmark", summary="Benchmark multiple models across multiple prompts")
async def run_benchmark(request: PlaygroundBenchmarkRequest):
    """
    Run a full benchmark suite: multiple models × multiple prompt templates.
    Returns raw results and a leaderboard ranked by overall score.
    """
    bench = PlaygroundBenchmark(api_keys=request.api_keys or {})
    try:
        results = bench.run_suite(
            request.model_ids,
            request.template_ids,
            request.variables,
        )
        leaderboard = bench.leaderboard(results)
        return {
            "total_runs": len(results),
            "leaderboard": leaderboard,
            "results": [
                {
                    "model_id": r.model_id,
                    "prompt_id": r.prompt_id,
                    "latency_ms": r.latency_ms,
                    "cost_usd": r.cost_usd,
                    "quality_score": r.quality_score,
                    "error": r.error,
                }
                for r in results
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@playground_router.get("/cost-estimate", summary="Estimate cost for a model")
async def cost_estimate(
    model_id: str = Query(..., description="Model ID to estimate cost for"),
    input_tokens: int = Query(500, description="Estimated input tokens per request"),
    output_tokens: int = Query(300, description="Estimated output tokens per request"),
):
    """Estimate API cost for different request volumes."""
    bench = PlaygroundBenchmark()
    try:
        return bench.cost_estimate(model_id, input_tokens, output_tokens)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")


# ---------------------------------------------------------------------------
# SDK endpoints
# ---------------------------------------------------------------------------

@sdk_router.get("/python", summary="Download Python SDK")
async def download_python_sdk():
    """
    Returns the auto-generated Python SDK for SintraPrime-Unified.
    Includes all API client classes, data models, retry logic, and auth.
    """
    spec = build_openapi_spec()
    generator = PythonSDKGenerator(spec)
    code = generator.generate()
    return Response(
        content=code,
        media_type="text/x-python",
        headers={"Content-Disposition": 'attachment; filename="sintraprime_sdk.py"'},
    )


@sdk_router.get("/typescript", summary="Download TypeScript SDK")
async def download_typescript_sdk():
    """
    Returns the auto-generated TypeScript/JavaScript SDK for SintraPrime-Unified.
    Includes typed interfaces, async/await API methods, and error handling.
    """
    spec = build_openapi_spec()
    generator = TypeScriptSDKGenerator(spec)
    code = generator.generate()
    return Response(
        content=code,
        media_type="text/typescript",
        headers={"Content-Disposition": 'attachment; filename="sintraprime_sdk.ts"'},
    )


@sdk_router.get("/curl", summary="Download curl examples")
async def download_curl_examples():
    """
    Returns a Markdown file with curl examples for every API endpoint.
    """
    spec = build_openapi_spec()
    generator = CurlExampleGenerator(spec)
    examples = generator.generate_all()

    lines = ["# SintraPrime API — curl Examples", "", f"Total endpoints: {len(examples)}", ""]
    by_tag: dict[str, list] = {}
    for ex in examples:
        tags = ex["tags"] or ["Other"]
        for tag in tags:
            by_tag.setdefault(tag, []).append(ex)

    for tag, tag_examples in sorted(by_tag.items()):
        lines.append(f"## {tag}")
        lines.append("")
        for ex in tag_examples:
            lines.append(f"### {ex['summary']}")
            lines.append(f"`{ex['method']} {ex['path']}`")
            lines.append("")
            lines.append("```bash")
            lines.append(ex["curl"])
            lines.append("```")
            lines.append("")

    content = "\n".join(lines)
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="curl_examples.md"'},
    )


@sdk_router.get("/info", summary="SDK generation info")
async def sdk_info():
    """Returns metadata about what SDKs are available and their contents."""
    spec = build_openapi_spec()
    paths = spec.get("paths", {})
    schemas = spec.get("components", {}).get("schemas", {})

    endpoint_count = sum(
        len([m for m, v in methods.items() if isinstance(v, dict)])
        for methods in paths.values()
    )

    return {
        "available_sdks": ["python", "typescript", "curl"],
        "spec_stats": {
            "total_endpoints": endpoint_count,
            "total_schemas": len(schemas),
            "api_version": spec["info"]["version"],
        },
        "download_urls": {
            "python": "/sdk/python",
            "typescript": "/sdk/typescript",
            "curl_examples": "/sdk/curl",
        },
    }


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

general_router = APIRouter(tags=["General"])


@general_router.get("/health", summary="Portal health check")
async def health_check():
    """Returns developer portal health status."""
    spec = build_openapi_spec()
    return {
        "status": "ok",
        "version": spec["info"]["version"],
        "modules": {
            "openapi_spec": True,
            "cookbook": len(SCENARIOS) > 0,
            "model_playground": len(SUPPORTED_MODELS) > 0,
            "sdk_generator": True,
        },
        "counts": {
            "cookbook_scenarios": len(SCENARIOS),
            "llm_models": len(SUPPORTED_MODELS),
            "prompt_templates": len(PROMPT_TEMPLATES),
            "api_schemas": len(spec.get("components", {}).get("schemas", {})),
        },
    }


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_dev_portal_app():
    """Create and return the complete developer portal FastAPI application."""
    if not FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI not installed. Run: pip install fastapi uvicorn")

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="SintraPrime Developer Portal",
        description=(
            "Interactive developer portal for SintraPrime-Unified API. "
            "Browse OpenAPI specs, run cookbook scenarios, test models, and download SDKs."
        ),
        version="2.0.0",
        docs_url="/",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(general_router)
    app.include_router(router)
    app.include_router(cookbook_router)
    app.include_router(playground_router)
    app.include_router(sdk_router)

    return app


if __name__ == "__main__":
    try:
        import uvicorn
        app = create_dev_portal_app()
        uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
    except ImportError:
        print("Install with: pip install fastapi uvicorn pyyaml")
