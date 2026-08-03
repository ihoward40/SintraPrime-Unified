"""Cross-jurisdiction legal rule comparison service."""

from __future__ import annotations

from datetime import date
from typing import Any

from legal_authority.engine import RuleEvaluationEngine
from legal_authority.repository import LegalAuthorityRepository

CONFLICT_OF_LAWS_WARNING = (
    "Applicable law depends on governing-law rules, trust situs, administration, "
    "party contacts, asset location, public policy, and other facts. A favorable "
    "rule in another jurisdiction may not govern the matter."
)

DEFAULT_COMPARISON_TOPICS = [
    "revocable trust settlor creditor exposure",
    "self-settled asset protection settlor creditor exposure",
    "spendthrift validity",
    "discretionary trusts mandatory overdue distributions",
    "modification reformation termination",
    "decanting",
    "trustee removal",
    "beneficiary information recordkeeping",
    "voidable transfer",
    "wage garnishment",
    "bank restraint levy exempt funds",
    "retirement protection",
    "tenancy by entirety",
    "homestead",
    "trust debtor naming",
    "UCC filing office",
    "continuation window",
    "resident trust",
]


class JurisdictionComparisonService:
    """Builds conservative side-by-side legal-rule comparisons."""

    def __init__(self, repository: LegalAuthorityRepository | None = None) -> None:
        self.repository = repository or LegalAuthorityRepository()
        self.engine = RuleEvaluationEngine(self.repository)

    def compare(
        self,
        jurisdictions: list[str],
        domain: str,
        topic: str,
        as_of_date: date | None = None,
    ) -> dict[str, Any]:
        normalized = [code.upper() for code in jurisdictions]
        rows: list[dict[str, Any]] = []
        selected_statements: dict[str, str] = {}
        for code in normalized:
            if self.repository.get_jurisdiction(code) is None:
                rows.append(
                    {
                        "jurisdiction": code,
                        "rule": None,
                        "authority": [],
                        "effective_date": None,
                        "material_differences": ["Unsupported jurisdiction."],
                        "exceptions": [],
                        "confidence": 0.0,
                        "review_status": "HUMAN_REVIEW_REQUIRED",
                        "conflict_warnings": [],
                        "missing_data": [
                            "Jurisdiction is not supported by the governed package set."
                        ],
                        "source_limitations": [],
                    }
                )
                continue
            selection = self.engine.select_rule(code, domain, topic, as_of_date)
            if selection.selected_rule is None:
                rows.append(
                    {
                        "jurisdiction": code,
                        "rule": None,
                        "authority": [a.model_dump(mode="json") for a in selection.authorities],
                        "effective_date": None,
                        "material_differences": [],
                        "exceptions": [],
                        "confidence": 0.0,
                        "review_status": selection.verification_status,
                        "conflict_warnings": [
                            c.model_dump(mode="json") for c in selection.conflicts
                        ],
                        "missing_data": [selection.explanation],
                        "source_limitations": selection.limitations,
                    }
                )
                continue
            rule = selection.selected_rule
            selected_statements[code] = rule.rule_statement
            rows.append(
                {
                    "jurisdiction": code,
                    "rule": rule.model_dump(mode="json"),
                    "authority": [a.model_dump(mode="json") for a in selection.authorities],
                    "effective_date": (
                        rule.effective_from.isoformat() if rule.effective_from else None
                    ),
                    "material_differences": [],
                    "exceptions": rule.exceptions,
                    "confidence": rule.confidence,
                    "review_status": (
                        "HUMAN_REVIEW_REQUIRED"
                        if rule.requires_human_review
                        else rule.review_status
                    ),
                    "conflict_warnings": [c.model_dump(mode="json") for c in selection.conflicts],
                    "missing_data": [],
                    "source_limitations": selection.limitations,
                }
            )
        for row in rows:
            if row["rule"] is not None:
                differences = [
                    f"Differs from {other_code}: {other_statement}"
                    for other_code, other_statement in selected_statements.items()
                    if other_code != row["jurisdiction"]
                    and other_statement != row["rule"]["rule_statement"]
                ]
                row["material_differences"] = differences or [
                    "No material difference detected in encoded rule statements."
                ]
        return {
            "domain": domain,
            "topic": topic,
            "as_of_date": (as_of_date.isoformat() if as_of_date else None),
            "jurisdictions": normalized,
            "rows": rows,
            "conflict_of_laws_warning": CONFLICT_OF_LAWS_WARNING,
            "limitations": [
                "Comparisons identify encoded rule differences, not legal advice or forum selection guidance.",
                "Missing or human-review-required rules remain visible rather than inferred.",
            ],
        }
