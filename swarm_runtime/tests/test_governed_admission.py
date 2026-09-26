"""GOD-1X governed admission gate + taxonomy tests.

Phases 1 (admission), 2 (execution class), 9 (network), 14 (severity),
23 (external-effect firewall).
"""

from __future__ import annotations

from swarm_runtime.governed_execution import (
    DENIED_EXECUTION_CLASSES,
    AuthorityEnvelope,
    ExecutionAdmissionGate,
    ExecutionClass,
    ExecutionRequest,
    Severity,
)


def _env(**overrides: bool) -> AuthorityEnvelope:
    base = {
        "mission_id": "M1", "swarm_id": "S1", "task_id": "T1", "agent_id": "A1",
        "authority_id": "AUTH1", "role_id": "code_search", "context_package_id": "CTX1",
        "mission_active": True, "swarm_authorized": True, "task_ready": True,
        "agent_authorized": True, "authority_valid": True, "context_valid": True,
        "role_allowed": True, "resource_allowed": True, "revoked": False,
    }
    base.update(overrides)
    return AuthorityEnvelope(**base)


def _req(effect_class: str = "read_only_inspection", **kw: object) -> ExecutionRequest:
    base = {
        "execution_request_id": "R1", "mission_id": "M1", "swarm_id": "S1", "task_id": "T1",
        "agent_id": "A1", "authority_id": "AUTH1", "context_package_id": "CTX1",
        "role_id": "code_search", "working_directory": ".", "timeout_seconds": 30,
        "effect_class": effect_class,
    }
    base.update(kw)
    return ExecutionRequest(**base)


def test_admit_read_only_allowed() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(), _env())
    assert d.allowed, d.reasons
    assert d.reasons == ["ADMITTED"]


def test_admit_missing_mission_active_denies() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(), _env(mission_active=False))
    assert not d.allowed
    assert "MISSION_NOT_ACTIVE" in d.reasons


def test_admit_missing_swarm_auth_denies() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(), _env(swarm_authorized=False))
    assert not d.allowed
    assert "SWARM_NOT_AUTHORIZED" in d.reasons


def test_admit_revoked_denies() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(), _env(revoked=True))
    assert not d.allowed
    assert "AUTHORITY_REVOKED" in d.reasons


def test_admit_identity_mismatch_denies() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(mission_id="M2"), _env())
    assert not d.allowed
    assert "MISSION_ID_MISMATCH" in d.reasons


def test_admit_external_effect_class_denied() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(effect_class=ExecutionClass.EXTERNAL_EFFECT_EXECUTION.value), _env())
    assert not d.allowed
    assert any(r.startswith("EXECUTION_CLASS_DENIED") for r in d.reasons)


def test_admit_privileged_class_denied() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(effect_class=ExecutionClass.PRIVILEGED_EXECUTION.value), _env())
    assert not d.allowed


def test_admit_network_class_denied_by_default() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(effect_class=ExecutionClass.NETWORKED_EXECUTION.value), _env())
    assert not d.allowed
    assert any(r.startswith("EXECUTION_CLASS_DENIED") for r in d.reasons)


def test_admit_network_required_unclassified_denies() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(effect_class="read_only_inspection", network_required=True), _env())
    assert not d.allowed
    assert "NETWORK_REQUIRED_BUT_UNCLASSIFIED" in d.reasons


def test_admit_shell_without_explicit_authority_denies() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(effect_class="read_only_inspection", shell=True), _env())
    assert not d.allowed
    assert "SHELL_EXECUTION_REQUIRES_EXPLICIT_AUTHORITY" in d.reasons


def test_admit_shell_with_authority_allows() -> None:
    gate = ExecutionAdmissionGate()
    req = _req(effect_class="read_only_inspection", shell=True,
               environment_policy={"shell_authorized": True})
    d = gate.admit(req, _env())
    assert d.allowed, d.reasons


def test_admit_build_execution_allowed() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(effect_class=ExecutionClass.BUILD_EXECUTION.value,
                        role_id="builder"), _env(role_allowed=True, resource_allowed=True))
    assert d.allowed, d.reasons


def test_unknown_execution_class_denies() -> None:
    gate = ExecutionAdmissionGate()
    d = gate.admit(_req(effect_class="not_a_real_class"), _env())
    assert not d.allowed
    assert "UNKNOWN_EXECUTION_CLASS" in d.reasons


def test_denied_classes_frozen_and_complete() -> None:
    assert frozenset({
        ExecutionClass.NETWORKED_EXECUTION,
        ExecutionClass.SHELL_EXECUTION,
        ExecutionClass.PRIVILEGED_EXECUTION,
        ExecutionClass.EXTERNAL_EFFECT_EXECUTION,
    }) == DENIED_EXECUTION_CLASSES


def test_severity_taxonomy_from_intent() -> None:
    assert Severity.from_intent("material") == Severity.MATERIAL
    assert Severity.from_intent("PRINCIPAL_DECISION_REQUIRED") == Severity.PRINCIPAL_DECISION_REQUIRED
    assert Severity.from_intent("") == Severity.INFO
    # Severity never confers authority; it is a pure visibility label.
    assert Severity.SECURITY.value != "authority"


def test_admit_external_effect_firewall_blocked_for_all_roles() -> None:
    gate = ExecutionAdmissionGate()
    for role in ("builder", "researcher", "operator"):
        d = gate.admit(
            _req(effect_class=ExecutionClass.EXTERNAL_EFFECT_EXECUTION.value, role_id=role),
            _env(role_id=role, role_allowed=True),
        )
        assert not d.allowed, role
