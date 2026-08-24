"""Tests for L1 Action Envelope validation - fail-closed envelope verification."""

from __future__ import annotations

import hashlib
import time
import pytest
from datetime import datetime, timezone, timedelta

from sintra_live.envelope.l1_action_envelope import (
    L1ActionEnvelope,
    EnvelopeValidator,
    create_l1_action_envelope,
    CAPABILITY_ID,
    COMMENT_BODY,
    COMMENT_BODY_SHA256,
    MAX_EXECUTIONS,
    ACTIVE_PROGRAM,
    ACTIVE_GATE,
    ACCOUNT,
    REPOSITORY,
    RESOURCE_TYPE,
    RESOURCE_NUMBER,
    HTTP_METHOD,
    EXACT_ENDPOINT,
    ACTION_TYPE,
    CONSEQUENCE_CLASS,
)


class TestL1EnvelopeValidation:
    """Test L1 action envelope validation - all fail-closed checks."""
    
    def setup_method(self):
        """Create a valid envelope for testing."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=1)
        
        self.valid_envelope = L1ActionEnvelope(
            program_id=ACTIVE_PROGRAM,
            gate_id=ACTIVE_GATE,
            authorization_id="auth-test-001",
            principal_id="principal-001",
            authenticated_provider_account=ACCOUNT,
            repository=REPOSITORY,
            resource_type=RESOURCE_TYPE,
            resource_number=RESOURCE_NUMBER,
            capability=CAPABILITY_ID,
            operation=ACTION_TYPE,
            http_method=HTTP_METHOD,
            endpoint=EXACT_ENDPOINT,
            comment_body=COMMENT_BODY,
            comment_body_sha256=COMMENT_BODY_SHA256,
            consequence_class=CONSEQUENCE_CLASS,
            max_executions=MAX_EXECUTIONS,
            execution_id="exec-test-001",
            execution_nonce="test-nonce-1234567890abcdef",
            execution_adapter="github-app-live-comment-v1",
            execution_entrypoint_id="sintra-live-l1-comment-runner-v1",
            provider_mode="LIVE",
            provider_class="GitHubAppLiveProvider",
            baseline_commit="baseline-commit-test",
            baseline_tree="baseline-tree-test",
            baseline_manifest_sha256="baseline-manifest-test",
            created_at_iso=now.isoformat(),
            expires_at_iso=expires_at.isoformat(),
            authority_snapshot_hash="auth-snap-test-001",
            approval_requirement_hash="approval-req-test-001",
        )
        self.validator = EnvelopeValidator()
    
    def test_valid_envelope_passes(self):
        """Valid envelope must pass all checks."""
        valid, errors = self.validator.validate(self.valid_envelope)
        assert valid, f"Valid envelope failed: {errors}"
    
    def test_wrong_program_denied(self):
        """Wrong program_id must be denied."""
        envelope = self._mutate(program_id="WRONG-PROGRAM")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("PROGRAM_MISMATCH" in e for e in errors)
    
    def test_wrong_gate_denied(self):
        """Wrong gate_id must be denied."""
        envelope = self._mutate(gate_id="WRONG_GATE")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("GATE_MISMATCH" in e for e in errors)
    
    def test_missing_authority_snapshot_denied(self):
        """Missing authority_snapshot_hash must be denied."""
        envelope = self._mutate(authority_snapshot_hash="")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("MISSING_AUTHORITY_SNAPSHOT_HASH" in e for e in errors)
    
    def test_stale_authority_snapshot_denied(self):
        """Stale authority snapshot (expired) - envelope expiry covers this."""
        # The envelope itself has an expiry; authority snapshot expiry is checked at gate level
        envelope = self._mutate(expires_at_iso=(datetime.now(timezone.utc) - timedelta(minutes=100)).isoformat())
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("ENVELOPE_EXPIRED" in e for e in errors)
    
    def test_wrong_account_denied(self):
        """Wrong authenticated provider account must be denied."""
        envelope = self._mutate(authenticated_provider_account="wrong-account")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("ACCOUNT_MISMATCH" in e for e in errors)
    
    def test_wrong_repository_denied(self):
        """Wrong repository must be denied."""
        envelope = self._mutate(repository="wrong/repo")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("REPOSITORY_MISMATCH" in e for e in errors)
    
    def test_wrong_pr_denied(self):
        """Wrong PR number must be denied."""
        envelope = self._mutate(resource_number=999)
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("RESOURCE_NUMBER_MISMATCH" in e for e in errors)
    
    def test_wrong_capability_denied(self):
        """Wrong capability must be denied."""
        envelope = self._mutate(capability="wrong.capability")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("CAPABILITY_MISMATCH" in e for e in errors)
    
    def test_capability_name_drift_denied(self):
        """Capability name drift (alias/substitution) must be denied.
        
        This is the critical regression test for the Hermes naming drift.
        AUTHORIZED = provider.github-issue-comment-create-v1
        REQUESTED = provider.github-comment-write-v1
        EXPECTED = DENY_CAPABILITY_MISMATCH
        """
        envelope = self._mutate(capability="provider.github-comment-write-v1")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("CAPABILITY_MISMATCH" in e for e in errors)
        assert "provider.github-issue-comment-create-v1" in str(errors)
        assert "provider.github-comment-write-v1" in str(errors)
    
    def test_body_mutation_denied(self):
        """Mutated comment body must be denied."""
        envelope = self._mutate(comment_body="Different body text")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("BODY_HASH_MISMATCH" in e for e in errors)
    
    def test_body_hash_mismatch_denied(self):
        """Body hash mismatch must be denied."""
        envelope = self._mutate(comment_body_sha256="wronghash123")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("BODY_HASH_MISMATCH" in e for e in errors)
    
    def test_max_executions_not_one_denied(self):
        """Max executions != 1 must be denied."""
        envelope = self._mutate(max_executions=2)
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("MAX_EXECUTIONS_MISMATCH" in e for e in errors)
    
    def test_missing_nonce_denied(self):
        """Missing execution nonce must be denied."""
        envelope = self._mutate(execution_nonce="")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("MISSING_EXECUTION_NONCE" in e for e in errors)
    
    def test_expired_envelope_denied(self):
        """Expired envelope must be denied."""
        envelope = self._mutate(expires_at_iso=(datetime.now(timezone.utc) - timedelta(minutes=100)).isoformat())
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("ENVELOPE_EXPIRED" in e for e in errors)
    
    def test_envelope_integrity_denied(self):
        """Envelope with tampered hash must be denied."""
        # Create valid envelope first
        envelope = self.valid_envelope
        # Now tamper with the hash AFTER creation
        object.__setattr__(envelope, 'envelope_hash', "tampered-hash")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("ENVELOPE_INTEGRITY_FAILURE" in e for e in errors)
    
    def test_envelope_mutation_detected(self):
        """Any mutation of envelope fields must be detected via integrity check."""
        # Test that envelope hash is deterministic and detects changes
        envelope1 = self.valid_envelope
        envelope2 = self._mutate(authorization_id="auth-different")
        
        assert envelope1.envelope_hash != envelope2.envelope_hash
        # Mutate envelope2's hash to test integrity detection
        object.__setattr__(envelope2, 'envelope_hash', "wrong-hash")
        assert not envelope2.verify_integrity()
    
    def test_authority_snapshot_hash_binding(self):
        """Envelope must bind authority snapshot hash."""
        envelope = self._mutate(authority_snapshot_hash="different-snapshot")
        valid, errors = self.validator.validate(envelope)
        # Should still pass validation but have different envelope hash
        assert envelope.envelope_hash != self.valid_envelope.envelope_hash
    
    def test_approval_requirement_hash_binding(self):
        """Envelope must bind approval requirement hash."""
        envelope = self._mutate(approval_requirement_hash="different-approval")
        assert envelope.envelope_hash != self.valid_envelope.envelope_hash
    
    def test_create_envelope_helper(self):
        """Test the create_l1_action_envelope helper function."""
        envelope = create_l1_action_envelope(
            authority_snapshot_hash="auth-snap-helper",
            approval_requirement_hash="approval-req-helper",
            baseline_commit="baseline-commit-helper",
            baseline_tree="baseline-tree-helper",
            baseline_manifest_sha256="baseline-manifest-helper",
        )
        
        assert envelope.program_id == ACTIVE_PROGRAM
        assert envelope.gate_id == ACTIVE_GATE
        assert envelope.capability == CAPABILITY_ID
        assert envelope.comment_body == COMMENT_BODY
        assert envelope.comment_body_sha256 == COMMENT_BODY_SHA256
        assert envelope.max_executions == MAX_EXECUTIONS
        assert envelope.execution_adapter == "github-app-live-comment-v1"
        assert envelope.provider_mode == "LIVE"
        assert envelope.provider_class == "GitHubAppLiveProvider"
        assert envelope.baseline_commit == "baseline-commit-helper"
        assert envelope.verify_integrity()
        # Verify ISO format timestamps
        assert "T" in envelope.created_at_iso
        assert "T" in envelope.expires_at_iso
        assert envelope.created_at_iso.endswith("+00:00") or envelope.created_at_iso.endswith("Z")
    
    def test_execution_adapter_mismatch_denied(self):
        """Wrong execution adapter must be denied."""
        envelope = self._mutate(execution_adapter="ad-hoc-mock-adapter")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("EXECUTION_ADAPTER_MISMATCH" in e for e in errors)
    
    def test_provider_mode_mismatch_denied(self):
        """MOCK provider mode in a live envelope must be denied."""
        envelope = self._mutate(provider_mode="MOCK")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("PROVIDER_MODE_MISMATCH" in e for e in errors)
    
    def test_provider_class_mismatch_denied(self):
        """Wrong provider class must be denied."""
        envelope = self._mutate(provider_class="MockGitHubCommentProvider")
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("PROVIDER_CLASS_MISMATCH" in e for e in errors)
    
    def test_missing_baseline_identity_denied(self):
        """Missing baseline commit/tree/manifest must be denied."""
        envelope = self._mutate(
            baseline_commit="",
            baseline_tree="",
            baseline_manifest_sha256="",
        )
        valid, errors = self.validator.validate(envelope)
        assert not valid
        assert any("MISSING_BASELINE_COMMIT" in e for e in errors)
        assert any("MISSING_BASELINE_TREE" in e for e in errors)
        assert any("MISSING_BASELINE_MANIFEST_SHA256" in e for e in errors)
    
    def test_baseline_identity_binds_envelope_hash(self):
        """Changing baseline identity must change envelope hash."""
        envelope1 = self.valid_envelope
        envelope2 = self._mutate(baseline_commit="different-commit")
        assert envelope1.envelope_hash != envelope2.envelope_hash
        assert envelope2.verify_integrity()
    
    def test_timezone_unambiguous(self):
        """Verify timestamps are offset-aware (contain timezone info)."""
        envelope = self.valid_envelope
        created_dt = datetime.fromisoformat(envelope.created_at_iso)
        expires_dt = datetime.fromisoformat(envelope.expires_at_iso)
        
        # Both should be timezone-aware
        assert created_dt.tzinfo is not None
        assert expires_dt.tzinfo is not None
        
        # Should be UTC (ends with +00:00 or Z)
        assert created_dt.tzinfo.utcoffset(created_dt).total_seconds() == 0
        assert expires_dt.tzinfo.utcoffset(expires_dt).total_seconds() == 0
    
    def _mutate(self, **kwargs) -> L1ActionEnvelope:
        """Create a mutated copy of the valid envelope."""
        data = {
            "program_id": self.valid_envelope.program_id,
            "gate_id": self.valid_envelope.gate_id,
            "authorization_id": self.valid_envelope.authorization_id,
            "principal_id": self.valid_envelope.principal_id,
            "authenticated_provider_account": self.valid_envelope.authenticated_provider_account,
            "repository": self.valid_envelope.repository,
            "resource_type": self.valid_envelope.resource_type,
            "resource_number": self.valid_envelope.resource_number,
            "capability": self.valid_envelope.capability,
            "operation": self.valid_envelope.operation,
            "http_method": self.valid_envelope.http_method,
            "endpoint": self.valid_envelope.endpoint,
            "comment_body": self.valid_envelope.comment_body,
            "comment_body_sha256": self.valid_envelope.comment_body_sha256,
            "consequence_class": self.valid_envelope.consequence_class,
            "max_executions": self.valid_envelope.max_executions,
            "execution_id": self.valid_envelope.execution_id,
            "execution_nonce": self.valid_envelope.execution_nonce,
            "execution_adapter": self.valid_envelope.execution_adapter,
            "execution_entrypoint_id": self.valid_envelope.execution_entrypoint_id,
            "provider_mode": self.valid_envelope.provider_mode,
            "provider_class": self.valid_envelope.provider_class,
            "baseline_commit": self.valid_envelope.baseline_commit,
            "baseline_tree": self.valid_envelope.baseline_tree,
            "baseline_manifest_sha256": self.valid_envelope.baseline_manifest_sha256,
            "created_at_iso": self.valid_envelope.created_at_iso,
            "expires_at_iso": self.valid_envelope.expires_at_iso,
            "authority_snapshot_hash": self.valid_envelope.authority_snapshot_hash,
            "approval_requirement_hash": self.valid_envelope.approval_requirement_hash,
            "envelope_hash": self.valid_envelope.envelope_hash,
        }
        data.update(kwargs)
        return L1ActionEnvelope(**data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])