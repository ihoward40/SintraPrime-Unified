"""
eSignature FastAPI Router

Provides REST API endpoints for document signing, status tracking,
template management, and vault operations.

Line count: 280+ lines
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Header, Body, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import json
import tempfile
from pathlib import Path

from .docusign_client import (
    DocuSignClient, Document, Recipient, RecipientRole, 
    EnvelopeConfig, NotificationSettings, SignatureTab, SignatureTabType
)
from .legal_signer import (
    LegalDocumentSigner, DocumentType, SigningParty, Jurisdiction, NotaryInfo
)
from .signature_vault import SignatureVault, DocumentAccessLevel, RetentionPolicy


# ===== Pydantic Models =====

class SendEnvelopeRequest(BaseModel):
    """Request to send envelope for signature."""
    subject: str = "Please Sign This Document"
    message: str = "Please review and sign."
    documents: List[Dict] = Field(..., description="List of document paths")
    recipients: List[Dict] = Field(..., description="List of recipient info")
    signature_tabs: Optional[List[Dict]] = None
    reminder_enabled: bool = False
    expiration_days: int = 30


class EnvelopeStatusResponse(BaseModel):
    """Response with envelope status."""
    envelope_id: str
    status: str
    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    recipients: List[Dict] = []


class TemplateCreateRequest(BaseModel):
    """Request to create a template."""
    name: str
    description: str
    subject: str = "Please Sign This Document"
    documents: List[Dict]
    signature_tabs: List[Dict]


class TemplateUseRequest(BaseModel):
    """Request to use a template."""
    template_id: str
    recipients: List[Dict]
    subject: str = "Please Sign This Document"
    message: str = "Please review and sign."


class VoidEnvelopeRequest(BaseModel):
    """Request to void an envelope."""
    reason: str = "Voided by client"


class WebhookEvent(BaseModel):
    """DocuSign webhook event."""
    event: str
    envelopeId: str
    timestamp: str
    status: str
    recipients: Optional[Dict] = None


class StoreSignedDocRequest(BaseModel):
    """Request to store signed document."""
    envelope_id: str
    matter_id: str
    client_id: str
    document_name: str
    document_type: str
    signed_by: List[str]
    access_level: str = "confidential"
    retention_days: int = 2555


class OICAnalysisRequest(BaseModel):
    """Request for OIC eligibility analysis."""
    gross_income: float
    total_taxes_owed: float
    assets: float
    monthly_expenses: float
    dependents: int


# ===== Router Setup =====

def create_esignature_router(
    docusign_client: DocuSignClient,
    signature_vault: SignatureVault
) -> APIRouter:
    """Create eSignature API router."""
    
    router = APIRouter(prefix="/esign", tags=["eSignature"])
    legal_signer = LegalDocumentSigner()
    
    # ===== Document Signing Endpoints =====
    
    @router.post("/send")
    async def send_for_signature(
        request: SendEnvelopeRequest,
        background_tasks: BackgroundTasks
    ) -> Dict:
        """
        Create and send document for signature.
        
        POST /esign/send
        {
            "subject": "Please Sign This Contract",
            "documents": [{"path": "/path/to/doc.pdf", "name": "Contract"}],
            "recipients": [{"email": "john@example.com", "name": "John Doe"}]
        }
        """
        try:
            # Create documents from uploaded files
            documents = []
            for i, doc_info in enumerate(request.documents):
                doc = Document(
                    file_path=doc_info.get("path"),
                    document_id=str(i + 1),
                    name=doc_info.get("name", f"Document {i+1}")
                )
                documents.append(doc)
            
            # Create recipients
            recipients = []
            for i, rec_info in enumerate(request.recipients):
                recipient = Recipient(
                    recipient_id=str(i + 1),
                    email=rec_info.get("email"),
                    name=rec_info.get("name"),
                    role=RecipientRole(rec_info.get("role", "signer")),
                    routing_order=rec_info.get("routing_order", i + 1)
                )
                recipients.append(recipient)
            
            # Create signature tabs
            signature_tabs = []
            if request.signature_tabs:
                for tab_info in request.signature_tabs:
                    tab = SignatureTab(
                        tab_label=tab_info.get("label"),
                        tab_type=SignatureTabType(tab_info.get("type", "signature")),
                        page_number=tab_info.get("page", 1),
                        x_position=tab_info.get("x", 100),
                        y_position=tab_info.get("y", 200)
                    )
                    signature_tabs.append(tab)
            
            # Create notification settings
            notifications = NotificationSettings(
                reminder_enabled=request.reminder_enabled,
                expiration_days=request.expiration_days
            )
            
            # Build envelope config
            config = EnvelopeConfig(
                subject=request.subject,
                message=request.message,
                documents=documents,
                recipients=recipients,
                signature_tabs=signature_tabs,
                notification_settings=notifications
            )
            
            # Create envelope
            envelope_id = docusign_client.create_envelope(config)
            
            return {
                "success": True,
                "envelope_id": envelope_id,
                "status": "sent",
                "recipients_count": len(recipients)
            }
        
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.get("/status/{envelope_id}")
    async def get_envelope_status(envelope_id: str) -> EnvelopeStatusResponse:
        """
        Get current status of envelope.
        
        GET /esign/status/envelope123
        """
        try:
            status_data = docusign_client.get_envelope_status(envelope_id)
            recipients = docusign_client.get_recipient_status(envelope_id)
            
            return EnvelopeStatusResponse(
                envelope_id=envelope_id,
                status=status_data.get("status"),
                created_at=status_data.get("createdDateTime"),
                sent_at=status_data.get("sentDateTime"),
                completed_at=status_data.get("completedDateTime"),
                recipients=recipients
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Envelope not found: {e}")
    
    @router.get("/download/{envelope_id}")
    async def download_signed_document(
        envelope_id: str,
        document_id: str = "combined"
    ) -> Dict:
        """
        Download signed document.
        
        GET /esign/download/envelope123?document_id=1
        """
        try:
            document_bytes = docusign_client.download_signed_document(
                envelope_id,
                document_id
            )
            
            return {
                "envelope_id": envelope_id,
                "document_id": document_id,
                "size_bytes": len(document_bytes),
                "download_url": f"/esign/download/{envelope_id}/file"
            }
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    @router.post("/void/{envelope_id}")
    async def void_envelope(
        envelope_id: str,
        request: VoidEnvelopeRequest
    ) -> Dict:
        """
        Void/cancel an envelope.
        
        POST /esign/void/envelope123
        {"reason": "Cancelled by client"}
        """
        try:
            docusign_client.void_envelope(envelope_id, request.reason)
            return {
                "success": True,
                "envelope_id": envelope_id,
                "status": "voided",
                "reason": request.reason
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # ===== Template Endpoints =====
    
    @router.post("/templates")
    async def create_template(request: TemplateCreateRequest) -> Dict:
        """
        Create a reusable template.
        
        POST /esign/templates
        {
            "name": "Standard Contract Template",
            "description": "For all vendor contracts",
            "documents": [...],
            "signature_tabs": [...]
        }
        """
        try:
            # Create documents
            documents = []
            for i, doc_info in enumerate(request.documents):
                doc = Document(
                    file_path=doc_info.get("path"),
                    document_id=str(i + 1),
                    name=doc_info.get("name")
                )
                documents.append(doc)
            
            # Create signature tabs
            signature_tabs = []
            for tab_info in request.signature_tabs:
                tab = SignatureTab(
                    tab_label=tab_info.get("label"),
                    tab_type=SignatureTabType(tab_info.get("type")),
                    page_number=tab_info.get("page", 1),
                    x_position=tab_info.get("x", 100),
                    y_position=tab_info.get("y", 200)
                )
                signature_tabs.append(tab)
            
            # Create config
            config = EnvelopeConfig(
                subject=request.subject,
                documents=documents,
                signature_tabs=signature_tabs
            )
            
            # Create template
            template_id = docusign_client.create_template(
                request.name,
                request.description,
                config
            )
            
            return {
                "success": True,
                "template_id": template_id,
                "name": request.name
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/templates/{template_id}/send")
    async def send_from_template(
        template_id: str,
        request: TemplateUseRequest
    ) -> Dict:
        """
        Send envelope using a template.
        
        POST /esign/templates/template123/send
        {
            "recipients": [{"email": "john@example.com", "name": "John"}]
        }
        """
        try:
            # Create recipients
            recipients = []
            for i, rec_info in enumerate(request.recipients):
                recipient = Recipient(
                    recipient_id=str(i + 1),
                    email=rec_info.get("email"),
                    name=rec_info.get("name"),
                    routing_order=rec_info.get("routing_order", i + 1)
                )
                recipients.append(recipient)
            
            # Send from template
            envelope_id = docusign_client.send_from_template(
                template_id,
                recipients,
                request.subject,
                request.message
            )
            
            return {
                "success": True,
                "envelope_id": envelope_id,
                "template_id": template_id,
                "status": "sent"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # ===== Vault Endpoints =====
    
    @router.post("/vault/store")
    async def store_signed_document(
        request: StoreSignedDocRequest,
        file: UploadFile = File(...)
    ) -> Dict:
        """
        Store a signed document in vault.
        
        POST /esign/vault/store
        """
        try:
            # Read file
            content = await file.read()
            
            # Determine access level
            access_level = DocumentAccessLevel(request.access_level)
            
            # Store in vault
            signed_doc = signature_vault.store_signed(
                envelope_id=request.envelope_id,
                matter_id=request.matter_id,
                client_id=request.client_id,
                document_name=request.document_name,
                document_type=request.document_type,
                file_content=content,
                signed_by=request.signed_by,
                access_level=access_level,
                retention_policy=RetentionPolicy.STANDARD
            )
            
            return {
                "success": True,
                "document_id": signed_doc.document_id,
                "envelope_id": signed_doc.envelope_id,
                "stored_at": signed_doc.stored_date.isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.get("/vault/{matter_id}")
    async def retrieve_vault_documents(matter_id: str) -> Dict:
        """
        Retrieve signed documents from vault by matter ID.
        
        GET /esign/vault/matter123
        """
        try:
            documents = signature_vault.retrieve_signed(matter_id=matter_id)
            
            return {
                "matter_id": matter_id,
                "document_count": len(documents),
                "documents": [d.to_dict() for d in documents]
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.get("/vault/{document_id}/audit")
    async def get_document_audit_trail(document_id: str) -> Dict:
        """
        Get audit trail for a document.
        
        GET /esign/vault/doc123/audit
        """
        try:
            audit_trail = signature_vault.get_audit_trail(document_id)
            if not audit_trail:
                raise HTTPException(status_code=404, detail="Document not found")
            
            is_valid, msg = audit_trail.verify_integrity()
            
            return {
                "document_id": document_id,
                "integrity_verified": is_valid,
                "entries": [e.to_dict() for e in audit_trail.entries],
                "verification_message": msg
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/vault/{document_id}/audit")
    async def add_audit_entry(
        document_id: str,
        action: str,
        user_id: str
    ) -> Dict:
        """
        Add entry to document's audit trail.
        
        POST /esign/vault/doc123/audit?action=viewed&user_id=user1
        """
        try:
            success = signature_vault.add_audit_entry(
                document_id,
                action,
                user_id
            )
            
            if not success:
                raise HTTPException(status_code=404, detail="Document not found")
            
            return {
                "success": True,
                "document_id": document_id,
                "action": action,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.get("/vault/{document_id}/verify")
    async def verify_document_integrity(document_id: str) -> Dict:
        """
        Verify document integrity.
        
        GET /esign/vault/doc123/verify
        """
        try:
            is_valid, message = signature_vault.verify_document_integrity(document_id)
            
            return {
                "document_id": document_id,
                "integrity_verified": is_valid,
                "message": message
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # ===== Webhook Endpoint =====
    
    @router.post("/webhook")
    async def handle_webhook(
        event: WebhookEvent,
        x_docusign_signature: Optional[str] = Header(None)
    ) -> Dict:
        """
        Handle DocuSign event webhooks.
        
        POST /esign/webhook
        """
        try:
            # Process event
            processed = docusign_client.process_webhook_event(event.dict())
            
            # Add audit entry for completion
            if event.status == "completed":
                envelope_id = event.envelopeId
                doc_id = signature_vault.envelope_index.get(envelope_id)
                
                if doc_id:
                    signature_vault.add_audit_entry(
                        doc_id,
                        "signing_completed",
                        "docusign_webhook",
                        details={"event": event.event}
                    )
            
            return {
                "success": True,
                "envelope_id": event.envelopeId,
                "event": event.event,
                "status": event.status
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    return router
