"""Trust Compliance Tool Registry - Phase 19C

Defines all Trust Compliance tools with risk levels, approval requirements,
and agent access controls for ToolGateway governance.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class TrustComplianceRisk(Enum):
    """Risk classification for Trust Compliance tools.
    
    R0: Read-only, no external impact
    R1: Client-visible, internal processing
    R2: External delivery (email/document)
    R3: Regulatory/tax submission, requires approval
    """
    R0 = 0  # Read-only, no external impact
    R1 = 1  # Client-visible, internal processing
    R2 = 2  # External delivery (email/document)
    R3 = 3  # Regulatory/tax submission, requires approval


@dataclass
class TrustComplianceTool:
    """Metadata for a Trust Compliance tool."""
    name: str
    description: str
    risk_level: TrustComplianceRisk
    requires_approval: bool
    agent: str  # which agent can call this


# Registry of all Trust Compliance tools
TRUST_TOOLS = {
    'trust_compliance.intake': TrustComplianceTool(
        name='intake',
        description='Client intake form processing and document collection',
        risk_level=TrustComplianceRisk.R0,
        requires_approval=False,
        agent='any'
    ),
    'trust_compliance.classify': TrustComplianceTool(
        name='classify',
        description='Determine trust type and jurisdiction requirements',
        risk_level=TrustComplianceRisk.R0,
        requires_approval=False,
        agent='any'
    ),
    'trust_compliance.generate_summary': TrustComplianceTool(
        name='generate_summary',
        description='Summarize trust structure and beneficiaries',
        risk_level=TrustComplianceRisk.R1,
        requires_approval=False,
        agent='sigma'
    ),
    'trust_compliance.rewrite_clause': TrustComplianceTool(
        name='rewrite_clause',
        description='Suggest improved trust language for specific provisions',
        risk_level=TrustComplianceRisk.R1,
        requires_approval=False,
        agent='sigma'
    ),
    'trust_compliance.create_exhibit': TrustComplianceTool(
        name='create_exhibit',
        description='Generate exhibits (family trees, asset schedules)',
        risk_level=TrustComplianceRisk.R1,
        requires_approval=False,
        agent='nova'
    ),
    'trust_compliance.prepare_bank_packet': TrustComplianceTool(
        name='prepare_bank_packet',
        description='Create bank-ready trust documents and forms',
        risk_level=TrustComplianceRisk.R2,
        requires_approval=False,
        agent='nova'
    ),
    'trust_compliance.prepare_court_packet': TrustComplianceTool(
        name='prepare_court_packet',
        description='Create court-ready trust litigation documents',
        risk_level=TrustComplianceRisk.R2,
        requires_approval=False,
        agent='nova'
    ),
    'trust_compliance.send_client_email': TrustComplianceTool(
        name='send_client_email',
        description='Send trust documents and summaries to client',
        risk_level=TrustComplianceRisk.R2,
        requires_approval=False,
        agent='nova'
    ),
    'trust_compliance.external_submit': TrustComplianceTool(
        name='external_submit',
        description='Submit trust documents to external parties (court, agency)',
        risk_level=TrustComplianceRisk.R3,
        requires_approval=True,
        agent='nova'
    ),
    'trust_compliance.tax_related_output': TrustComplianceTool(
        name='tax_related_output',
        description='Generate tax-related filings or returns',
        risk_level=TrustComplianceRisk.R3,
        requires_approval=True,
        agent='nova'
    ),
}


def get_tool(name: str) -> TrustComplianceTool:
    """Retrieve a tool by name from the registry.
    
    Args:
        name: Tool name (e.g., 'trust_compliance.intake')
    
    Returns:
        TrustComplianceTool if found, None otherwise
    """
    return TRUST_TOOLS.get(name)


def get_tools_by_risk(risk: TrustComplianceRisk) -> List[TrustComplianceTool]:
    """Get all tools at a specific risk level.
    
    Args:
        risk: TrustComplianceRisk level to filter
    
    Returns:
        List of tools at the specified risk level
    """
    return [t for t in TRUST_TOOLS.values() if t.risk_level == risk]


def get_tools_by_agent(agent: str) -> List[str]:
    """Get all tool names accessible by an agent.
    
    Args:
        agent: Agent name (e.g., 'nova', 'sigma', 'any')
    
    Returns:
        List of tool names the agent can call
    """
    return [
        name for name, tool in TRUST_TOOLS.items()
        if tool.agent == 'any' or tool.agent == agent
    ]
