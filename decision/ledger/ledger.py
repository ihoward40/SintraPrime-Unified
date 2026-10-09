"""Hash-chained append-only receipts (R1 ledger).

Receipts are hash-chained (prev_hash -> hash over canonical bytes of every field
except the chain fields). Ledger.verify() recomputes the chain; mutation of any
canonical field breaks verification. In-memory reference implementation;
production persistence is a later governed increment and must preserve the chain.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from decision.canonical.jcs import canonical_bytes

REQUIRED_FIELDS = (
    "index", "ts", "state_sha256", "contract_sha256",
    "provider_request_id", "latency_ms", "kind", "disposition",
)


def _chain_fields(record: Dict) -> Dict:
    return {k: record[k] for k in REQUIRED_FIELDS if k in record}


def receipt_hash(prev_hash: str, fields: Dict) -> str:
    import hashlib
    envelope = {"prev_hash": prev_hash, **fields}
    return hashlib.sha256(canonical_bytes(envelope)).hexdigest()


class Ledger:
    def __init__(self) -> None:
        self.entries: List[Dict] = []
        self.head_hash = "0" * 64

    def append(self, *, state_sha256: str, contract_sha256: str,
               provider_request_id: str, latency_ms: float,
               kind: str, disposition: str) -> Dict:
        index = len(self.entries)
        fields = {
            "index": index,
            "ts": time.time_ns(),
            "state_sha256": state_sha256,
            "contract_sha256": contract_sha256,
            "provider_request_id": provider_request_id,
            "latency_ms": latency_ms,
            "kind": kind,
            "disposition": disposition,
        }
        h = receipt_hash(self.head_hash, fields)
        record = {**fields, "prev_hash": self.head_hash, "hash": h}
        self.entries.append(record)
        self.head_hash = h
        return record

    def verify(self) -> bool:
        prev = "0" * 64
        for rec in self.entries:
            fields = _chain_fields(rec)
            expect = receipt_hash(prev, fields)
            if rec.get("hash") != expect or rec.get("prev_hash") != prev:
                return False
            prev = rec["hash"]
        return True

    def __len__(self) -> int:
        return len(self.entries)
