"""
DocuSign eSignature API Integration Client

Provides OAuth2 JWT authentication, envelope management, recipient handling,
signature tab placement, template management, and real-time status tracking.

Line count: 480+ lines
"""

import json
import base64
import hashlib
import time
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import requests
from requests.auth import HTTPBasicAuth


class RecipientRole(Enum):
    """Types of signers in a DocuSign envelope."""
    SIGNER = "signer"
    CARBON_COPY = "carbonCopy"
    WITNESS = "witness"
    NOTARY = "notary"
    EDITOR = "editor"


class SignatureTabType(Enum):
    """Types of signature tabs available."""
    SIGNATURE = "signHere"
    INITIALS = "initialHere"
    DATE = "dateTag"
    CHECKBOX = "checkbox"
    TEXT = "text"
    EMAIL = "email"
    FULL_NAME = "fullName"


class EnvelopeStatus(Enum):
    """Envelope status states."""
    DRAFT = "created"
    SENT = "sent"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    VOIDED = "voided"
    DECLINED = "declined"


class SigningCeremonyType(Enum):
    """Types of signing ceremonies."""
    EMBEDDED = "embedded"  # In-app signing
    REMOTE = "remote"      # Email-based signing
    HYBRID = "hybrid"      # Mix of both


@dataclass
class Document:
    """Represents a document to be signed."""
    file_path: str
    document_id: str
    name: str
    file_extension: str = "pdf"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API."""
        with open(self.file_path, 'rb') as f:
            document_base64 = base64.b64encode(f.read()).decode()
        
        return {
            "documentId": self.document_id,
            "name": self.name,
            "fileExtension": self.file_extension,
            "documentBase64": document_base64
        }


@dataclass
class Recipient:
    """Represents a signer or recipient in an envelope."""
    recipient_id: str
    email: str
    name: str
    role: RecipientRole = RecipientRole.SIGNER
    routing_order: int = 1
    access_code: Optional[str] = None
    embed_token_only: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API."""
        return {
            "recipientId": self.recipient_id,
            "email": self.email,
            "name": self.name,
            "recipientType": self.role.value,
            "routingOrder": self.routing_order,
            "accessCode": self.access_code,
            "embedTokenOnly": self.embed_token_only,
            "clientUserId": self.recipient_id if self.embed_token_only else None
        }


@dataclass
class SignatureTab:
    """Represents a signature tab placement on a document page."""
    tab_label: str
    tab_type: SignatureTabType
    page_number: int
    x_position: int
    y_position: int
    width: int = 100
    height: int = 50
    is_required: bool = True
    document_id: str = "1"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API."""
        return {
            "tabLabel": self.tab_label,
            self.tab_type.value: {
                "documentId": self.document_id,
                "pageNumber": self.page_number,
                "xPosition": self.x_position,
                "yPosition": self.y_position,
                "width": self.width,
                "height": self.height,
            },
            "required": self.is_required
        }


@dataclass
class NotificationSettings:
    """Envelope notification settings."""
    reminder_enabled: bool = False
    reminder_delay: int = 3
    expiration_enabled: bool = False
    expiration_days: int = 30
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API."""
        return {
            "reminders": {
                "reminderEnabled": self.reminder_enabled,
                "reminderDelay": self.reminder_delay,
                "reminderFrequency": "daily"
            },
            "expirations": {
                "expireEnabled": self.expiration_enabled,
                "expireAfter": self.expiration_days,
                "expireWarn": self.expiration_days - 3
            }
        }


@dataclass
class EnvelopeConfig:
    """Configuration for creating an envelope."""
    envelope_id: Optional[str] = None
    subject: str = "Please Sign This Document"
    message: str = "Please review and sign the attached document."
    documents: List[Document] = field(default_factory=list)
    recipients: List[Recipient] = field(default_factory=list)
    signature_tabs: List[SignatureTab] = field(default_factory=list)
    signing_ceremony: SigningCeremonyType = SigningCeremonyType.REMOTE
    notification_settings: NotificationSettings = field(default_factory=NotificationSettings)
    status: EnvelopeStatus = EnvelopeStatus.DRAFT
    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    webhook_url: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API."""
        return {
            "envelopeIdStamping": "true",
            "autoNavigation": "true",
            "envelopeFrom": "noreply@example.com",
            "brandId": "default",
            "status": self.status.value,
            "emailSubject": self.subject,
            "emailBlurb": self.message,
            "documents": [doc.to_dict() for doc in self.documents],
            "recipients": {
                "signers": [r.to_dict() for r in self.recipients 
                           if r.role == RecipientRole.SIGNER],
                "carbonCopies": [r.to_dict() for r in self.recipients 
                                if r.role == RecipientRole.CARBON_COPY],
                "witnesses": [r.to_dict() for r in self.recipients 
                             if r.role == RecipientRole.WITNESS],
                "notaries": [r.to_dict() for r in self.recipients 
                            if r.role == RecipientRole.NOTARY],
            },
            "signatureInfo": [tab.to_dict() for tab in self.signature_tabs],
            "notification": self.notification_settings.to_dict()
        }


class DocuSignClient:
    """
    DocuSign eSignature API Client with OAuth2 JWT Authentication.
    
    Handles:
    - OAuth2 JWT authentication with service account
    - Envelope creation from PDF, DOCX, HTML
    - Recipient management (signers, CC, witnesses, notaries)
    - Signature tab placement (signature, initials, date, text, etc.)
    - Template management and bulk sending
    - Embedded and remote signing ceremonies
    - Real-time status polling and webhook handling
    - Reminder and expiration configuration
    - Certificate of completion retrieval
    - Bulk send capabilities
    """
    
    API_BASE_URL = "https://demo.docusign.net/restapi/v2.1"
    OAUTH_URL = "https://account-d.docusign.com/oauth/token"
    
    def __init__(
        self,
        account_id: str,
        client_id: str,
        client_secret: str,
        private_key_pem: str,
        user_id: str,
        impersonate_user: Optional[str] = None
    ):
        """
        Initialize DocuSign client.
        
        Args:
            account_id: DocuSign account ID
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            private_key_pem: RSA private key for JWT authentication
            user_id: User ID for authentication
            impersonate_user: Optional user to impersonate (for service accounts)
        """
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.private_key_pem = private_key_pem
        self.user_id = user_id
        self.impersonate_user = impersonate_user
        self.access_token = None
        self.token_expiry = None
        self.templates_cache: Dict[str, Dict] = {}
    
    def _get_access_token(self) -> str:
        """
        Get OAuth2 access token via JWT bearer assertion.
        
        Returns:
            Access token string
        """
        if self.access_token and self.token_expiry > datetime.now():
            return self.access_token
        
        # Create JWT assertion
        import jwt
        
        now = datetime.utcnow()
        payload = {
            "iss": self.client_id,
            "sub": self.user_id,
            "aud": "account-d.docusign.com",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "scope": "signature"
        }
        
        if self.impersonate_user:
            payload["impersonated_user_guid"] = self.impersonate_user
        
        token = jwt.encode(
            payload,
            self.private_key_pem,
            algorithm="RS256"
        )
        
        # Exchange JWT for access token
        response = requests.post(
            self.OAUTH_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": token
            }
        )
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["access_token"]
        self.token_expiry = datetime.now() + timedelta(seconds=data["expires_in"] - 300)
        
        return self.access_token
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization."""
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def create_envelope(
        self,
        config: EnvelopeConfig
    ) -> str:
        """
        Create and send an envelope for signature.
        
        Args:
            config: EnvelopeConfig with documents, recipients, tabs
            
        Returns:
            Envelope ID
        """
        url = f"{self.API_BASE_URL}/accounts/{self.account_id}/envelopes"
        
        payload = config.to_dict()
        
        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        envelope_id = data["envelopeId"]
        config.envelope_id = envelope_id
        config.status = EnvelopeStatus.SENT
        config.sent_at = datetime.now()
        
        return envelope_id
    
    def get_envelope_status(self, envelope_id: str) -> Dict:
        """
        Get current status of an envelope.
        
        Returns:
            Dictionary with status, recipients, documents info
        """
        url = f"{self.API_BASE_URL}/accounts/{self.account_id}/envelopes/{envelope_id}"
        
        response = requests.get(
            url,
            headers=self._get_headers()
        )
        response.raise_for_status()
        
        return response.json()
    
    def get_recipient_status(self, envelope_id: str) -> List[Dict]:
        """
        Get status of all recipients in an envelope.
        
        Returns:
            List of recipient status dictionaries
        """
        url = f"{self.API_BASE_URL}/accounts/{self.account_id}/envelopes/{envelope_id}/recipients"
        
        response = requests.get(
            url,
            headers=self._get_headers()
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("signers", [])
    
    def void_envelope(self, envelope_id: str, reason: str = "Voided by client") -> None:
        """
        Void/cancel an envelope.
        
        Args:
            envelope_id: ID of envelope to void
            reason: Reason for voiding
        """
        url = f"{self.API_BASE_URL}/accounts/{self.account_id}/envelopes/{envelope_id}"
        
        payload = {
            "status": "voided",
            "voidedReason": reason
        }
        
        response = requests.put(
            url,
            headers=self._get_headers(),
            json=payload
        )
        response.raise_for_status()
    
    def download_signed_document(self, envelope_id: str, document_id: str = "combined") -> bytes:
        """
        Download signed document.
        
        Args:
            envelope_id: ID of completed envelope
            document_id: Document ID (default "combined" for all)
            
        Returns:
            Document bytes
        """
        url = f"{self.API_BASE_URL}/accounts/{self.account_id}/envelopes/{envelope_id}/documents/{document_id}"
        
        response = requests.get(
            url,
            headers=self._get_headers()
        )
        response.raise_for_status()
        
        return response.content
    
    def download_certificate_of_completion(self, envelope_id: str) -> bytes:
        """
        Download certificate of completion (audit trail document).
        
        Returns:
            PDF certificate bytes
        """
        return self.download_signed_document(envelope_id, "certificate")
    
    def create_template(
        self,
        name: str,
        description: str,
        config: EnvelopeConfig
    ) -> str:
        """
        Create a reusable envelope template.
        
        Args:
            name: Template name
            description: Template description
            config: EnvelopeConfig for template
            
        Returns:
            Template ID
        """
        url = f"{self.API_BASE_URL}/accounts/{self.account_id}/templates"
        
        payload = config.to_dict()
        payload["name"] = name
        payload["description"] = description
        payload["shared"] = "false"
        
        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        template_id = data["templateId"]
        self.templates_cache[template_id] = data
        
        return template_id
    
    def send_from_template(
        self,
        template_id: str,
        recipients: List[Recipient],
        subject: str = "Please Sign This Document",
        message: str = "Please review and sign."
    ) -> str:
        """
        Send an envelope using a saved template.
        
        Args:
            template_id: ID of template to use
            recipients: List of recipients to sign
            subject: Email subject
            message: Email message
            
        Returns:
            Envelope ID
        """
        url = f"{self.API_BASE_URL}/accounts/{self.account_id}/envelopes"
        
        signers = [r.to_dict() for r in recipients if r.role == RecipientRole.SIGNER]
        
        payload = {
            "templateId": template_id,
            "templateRoles": signers,
            "status": "sent",
            "emailSubject": subject,
            "emailBlurb": message
        }
        
        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload
        )
        response.raise_for_status()
        
        return response.json()["envelopeId"]
    
    def bulk_send(
        self,
        template_id: str,
        recipients_list: List[List[Recipient]],
        subject: str = "Please Sign This Document"
    ) -> List[str]:
        """
        Send same document to multiple recipient groups.
        
        Args:
            template_id: Template ID
            recipients_list: List of recipient lists (each list is a group)
            subject: Email subject
            
        Returns:
            List of envelope IDs
        """
        envelope_ids = []
        
        for recipients in recipients_list:
            envelope_id = self.send_from_template(
                template_id,
                recipients,
                subject=subject
            )
            envelope_ids.append(envelope_id)
            time.sleep(0.5)  # Rate limiting
        
        return envelope_ids
    
    def get_embedded_signing_url(
        self,
        envelope_id: str,
        recipient_id: str,
        return_url: str
    ) -> str:
        """
        Get embedded signing URL for in-app signing ceremony.
        
        Args:
            envelope_id: ID of envelope
            recipient_id: ID of recipient
            return_url: URL to return to after signing
            
        Returns:
            Embedded signing URL
        """
        url = f"{self.API_BASE_URL}/accounts/{self.account_id}/envelopes/{envelope_id}/views/recipient"
        
        payload = {
            "returnUrl": return_url,
            "recipientId": recipient_id,
            "clientUserId": recipient_id,
            "authenticationType": "None"
        }
        
        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload
        )
        response.raise_for_status()
        
        return response.json()["url"]
    
    def poll_envelope_status(
        self,
        envelope_id: str,
        max_attempts: int = 60,
        interval_seconds: int = 5
    ) -> EnvelopeStatus:
        """
        Poll envelope status until completed or timeout.
        
        Args:
            envelope_id: ID of envelope
            max_attempts: Maximum polling attempts
            interval_seconds: Seconds between polls
            
        Returns:
            Final envelope status
        """
        for attempt in range(max_attempts):
            status_data = self.get_envelope_status(envelope_id)
            status = status_data.get("status")
            
            if status in ["completed", "voided", "declined"]:
                return EnvelopeStatus(status)
            
            if attempt < max_attempts - 1:
                time.sleep(interval_seconds)
        
        return EnvelopeStatus.SENT
    
    def register_webhook(self, envelope_id: str, webhook_url: str) -> None:
        """
        Register webhook for envelope events.
        
        Args:
            envelope_id: ID of envelope
            webhook_url: URL to post events to
        """
        url = f"{self.API_BASE_URL}/accounts/{self.account_id}/envelopes/{envelope_id}/listeners"
        
        payload = {
            "url": webhook_url,
            "events": [
                "envelope-sent",
                "envelope-delivered",
                "envelope-completed",
                "envelope-voided",
                "recipient-declined"
            ]
        }
        
        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload
        )
        response.raise_for_status()
    
    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature: str,
        webhook_key: str
    ) -> bool:
        """
        Verify DocuSign webhook signature.
        
        Args:
            payload_bytes: Raw request body
            signature: X-Docusign-Signature header value
            webhook_key: Webhook secret key
            
        Returns:
            True if signature is valid
        """
        hmac_obj = hashlib.sha256(webhook_key.encode())
        hmac_obj.update(payload_bytes)
        expected_signature = base64.b64encode(hmac_obj.digest()).decode()
        
        return signature == expected_signature
    
    def process_webhook_event(self, event_data: Dict) -> Dict:
        """
        Process incoming webhook event.
        
        Args:
            event_data: Event data from DocuSign
            
        Returns:
            Processed event with status information
        """
        envelope_id = event_data.get("envelopeId")
        status_data = self.get_envelope_status(envelope_id)
        
        return {
            "envelope_id": envelope_id,
            "event_type": event_data.get("event"),
            "timestamp": event_data.get("timestamp"),
            "status": status_data.get("status"),
            "recipients": status_data.get("recipients", {})
        }
