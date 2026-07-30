"""Default authority policy for browser automation."""

from __future__ import annotations

from .contracts import ActionDecision, ActionPolicy, BrowserAction


class DefaultActionPolicy(ActionPolicy):
    """Fail closed for consequential actions and permit read-only navigation.

    Provider adapters must call this policy before execution.  A later adapter
    can connect decisions to Mission Control receipts and approval records.
    """

    _READ_ONLY = frozenset({"open", "navigate", "read", "scroll", "screenshot"})
    _APPROVAL_REQUIRED = frozenset(
        {
            "click",
            "type",
            "upload",
            "download",
            "submit",
            "send",
            "purchase",
            "sign",
            "file",
            "delete",
        }
    )

    def decide(
        self,
        action: BrowserAction,
        *,
        tenant_id: str,
        actor_id: str,
    ) -> ActionDecision:
        if not tenant_id.strip() or not actor_id.strip():
            return ActionDecision.DENY
        normalized = action.action.strip().lower()
        if normalized in self._READ_ONLY:
            return ActionDecision.ALLOW
        if normalized in self._APPROVAL_REQUIRED:
            return ActionDecision.REQUIRE_APPROVAL
        return ActionDecision.DENY
