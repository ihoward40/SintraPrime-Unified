from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    document_hash: str
    missing_fields: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FilingPayload:
    filing_type: str
    document_hash: str
    jurisdiction: str
    transformed_fields: dict[str, Any]


class ExecutionBridge:
    """Document validation and transformation for filing submission."""

    _required_fields: dict[str, tuple[str, ...]] = {
        "ucc-1": ("debtor_name", "secured_party_name", "collateral"),
        "court": ("case_number", "court_name", "filing_party"),
    }

    _base_fees: dict[str, int] = {
        "ucc-1": 35,
        "court": 150,
    }

    def validate(
        self,
        *,
        document: str,
        filing_type: str,
        metadata: dict[str, Any],
    ) -> ValidationResult:
        normalized_document = document.strip()
        normalized_type = filing_type.lower()
        required = self._required_fields.get(normalized_type, ())
        missing = [key for key in required if not metadata.get(key)]
        messages: list[str] = []
        if not normalized_document:
            messages.append("document is empty")
        if normalized_type not in self._required_fields:
            messages.append(f"unsupported filing type: {filing_type}")
        document_hash = sha256(normalized_document.encode("utf-8")).hexdigest()
        return ValidationResult(
            is_valid=not missing and not messages,
            document_hash=document_hash,
            missing_fields=missing,
            messages=messages,
        )

    def transform(
        self,
        *,
        document: str,
        filing_type: str,
        metadata: dict[str, Any],
    ) -> FilingPayload:
        validation = self.validate(document=document, filing_type=filing_type, metadata=metadata)
        if not validation.is_valid:
            raise ValueError(
                f"cannot transform invalid filing payload: missing={validation.missing_fields}, messages={validation.messages}"
            )
        normalized_document = document.strip()
        transformed = {
            **metadata,
            "document_preview": normalized_document[:120],
            "document_length": len(normalized_document),
        }
        jurisdiction = str(metadata.get("jurisdiction", "unknown"))
        return FilingPayload(
            filing_type=filing_type.lower(),
            document_hash=validation.document_hash,
            jurisdiction=jurisdiction,
            transformed_fields=transformed,
        )

    def estimate_cost(self, *, filing_type: str, rush: bool = False) -> int:
        normalized_type = filing_type.lower()
        if normalized_type not in self._base_fees:
            raise ValueError(f"unsupported filing type: {filing_type}")
        base = self._base_fees[normalized_type]
        return int(base * 1.5) if rush else base

    def validate_and_transform(
        self,
        *,
        document: str,
        filing_type: str,
        metadata: dict[str, Any],
    ) -> FilingPayload:
        return self.transform(document=document, filing_type=filing_type, metadata=metadata)
