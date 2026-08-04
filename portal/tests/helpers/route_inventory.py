"""Version-tolerant recursive route inventory for API-surface tests."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResolvedRoute:
    """A terminal route paired with its fully resolved mounted path."""

    path: str
    route: Any


def normalize_route_path(path: str) -> str:
    """Return a stable absolute route path with duplicate slashes removed."""
    if not path:
        return ""
    normalized = path.replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    if normalized and not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if len(normalized) > 1:
        normalized = normalized.rstrip("/")
    return normalized


def _join_paths(prefix: str, segment: str) -> str:
    if not prefix:
        return normalize_route_path(segment)
    if not segment:
        return normalize_route_path(prefix)
    return normalize_route_path(f"{prefix}/{segment}")


def _route_collection(value: Any) -> tuple[Any, ...]:
    if value is None or isinstance(value, (str, bytes)):
        return ()
    if isinstance(value, Iterable):
        return tuple(value)
    return ()


def iter_resolved_routes(app_or_routes: Any) -> Iterator[ResolvedRoute]:
    """Yield every terminal route across FastAPI/Starlette container shapes.

    Supported containers include ``APIRoute`` leaves, Starlette ``Mount``
    objects, nested ``.routes`` collections, and FastAPI ``_IncludedRouter``
    wrappers that expose ``.original_router.routes`` with an
    ``.include_context.prefix``. Recursion is cycle-safe without suppressing a
    router that is legitimately included under more than one prefix.
    """

    root_routes = getattr(app_or_routes, "routes", app_or_routes)
    yield from _iter_routes(_route_collection(root_routes), prefix="", ancestors=frozenset())


def _iter_routes(
    routes: tuple[Any, ...],
    *,
    prefix: str,
    ancestors: frozenset[int],
) -> Iterator[ResolvedRoute]:
    for route in routes:
        route_id = id(route)
        if route_id in ancestors:
            continue
        next_ancestors = ancestors | {route_id}

        original_router = getattr(route, "original_router", None)
        original_routes = _route_collection(getattr(original_router, "routes", None))
        if original_routes:
            include_context = getattr(route, "include_context", None)
            include_prefix = getattr(include_context, "prefix", "") if include_context else ""
            yield from _iter_routes(
                original_routes,
                prefix=_join_paths(prefix, include_prefix),
                ancestors=next_ancestors,
            )
            continue

        route_path = getattr(route, "path", "") or ""
        resolved_path = _join_paths(prefix, route_path)
        direct_routes = _route_collection(getattr(route, "routes", None))
        if direct_routes:
            yield from _iter_routes(
                direct_routes,
                prefix=resolved_path,
                ancestors=next_ancestors,
            )
            continue

        yield ResolvedRoute(path=resolved_path, route=route)
