"""
Agent Dispatch Service.
Routes leads to assigned agents and creates tasks for review.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from models.lead import Lead, AgentType
from utils.matching import get_agent_display_name

logger = logging.getLogger(__name__)


class AgentService:
    """Service for dispatching leads to agents."""
    
    # Agent contact info and queue assignments
    AGENT_INFO = {
        AgentType.LEGAL_SPECIALIST: {
            "name": "Zero",
            "display_name": "Zero (Legal Specialist)",
            "email": "zero@sintraprime.ai",
            "specialty": "Legal Planning & Asset Protection",
            "phone": "+1-555-ZERO-LEG",
            "slack_user_id": "U_ZERO_LEGAL",
        },
        AgentType.FINANCIAL_SPECIALIST: {
            "name": "Sigma",
            "display_name": "Sigma (Financial Specialist)",
            "email": "sigma@sintraprime.ai",
            "specialty": "Financial Strategy & Wealth Management",
            "phone": "+1-555-SIGMA-FIN",
            "slack_user_id": "U_SIGMA_FIN",
        },
        AgentType.COMBINED_SPECIALIST: {
            "name": "Nova",
            "display_name": "Nova (Combined Specialist)",
            "email": "nova@sintraprime.ai",
            "specialty": "Integrated Legal & Financial Planning",
            "phone": "+1-555-NOVA-INT",
            "slack_user_id": "U_NOVA_COMBINED",
        },
    }
    
    def __init__(self):
        """Initialize agent service."""
        self.tasklet_enabled = os.getenv("TASKLET_API_ENABLED", "false").lower() == "true"
        self.slack_enabled = os.getenv("SLACK_ENABLED", "false").lower() == "true"
    
    def dispatch_lead(self, lead: Lead) -> Dict[str, Any]:
        """
        Dispatch lead to assigned agent.
        Creates task in Tasklet agent queue if enabled.
        
        Args:
            lead: Lead object with assigned agent
            
        Returns:
            Dispatch result
        """
        try:
            agent_type = lead.assigned_agent
            agent_info = self.AGENT_INFO.get(agent_type)
            
            if not agent_info:
                return {
                    "success": False,
                    "error": f"Unknown agent type: {agent_type}",
                }
            
            logger.info(f"Dispatching lead {lead.lead_id} to {agent_info['name']}")
            
            # Create task in Tasklet if enabled
            tasklet_result = {"created": False}
            if self.tasklet_enabled:
                tasklet_result = self._create_tasklet_task(lead, agent_info)
            
            # Send Slack notification if enabled
            slack_result = {"sent": False}
            if self.slack_enabled:
                slack_result = self._send_slack_notification(lead, agent_info)
            
            return {
                "success": True,
                "agent_name": agent_info["display_name"],
                "agent_email": agent_info["email"],
                "agent_phone": agent_info["phone"],
                "specialty": agent_info["specialty"],
                "tasklet": tasklet_result,
                "slack": slack_result,
            }
        
        except Exception as e:
            logger.error(f"Failed to dispatch lead: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _create_tasklet_task(
        self,
        lead: Lead,
        agent_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a task in Tasklet agent queue (stub implementation).
        
        Args:
            lead: Lead to create task for
            agent_info: Agent information
            
        Returns:
            Task creation result
        """
        try:
            # Stub implementation - would call Tasklet API in production
            logger.info(
                f"[STUB] Creating Tasklet task for {agent_info['name']} "
                f"to review lead {lead.lead_id}"
            )
            
            task_data = {
                "agent": agent_info["name"],
                "lead_id": lead.lead_id,
                "lead_name": lead.name,
                "lead_email": lead.email,
                "phone": lead.phone,
                "legal_score": lead.legal_score,
                "financial_score": lead.financial_score,
                "urgency_score": lead.urgency_score,
                "qualification_score": lead.qualification_score,
                "assigned_at": datetime.utcnow().isoformat(),
            }
            
            # In production, would call:
            # tasklet_client.create_task(
            #     title=f"Review Lead: {lead.name}",
            #     description=f"Lead {lead.lead_id} qualified for {agent_info['specialty']}",
            #     assigned_to=agent_info["slack_user_id"],
            #     metadata=task_data,
            # )
            
            return {
                "created": True,
                "task_id": f"task_{lead.lead_id}",
                "agent": agent_info["name"],
            }
        
        except Exception as e:
            logger.error(f"Failed to create Tasklet task: {str(e)}")
            return {
                "created": False,
                "error": str(e),
            }
    
    def _send_slack_notification(
        self,
        lead: Lead,
        agent_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send Slack notification to agent (stub implementation).
        
        Args:
            lead: Lead to notify about
            agent_info: Agent information
            
        Returns:
            Notification result
        """
        try:
            # Stub implementation - would use Slack API in production
            logger.info(
                f"[STUB] Sending Slack notification to {agent_info['name']} "
                f"about lead {lead.lead_id}"
            )
            
            message = f"""
New Lead Assignment: {lead.name}
Lead ID: {lead.lead_id}
Email: {lead.email}
Phone: {lead.phone}

Legal Score: {lead.legal_score}/100
Financial Score: {lead.financial_score}/100
Urgency: {lead.urgency_score}/100
Qualification: {lead.qualification_score}/100

Legal Situation: {lead.legal_situation[:100]}...
Financial Snapshot: {lead.financial_snapshot[:100]}...
Goals: {lead.goals[:100]}...

Action: Review this lead and reach out within 24 hours.
            """
            
            # In production, would call:
            # slack_client.chat_postMessage(
            #     channel=f"@{agent_info['slack_user_id']}",
            #     text=message,
            # )
            
            return {
                "sent": True,
                "agent": agent_info["name"],
                "message_preview": message[:100],
            }
        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return {
                "sent": False,
                "error": str(e),
            }
    
    def get_agent_info(self, agent_type: AgentType) -> Optional[Dict[str, Any]]:
        """Get agent information by type."""
        return self.AGENT_INFO.get(agent_type)
    
    def get_all_agents(self) -> Dict[str, Any]:
        """Get information for all agents."""
        return {
            agent_type.value: info
            for agent_type, info in self.AGENT_INFO.items()
        }


# Singleton instance
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """Get or create agent service singleton."""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
