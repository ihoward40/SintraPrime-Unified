"""Collaboration receipts — forensic traceability (§XLVIII, §XLIX, §LXXXII-CF-1D).

Reuses the hash-chain receipt pattern from
portal/services/mission_control_command_service.py (SHA-256 chained JSONL).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class EventReceipt:
    """Every event dispatch records matched/activated/skipped agents."""

    receipt_id: str
    event_id: str
    event_type: str
    tenant_id: str
    channel_id: str
    correlation_id: str
    matched_agents: int = 0
    activated_agents: list[str] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    previous_hash: str = ""
    receipt_hash: str = ""


@dataclass
class ActivationReceipt:
    """One agent activation receipt (§XLVIII)."""

    receipt_id: str
    activation_id: str
    agent_id: str
    channel_id: str
    tenant_id: str
    trigger_event_id: str = ""
    provider: str = ""
    model: str = ""
    capabilities_used: list[str] = field(default_factory=list)
    input_artifacts: list[str] = field(default_factory=list)
    output_artifacts: list[str] = field(default_factory=list)
    duration: float = 0.0
    token_usage: int = 0
    cost: float = 0.0
    result_status: str = ""
    policy_version: str = ""
    behavior_contract_hash: str = ""
    execution_host: str = ""
    correlation_id: str = ""
    created_at: str = field(default_factory=_now_iso)
    previous_hash: str = ""
    receipt_hash: str = ""


@dataclass
class HandoffReceipt:
    """Structured handoff receipt."""

    receipt_id: str
    handoff_id: str
    source_agent: str
    target_agent: str
    channel_id: str
    tenant_id: str
    task: str = ""
    status: str = ""
    created_at: str = field(default_factory=_now_iso)
    previous_hash: str = ""
    receipt_hash: str = ""


def _hash(receipt: dict) -> str:
    canonical = json.dumps(receipt, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CollaborationReceiptStore:
    """Append-only hash-chained JSONL receipt store."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _chain_file(self, kind: str, key: str) -> Path:
        return self.base_dir / f"{kind}_{key}.jsonl"

    def _append(self, kind: str, key: str, receipt: dict) -> dict:
        chain_file = self._chain_file(kind, key)
        previous_hash = ""
        if chain_file.exists():
            lines = [ln for ln in chain_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if lines:
                previous_hash = json.loads(lines[-1])["receipt_hash"]
        receipt["previous_hash"] = previous_hash
        # Hash covers all fields EXCEPT receipt_hash itself (consistent with verify)
        payload = {k: v for k, v in receipt.items() if k != "receipt_hash"}
        receipt["receipt_hash"] = _hash(payload)
        with chain_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(receipt, sort_keys=True, default=str) + "\n")
        return receipt

    def record_event(self, receipt: EventReceipt) -> EventReceipt:
        data = asdict(receipt)
        stored = self._append("event", receipt.event_id, data)
        return EventReceipt(**{k: v for k, v in stored.items() if k != "receipt_hash"})

    def record_activation(self, receipt: ActivationReceipt) -> ActivationReceipt:
        data = asdict(receipt)
        stored = self._append("activation", receipt.activation_id, data)
        return ActivationReceipt(**{k: v for k, v in stored.items() if k != "receipt_hash"})

    def record_handoff(self, receipt: HandoffReceipt) -> HandoffReceipt:
        data = asdict(receipt)
        stored = self._append("handoff", receipt.handoff_id, data)
        return HandoffReceipt(**{k: v for k, v in stored.items() if k != "receipt_hash"})

    def verify_chain(self, kind: str, key: str) -> tuple[bool, str]:
        """Verify hash chain integrity: each receipt's hash covers previous_hash."""
        chain_file = self._chain_file(kind, key)
        if not chain_file.exists():
            return False, "chain not found"
        lines = [ln for ln in chain_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        previous_hash = ""
        for idx, line in enumerate(lines):
            receipt = json.loads(line)
            if receipt["previous_hash"] != previous_hash:
                return False, f"hash mismatch at index {idx}"
            payload = {k: v for k, v in receipt.items() if k != "receipt_hash"}
            computed = _hash(payload)
            if computed != receipt["receipt_hash"]:
                return False, f"hash mismatch at index {idx}"
            previous_hash = receipt["receipt_hash"]
        return True, "chain ok"
