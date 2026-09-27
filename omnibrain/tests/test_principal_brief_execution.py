"""GOD-1X execution-state brief contract tests (Phase 15)."""

from __future__ import annotations

from omnibrain.principal_brief import (
    BriefAgent,
    BriefExecutionState,
    build_brief,
    build_execution_state,
)


def test_build_execution_state_aggregates_zero_by_default() -> None:
    s = build_execution_state()
    assert s == BriefExecutionState()
    assert s.denied_executions == 0
    assert s.external_effect_blocked == 0


def test_brief_carries_execution_state_additively() -> None:
    state = build_execution_state(
        running_workers=2, execution_failures=1, denied_executions=3,
        external_effect_blocked=1,
    )
    brief = build_brief(
        agents=[BriefAgent("a1", "M1", "GOVERNED_RUNTIME", "ACTIVE")],
        pending_approvals=[],
        security_events=[],
        recent_receipt_ids=[],
        authority_expirations=[],
        memory_change_summary={},
        recommended_principal_decisions=[],
        execution_state=state,
    )
    d = brief.to_dict()
    assert d["execution_state"]["running_workers"] == 2
    assert d["execution_state"]["denied_executions"] == 3
    # additive: absence of execution_state still constructs
    brief2 = build_brief(
        agents=[], pending_approvals=[], security_events=[],
        recent_receipt_ids=[], authority_expirations=[],
        memory_change_summary={}, recommended_principal_decisions=[],
    )
    assert brief2.execution_state is None
    assert "execution_state" in brief2.to_dict()


def test_execution_state_network_fields_default_and_roundtrip() -> None:
    # Defaults: deny policy, policy-level enforcement, available, policy_only cert.
    s = build_execution_state()
    assert s.network_policy_status == "deny"
    assert s.network_enforcement_level == "policy_enforced"
    assert s.network_sandbox_available is True
    assert s.network_certification == "policy_only"

    # Explicit OS-equivalent posture is carried into the brief contract.
    s2 = build_execution_state(
        network_policy_status="deny",
        network_enforcement_level="os_enforced",
        network_sandbox_available=True,
        network_certification="certified",
    )
    d = build_brief(
        agents=[BriefAgent("a1", "M1", "GOVERNED_RUNTIME", "ACTIVE")],
        pending_approvals=[], security_events=[], recent_receipt_ids=[],
        authority_expirations=[], memory_change_summary={},
        recommended_principal_decisions=[], execution_state=s2,
    ).to_dict()
    assert d["execution_state"]["network_enforcement_level"] == "os_enforced"
    assert d["execution_state"]["network_certification"] == "certified"
