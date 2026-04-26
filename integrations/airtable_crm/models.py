"""
Data models for the Airtable CRM integration.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum


class ContactStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PROSPECT = "Prospect"
    LEAD = "Lead"
    CLIENT = "Client"
    FORMER_CLIENT = "Former Client"


class CaseStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    PENDING_REVIEW = "Pending Review"
    CLOSED = "Closed"
    WON = "Won"
    LOST = "Lost"


class CasePriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class ActivityType(str, Enum):
    CALL = "Call"
    EMAIL = "Email"
    MEETING = "Meeting"
    NOTE = "Note"
    TASK = "Task"
    DOCUMENT = "Document"
    COURT_FILING = "Court Filing"
    DISPUTE_LETTER = "Dispute Letter"


class PipelineStage(str, Enum):
    LEAD = "Lead"
    QUALIFIED = "Qualified"
    PROPOSAL = "Proposal"
    NEGOTIATION = "Negotiation"
    CLOSED_WON = "Closed Won"
    CLOSED_LOST = "Closed Lost"


@dataclass
class Contact:
    """Represents a CRM contact (client or prospect)."""
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    status: str = ContactStatus.PROSPECT.value
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    airtable_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_airtable_fields(self) -> Dict[str, Any]:
        """Convert to Airtable API field format."""
        fields = {
            "Name": self.name,
            "Email": self.email,
            "Status": self.status,
        }
        if self.phone:
            fields["Phone"] = self.phone
        if self.address:
            fields["Address"] = self.address
        if self.notes:
            fields["Notes"] = self.notes
        if self.tags:
            fields["Tags"] = self.tags
        fields.update(self.custom_fields)
        return fields

    @classmethod
    def from_airtable_record(cls, record: Dict[str, Any]) -> "Contact":
        """Create Contact from Airtable API record."""
        fields = record.get("fields", {})
        return cls(
            airtable_id=record.get("id"),
            name=fields.get("Name", ""),
            email=fields.get("Email", ""),
            phone=fields.get("Phone"),
            address=fields.get("Address"),
            status=fields.get("Status", ContactStatus.PROSPECT.value),
            tags=fields.get("Tags", []),
            notes=fields.get("Notes"),
        )


@dataclass
class Case:
    """Represents a legal case or matter."""
    title: str
    contact_id: str
    case_type: str
    status: str = CaseStatus.OPEN.value
    priority: str = CasePriority.MEDIUM.value
    description: Optional[str] = None
    court_name: Optional[str] = None
    case_number: Optional[str] = None
    filing_date: Optional[str] = None
    hearing_date: Optional[str] = None
    assigned_attorney: Optional[str] = None
    estimated_value: Optional[float] = None
    airtable_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_airtable_fields(self) -> Dict[str, Any]:
        """Convert to Airtable API field format."""
        fields = {
            "Title": self.title,
            "Contact": [self.contact_id],
            "Case Type": self.case_type,
            "Status": self.status,
            "Priority": self.priority,
        }
        if self.description:
            fields["Description"] = self.description
        if self.court_name:
            fields["Court Name"] = self.court_name
        if self.case_number:
            fields["Case Number"] = self.case_number
        if self.filing_date:
            fields["Filing Date"] = self.filing_date
        if self.hearing_date:
            fields["Hearing Date"] = self.hearing_date
        if self.assigned_attorney:
            fields["Assigned Attorney"] = self.assigned_attorney
        if self.estimated_value is not None:
            fields["Estimated Value"] = self.estimated_value
        fields.update(self.custom_fields)
        return fields

    @classmethod
    def from_airtable_record(cls, record: Dict[str, Any]) -> "Case":
        """Create Case from Airtable API record."""
        fields = record.get("fields", {})
        contact_ids = fields.get("Contact", [])
        return cls(
            airtable_id=record.get("id"),
            title=fields.get("Title", ""),
            contact_id=contact_ids[0] if contact_ids else "",
            case_type=fields.get("Case Type", ""),
            status=fields.get("Status", CaseStatus.OPEN.value),
            priority=fields.get("Priority", CasePriority.MEDIUM.value),
            description=fields.get("Description"),
            court_name=fields.get("Court Name"),
            case_number=fields.get("Case Number"),
            filing_date=fields.get("Filing Date"),
            hearing_date=fields.get("Hearing Date"),
            assigned_attorney=fields.get("Assigned Attorney"),
            estimated_value=fields.get("Estimated Value"),
        )


@dataclass
class Activity:
    """Represents an activity log entry."""
    contact_id: str
    activity_type: str
    subject: str
    description: Optional[str] = None
    case_id: Optional[str] = None
    duration_minutes: Optional[int] = None
    outcome: Optional[str] = None
    follow_up_date: Optional[str] = None
    airtable_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_airtable_fields(self) -> Dict[str, Any]:
        """Convert to Airtable API field format."""
        fields = {
            "Contact": [self.contact_id],
            "Activity Type": self.activity_type,
            "Subject": self.subject,
            "Date": self.created_at[:10],
        }
        if self.description:
            fields["Description"] = self.description
        if self.case_id:
            fields["Case"] = [self.case_id]
        if self.duration_minutes is not None:
            fields["Duration (min)"] = self.duration_minutes
        if self.outcome:
            fields["Outcome"] = self.outcome
        if self.follow_up_date:
            fields["Follow-up Date"] = self.follow_up_date
        fields.update(self.custom_fields)
        return fields

    @classmethod
    def from_airtable_record(cls, record: Dict[str, Any]) -> "Activity":
        """Create Activity from Airtable API record."""
        fields = record.get("fields", {})
        contact_ids = fields.get("Contact", [])
        case_ids = fields.get("Case", [])
        return cls(
            airtable_id=record.get("id"),
            contact_id=contact_ids[0] if contact_ids else "",
            activity_type=fields.get("Activity Type", ""),
            subject=fields.get("Subject", ""),
            description=fields.get("Description"),
            case_id=case_ids[0] if case_ids else None,
            duration_minutes=fields.get("Duration (min)"),
            outcome=fields.get("Outcome"),
            follow_up_date=fields.get("Follow-up Date"),
        )


@dataclass
class Pipeline:
    """Represents a sales/case pipeline entry."""
    contact_id: str
    stage: str = PipelineStage.LEAD.value
    value: float = 0.0
    probability: int = 0
    expected_close_date: Optional[str] = None
    notes: Optional[str] = None
    case_id: Optional[str] = None
    airtable_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_airtable_fields(self) -> Dict[str, Any]:
        """Convert to Airtable API field format."""
        fields = {
            "Contact": [self.contact_id],
            "Stage": self.stage,
            "Value": self.value,
            "Probability (%)": self.probability,
        }
        if self.expected_close_date:
            fields["Expected Close Date"] = self.expected_close_date
        if self.notes:
            fields["Notes"] = self.notes
        if self.case_id:
            fields["Case"] = [self.case_id]
        return fields

    @classmethod
    def from_airtable_record(cls, record: Dict[str, Any]) -> "Pipeline":
        """Create Pipeline from Airtable API record."""
        fields = record.get("fields", {})
        contact_ids = fields.get("Contact", [])
        case_ids = fields.get("Case", [])
        return cls(
            airtable_id=record.get("id"),
            contact_id=contact_ids[0] if contact_ids else "",
            stage=fields.get("Stage", PipelineStage.LEAD.value),
            value=fields.get("Value", 0.0),
            probability=fields.get("Probability (%)", 0),
            expected_close_date=fields.get("Expected Close Date"),
            notes=fields.get("Notes"),
            case_id=case_ids[0] if case_ids else None,
        )
