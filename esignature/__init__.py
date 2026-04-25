"""
DocuSign e-signature integration module for SintraPrime-Unified.

Provides comprehensive e-signature capabilities for legal documents:
- Document envelope creation and management
- Multi-party signing workflows
- Template management
- Real-time status tracking
- Signed document vault with audit trails
"""

from .docusign_client import DocuSignClient, EnvelopeConfig, EnvelopeStatus
from .legal_signer import LegalDocumentSigner, NotaryInfo
from .signature_vault import SignatureVault, SignedDocument, AuditTrail

__all__ = [
    "DocuSignClient",
    "EnvelopeConfig",
    "EnvelopeStatus",
    "LegalDocumentSigner",
    "NotaryInfo",
    "SignatureVault",
    "SignedDocument",
    "AuditTrail",
]

__version__ = "1.0.0"
