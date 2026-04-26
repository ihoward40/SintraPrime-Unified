"""
SintraPrime-Unified Governance Module
======================================
Human-in-the-Loop (HITL) and AI Governance for enterprise-grade AI operations.

Inspired by:
- OpenAI Operator (approval gates for sensitive actions)
- GPT-5.5 human-in-loop verification for high-stakes tasks
- Gartner: "40% of agentic AI projects cancelled by 2027 due to missing governance"
- Claude Computer Use (approval gates before destructive actions)
- Enterprise AI governance: SOC2, audit trails, intervention controls
"""

from governance.governance_engine import GovernanceEngine
from governance.approval_gate import ApprovalGate
from governance.audit_trail import AuditTrail
from governance.risk_assessor import RiskAssessor
from governance.intervention_controller import InterventionController
from governance.compliance_monitor import ComplianceMonitor

__all__ = [
    "GovernanceEngine",
    "ApprovalGate",
    "AuditTrail",
    "RiskAssessor",
    "InterventionController",
    "ComplianceMonitor",
]

__version__ = "1.0.0"
__author__ = "SintraPrime-Unified Team"
