"""SP-HASH-ANCHOR-001 — external monthly hash anchoring for capital governance.

Creates a monthly anchor package for the decision-journal head hash and records
independent anchor receipts. An anchor strengthens evidence of existence/integrity
at or before a point in time; it does not make the underlying decisions legally valid.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class AnchorReceipt:
    period: str
    journal_head_hash: str
    anchor_payload_hash: str
    anchored_at: str
    provider: str
    external_reference: str
    evidence_ref: str
    status: str = "ANCHORED"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnchorReport:
    module_id: str
    period: str
    anchor_payload_hash: str
    receipts: list[AnchorReceipt] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return bool(self.receipts) and not self.findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "period": self.period,
            "anchor_payload_hash": self.anchor_payload_hash,
            "valid": self.valid,
            "receipts": [r.as_dict() for r in self.receipts],
            "findings": self.findings,
            "beneficial_suggestions": self.beneficial_suggestions,
        }


class HashAnchorEngine:
    MODULE_ID = "SP-HASH-ANCHOR-001"

    @staticmethod
    def build_payload(*, period: str, journal_head_hash: str, journal_entries: int, audit_packet_hash: str | None = None) -> dict[str, Any]:
        payload = {
            "period": period,
            "journal_head_hash": journal_head_hash,
            "journal_entries": int(journal_entries),
            "audit_packet_hash": audit_packet_hash or "",
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload["anchor_payload_hash"] = hashlib.sha256(raw).hexdigest()
        return payload

    def record_anchor(self, *, payload: dict[str, Any], provider: str, external_reference: str, evidence_ref: str, anchored_at: str | None = None) -> AnchorReceipt:
        if not provider or not external_reference or not evidence_ref:
            raise ValueError("provider, external_reference, and evidence_ref are required")
        return AnchorReceipt(
            period=str(payload["period"]),
            journal_head_hash=str(payload["journal_head_hash"]),
            anchor_payload_hash=str(payload["anchor_payload_hash"]),
            anchored_at=anchored_at or datetime.now(timezone.utc).isoformat(),
            provider=provider,
            external_reference=external_reference,
            evidence_ref=evidence_ref,
        )

    def verify(self, payload: dict[str, Any], receipts: list[AnchorReceipt]) -> AnchorReport:
        expected = self.build_payload(
            period=str(payload.get("period") or ""),
            journal_head_hash=str(payload.get("journal_head_hash") or ""),
            journal_entries=int(payload.get("journal_entries") or 0),
            audit_packet_hash=str(payload.get("audit_packet_hash") or ""),
        )
        findings: list[str] = []
        if expected["anchor_payload_hash"] != payload.get("anchor_payload_hash"):
            findings.append("ANCHOR_PAYLOAD_HASH_MISMATCH")
        if not receipts:
            findings.append("NO_EXTERNAL_ANCHOR_RECEIPT")
        for receipt in receipts:
            if receipt.anchor_payload_hash != expected["anchor_payload_hash"]:
                findings.append(f"RECEIPT_HASH_MISMATCH:{receipt.provider}")
            if receipt.journal_head_hash != expected["journal_head_hash"]:
                findings.append(f"RECEIPT_HEAD_HASH_MISMATCH:{receipt.provider}")
        return AnchorReport(
            module_id=self.MODULE_ID,
            period=str(payload.get("period") or ""),
            anchor_payload_hash=str(expected["anchor_payload_hash"]),
            receipts=receipts,
            findings=list(dict.fromkeys(findings)),
            beneficial_suggestions=[
                "Use at least one independently controlled anchor destination with durable timestamps and retained receipts.",
                "For higher assurance, use two different anchor channels under separate credentials or custodians.",
                "Store the anchor receipt alongside signed monthly minutes/certification and the audit-packet hash.",
                "Never claim anchoring proves the truth or legality of the underlying decision; it supports timing and integrity only.",
            ],
        )
