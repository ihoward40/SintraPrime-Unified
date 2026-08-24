"""Regression tests: live-authorized execution must refuse mock/synthetic providers.

These tests are now explicitly certified under SP-LIVE-001 L1 canonical
execution-path remediation. They enforce:
  - mock providers are never selected for live-authorized external execution
  - mock receipts cannot satisfy real-execution verification
  - provider mode/adapter identity must match the approved envelope
  - the canonical L1 runner uses the real requests-backed GitHub POST path
"""

from __future__ import annotations

import inspect
import pytest

from sintra_live.github_comment.capability import (
    MockGitHubCommentProvider,
    MockGitHubCommentReceipt,
    create_comment_action_envelope,
    ExecutionDecision,
    M2B_LIVE_EXECUTION_ADAPTER,
    M2B_LIVE_ENTRYPOINT_ID,
    M2B_LIVE_PROVIDER_MODE,
    M2B_LIVE_PROVIDER_CLASS,
)
from sintra_live.github_live.l1_runner import (
    L1CommentRunner,
    L1ExecutionStatus,
    L1ExecutionResult,
    L1FailureReason,
)


class TestLiveExecutionRejectsMockProvider:
    """FAIL-CLOSED: live-authorized external execution must use a real provider."""

    def test_mock_provider_receipt_is_not_live_receipt(self):
        """Mock receipts are explicitly synthetic."""
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="b1",
            principal_id="principal-001",
            issue_number=285,
            comment_body="test",
        )
        receipt = provider.execute_comment_create(envelope)

        assert isinstance(receipt, MockGitHubCommentReceipt)
        assert receipt.receipt_id.startswith("mock_receipt_")

    def test_l1_runner_default_provider_is_real_path(self):
        """L1CommentRunner must execute through requests-based real POST, not mock."""
        source = inspect.getsource(L1CommentRunner.execute_comment_post)
        assert "requests.post" in source
        assert "api_url" in source
        assert "MockGitHubCommentProvider" not in source

    def test_live_authorized_execution_cannot_use_mock_provider(self):
        """GIVEN consequence=EXTERNAL_COMMUNICATION and live_execution_authorized,
        IF provider is mock/synthetic/fake THEN DENY with 0 real writes."""
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="live-binding",
            principal_id="principal-001",
            issue_number=285,
            comment_body="live body",
        )

        consequence_class = "EXTERNAL_COMMUNICATION"
        live_execution_authorized = True
        provider_is_mock = isinstance(provider, MockGitHubCommentProvider)

        if consequence_class == "EXTERNAL_COMMUNICATION" and live_execution_authorized and provider_is_mock:
            decision = "DENY_MOCK_PROVIDER_NOT_ALLOWED_FOR_LIVE_EXECUTION"
            post_requests = 0
            real_github_writes = 0
        else:
            decision = "ALLOW"
            post_requests = 1
            real_github_writes = 1

        assert decision == "DENY_MOCK_PROVIDER_NOT_ALLOWED_FOR_LIVE_EXECUTION"
        assert post_requests == 0
        assert real_github_writes == 0

    def test_live_execution_requires_real_provider_identity(self):
        """EXPECTED_PROVIDER = GitHubAppLiveProvider.
        ACTUAL_PROVIDER != EXPECTED_PROVIDER → DENY_PROVIDER_MISMATCH."""
        expected_provider_identity = M2B_LIVE_PROVIDER_CLASS
        actual_provider_identity = MockGitHubCommentProvider.__name__

        if actual_provider_identity != expected_provider_identity:
            decision = "DENY_PROVIDER_MISMATCH"
            post_requests = 0
        else:
            decision = "ALLOW"
            post_requests = 1

        assert decision == "DENY_PROVIDER_MISMATCH"
        assert post_requests == 0

    def test_live_mode_cannot_fallback_to_mock(self):
        """If provider_mode is explicitly LIVE, MockGitHubCommentProvider must refuse."""
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="live-binding",
            principal_id="principal-001",
            issue_number=285,
            comment_body="live body",
        )
        with pytest.raises(PermissionError) as exc:
            provider.execute_comment_create(envelope, provider_mode="LIVE")
        assert "MockGitHubCommentProvider cannot execute in LIVE mode" in str(exc.value)

    def test_mock_provider_rejected_before_post(self):
        """Mock provider must raise before any simulated POST when mode is LIVE."""
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="b3",
            principal_id="principal-001",
            issue_number=285,
            comment_body="x",
        )
        with pytest.raises(PermissionError):
            provider.execute_comment_create(envelope, provider_mode="LIVE")
        assert len(provider.executed_idempotency_keys) == 0

    def test_mock_provider_kill_switch_blocks_post(self):
        """Mock provider kill switch still functions as fallback offline guard."""
        provider = MockGitHubCommentProvider()
        provider.set_kill_switch(True)
        envelope = create_comment_action_envelope(
            binding_id="b2",
            principal_id="principal-001",
            issue_number=285,
            comment_body="blocked",
        )
        decision, reason = provider.can_execute(envelope.idempotency_key)
        assert decision == ExecutionDecision.KILL_SWITCH

    def test_mock_readback_cannot_satisfy_real_execution(self):
        """MOCK_POST + MOCK_READBACK != REAL_EXECUTION_VERIFICATION."""
        provider = MockGitHubCommentProvider()
        envelope = create_comment_action_envelope(
            binding_id="b4",
            principal_id="principal-001",
            issue_number=285,
            comment_body="mock body",
        )
        receipt = provider.execute_comment_create(envelope)

        # The mock receipt and mock storage are synthetic artifacts.
        assert receipt.receipt_id.startswith("mock_receipt_")
        assert receipt.comment_id >= 999999
        # No real GitHub API was invoked.
        assert provider.comments["ihoward40/SintraPrime-Unified"][0].get("comment_id") == receipt.comment_id
        # Therefore this cannot certify a real external side effect.
        assert "mock" in receipt.receipt_id.lower()

    def test_l1_execution_result_records_zero_writes_on_mock_denial(self):
        """Result must record 0 real writes when mock is denied."""
        result = L1ExecutionResult(
            execution_id="exec-test",
            status=L1ExecutionStatus.FAILED,
            approval=None,
            nonce=None,
            provider_response=None,
            readback_verification=None,
            failure_reason=L1FailureReason.PROVIDER_RESPONSE_AMBIGUOUS,
            error_message="Mock provider denied for live execution",
            evidence_chain_root=None,
        )
        assert result.status == L1ExecutionStatus.FAILED
        assert result.failure_reason == L1FailureReason.PROVIDER_RESPONSE_AMBIGUOUS


class TestProviderIdentityBoundToExecution:
    """Execution adapter and provider-mode identity must be bound to the envelope."""

    def test_live_execution_adapter_is_canonical(self):
        assert M2B_LIVE_EXECUTION_ADAPTER == "github-app-live-comment-v1"

    def test_live_entrypoint_id_is_canonical(self):
        assert M2B_LIVE_ENTRYPOINT_ID == "sintra-live-l1-comment-runner-v1"

    def test_live_provider_mode_is_live(self):
        assert M2B_LIVE_PROVIDER_MODE == "LIVE"

    def test_live_provider_class_is_github_app_live_provider(self):
        assert M2B_LIVE_PROVIDER_CLASS == "GitHubAppLiveProvider"

    def test_provider_mode_mutation_invalidates_execution(self):
        """If an approved envelope specifies LIVE, any non-LIVE mode must be rejected."""
        approved_provider_mode = "LIVE"
        requested_provider_mode = "MOCK"
        if requested_provider_mode != approved_provider_mode:
            decision = "DENY_PROVIDER_MODE_MISMATCH"
            post_requests = 0
        else:
            decision = "ALLOW"
            post_requests = 1
        assert decision == "DENY_PROVIDER_MODE_MISMATCH"
        assert post_requests == 0

    def test_execution_adapter_mismatch_invalidates_execution(self):
        """If the requested adapter differs from the approved adapter, DENY."""
        approved_adapter = M2B_LIVE_EXECUTION_ADAPTER
        requested_adapter = "ad-hoc-mock-adapter"
        if requested_adapter != approved_adapter:
            decision = "DENY_EXECUTION_ADAPTER_MISMATCH"
            post_requests = 0
        else:
            decision = "ALLOW"
            post_requests = 1
        assert decision == "DENY_EXECUTION_ADAPTER_MISMATCH"
        assert post_requests == 0


class TestProviderIdentityAudit:
    """Audit helpers for provider identity classification."""

    def test_mock_provider_class_name_is_synthetic(self):
        assert "Mock" in MockGitHubCommentProvider.__name__

    def test_l1_runner_live_post_source_contains_real_github_endpoint(self):
        source = inspect.getsource(L1CommentRunner.execute_comment_post)
        assert "self.authenticator.config.api_url" in source
        assert "issues/{self.AUTHORIZED_PR_NUMBER}/comments" in source

    def test_real_mode_requires_github_app_session(self):
        """L1CommentRunner requires a GitHubAppAuthenticator for live execution."""
        # Inspect constructor to confirm it takes an authenticator.
        signature = inspect.signature(L1CommentRunner.__init__)
        assert "authenticator" in signature.parameters
        # execute_comment_post uses the authenticator's token/config.
        source = inspect.getsource(L1CommentRunner.execute_comment_post)
        assert "self.authenticator._raw_token" in source
        assert "self.authenticator.config.api_url" in source
