"""Immutable evidence receipts with hash chaining.

Every completed node produces a receipt. Receipts chain via
previous_hash. Receipts are written to disk and never mutated.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import (
    NodeStatus,
    NodeType,
    WorkflowReceipt,
    compute_receipt_hash,
    sha256_json,
    utcnow_iso,
)


class ReceiptStore:
    """Append-only receipt store.

    Phase 5A stores receipts as JSONL files (one line per receipt)
    under a run directory. Each new receipt carries the hash of the
    previous receipt, forming an immutable chain.
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _chain_file(self, run_id: str) -> Path:
        return self.base_dir / f"receipts_{run_id}.jsonl"

    def append(
        self,
        *,
        run_id: str,
        node_id: str,
        node_type: NodeType,
        status: NodeStatus,
        output: dict[str, Any],
        provider: str | None = None,
        model: str | None = None,
        tokens_used: int = 0,
        cost: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowReceipt:
        chain_file = self._chain_file(run_id)
        previous_hash = None
        if chain_file.exists():
            lines = [
                line for line in chain_file.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
            if lines:
                previous_hash = json.loads(lines[-1])["receipt_hash"]

        receipt = WorkflowReceipt(
            receipt_id=str(uuid.uuid4()),
            run_id=run_id,
            node_id=node_id,
            node_type=node_type,
            status=status,
            output_hash=sha256_json(output) if output else "",
            provider=provider,
            model=model,
            tokens_used=tokens_used,
            cost=cost,
            previous_hash=previous_hash,
            receipt_hash="",  # set below
            created_at=utcnow_iso(),
            metadata=metadata or {},
        )
        receipt.receipt_hash = compute_receipt_hash(receipt)

        with open(chain_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(receipt), ensure_ascii=False) + "\n")

        return receipt

    def load_chain(self, run_id: str) -> list[WorkflowReceipt]:
        chain_file = self._chain_file(run_id)
        if not chain_file.exists():
            return []
        receipts: list[WorkflowReceipt] = []
        for line in chain_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            receipts.append(WorkflowReceipt(**json.loads(line)))
        return receipts

    def verify_chain(self, run_id: str) -> tuple[bool, str]:
        """Verify the hash chain integrity. Returns (ok, reason)."""
        receipts = self.load_chain(run_id)
        if not receipts:
            return False, "no receipts"
        previous: str | None = None
        for i, r in enumerate(receipts):
            if r.previous_hash != previous:
                return False, f"broken link at receipt {i} ({r.node_id})"
            expected = compute_receipt_hash(r)
            if r.receipt_hash != expected:
                return False, f"hash mismatch at receipt {i} ({r.node_id})"
            previous = r.receipt_hash
        return True, f"{len(receipts)} receipts verified"
