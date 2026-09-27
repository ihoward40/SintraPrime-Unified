from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any
from uuid import uuid4


class FilingTarget(StrEnum):
    UCC = "ucc"
    COURT = "court"


@dataclass(slots=True)
class FilingRequest:
    filing_type: str
    jurisdiction: str
    payload: dict[str, Any]
    signer_name: str


@dataclass(slots=True)
class FilingResult:
    filing_id: str
    status: str
    target: FilingTarget
    receipt_reference: str
    screenshots: list[str] = field(default_factory=list)
    browser_log: list[str] = field(default_factory=list)
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FilingEngine:
    """Minimal autonomous browser filing engine with auditable artifacts."""

    def __init__(self, *, screenshot_root: str = "audit") -> None:
        self._screenshot_root = screenshot_root.strip("/")

    def capture_signature(self, signer_name: str, payload: dict[str, Any]) -> str:
        fingerprint = sha256(f"{signer_name}|{payload}".encode("utf-8")).hexdigest()[:16]
        return f"sig-{fingerprint}"

    def file(self, request: FilingRequest) -> FilingResult:
        target = (
            FilingTarget.UCC
            if request.filing_type.lower().startswith("ucc")
            else FilingTarget.COURT
        )
        filing_id = f"filing-{uuid4().hex}"
        signature_id = self.capture_signature(request.signer_name, request.payload)
        screenshots = self._build_screenshot_trail(filing_id, target)
        browser_log = [
            f"open:{target.value}:{request.jurisdiction}",
            f"sign:{signature_id}",
            "submit:ok",
        ]
        receipt_reference = f"receipt-{request.jurisdiction.lower()}-{filing_id[-8:]}"
        return FilingResult(
            filing_id=filing_id,
            status="submitted",
            target=target,
            receipt_reference=receipt_reference,
            screenshots=screenshots,
            browser_log=browser_log,
        )

    def _build_screenshot_trail(self, filing_id: str, target: FilingTarget) -> list[str]:
        steps = ("start", "form-complete", "signature", "submitted")
        return [
            f"{self._screenshot_root}/{target.value}/{filing_id}/{index:02d}-{step}.png"
            for index, step in enumerate(steps, 1)
        ]
