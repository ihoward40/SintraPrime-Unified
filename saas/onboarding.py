"""
Onboarding Engine for SintraPrime-Unified SaaS

Manages 6-step tenant onboarding workflow with progress tracking,
email automation, and sample data generation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
import uuid
import json

logger = logging.getLogger(__name__)


class OnboardingStep(int, Enum):
    """Onboarding workflow steps."""
    FIRM_PROFILE = 1
    TEAM_MEMBERS = 2
    BRAND_CONFIG = 3
    INTEGRATIONS = 4
    IMPORT_CLIENTS = 5
    TRAINING = 6


class OnboardingStepStatus(str, Enum):
    """Status of an onboarding step."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class StepData:
    """Data for a completed onboarding step."""
    step: OnboardingStep
    status: OnboardingStepStatus
    data: Dict[str, Any] = field(default_factory=dict)
    completed_at: Optional[datetime] = None


@dataclass
class OnboardingState:
    """Complete onboarding state for a tenant."""
    tenant_id: str
    current_step: OnboardingStep
    completed_steps: List[OnboardingStep] = field(default_factory=list)
    skipped_steps: List[OnboardingStep] = field(default_factory=list)
    step_data: Dict[int, StepData] = field(default_factory=dict)
    completion_percentage: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    rewards_earned: int = 0
    emails_sent: List[str] = field(default_factory=list)


class OnboardingEngine:
    """
    Manages multi-step tenant onboarding.
    
    Features:
    - 6-step guided onboarding workflow
    - Progress tracking and persistence
    - Email automation during onboarding
    - In-app completion checklist
    - Sample data generation
    - Completion rewards
    """

    # Email templates for each step
    EMAIL_TEMPLATES = {
        OnboardingStep.FIRM_PROFILE: {
            "subject": "Welcome to SintraPrime! Let's set up your firm profile",
            "template": "step1_firm_profile",
        },
        OnboardingStep.TEAM_MEMBERS: {
            "subject": "Invite your team members to SintraPrime",
            "template": "step2_team_members",
        },
        OnboardingStep.BRAND_CONFIG: {
            "subject": "Customize SintraPrime with your firm's branding",
            "template": "step3_brand_config",
        },
        OnboardingStep.INTEGRATIONS: {
            "subject": "Connect your favorite tools to SintraPrime",
            "template": "step4_integrations",
        },
        OnboardingStep.IMPORT_CLIENTS: {
            "subject": "Import your existing clients into SintraPrime",
            "template": "step5_import_clients",
        },
        OnboardingStep.TRAINING: {
            "subject": "Complete your interactive SintraPrime training",
            "template": "step6_training",
        },
    }

    # Sample data templates for demo mode
    SAMPLE_CLIENTS = [
        {"name": "Johnson Family Trust", "type": "individual"},
        {"name": "Anderson Corporation", "type": "business"},
        {"name": "Smith Estate Planning", "type": "estate"},
    ]

    SAMPLE_MATTERS = [
        {"title": "Corporate Formation", "area": "corporate"},
        {"title": "Divorce Proceedings", "area": "family"},
        {"title": "Contract Review", "area": "contract_law"},
        {"title": "IP Registration", "area": "intellectual_property"},
    ]

    REWARDS = {
        "step_completed": 10,
        "all_steps_completed": 100,
        "team_invited": 5,
        "integration_enabled": 15,
    }

    def __init__(self, email_service=None):
        """
        Initialize onboarding engine.
        
        Args:
            email_service: Email sending service (optional)
        """
        self.email_service = email_service
        self._states: Dict[str, OnboardingState] = {}
        self._step_requirements = {
            OnboardingStep.FIRM_PROFILE: ["firm_name", "address", "practice_areas"],
            OnboardingStep.TEAM_MEMBERS: ["team_members"],
            OnboardingStep.BRAND_CONFIG: ["logo", "colors"],
            OnboardingStep.INTEGRATIONS: [],  # Optional
            OnboardingStep.IMPORT_CLIENTS: [],  # Optional
            OnboardingStep.TRAINING: [],  # Optional
        }

    def initialize_onboarding(self, tenant_id: str) -> OnboardingState:
        """Initialize onboarding for a new tenant."""
        state = OnboardingState(
            tenant_id=tenant_id,
            current_step=OnboardingStep.FIRM_PROFILE,
        )
        self._states[tenant_id] = state
        logger.info(f"Initialized onboarding for tenant {tenant_id}")
        return state

    def advance_step(
        self,
        tenant_id: str,
        step: OnboardingStep,
        data: Dict[str, Any],
        skip: bool = False
    ) -> Optional[OnboardingState]:
        """
        Advance to next onboarding step.
        
        Args:
            tenant_id: Tenant ID
            step: Current step being completed
            data: Step data/answers
            skip: Skip this step (for optional steps)
            
        Returns:
            Updated OnboardingState or None if validation fails
        """
        state = self._states.get(tenant_id)
        if not state:
            logger.error(f"Onboarding state not found for tenant {tenant_id}")
            return None

        # Validate step data
        if not skip:
            requirements = self._step_requirements.get(step, [])
            missing = [req for req in requirements if req not in data]
            if missing:
                logger.warning(
                    f"Missing required fields for step {step}: {missing}"
                )
                return None

        # Record step completion
        if skip:
            state.skipped_steps.append(step)
        else:
            state.completed_steps.append(step)

        # Store step data
        state.step_data[step] = StepData(
            step=step,
            status=OnboardingStepStatus.COMPLETED if not skip 
                   else OnboardingStepStatus.SKIPPED,
            data=data,
            completed_at=datetime.utcnow(),
        )

        # Advance to next step
        next_step = OnboardingStep((step % 6) + 1)
        state.current_step = next_step

        # Update completion percentage
        state.completion_percentage = (
            (len(state.completed_steps) / 6) * 100
        )

        # Award points for step completion
        if not skip:
            state.rewards_earned += self.REWARDS.get("step_completed", 0)

        # Check if onboarding complete
        if state.completion_percentage == 100:
            state.completed_at = datetime.utcnow()
            state.rewards_earned += self.REWARDS.get("all_steps_completed", 0)
            logger.info(f"Onboarding completed for tenant {tenant_id}")
            self._send_completion_email(tenant_id)
        else:
            # Send next step email
            self._send_step_email(tenant_id, next_step)

        logger.info(
            f"Advanced tenant {tenant_id} to step {next_step.value} "
            f"({state.completion_percentage}% complete)"
        )
        return state

    def get_onboarding_state(self, tenant_id: str) -> Optional[OnboardingState]:
        """Get current onboarding state for a tenant."""
        return self._states.get(tenant_id)

    def get_step_status(
        self,
        tenant_id: str,
        step: OnboardingStep
    ) -> OnboardingStepStatus:
        """Get status of a specific onboarding step."""
        state = self._states.get(tenant_id)
        if not state:
            return OnboardingStepStatus.NOT_STARTED

        if step in state.completed_steps:
            return OnboardingStepStatus.COMPLETED
        elif step in state.skipped_steps:
            return OnboardingStepStatus.SKIPPED
        elif step == state.current_step:
            return OnboardingStepStatus.IN_PROGRESS
        else:
            return OnboardingStepStatus.NOT_STARTED

    def get_checklist(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get checklist of onboarding steps with status."""
        state = self._states.get(tenant_id)
        if not state:
            return []

        checklist = []
        for step in OnboardingStep:
            status = self.get_step_status(tenant_id, step)
            checklist.append({
                "step": step.value,
                "name": self._get_step_name(step),
                "description": self._get_step_description(step),
                "status": status,
                "optional": step in [OnboardingStep.INTEGRATIONS, 
                                     OnboardingStep.IMPORT_CLIENTS,
                                     OnboardingStep.TRAINING],
                "estimated_time_minutes": self._get_step_duration(step),
            })

        return checklist

    def generate_sample_data(self, tenant_id: str) -> Dict[str, int]:
        """
        Generate sample data for demo/testing mode.
        
        Returns:
            Dictionary with counts of generated items
        """
        counts = {
            "clients": 0,
            "matters": 0,
            "documents": 0,
            "team_members": 0,
        }

        # Generate sample clients
        for client_template in self.SAMPLE_CLIENTS:
            client_id = str(uuid.uuid4())
            # In production, would save to database
            counts["clients"] += 1
            logger.debug(f"Generated sample client {client_id}")

        # Generate sample matters for each client
        for i in range(len(self.SAMPLE_CLIENTS)):
            for matter_template in self.SAMPLE_MATTERS[:2]:  # 2 matters per client
                matter_id = str(uuid.uuid4())
                counts["matters"] += 1
                logger.debug(f"Generated sample matter {matter_id}")

                # Generate sample documents for each matter
                for j in range(3):
                    doc_id = str(uuid.uuid4())
                    counts["documents"] += 1

        # Generate sample team members
        team_titles = ["Senior Attorney", "Associate", "Paralegal", "Client Relations"]
        for title in team_titles:
            member_id = str(uuid.uuid4())
            counts["team_members"] += 1
            logger.debug(f"Generated sample team member {member_id}")

        logger.info(
            f"Generated sample data for tenant {tenant_id}: "
            f"{counts['clients']} clients, {counts['matters']} matters, "
            f"{counts['documents']} documents"
        )
        return counts

    def get_onboarding_analytics(self, tenant_id: str) -> Dict[str, Any]:
        """Get analytics about onboarding progress."""
        state = self._states.get(tenant_id)
        if not state:
            return {}

        total_duration = datetime.utcnow() - state.started_at
        completed_duration = (
            (state.completed_at - state.started_at).total_seconds() / 3600
            if state.completed_at else None
        )

        return {
            "tenant_id": tenant_id,
            "started_at": state.started_at.isoformat(),
            "completed_at": state.completed_at.isoformat() if state.completed_at else None,
            "duration_hours": total_duration.total_seconds() / 3600,
            "completion_hours": completed_duration,
            "completion_percentage": state.completion_percentage,
            "steps_completed": len(state.completed_steps),
            "steps_skipped": len(state.skipped_steps),
            "rewards_earned": state.rewards_earned,
            "emails_sent": len(state.emails_sent),
        }

    def _send_step_email(self, tenant_id: str, step: OnboardingStep):
        """Send email for next onboarding step."""
        if not self.email_service:
            return

        template = self.EMAIL_TEMPLATES.get(step)
        if not template:
            return

        state = self._states.get(tenant_id)
        if not state:
            return

        # Get recipient from tenant
        recipient = "admin@example.com"  # Would fetch from tenant info

        try:
            self.email_service.send(
                to=recipient,
                subject=template["subject"],
                template=template["template"],
                context={
                    "tenant_id": tenant_id,
                    "step": step.value,
                    "completion_percentage": state.completion_percentage,
                }
            )
            state.emails_sent.append(f"step_{step.value}")
            logger.info(f"Sent onboarding email for step {step.value} to {recipient}")
        except Exception as e:
            logger.error(f"Failed to send onboarding email: {e}")

    def _send_completion_email(self, tenant_id: str):
        """Send completion congratulations email."""
        if not self.email_service:
            return

        state = self._states.get(tenant_id)
        if not state:
            return

        recipient = "admin@example.com"  # Would fetch from tenant info

        try:
            self.email_service.send(
                to=recipient,
                subject="Congratulations! Your SintraPrime setup is complete!",
                template="onboarding_complete",
                context={
                    "tenant_id": tenant_id,
                    "rewards_earned": state.rewards_earned,
                }
            )
            state.emails_sent.append("completion")
            logger.info(f"Sent completion email to {recipient}")
        except Exception as e:
            logger.error(f"Failed to send completion email: {e}")

    def _get_step_name(self, step: OnboardingStep) -> str:
        """Get user-friendly name for a step."""
        names = {
            OnboardingStep.FIRM_PROFILE: "Firm Profile",
            OnboardingStep.TEAM_MEMBERS: "Team Members",
            OnboardingStep.BRAND_CONFIG: "Brand Configuration",
            OnboardingStep.INTEGRATIONS: "Integrations",
            OnboardingStep.IMPORT_CLIENTS: "Import Clients",
            OnboardingStep.TRAINING: "Training Walkthrough",
        }
        return names.get(step, "Unknown")

    def _get_step_description(self, step: OnboardingStep) -> str:
        """Get description for a step."""
        descriptions = {
            OnboardingStep.FIRM_PROFILE: 
                "Tell us about your firm, practice areas, and office details",
            OnboardingStep.TEAM_MEMBERS: 
                "Invite your team members and set their roles",
            OnboardingStep.BRAND_CONFIG: 
                "Customize colors, logo, and domain",
            OnboardingStep.INTEGRATIONS: 
                "Connect DocuSign, Plaid, calendar, and other services",
            OnboardingStep.IMPORT_CLIENTS: 
                "Import your existing client database",
            OnboardingStep.TRAINING: 
                "Complete interactive feature walkthrough",
        }
        return descriptions.get(step, "Complete this step")

    def _get_step_duration(self, step: OnboardingStep) -> int:
        """Get estimated duration in minutes for a step."""
        durations = {
            OnboardingStep.FIRM_PROFILE: 10,
            OnboardingStep.TEAM_MEMBERS: 15,
            OnboardingStep.BRAND_CONFIG: 10,
            OnboardingStep.INTEGRATIONS: 20,
            OnboardingStep.IMPORT_CLIENTS: 15,
            OnboardingStep.TRAINING: 20,
        }
        return durations.get(step, 15)

    def reset_onboarding(self, tenant_id: str) -> bool:
        """Reset onboarding state (for testing)."""
        if tenant_id in self._states:
            self._states[tenant_id] = OnboardingState(tenant_id=tenant_id)
            logger.info(f"Reset onboarding for tenant {tenant_id}")
            return True
        return False

    def export_onboarding_data(self, tenant_id: str) -> Optional[str]:
        """Export onboarding state as JSON."""
        state = self._states.get(tenant_id)
        if not state:
            return None

        return json.dumps({
            "tenant_id": state.tenant_id,
            "current_step": state.current_step.value,
            "completed_steps": [s.value for s in state.completed_steps],
            "completion_percentage": state.completion_percentage,
            "started_at": state.started_at.isoformat(),
            "completed_at": state.completed_at.isoformat() if state.completed_at else None,
            "rewards_earned": state.rewards_earned,
        })
