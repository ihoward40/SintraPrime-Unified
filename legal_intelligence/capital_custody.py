"""SP-CAPITAL-CUSTODY-001 — independent maker/checker control plane.

Separates initiation, review, approval, anchoring, and certification duties for
private-capital actions. This is an internal governance control, not a banking or
custodial license.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CustodyRoleAssignment:
    actor: str
    roles: tuple[str, ...]


@dataclass
class CustodyDecision:
    module_id: str
    action_type: str
    allowed: bool
    maker: str
    checker: str
    approver: str
    anchor_actor: str | None
    certifier: str | None
    violations: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalCustodyEngine:
    MODULE_ID = "SP-CAPITAL-CUSTODY-001"

    SENSITIVE_ACTIONS = {
        "funding",
        "collateral_change",
        "policy_override",
        "journal_anchor",
        "monthly_audit_certification",
        "restructure_approval",
        "writeoff_approval",
    }

    def evaluate(self, context: dict[str, Any]) -> CustodyDecision:
        action = str(context.get("action_type") or "").strip().lower()
        maker = str(context.get("maker") or "").strip()
        checker = str(context.get("checker") or "").strip()
        approver = str(context.get("approver") or "").strip()
        anchor_actor = str(context.get("anchor_actor") or "").strip() or None
        certifier = str(context.get("certifier") or "").strip() or None

        violations: list[str] = []
        actors = [x for x in [maker, checker, approver] if x]
        if action in self.SENSITIVE_ACTIONS:
            if not maker:
                violations.append("MAKER_REQUIRED")
            if not checker:
                violations.append("CHECKER_REQUIRED")
            if not approver:
                violations.append("APPROVER_REQUIRED")
            if len(set(actors)) != len(actors):
                violations.append("SELF_APPROVAL_OR_ROLE_COLLISION")

        if action == "journal_anchor":
            if not anchor_actor:
                violations.append("ANCHOR_ACTOR_REQUIRED")
            elif anchor_actor in {maker, checker, approver}:
                violations.append("ANCHOR_ROLE_NOT_INDEPENDENT")

        if action == "monthly_audit_certification":
            if not certifier:
                violations.append("CERTIFIER_REQUIRED")
            elif certifier in {maker, checker, approver}:
                violations.append("CERTIFIER_ROLE_NOT_INDEPENDENT")

        if context.get("same_credentials_shared"):
            violations.append("SHARED_CREDENTIALS_PROHIBITED")
        if context.get("single_device_uncontrolled"):
            violations.append("UNCONTROLLED_SINGLE_DEVICE_RISK")

        suggestions = [
            "Use separate named identities and credentials for maker, checker, approver, anchoring, and certification roles.",
            "Require role changes and emergency overrides to be journaled and independently reviewed.",
            "Keep approval evidence and anchor receipts outside the same primary database when practical.",
        ]
        if violations:
            suggestions.append("Do not execute the sensitive action until all custody violations are resolved or a documented Principal-approved emergency control is invoked.")

        return CustodyDecision(
            module_id=self.MODULE_ID,
            action_type=action,
            allowed=not violations,
            maker=maker,
            checker=checker,
            approver=approver,
            anchor_actor=anchor_actor,
            certifier=certifier,
            violations=violations,
            beneficial_suggestions=suggestions,
        )
