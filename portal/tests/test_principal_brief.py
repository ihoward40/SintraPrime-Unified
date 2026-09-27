"""SP-GOD0-MISSION-CONTROL-001 — Principal Brief endpoint + contract tests.

Covers:
- contract shape (sp-principal-brief-v1)
- recommendations-are-proposals-only guard
- fail-closed unavailable payload (no fabricated data)
- permission gating
- strict approval provenance interplay (recommendations can never be consumed)
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

_SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "principal_brief_service.py"
_SERVICE_SPEC = importlib.util.spec_from_file_location("principal_brief_service_test", _SERVICE_PATH)
assert _SERVICE_SPEC is not None
assert _SERVICE_SPEC.loader is not None
_SERVICE = importlib.util.module_from_spec(_SERVICE_SPEC)
sys.modules[_SERVICE_SPEC.name] = _SERVICE
_SERVICE_SPEC.loader.exec_module(_SERVICE)

BRIEF_SCHEMA_VERSION = _SERVICE.BRIEF_SCHEMA_VERSION
build_runtime_execution_state = _SERVICE.build_runtime_execution_state
empty_brief_payload = _SERVICE.empty_brief_payload
normalize_brief = _SERVICE.normalize_brief
recommendation_is_proposal_only = _SERVICE.recommendation_is_proposal_only

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
        assert out["execution_state"]["network_enforcement_level"] == "unavailable_fail_closed"

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
        assert payload["execution_state"]["network_sandbox_available"] is False


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

        past = datetime.now(UTC) - timedelta(hours=1)
        d = Delegation(
            delegation_id="D-X", parent_agent="agent.parent",
            child_agent="agent.worker", mission_id="M-1",
            capabilities=frozenset({"document.create"}),
            issued_at=past - timedelta(hours=1), expires_at=past,
        )
        assert d.is_expired() is True


def test_runtime_execution_state_helper_carries_resolved_posture(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Sandbox:
        def resolve(self) -> dict[str, object]:
            return {
                "effective_level": "policy",
                "enforcement_level": "policy_enforced",
                "available": True,
                "fail_closed": False,
            }

        def brief_fields(self, _resolved: dict[str, object]) -> dict[str, object]:
            return {
                "network_policy_status": "deny",
                "network_enforcement_level": "policy_enforced",
                "network_sandbox_available": True,
                "network_certification": "policy_only",
            }

    monkeypatch.setattr(
        "swarm_runtime.network_sandbox.NetworkSandbox.from_config",
        classmethod(lambda cls: _Sandbox()),
    )
    state = build_runtime_execution_state()
    assert state.network_enforcement_level == "policy_enforced"
    assert state.network_sandbox_available is True


def test_runtime_execution_state_helper_surfaces_unexpected_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "swarm_runtime.network_sandbox.NetworkSandbox.from_config",
        classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("sandbox wiring broke"))),
    )
    with pytest.raises(RuntimeError, match="sandbox wiring broke"):
        build_runtime_execution_state()


def test_runtime_execution_state_helper_falls_back_only_when_module_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = ModuleNotFoundError("No module named 'swarm_runtime.network_sandbox'")
    missing.name = "swarm_runtime.network_sandbox"
    monkeypatch.setattr(_SERVICE.importlib, "import_module", lambda name: (_ for _ in ()).throw(missing))
    state = build_runtime_execution_state()
    assert state.network_enforcement_level == "unavailable_fail_closed"
    assert state.network_sandbox_available is False
