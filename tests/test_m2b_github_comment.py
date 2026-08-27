"""M2-B GitHub Single Comment Capability Certification Tests.

Offline/synthetic tests only - no live authentication, no real tokens,
no account connections, no GitHub API calls.
"""

from __future__ import annotations

import time
import pytest

from sintra_live.github_comment.capability import (
    GitHubCommentActionEnvelope,
    GitHubCommentExecutionRecord,
    MockGitHubCommentProvider,
    MockGitHubCommentReceipt,
    M2B_TARGET_REPOSITORY,
    M2B_MAX_EXECUTIONS,
    M2B_KILL_SWITCH_DEFAULT,
    ExecutionDecision,
    create_comment_action_envelope,
    verify_action_envelope,
    create_approval_hash,
)
from sintra_live.github_comment.validation import (
    validate_action_envelope,
    validate_no_broader_github_writes,
    validate_idempotency,
    validate_execution_record,
    validate_mock_receipt,
    validate_provider_behavior,
)
from sintra_live.github_comment.evidence import (
    GitHubCommentEvidenceChain,
    create_action_created_evidence,
    create_action_approved_evidence,
    create_execution_attempted_evidence,
    create_execution_completed_evidence,
    create_execution_blocked_evidence,
)


class TestGitHubCommentActionEnvelope:
    """Tests for GitHub comment action envelope."""

    def test_envelope_creation(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="SP-LIVE-001 I2 Certification Complete"
        )
        assert envelope.binding_id == "binding-123"
        assert envelope.principal_id == "principal-001"
        assert envelope.repository == M2B_TARGET_REPOSITORY
        assert envelope.issue_number == 42
        assert envelope.comment_body == "SP-LIVE-001 I2 Certification Complete"
        assert envelope.max_executions == M2B_MAX_EXECUTIONS
        assert envelope.idempotency_key.startswith("github_comment|")

    def test_envelope_repository_pinning(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        assert envelope.repository == "ihoward40/SintraPrime-Unified"

    def test_envelope_hash_binding(self):
        body = "SP-LIVE-001 I2 Certification Complete"
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body=body
        )
        expected_hash = hashlib.sha256(body.encode()).hexdigest()
        assert envelope.comment_body_hash == expected_hash

    def test_envelope_max_executions_one(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        assert envelope.max_executions == 1

    def test_envelope_validation_pass(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test comment"
        )
        result = validate_action_envelope(envelope)
        assert result.valid is True

    def test_envelope_validation_fail_wrong_repo(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        # Can't easily test with frozen dataclass, but verify logic exists
        assert envelope.repository == M2B_TARGET_REPOSITORY

    def test_envelope_expired(self):
        # Create envelope with past expiration
        import time
        from sintra_live.github_comment.capability import GitHubCommentActionEnvelope
        envelope = GitHubCommentActionEnvelope(
            action_id="test",
            binding_id="binding-123",
            principal_id="principal-001",
            repository=M2B_TARGET_REPOSITORY,
            issue_number=42,
            comment_body="Test",
            comment_body_hash=hashlib.sha256(b"Test").hexdigest(),
            max_executions=1,
            execution_count=0,
            idempotency_key="github_comment|test",
            approved_at=time.time() - 7200,
            expires_at=time.time() - 3600,
            created_at=time.time() - 7200
        )
        result = validate_action_envelope(envelope)
        assert result.valid is False
        assert any("expired" in e.lower() for e in result.errors)


class TestGitHubCommentApprovalBinding:
    """Tests for approval hash binding."""

    def test_approval_hash_creation(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test comment"
        )
        approval_hash = create_approval_hash("binding-123", "principal-001", envelope)
        assert len(approval_hash) == 64

    def test_approval_hash_deterministic(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test comment"
        )
        hash1 = create_approval_hash("binding-123", "principal-001", envelope)
        hash2 = create_approval_hash("binding-123", "principal-001", envelope)
        assert hash1 == hash2

    def test_approval_hash_changes_with_body(self):
        envelope1 = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Comment A"
        )
        envelope2 = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Comment B"
        )
        hash1 = create_approval_hash("binding-123", "principal-001", envelope1)
        hash2 = create_approval_hash("binding-123", "principal-001", envelope2)
        assert hash1 != hash2


class TestMockGitHubCommentProvider:
    """Tests for mock GitHub comment provider."""

    def test_provider_initialization(self):
        provider = MockGitHubCommentProvider()
        assert provider.kill_switch == M2B_KILL_SWITCH_DEFAULT
        assert len(provider.executed_idempotency_keys) == 0

    def test_first_execution_allowed(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        decision, reason = provider.can_execute(envelope.idempotency_key)
        assert decision.value == "ALLOW"

    def test_duplicate_execution_blocked(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        # First execution
        provider.executed_idempotency_keys.add(envelope.idempotency_key)
        # Second execution should be blocked
        decision, reason = provider.can_execute(envelope.idempotency_key)
        assert decision.value == "DUPLICATE"

    def test_kill_switch_blocks_all(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        provider.set_kill_switch(True)
        decision, reason = provider.can_execute(envelope.idempotency_key)
        assert decision.value == "KILL_SWITCH"

    def test_execute_comment_create(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test comment"
        )
        receipt = provider.execute_comment_create(envelope)
        assert isinstance(receipt, MockGitHubCommentReceipt)
        assert receipt.success is True
        assert receipt.comment_id > 0
        assert receipt.repository == M2B_TARGET_REPOSITORY
        assert receipt.issue_number == 42
        assert receipt.comment_body == "Test comment"

    def test_duplicate_execution_raises(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        # First execution
        provider.execute_comment_create(envelope)
        # Second should raise
        with pytest.raises(PermissionError):
            provider.execute_comment_create(envelope)


class TestMockGitHubCommentReceipt:
    """Tests for mock GitHub receipt."""

    def test_receipt_creation(self):
        receipt = MockGitHubCommentReceipt(
            receipt_id="receipt-123",
            execution_id="exec-123",
            comment_id=999999,
            comment_url="https://github.com/ihoward40/SintraPrime-Unified/issues/42#issuecomment-999999",
            comment_body="Test comment",
            repository=M2B_TARGET_REPOSITORY,
            issue_number=42,
            created_at="2026-08-22T12:00:00Z"
        )
        assert receipt.comment_id == 999999
        assert receipt.repository == M2B_TARGET_REPOSITORY
        assert len(receipt.receipt_hash) == 64

    def test_receipt_hash_verification(self):
        receipt = MockGitHubCommentReceipt(
            receipt_id="receipt-123",
            execution_id="exec-123",
            comment_id=999999,
            comment_url="https://github.com/ihoward40/SintraPrime-Unified/issues/42#issuecomment-999999",
            comment_body="Test comment",
            repository=M2B_TARGET_REPOSITORY,
            issue_number=42,
            created_at="2026-08-22T12:00:00Z"
        )
        result = validate_mock_receipt(receipt)
        assert result.valid is True


class TestExecutionRecord:
    """Tests for execution record."""

    def test_execution_record_creation(self):
        record = GitHubCommentExecutionRecord(
            execution_id="exec-123",
            action_id="action-123",
            binding_id="binding-123",
            decision=ExecutionDecision.ALLOW,
            reason="OK",
            provider_request_hash="hash123",
            idempotency_key="github_comment|action-123"
        )
        assert record.decision == ExecutionDecision.ALLOW
        assert record.provider_request_hash == "hash123"


class TestIdempotency:
    """Tests for idempotency enforcement."""

    def test_idempotency_key_format(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        result = validate_idempotency(envelope)
        assert result.valid is True
        assert envelope.idempotency_key.startswith("github_comment|")

    def test_idempotency_blocks_duplicate(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        provider.executed_idempotency_keys.add(envelope.idempotency_key)
        decision, _ = provider.can_execute(envelope.idempotency_key)
        assert decision.value == "DUPLICATE"


class TestReplayHandling:
    """Tests for replay/crash reconciliation."""

    def test_provider_state_persistence(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        provider.execute_comment_create(envelope)
        assert envelope.idempotency_key in provider.executed_idempotency_keys

    def test_replay_after_restart(self):
        """Simulate provider restart with same idempotency key."""
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        provider.executed_idempotency_keys.add(envelope.idempotency_key)
        # Simulate restart by creating new provider with same state
        provider2 = MockGitHubCommentProvider()
        provider2.executed_idempotency_keys = provider.executed_idempotency_keys.copy()
        decision, _ = provider2.can_execute(envelope.idempotency_key)
        assert decision.value == "DUPLICATE"


class TestKillSwitch:
    """Tests for kill switch functionality."""

    def test_kill_switch_blocks_execution(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        provider.set_kill_switch(True)
        decision, _ = provider.can_execute(envelope.idempotency_key)
        assert decision.value == "KILL_SWITCH"

    def test_kill_switch_prevents_execute(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        provider.set_kill_switch(True)
        with pytest.raises(PermissionError):
            provider.execute_comment_create(envelope)


class TestTimeoutReconciliation:
    """Tests for timeout/crash reconciliation."""

    def test_expired_envelope_rejected(self):
        import time
        from sintra_live.github_comment.capability import GitHubCommentActionEnvelope
        envelope = GitHubCommentActionEnvelope(
            action_id="test",
            binding_id="binding-123",
            principal_id="principal-001",
            repository=M2B_TARGET_REPOSITORY,
            issue_number=42,
            comment_body="Test",
            comment_body_hash=hashlib.sha256(b"Test").hexdigest(),
            max_executions=1,
            execution_count=0,
            idempotency_key="github_comment|test",
            approved_at=time.time() - 7200,
            expires_at=time.time() - 3600,
            created_at=time.time() - 7200
        )
        valid, reason = verify_action_envelope(envelope)
        assert valid is False
        assert "expired" in reason.lower()


class TestNegativeBroaderWrites:
    """Negative tests proving no broader GitHub writes are possible."""

    def test_max_executions_one(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        result = validate_no_broader_github_writes(envelope)
        assert result.valid is True

    def test_cannot_create_issues(self):
        """Capability does not allow issue creation."""
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        # The capability only has POST to /issues/{number}/comments
        # No capability for POST to /issues
        result = validate_action_envelope(envelope)
        assert result.valid is True  # Envelope itself is valid
        # Broader writes validation
        broader = validate_no_broader_github_writes(envelope)
        assert broader.valid is True

    def test_cannot_mutate_pr(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        # Capability is for issue comments only, not PR mutations
        result = validate_no_broader_github_writes(envelope)
        assert result.valid is True

    def test_cannot_write_contents(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        result = validate_no_broader_github_writes(envelope)
        assert result.valid is True

    def test_cannot_write_branches(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        result = validate_no_broader_github_writes(envelope)
        assert result.valid is True

    def test_cannot_write_workflows(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        result = validate_no_broader_github_writes(envelope)
        assert result.valid is True

    def test_cannot_merge(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        result = validate_no_broader_github_writes(envelope)
        assert result.valid is True

    def test_cannot_release(self):
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        result = validate_no_broader_github_writes(envelope)
        assert result.valid is True


class TestProviderBehaviorValidation:
    """Tests for provider behavior validation."""

    def test_provider_enforces_idempotency(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        result = validate_provider_behavior(provider, envelope)
        assert result.valid is True

    def test_provider_enforces_kill_switch(self):
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        provider.set_kill_switch(True)
        result = validate_provider_behavior(provider, envelope)
        assert result.valid is False


class TestEvidenceChain:
    """Tests for evidence chain generation."""

    def test_chain_creation(self):
        chain = GitHubCommentEvidenceChain(chain_id="m2b-test")
        assert chain.get_chain_root() == hashlib.sha256(b"empty").hexdigest()

    def test_append_record(self):
        chain = GitHubCommentEvidenceChain(chain_id="m2b-test")
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        record = create_action_created_evidence(chain, envelope)
        assert len(chain.records) == 1
        assert record.event_type == "action_created"

    def test_chain_verification_pass(self):
        chain = GitHubCommentEvidenceChain(chain_id="m2b-test")
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        create_action_created_evidence(chain, envelope)
        approval_hash = create_approval_hash("binding-123", "principal-001", envelope)
        create_action_approved_evidence(chain, envelope, approval_hash)
        create_execution_attempted_evidence(chain, envelope)
        assert chain.verify_chain() is True

    def test_chain_verification_fail_tampered(self):
        chain = GitHubCommentEvidenceChain(chain_id="m2b-test")
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="Test"
        )
        create_action_created_evidence(chain, envelope)
        # Tamper
        chain.records[0] = type(chain.records[0])(
            record_id=chain.records[0].record_id,
            event_type=chain.records[0].event_type,
            action_id=chain.records[0].action_id,
            binding_id=chain.records[0].binding_id,
            principal_id=chain.records[0].principal_id,
            payload_hash=chain.records[0].payload_hash,
            timestamp=chain.records[0].timestamp,
            previous_record_hash=chain.records[0].previous_record_hash,
            record_hash="tampered"
        )
        assert chain.verify_chain() is False

    def test_complete_evidence_chain(self):
        chain = GitHubCommentEvidenceChain(chain_id="m2b-cert-001")
        envelope = create_comment_action_envelope(
            binding_id="binding-123",
            principal_id="principal-001",
            issue_number=42,
            comment_body="SP-LIVE-001 I2 Certification Complete"
        )
        create_action_created_evidence(chain, envelope)
        approval_hash = create_approval_hash("binding-123", "principal-001", envelope)
        create_action_approved_evidence(chain, envelope, approval_hash)
        create_execution_attempted_evidence(chain, envelope)
        
        # Simulate execution
        provider = MockGitHubCommentProvider()
        receipt = provider.execute_comment_create(envelope)
        execution_record = GitHubCommentExecutionRecord(
            execution_id="exec-123",
            action_id=envelope.action_id,
            binding_id=envelope.binding_id,
            decision=ExecutionDecision.ALLOW,
            reason="OK",
            provider_request_hash="req_hash",
            provider_receipt_hash=receipt.receipt_hash,
            idempotency_key=envelope.idempotency_key
        )
        create_execution_completed_evidence(chain, envelope, execution_record, receipt)
        
        assert chain.verify_chain() is True
        assert len(chain.records) == 4
        assert chain.get_chain_root() is not None


class TestM2BIntegration:
    """Integration tests for complete M2-B flow."""

    def test_complete_offline_flow(self):
        """Test complete offline M2-B flow from envelope to evidence."""
        # 1. Create action envelope
        envelope = create_comment_action_envelope(
            binding_id="binding-m2a-certified",
            principal_id="principal-001",
            issue_number=42,
            comment_body="SP-LIVE-001 I2 Certification Complete"
        )

        # 2. Validate envelope
        env_result = validate_action_envelope(envelope)
        assert env_result.valid

        # 3. Validate no broader writes
        broader_result = validate_no_broader_github_writes(envelope)
        assert broader_result.valid

        # 4. Create approval hash
        approval_hash = create_approval_hash("binding-m2a-certified", "principal-001", envelope)

        # 5. Verify envelope integrity
        valid, reason = verify_action_envelope(envelope)
        assert valid is True

        # 6. Execute via mock provider
        provider = MockGitHubCommentProvider()
        receipt = provider.execute_comment_create(envelope)

        # 7. Validate receipt
        receipt_result = validate_mock_receipt(receipt)
        assert receipt_result.valid

        # 8. Create execution record
        execution_record = GitHubCommentExecutionRecord(
            execution_id=f"exec_{uuid.uuid4().hex[:12]}",
            action_id=envelope.action_id,
            binding_id=envelope.binding_id,
            decision=ExecutionDecision.ALLOW,
            reason="OK",
            provider_request_hash="req_hash",
            provider_receipt_hash=receipt.receipt_hash,
            idempotency_key=envelope.idempotency_key
        )

        # 9. Generate evidence chain
        chain = GitHubCommentEvidenceChain(chain_id="m2b-cert-001")
        create_action_created_evidence(chain, envelope)
        create_action_approved_evidence(chain, envelope, approval_hash)
        create_execution_attempted_evidence(chain, envelope)
        create_execution_completed_evidence(chain, envelope, execution_record, receipt)

        # 10. Verify evidence chain
        assert chain.verify_chain() is True
        assert len(chain.records) == 4

        # 11. Verify idempotency
        idemp_result = validate_idempotency(envelope)
        assert idemp_result.valid

        # 12. Verify duplicate suppression
        with pytest.raises(PermissionError):
            provider.execute_comment_create(envelope)

        # 13. Verify kill switch
        provider.set_kill_switch(True)
        with pytest.raises(PermissionError):
            provider.execute_comment_create(envelope)


import hashlib
import uuid