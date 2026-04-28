"""Trust Compliance Policy Mapping - Phase 19C

Converts Trust Compliance tool registry to IkeOS ToolGateway policy format
for integrated governance and access control.
"""

from tool_registry import TrustComplianceRisk, TRUST_TOOLS


class TrustCompliancePolicyMapper:
    """Maps Trust Compliance tools to IkeOS ToolGateway policy.
    
    Provides:
    - Risk-level policy definitions
    - Agent access controls
    - Rate limiting rules
    - Approval workflow configuration
    """
    
    @staticmethod
    def get_policy() -> dict:
        """Return policy dict for ToolGateway integration.
        
        Returns:
            Dictionary with:
            - domain: 'trust_compliance'
            - tools: Tool definitions with risk levels and access control
            - approval_queue: Approval workflow configuration
        """
        policy = {
            'domain': 'trust_compliance',
            'tools': {},
            'approval_queue': {
                'enabled': True,
                'timeout_seconds': 3600,  # 1 hour to approve
                'roles': ['admin', 'senior_attorney']
            }
        }
        
        # Build tool policies
        for name, tool in TRUST_TOOLS.items():
            # Determine allowed agents based on risk level
            if tool.requires_approval:
                # R3 tools only for senior agents
                allowed_agents = ['sigma', 'nova']
            else:
                # R0-R1-R2 tools available to all agents
                if tool.agent == 'any':
                    allowed_agents = ['zero', 'sigma', 'nova', 'chat']
                else:
                    # Specific agent requirement
                    allowed_agents = ['zero', 'sigma', 'nova', 'chat']
            
            # Determine rate limit based on risk
            if tool.risk_level == TrustComplianceRisk.R0:
                rate_limit = '10000/hour'  # Very permissive for read-only
            elif tool.risk_level == TrustComplianceRisk.R1:
                rate_limit = '1000/hour'   # Standard for internal processing
            elif tool.risk_level == TrustComplianceRisk.R2:
                rate_limit = '500/hour'    # More restricted for external delivery
            else:  # R3
                rate_limit = '100/hour'    # Very restricted for regulatory
            
            policy['tools'][name] = {
                'name': tool.name,
                'description': tool.description,
                'risk_level': f'R{tool.risk_level.value}',
                'requires_approval': tool.requires_approval,
                'allowed_agents': allowed_agents,
                'rate_limit': rate_limit,
                'timeout_seconds': 300 if tool.risk_level.value <= 2 else 600
            }
        
        return policy
    
    @staticmethod
    def map_to_tool_gateway() -> dict:
        """Convert to ToolGateway format for integration.
        
        Returns:
            Dictionary with:
            - gateway_tools: List of tools in ToolGateway format
            - approval_config: Approval configuration
        """
        policy = TrustCompliancePolicyMapper.get_policy()
        
        return {
            'gateway_tools': [
                {
                    'id': name,
                    'name': tool_policy['name'],
                    'description': tool_policy['description'],
                    'risk_level': tool_policy['risk_level'],
                    'requires_approval': tool_policy['requires_approval'],
                    'allowed_agents': tool_policy['allowed_agents'],
                    'rate_limit': tool_policy['rate_limit'],
                    'timeout_seconds': tool_policy['timeout_seconds']
                }
                for name, tool_policy in policy['tools'].items()
            ],
            'approval_config': policy['approval_queue'],
            'domain': policy['domain']
        }
    
    @staticmethod
    def get_risk_matrix() -> dict:
        """Get risk classification matrix for all tools.
        
        Returns:
            Dictionary mapping risk levels to lists of tools
        """
        matrix = {
            'R0': [],
            'R1': [],
            'R2': [],
            'R3': []
        }
        
        for name, tool in TRUST_TOOLS.items():
            risk_key = f'R{tool.risk_level.value}'
            matrix[risk_key].append({
                'name': name,
                'requires_approval': tool.requires_approval,
                'agent': tool.agent
            })
        
        return matrix
    
    @staticmethod
    def get_tools_requiring_approval() -> list:
        """Get list of all tools that require approval.
        
        Returns:
            List of tool names requiring approval
        """
        return [
            name for name, tool in TRUST_TOOLS.items()
            if tool.requires_approval
        ]
    
    @staticmethod
    def get_tools_by_agent(agent: str) -> list:
        """Get all tools accessible by a specific agent.
        
        Args:
            agent: Agent name to check
        
        Returns:
            List of tool names accessible to the agent
        """
        accessible = []
        for name, tool_policy in TrustCompliancePolicyMapper.get_policy()['tools'].items():
            if agent in tool_policy['allowed_agents']:
                accessible.append(name)
        return accessible
    
    @staticmethod
    def validate_tool_access(tool_name: str, agent: str) -> tuple:
        """Validate if an agent can access a tool.
        
        Args:
            tool_name: Tool name to check
            agent: Agent trying to access
        
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        policy = TrustCompliancePolicyMapper.get_policy()
        
        if tool_name not in policy['tools']:
            return False, f'Unknown tool: {tool_name}'
        
        tool_policy = policy['tools'][tool_name]
        
        if agent not in tool_policy['allowed_agents']:
            return False, f'Agent {agent} not allowed for tool {tool_name}'
        
        return True, 'Access granted'


class IkeOSPolicyIntegration:
    """Integration point with IkeOS ToolGateway.
    
    This would be called from core/ikeos_integration/policy_mapper.py
    """
    
    def __init__(self):
        self.trust_compliance_policy = TrustCompliancePolicyMapper.get_policy()
        self.gateway_format = TrustCompliancePolicyMapper.map_to_tool_gateway()
    
    def get_risk_level(self, tool_name: str) -> int:
        """Get numeric risk level for a tool.
        
        Args:
            tool_name: Tool name
        
        Returns:
            Risk level (0-3) or None if tool not found
        """
        if tool_name.startswith('trust_compliance.'):
            tool_policy = self.trust_compliance_policy['tools'].get(tool_name)
            if tool_policy:
                # Map R0-R3 to risk integers
                risk_map = {'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3}
                return risk_map[tool_policy['risk_level']]
        return None
    
    def requires_approval(self, tool_name: str) -> bool:
        """Check if a tool requires approval.
        
        Args:
            tool_name: Tool name
        
        Returns:
            True if approval required, False otherwise
        """
        if tool_name.startswith('trust_compliance.'):
            tool_policy = self.trust_compliance_policy['tools'].get(tool_name)
            if tool_policy:
                return tool_policy['requires_approval']
        return False
    
    def get_rate_limit(self, tool_name: str) -> str:
        """Get rate limit for a tool.
        
        Args:
            tool_name: Tool name
        
        Returns:
            Rate limit string (e.g., '100/hour')
        """
        if tool_name.startswith('trust_compliance.'):
            tool_policy = self.trust_compliance_policy['tools'].get(tool_name)
            if tool_policy:
                return tool_policy['rate_limit']
        return '100/hour'  # Default
