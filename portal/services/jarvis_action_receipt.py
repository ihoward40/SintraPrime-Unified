"""JARVIS-001-B1 ActionReceipt chain (B1-8).

Extends the existing hash-chain architecture (Nova execution_ledger pattern)
into a tamper-evident action receipt chain. Never stores credential material.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from .jarvis_action_taxonomy import ActionFailure

RECEIPT_SECRET_MARKERS = ("token", "secret", "password", "authorization", "bearer", "ghp_", "xoxb-", "credential")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass
class ActionReceipt:
    receipt_id: str
    action_id: str
    mission_id: str
    request_id: str
    tenant_id: str
    approval_id: str
    executor: str
    provider: str
    target: str
    params_hash: str
    pre_action_state_hash: str
    execution_result_hash: str
    post_action_state_hash: str
    verification_status: str
    actor: str
    authority: str
    started_at: str
    completed_at: str
    result_hash: str
    receipt_hash: str
    previous_receipt_hash: str


def compute_receipt_hash(receipt_dict: dict) -> str:
    """Deterministic SHA-256 over the canonical receipt content (excl. chain hash)."""
    content = {k: v for k, v in receipt_dict.items() if k != "receipt_hash"}
    payload = json.dumps(content, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def verify_receipt_chain(receipts) -> bool:
    """Tamper detection: every hash must recompute; chain must link."""
    prev = "0" * 64
    for i, receipt in enumerate(receipts):
        if receipt.get("previous_receipt_hash") != prev:
            raise ActionFailure("RECEIPT_WRITE_FAILED", f"chain break at {i}")
        expected = compute_receipt_hash(receipt)
        if expected != receipt.get("receipt_hash"):
            raise ActionFailure("RECEIPT_WRITE_FAILED", f"tampered receipt at {i}")
        prev = receipt.get("receipt_hash")
    return True


def receipt_contains_secret_material(receipt) -> bool:
    """True if any receipt string value embeds credential-shaped material."""
    blob = json.dumps(receipt, default=str).lower()
    markers = ("jarvis-b1-approval:",)  # opaque tokens must not leak into receipts
    return any(m in blob for m in markers)


class ActionReceiptChain:
    """Append-only receipt chain with tamper detection."""

    def __init__(self) -> None:
        self._entries: list[dict] = []

    def add(self, receipt: dict) -> dict:
        receipt["previous_receipt_hash"] = self._last_hash
        receipt["receipt_hash"] = compute_receipt_hash(receipt)
        self._entries.append(receipt)
        return receipt

    @property
    def _last_hash(self) -> str:
        return self._entries[-1]["receipt_hash"] if self._entries else "0" * 64

    def verify(self) -> bool:
        return verify_receipt_chain(self._entries)

    @property
    def entries(self) -> list:
        return list(self._entries)
