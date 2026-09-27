"""Bounded, provenance-aware context packaging for long-context models."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextItem:
    source_id: str
    text: str
    token_estimate: int
    relevance: float = 0.0
    provenance: str = "unknown"
    required: bool = False


@dataclass
class ContextPack:
    items: list[ContextItem] = field(default_factory=list)
    token_budget: int = 0

    @property
    def tokens(self) -> int:
        return sum(i.token_estimate for i in self.items)

    def render(self) -> str:
        return "\n\n".join(
            f"[SOURCE {i.source_id} | provenance={i.provenance}]\n{i.text}" for i in self.items
        )


class ContextPackBuilder:
    def __init__(self, token_budget: int):
        if token_budget <= 0:
            raise ValueError("token_budget must be positive")
        self.token_budget = token_budget

    def build(self, items: Iterable[ContextItem]) -> ContextPack:
        pool = list(items)
        for item in pool:
            if item.token_estimate < 0:
                raise ValueError("token_estimate cannot be negative")
        required = [i for i in pool if i.required]
        if sum(i.token_estimate for i in required) > self.token_budget:
            raise ValueError("REQUIRED_CONTEXT_EXCEEDS_BUDGET")
        selected = list(required)
        selected_ids = {id(item) for item in selected}
        remaining = sorted(
            (i for i in pool if id(i) not in selected_ids),
            key=lambda i: (-i.relevance, i.token_estimate, i.source_id),
        )
        used = sum(i.token_estimate for i in selected)
        for item in remaining:
            if used + item.token_estimate <= self.token_budget:
                selected.append(item)
                used += item.token_estimate
        return ContextPack(selected, self.token_budget)
