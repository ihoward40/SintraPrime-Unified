"""ORM models package.

Importing this package registers every ORM model class against ``Base.metadata``.
Any model omitted here would be absent from ``Base.metadata.create_all`` and from
Alembic autogenerate.  Keep this list complete.
"""

from .audit import AuditLog
from .audit_record import AuditRecord
from .billing import Expense, Invoice, InvoiceLineItem, Payment, TimeEntry, TrustAccount
from .blackstone import BlackstoneEvaluation, EvidenceLedger
from .case import Case, CaseDeadline, CaseEvent, CaseNote, CaseTask
from .client import Client, Matter
from .deadline_evidence import (
    MatterDeadline,
    MatterDeadlineVersion,
    MatterEvidenceFinding,
    MatterEvidenceLink,
    MatterEvidenceNode,
)
from .document import Document, DocumentFolder, DocumentShare, DocumentVersion
from .evidence_snapshot import EvidenceSnapshot
from .legal_authority import JurisdictionRuleRecord, LegalAuthorityRecord, ProfessionalReviewRecord
from .matter_intelligence import (
    MatterAccount,
    MatterAssessment,
    MatterAssessmentVersion,
    MatterAttachment,
    MatterAuditEvent,
    MatterCommunication,
    MatterDispute,
    MatterFiling,
    MatterParty,
)
from .message import Message, MessageAttachment, MessageThread
from .mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from .mission_control_outbox import MissionControlOutbox
from .mission_control_run_control import (
    MissionControlRunControl,
    MissionControlRunControlEvent,
    RunControlState,
)
from .user import Permission as UserPermission
from .user import Role as UserRole
from .user import RolePermission, Tenant, User, UserPermissionAssoc
from .voice_command import VoiceCommand, VoiceCommandEvent, VoiceCommandReceipt

__all__ = [
    "AuditLog",
    "AuditRecord",
    "BlackstoneEvaluation",
    "Case",
    "CaseDeadline",
    "CaseEvent",
    "CaseNote",
    "CaseTask",
    "Client",
    "Document",
    "DocumentFolder",
    "DocumentShare",
    "DocumentVersion",
    "EvidenceLedger",
    "EvidenceSnapshot",
    "Expense",
    "Invoice",
    "InvoiceLineItem",
    "JurisdictionRuleRecord",
    "LegalAuthorityRecord",
    "Matter",
    "MatterAccount",
    "MatterAssessment",
    "MatterAssessmentVersion",
    "MatterAttachment",
    "MatterAuditEvent",
    "MatterCommunication",
    "MatterDeadline",
    "MatterDeadlineVersion",
    "MatterDispute",
    "MatterEvidenceFinding",
    "MatterEvidenceLink",
    "MatterEvidenceNode",
    "MatterFiling",
    "MatterParty",
    "Message",
    "MessageAttachment",
    "MessageThread",
    "MissionControlCommand",
    "MissionControlCommandEvent",
    "MissionControlCommandReceipt",
    "MissionControlOutbox",
    "MissionControlRunControl",
    "MissionControlRunControlEvent",
    "Payment",
    "ProfessionalReviewRecord",
    "RolePermission",
    "RunControlState",
    "Tenant",
    "TimeEntry",
    "TrustAccount",
    "User",
    "UserPermission",
    "UserPermissionAssoc",
    "UserRole",
    "VoiceCommand",
    "VoiceCommandEvent",
    "VoiceCommandReceipt",
]
