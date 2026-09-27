"""Monthly credit/risk committee pack assembler for the private-capital stack.

Combines governance outputs without converting internal controls into a bank-regulatory
report or external audit opinion. Missing sections remain visible as exceptions rather
than being silently omitted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class CommitteePack:
    module_id: str
    period: str
    status: str
    executive_summary: dict[str, Any]
    sections: dict[str, Any]
    unresolved_exceptions: tuple[str, ...]
    decisions_required: tuple[str, ...]
    evidence_index: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]
    assembled_at: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalCommitteePackEngine:
    MODULE_ID = "SP-CAPITAL-COMMITTEE-PACK-001"
    REQUIRED_SECTIONS = (
        "dashboard",
        "risk_trends",
        "cases",
        "overrides",
        "stress_results",
        "workout_recoveries",
        "policy_changes",
        "audit_exceptions",
        "decision_journal_anchor",
    )

    def assemble(self, context: dict[str, Any]) -> CommitteePack:
        period = str(context.get("period", ""))
        sections = {name: context.get(name) for name in self.REQUIRED_SECTIONS}
        unresolved: list[str] = []
        evidence_index: list[str] = []
        decisions: list[str] = []

        if not period:
            unresolved.append("MISSING_PERIOD")

        for name, value in sections.items():
            if value is None:
                unresolved.append(f"MISSING_SECTION:{name}")
            refs = self._extract_refs(value)
            evidence_index.extend(refs)

        dashboard = sections.get("dashboard") or {}
        trends = sections.get("risk_trends") or {}
        cases = sections.get("cases") or []
        overrides = sections.get("overrides") or []
        stress = sections.get("stress_results") or {}
        audit_exceptions = sections.get("audit_exceptions") or []

        open_cases = self._count(cases, lambda r: str(r.get("status", "")).upper() not in {"CLOSED", "RESOLVED"})
        critical_cases = self._count(cases, lambda r: str(r.get("severity", "")).upper() == "CRITICAL")
        expired_overrides = self._count(overrides, lambda r: str(r.get("status", "")).upper() in {"EXPIRED", "LAPSED"})
        active_overrides = self._count(overrides, lambda r: str(r.get("status", "")).upper() in {"ACTIVE", "APPROVED"})

        trend_direction = str(trends.get("direction", "UNKNOWN"))
        stress_status = str(stress.get("status", stress.get("decision", "UNKNOWN")))
        reserve_shortfall = dashboard.get("reserve_shortfall", 0) or 0

        if critical_cases:
            decisions.append("REVIEW_CRITICAL_CASES")
        if active_overrides:
            decisions.append("REVIEW_ACTIVE_OVERRIDES_AND_EXPIRY")
        if expired_overrides:
            decisions.append("CONFIRM_EXPIRED_OVERRIDES_REINSTATED_CONTROLS")
        if trend_direction == "DETERIORATING":
            decisions.append("APPROVE_PORTFOLIO_RISK_REMEDIATION_PLAN")
        if stress_status in {"BLOCK_NEW_ADVANCES", "FAIL", "CRITICAL", "BREACH"}:
            decisions.append("REVIEW_STRESS_BREACH_AND_FUNDING_POSTURE")
        if float(reserve_shortfall) > 0:
            decisions.append("ADDRESS_RESERVE_SHORTFALL")
        if audit_exceptions:
            decisions.append("DISPOSE_AUDIT_EXCEPTIONS_WITH_OWNER_AND_DUE_DATE")

        status = "READY"
        if unresolved:
            status = "INCOMPLETE"
        elif critical_cases or float(reserve_shortfall) > 0 or stress_status in {"BLOCK_NEW_ADVANCES", "FAIL", "CRITICAL", "BREACH"}:
            status = "READY_WITH_CRITICAL_ITEMS"
        elif decisions:
            status = "READY_WITH_DECISIONS"

        executive = {
            "period": period,
            "total_exposure": dashboard.get("total_exposure"),
            "available_liquidity": dashboard.get("available_liquidity"),
            "reserve_shortfall": reserve_shortfall,
            "trend_direction": trend_direction,
            "open_cases": open_cases,
            "critical_cases": critical_cases,
            "active_overrides": active_overrides,
            "expired_overrides": expired_overrides,
            "stress_status": stress_status,
            "audit_exception_count": len(audit_exceptions) if isinstance(audit_exceptions, list) else 0,
        }

        suggestions = [
            "Require committee disposition for every decision-required item and record the result in the decision journal.",
            "Attach source references for every material number or exception so the pack is reconstructable.",
            "Compare the current pack against prior committee packs to distinguish persistent issues from new deterioration.",
            "Do not treat committee approval as curing missing legal authority, documentation, perfection, licensing, or fiduciary review.",
        ]
        if unresolved:
            suggestions.append("Do not certify the monthly committee pack complete until every required section is supplied or formally marked unavailable with explanation.")

        return CommitteePack(
            module_id=self.MODULE_ID,
            period=period,
            status=status,
            executive_summary=executive,
            sections=sections,
            unresolved_exceptions=tuple(unresolved),
            decisions_required=tuple(dict.fromkeys(decisions)),
            evidence_index=tuple(dict.fromkeys(evidence_index)),
            beneficial_suggestions=tuple(suggestions),
            assembled_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _count(rows: Any, predicate: Any) -> int:
        if not isinstance(rows, list):
            return 0
        return sum(1 for row in rows if isinstance(row, dict) and predicate(row))

    @classmethod
    def _extract_refs(cls, value: Any) -> list[str]:
        refs: list[str] = []
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"evidence_ref", "source_ref", "anchor_ref", "journal_ref", "document_ref"} and item:
                    refs.append(str(item))
                elif key in {"evidence_refs", "source_refs", "document_refs"} and isinstance(item, (list, tuple)):
                    refs.extend(str(x) for x in item if x)
                else:
                    refs.extend(cls._extract_refs(item))
        elif isinstance(value, list):
            for item in value:
                refs.extend(cls._extract_refs(item))
        return refs
