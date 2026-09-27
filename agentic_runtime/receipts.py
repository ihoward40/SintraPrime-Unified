"""Canonical cryptographically referenced execution receipts."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionReceipt:
    run_id: str
    base_ref: str
    head_ref: str
    status: str
    changed_files: List[str] = field(default_factory=list)
    tests: Dict[str, Any] = field(default_factory=dict)
    model_evidence: Dict[str, Any] = field(default_factory=dict)
    budget: Dict[str, Any] = field(default_factory=dict)
    ledger_entry_hash: Optional[str] = None
    previous_receipt_hash: str = ""
    receipt_hash: str = ""

    def canonical_payload(self) -> Dict[str, Any]:
        data = asdict(self)
        data["receipt_hash"] = ""
        return data

    def seal(self) -> str:
        raw = json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":")).encode()
        self.receipt_hash = hashlib.sha256(raw).hexdigest()
        return self.receipt_hash

    def verify(self) -> bool:
        existing = self.receipt_hash
        return bool(existing) and self.seal() == existing


def bind_ledger_hash(receipt: ExecutionReceipt, ledger_hash: str) -> ExecutionReceipt:
    if not ledger_hash or len(ledger_hash) != 64:
        raise ValueError("ledger_hash must be a SHA-256 hex digest")
    int(ledger_hash, 16)
    receipt.ledger_entry_hash = ledger_hash
    receipt.seal()
    return receipt
