"""Runtime fail-closed adapters for legacy mutation surfaces."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from portal.services.jarvis_legacy_containment import LegacySurface, require_governed_b2_context


def guarded_legacy_mutation(*, surface: LegacySurface, governed_context: Any | None, mutation: Callable[..., Any], **kwargs: Any) -> Any:
    """Invoke a legacy callable only when a canonical governed context exists."""
    require_governed_b2_context(surface=surface, governed=governed_context is not None)
    return mutation(governed_context=governed_context, **kwargs)


def legacy_mutation_guard(surface: LegacySurface, governed: bool = False) -> None:
    require_governed_b2_context(surface=surface, governed=governed)
