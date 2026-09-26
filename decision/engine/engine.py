"""DecisionEngine — the fabric facade. Orchestrates provider -> policy -> ledger."""

from __future__ import annotations

import uuid
from typing import Optional

from ..canonical.jcs import canonical_state
from ..ledger.ledger import Ledger, build_receipt
from ..policy.policy import PolicyDecision, apply_policy
from ..providers.base import DecisionProvider


class DecisionEngine:
    def __init__(self, provider: DecisionProvider, *, shadow_only: bool = True,
                 ledger: Optional[Ledger] = None) -> None:
        self.provider = provider
        self.shadow_only = shadow_only
        self.ledger = ledger if ledger is not None else Ledger()

    async def evaluate(self, *, state: dict, contract: DecisionContract,
                       run_id: Optional[str] = None) -> tuple[DecisionResult, PolicyDecision, dict]:
        canonical = canonical_state(state)
        result = await self.provider.evaluate(state=state, contract=contract)
        policy = apply_policy(result, shadow_only=self.shadow_only)
        decision_id = f"DEC-{uuid.uuid4().hex[:12].upper()}"
        receipt = build_receipt(
            decision_id=decision_id,
            run_id=run_id or f"RUN-{uuid.uuid4().hex[:12].upper()}",
            state=canonical,
            contract_raw=contract.raw,
            result=result,
            policy=policy,
        )
        stored = self.ledger.append(receipt)
        return result, policy, stored
