"""Effect receipts with idempotency (§20, §117, §140)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from collaboration.services.store import CollaborationStore


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class EffectReceipt:
    """Immutable receipt for external/internal consequential effects (§117)."""

    effect_id: str
    operation: str
    target: str
    idempotency_key: str = ""
    before_state: str = ""
    after_state: str = ""
    authorization: str = ""
    result: str = ""
    tenant_id: str = ""
    actor_id: str = ""
    created_at: str = field(default_factory=_now)
    previous_hash: str = ""
    receipt_hash: str = ""


class EffectService:
    """Effect-level idempotency: retries return the existing effect result (§20)."""

    def __init__(self, store: CollaborationStore, *, effects_dir: str | None = None):
        self.store = store
        self.effects_dir = Path(effects_dir) if effects_dir else None

    def _hash(self, receipt: dict) -> str:
        # hash covers all fields except receipt_hash itself
        payload = {k: v for k, v in receipt.items() if k != "receipt_hash"}
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def apply(
        self,
        *,
        effect_id: str,
        operation: str,
        target: str,
        idempotency_key: str,
        before_state: str,
        after_state: str,
        authorization: str,
        result: str,
        tenant_id: str = "",
        actor_id: str = "",
    ) -> EffectReceipt:
        """If key exists → return existing receipt (no duplicate effect)."""
        existing = self.store.load("effects", idempotency_key, EffectReceipt)
        if existing is not None:
            return existing

        receipt = EffectReceipt(
            effect_id=effect_id,
            operation=operation,
            target=target,
            idempotency_key=idempotency_key,
            before_state=before_state,
            after_state=after_state,
            authorization=authorization,
            result=result,
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        receipt.receipt_hash = self._hash(asdict(receipt))
        self.store.save("effects", idempotency_key, receipt)
        return receipt

    def get(self, idempotency_key: str) -> EffectReceipt | None:
        return self.store.load("effects", idempotency_key, EffectReceipt)

    def verify_hash(self, idempotency_key: str) -> bool:
        receipt = self.get(idempotency_key)
        if receipt is None:
            return False
        return self._hash(asdict(receipt)) == receipt.receipt_hash
