import logging
import yaml
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class PolicyEffect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    AUDIT = "AUDIT"

class PolicyStatement(BaseModel):
    id: str
    effect: PolicyEffect
    actions: List[str]
    resources: List[str]
    conditions: Optional[Dict[str, Any]] = None

class PolicyAsCodeService:
    """
    Phase 7: Policy-as-Code.
    Enforces governance rules and security constraints across the platform.
    """
    def __init__(self):
        self.global_policies: Dict[str, PolicyStatement] = {}
        self.tenant_policies: Dict[str, Dict[str, PolicyStatement]] = {}

    def load_policy_from_yaml(self, yaml_content: str, tenant_id: Optional[str] = None):
        """Loads a policy definition from YAML."""
        data = yaml.safe_load(yaml_content)
        statement = PolicyStatement(**data)
        
        if tenant_id:
            if tenant_id not in self.tenant_policies:
                self.tenant_policies[tenant_id] = {}
            self.tenant_policies[tenant_id][statement.id] = statement
            logger.info(f"[POLICY_AS_CODE] Loaded tenant policy {statement.id} for {tenant_id}")
        else:
            self.global_policies[statement.id] = statement
            logger.info(f"[POLICY_AS_CODE] Loaded global policy {statement.id}")

    def evaluate_action(self, tenant_id: str, action: str, resource: str, context: Dict[str, Any]) -> PolicyEffect:
        """Evaluates an action against global and tenant policies."""
        # 1. Check Global Denies (Highest Priority)
        for policy in self.global_policies.values():
            if policy.effect == PolicyEffect.DENY and self._matches(policy, action, resource, context):
                return PolicyEffect.DENY
        
        # 2. Check Tenant Denies
        if tenant_id in self.tenant_policies:
            for policy in self.tenant_policies[tenant_id].values():
                if policy.effect == PolicyEffect.DENY and self._matches(policy, action, resource, context):
                    return PolicyEffect.DENY
                    
        # 3. Check Global Allows
        for policy in self.global_policies.values():
            if policy.effect == PolicyEffect.ALLOW and self._matches(policy, action, resource, context):
                return PolicyEffect.ALLOW
                
        # 4. Check Tenant Allows
        if tenant_id in self.tenant_policies:
            for policy in self.tenant_policies[tenant_id].values():
                if policy.effect == PolicyEffect.ALLOW and self._matches(policy, action, resource, context):
                    return PolicyEffect.ALLOW
                    
        # Default Deny
        return PolicyEffect.DENY

    def _matches(self, policy: PolicyStatement, action: str, resource: str, context: Dict[str, Any]) -> bool:
        """Checks if a policy statement matches the current request."""
        action_match = "*" in policy.actions or action in policy.actions
        resource_match = "*" in policy.resources or resource in policy.resources
        
        # Simple condition check (mocked for foundation)
        condition_match = True
        if policy.conditions:
            for key, value in policy.conditions.items():
                if context.get(key) != value:
                    condition_match = False
                    break
                    
        return action_match and resource_match and condition_match

# Global instance
policy_engine = PolicyAsCodeService()
