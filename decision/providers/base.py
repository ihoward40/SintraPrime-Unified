"""DecisionProvider protocol — the ONLY extension point (R1)."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from decision.engine.types import DecisionContract, DecisionResult


@runtime_checkable
class DecisionProvider(Protocol):
    name: str
    model: str

    async def evaluate(self, *, state: dict, contract: DecisionContract) -> DecisionResult:
        ...
