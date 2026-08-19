import logging
from enum import StrEnum
from typing import Any

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PolicyEffect(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    AUDIT = "AUDIT"


class PolicyStatement(BaseModel):
    id: str
    effect: PolicyEffect
    actions: list[str]
    resources: list[str]
    conditions: dict[str, Any] | None = None


class PolicyAsCodeService:
    """Enforce governance rules and security constraints across the platform."""

    def __init__(self):
        self.global_policies: dict[str, PolicyStatement] = {}
        self.tenant_policies: dict[str, dict[str, PolicyStatement]] = {}

    def load_policy_from_yaml(self, yaml_content: str, tenant_id: str | None = None):
        """Load a policy definition from YAML."""
        data = yaml.safe_load(yaml_content)
        statement = PolicyStatement(**data)

        if tenant_id:
            self.tenant_policies.setdefault(tenant_id, {})[statement.id] = statement
            logger.info(
                "[POLICY_AS_CODE] Loaded tenant policy %s for %s",
                statement.id,
                tenant_id,
            )
        else:
            self.global_policies[statement.id] = statement
            logger.info("[POLICY_AS_CODE] Loaded global policy %s", statement.id)

    def evaluate_action(
        self,
        tenant_id: str,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyEffect:
        """Evaluate an action against global and tenant policies."""
        for policy in self.global_policies.values():
            if policy.effect == PolicyEffect.DENY and self._matches(
                policy,
                action,
                resource,
                context,
            ):
                return PolicyEffect.DENY

        for policy in self.tenant_policies.get(tenant_id, {}).values():
            if policy.effect == PolicyEffect.DENY and self._matches(
                policy,
                action,
                resource,
                context,
            ):
                return PolicyEffect.DENY

        for policy in self.global_policies.values():
            if policy.effect == PolicyEffect.ALLOW and self._matches(
                policy,
                action,
                resource,
                context,
            ):
                return PolicyEffect.ALLOW

        for policy in self.tenant_policies.get(tenant_id, {}).values():
            if policy.effect == PolicyEffect.ALLOW and self._matches(
                policy,
                action,
                resource,
                context,
            ):
                return PolicyEffect.ALLOW

        return PolicyEffect.DENY

    def _matches(
        self,
        policy: PolicyStatement,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> bool:
        """Check whether a policy statement matches the current request."""
        action_match = "*" in policy.actions or action in policy.actions
        resource_match = "*" in policy.resources or resource in policy.resources
        condition_match = not policy.conditions or all(
            context.get(key) == value for key, value in policy.conditions.items()
        )
        return action_match and resource_match and condition_match


policy_engine = PolicyAsCodeService()
