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
