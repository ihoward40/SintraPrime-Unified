"""Evidence-based UCC filing assessment workflow."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

from legal_authority.models import AuditEvent
from legal_authority.repository import LegalAuthorityRepository

FILING_ACK_WARNING = (
    "A filing-office acknowledgment confirms receipt and indexing. It does not "
    "independently establish attachment, enforceability, ownership, priority, or "
    "the legal validity of every collateral claim."
)

SENSITIVE_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{9}\b"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
]
PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "system prompt",
    "developer message",
    "act as",
    "override",
]


@dataclass
class UCCFilingAssessmentService:
    repository: LegalAuthorityRepository = field(default_factory=LegalAuthorityRepository)
    _store: dict[str, dict[str, Any]] = field(default_factory=dict)

    def evaluate(
        self, payload: dict[str, Any], actor_role: str, actor_identity: str
    ) -> dict[str, Any]:
        jurisdiction = str(payload.get("filing_jurisdiction", "")).upper()
        if jurisdiction not in {"NY", "PA", "NJ"}:
            raise ValueError("unsupported filing jurisdiction")
        filing_date = self._parse_date(payload.get("filing_date"))
        debtor_name = self._redact(str(payload.get("debtor_name", "")))
        collateral = self._redact(str(payload.get("collateral_summary", "")))
        secured_party = self._redact(str(payload.get("secured_party", "")))
        continuation = self._continuation_window(filing_date, payload.get("duration_exception"))
        issues = self._issues(payload, jurisdiction, debtor_name, collateral, continuation)
        evaluation_id = f"ucc-eval-{uuid4()}"
        audit_event = AuditEvent(
            id=f"audit-{uuid4()}",
            event_type="UCC_EVALUATION_CREATED",
            object_type="UCCFilingEvaluation",
            object_id=evaluation_id,
            actor_role=actor_role,
            actor_identity=actor_identity,
            reason="Nonpersistent UCC filing assessment created.",
            payload={
                "jurisdiction": jurisdiction,
                "filing_number_present": bool(payload.get("filing_number")),
            },
            created_at=datetime.now(UTC),
        )
        result = {
            "evaluation_id": evaluation_id,
            "stored_persistently": False,
            "jurisdiction": jurisdiction,
            "filing_facts": {
                "filing_number": self._redact(str(payload.get("filing_number", ""))),
                "filing_date": filing_date.isoformat(),
                "debtor_type": payload.get("debtor_type"),
                "debtor_name": debtor_name,
                "secured_party": secured_party,
                "collateral_summary": collateral,
                "termination_status": payload.get("termination_status"),
            },
            "continuation_window": continuation,
            "assessment_items": issues,
            "missing_evidence": [
                item["label"] for item in issues if item["status"] == "EVIDENCE_MISSING"
            ],
            "warnings": [
                FILING_ACK_WARNING,
                "Collateral descriptions are treated as untrusted text, not application instructions.",
            ],
            "redaction_applied": self._has_sensitive_text(payload),
            "audit_event": audit_event.model_dump(mode="json"),
        }
        self._store[evaluation_id] = result
        return result

    def get(self, evaluation_id: str) -> dict[str, Any] | None:
        return self._store.get(evaluation_id)

    def _issues(
        self,
        payload: dict[str, Any],
        jurisdiction: str,
        debtor_name: str,
        collateral: str,
        continuation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        expected_office = (
            "New York Department of State"
            if jurisdiction == "NY"
            else (
                "Pennsylvania Department of State"
                if jurisdiction == "PA"
                else "New Jersey Department of the Treasury"
            )
        )
        supplied_office = str(payload.get("filing_office", ""))
        wrong_office = bool(
            supplied_office and expected_office.lower() not in supplied_office.lower()
        )
        security_agreement = bool(payload.get("security_agreement_available"))
        value = bool(payload.get("value_evidence_available"))
        rights = bool(payload.get("debtor_rights_in_collateral"))
        prompt_risk = any(p in collateral.lower() for p in PROMPT_INJECTION_PATTERNS)
        misleading_name = len(debtor_name.strip()) < 3 or any(
            word in debtor_name.lower() for word in ["all caps", "strawman", "birth certificate"]
        )
        unsupported_collateral = any(
            word in collateral.lower()
            for word in [
                "birth certificate",
                "secret treasury",
                "person as collateral",
                "accepted for value",
            ]
        )
        return [
            self._item(
                "FILING FACT",
                "Filing-office acceptance",
                "EVIDENCE_PRESENT" if payload.get("filing_number") else "EVIDENCE_MISSING",
                FILING_ACK_WARNING,
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Correct filing location",
                "RISK" if wrong_office else "EVIDENCE_PRESENT",
                f"Expected office: {expected_office}.",
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Debtor-name sufficiency",
                "RISK" if misleading_name else "HUMAN_REVIEW_REQUIRED",
                "Debtor names require Article 9 and public-record review.",
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Debtor authorization",
                "EVIDENCE_MISSING",
                "Filing acceptance does not prove authorization.",
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Authenticated security agreement",
                "EVIDENCE_PRESENT" if security_agreement else "EVIDENCE_MISSING",
                "Attachment requires agreement evidence or another authenticated record.",
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Value given",
                "EVIDENCE_PRESENT" if value else "EVIDENCE_MISSING",
                "Attachment requires value.",
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Debtor rights in collateral",
                "EVIDENCE_PRESENT" if rights else "EVIDENCE_MISSING",
                "Attachment requires debtor rights or power to transfer rights.",
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Adequate collateral description",
                "RISK" if unsupported_collateral else "HUMAN_REVIEW_REQUIRED",
                "Unsupported collateral assertions are not accepted as facts.",
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Attachment",
                (
                    "EVIDENCE_PRESENT"
                    if security_agreement and value and rights
                    else "EVIDENCE_MISSING"
                ),
                "All attachment elements must be separately supported.",
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Perfection",
                "HUMAN_REVIEW_REQUIRED",
                "Perfection depends on collateral type, filing office, debtor name, and attachment.",
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Priority",
                "HUMAN_REVIEW_REQUIRED",
                "Priority is not established by this assessment.",
            ),
            self._item(
                "SUBSTANTIVE_REQUIREMENT",
                "Continuation timing",
                (
                    "RISK"
                    if continuation["early_filing_ineffective"] or continuation["lapsed"]
                    else "HUMAN_REVIEW_REQUIRED"
                ),
                continuation["explanation"],
            ),
            self._item(
                "RISK",
                "Potential seriously misleading errors",
                "RISK" if misleading_name or wrong_office else "HUMAN_REVIEW_REQUIRED",
                "Name and office errors require human review.",
            ),
            self._item(
                "RISK",
                "Unsupported collateral assertions",
                "RISK" if unsupported_collateral else "EVIDENCE_PRESENT",
                "Private-law collateral theories are quarantined.",
            ),
            self._item(
                "RISK",
                "Privacy-sensitive public filing content",
                "RISK" if self._has_sensitive_text(payload) else "EVIDENCE_PRESENT",
                "SSNs, account numbers, and private identifiers are redacted from display.",
            ),
            self._item(
                "RISK",
                "Prompt injection in collateral text",
                "RISK" if prompt_risk else "EVIDENCE_PRESENT",
                "Collateral text is untrusted data.",
            ),
        ]

    @staticmethod
    def _item(kind: str, label: str, status: str, detail: str) -> dict[str, str]:
        return {"kind": kind, "label": label, "status": status, "detail": detail}

    @staticmethod
    def _parse_date(value: Any) -> date:
        if isinstance(value, date):
            return value
        if not value:
            raise ValueError("filing_date is required")
        return date.fromisoformat(str(value))

    @staticmethod
    def _continuation_window(filing_date: date, duration_exception: Any) -> dict[str, Any]:
        if duration_exception:
            return {
                "initial_filing_date": filing_date.isoformat(),
                "ordinary_lapse_date": None,
                "first_permitted_continuation_date": None,
                "final_permitted_continuation_date": None,
                "currently_eligible": False,
                "early_filing_ineffective": False,
                "lapsed": False,
                "exception_requires_review": True,
                "explanation": "Special duration exception supplied; ordinary five-year calculation not applied.",
            }
        lapse = filing_date.replace(year=filing_date.year + 5)
        first = lapse - timedelta(days=183)
        today = date.today()
        return {
            "initial_filing_date": filing_date.isoformat(),
            "ordinary_lapse_date": lapse.isoformat(),
            "first_permitted_continuation_date": first.isoformat(),
            "final_permitted_continuation_date": lapse.isoformat(),
            "currently_eligible": first <= today <= lapse,
            "early_filing_ineffective": today < first,
            "lapsed": today > lapse,
            "exception_requires_review": False,
            "explanation": "Ordinary five-year financing statement continuation window calculated as six months before lapse.",
        }

    @classmethod
    def _redact(cls, text: str) -> str:
        redacted = text
        for pattern in SENSITIVE_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted

    @classmethod
    def _has_sensitive_text(cls, payload: dict[str, Any]) -> bool:
        text = " ".join(str(value) for value in payload.values())
        return any(pattern.search(text) for pattern in SENSITIVE_PATTERNS)
