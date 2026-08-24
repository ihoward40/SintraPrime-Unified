import pytest
import time
import json
from unittest.mock import Mock

from sintra_live.github_live.l1_runner import L1CommentRunner, L1ExecutionNonce, DurableExecutionState
from sintra_live.github_app.auth import (
    GitHubAppAuthenticator,
    GitHubAppAuthSession,
    GitHubAppUserIdentity,
    GitHubAppInstallation,
    GitHubAppConfig,
    GitHubAppTokenResponse,
)


def create_mock_session(
    login: str = "ihoward40",
    account_id: int = 139932709,
    installation: GitHubAppInstallation = None
) -> GitHubAppAuthSession:
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
    auth = GitHubAppAuthenticator(GitHubAppConfig(client_id="test_client_id"))
    auth.session = session
    auth._raw_token = "mock_token"
    return auth


class TestL1ExecutionIdentityBinding:
    """Tests for envelope-bound execution identity in the canonical live runner."""

    def test_live_runner_accepts_approved_execution_id(self):
        """Live mode must accept an externally supplied execution_id."""
        session = create_mock_session()
        auth = create_mock_authenticator(session)
        runner = L1CommentRunner(
            authenticator=auth,
            live_execution=True,
            execution_id="approved-exec-id-123",
            execution_nonce="approved-nonce-456",
        )
        assert runner.execution_id == "approved-exec-id-123"
        assert runner._bound_execution_id == "approved-exec-id-123"

    def test_live_runner_accepts_approved_execution_nonce(self):
        """Live mode must accept an externally supplied execution_nonce."""
        session = create_mock_session()
        auth = create_mock_authenticator(session)
        runner = L1CommentRunner(
            authenticator=auth,
            live_execution=True,
            execution_id="approved-exec-id-123",
            execution_nonce="approved-nonce-456",
        )
        assert runner._nonce is not None
        assert runner._nonce.nonce == "approved-nonce-456"
        assert runner._nonce.consumed is False
        assert runner._bound_execution_nonce == "approved-nonce-456"

    def test_live_runner_rejects_missing_execution_id(self):
        """Live mode without execution_id must fail closed."""
        session = create_mock_session()
        auth = create_mock_authenticator(session)
        with pytest.raises(PermissionError, match="LIVE_EXECUTION_ID_REQUIRED"):
            L1CommentRunner(
                authenticator=auth,
                live_execution=True,
                execution_id=None,
                execution_nonce="approved-nonce-456",
            )

    def test_live_runner_rejects_missing_nonce(self):
        """Live mode without execution_nonce must fail closed."""
        session = create_mock_session()
        auth = create_mock_authenticator(session)
        with pytest.raises(PermissionError, match="LIVE_EXECUTION_NONCE_REQUIRED"):
            L1CommentRunner(
                authenticator=auth,
                live_execution=True,
                execution_id="approved-exec-id-123",
                execution_nonce=None,
            )

    def test_live_runner_rejects_execution_id_mismatch(self):
        """Runtime identity mismatch against the approved envelope must be denied."""
        session = create_mock_session()
        auth = create_mock_authenticator(session)
        runner = L1CommentRunner(
            authenticator=auth,
            live_execution=True,
            execution_id="approved-exec-id-123",
            execution_nonce="approved-nonce-456",
        )
        runner.execution_id = "tampered-id"
        assert not runner._verify_identity_binding("approved-exec-id-123", "approved-nonce-456")

    def test_live_runner_rejects_nonce_mismatch(self):
        """Runtime nonce mismatch against the approved envelope must be denied."""
        session = create_mock_session()
        auth = create_mock_authenticator(session)
        runner = L1CommentRunner(
            authenticator=auth,
            live_execution=True,
            execution_id="approved-exec-id-123",
            execution_nonce="approved-nonce-456",
        )
        runner._nonce = L1ExecutionNonce(nonce="tampered-nonce", created_at=time.time())
        assert not runner._verify_identity_binding("approved-exec-id-123", "approved-nonce-456")

    def test_live_runner_does_not_autogenerate_identity_in_live_mode(self):
        """Live mode must never autogenerate execution_id or nonce."""
        session = create_mock_session()
        auth = create_mock_authenticator(session)
        runner = L1CommentRunner(
            authenticator=auth,
            live_execution=True,
            execution_id="approved-exec-id-123",
            execution_nonce="approved-nonce-456",
        )
        assert runner.execution_id == "approved-exec-id-123"
        assert runner._nonce.nonce == "approved-nonce-456"

    def test_mock_or_offline_mode_may_autogenerate_identity_if_previously_supported(self):
        """Offline/mock mode may still autogenerate identity for backward compatibility."""
        session = create_mock_session()
        auth = create_mock_authenticator(session)
        runner = L1CommentRunner(authenticator=auth)
        assert runner.execution_id is not None
        assert runner._nonce is not None
        assert runner._nonce.nonce is not None

    def test_identity_propagated_to_preflight_evidence(self):
        """Bound execution_id/nonce must appear in preflight evidence via action_id and record hash inputs."""
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
        auth = create_mock_authenticator(session)
        auth.verify_pr_access = Mock(return_value={"accessible": True, "state": "open"})
        runner = L1CommentRunner(
            authenticator=auth,
            live_execution=True,
            execution_id="approved-exec-id-123",
            execution_nonce="approved-nonce-456",
        )
        runner.run_preflight_checks()
        record = runner.evidence_chain.records[0]
        assert record.action_id == "approved-exec-id-123"
        # payload_hash is a SHA-256 of JSON that includes execution_id and nonce keys.
        assert record.payload_hash is not None
        assert len(record.payload_hash) == 64

    def test_identity_propagated_to_durable_state(self):
        """Durable execution state must carry the bound execution_id and nonce."""
        session = create_mock_session()
        auth = create_mock_authenticator(session)
        runner = L1CommentRunner(
            authenticator=auth,
            live_execution=True,
            execution_id="approved-exec-id-123",
            execution_nonce="approved-nonce-456",
        )
        durable = DurableExecutionState.create(
            execution_id=runner.execution_id,
            nonce=runner._nonce.nonce,
            approval_hash="test-approval",
            body_hash=runner.AUTHORIZED_BODY_HASH,
            target_repository=runner.AUTHORIZED_REPOSITORY,
            target_pr=runner.AUTHORIZED_PR_NUMBER
        )
        assert durable.execution_id == "approved-exec-id-123"
        assert durable.nonce == "approved-nonce-456"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
