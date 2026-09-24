"""Tamper-evident decision journal for private-capital governance.

Each journal entry hashes the prior entry hash plus a canonicalized decision payload.
This creates evidence of later alteration but is not a substitute for an external
trusted timestamp, digital signature, WORM storage, notarization, or third-party audit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class DecisionJournalEntry:
    sequence: int
    timestamp: str
    actor: str
    action: str
    subject_id: str
    decision: str
    rationale: str
    evidence_refs: tuple[str, ...]
    prior_hash: str
    entry_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class DecisionJournalHashChain:
    MODULE_ID = "SP-DECISION-JOURNAL-001"

    @staticmethod
    def _canonical_payload(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def append(
        self,
        *,
        actor: str,
        action: str,
        subject_id: str,
        decision: str,
        rationale: str,
        evidence_refs: list[str] | tuple[str, ...],
        prior_entry: DecisionJournalEntry | None = None,
        timestamp: str | None = None,
    ) -> DecisionJournalEntry:
        sequence = 1 if prior_entry is None else prior_entry.sequence + 1
        prior_hash = GENESIS_HASH if prior_entry is None else prior_entry.entry_hash
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        payload = {
            "sequence": sequence,
            "timestamp": ts,
            "actor": actor,
            "action": action,
            "subject_id": subject_id,
            "decision": decision,
            "rationale": rationale,
            "evidence_refs": list(evidence_refs),
            "prior_hash": prior_hash,
        }
        digest = hashlib.sha256(self._canonical_payload(payload)).hexdigest()
        return DecisionJournalEntry(
            sequence=sequence,
            timestamp=ts,
            actor=actor,
            action=action,
            subject_id=subject_id,
            decision=decision,
            rationale=rationale,
            evidence_refs=tuple(evidence_refs),
            prior_hash=prior_hash,
            entry_hash=digest,
        )

    def verify(self, entries: list[DecisionJournalEntry]) -> dict[str, Any]:
        expected_prior = GENESIS_HASH
        issues: list[str] = []
        for expected_sequence, entry in enumerate(entries, start=1):
            if entry.sequence != expected_sequence:
                issues.append(f"SEQUENCE_MISMATCH:{entry.sequence}")
            if entry.prior_hash != expected_prior:
                issues.append(f"PRIOR_HASH_MISMATCH:{entry.sequence}")
            payload = {
                "sequence": entry.sequence,
                "timestamp": entry.timestamp,
                "actor": entry.actor,
                "action": entry.action,
                "subject_id": entry.subject_id,
                "decision": entry.decision,
                "rationale": entry.rationale,
                "evidence_refs": list(entry.evidence_refs),
                "prior_hash": entry.prior_hash,
            }
            expected_hash = hashlib.sha256(self._canonical_payload(payload)).hexdigest()
            if expected_hash != entry.entry_hash:
                issues.append(f"ENTRY_HASH_MISMATCH:{entry.sequence}")
            expected_prior = entry.entry_hash
        return {
            "module_id": self.MODULE_ID,
            "valid": not issues,
            "entries": len(entries),
            "head_hash": expected_prior if entries else GENESIS_HASH,
            "issues": issues,
            "beneficial_suggestions": [
                "Anchor the monthly head hash in an independent system such as signed board/trust minutes, external object storage with retention lock, or another trusted timestamping process.",
                "Do not store secrets, bank credentials, SSNs, or unnecessary personal data in the journal payload.",
                "Require a new journal entry for overrides, restructures, collateral revaluations, policy exceptions, and reversals rather than editing prior entries.",
            ],
        }
