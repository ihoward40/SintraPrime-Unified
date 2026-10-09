"""DecisionEngine facade: provider -> policy -> ledger (R1 engine)."""
from __future__ import annotations

import time
from typing import Optional, Tuple

from decision.canonical.jcs import state_sha256
from decision.contracts.contracts import contract_sha256, normalize_contract
from decision.engine.types import DecisionContract, DecisionResult, PolicyDisposition, ResultKind
from decision.ledger.ledger import Ledger
from decision.policy.policy import apply_policy
from decision.providers.config import Settings
from decision.providers.mock import MockDecisionProvider


def _contract_hash(contract: DecisionContract) -> str:
    norm = normalize_contract({
        "name": contract.name,
        "risk": contract.risk.name,
        "questions": contract.questions,
    })
    return contract_sha256(norm)


class DecisionEngine:
    def __init__(self, settings: Settings, provider=None, ledger: Optional[Ledger] = None):
        self.settings = settings
        self.provider = provider or MockDecisionProvider(settings)
        self.ledger = ledger if ledger is not None else Ledger()

    async def evaluate(self, state: dict, contract: DecisionContract
                       ) -> Tuple[DecisionResult, PolicyDisposition, dict]:
        s_hash = state_sha256({k: v for k, v in state.items() if not str(k).startswith("_mock_")})
        c_hash = _contract_hash(contract)
        start = time.monotonic()
        result = await self.provider.evaluate(state=state, contract=contract)
        latency = round((time.monotonic() - start) * 1000.0, 3)
        disposition = apply_policy(result, self.settings.shadow_only, contract)
        receipt = self.ledger.append(
            state_sha256=s_hash, contract_sha256=c_hash,
            provider_request_id=result.provider_request_id, latency_ms=latency,
            kind=result.kind.value, disposition=disposition.value,
        )
        return result, disposition, receipt
