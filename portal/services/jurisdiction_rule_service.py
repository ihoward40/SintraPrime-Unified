"""Read-only portal service for jurisdiction legal rules."""

from __future__ import annotations

from datetime import date
from typing import Any

from legal_authority.engine import RuleEvaluationEngine
from legal_authority.repository import LegalAuthorityRepository


class JurisdictionRuleService:
    """Shapes legal authority repository results for API consumers."""

    def __init__(self, repository: LegalAuthorityRepository | None = None) -> None:
        self.repository = repository or LegalAuthorityRepository()
        self.engine = RuleEvaluationEngine(self.repository)

    def list_jurisdictions(self) -> list[dict[str, Any]]:
        return self.repository.list_jurisdictions()

    def get_jurisdiction(self, code: str) -> dict[str, Any] | None:
        return self.repository.get_jurisdiction(code)

    def get_coverage(self, code: str) -> dict[str, Any] | None:
        coverage = self.repository.get_coverage(code)
        if coverage is None:
            return None
        rules = self.repository.query_rules(jurisdiction=code)
        return {
            **coverage,
            "domains": sorted({rule.domain for rule in rules}),
            "topics": sorted({rule.topic for rule in rules}),
            "rule_count": len(rules),
            "authority_count": len(
                {authority_id for rule in rules for authority_id in rule.authority_ids}
            ),
            "human_review_warning": "Educational and issue-spotting output only. Not a legal opinion.",
        }

    def list_rules(
        self,
        code: str,
        domain: str | None = None,
        topic: str | None = None,
        status: str | None = None,
        verification_state: str | None = None,
        requires_human_review: bool | None = None,
        effective_date: date | None = None,
    ) -> list[dict[str, Any]] | None:
        if self.repository.get_jurisdiction(code) is None:
            return None
        rules = self.repository.query_rules(
            jurisdiction=code,
            domain=domain,
            topic=topic,
            status=status,
            verification_state=verification_state,
            requires_human_review=requires_human_review,
        )
        if effective_date is not None:
            rules = [
                rule
                for rule in rules
                if rule.effective_from is not None
                and rule.effective_from <= effective_date
                and (rule.effective_to is None or rule.effective_to > effective_date)
            ]
        return [self._rule_payload(rule.id) for rule in rules]

    def get_rule(
        self, code: str, rule_id: str, as_of_date: date | None = None
    ) -> dict[str, Any] | None:
        rule = self.repository.get_rule(rule_id)
        if rule is None or rule.jurisdiction != code.upper():
            return None
        selection = self.engine.select_rule(rule.jurisdiction, rule.domain, rule.topic, as_of_date)
        payload = self._rule_payload(rule.id)
        payload["selection"] = selection.model_dump(mode="json")
        return payload

    def get_authority(self, authority_id: str) -> dict[str, Any] | None:
        authority = self.repository.get_authority(authority_id)
        if authority is None:
            return None
        return authority.model_dump(mode="json")

    def compare(
        self,
        jurisdiction: str,
        domain: str,
        topic: str,
        as_of_date: date | None = None,
    ) -> dict[str, Any]:
        return self.engine.compare_rules(jurisdiction, domain, topic, as_of_date)

    def _rule_payload(self, rule_id: str) -> dict[str, Any]:
        rule = self.repository.get_rule(rule_id)
        if rule is None:
            raise KeyError(rule_id)
        authorities = self.repository.authorities_for_rule(rule)
        verification_states = sorted({authority.verification_status for authority in authorities})
        limitations = sorted({item for authority in authorities for item in authority.limitations})
        if rule.requires_human_review:
            limitations.append("Educational and issue-spotting output only. Not a legal opinion.")
        return {
            **rule.model_dump(mode="json"),
            "verification_statuses": verification_states,
            "human_review_status": (
                "HUMAN_REVIEW_REQUIRED" if rule.requires_human_review else "NOT_REQUIRED"
            ),
            "limitations": sorted(set(limitations)),
            "provenance": {
                "rule_id": rule.id,
                "authority_ids": rule.authority_ids,
                "jurisdiction": rule.jurisdiction,
                "effective_from": rule.effective_from.isoformat() if rule.effective_from else None,
                "effective_to": rule.effective_to.isoformat() if rule.effective_to else None,
                "verification_status": verification_states,
                "human_review_status": (
                    "HUMAN_REVIEW_REQUIRED" if rule.requires_human_review else "NOT_REQUIRED"
                ),
                "limitations": sorted(set(limitations)),
            },
        }
