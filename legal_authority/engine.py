"""Effective-date, supersession, and conflict evaluation."""

from __future__ import annotations

from datetime import UTC, date, datetime

from legal_authority.constants import AUTHORITY_HIERARCHY
from legal_authority.models import ConflictRecord, JurisdictionRule, RuleSelection
from legal_authority.repository import LegalAuthorityRepository


class RuleEvaluationEngine:
    """Selects the applicable rule for a topic and date with provenance."""

    def __init__(self, repository: LegalAuthorityRepository | None = None) -> None:
        self.repository = repository or LegalAuthorityRepository()

    def select_rule(
        self,
        jurisdiction: str,
        domain: str,
        topic: str,
        as_of_date: date | None = None,
    ) -> RuleSelection:
        query_date = as_of_date or datetime.now(UTC).date()
        candidates = [
            rule
            for rule in self.repository.query_rules(jurisdiction=jurisdiction, domain=domain)
            if topic.lower() in rule.topic.lower()
        ]
        dated, missing_dates = self._split_active_by_date(candidates, query_date)
        conflicts = self._conflicts_for_rules(dated)

        if missing_dates:
            authorities = self._unique_authorities(missing_dates)
            return RuleSelection(
                selected_rule=None,
                candidate_rule_ids=[rule.id for rule in missing_dates],
                conflicts=conflicts,
                verification_status="HUMAN_REVIEW_REQUIRED",
                human_review_required=True,
                explanation="One or more candidate rules lack effective dates, so no legal conclusion was selected.",
                as_of_date=query_date,
                limitations=["Missing effective dates require professional review before use."],
                authorities=authorities,
            )

        if conflicts:
            authorities = self._unique_authorities(dated)
            return RuleSelection(
                selected_rule=None,
                candidate_rule_ids=[rule.id for rule in dated],
                conflicts=conflicts,
                verification_status="CONFLICTING_AUTHORITY",
                human_review_required=True,
                explanation="Overlapping candidate rules have unresolved conflicting authority.",
                as_of_date=query_date,
                limitations=["The system does not average conflicting legal authorities."],
                authorities=authorities,
            )

        if not dated:
            return RuleSelection(
                selected_rule=None,
                candidate_rule_ids=[],
                conflicts=[],
                verification_status="HUMAN_REVIEW_REQUIRED",
                human_review_required=True,
                explanation="No active rule matched the requested jurisdiction, domain, topic, and date.",
                as_of_date=query_date,
                limitations=["Unsupported or unencoded topic."],
                authorities=[],
            )

        selected = self._highest_authority_rule(dated)
        authorities = self.repository.authorities_for_rule(selected)
        verification = self._combined_verification(selected)
        human_review = selected.requires_human_review or verification != "PRIMARY_SOURCE_VERIFIED"
        return RuleSelection(
            selected_rule=selected,
            candidate_rule_ids=[rule.id for rule in dated],
            conflicts=[],
            verification_status=verification if not human_review else "HUMAN_REVIEW_REQUIRED",
            human_review_required=human_review,
            explanation=self._selection_explanation(selected, query_date, dated),
            as_of_date=query_date,
            limitations=self._combined_limitations(selected),
            authorities=authorities,
        )

    def compare_rules(
        self,
        jurisdiction: str,
        domain: str,
        topic: str,
        as_of_date: date | None = None,
    ) -> dict:
        return self.select_rule(jurisdiction, domain, topic, as_of_date).model_dump(mode="json")

    def _split_active_by_date(
        self, rules: list[JurisdictionRule], as_of_date: date
    ) -> tuple[list[JurisdictionRule], list[JurisdictionRule]]:
        active: list[JurisdictionRule] = []
        missing_dates: list[JurisdictionRule] = []
        for rule in rules:
            if rule.status in {"QUARANTINED", "DRAFT"}:
                continue
            if rule.effective_from is None:
                missing_dates.append(rule)
                continue
            if rule.effective_from > as_of_date:
                continue
            if rule.effective_to is not None and rule.effective_to <= as_of_date:
                continue
            if rule.superseded_by_rule_ids and any(
                self._is_superseding_rule_active(rule_id, as_of_date)
                for rule_id in rule.superseded_by_rule_ids
            ):
                continue
            active.append(rule)
        return active, missing_dates

    def _is_superseding_rule_active(self, rule_id: str, as_of_date: date) -> bool:
        rule = self.repository.get_rule(rule_id)
        if rule is None or rule.effective_from is None:
            return False
        if rule.effective_from > as_of_date:
            return False
        return rule.effective_to is None or rule.effective_to > as_of_date

    def _conflicts_for_rules(self, rules: list[JurisdictionRule]) -> list[ConflictRecord]:
        rule_ids = {rule.id for rule in rules}
        conflicts = []
        for conflict in self.repository.conflicts.values():
            if len(rule_ids.intersection(conflict.competing_rules)) >= 2:
                conflicts.append(conflict)
        if len(rules) > 1 and not conflicts:
            authorities = self._unique_authorities(rules)
            ranking = [
                {
                    "authority_id": authority.id,
                    "authority_type": authority.authority_type,
                    "authority_weight": authority.authority_weight,
                }
                for authority in sorted(
                    authorities, key=lambda authority: authority.authority_weight, reverse=True
                )
            ]
            conflicts.append(
                ConflictRecord(
                    id="generated-overlap-" + "-".join(sorted(rule_ids)),
                    issue="Overlapping active rules",
                    jurisdiction=rules[0].jurisdiction,
                    competing_rules=sorted(rule_ids),
                    competing_authorities=[authority.id for authority in authorities],
                    authority_ranking=ranking,
                    date_relationship="Rules overlap for the requested as-of date.",
                    factual_distinctions=[],
                    unresolved_questions=["Determine whether one rule is narrower or superseded."],
                    recommended_controlling_rule=None,
                    confidence=0.0,
                    human_review_required=True,
                )
            )
        return conflicts

    def _highest_authority_rule(self, rules: list[JurisdictionRule]) -> JurisdictionRule:
        return max(rules, key=self._rule_weight)

    def _rule_weight(self, rule: JurisdictionRule) -> int:
        return max(
            AUTHORITY_HIERARCHY[self.repository.authorities[authority_id].authority_type]
            for authority_id in rule.authority_ids
        )

    def _combined_verification(self, rule: JurisdictionRule) -> str:
        states = {
            self.repository.authorities[authority_id].verification_status
            for authority_id in rule.authority_ids
        }
        if "CONFLICTING_AUTHORITY" in states:
            return "CONFLICTING_AUTHORITY"
        if states == {"PRIMARY_SOURCE_VERIFIED"}:
            return "PRIMARY_SOURCE_VERIFIED"
        if "PRIMARY_SOURCE_LOCATED" in states:
            return "PRIMARY_SOURCE_LOCATED"
        return "HUMAN_REVIEW_REQUIRED"

    def _combined_limitations(self, rule: JurisdictionRule) -> list[str]:
        limitations: list[str] = []
        for authority in self.repository.authorities_for_rule(rule):
            limitations.extend(authority.limitations)
        if rule.requires_human_review:
            limitations.append("Educational and issue-spotting output only. Not a legal opinion.")
        return sorted(set(limitations))

    def _unique_authorities(self, rules: list[JurisdictionRule]):
        authorities = {}
        for rule in rules:
            for authority in self.repository.authorities_for_rule(rule):
                authorities[authority.id] = authority
        return list(authorities.values())

    def _selection_explanation(
        self,
        selected: JurisdictionRule,
        as_of_date: date,
        candidates: list[JurisdictionRule],
    ) -> str:
        if len(candidates) == 1:
            return (
                f"{selected.id} applies on {as_of_date.isoformat()} because it is "
                "effective and not repealed or superseded."
            )
        return (
            f"{selected.id} applies on {as_of_date.isoformat()} because it has the highest "
            "controlling authority among non-conflicting effective candidates."
        )
