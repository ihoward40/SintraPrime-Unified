"""SP-CAPITAL-POLICY-ENGINE-001 — centralized private-capital policy control plane.

Provides one versioned source of truth for reserve, DSCR, LTV, concentration,
maker/checker, revaluation, delinquency, and stress thresholds. Downstream decisions
should persist policy_id + policy_version so historical approvals remain reproducible.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CapitalPolicy:
    policy_id: str
    policy_version: str
    effective_date: str
    reserve_floor_amount: float
    reserve_floor_ratio: float
    dscr_minimum: float
    ltv_maximum: float
    borrower_concentration_max: float
    affiliate_group_concentration_max: float
    collateral_class_concentration_max: float
    receivable_customer_concentration_max: float
    maker_checker_threshold: float
    revaluation_frequency_days: int
    maximum_delinquency_days: int
    stress_buffer_ratio: float
    liquidity_buffer_ratio: float
    override_authorities: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyEvaluation:
    module_id: str
    policy_id: str
    policy_version: str
    status: str
    breaches: list[str]
    warnings: list[str]
    beneficial_suggestions: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalPolicyEngine:
    MODULE_ID = "SP-CAPITAL-POLICY-ENGINE-001"

    REQUIRED_THRESHOLDS = (
        "reserve_floor_amount", "reserve_floor_ratio", "dscr_minimum", "ltv_maximum",
        "borrower_concentration_max", "affiliate_group_concentration_max",
        "collateral_class_concentration_max", "receivable_customer_concentration_max",
        "maker_checker_threshold", "revaluation_frequency_days",
        "maximum_delinquency_days", "stress_buffer_ratio", "liquidity_buffer_ratio",
    )

    def validate_policy(self, policy: CapitalPolicy) -> list[str]:
        errors: list[str] = []
        if not policy.policy_id:
            errors.append("POLICY_ID_REQUIRED")
        if not policy.policy_version:
            errors.append("POLICY_VERSION_REQUIRED")
        if not policy.effective_date:
            errors.append("POLICY_EFFECTIVE_DATE_REQUIRED")
        if policy.dscr_minimum <= 0:
            errors.append("DSCR_MINIMUM_INVALID")
        if not 0 < policy.ltv_maximum <= 1.0:
            errors.append("LTV_MAXIMUM_INVALID")
        for name in (
            "reserve_floor_ratio", "borrower_concentration_max",
            "affiliate_group_concentration_max", "collateral_class_concentration_max",
            "receivable_customer_concentration_max", "stress_buffer_ratio",
            "liquidity_buffer_ratio",
        ):
            value = float(getattr(policy, name))
            if value < 0 or value > 1.0:
                errors.append(f"{name.upper()}_INVALID")
        if policy.revaluation_frequency_days <= 0:
            errors.append("REVALUATION_FREQUENCY_INVALID")
        if policy.maximum_delinquency_days < 0:
            errors.append("MAXIMUM_DELINQUENCY_INVALID")
        return errors

    def evaluate(self, policy: CapitalPolicy, metrics: dict[str, Any]) -> PolicyEvaluation:
        breaches: list[str] = []
        warnings: list[str] = []
        reserve_available = float(metrics.get("reserve_available") or 0)
        total_exposure = float(metrics.get("total_exposure") or 0)
        reserve_ratio = (reserve_available / total_exposure) if total_exposure > 0 else 1.0
        dscr = float(metrics.get("dscr") or 0)
        ltv = float(metrics.get("ltv") or 0)
        days_past_due = int(metrics.get("days_past_due") or 0)
        liquidity_ratio = float(metrics.get("liquidity_ratio") or 0)

        if reserve_available < policy.reserve_floor_amount or reserve_ratio < policy.reserve_floor_ratio:
            breaches.append("RESERVE_POLICY_BREACH")
        if dscr and dscr < policy.dscr_minimum:
            breaches.append("DSCR_POLICY_BREACH")
        if ltv and ltv > policy.ltv_maximum:
            breaches.append("LTV_POLICY_BREACH")
        if days_past_due > policy.maximum_delinquency_days:
            breaches.append("DELINQUENCY_POLICY_BREACH")
        if liquidity_ratio < policy.liquidity_buffer_ratio:
            breaches.append("LIQUIDITY_POLICY_BREACH")

        concentration_map = {
            "borrower_concentration": policy.borrower_concentration_max,
            "affiliate_group_concentration": policy.affiliate_group_concentration_max,
            "collateral_class_concentration": policy.collateral_class_concentration_max,
            "receivable_customer_concentration": policy.receivable_customer_concentration_max,
        }
        for key, limit in concentration_map.items():
            value = float(metrics.get(key) or 0)
            if value > limit:
                breaches.append(f"{key.upper()}_BREACH")
            elif limit and value >= limit * 0.9:
                warnings.append(f"{key.upper()}_NEAR_LIMIT")

        age = int(metrics.get("collateral_valuation_age_days") or 0)
        if age > policy.revaluation_frequency_days:
            breaches.append("COLLATERAL_REVALUATION_OVERDUE")
        elif age >= int(policy.revaluation_frequency_days * 0.8):
            warnings.append("COLLATERAL_REVALUATION_DUE_SOON")

        amount = float(metrics.get("transaction_amount") or 0)
        if amount >= policy.maker_checker_threshold and not bool(metrics.get("independent_checker_present")):
            breaches.append("MAKER_CHECKER_REQUIRED")

        status = "BREACH" if breaches else ("WATCH" if warnings else "COMPLIANT")
        suggestions = [
            "Persist policy_id and policy_version on every approval, override, funding, restructure, and monthly certification.",
            "Require formal versioning rather than silently editing thresholds in place.",
            "Run impact analysis before activating a stricter or looser policy version.",
        ]
        if breaches:
            suggestions.append("Freeze affected new capital deployment until the breach is cured or a documented authorized override is approved.")
        return PolicyEvaluation(self.MODULE_ID, policy.policy_id, policy.policy_version, status, breaches, warnings, suggestions)

    @staticmethod
    def threshold(policy: CapitalPolicy, name: str) -> Any:
        if name not in CapitalPolicyEngine.REQUIRED_THRESHOLDS:
            raise KeyError(name)
        return getattr(policy, name)
