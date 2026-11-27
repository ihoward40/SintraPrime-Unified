"""SP-POLICY-CHANGE-CONTROL-001 — governed capital-policy change control.

Every material threshold/rule change is treated as a controlled event with explicit
impact analysis, approval authority, effective date, rollback target, affected-facility
inventory, migration treatment, and grandfather/re-underwrite rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any


@dataclass(frozen=True)
class PolicyChangeRequest:
    change_id: str
    policy_id: str
    from_version: str
    to_version: str
    requested_by: str
    effective_date: str
    changed_fields: tuple[str, ...]
    rationale: str
    rollback_version: str
    affected_facilities: tuple[str, ...]
    migration_rule: str
    grandfather_existing: bool
    reunderwrite_required: bool
    impact_analysis_complete: bool
    approval_authority: str
    approved_by: str = ""
    evidence_refs: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyChangeDecision:
    module_id: str
    decision: str
    blocking_reasons: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    migration_actions: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class PolicyChangeControlEngine:
    MODULE_ID = "SP-POLICY-CHANGE-CONTROL-001"

    MATERIAL_FIELDS = {
        "reserve_floor",
        "minimum_dscr",
        "maximum_ltv",
        "borrower_concentration_limit",
        "affiliate_group_concentration_limit",
        "collateral_class_concentration_limit",
        "receivable_customer_concentration_limit",
        "maker_checker_threshold",
        "revaluation_frequency_days",
        "maximum_delinquency_days",
        "liquidity_buffer",
        "stress_buffer",
        "override_authority",
    }

    def evaluate(self, request: PolicyChangeRequest) -> PolicyChangeDecision:
        blockers: list[str] = []
        conditions: list[str] = []
        actions: list[str] = []

        if not request.change_id:
            blockers.append("POLICY_CHANGE_ID_REQUIRED")
        if not request.policy_id or not request.from_version or not request.to_version:
            blockers.append("POLICY_VERSION_LINEAGE_REQUIRED")
        if request.from_version == request.to_version:
            blockers.append("POLICY_VERSION_MUST_CHANGE")
        if not request.changed_fields:
            blockers.append("POLICY_CHANGED_FIELDS_REQUIRED")
        if not request.rationale:
            blockers.append("POLICY_CHANGE_RATIONALE_REQUIRED")
        if not request.impact_analysis_complete:
            blockers.append("POLICY_IMPACT_ANALYSIS_REQUIRED")
        if not request.approval_authority:
            blockers.append("POLICY_APPROVAL_AUTHORITY_REQUIRED")
        if not request.approved_by:
            blockers.append("POLICY_APPROVER_REQUIRED")
        if request.requested_by and request.approved_by and request.requested_by == request.approved_by:
            blockers.append("POLICY_SELF_APPROVAL_PROHIBITED")
        if not request.effective_date:
            blockers.append("POLICY_EFFECTIVE_DATE_REQUIRED")
        if not request.rollback_version:
            blockers.append("POLICY_ROLLBACK_VERSION_REQUIRED")
        if not request.migration_rule:
            blockers.append("POLICY_MIGRATION_RULE_REQUIRED")

        material = bool(set(request.changed_fields) & self.MATERIAL_FIELDS)
        if material and not request.affected_facilities:
            blockers.append("AFFECTED_FACILITY_INVENTORY_REQUIRED")

        if request.grandfather_existing and request.reunderwrite_required:
            conditions.append("Resolve conflict between grandfathering and mandatory re-underwriting before activation.")

        if request.affected_facilities:
            actions.append("Snapshot every affected facility under the prior policy version before migration.")
            actions.append("Run before/after policy tests and record newly created breaches or exceptions.")
            if request.reunderwrite_required:
                actions.append("Re-underwrite each affected facility before migrated terms become operative.")
            elif request.grandfather_existing:
                actions.append("Record grandfather status and define the event that causes migration to the new policy.")
            else:
                actions.append("Apply the stated migration rule consistently to all affected facilities and document exceptions.")

        actions.extend([
            "Persist the prior and new policy snapshots with immutable hashes.",
            "Record the change in the decision journal and include the new policy version in the next monthly audit package.",
            "Run stress and concentration analysis under both old and new thresholds before the effective date.",
        ])

        decision = "BLOCK" if blockers else ("PASS_WITH_CONDITIONS" if conditions else "PASS")
        suggestions = [
            "Use semantic versioning or another monotonic policy-version convention and never silently overwrite a published version.",
            "Require emergency policy changes to expire automatically unless ratified through the ordinary governance path.",
            "Maintain a rollback rehearsal so the prior version can be restored without losing audit lineage.",
            "Generate a facility-by-facility migration report showing old status, new status, and required remediation.",
        ]
        return PolicyChangeDecision(
            module_id=self.MODULE_ID,
            decision=decision,
            blocking_reasons=list(dict.fromkeys(blockers)),
            conditions=list(dict.fromkeys(conditions)),
            migration_actions=list(dict.fromkeys(actions)),
            beneficial_suggestions=suggestions,
        )

    @staticmethod
    def effective_date_is_future_or_today(effective_date: str, *, today: str | None = None) -> bool:
        try:
            target = date.fromisoformat(effective_date)
            current = date.fromisoformat(today) if today else date.today()
            return target >= current
        except ValueError:
            return False
