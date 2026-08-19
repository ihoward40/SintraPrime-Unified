"""ORM models package."""

from sqlalchemy import UUID, String

from .audit import AuditLog
from .audit_record import AuditRecord
from .billing import Expense, Invoice, InvoiceLineItem, Payment, TimeEntry, TrustAccount
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
from .governed_service_identity import GovernedServiceIdentityRecord
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
from .mission_control_run_control import (
    MissionControlRunControl,
    MissionControlRunControlEvent,
    RunControlState,
)
from .orchestration import (
    ApprovalRequest,
    ApprovalStatus,
    BudgetUsage,
    EvidenceReference,
    MemoryEntry,
    OrchestrationEvent,
    OrchestrationExecutionMode,
    OrchestrationLinkage,
    OrchestrationNode,
    OrchestrationNodeStatus,
    OrchestrationRole,
    OrchestrationRun,
    OrchestrationRunStatus,
    OrchestrationSensitivity,
    OrchestrationTaskType,
    PrincipalAuthority,
    ProviderDefinition,
    ReconciliationResult,
    RoutingDecision,
    VerificationResult,
)
from .user import Permission as UserPermission
from .user import Role as UserRole
from .user import User, UserPermissionAssoc


def _align_external_identity_foreign_keys() -> None:
    """Match orchestration tenant/user FKs to the canonical VARCHAR(36) identity schema."""
    external_identity_columns = (
        OrchestrationRun.__table__.c.tenant_id,
        OrchestrationRun.__table__.c.created_by,
        ApprovalRequest.__table__.c.principal_id,
        OrchestrationLinkage.__table__.c.tenant_id,
        PrincipalAuthority.__table__.c.tenant_id,
        PrincipalAuthority.__table__.c.user_id,
        MemoryEntry.__table__.c.tenant_id,
    )
    for column in external_identity_columns:
        column.type = String(36)


def _align_orchestration_uuid_python_representation() -> None:
    """Keep PostgreSQL UUID storage while accepting canonical string UUIDs in Python.

    The orchestration API, persistence dictionaries, and Mission Control command
    contracts use string UUIDs. ``UUID(as_uuid=False)`` preserves native PostgreSQL
    UUID columns but prevents SQLAlchemy from requiring ``uuid.UUID`` objects at every
    application boundary.
    """
    orchestration_tables = (
        OrchestrationRun.__table__,
        OrchestrationNode.__table__,
        OrchestrationEvent.__table__,
        ProviderDefinition.__table__,
        RoutingDecision.__table__,
        VerificationResult.__table__,
        ReconciliationResult.__table__,
        ApprovalRequest.__table__,
        EvidenceReference.__table__,
        BudgetUsage.__table__,
        OrchestrationLinkage.__table__,
        PrincipalAuthority.__table__,
        MemoryEntry.__table__,
    )
    for table in orchestration_tables:
        for column in table.columns:
            if isinstance(column.type, UUID):
                column.type = UUID(as_uuid=False)


_align_external_identity_foreign_keys()
_align_orchestration_uuid_python_representation()

__all__ = [
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditLog",
    "AuditRecord",
    "BudgetUsage",
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
    "EvidenceReference",
    "EvidenceSnapshot",
    "Expense",
    "GovernedServiceIdentityRecord",
    "Invoice",
    "InvoiceLineItem",
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
    "MemoryEntry",
    "Message",
    "MessageAttachment",
    "MessageThread",
    "MissionControlCommand",
    "MissionControlCommandEvent",
    "MissionControlCommandReceipt",
    "MissionControlRunControl",
    "MissionControlRunControlEvent",
    "OrchestrationEvent",
    "OrchestrationExecutionMode",
    "OrchestrationLinkage",
    "OrchestrationNode",
    "OrchestrationNodeStatus",
    "OrchestrationRole",
    "OrchestrationRun",
    "OrchestrationRunStatus",
    "OrchestrationSensitivity",
    "OrchestrationTaskType",
    "Payment",
    "PrincipalAuthority",
    "ProviderDefinition",
    "ReconciliationResult",
    "RoutingDecision",
    "RunControlState",
    "TimeEntry",
    "TrustAccount",
    "User",
    "UserPermission",
    "UserPermissionAssoc",
    "UserRole",
    "VerificationResult",
]
