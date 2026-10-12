"""SP-A2A-AUTHORITY-PHASE-B-005-R1: 18-Test Authority Enforcement Suite.

Covers 17 Negative/Denial/Recovery tests and 1 Positive Authorized test.
Proves fail-closed security invariants across cryptographic Principal token verification,
default-deny worker capabilities, SQLite atomic transactions, and multi-process replay protection.
"""
from __future__ import annotations

import hashlib
import hmac
import multiprocessing
import os
import sqlite3
import subprocess
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from mission_wiring.approval_ledger import ApprovalLedger, LedgerError, LedgerUnavailableError
from mission_wiring.approval_service import (
    ApprovalBinding,
    ApprovalInvalidError,
    AuthorityApprovalService,
    PrincipalAuthToken,
)
from swarm_runtime.controller import SwarmController
from swarm_runtime.governed_execution import (
    AuthorityEnvelope,
    ExecutionAdmissionGate,
    ExecutionClass,
    ExecutionRequest,
)
from swarm_runtime.hermes_adapter import DelegateTask, HermesSwarmAdapter


@pytest.fixture
def tmp_ledger(tmp_path: Path) -> ApprovalLedger:
    db_file = tmp_path / "ledger.db"
    return ApprovalLedger(db_file)


@pytest.fixture
def approval_svc(tmp_ledger: ApprovalLedger) -> AuthorityApprovalService:
    return AuthorityApprovalService(ledger=tmp_ledger)


def _sign_token(
    *,
    principal_id: str = "principal-1",
    tenant_id: str = "default",
    mission_id: str = "m-1",
    actor_id: str = "W1",
    capabilities_hash: str = "caps-hash-1",
    resource_urls_hash: str = "res-hash-1",
    context_hash: str = "051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    role: str = "auditor",
    worker_class: str = "CodeSearchWorker",
    effect_class: str = "read_only_inspection",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    nonce: str = "nonce-12345",
    secret_key: bytes = b"sintraprime-default-principal-secret",
) -> PrincipalAuthToken:
    i_at = issued_at or datetime.now(UTC)
    e_at = expires_at or (i_at + timedelta(seconds=3600))
    tok = PrincipalAuthToken(
        principal_id=principal_id,
        tenant_id=tenant_id,
        mission_id=mission_id,
        actor_id=actor_id,
        capabilities_hash=capabilities_hash,
        resource_urls_hash=resource_urls_hash,
        context_hash=context_hash,
        role=role,
        worker_class=worker_class,
        effect_class=effect_class,
        issued_at=i_at,
        expires_at=e_at,
        nonce=nonce,
        signature="",
    )
    sig = hmac.new(secret_key, tok.canonical_payload(), hashlib.sha256).hexdigest()
    return PrincipalAuthToken(
        principal_id=tok.principal_id,
        tenant_id=tok.tenant_id,
        mission_id=tok.mission_id,
        actor_id=tok.actor_id,
        capabilities_hash=tok.capabilities_hash,
        resource_urls_hash=tok.resource_urls_hash,
        context_hash=tok.context_hash,
        role=tok.role,
        worker_class=tok.worker_class,
        effect_class=tok.effect_class,
        issued_at=tok.issued_at,
        expires_at=tok.expires_at,
        nonce=tok.nonce,
        signature=sig,
    )


def _make_exec_req(
    *,
    execution_request_id: str = "r1",
    mission_id: str = "m-1",
    swarm_id: str = "s-1",
    task_id: str = "t-1",
    agent_id: str = "W1",
    authority_id: str = "appr-1",
    context_package_id: str = "051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    role_id: str = "auditor",
    working_directory: str = ".",
    timeout_seconds: int = 30,
    effect_class: str = "read_only_inspection",
    worker_class: str = "CodeSearchWorker",
    read_paths: list[str] | None = None,
    write_paths: list[str] | None = None,
    task_params: dict | None = None,
) -> ExecutionRequest:
    return ExecutionRequest(
        execution_request_id=execution_request_id,
        mission_id=mission_id,
        swarm_id=swarm_id,
        task_id=task_id,
        agent_id=agent_id,
        authority_id=authority_id,
        context_package_id=context_package_id,
        role_id=role_id,
        working_directory=working_directory,
        timeout_seconds=timeout_seconds,
        effect_class=effect_class,
        worker_class=worker_class,
        read_paths=read_paths or [],
        write_paths=write_paths or [],
        task_params=task_params or {},
    )


# ==============================================================================
# 17 NEGATIVE / DENIAL / RECOVERY TESTS
# ==============================================================================

def test_neg_01_missing_verifier():
    """NEG-01: ExecutionAdmissionGate without approval service fails closed."""
    gate = ExecutionAdmissionGate(approval_service=None)
    req = _make_exec_req()
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id="appr-1",
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert "APPROVAL_SERVICE_MANDATORY" in decision.reasons


def test_neg_02_forged_approval_id(approval_svc):
    """NEG-02: Forged approval handle that was never issued fails closed."""
    gate = ExecutionAdmissionGate(approval_service=approval_svc)
    req = _make_exec_req(authority_id="appr-forged-uuid")
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id="appr-forged-uuid",
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert any("AUTHORITY_REVALIDATION_FAILED:UNKNOWN_APPROVAL" in r for r in decision.reasons)


def test_neg_03_forged_principal_signature(approval_svc):
    """NEG-03: Principal token with corrupted signature is rejected on issuance."""
    tok = _sign_token()
    bad_tok = PrincipalAuthToken(
        principal_id=tok.principal_id,
        tenant_id=tok.tenant_id,
        mission_id=tok.mission_id,
        actor_id=tok.actor_id,
        capabilities_hash=tok.capabilities_hash,
        resource_urls_hash=tok.resource_urls_hash,
        context_hash=tok.context_hash,
        role=tok.role,
        worker_class=tok.worker_class,
        effect_class=tok.effect_class,
        issued_at=tok.issued_at,
        expires_at=tok.expires_at,
        nonce=tok.nonce,
        signature="bad-signature-hex",
    )
    with pytest.raises(ApprovalInvalidError) as exc:
        approval_svc.issue(
            approval_id="appr-1",
            mission_id=tok.mission_id,
            actor_id=tok.actor_id,
            tenant_id=tok.tenant_id,
            capabilities=frozenset({"repository.read"}),
            resource_urls=frozenset(),
            issued_by="PRINCIPAL",
            principal_token=bad_tok,
        )
    assert exc.value.code == "UNAUTHENTICATED_PRINCIPAL"


def test_neg_04_token_mission_mismatch(approval_svc):
    """NEG-04: Token signed for mission-A used to request approval for mission-B fails closed."""
    tok = _sign_token(mission_id="mission-alpha")
    with pytest.raises(ApprovalInvalidError) as exc:
        approval_svc.issue(
            approval_id="appr-1",
            mission_id="mission-beta",
            actor_id=tok.actor_id,
            tenant_id=tok.tenant_id,
            capabilities=frozenset({"repository.read"}),
            resource_urls=frozenset(),
            issued_by="PRINCIPAL",
            principal_token=tok,
        )
    assert exc.value.code == "TOKEN_SCOPE_MISMATCH"


def test_neg_05_unknown_worker_class(approval_svc):
    """NEG-05: Unregistered worker class is denied default-deny."""
    gate = ExecutionAdmissionGate(approval_service=approval_svc)
    req = _make_exec_req(worker_class="UnauthorizedExploitWorker")
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id="appr-1",
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert any("UNKNOWN_WORKER_CLASS:UnauthorizedExploitWorker" in r for r in decision.reasons)


def test_neg_06_known_worker_class_escalation(approval_svc):
    """NEG-06: Task requests BuilderWorker when approval permits only CodeSearchWorker."""
    tok = _sign_token(worker_class="CodeSearchWorker")
    appr = approval_svc.issue(
        approval_id="appr-1",
        mission_id="m-1",
        actor_id="W1",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset(),
        issued_by="PRINCIPAL",
        permitted_roles=frozenset({"auditor"}),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        principal_token=tok,
    )
    gate = ExecutionAdmissionGate(approval_service=approval_svc)
    req = _make_exec_req(authority_id=appr.approval_id, worker_class="BuilderWorker")
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id=appr.approval_id,
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert any("AUTHORITY_REVALIDATION_FAILED:WORKER_CLASS_DENIED" in r for r in decision.reasons)


def test_neg_07_missing_allowlist_scope(approval_svc):
    """NEG-07: Approval with empty permitted_roles is rejected."""
    appr = approval_svc.issue(
        approval_id="appr-empty-role",
        mission_id="m-1",
        actor_id="W1",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset(),
        issued_by="PRINCIPAL",
        permitted_roles=frozenset(),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )
    gate = ExecutionAdmissionGate(approval_service=approval_svc)
    req = _make_exec_req(authority_id=appr.approval_id)
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id=appr.approval_id,
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert any("AUTHORITY_REVALIDATION_FAILED:ROLE_NOT_ALLOWED" in r for r in decision.reasons)


def test_neg_08_role_escalation_attack(approval_svc):
    """NEG-08: Task requesting root role when approval binds auditor fails closed."""
    appr = approval_svc.issue(
        approval_id="appr-1",
        mission_id="m-1",
        actor_id="W1",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset(),
        issued_by="PRINCIPAL",
        permitted_roles=frozenset({"auditor"}),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )
    gate = ExecutionAdmissionGate(approval_service=approval_svc)
    req = _make_exec_req(authority_id=appr.approval_id, role_id="root_administrator")
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id=appr.approval_id,
        role_id="root_administrator",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert any("AUTHORITY_REVALIDATION_FAILED:ROLE_NOT_ALLOWED" in r for r in decision.reasons)


def test_neg_09_execution_class_escalation(approval_svc):
    """NEG-09: Task requesting shell_execution when approval binds read_only fails closed."""
    appr = approval_svc.issue(
        approval_id="appr-1",
        mission_id="m-1",
        actor_id="W1",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset(),
        issued_by="PRINCIPAL",
        permitted_roles=frozenset({"auditor"}),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )
    gate = ExecutionAdmissionGate(approval_service=approval_svc)
    req = _make_exec_req(authority_id=appr.approval_id, effect_class="shell_execution")
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id=appr.approval_id,
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert any("AUTHORITY_REVALIDATION_FAILED:EXECUTION_CLASS_DENIED" in r for r in decision.reasons)


def test_neg_10_resource_escalation_attack(approval_svc):
    """NEG-10: Task requesting /etc/shadow outside approved resource scope fails closed."""
    appr = approval_svc.issue(
        approval_id="appr-1",
        mission_id="m-1",
        actor_id="W1",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset({"portal/"}),
        issued_by="PRINCIPAL",
        permitted_roles=frozenset({"auditor"}),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )
    gate = ExecutionAdmissionGate(approval_service=approval_svc)
    req = _make_exec_req(authority_id=appr.approval_id, read_paths=["/etc/shadow"])
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id=appr.approval_id,
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert any("AUTHORITY_REVALIDATION_FAILED:RESOURCE_NOT_APPROVED" in r for r in decision.reasons)


def test_neg_11_context_hash_mismatch(approval_svc):
    """NEG-11: Request with altered base SHA context package fails closed."""
    appr = approval_svc.issue(
        approval_id="appr-1",
        mission_id="m-1",
        actor_id="W1",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset(),
        issued_by="PRINCIPAL",
        permitted_roles=frozenset({"auditor"}),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )
    gate = ExecutionAdmissionGate(approval_service=approval_svc)
    req = _make_exec_req(
        authority_id=appr.approval_id,
        context_package_id="bad-modified-context-hash-12345",
    )
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id=appr.approval_id,
        role_id="auditor",
        context_package_id="bad-modified-context-hash-12345",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert any("AUTHORITY_REVALIDATION_FAILED:CONTEXT_MISMATCH" in r for r in decision.reasons)


def test_neg_12_expired_approval(approval_svc):
    """NEG-12: Expired approval fails validation at the execution boundary."""
    appr = approval_svc.issue(
        approval_id="appr-expired",
        mission_id="m-1",
        actor_id="W1",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset(),
        issued_by="PRINCIPAL",
        ttl_seconds=1,
        permitted_roles=frozenset({"auditor"}),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )
    time.sleep(1.2)
    gate = ExecutionAdmissionGate(approval_service=approval_svc)
    req = _make_exec_req(authority_id=appr.approval_id)
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id=appr.approval_id,
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert any("AUTHORITY_REVALIDATION_FAILED:APPROVAL_EXPIRED" in r for r in decision.reasons)


def test_neg_13_revoked_approval(approval_svc):
    """NEG-13: Revoked approval is immediately denied admission."""
    appr = approval_svc.issue(
        approval_id="appr-revoked",
        mission_id="m-1",
        actor_id="W1",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset(),
        issued_by="PRINCIPAL",
        permitted_roles=frozenset({"auditor"}),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )
    approval_svc.revoke(appr.approval_id, by="PRINCIPAL", reason="Security containment")
    gate = ExecutionAdmissionGate(approval_service=approval_svc)
    req = _make_exec_req(authority_id=appr.approval_id)
    env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-1",
        task_id="t-1",
        agent_id="W1",
        authority_id=appr.approval_id,
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    decision = gate.admit(req, env)
    assert not decision.allowed
    assert any("AUTHORITY_REVALIDATION_FAILED:APPROVAL_REVOKED" in r for r in decision.reasons)


def test_neg_14_direct_controller_bypass(approval_svc, tmp_path):
    """NEG-14: Caller supplying fake envelope booleans without valid authority handle is denied."""
    ctrl = SwarmController(
        swarm_id="s-bypass",
        repo_path=str(tmp_path),
        run_dir=str(tmp_path / "runs"),
        approval_service=approval_svc,
    )
    fake_env = AuthorityEnvelope(
        mission_id="m-1",
        swarm_id="s-bypass",
        task_id="t-1",
        agent_id="W1",
        authority_id="non-existent-authority",
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    req = _make_exec_req(swarm_id="s-bypass", authority_id="non-existent-authority")
    res = ctrl.launch_governed(req, fake_env)
    assert res.status == "DENIED"
    assert any("AUTHORITY_REVALIDATION_FAILED:UNKNOWN_APPROVAL" in r for r in res.rejection_reasons)


def _worker_proc_consume(db_path: str, approval_id: str, results_list: Any) -> None:
    ledger = ApprovalLedger(db_path)
    try:
        ledger.validate_and_consume(
            approval_id,
            mission_id="m-concurrent",
            actor_id="W-concurrent",
            tenant_id="default",
            capabilities=frozenset({"repository.read"}),
            resource_urls=frozenset(),
            role="auditor",
            worker_class="CodeSearchWorker",
            effect_class="read_only_inspection",
            context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        )
        results_list.append("SUCCESS")
    except LedgerError as exc:
        results_list.append(exc.code)


def test_neg_15_concurrent_multiprocess_replay_race(tmp_path):
    """NEG-15: Concurrent processes racing to consume the same approval; exactly one succeeds."""
    db_file = tmp_path / "concurrent_ledger.db"
    ledger = ApprovalLedger(db_file)
    appr_id = "appr-race-1"
    ledger.issue(
        approval_id=appr_id,
        mission_id="m-concurrent",
        actor_id="W-concurrent",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset(),
        issued_by="PRINCIPAL",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(seconds=3600),
        permitted_roles=frozenset({"auditor"}),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )

    manager = multiprocessing.Manager()
    results = manager.list()

    p1 = multiprocessing.Process(target=_worker_proc_consume, args=(str(db_file), appr_id, results))
    p2 = multiprocessing.Process(target=_worker_proc_consume, args=(str(db_file), appr_id, results))

    p1.start()
    p2.start()
    p1.join()
    p2.join()

    res_list = list(results)
    assert res_list.count("SUCCESS") == 1
    assert res_list.count("APPROVAL_ALREADY_CONSUMED") == 1


def test_neg_16_inaccessible_locked_ledger(tmp_path):
    """NEG-16: Inaccessible/locked SQLite ledger fails closed with LedgerUnavailableError."""
    db_dir = tmp_path / "not_a_db"
    db_dir.mkdir()
    # Pointing ledger at an existing directory instead of a file causes sqlite3.connect or DDL to fail
    with pytest.raises(LedgerUnavailableError):
        ApprovalLedger(db_dir)


def test_neg_17_crash_after_consumption_recovery(approval_svc, tmp_path):
    """NEG-17: Crash after approval consumption records failure and permanently marks approval consumed."""
    appr = approval_svc.issue(
        approval_id="appr-crash-test",
        mission_id="m-crash",
        actor_id="W-crash",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset(),
        issued_by="PRINCIPAL",
        permitted_roles=frozenset({"auditor"}),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
    )
    ctrl = SwarmController(
        swarm_id="s-crash",
        repo_path=str(tmp_path),
        run_dir=str(tmp_path / "runs"),
        approval_service=approval_svc,
    )
    env = AuthorityEnvelope(
        mission_id="m-crash",
        swarm_id="s-crash",
        task_id="t-crash",
        agent_id="W-crash",
        authority_id=appr.approval_id,
        role_id="auditor",
        context_package_id="051e2594c67a805ceacc66ea2a6fc6db9c0bc793",
        mission_active=True,
        swarm_authorized=True,
        task_ready=True,
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=True,
        resource_allowed=True,
    )
    req = _make_exec_req(
        execution_request_id="r-crash",
        mission_id="m-crash",
        swarm_id="s-crash",
        task_id="t-crash",
        agent_id="W-crash",
        authority_id=appr.approval_id,
    )

    # Simulate crash during launch by monkeypatching _launch_worker to raise an unhandled exception
    def _exploding_launch(*args, **kwargs):
        raise RuntimeError("SIMULATED_PROCESS_SPAWN_CRASH")

    ctrl._launch_worker = _exploding_launch

    res = ctrl.launch_governed(req, env)
    assert res.status == "FAILED"
    assert any("WORKER_LAUNCH_CRASH" in r for r in res.rejection_reasons)

    # Invariant: Approval was already consumed and CANNOT be reused or replayed
    assert approval_svc.status(appr.approval_id) == "CONSUMED"
    with pytest.raises(ApprovalInvalidError) as exc:
        approval_svc.validate(
            appr.approval_id,
            mission_id="m-crash",
            actor_id="W-crash",
            tenant_id="default",
            capabilities=frozenset({"repository.read"}),
            resource_urls=frozenset(),
        )
    assert exc.value.code == "APPROVAL_ALREADY_CONSUMED"


# ==============================================================================
# 1 POSITIVE AUTHORIZED TEST
# ==============================================================================

def test_pos_01_legitimate_authorized_delegation(approval_svc, tmp_path):
    """POS-01: End-to-end authorized delegation via HermesSwarmAdapter with valid Principal token."""
    base_sha = "051e2594c67a805ceacc66ea2a6fc6db9c0bc793"
    token = _sign_token(
        principal_id="principal-authorized",
        tenant_id="default",
        mission_id="pos-mission",
        actor_id="W-pos",
        role="auditor",
        worker_class="CodeSearchWorker",
        effect_class="read_only_inspection",
        context_hash=base_sha,
    )
    appr = approval_svc.issue(
        approval_id="appr-pos-01",
        mission_id="pos-mission",
        actor_id="W-pos",
        tenant_id="default",
        capabilities=frozenset({"repository.read"}),
        resource_urls=frozenset({"portal/"}),
        issued_by="PRINCIPAL",
        permitted_roles=frozenset({"auditor"}),
        permitted_workers=frozenset({"CodeSearchWorker"}),
        permitted_execution_classes=frozenset({"read_only_inspection"}),
        context_hash=base_sha,
        principal_token=token,
    )

    adapter = HermesSwarmAdapter(
        repo_path=str(tmp_path),
        run_dir=str(tmp_path / "runs"),
        max_concurrent=1,
        approval_service=approval_svc,
    )
    task = DelegateTask(
        task_id="W-pos",
        description="Search for ForeignKey references",
        role="auditor",
        base_sha=base_sha,
        read_paths=["portal/"],
        write_paths=[],
        expected_artifact="findings",
        timeout_seconds=30,
        tenant="default",
        mission="pos-mission",
        run_context={"swarm_id": "swarm-pos", "approval_id": appr.approval_id},
        worker_class="CodeSearchWorker",
        task_params={"pattern": "class ", "path": "portal/", "file_glob": "*.py"},
        artifact_filename="artifacts/pos.json",
    )

    env = task.to_authority_envelope("W-pos", approval_service=approval_svc)
    assert env.mission_active is True
    assert env.swarm_authorized is True
    assert env.task_ready is True
    assert env.agent_authorized is True
    assert env.authority_valid is True
    assert env.context_valid is True
    assert env.role_allowed is True
    assert env.resource_allowed is True
    assert env.revoked is False

    # Execute through SwarmController
    ctrl = SwarmController(
        swarm_id="swarm-pos",
        repo_path=str(tmp_path),
        run_dir=str(tmp_path / "runs"),
        approval_service=approval_svc,
    )
    req = task.to_execution_request("W-pos", appr.approval_id, base_sha)
    res = ctrl.launch_governed(req, env)

    assert res.status == "RUNNING"
    # Invariant: Approval is now atomic consumed
    assert approval_svc.status(appr.approval_id) == "CONSUMED"
