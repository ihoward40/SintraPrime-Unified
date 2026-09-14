"""SP-CAPITAL-OVERRIDE-001 — governed policy overrides, waivers, freeze releases, and exception closures."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


ALLOWED_OVERRIDE_TYPES = {
    "POLICY_OVERRIDE",
    "FUNDING_FREEZE_RELEASE",
    "COVENANT_WAIVER",
    "EXCEPTION_CLOSURE",
}


@dataclass
class CapitalOverride:
    override_id: str
    override_type: str
    subject_id: str
    reason_code: str
    rationale: str
    requested_by: str
    approved_by: str
    approval_authority: str
    effective_at: str
    expires_at: str
    compensating_controls: list[str] = field(default_factory=list)
    re_review_at: str = ""
    policy_id: str = ""
    policy_version: str = ""
    status: str = "ACTIVE"
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalOverrideEngine:
    MODULE_ID = "SP-CAPITAL-OVERRIDE-001"

    def create(self, context: dict[str, Any]) -> CapitalOverride:
        override_type = str(context.get("override_type") or "").upper()
        if override_type not in ALLOWED_OVERRIDE_TYPES:
            raise ValueError("OVERRIDE_TYPE_INVALID")
        requested_by = str(context.get("requested_by") or "")
        approved_by = str(context.get("approved_by") or "")
        if not requested_by or not approved_by:
            raise ValueError("OVERRIDE_REQUESTER_AND_APPROVER_REQUIRED")
        if requested_by == approved_by:
            raise ValueError("OVERRIDE_SELF_APPROVAL_PROHIBITED")
        required = [
            "override_id", "subject_id", "reason_code", "rationale", "approval_authority",
            "effective_at", "expires_at", "re_review_at", "policy_id", "policy_version",
        ]
        missing = [x for x in required if not str(context.get(x) or "")]
        if missing:
            raise ValueError("OVERRIDE_REQUIRED_FIELDS_MISSING:" + ",".join(missing))
        controls = list(context.get("compensating_controls") or [])
        if not controls:
            raise ValueError("OVERRIDE_COMPENSATING_CONTROLS_REQUIRED")
        effective = datetime.fromisoformat(str(context["effective_at"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(context["expires_at"]).replace("Z", "+00:00"))
        review = datetime.fromisoformat(str(context["re_review_at"]).replace("Z", "+00:00"))
        if expires <= effective:
            raise ValueError("OVERRIDE_EXPIRY_MUST_FOLLOW_EFFECTIVE_DATE")
        if review > expires:
            raise ValueError("OVERRIDE_REREVIEW_AFTER_EXPIRY")
        suggestions = [
            "Prefer narrowly scoped, time-limited overrides over permanent threshold weakening.",
            "Record the override in the decision journal and link it to the affected case, facility, policy version, and evidence.",
            "Require a fresh approval if the override must continue beyond its original expiry.",
        ]
        return CapitalOverride(
            override_id=str(context["override_id"]),
            override_type=override_type,
            subject_id=str(context["subject_id"]),
            reason_code=str(context["reason_code"]),
            rationale=str(context["rationale"]),
            requested_by=requested_by,
            approved_by=approved_by,
            approval_authority=str(context["approval_authority"]),
            effective_at=effective.isoformat(),
            expires_at=expires.isoformat(),
            compensating_controls=controls,
            re_review_at=review.isoformat(),
            policy_id=str(context["policy_id"]),
            policy_version=str(context["policy_version"]),
            beneficial_suggestions=suggestions,
        )

    def evaluate(self, override: CapitalOverride, *, now: str | None = None, trigger_resolved: bool = False) -> dict[str, Any]:
        current = datetime.fromisoformat((now or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
        expiry = datetime.fromisoformat(override.expires_at.replace("Z", "+00:00"))
        review = datetime.fromisoformat(override.re_review_at.replace("Z", "+00:00"))
        expired = current >= expiry
        review_due = current >= review and not expired
        status = "EXPIRED" if expired else "REVIEW_DUE" if review_due else override.status
        actions: list[str] = []
        if expired:
            actions.extend(["REINSTATE_UNDERLYING_CONTROL", "REOPEN_ASSOCIATED_CASE", "BLOCK_RELIANCE_ON_OVERRIDE"])
        elif review_due:
            actions.append("MANDATORY_REREVIEW")
        if trigger_resolved:
            actions.append("CONSIDER_EARLY_TERMINATION")
        return {
            "module_id": self.MODULE_ID,
            "override_id": override.override_id,
            "status": status,
            "expired": expired,
            "review_due": review_due,
            "actions": actions,
            "beneficial_suggestions": [
                "Do not auto-renew overrides; require a new decision with current evidence and authority.",
                "Escalate expired funding-freeze releases or covenant waivers back to case management immediately.",
            ],
        }

    def can_release_funding_freeze(self, context: dict[str, Any]) -> dict[str, Any]:
        issues: list[str] = []
        if not context.get("underlying_trigger_resolved"):
            issues.append("UNDERLYING_TRIGGER_NOT_RESOLVED")
        if not context.get("case_owner_recommendation"):
            issues.append("CASE_OWNER_RECOMMENDATION_REQUIRED")
        if not context.get("independent_approval"):
            issues.append("INDEPENDENT_APPROVAL_REQUIRED")
        if not context.get("current_policy_evaluation_passed"):
            issues.append("CURRENT_POLICY_REEVALUATION_REQUIRED")
        if not context.get("stress_test_passed"):
            issues.append("STRESS_TEST_REEVALUATION_REQUIRED")
        return {
            "module_id": self.MODULE_ID,
            "release_allowed": not issues,
            "issues": issues,
        }
