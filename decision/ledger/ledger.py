"""Ledger: tamper-evident decision receipts (append-only, hash-chained)."""

from __future__ import annotations

import threading
from hashlib import sha256

from ..canonical.jcs import canonical_bytes, state_sha256
from ..contracts.contracts import semantic_contract_sha256
from ..engine.types import DecisionResult
from ..policy.policy import PolicyDecision

SCHEMA_VERSION = "sp-decision-receipt-v1"


def build_receipt(*, decision_id: str, run_id: str, state: dict, contract_raw: dict,
                  result: DecisionResult, policy: PolicyDecision,
                  timestamps: dict | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "decision_id": decision_id,
        "run_id": run_id,
        "contract": {
            "name": contract_raw.get("contract_id"),
            "version": str(contract_raw.get("version", "1")),
            "semantic_sha256": semantic_contract_sha256(contract_raw),
        },
        "state": {
            "canonical_version": "sp-decision-state-v1",
            "sha256": state_sha256(state),
        },
        "provider": {
            "adapter": result.provider,
            "model": result.model,
            "raw_primitive": None,  # filled per-answer below when applicable
            "canonical_primitive": "choice|score|boolean",
        },
        "provider_raw_primitives": dict(result.raw_primitive_names),
        "result": {
            "kind": result.kind.value,
            "answers": {k: a.to_dict() for k, a in result.answers.items()},
            "reason": result.reason,
        },
        "policy": {
            "decision": policy.decision,
            "risk": policy.risk,
            "reason": policy.reason,
        },
        "provider_request_id": result.provider_request_id,
        "latency_ms": result.latency_ms,
        "timestamps": timestamps or {},
    }


def entry_hash(entry: dict) -> str:
    """Authenticate an entry over its FULL semantic content, including prev_hash.

    Invariant (SP-SYSTEM-ONE-DECISION-FABRIC-001-R1-LGR-FIX): the current
    entry hash cryptographically commits to the predecessor reference.
    Only the hash field itself is excluded from its own preimage.
    Genesis entries carry prev_hash=None, which participates in the preimage
    like any other value.
    """
    body = {k: v for k, v in entry.items() if k != "hash"}
    return sha256(canonical_bytes(body)).hexdigest()


def receipt_integrity_fields(receipt: dict) -> dict:
    """Chain hash fields. `prev_hash` is an authenticated semantic field:
    it participates in the entry's own hash preimage (Class A linkage)."""
    return {"prev_hash": receipt.get("prev_hash"), "hash": entry_hash(receipt)}


class Ledger:
    """In-memory append-only ledger with hash chaining (R1 reference impl).

    Chain invariant: entry[N].hash = SHA256(canonical_jcs(entry[N] minus
    {hash})), with entry[N].prev_hash = entry[N-1].hash INSIDE that preimage.
    Genesis entry: prev_hash = None (authenticated as part of the preimage).

    Test-side injection of receipts is instrumentation; production ledgers
    persist externally (out of R1 scope).
    """

    def __init__(self) -> None:
        self._entries: list[dict] = []
        self._lock = threading.Lock()

    def append(self, receipt: dict) -> dict:
        with self._lock:
            prev = self._entries[-1]["hash"] if self._entries else None
            entry = dict(receipt)
            entry["prev_hash"] = prev
            # prev_hash IS authenticated: only the hash field excludes itself
            entry["hash"] = entry_hash(entry)
            self._entries.append(entry)
            return dict(entry)

    def verify(self) -> bool:
        prev = None
        for e in self._entries:
            # identical preimage semantics to append(): hash covers
            # everything except the hash field itself — including prev_hash
            if e.get("prev_hash") != prev or e.get("hash") != entry_hash(e):
                return False
            prev = e["hash"]
        return True

    def __len__(self) -> int:
        return len(self._entries)

    def entries(self) -> list[dict]:
        return [dict(e) for e in self._entries]
