"""
Pydantic models for lead management and intake data.
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, EmailStr, Field


class AgentType(str, Enum):
    """Available agent specialties."""
    LEGAL_SPECIALIST = "legal-specialist"
    FINANCIAL_SPECIALIST = "financial-specialist"
    COMBINED_SPECIALIST = "combined-specialist"
    GENERAL_INQUIRY = "general-inquiry"


class LeadStatus(str, Enum):
    """Lead lifecycle status."""
    NEW = "new"
    CONTACTED = "contacted"
    DEMO_SCHEDULED = "demo-scheduled"
    WON = "won"
    LOST = "lost"


class IntakeData(BaseModel):
    """
    Intake form submission from prospective client.
    Matches the form fields from Phase 10.1.
    """
    name: str = Field(..., min_length=1, description="Full name of prospect")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., pattern=r"^\+?[\d\s\-\(\)]{10,}$", description="Phone number")
    
    # Legal situation assessment
    legal_situation: str = Field(..., min_length=10, description="Description of legal concerns")
    legal_keywords: Optional[list[str]] = Field(
        default=None,
        description="Detected legal keywords: trust, estate, business, liability, contract, etc."
    )
    
    # Financial assessment
    financial_snapshot: str = Field(..., min_length=10, description="Description of financial situation")
    financial_keywords: Optional[list[str]] = Field(
        default=None,
        description="Detected financial keywords: debt, credit, assets, tax, liability, etc."
    )
    
    # Goals and timeline
    goals: str = Field(..., min_length=10, description="What the prospect wants to achieve")
    timeline: Optional[str] = Field(
        default=None,
        description="Urgency/timeline: immediate, within-6-months, long-term, etc."
    )
    
    # Optional context
    company_name: Optional[str] = Field(default=None, description="Business name if applicable")
    industry: Optional[str] = Field(default=None, description="Industry/sector")
    referral_source: Optional[str] = Field(
        default="organic",
        description="How they heard about us: organic, referral, ad, event, etc."
    )


class RoutingResult(BaseModel):
    """Result of lead routing algorithm."""
    assigned_agent: AgentType
    legal_score: float = Field(..., ge=0, le=100)
    financial_score: float = Field(..., ge=0, le=100)
    urgency_score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=100, description="Overall match confidence")
    reasoning: str = Field(..., description="Why this agent was selected")


class Lead(BaseModel):
    """Complete lead record for CRM storage."""
    lead_id: str = Field(..., description="UUID for lead tracking")
    name: str
    email: str
    phone: str
    legal_situation: str
    financial_snapshot: str
    goals: str
    company_name: Optional[str] = None
    industry: Optional[str] = None
    referral_source: str = "organic"
    
    # Routing results
    assigned_agent: AgentType
    legal_score: float
    financial_score: float
    urgency_score: float
    qualification_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Overall lead quality score"
    )
    
    # CRM tracking
    status: LeadStatus = LeadStatus.NEW
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    contacted_at: Optional[datetime] = None
    demo_scheduled_at: Optional[datetime] = None
    
    # Airtable ID
    airtable_id: Optional[str] = None
    
    class Config:
        use_enum_values = False


class LeadSubmissionResponse(BaseModel):
    """API response to lead submission."""
    status: str = Field(..., description="success or error")
    lead_id: str = Field(..., description="UUID for this lead")
    assigned_agent: str = Field(..., description="Agent name assigned to lead")
    confidence: float = Field(..., ge=0, le=100, description="Match confidence score")
    next_step: str = Field(..., description="What happens next")
    callback_url: str = Field(..., description="Calendly or scheduling link")
    email_sent: bool = Field(..., description="Whether confirmation email was sent")
    message: Optional[str] = None
