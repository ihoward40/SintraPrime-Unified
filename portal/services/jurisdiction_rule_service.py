"""Portal service for jurisdiction legal rules and governed review workflows."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from legal_authority.comparison import JurisdictionComparisonService
from legal_authority.engine import RuleEvaluationEngine
from legal_authority.repository import LegalAuthorityRepository
from legal_authority.review_workflow import ReviewWorkflow
from legal_authority.source_monitor import SourceMonitor
from legal_authority.ucc_filing import UCCFilingAssessmentService


class JurisdictionRuleService:
    """Shapes legal authority repository results for API consumers."""

    def __init__(self, repository: LegalAuthorityRepository | None = None) -> None:
        self.repository = repository or LegalAuthorityRepository()
        self.engine = RuleEvaluationEngine(self.repository)
        self.review_workflow = ReviewWorkflow(self.repository)
        self.source_monitor = SourceMonitor(self.repository)
        self.comparison_service = JurisdictionComparisonService(self.repository)
        self.ucc_filing_service = UCCFilingAssessmentService(self.repository)

    def list_jurisdictions(self) -> list[dict[str, Any]]:
        return self.repository.list_jurisdictions()

    def get_jurisdiction(self, code: str) -> dict[str, Any] | None:
        return self.repository.get_jurisdiction(code)

    def get_coverage(self, code: str) -> dict[str, Any] | None:
        coverage = self.repository.get_coverage(code)
        if coverage is None:
            return None
        rules = self.repository.query_rules(jurisdiction=code)
        stale_authorities = self.repository.stale_authorities(code)
        return {
            **coverage,
            "domains": sorted({rule.domain for rule in rules}),
            "topics": sorted({rule.topic for rule in rules}),
            "rule_count": len(rules),
            "authority_count": len(
                {authority_id for rule in rules for authority_id in rule.authority_ids}
            ),
            "rules_requiring_review": len([rule for rule in rules if rule.requires_human_review]),
            "conflict_count": len(self.repository.conflicts_for_jurisdiction(code)),
            "stale_authority_count": len(stale_authorities),
            "production_eligible_count": 0,
            "human_review_warning": (
                "Educational and issue-spotting output only. This system does not provide "
                "a legal opinion or replace review by a licensed attorney."
            ),
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
        payload["production_gate"] = self.review_workflow.production_eligibility(
            rule.id, as_of_date
        )
        return payload

    def federal_domains(self) -> list[dict[str, Any]]:
        rules = self.repository.query_rules(jurisdiction="FED")
        grouped: dict[str, list[Any]] = {}
        for rule in rules:
            grouped.setdefault(rule.domain, []).append(rule)
        return [
            {
                "domain": domain,
                "rule_count": len(domain_rules),
                "topics": sorted({rule.topic for rule in domain_rules}),
                "human_review_required": all(rule.requires_human_review for rule in domain_rules),
                "production_eligible": False,
            }
            for domain, domain_rules in sorted(grouped.items())
        ]

    def federal_rules(
        self, domain: str | None = None, topic: str | None = None
    ) -> list[dict[str, Any]]:
        rules = self.repository.query_rules(jurisdiction="FED", domain=domain, topic=topic)
        return [self._rule_payload(rule.id) for rule in rules]

    def federal_authorities(self) -> list[dict[str, Any]]:
        return [
            authority.model_dump(mode="json")
            for authority in sorted(self.repository.authorities.values(), key=lambda item: item.id)
            if authority.jurisdiction == "FED"
        ]

    def federal_conflicts(self) -> list[dict[str, Any]]:
        return [
            conflict.model_dump(mode="json")
            for conflict in self.repository.conflicts_for_jurisdiction("FED")
        ]

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
        jurisdictions: list[str] | None = None,
    ) -> dict[str, Any]:
        if jurisdictions:
            return self.comparison_service.compare(jurisdictions, domain, topic, as_of_date)
        return self.engine.compare_rules(jurisdiction, domain, topic, as_of_date)

    def compare_region(
        self,
        jurisdictions: list[str],
        domain: str,
        topic: str,
        as_of_date: date | None = None,
    ) -> dict[str, Any]:
        return self.comparison_service.compare(jurisdictions, domain, topic, as_of_date)

    def evaluate_ucc_filing(
        self, payload: dict[str, Any], actor_role: str, actor_identity: str
    ) -> dict[str, Any]:
        return self.ucc_filing_service.evaluate(payload, actor_role, actor_identity)

    def get_ucc_evaluation(self, evaluation_id: str) -> dict[str, Any] | None:
        return self.ucc_filing_service.get(evaluation_id)

    def review_queue(self, code: str) -> dict[str, Any] | None:
        if self.repository.get_jurisdiction(code) is None:
            return None
        rules = self.repository.query_rules(jurisdiction=code, requires_human_review=True)
        conflicts = self.repository.conflicts_for_jurisdiction(code)
        stale = self.repository.stale_authorities(code)
        challenged = [
            challenge.model_dump(mode="json")
            for challenge in self.repository.challenges.values()
            if challenge.jurisdiction == code.upper()
            and challenge.challenge_state not in {"REJECTED", "RESOLVED"}
        ]
        return {
            "jurisdiction": code.upper(),
            "pending_rules": [self._rule_payload(rule.id) for rule in rules],
            "unresolved_conflicts": [conflict.model_dump(mode="json") for conflict in conflicts],
            "stale_authorities": [authority.model_dump(mode="json") for authority in stale],
            "challenged_rules": challenged,
        }

    def conflicts(self, code: str) -> list[dict[str, Any]] | None:
        if self.repository.get_jurisdiction(code) is None:
            return None
        return [
            conflict.model_dump(mode="json")
            for conflict in self.repository.conflicts_for_jurisdiction(code)
        ]

    def stale_authorities(self, code: str) -> list[dict[str, Any]] | None:
        if self.repository.get_jurisdiction(code) is None:
            return None
        return [
            authority.model_dump(mode="json")
            for authority in self.repository.stale_authorities(code)
        ]

    def submit_review(
        self,
        rule_id: str,
        actor_role: str,
        actor_identity: str,
        findings: str | None = None,
    ) -> dict[str, Any]:
        review = self.review_workflow.submit_rule_review(
            rule_id,
            actor_role=actor_role,
            actor_identity=actor_identity,
            findings=findings or "Submitted for professional legal review.",
        )
        return review.model_dump(mode="json")

    def record_review(
        self,
        rule_id: str,
        actor_role: str,
        actor_identity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        review = self.review_workflow.record_rule_review(
            rule_id,
            reviewer_role=actor_role,
            reviewer_identity=actor_identity,
            review_status=payload["review_status"],
            findings=payload["findings"],
            declared_credentials=payload.get("declared_credentials"),
            credential_verification_status=payload.get(
                "credential_verification_status", "NOT_VERIFIED"
            ),
            conditions=payload.get("conditions"),
            reviewed_authorities=payload.get("reviewed_authorities"),
            rejected_authorities=payload.get("rejected_authorities"),
            approval_scope=payload.get("approval_scope"),
            effective_date=payload.get("effective_date"),
            expires_at=payload.get("expires_at"),
            digital_signature=payload.get("digital_signature"),
        )
        return review.model_dump(mode="json")

    def submit_challenge(
        self,
        rule_id: str,
        actor_role: str,
        actor_identity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        challenge = self.review_workflow.submit_challenge(
            rule_id,
            challenge_type=payload["challenge_type"],
            issue=payload["issue"],
            submitted_by_role=actor_role,
            submitted_by_identity=actor_identity,
            challenged_version=payload.get("challenged_version", {}),
            evidence_submitted=payload.get("evidence_submitted"),
        )
        return challenge.model_dump(mode="json")

    def reviews_for_rule(self, rule_id: str) -> list[dict[str, Any]] | None:
        if self.repository.get_rule(rule_id) is None:
            return None
        return [
            review.model_dump(mode="json") for review in self.repository.reviews_for_rule(rule_id)
        ]

    def challenges_for_rule(self, rule_id: str) -> list[dict[str, Any]] | None:
        if self.repository.get_rule(rule_id) is None:
            return None
        return [
            challenge.model_dump(mode="json")
            for challenge in self.repository.challenges_for_rule(rule_id)
        ]

    def refresh_authority_metadata(
        self,
        authority_id: str,
        actor_role: str,
        actor_identity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        result = self.source_monitor.refresh_authority_metadata(
            authority_id,
            actor_role=actor_role,
            actor_identity=actor_identity,
            supplied_content=payload.get("supplied_content"),
            supplied_hash=payload.get("supplied_hash"),
            source_available=payload.get("source_available", True),
            reason=payload.get("reason"),
        )
        return result.model_dump(mode="json")

    def _rule_payload(self, rule_id: str) -> dict[str, Any]:
        rule = self.repository.get_rule(rule_id)
        if rule is None:
            raise KeyError(rule_id)
        authorities = self.repository.authorities_for_rule(rule)
        verification_states = sorted({authority.verification_status for authority in authorities})
        limitations = sorted({item for authority in authorities for item in authority.limitations})
        if rule.requires_human_review:
            limitations.append(
                "Educational and issue-spotting output only. This system does not provide a legal opinion or replace review by a licensed attorney."
            )
        reviews = self.repository.reviews_for_rule(rule.id)
        return {
            **rule.model_dump(mode="json"),
            "verification_statuses": verification_states,
            "human_review_status": (
                "HUMAN_REVIEW_REQUIRED" if rule.requires_human_review else rule.review_status
            ),
            "review_count": len(reviews),
            "limitations": sorted(set(limitations)),
            "provenance": {
                "rule_id": rule.id,
                "authority_ids": rule.authority_ids,
                "jurisdiction": rule.jurisdiction,
                "effective_from": rule.effective_from.isoformat() if rule.effective_from else None,
                "effective_to": rule.effective_to.isoformat() if rule.effective_to else None,
                "verification_status": verification_states,
                "human_review_status": (
                    "HUMAN_REVIEW_REQUIRED" if rule.requires_human_review else rule.review_status
                ),
                "limitations": sorted(set(limitations)),
            },
        }
