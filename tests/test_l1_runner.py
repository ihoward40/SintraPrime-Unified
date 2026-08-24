"""L1 Runner Implementation Tests.

These tests verify the L1 runner implementation behavior offline,
including execution safety controls for timeout reconciliation,
ambiguous result handling, readback verification, second POST suppression,
and evidence chain verification.
"""

from __future__ import annotations

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from sintra_live.github_live.l1_runner import (
    L1CommentRunner,
    L1ExecutionNonce,
    L1ApprovalRecord,
    L1ExecutionStatus,
    L1FailureReason,
    ExecutionState,
    DurableExecutionState,
    run_l1_zero_write_preflight,
)
from sintra_live.github_app.auth import GitHubAppAuthenticator, GitHubAppAuthSession, GitHubAppUserIdentity, GitHubAppInstallation, GitHubAppConfig, GitHubAppTokenResponse
from sintra_live.github_comment.evidence import GitHubCommentEvidenceRecord


def create_mock_session(
    login: str = "ihoward40",
    account_id: int = 139932709,
    installation: GitHubAppInstallation = None
) -> GitHubAppAuthSession:
    """Create a mock authenticated session."""
    user = GitHubAppUserIdentity(
        login=login,
        account_id=account_id,
        avatar_url="https://avatars.githubusercontent.com/u/139932709",
        html_url="https://github.com/ihoward40",
        type="User"
    )
    
    if installation is None:
        installation = GitHubAppInstallation(
            installation_id=155799350,
            account_login="ihoward40",
            account_id=139932709,
            repository_selection="selected",
            repositories=[{"full_name": "ihoward40/SintraPrime-Unified"}],
            permissions={"pull_requests": "write", "metadata": "read"},
            events=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
    
    token = GitHubAppTokenResponse(
        access_token_redacted="ghu_**REDACTED_**",
        token_type="bearer",
        scope="",
        expires_in=3600
    )
    
    config = GitHubAppConfig(client_id="test_client_id")
    
    return GitHubAppAuthSession(
        session_id="test-session",
        config=config,
        token=token,
        user=user,
        installation=installation,
        authenticated_at=time.time(),
        expires_at=time.time() + 3600,
        scopes_granted=[]
    )


def create_mock_authenticator(session: GitHubAppAuthSession) -> GitHubAppAuthenticator:
    """Create a mock authenticator with the given session."""
    auth = GitHubAppAuthenticator(GitHubAppConfig(client_id="test_client_id"))
    auth.session = session
    auth._raw_token = "mock_token"
    return auth


class TestL1ExecutionNonce:
    """Tests for execution nonce."""
    
    def test_nonce_generation(self):
        """Test nonce generation."""
        nonce = L1ExecutionNonce.generate()
        assert nonce.nonce is not None
        assert not nonce.consumed
        assert nonce.consumed_at is None
    
    def test_nonce_consumption(self):
        """Test nonce consumption."""
        nonce = L1ExecutionNonce.generate()
        consumed = nonce.mark_consumed()
        assert consumed.consumed
        assert consumed.consumed_at is not None
        assert consumed.nonce == nonce.nonce


class TestDurableExecutionState:
    """Tests for durable execution state persistence."""
    
    def test_state_creation(self):
        """Test durable state creation."""
        state = DurableExecutionState.create(
            execution_id="test_exec",
            nonce="test_nonce",
            approval_hash="test_approval",
            body_hash="test_body",
            target_repository="ihoward40/SintraPrime-Unified",
            target_pr=285
        )
        assert state.state == ExecutionState.PREPARED
        assert state.execution_id == "test_exec"
        assert state.nonce == "test_nonce"
    
    def test_state_transition(self):
        """Test state transitions."""
        state = DurableExecutionState.create(
            execution_id="test_exec",
            nonce="test_nonce",
            approval_hash="test_approval",
            body_hash="test_body",
            target_repository="ihoward40/SintraPrime-Unified",
            target_pr=285
        )
        new_state = state.with_state(ExecutionState.EXECUTION_STARTED)
        assert new_state.state == ExecutionState.EXECUTION_STARTED
        assert new_state.execution_id == state.execution_id
    
    def test_state_serialization(self):
        """Test state serialization round-trip."""
        state = DurableExecutionState.create(
            execution_id="test_exec",
            nonce="test_nonce",
            approval_hash="test_approval",
            body_hash="test_body",
            target_repository="ihoward40/SintraPrime-Unified",
            target_pr=285
        )
        state = state.with_state(ExecutionState.EXECUTION_STARTED)
        data = state.to_dict()
        restored = DurableExecutionState.from_dict(data)
        assert restored.execution_id == state.execution_id
        assert restored.state == state.state
        assert restored.nonce == state.nonce


class TestL1ApprovalRecord:
    """Tests for approval record."""
    
    def test_approval_creation(self):
        """Test approval record creation."""
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash="test_hash",
            max_executions=1,
            nonce="test_nonce"
        )
        assert approval.approval_id is not None
        assert approval.approval_hash is not None
        assert approval.nonce == "test_nonce"
        assert approval.max_executions == 1
    
    def test_approval_verification(self):
        """Test approval hash verification."""
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash="test_hash",
            max_executions=1,
            nonce="test_nonce"
        )
        assert approval.verify()
    
    def test_approval_tampering_detected(self):
        """Test that approval tampering is detected."""
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash="test_hash",
            max_executions=1,
            nonce="test_nonce"
        )
        # Tamper with a field
        tampered = L1ApprovalRecord(
            approval_id=approval.approval_id,
            principal_id="different_principal",
            account=approval.account,
            repository=approval.repository,
            pr_number=approval.pr_number,
            capability=approval.capability,
            body_hash=approval.body_hash,
            max_executions=approval.max_executions,
            nonce=approval.nonce,
            timestamp=approval.timestamp,
            approval_hash=approval.approval_hash
        )
        assert not tampered.verify()


class TestL1CommentRunnerPreflight:
    """Tests for L1 runner preflight checks."""
    
    def test_preflight_success(self):
        """Test successful preflight."""
        installation = GitHubAppInstallation(
            installation_id=155799350,
            account_login="ihoward40",
            account_id=139932709,
            repository_selection="selected",
            repositories=[{"full_name": "ihoward40/SintraPrime-Unified"}],
            permissions={"pull_requests": "write", "metadata": "read"},
            events=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        session = create_mock_session(installation=installation)
        authenticator = create_mock_authenticator(session)
        
        # Mock the PR access check
        authenticator.verify_pr_access = Mock(return_value={
            "accessible": True,
            "state": "open"
        })
        
        runner = L1CommentRunner(authenticator)
        results = runner.run_preflight_checks()
        
        assert results["authenticated"] is True
        assert results["account_match"] is True
        assert results["installation_match"] is True
        assert results["permissions_match"] is True
        assert results["pr_open"] is True
        assert len(results["errors"]) == 0
    
    def test_preflight_account_mismatch(self):
        """Test preflight fails on account mismatch."""
        installation = GitHubAppInstallation(
            installation_id=155799350,
            account_login="ihoward40",
            account_id=139932709,
            repository_selection="selected",
            repositories=[{"full_name": "ihoward40/SintraPrime-Unified"}],
            permissions={"pull_requests": "write", "metadata": "read"},
            events=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        session = create_mock_session(login="wronguser", installation=installation)
        authenticator = create_mock_authenticator(session)
        
        runner = L1CommentRunner(authenticator)
        results = runner.run_preflight_checks()
        
        assert results["account_match"] is False
        assert any("Account mismatch" in e for e in results["errors"])
    
    def test_preflight_installation_scope_mismatch(self):
        """Test preflight fails on installation scope mismatch."""
        installation = GitHubAppInstallation(
            installation_id=155799350,
            account_login="ihoward40",
            account_id=139932709,
            repository_selection="all",
            repositories=[{"full_name": "ihoward40/SintraPrime-Unified"}, {"full_name": "ihoward40/other-repo"}],
            permissions={"pull_requests": "write", "metadata": "read"},
            events=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        session = create_mock_session(installation=installation)
        authenticator = create_mock_authenticator(session)
        
        runner = L1CommentRunner(authenticator)
        results = runner.run_preflight_checks()
        
        assert results["installation_match"] is False
        assert any("Installation scope mismatch" in e for e in results["errors"])
    
    def test_preflight_permissions_mismatch(self):
        """Test preflight fails on permissions mismatch."""
        installation = GitHubAppInstallation(
            installation_id=155799350,
            account_login="ihoward40",
            account_id=139932709,
            repository_selection="selected",
            repositories=[{"full_name": "ihoward40/SintraPrime-Unified"}],
            permissions={"pull_requests": "write", "contents": "write"},
            events=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        session = create_mock_session(installation=installation)
        authenticator = create_mock_authenticator(session)
        
        runner = L1CommentRunner(authenticator)
        results = runner.run_preflight_checks()
        
        assert results["permissions_match"] is False
        assert any("Permissions mismatch" in e for e in results["errors"])
    
    def test_preflight_pr_closed(self):
        """Test preflight fails when PR is closed."""
        installation = GitHubAppInstallation(
            installation_id=155799350,
            account_login="ihoward40",
            account_id=139932709,
            repository_selection="selected",
            repositories=[{"full_name": "ihoward40/SintraPrime-Unified"}],
            permissions={"pull_requests": "write", "metadata": "read"},
            events=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        session = create_mock_session(installation=installation)
        authenticator = create_mock_authenticator(session)
        authenticator.verify_pr_access = Mock(return_value={
            "accessible": True,
            "state": "closed"
        })
        
        runner = L1CommentRunner(authenticator)
        results = runner.run_preflight_checks()
        
        assert results["pr_open"] is False
        assert any("not accessible or not open" in e for e in results["errors"])


class TestL1ApprovalVerification:
    """Tests for approval verification."""
    
    def test_approval_verification_success(self):
        """Test valid approval verification."""
        installation = GitHubAppInstallation(
            installation_id=155799350,
            account_login="ihoward40",
            account_id=139932709,
            repository_selection="selected",
            repositories=[{"full_name": "ihoward40/SintraPrime-Unified"}],
            permissions={"pull_requests": "write", "metadata": "read"},
            events=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        session = create_mock_session(installation=installation)
        authenticator = create_mock_authenticator(session)
        
        runner = L1CommentRunner(authenticator)
        runner._nonce = L1ExecutionNonce.generate()
        
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash="9fac685186ee96aa62ff60eb818fe65857530f69e188c74997a035e5b5f842b1",
            max_executions=1,
            nonce=runner._nonce.nonce
        )
        
        assert runner.verify_approval(approval) is True
    
    def test_approval_verification_fails_on_stale(self):
        """Test approval verification fails on stale approval."""
        import time
        
        installation = GitHubAppInstallation(
            installation_id=155799350,
            account_login="ihoward40",
            account_id=139932709,
            repository_selection="selected",
            repositories=[{"full_name": "ihoward40/SintraPrime-Unified"}],
            permissions={"pull_requests": "write", "metadata": "read"},
            events=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        session = create_mock_session(installation=installation)
        authenticator = create_mock_authenticator(session)
        
        runner = L1CommentRunner(authenticator)
        runner._nonce = L1ExecutionNonce.generate()
        
        approval = L1ApprovalRecord(
            approval_id="test",
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash="9fac685186ee96aa62ff60eb818fe65857530f69e188c74997a035e5b5f842b1",
            max_executions=1,
            nonce=runner._nonce.nonce,
            timestamp=time.time() - 1000,
            approval_hash="test_hash"
        )
        
        assert runner.verify_approval(approval) is False
    
    def test_approval_verification_fails_on_field_mismatch(self):
        """Test approval verification fails on field mismatch."""
        installation = GitHubAppInstallation(
            installation_id=155799350,
            account_login="ihoward40",
            account_id=139932709,
            repository_selection="selected",
            repositories=[{"full_name": "ihoward40/SintraPrime-Unified"}],
            permissions={"pull_requests": "write", "metadata": "read"},
            events=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        session = create_mock_session(installation=installation)
        authenticator = create_mock_authenticator(session)
        
        runner = L1CommentRunner(authenticator)
        runner._nonce = L1ExecutionNonce.generate()
        
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="wronguser",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash="9fac685186ee96aa62ff60eb818fe65857530f69e188c74997a035e5b5f842b1",
            max_executions=1,
            nonce=runner._nonce.nonce
        )
        
        assert runner.verify_approval(approval) is False


class TestL1ExecutionSafetyControls:
    """Tests for the five execution safety controls."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.installation = GitHubAppInstallation(
            installation_id=155799350,
            account_login="ihoward40",
            account_id=139932709,
            repository_selection="selected",
            repositories=[{"full_name": "ihoward40/SintraPrime-Unified"}],
            permissions={"pull_requests": "write", "metadata": "read"},
            events=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        self.session = create_mock_session(installation=self.installation)
        self.authenticator = create_mock_authenticator(self.session)
        self.authenticator.verify_pr_access = Mock(return_value={
            "accessible": True,
            "state": "open"
        })
        self.runner = L1CommentRunner(self.authenticator)
    
    def test_timeout_after_possible_send_reconciles_without_retry(self):
        """Test timeout after possible send triggers reconciliation without retry."""
        # Setup
        self.runner._nonce = L1ExecutionNonce.generate()
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash=self.runner.AUTHORIZED_BODY_HASH,
            max_executions=1,
            nonce=self.runner._nonce.nonce
        )
        self.runner._approval = approval
        
        # Mock the duplicate check to return a matching comment
        mock_comment = {
            "id": 12345,
            "body": self.runner.AUTHORIZED_COMMENT_BODY,
            "user": {"login": "ihoward40"},
            "html_url": "https://github.com/ihoward40/SintraPrime-Unified/pull/285#comment-12345",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        with patch.object(self.runner, 'check_duplicate_comment', return_value={"found": True, **mock_comment}):
            # Simulate timeout result
            timeout_result = {
                "success": False,
                "error": "TIMEOUT_BEFORE_OUTCOME - reconciliation required",
                "timeout": True,
                "provider_may_have_sent": True
            }
            
            with patch.object(self.runner, 'execute_comment_post', return_value=timeout_result):
                with patch.object(self.runner, 'verify_readback') as mock_verify:
                    mock_verify.return_value = {"all_verified": True, "author_verified": True, "body_hash_verified": True}
                    
                    result = self.runner.execute_live_post()
                    
                    # Should succeed via reconciliation
                    assert result.status == L1ExecutionStatus.AUTHORITY_CONSUMED
                    assert result.failure_reason is None
                    # Verify NO retry was attempted (execute_comment_post called once)
                    assert self.runner.execute_comment_post.call_count == 1
    
    def test_timeout_no_match_stops_unverified(self):
        """Test timeout with no matching comment stops as UNVERIFIED."""
        self.runner._nonce = L1ExecutionNonce.generate()
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash=self.runner.AUTHORIZED_BODY_HASH,
            max_executions=1,
            nonce=self.runner._nonce.nonce
        )
        self.runner._approval = approval
        
        # Mock duplicate check to return no match
        with patch.object(self.runner, 'check_duplicate_comment', return_value={"found": False}):
            timeout_result = {
                "success": False,
                "error": "TIMEOUT_BEFORE_OUTCOME - reconciliation required",
                "timeout": True,
                "provider_may_have_sent": True
            }
            
            with patch.object(self.runner, 'execute_comment_post', return_value=timeout_result):
                result = self.runner.execute_live_post()
                
                assert result.status == L1ExecutionStatus.FAILED
                assert result.failure_reason == L1FailureReason.TIMEOUT_BEFORE_OUTCOME
    
    def test_timeout_exact_match_verifies(self):
        """Test timeout with exact matching comment verifies successfully."""
        self.runner._nonce = L1ExecutionNonce.generate()
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash=self.runner.AUTHORIZED_BODY_HASH,
            max_executions=1,
            nonce=self.runner._nonce.nonce
        )
        self.runner._approval = approval
        
        mock_comment = {
            "id": 12345,
            "body": self.runner.AUTHORIZED_COMMENT_BODY,
            "user": {"login": "ihoward40"},
            "html_url": "https://github.com/ihoward40/SintraPrime-Unified/pull/285#comment-12345",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        with patch.object(self.runner, 'check_duplicate_comment', return_value={"found": True, **mock_comment}):
            timeout_result = {
                "success": False,
                "error": "TIMEOUT_BEFORE_OUTCOME - reconciliation required",
                "timeout": True,
                "provider_may_have_sent": True
            }
            
            with patch.object(self.runner, 'execute_comment_post', return_value=timeout_result):
                with patch.object(self.runner, 'verify_readback') as mock_verify:
                    mock_verify.return_value = {"all_verified": True, "author_verified": True, "body_hash_verified": True}
                    
                    result = self.runner.execute_live_post()
                    
                    assert result.status == L1ExecutionStatus.AUTHORITY_CONSUMED
    
    def test_ambiguous_provider_result_never_retries(self):
        """Test ambiguous provider result never retries."""
        self.runner._nonce = L1ExecutionNonce.generate()
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash=self.runner.AUTHORIZED_BODY_HASH,
            max_executions=1,
            nonce=self.runner._nonce.nonce
        )
        self.runner._approval = approval
        
        ambiguous_result = {
            "success": False,
            "error": "HTTP 500: Internal Server Error"
        }
        
        with patch.object(self.runner, 'execute_comment_post', return_value=ambiguous_result) as mock_post:
            result = self.runner.execute_live_post()
            
            assert result.status == L1ExecutionStatus.FAILED
            assert result.failure_reason == L1FailureReason.PROVIDER_RESPONSE_AMBIGUOUS
            # Verify only one POST attempt
            assert mock_post.call_count == 1
    
    def test_readback_wrong_body_fails(self):
        """Test readback with wrong body fails verification."""
        self.runner._nonce = L1ExecutionNonce.generate()
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash=self.runner.AUTHORIZED_BODY_HASH,
            max_executions=1,
            nonce=self.runner._nonce.nonce
        )
        self.runner._approval = approval
        
        # Successful POST but readback returns wrong body
        provider_result = {
            "success": True,
            "response": {"id": 12345, "body": "wrong body"}
        }
        
        with patch.object(self.runner, 'execute_comment_post', return_value=provider_result):
            with patch.object(self.runner, 'verify_readback') as mock_verify:
                mock_verify.return_value = {
                    "all_verified": False,
                    "author_verified": True,
                    "body_hash_verified": False,
                    "author": "ihoward40",
                    "body": "wrong body",
                    "body_hash": "different_hash"
                }
                
                result = self.runner.execute_live_post()
                
                assert result.status == L1ExecutionStatus.FAILED
                assert result.failure_reason == L1FailureReason.READBACK_VERIFICATION_FAILED
    
    def test_readback_wrong_author_fails(self):
        """Test readback with wrong author fails verification."""
        self.runner._nonce = L1ExecutionNonce.generate()
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash=self.runner.AUTHORIZED_BODY_HASH,
            max_executions=1,
            nonce=self.runner._nonce.nonce
        )
        self.runner._approval = approval
        
        provider_result = {"success": True, "response": {"id": 12345}}
        
        with patch.object(self.runner, 'execute_comment_post', return_value=provider_result):
            with patch.object(self.runner, 'verify_readback') as mock_verify:
                mock_verify.return_value = {
                    "all_verified": False,
                    "author_verified": False,
                    "body_hash_verified": True,
                    "author": "wronguser"
                }
                
                result = self.runner.execute_live_post()
                
                assert result.status == L1ExecutionStatus.FAILED
                assert result.failure_reason == L1FailureReason.READBACK_VERIFICATION_FAILED
    
    def test_readback_duplicate_matches_fail(self):
        """Test readback with multiple matching comments fails."""
        self.runner._nonce = L1ExecutionNonce.generate()
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash=self.runner.AUTHORIZED_BODY_HASH,
            max_executions=1,
            nonce=self.runner._nonce.nonce
        )
        self.runner._approval = approval
        
        provider_result = {"success": True, "response": {"id": 12345}}
        
        with patch.object(self.runner, 'execute_comment_post', return_value=provider_result):
            with patch.object(self.runner, 'verify_readback') as mock_verify:
                mock_verify.return_value = {
                    "all_verified": False,
                    "error": "Multiple matching comments found"
                }
                
                result = self.runner.execute_live_post()
                
                assert result.status == L1ExecutionStatus.FAILED
                assert result.failure_reason == L1FailureReason.READBACK_VERIFICATION_FAILED
    
    def test_restart_after_attempt_suppresses_second_post(self):
        """Test restart after attempt suppresses second POST."""
        self.runner._nonce = L1ExecutionNonce.generate()
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash=self.runner.AUTHORIZED_BODY_HASH,
            max_executions=1,
            nonce=self.runner._nonce.nonce
        )
        self.runner._approval = approval
        
        # Create durable state file
        durable = DurableExecutionState.create(
            execution_id=self.runner.execution_id,
            nonce=self.runner._nonce.nonce,
            approval_hash=approval.approval_hash,
            body_hash=self.runner.AUTHORIZED_BODY_HASH,
            target_repository=self.runner.AUTHORIZED_REPOSITORY,
            target_pr=self.runner.AUTHORIZED_PR_NUMBER
        )
        durable = durable.with_state(ExecutionState.PROVIDER_ATTEMPT_RECORDED)
        self.runner._save_durable_state(durable)
        
        # Create new runner instance (simulating restart)
        new_runner = L1CommentRunner(self.authenticator)
        new_runner.execution_id = self.runner.execution_id
        new_runner._nonce = self.runner._nonce
        new_runner._approval = self.runner._approval
        
        # Mock duplicate check finding the comment
        mock_comment = {
            "id": 12345,
            "body": self.runner.AUTHORIZED_COMMENT_BODY,
            "user": {"login": "ihoward40"},
            "html_url": "https://github.com/ihoward40/SintraPrime-Unified/pull/285#comment-12345",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        with patch.object(new_runner, 'check_duplicate_comment', return_value={"found": True, **mock_comment}):
            with patch.object(new_runner, 'verify_readback') as mock_verify:
                mock_verify.return_value = {"all_verified": True}
                with patch.object(new_runner, 'execute_comment_post') as mock_post:
                    result = new_runner.execute_live_post()
                    
                    # Should NOT call execute_comment_post (reconciliation path)
                    assert mock_post.call_count == 0
                    assert result.status == L1ExecutionStatus.AUTHORITY_CONSUMED
    
    def test_consumed_nonce_cannot_execute_again(self):
        """Test consumed nonce cannot execute again."""
        self.runner._nonce = L1ExecutionNonce.generate()
        approval = L1ApprovalRecord.create(
            principal_id="principal-001",
            account="ihoward40",
            repository="ihoward40/SintraPrime-Unified",
            pr_number=285,
            capability="provider.github-issue-comment-create-v1",
            body_hash=self.runner.AUTHORIZED_BODY_HASH,
            max_executions=1,
            nonce=self.runner._nonce.nonce
        )
        self.runner._approval = approval
        
        # Mark nonce as consumed
        self.runner._nonce = self.runner._nonce.mark_consumed()
        
        result = self.runner.execute_live_post()
        
        assert result.status == L1ExecutionStatus.FAILED
        assert result.failure_reason == L1FailureReason.NONCE_ALREADY_CONSUMED
    
    def test_evidence_chain_validates(self):
        """Test evidence chain hash linkage verification."""
        from sintra_live.github_comment.evidence import GitHubCommentEvidenceChain
        
        chain = GitHubCommentEvidenceChain(chain_id="test-chain")
        
        chain.append("event1", "exec1", "binding1", "principal1", {"data": "test1"})
        chain.append("event2", "exec1", "binding1", "principal1", {"data": "test2"})
        chain.append("event3", "exec1", "binding1", "principal1", {"data": "test3"})
        
        assert chain.verify_chain() is True
        root = chain.get_chain_root()
        assert root is not None
        assert len(root) == 64  # SHA256 hex
    
    def test_evidence_chain_tamper_detected(self):
        """Test evidence chain tampering is detected."""
        from sintra_live.github_comment.evidence import GitHubCommentEvidenceChain
        
        chain = GitHubCommentEvidenceChain(chain_id="test-chain")
        
        chain.append("event1", "exec1", "binding1", "principal1", {"data": "test1"})
        chain.append("event2", "exec1", "binding1", "principal1", {"data": "test2"})
        
        # Tamper with a record by replacing it
        original = chain.records[0]
        tampered = GitHubCommentEvidenceRecord(
            record_id=original.record_id,
            event_type=original.event_type,
            action_id=original.action_id,
            binding_id=original.binding_id,
            principal_id=original.principal_id,
            payload_hash="tampered_hash",
            timestamp=original.timestamp,
            previous_record_hash=original.previous_record_hash
        )
        chain.records[0] = tampered
        
        assert chain.verify_chain() is False
    
    def test_broken_previous_hash_detected(self):
        """Test broken previous hash in chain is detected."""
        from sintra_live.github_comment.evidence import GitHubCommentEvidenceChain
        
        chain = GitHubCommentEvidenceChain(chain_id="test-chain")
        
        chain.append("event1", "exec1", "binding1", "principal1", {"data": "test1"})
        chain.append("event2", "exec1", "binding1", "principal1", {"data": "test2"})
        
        # Break the hash linkage
        original = chain.records[1]
        tampered = GitHubCommentEvidenceRecord(
            record_id=original.record_id,
            event_type=original.event_type,
            action_id=original.action_id,
            binding_id=original.binding_id,
            principal_id=original.principal_id,
            payload_hash=original.payload_hash,
            timestamp=original.timestamp,
            previous_record_hash="broken_hash"
        )
        chain.records[1] = tampered
        
        assert chain.verify_chain() is False


class TestL1DuplicateDetection:
    """Tests for duplicate comment detection."""
    
    def test_duplicate_detection(self):
        """Test duplicate comment detection logic."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])