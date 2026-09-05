"""B2-B9 deterministic, immutable, non-authorizing receipts."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from typing import Any, Iterable


class ReceiptCreationDeniedError(ValueError):
    """Execution evidence cannot produce a trustworthy receipt."""


@dataclass(frozen=True)
class ActionReceipt:
    receipt_id: str
    receipt_schema_version: str
    tenant_id: str
    mission_id: str
    action_id: str
    operation_id: str
    attempt_id: str
    principal_id: str
    approval_id: str
    capability_id: str
    capability_version: str
    capability_contract_hash: str
    approved_contract_hash: str
    runtime_contract_hash: str
    operation_contract_hash: str
    registry_revision: int
    lease_id: str
    lease_revision: int
    credential_grant_id: str
    executor_id: str
    executor_version: str
    executor_artifact_hash: str
    adapter_id: str
    adapter_version: str
    adapter_artifact_hash: str
    operation: str
    target: str
    params_hash: str
    pre_state_hash: str
    provider_result_hash: str
    post_state_hash: str
    verification_status: str
    verification_reason: str
    execution_started_at: str
    execution_completed_at: str
    verified_at: str
    receipt_created_at: str
    previous_receipt_hash: str | None
    receipt_hash: str

    @classmethod
    def create(cls, *, previous_receipt_hash: str | None = None, **values: Any) -> ActionReceipt:
        values.setdefault("receipt_id", str(uuid.uuid4()))
        values.setdefault("receipt_schema_version", "1")
        values.setdefault("receipt_created_at", datetime.now(UTC).isoformat())
        values["previous_receipt_hash"] = previous_receipt_hash
        values["receipt_hash"] = ""
        if any(values.get(key) != values.get("approved_contract_hash") for key in (
            "runtime_contract_hash", "operation_contract_hash", "capability_contract_hash"
        )):
            raise ReceiptCreationDeniedError("RECEIPT_CREATION_DENIED:CONTRACT_HASH_MISMATCH")
        if not values.get("verification_status") or not values.get("post_state_hash"):
            raise ReceiptCreationDeniedError("RECEIPT_CREATION_DENIED:INCOMPLETE_EVIDENCE")
        candidate = cls(**values)
        return replace(candidate, receipt_hash=receipt_hash(candidate))

    def to_safe_dict(self) -> dict[str, Any]:
        return asdict(self)

    def as_authority(self) -> None:
        raise ReceiptCreationDeniedError("RECEIPT_IS_NOT_AUTHORITY")


def canonical_receipt_payload(receipt: ActionReceipt) -> bytes:
    payload = asdict(receipt)
    payload.pop("receipt_hash", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def receipt_hash(receipt: ActionReceipt) -> str:
    return hashlib.sha256(canonical_receipt_payload(receipt)).hexdigest()


def verify_receipt(receipt: ActionReceipt) -> bool:
    return receipt.receipt_hash == receipt_hash(receipt)


def verify_receipt_chain(receipts: Iterable[ActionReceipt], *, tenant_id: str | None = None) -> bool:
    items = list(receipts)
    previous = None
    seen: set[str] = set()
    for receipt in items:
        if tenant_id is not None and receipt.tenant_id != tenant_id:
            return False
        if receipt.receipt_id in seen or not verify_receipt(receipt):
            return False
        if receipt.previous_receipt_hash != previous:
            return False
        seen.add(receipt.receipt_id)
        previous = receipt.receipt_hash
    return True
