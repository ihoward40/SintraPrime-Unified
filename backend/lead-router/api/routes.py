"""
FastAPI routes for lead submission and management.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from models.lead import IntakeData, LeadSubmissionResponse
from router import get_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["leads"])


@router.post("/leads", response_model=LeadSubmissionResponse)
async def submit_lead(intake_data: IntakeData) -> LeadSubmissionResponse:
    """
    Submit a new lead intake form.
    
    Endpoint: POST /api/leads
    
    This endpoint:
    1. Validates the intake form submission
    2. Runs the lead routing algorithm
    3. Writes to Airtable CRM
    4. Sends confirmation email
    5. Assigns to appropriate specialist agent
    6. Returns confirmation with scheduling link
    
    Args:
        intake_data: Lead intake form data
    
    Returns:
        LeadSubmissionResponse with lead ID, assigned agent, and next steps
    
    Raises:
        HTTPException: If validation or processing fails
    """
    try:
        logger.info(f"Received lead submission from {intake_data.email}")
        
        router_instance = get_router()
        success, result = router_instance.process_intake(intake_data)
        
        if not success:
            logger.warning(f"Lead processing failed: {result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result.get("message", "Failed to process lead submission"),
            )
        
        # Convert result to response model
        return LeadSubmissionResponse(
            status=result["status"],
            lead_id=result["lead_id"],
            assigned_agent=result["assigned_agent"],
            confidence=result["confidence"],
            next_step=result["next_step"],
            callback_url=result["callback_url"],
            email_sent=result["email_sent"],
            message=result["message"],
        )
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in lead submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )


@router.get("/leads/{lead_id}")
async def get_lead_status(lead_id: str):
    """
    Get the status of a submitted lead.
    
    Endpoint: GET /api/leads/{lead_id}
    
    Args:
        lead_id: UUID of the lead
    
    Returns:
        Lead status information including agent assignment and timeline
    
    Raises:
        HTTPException: If lead not found
    """
    try:
        router_instance = get_router()
        result = router_instance.get_lead_status(lead_id)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", "Lead not found"),
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lead status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred retrieving lead status",
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Endpoint: GET /api/health
    
    Returns:
        Service status
    """
    return {
        "status": "healthy",
        "service": "lead-router",
        "version": "1.0.0",
    }


@router.get("/agents")
async def get_agents():
    """
    Get list of available agents and their specialties.
    
    Endpoint: GET /api/agents
    
    Returns:
        Information about all available agents
    """
    try:
        from services import get_agent_service
        
        agent_service = get_agent_service()
        agents = agent_service.get_all_agents()
        
        return {
            "success": True,
            "agents": agents,
        }
    
    except Exception as e:
        logger.error(f"Error retrieving agents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving agent information",
        )
