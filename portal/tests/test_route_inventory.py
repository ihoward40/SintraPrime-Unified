"""Contract tests for the shared recursive route inventory."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import APIRouter, FastAPI
from starlette.routing import Mount

from portal.tests.helpers.route_inventory import iter_resolved_routes, normalize_route_path


def test_inventory_resolves_api_routes_and_nested_mounts() -> None:
    nested = FastAPI()

    @nested.get("/health/")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app = FastAPI()
    app.mount("/api//v1", nested)

    paths = {item.path for item in iter_resolved_routes(app)}
    assert "/api/v1/health" in paths


def test_inventory_resolves_included_router_context_prefix() -> None:
    router = APIRouter()

    @router.get("/commands")
    async def commands() -> dict[str, list]:
        return {"commands": []}

    included_router = SimpleNamespace(
        original_router=router,
        include_context=SimpleNamespace(prefix="/api/v1/mission-control"),
    )

    paths = {item.path for item in iter_resolved_routes([included_router])}
    assert paths == {"/api/v1/mission-control/commands"}


def test_inventory_is_cycle_safe() -> None:
    cyclic = SimpleNamespace(path="/cycle", routes=[])
    cyclic.routes.append(cyclic)
    assert list(iter_resolved_routes([cyclic])) == []


def test_inventory_preserves_same_router_under_distinct_prefixes() -> None:
    app = FastAPI()
    router = APIRouter()

    @router.get("/status")
    async def status() -> dict[str, str]:
        return {"status": "ok"}

    app.router.routes.extend(
        [
            Mount("/one", routes=router.routes),
            Mount("/two", routes=router.routes),
        ]
    )

    paths = {item.path for item in iter_resolved_routes(app)}
    assert "/one/status" in paths
    assert "/two/status" in paths


def test_normalize_route_path_collapses_slashes_and_trailing_separator() -> None:
    assert normalize_route_path("api//v1///commands/") == "/api/v1/commands"
