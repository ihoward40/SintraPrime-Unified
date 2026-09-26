"""SP-GOD0-MISSION-CONTROL-001 — Principal Brief endpoint + contract tests.

Covers:
- contract shape (sp-principal-brief-v1)
- recommendations-are-proposals-only guard
- fail-closed unavailable payload (no fabricated data)
- permission gating
- strict approval provenance interplay (recommendations can never be consumed)
"""
from __future__ import annotations

import pytest
from datetime import UTC, datetime

from portal.services.principal_brief_service import (
    BRIEF_SCHEMA_VERSION,
    empty_brief_payload,
    normalize_brief,
    recommendation_is_proposal_only,
)


# ---------------------------------------------------------------------------
# Contract shape
# ---------------------------------------------------------------------------

class TestBriefContract:
    def test_normalize_accepts_valid_brief(self):
        raw = {
            "schema_version": BRIEF_SCHEMA_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "available": True,
            "active_missions": ["M-1"],
            "agents": [],
            "recommended_principal_decisions": [],
        }
        out = normalize_brief(raw)
        assert out["schema_version"] == BRIEF_SCHEMA_VERSION
        assert out["active_missions"] == ["M-1"]

    def test_normalize_rejects_wrong_schema_version(self):
        raw = {"schema_version": "sp-principal-brief-v0", "available": True}
        with pytest.raises(ValueError, match="unsupported brief schema_version"):
            normalize_brief(raw)

    def test_unavailable_payload_is_well_formed(self):
        payload = empty_brief_payload(reason="runtime store unavailable")
        assert payload["available"] is False
        assert payload["unavailable_reason"] == "runtime store unavailable"
        assert payload["pending_approvals"] == []
        assert payload["schema_version"] == BRIEF_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Recommendations can never become approvals
# ---------------------------------------------------------------------------

class TestRecommendationSafety:
    def test_recommendation_without_token_is_proposal(self):
        assert recommendation_is_proposal_only({
            "kind": "extend_authority",
            "provenance": "receipt-123",
        }) is True

    def test_recommendation_carrying_approval_reference_is_rejected(self):
        assert recommendation_is_proposal_only({
            "kind": "approve",
            "approval_reference": "GOV-APPROVED-1",
        }) is False

    def test_recommendation_carrying_approval_token_is_rejected(self):
        assert recommendation_is_proposal_only({
            "kind": "approve",
            "approval_token": "tok-xyz",
        }) is False

    def test_recommendation_carrying_approval_id_is_rejected(self):
        assert recommendation_is_proposal_only({
            "kind": "approve",
            "approval_id": "apr-1",
        }) is False


# ---------------------------------------------------------------------------
# Strict approval provenance interplay (fabricated / replayed)
# ---------------------------------------------------------------------------

class TestStrictApprovalProvenance:
    def test_fabricated_approval_reference_not_consumable(self):
        from agent_runtime.delegation import DelegationAuthority

        auth = DelegationAuthority(strict_approval_provenance=True)
        assert auth.consume_approval("MODEL-SAID-APPROVED") is False

    def test_registered_approval_consumable_exactly_once(self):
        from agent_runtime.delegation import DelegationAuthority

        auth = DelegationAuthority(strict_approval_provenance=True)
        auth.register_issued_approval("GOV-APPROVED-1")
        assert auth.consume_approval("GOV-APPROVED-1") is True
        assert auth.consume_approval("GOV-APPROVED-1") is False  # replay

    def test_expired_authority_refused(self):
        from datetime import timedelta

        from agent_runtime.delegation import Delegation, DelegationAuthority
        from agent_runtime.manifest import AgentManifest

        auth = DelegationAuthority(strict_approval_provenance=True)
        past = datetime.now(UTC) - timedelta(hours=1)
        d = Delegation(
            delegation_id="D-X", parent_agent="agent.parent",
            child_agent="agent.worker", mission_id="M-1",
            capabilities=frozenset({"document.create"}),
            issued_at=past - timedelta(hours=1), expires_at=past,
        )
        assert d.is_expired() is True
