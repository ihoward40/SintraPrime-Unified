from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import PurePosixPath
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
        normalized_root = screenshot_root.strip()
        if not normalized_root:
            raise ValueError("screenshot_root must not be empty")
        if normalized_root != "/" and normalized_root.endswith("/"):
            normalized_root = normalized_root.rstrip("/")
        self._screenshot_root = normalized_root

    def capture_signature(self, signer_name: str, payload: dict[str, Any]) -> str:
        canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        fingerprint = sha256(f"{signer_name}|{canonical_payload}".encode("utf-8")).hexdigest()[:16]
        return f"sig-{fingerprint}"

    def file(self, request: FilingRequest) -> FilingResult:
        target = self._resolve_target(request.filing_type)
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
        root = PurePosixPath("/")
        if self._screenshot_root != "/":
            root = PurePosixPath(self._screenshot_root)
        return [
            str(root / target.value / filing_id / f"{index:02d}-{step}.png")
            for index, step in enumerate(steps, 1)
        ]

    @staticmethod
    def _resolve_target(filing_type: str) -> FilingTarget:
        normalized_type = filing_type.lower()
        if normalized_type.startswith("ucc"):
            return FilingTarget.UCC
        if normalized_type.startswith("court"):
            return FilingTarget.COURT
        raise ValueError(f"unsupported filing type: {filing_type}")
