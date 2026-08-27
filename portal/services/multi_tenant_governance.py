import logging
from typing import Any

from .policy_as_code import PolicyEffect, policy_engine

logger = logging.getLogger(__name__)


class MultiTenantGovernanceService:
    """Manage tenant isolation, resource quotas, and policy enforcement."""

    def __init__(self):
        self.policy_engine = policy_engine
        self.active_tenants: dict[str, dict[str, Any]] = {}

    def register_tenant(self, tenant_id: str, plan: str = "STANDARD"):
        self.active_tenants[tenant_id] = {
            "plan": plan,
            "resource_quota": 100 if plan == "GOLD" else 10,
            "active_intents": 0,
        }
        logger.info("[GOVERNANCE] Registered tenant %s on %s plan", tenant_id, plan)

    async def authorize_intent(
        self,
        tenant_id: str,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> bool:
        """Authorize an intent based on tenant policies and quotas."""
        if tenant_id not in self.active_tenants:
            logger.error("[GOVERNANCE] Unauthorized tenant: %s", tenant_id)
            return False

        effect = self.policy_engine.evaluate_action(tenant_id, action, resource, context)
        if effect == PolicyEffect.DENY:
            logger.warning(
                "[GOVERNANCE] Policy DENY for %s: %s on %s",
                tenant_id,
                action,
                resource,
            )
            return False

        tenant = self.active_tenants[tenant_id]
        if tenant["active_intents"] >= tenant["resource_quota"]:
            logger.warning("[GOVERNANCE] Quota exceeded for %s", tenant_id)
            return False

        logger.info(
            "[GOVERNANCE] Intent AUTHORIZED for %s: %s on %s",
            tenant_id,
            action,
            resource,
        )
        return True


governance_service = MultiTenantGovernanceService()
