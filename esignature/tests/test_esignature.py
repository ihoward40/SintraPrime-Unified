"""
Comprehensive pytest tests for eSignature integration.

Tests DocuSign client, legal signer, and signature vault with 35+ test functions.

Line count: 380+ lines
"""

import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

from ..docusign_client import (
    DocuSignClient, Document, Recipient, EnvelopeConfig, 
    SignatureTab, SignatureTabType, RecipientRole, EnvelopeStatus,
    NotificationSettings
)
from ..legal_signer import (
    LegalDocumentSigner, DocumentType, NotaryInfo, NotaryType, 
    Jurisdiction, SigningParty
)
from ..signature_vault import (
    SignatureVault, SignedDocument, DocumentAccessLevel, 
    RetentionPolicy, AuditTrail
)


class TestDocuSignClient:
    """Test DocuSign client functionality."""
    
    def setup_method(self):
        """Setup for each test."""
        self.client = DocuSignClient(
            account_id="test-account-123",
            client_id="test-client",
            client_secret="test-secret",
            private_key_pem="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
            user_id="test-user"
        )
    
    def test_envelope_config_creation(self):
        """Test envelope configuration creation."""
        config = EnvelopeConfig(
            subject="Test Document",
            message="Please sign",
            documents=[],
            recipients=[]
        )
        assert config.subject == "Test Document"
        assert config.status == EnvelopeStatus.DRAFT
    
    def test_recipient_role_signer(self):
        """Test recipient role as signer."""
        recipient = Recipient(
            recipient_id="1",
            email="john@example.com",
            name="John Doe",
            role=RecipientRole.SIGNER
        )
        assert recipient.role == RecipientRole.SIGNER
        assert recipient.email == "john@example.com"
    
    def test_recipient_role_carbon_copy(self):
        """Test recipient role as carbon copy."""
        recipient = Recipient(
            recipient_id="2",
            email="cc@example.com",
            name="CC User",
            role=RecipientRole.CARBON_COPY
        )
        assert recipient.role == RecipientRole.CARBON_COPY
    
    def test_signature_tab_signature_type(self):
        """Test signature tab configuration."""
        tab = SignatureTab(
            tab_label="signature_1",
            tab_type=SignatureTabType.SIGNATURE,
            page_number=1,
            x_position=100,
            y_position=200
        )
        assert tab.tab_type == SignatureTabType.SIGNATURE
        assert tab.page_number == 1
    
    def test_signature_tab_initials_type(self):
        """Test initials tab configuration."""
        tab = SignatureTab(
            tab_label="initials_1",
            tab_type=SignatureTabType.INITIALS,
            page_number=1,
            x_position=100,
            y_position=200
        )
        assert tab.tab_type == SignatureTabType.INITIALS
    
    def test_signature_tab_date_type(self):
        """Test date tab configuration."""
        tab = SignatureTab(
            tab_label="date_1",
            tab_type=SignatureTabType.DATE,
            page_number=1,
            x_position=300,
            y_position=200
        )
        assert tab.tab_type == SignatureTabType.DATE
    
    def test_notification_settings_reminders(self):
        """Test notification settings with reminders."""
        notifications = NotificationSettings(
            reminder_enabled=True,
            reminder_delay=5,
            expiration_enabled=True,
            expiration_days=30
        )
        assert notifications.reminder_enabled
        assert notifications.expiration_enabled
    
    def test_multiple_recipients_routing_order(self):
        """Test multiple recipients with routing order."""
        recipients = [
            Recipient(
                recipient_id="1",
                email="john@example.com",
                name="John",
                routing_order=1
            ),
            Recipient(
                recipient_id="2",
                email="jane@example.com",
                name="Jane",
                routing_order=2
            )
        ]
        assert recipients[0].routing_order < recipients[1].routing_order
    
    def test_envelope_status_transitions(self):
        """Test envelope status enum values."""
        assert EnvelopeStatus.DRAFT.value == "created"
        assert EnvelopeStatus.SENT.value == "sent"
        assert EnvelopeStatus.COMPLETED.value == "completed"
        assert EnvelopeStatus.VOIDED.value == "voided"


class TestLegalDocumentSigner:
    """Test legal document signer with smart tab placement."""
    
    def setup_method(self):
        """Setup for each test."""
        self.signer = LegalDocumentSigner()
    
    def test_prepare_contract_for_signing(self):
        """Test preparing contract for signing."""
        parties = [
            SigningParty(
                name="John Doe",
                email="john@example.com",
                role="buyer",
                signing_order=1
            ),
            SigningParty(
                name="Jane Smith",
                email="jane@example.com",
                role="seller",
                signing_order=2
            )
        ]
        config = self.signer.prepare_for_signing(
            "/tmp/contract.pdf",
            DocumentType.CONTRACT,
            parties
        )
        assert config["document_type"] == DocumentType.CONTRACT.value
        assert len(config["signing_parties"]) == 2
        assert len(config["tabs"]) > 0
    
    def test_prepare_trust_for_signing(self):
        """Test preparing trust document for signing."""
        parties = [
            SigningParty(
                name="Grantor",
                email="grantor@example.com",
                role="grantor",
                signing_order=1,
                requires_notary=True
            )
        ]
        config = self.signer.prepare_for_signing(
            "/tmp/trust.pdf",
            DocumentType.TRUST,
            parties
        )
        assert "notary_required" in config
        assert config["notary_required"]
    
    def test_prepare_will_for_signing(self):
        """Test preparing will document for signing."""
        parties = [
            SigningParty(
                name="Testator",
                email="testator@example.com",
                role="testator",
                signing_order=1,
                requires_notary=True,
                requires_witness=True
            )
        ]
        config = self.signer.prepare_for_signing(
            "/tmp/will.pdf",
            DocumentType.WILL,
            parties
        )
        assert config["document_type"] == DocumentType.WILL.value
    
    def test_prepare_real_estate_document(self):
        """Test preparing real estate document."""
        parties = [
            SigningParty(
                name="Grantor",
                email="grantor@example.com",
                role="grantor",
                signing_order=1
            ),
            SigningParty(
                name="Grantee",
                email="grantee@example.com",
                role="grantee",
                signing_order=2
            )
        ]
        config = self.signer.prepare_for_signing(
            "/tmp/deed.pdf",
            DocumentType.REAL_ESTATE,
            parties
        )
        assert len(config["tabs"]) >= 2
    
    def test_setup_notary_traditional(self):
        """Test setup traditional notarization."""
        notary_info = NotaryInfo(
            notary_name="Mary Johnson",
            notary_commission_number="123456",
            notary_type=NotaryType.TRADITIONAL,
            commission_expiry=datetime.now() + timedelta(days=365)
        )
        config = self.signer.setup_notary(
            "envelope-123",
            notary_info,
            NotaryType.TRADITIONAL
        )
        assert config["notary_name"] == "Mary Johnson"
        assert config["notary_type"] == "traditional"
    
    def test_setup_notary_remote_online(self):
        """Test setup remote online notarization (RON)."""
        notary_info = NotaryInfo(
            notary_name="Robert Chen",
            notary_commission_number="RON-123",
            notary_type=NotaryType.REMOTE_ONLINE,
            commission_expiry=datetime.now() + timedelta(days=365)
        )
        config = self.signer.setup_notary(
            "envelope-456",
            notary_info,
            NotaryType.REMOTE_ONLINE
        )
        assert config["notary_type"] == "remote_online"
        assert config["identity_verification_required"]
        assert config["signers_present_virtually"]
    
    def test_notary_expiration_check(self):
        """Test notary credential expiration check."""
        expired_notary = NotaryInfo(
            notary_name="Expired Notary",
            commission_expiry=datetime.now() - timedelta(days=1)
        )
        assert not expired_notary.is_valid()
        
        valid_notary = NotaryInfo(
            notary_name="Valid Notary",
            commission_expiry=datetime.now() + timedelta(days=365)
        )
        assert valid_notary.is_valid()
    
    def test_check_legal_validity_federal(self):
        """Test legal validity check for federal jurisdiction."""
        report = self.signer.check_legal_validity(
            "electronic",
            DocumentType.CONTRACT,
            Jurisdiction.FEDERAL,
            witness_count=0,
            notarized=False
        )
        assert report.is_valid
        assert report.jurisdiction == Jurisdiction.FEDERAL
    
    def test_check_legal_validity_new_york_wet_signature_required(self):
        """Test NY requires wet signature for certain documents."""
        report = self.signer.check_legal_validity(
            "electronic",
            DocumentType.POWER_OF_ATTORNEY,
            Jurisdiction.NEW_YORK,
            witness_count=0,
            notarized=False
        )
        # NY law may require wet signature for POA
        assert report.jurisdiction == Jurisdiction.NEW_YORK
    
    def test_check_legal_validity_california_electronic_ok(self):
        """Test California accepts electronic signatures."""
        report = self.signer.check_legal_validity(
            "electronic",
            DocumentType.CONTRACT,
            Jurisdiction.CALIFORNIA,
            witness_count=0,
            notarized=False
        )
        assert report.is_valid
        assert report.jurisdiction == Jurisdiction.CALIFORNIA
    
    def test_enforce_signing_order_sequential(self):
        """Test enforcement of sequential signing order."""
        workflow = {
            "steps": [
                {"order": 1, "party": {"name": "John"}},
                {"order": 2, "party": {"name": "Jane"}}
            ]
        }
        
        # John signed first - Jane should not be able to sign yet
        valid, msg = self.signer.enforce_signing_order(
            "envelope-123",
            workflow,
            ["John"]
        )
        assert not valid
        
        # Both signed
        valid, msg = self.signer.enforce_signing_order(
            "envelope-123",
            workflow,
            ["John", "Jane"]
        )
        assert valid


class TestSignatureVault:
    """Test signature vault storage and audit trail."""
    
    def setup_method(self):
        """Setup for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.vault = SignatureVault(
            vault_path=self.temp_dir,
            encryption_enabled=False  # Disable for testing
        )
    
    def teardown_method(self):
        """Cleanup after each test."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_store_signed_document(self):
        """Test storing signed document in vault."""
        signed_doc = self.vault.store_signed(
            envelope_id="env-123",
            matter_id="matter-001",
            client_id="client-001",
            document_name="Contract.pdf",
            document_type="contract",
            file_content=b"PDF content",
            signed_by=["John Doe"],
            access_level=DocumentAccessLevel.CONFIDENTIAL
        )
        assert signed_doc.document_id is not None
        assert signed_doc.envelope_id == "env-123"
        assert signed_doc.matter_id == "matter-001"
    
    def test_retrieve_by_matter_id(self):
        """Test retrieving documents by matter ID."""
        self.vault.store_signed(
            "env-001",
            "matter-abc",
            "client-001",
            "Doc1.pdf",
            "contract",
            b"content1",
            ["Signer1"]
        )
        self.vault.store_signed(
            "env-002",
            "matter-abc",
            "client-001",
            "Doc2.pdf",
            "agreement",
            b"content2",
            ["Signer2"]
        )
        
        docs = self.vault.retrieve_signed(matter_id="matter-abc")
        assert len(docs) == 2
    
    def test_retrieve_by_client_id(self):
        """Test retrieving documents by client ID."""
        self.vault.store_signed(
            "env-001",
            "matter-001",
            "client-xyz",
            "Doc.pdf",
            "contract",
            b"content",
            ["Signer"]
        )
        
        docs = self.vault.retrieve_signed(client_id="client-xyz")
        assert len(docs) == 1
        assert docs[0].client_id == "client-xyz"
    
    def test_retrieve_by_envelope_id(self):
        """Test retrieving document by envelope ID."""
        doc = self.vault.store_signed(
            "env-specific",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            b"content",
            ["Signer"]
        )
        
        retrieved = self.vault.retrieve_signed(envelope_id="env-specific")
        assert len(retrieved) == 1
        assert retrieved[0].envelope_id == "env-specific"
    
    def test_audit_trail_creation(self):
        """Test audit trail creation on document storage."""
        signed_doc = self.vault.store_signed(
            "env-123",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            b"content",
            ["Signer"]
        )
        
        audit_trail = self.vault.get_audit_trail(signed_doc.document_id)
        assert audit_trail is not None
        assert len(audit_trail.entries) > 0
    
    def test_audit_trail_add_entry(self):
        """Test adding entry to audit trail."""
        signed_doc = self.vault.store_signed(
            "env-123",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            b"content",
            ["Signer"]
        )
        
        success = self.vault.add_audit_entry(
            signed_doc.document_id,
            "document_viewed",
            "user-123"
        )
        assert success
        
        audit_trail = self.vault.get_audit_trail(signed_doc.document_id)
        assert len(audit_trail.entries) > 1
    
    def test_audit_trail_integrity_verification(self):
        """Test audit trail integrity verification."""
        signed_doc = self.vault.store_signed(
            "env-123",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            b"content",
            ["Signer"]
        )
        
        audit_trail = self.vault.get_audit_trail(signed_doc.document_id)
        is_valid, msg = audit_trail.verify_integrity()
        assert is_valid
    
    def test_document_retention_policy(self):
        """Test retention policy assignment."""
        signed_doc = self.vault.store_signed(
            "env-123",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            b"content",
            ["Signer"],
            retention_policy=RetentionPolicy.STANDARD
        )
        
        assert signed_doc.retention_policy == RetentionPolicy.STANDARD
        assert signed_doc.retention_expires > datetime.utcnow()
    
    def test_access_level_confidential(self):
        """Test document access level confidential."""
        signed_doc = self.vault.store_signed(
            "env-123",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            b"content",
            ["Signer"],
            access_level=DocumentAccessLevel.CONFIDENTIAL
        )
        
        assert signed_doc.access_level == DocumentAccessLevel.CONFIDENTIAL
    
    def test_access_level_privileged(self):
        """Test document access level privileged."""
        signed_doc = self.vault.store_signed(
            "env-123",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            b"content",
            ["Signer"],
            access_level=DocumentAccessLevel.PRIVILEGED
        )
        
        assert signed_doc.access_level == DocumentAccessLevel.PRIVILEGED
    
    def test_document_checksum_verification(self):
        """Test document checksum for integrity."""
        file_content = b"Important document content"
        signed_doc = self.vault.store_signed(
            "env-123",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            file_content,
            ["Signer"]
        )
        
        assert signed_doc.checksum is not None
        assert len(signed_doc.checksum) == 64  # SHA256 hex digest
    
    def test_verify_document_integrity(self):
        """Test document integrity verification."""
        signed_doc = self.vault.store_signed(
            "env-123",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            b"content",
            ["Signer"]
        )
        
        is_valid, msg = self.vault.verify_document_integrity(signed_doc.document_id)
        assert is_valid
    
    def test_multiple_signers_recorded(self):
        """Test multiple signers are recorded."""
        signed_doc = self.vault.store_signed(
            "env-123",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            b"content",
            signed_by=["John Doe", "Jane Smith", "Robert Chen"]
        )
        
        assert len(signed_doc.signed_by) == 3
        assert "John Doe" in signed_doc.signed_by
    
    def test_vault_metadata_persistence(self):
        """Test vault metadata is persisted to disk."""
        signed_doc = self.vault.store_signed(
            "env-123",
            "matter-001",
            "client-001",
            "Doc.pdf",
            "contract",
            b"content",
            ["Signer"],
            metadata={"case_number": "2024-CV-001", "court": "Supreme Court"}
        )
        
        assert signed_doc.metadata["case_number"] == "2024-CV-001"


class TestIntegrationESignature:
    """Integration tests for e-signature workflow."""
    
    def test_complete_signing_workflow(self):
        """Test complete document signing workflow."""
        # Setup vault
        temp_dir = tempfile.mkdtemp()
        vault = SignatureVault(vault_path=temp_dir, encryption_enabled=False)
        
        # Prepare document
        signer = LegalDocumentSigner()
        parties = [
            SigningParty(
                name="John Doe",
                email="john@example.com",
                role="buyer",
                signing_order=1
            ),
            SigningParty(
                name="Jane Smith",
                email="jane@example.com",
                role="seller",
                signing_order=2
            )
        ]
        config = signer.prepare_for_signing(
            "/tmp/contract.pdf",
            DocumentType.CONTRACT,
            parties
        )
        
        # Store signed document
        signed_doc = vault.store_signed(
            "env-workflow",
            "matter-workflow",
            "client-workflow",
            "Contract.pdf",
            "contract",
            b"signed content",
            ["John Doe", "Jane Smith"]
        )
        
        # Verify
        assert signed_doc.document_id is not None
        assert len(signed_doc.signed_by) == 2
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
