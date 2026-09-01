import logging
from typing import Any, Dict, List, Optional

from .policy_as_code import PolicyEffect, policy_engine

logger = logging.getLogger(__name__)

class MultiTenantGovernanceService:
    """
    Phase 7: Multi-Tenant Governance.
    Manages tenant isolation, resource quotas, and policy enforcement.
    """
    def __init__(self):
        self.policy_engine = policy_engine
        self.active_tenants: Dict[str, Dict[str, Any]] = {}

    def register_tenant(self, tenant_id: str, plan: str = "STANDARD"):
        self.active_tenants[tenant_id] = {
            "plan": plan,
            "resource_quota": 100 if plan == "GOLD" else 10,
            "active_intents": 0
        }
        logger.info(f"[GOVERNANCE] Registered tenant {tenant_id} on {plan} plan")

    async def authorize_intent(self, tenant_id: str, action: str, resource: str, context: Dict[str, Any]) -> bool:
        """
        Authorizes an intent based on tenant policies and quotas.
        """
        if tenant_id not in self.active_tenants:
            logger.error(f"[GOVERNANCE] Unauthorized tenant: {tenant_id}")
            return False

        # 1. Check Policy-as-Code
        effect = self.policy_engine.evaluate_action(tenant_id, action, resource, context)
        if effect == PolicyEffect.DENY:
            logger.warning(f"[GOVERNANCE] Policy DENY for {tenant_id}: {action} on {resource}")
            return False

        # 2. Check Resource Quotas
        tenant = self.active_tenants[tenant_id]
        if tenant["active_intents"] >= tenant["resource_quota"]:
            logger.warning(f"[GOVERNANCE] Quota exceeded for {tenant_id}")
            return False

        logger.info(f"[GOVERNANCE] Intent AUTHORIZED for {tenant_id}: {action} on {resource}")
        return True

# Global instance
governance_service = MultiTenantGovernanceService()
