"""
Provenance Engine — record chain of custody and lineage for knowledge objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from blackstone.models import EvidenceItem


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class ProvenanceRecord:
    object_id: str
    object_type: str
    action: str
    actor: str
    timestamp: datetime = field(default_factory=utcnow)
    payload: dict[str, Any] = field(default_factory=dict)
    prior_hash: str = ""
    record_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "action": self.action,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "prior_hash": self.prior_hash,
            "record_hash": self.record_hash,
        }


class ProvenanceEngine:
    """
    Maintain tamper-evident chain of custody records for evidence and claims.
    """

    def __init__(self, hasher: Any | None = None) -> None:
        self._records: dict[str, list[ProvenanceRecord]] = {}
        self._hasher = hasher or self._default_hash

    @staticmethod
    def _default_hash(data: str) -> str:
        import hashlib

        return hashlib.sha256(data.encode("utf-8")).hexdigest()[:32]

    def record(
        self,
        object_id: str,
        object_type: str,
        action: str,
        actor: str,
        payload: dict[str, Any] | None = None,
    ) -> ProvenanceRecord:
        chain = self._records.setdefault(object_id, [])
        prior_hash = chain[-1].record_hash if chain else ""
        payload = payload or {}
        record = ProvenanceRecord(
            object_id=object_id,
            object_type=object_type,
            action=action,
            actor=actor,
            payload=payload,
            prior_hash=prior_hash,
        )
        record.record_hash = self._hasher(f"{prior_hash}:{object_id}:{record.timestamp.isoformat()}:{payload!s}")
        chain.append(record)
        return record

    def chain(self, object_id: str) -> list[ProvenanceRecord]:
        return list(self._records.get(object_id, []))

    def verify(self, object_id: str) -> dict[str, object]:
        """
        Verify the integrity of a provenance chain by re-checking hashes.
        """
        records = self._records.get(object_id, [])
        if not records:
            return {"object_id": object_id, "valid": False, "breaks": ["no records"]}

        breaks: list[str] = []
        for i, record in enumerate(records):
            expected_prior = records[i - 1].record_hash if i > 0 else ""
            if record.prior_hash != expected_prior:
                breaks.append(f"record {i}: prior_hash mismatch")
            expected_hash = self._hasher(
                f"{record.prior_hash}:{record.object_id}:{record.timestamp.isoformat()}:{record.payload!s}"
            )
            if record.record_hash != expected_hash:
                breaks.append(f"record {i}: record_hash mismatch")

        return {"object_id": object_id, "valid": len(breaks) == 0, "breaks": breaks}

    def custody_summary(self, evidence: EvidenceItem) -> dict[str, object]:
        return {
            "evidence_id": evidence.id,
            "source_id": evidence.source.id,
            "reviewer": evidence.reviewer,
            "reviewed_at": evidence.reviewed_at.isoformat() if evidence.reviewed_at else None,
            "created_at": evidence.created_at.isoformat(),
            "chain_length": len(self._records.get(evidence.id, [])),
            "verified": self.verify(evidence.id)["valid"],
        }
