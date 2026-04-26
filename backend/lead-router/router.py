"""
Lead Router - Main orchestration logic.
Receives intake data, routes to best agent, and triggers workflows.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Tuple

from models.lead import Lead, IntakeData, AgentType, LeadStatus
from utils.matching import (
    route_lead,
    calculate_qualification_score,
    get_agent_display_name,
)
from services import (
    get_airtable_service,
    get_email_service,
    get_agent_service,
)

logger = logging.getLogger(__name__)


class LeadRouter:
    """Main lead routing orchestrator."""
    
    def __init__(self):
        """Initialize router with service dependencies."""
        self.airtable = get_airtable_service()
        self.email = get_email_service()
        self.agent = get_agent_service()
    
    def process_intake(self, intake_data: IntakeData) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a lead submission intake form.
        
        Steps:
        1. Validate input
        2. Run routing algorithm
        3. Calculate qualification score
        4. Write to Airtable
        5. Send confirmation email
        6. Dispatch to agent
        7. Return response with confirmation details
        
        Args:
            intake_data: Intake form data from submission
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        try:
            logger.info(f"Processing intake for {intake_data.name} ({intake_data.email})")
            
            # Step 1: Validate input (Pydantic does this on __init__)
            # If we get here, input is valid
            
            # Step 2: Run routing algorithm
            routing_result = route_lead(intake_data)
            logger.info(
                f"Routing result: {routing_result.assigned_agent.value}, "
                f"confidence: {routing_result.confidence}"
            )
            
            # Step 3: Calculate qualification score
            qualification_score = calculate_qualification_score(
                legal_score=routing_result.legal_score,
                financial_score=routing_result.financial_score,
                urgency_score=routing_result.urgency_score,
            )
            
            # Create lead record
            lead_id = str(uuid.uuid4())
            lead = Lead(
                lead_id=lead_id,
                name=intake_data.name,
                email=intake_data.email,
                phone=intake_data.phone,
                legal_situation=intake_data.legal_situation,
                financial_snapshot=intake_data.financial_snapshot,
                goals=intake_data.goals,
                company_name=intake_data.company_name,
                industry=intake_data.industry,
                referral_source=intake_data.referral_source or "organic",
                assigned_agent=routing_result.assigned_agent,
                legal_score=routing_result.legal_score,
                financial_score=routing_result.financial_score,
                urgency_score=routing_result.urgency_score,
                qualification_score=qualification_score,
                status=LeadStatus.NEW,
                submitted_at=datetime.utcnow(),
            )
            
            # Step 4: Write to Airtable
            logger.info(f"Writing lead {lead_id} to Airtable")
            airtable_result = self.airtable.write_lead(lead)
            
            if airtable_result.get("success"):
                lead.airtable_id = airtable_result.get("airtable_id")
                logger.info(f"Lead written to Airtable with ID {lead.airtable_id}")
            else:
                logger.warning(f"Failed to write lead to Airtable: {airtable_result.get('error')}")
            
            # Step 5: Send confirmation email
            agent_display_name = get_agent_display_name(routing_result.assigned_agent)
            logger.info(f"Sending confirmation email to {intake_data.email}")
            
            email_result = self.email.send_confirmation_email(
                lead=lead,
                agent_name=agent_display_name,
            )
            
            email_sent = email_result.get("success", False)
            if email_sent:
                logger.info(f"Confirmation email sent with ID {email_result.get('email_id')}")
            else:
                logger.warning(f"Failed to send confirmation email: {email_result.get('error')}")
            
            # Step 6: Dispatch to agent
            logger.info(f"Dispatching lead to {agent_display_name}")
            dispatch_result = self.agent.dispatch_lead(lead)
            
            if dispatch_result.get("success"):
                logger.info(f"Lead dispatched to agent {dispatch_result.get('agent_name')}")
            else:
                logger.warning(f"Failed to dispatch lead: {dispatch_result.get('error')}")
            
            # Step 7: Return confirmation response
            response = {
                "status": "success",
                "lead_id": lead_id,
                "assigned_agent": agent_display_name,
                "confidence": routing_result.confidence,
                "next_step": "Expect a call within 24 hours. "
                             "You can also schedule a demo directly.",
                "callback_url": "https://calendly.com/sintraprime/demo",
                "email_sent": email_sent,
                "airtable_written": airtable_result.get("success", False),
                "message": f"Welcome {intake_data.name}! Your intake has been received "
                          f"and routed to {agent_display_name}.",
            }
            
            logger.info(f"Lead {lead_id} processed successfully")
            return True, response
        
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return False, {
                "status": "error",
                "error": f"Validation error: {str(e)}",
                "message": "Your submission is missing required information.",
            }
        
        except Exception as e:
            logger.error(f"Unexpected error processing intake: {str(e)}")
            return False, {
                "status": "error",
                "error": str(e),
                "message": "An unexpected error occurred. Please try again later.",
            }
    
    def get_lead_status(self, lead_id: str) -> Dict[str, Any]:
        """
        Get status of a lead.
        
        Args:
            lead_id: Lead UUID
            
        Returns:
            Lead status information
        """
        try:
            lead_record = self.airtable.get_lead_by_id(lead_id)
            
            if not lead_record:
                return {
                    "success": False,
                    "error": "Lead not found",
                }
            
            fields = lead_record.get("fields", {})
            return {
                "success": True,
                "lead_id": lead_id,
                "name": fields.get("Name"),
                "status": fields.get("Status"),
                "assigned_agent": fields.get("AssignedAgent"),
                "contacted_at": fields.get("ContactedAt"),
                "demo_scheduled_at": fields.get("DemoScheduledAt"),
                "qualification_score": fields.get("QualificationScore"),
            }
        
        except Exception as e:
            logger.error(f"Error retrieving lead status: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }


# Singleton instance
_router: LeadRouter = None


def get_router() -> LeadRouter:
    """Get or create lead router singleton."""
    global _router
    if _router is None:
        _router = LeadRouter()
    return _router
