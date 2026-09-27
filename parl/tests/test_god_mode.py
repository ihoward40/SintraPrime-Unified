from datetime import datetime, timedelta, timezone

import pytest

from parl.god_mode import ActionRisk, GodModeTier, PrincipalCommandPolicy, PrincipalSession


def session(tier: GodModeTier, *, step_up: bool = False, capabilities=frozenset()):
    return PrincipalSession(
        principal_id="principal-test",
        tier=tier,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        step_up_verified=step_up,
        capabilities=frozenset(capabilities),
    )


def test_ordinary_orchestration_remains_backward_compatible():
    decision = PrincipalCommandPolicy().evaluate(risk=ActionRisk.ORCHESTRATE, session=None)
    assert decision.allowed is True


def test_write_requires_principal_session():
    decision = PrincipalCommandPolicy().evaluate(risk=ActionRisk.WRITE, session=None)
    assert decision.allowed is False
    assert decision.minimum_tier is GodModeTier.CONTROLLED_WRITE


def test_external_action_requires_downstream_approval():
    policy = PrincipalCommandPolicy()
    principal = session(GodModeTier.EXTERNAL_ACTION)
    decision = policy.evaluate(risk=ActionRisk.EXTERNAL, session=principal)
    assert decision.allowed is True
    assert decision.approval_required is True


def test_critical_admin_requires_step_up():
    policy = PrincipalCommandPolicy()
    principal = session(GodModeTier.CRITICAL_ADMIN, step_up=False)
    assert policy.evaluate(risk=ActionRisk.CRITICAL, session=principal).allowed is False

    elevated = session(GodModeTier.CRITICAL_ADMIN, step_up=True)
    decision = policy.evaluate(risk=ActionRisk.CRITICAL, session=elevated)
    assert decision.allowed is True
    assert decision.approval_required is True


def test_non_delegable_capabilities_stay_blocked_even_in_critical_admin():
    principal = session(GodModeTier.CRITICAL_ADMIN, step_up=True)
    decision = PrincipalCommandPolicy().evaluate(
        risk=ActionRisk.CRITICAL,
        session=principal,
        requested_capability="bypass_approval",
    )
    assert decision.allowed is False


def test_expired_session_is_rejected():
    expired = PrincipalSession(
        principal_id="principal-test",
        tier=GodModeTier.CRITICAL_ADMIN,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        step_up_verified=True,
    )
    decision = PrincipalCommandPolicy().evaluate(risk=ActionRisk.WRITE, session=expired)
    assert decision.allowed is False


def test_authorize_specs_denies_external_action_without_approval():
    policy = PrincipalCommandPolicy()
    principal = session(GodModeTier.EXTERNAL_ACTION)
    with pytest.raises(PermissionError, match="downstream approval"):
        policy.authorize_specs(
            [{"risk_level": "external", "payload": {"capability": "send_message"}}],
            session=principal,
        )


def test_authorize_specs_accepts_scoped_external_action_with_approval():
    policy = PrincipalCommandPolicy()
    principal = session(GodModeTier.EXTERNAL_ACTION, capabilities={"send_message"})
    policy.authorize_specs(
        [
            {
                "risk_level": "external",
                "payload": {"capability": "send_message", "approval_granted": True},
            }
        ],
        session=principal,
    )
