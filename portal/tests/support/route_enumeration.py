"""Shared test helpers for route enumeration across FastAPI versions.

FastAPI 0.139+ wraps included routers in ``_IncludedRouter`` objects that do
not expose ``.path`` or ``.routes`` directly.  Direct iteration over
``app.routes`` therefore misses terminal routes on newer FastAPI versions.

This module provides :func:`iter_terminal_routes`, a recursive, cycle-safe
iterator that handles all known route-container shapes:

- ``Mount`` / ``APIRouter`` — children via ``.routes``, prefix from ``.path``
- ``_IncludedRouter`` (FastAPI 0.139+) — children via
  ``.original_router.routes``, prefix from ``.include_context.prefix``

Only terminal (leaf) routes are yielded.  The helper supports both old and
new FastAPI/Starlette route structures and does not silently omit nested
application routes.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


def _normalize_path(path: str) -> str:
    """Normalize a route path by collapsing duplicate slashes."""
    if not path:
        return ""
    normalized = path
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized


def iter_terminal_routes(
    routes: list[Any],
    prefix: str = "",
    _visited: set[int] | None = None,
) -> Iterator[tuple[str, Any]]:
    """Recursively flatten the route tree, yielding ``(full_path, route)``.

    Handles all known route-container shapes across FastAPI/Starlette
    versions without relying on private class names:

    - ``Mount`` / ``APIRouter``: children exposed via ``.routes``,
      prefix from ``route.path``.
    - ``_IncludedRouter`` (FastAPI 0.139+): children exposed via
      ``.original_router.routes``, prefix from
      ``.include_context.prefix``.  Does NOT have ``.routes`` or
      ``.path``.

    Only terminal (leaf) routes are yielded.  Cycle-safe via an
    ``id()``-based visited set.
    """
    if _visited is None:
        _visited = set()
    for route in routes:
        rid = id(route)
        if rid in _visited:
            continue
        _visited.add(rid)

        # Determine this route's own path segment and child collection.
        # _IncludedRouter has no .path; its prefix lives in include_context.
        route_path = getattr(route, "path", "") or ""
        child_prefix = f"{prefix}{route_path}"

        # Collect child routes from every known container shape.
        child_collections: list[list[Any]] = []

        # Shape 1: Mount / APIRouter — direct .routes attribute
        direct_routes = getattr(route, "routes", None)
        if direct_routes and isinstance(direct_routes, list):
            child_collections.append(direct_routes)

        # Shape 2: _IncludedRouter (FastAPI 0.139+) —
        # .original_router.routes + .include_context.prefix
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            orig_routes = getattr(original_router, "routes", None)
            if orig_routes and isinstance(orig_routes, list):
                ctx = getattr(route, "include_context", None)
                ctx_prefix = getattr(ctx, "prefix", "") if ctx else ""
                # _IncludedRouter contributes its own prefix, not .path
                child_collections.append(orig_routes)
                child_prefix = f"{prefix}{ctx_prefix}"

        if child_collections:
            for children in child_collections:
                yield from iter_terminal_routes(children, child_prefix, _visited)
        else:
            yield _normalize_path(child_prefix), route


def get_terminal_route_paths(app: Any) -> set[str]:
    """Return a set of all terminal route paths from a FastAPI app.

    This is the direct replacement for ``{route.path for route in app.routes}``
    that safely handles ``_IncludedRouter`` wrappers.
    """
    return {full_path for full_path, _route in iter_terminal_routes(app.routes)}
