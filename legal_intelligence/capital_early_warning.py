"""SP-CAPITAL-EARLY-WARNING-001 — proactive portfolio deterioration surveillance.

Consumes policy plus current/prior metrics and produces watch signals before formal default.
Signals are operational risk indicators, not legal conclusions or declarations of default.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from legal_intelligence.capital_policy_engine import CapitalPolicy


@dataclass(frozen=True)
class EarlyWarningSignal:
    code: str
    severity: str
    message: str
    source_metric: str
    current_value: Any
    prior_value: Any = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EarlyWarningReport:
    module_id: str
    policy_id: str
    policy_version: str
    watch_level: str
    signals: list[EarlyWarningSignal]
    recommended_actions: list[str]
    beneficial_suggestions: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "watch_level": self.watch_level,
            "signals": [x.as_dict() for x in self.signals],
            "recommended_actions": self.recommended_actions,
            "beneficial_suggestions": self.beneficial_suggestions,
        }


class CapitalEarlyWarningEngine:
    MODULE_ID = "SP-CAPITAL-EARLY-WARNING-001"

    def scan(self, *, policy: CapitalPolicy, current: dict[str, Any], prior: dict[str, Any] | None = None) -> EarlyWarningReport:
        prior = prior or {}
        signals: list[EarlyWarningSignal] = []

        self._drop_signal(signals, "EWS_COLLECTION_DECLINE", "HIGH", "collection_rate", current, prior, 0.10,
                          "Collections declined materially from the prior period")
        self._rise_signal(signals, "EWS_DSO_RISING", "MEDIUM", "days_sales_outstanding", current, prior, 0.10,
                          "Receivables are collecting more slowly")
        self._drop_signal(signals, "EWS_COLLATERAL_COVERAGE_FALLING", "HIGH", "collateral_coverage_ratio", current, prior, 0.10,
                          "Collateral coverage has materially weakened")
        self._drop_signal(signals, "EWS_LIQUIDITY_COMPRESSION", "HIGH", "liquidity_ratio", current, prior, 0.10,
                          "Liquidity has materially compressed")

        waiver_count = int(current.get("covenant_waivers_rolling_12m") or 0)
        if waiver_count >= 2:
            signals.append(EarlyWarningSignal("EWS_REPEAT_COVENANT_WAIVERS", "HIGH", "Repeated covenant waivers may indicate persistent weakness", "covenant_waivers_rolling_12m", waiver_count))

        concentration = float(current.get("receivable_customer_concentration") or 0)
        if policy.receivable_customer_concentration_max and concentration >= policy.receivable_customer_concentration_max * 0.9:
            severity = "HIGH" if concentration > policy.receivable_customer_concentration_max else "MEDIUM"
            signals.append(EarlyWarningSignal("EWS_CONCENTRATION_DRIFT", severity, "Customer concentration is near or above policy limit", "receivable_customer_concentration", concentration))

        if current.get("insurance_status") in {"lapsed", "expired", "cancelled", False}:
            signals.append(EarlyWarningSignal("EWS_INSURANCE_LAPSE", "CRITICAL", "Collateral insurance appears lapsed or inactive", "insurance_status", current.get("insurance_status")))

        perfection_days = current.get("perfection_expiry_days")
        if perfection_days is not None and int(perfection_days) <= 90:
            sev = "CRITICAL" if int(perfection_days) <= 30 else "HIGH"
            signals.append(EarlyWarningSignal("EWS_PERFECTION_EXPIRING", sev, "Perfection/continuation action may be approaching", "perfection_expiry_days", int(perfection_days)))

        exception_count = int(current.get("policy_exceptions_rolling_6m") or 0)
        if exception_count >= 3:
            signals.append(EarlyWarningSignal("EWS_RECURRING_POLICY_EXCEPTIONS", "HIGH", "Recurring policy exceptions may indicate control erosion", "policy_exceptions_rolling_6m", exception_count))

        dpd = int(current.get("days_past_due") or 0)
        if dpd > 0:
            severity = "HIGH" if dpd >= max(1, int(policy.maximum_delinquency_days * 0.75)) else "MEDIUM"
            signals.append(EarlyWarningSignal("EWS_DELINQUENCY_EMERGING", severity, "Delinquency is developing before/near policy default threshold", "days_past_due", dpd))

        reserve_ratio = float(current.get("reserve_ratio") or 0)
        if reserve_ratio and reserve_ratio <= policy.reserve_floor_ratio + policy.stress_buffer_ratio:
            signals.append(EarlyWarningSignal("EWS_RESERVE_BUFFER_THIN", "HIGH", "Reserve ratio is approaching policy floor after stress buffer", "reserve_ratio", reserve_ratio))

        level = self._level(signals)
        actions = self._actions(signals)
        suggestions = [
            "Trend signals over multiple periods; do not treat a single noisy data point as a legal default.",
            "Link every signal to source evidence and the governing policy version.",
            "Escalate CRITICAL signals to independent review before new funding, distributions, collateral releases, or restructures.",
            "Track whether management responses resolved, stabilized, or worsened each signal in the next reporting cycle.",
        ]
        return EarlyWarningReport(self.MODULE_ID, policy.policy_id, policy.policy_version, level, signals, actions, suggestions)

    @staticmethod
    def _drop_signal(signals, code, severity, key, current, prior, threshold, message):
        if key not in current or key not in prior:
            return
        c, p = float(current[key] or 0), float(prior[key] or 0)
        if p > 0 and (p - c) / p >= threshold:
            signals.append(EarlyWarningSignal(code, severity, message, key, c, p))

    @staticmethod
    def _rise_signal(signals, code, severity, key, current, prior, threshold, message):
        if key not in current or key not in prior:
            return
        c, p = float(current[key] or 0), float(prior[key] or 0)
        if p > 0 and (c - p) / p >= threshold:
            signals.append(EarlyWarningSignal(code, severity, message, key, c, p))

    @staticmethod
    def _level(signals: list[EarlyWarningSignal]) -> str:
        severities = {x.severity for x in signals}
        if "CRITICAL" in severities:
            return "CRITICAL"
        if "HIGH" in severities:
            return "HIGH"
        if "MEDIUM" in severities:
            return "WATCH"
        return "NORMAL"

    @staticmethod
    def _actions(signals: list[EarlyWarningSignal]) -> list[str]:
        codes = {x.code for x in signals}
        actions: list[str] = []
        if codes & {"EWS_COLLECTION_DECLINE", "EWS_DSO_RISING"}:
            actions.append("Re-underwrite receivable quality and collections assumptions; refresh borrowing base.")
        if "EWS_COLLATERAL_COVERAGE_FALLING" in codes:
            actions.append("Obtain an updated collateral valuation and review LTV/covenant headroom.")
        if "EWS_INSURANCE_LAPSE" in codes:
            actions.append("Verify coverage immediately and block collateral release or new funding until resolved.")
        if "EWS_PERFECTION_EXPIRING" in codes:
            actions.append("Verify filing/control status and calendar continuation or renewal action before expiry.")
        if codes & {"EWS_REPEAT_COVENANT_WAIVERS", "EWS_RECURRING_POLICY_EXCEPTIONS"}:
            actions.append("Escalate to credit committee for root-cause review rather than issuing another routine exception.")
        if "EWS_LIQUIDITY_COMPRESSION" in codes or "EWS_RESERVE_BUFFER_THIN" in codes:
            actions.append("Reduce discretionary deployment and rerun stress testing before additional advances.")
        return actions
