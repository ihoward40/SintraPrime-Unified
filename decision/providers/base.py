"""DecisionProvider protocol — the ONLY extension point for decision models."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts.contracts import DecisionContract
from ..engine.types import DecisionResult


@runtime_checkable
class DecisionProvider(Protocol):
    """All providers MUST return a DecisionResult and never raise for
    provider-side failure: failures are first-class results
    (ResultKind.ERROR / ResultKind.UNAVAILABLE) so the fabric can fail closed.
    """

    name: str
    model: str

    async def evaluate(self, *, state: dict, contract: DecisionContract) -> DecisionResult:
        """Evaluate canonical state against the contract.

        Implementations must:
        - never leak provider terminology into canonical types
        - return ResultKind.UNAVAILABLE on transport/outage problems
        - return ResultKind.ERROR on malformed/contract-mismatched responses
        - return ResultKind.ABSTAIN when the provider says it cannot classify
        """
        ...
