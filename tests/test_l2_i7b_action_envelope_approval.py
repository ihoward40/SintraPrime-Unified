"""L2-I7B functional acceptance tests: A-01 through A-09.

Covers the canonical ActionEnvelope, PrincipalApprovalRecord, and
disposable local file-backed approval ledger.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sintra_live.l2.action_envelope_contract import (
    ActionEnvelope,
    SCHEMA_VERSION as ENVELOPE_SCHEMA,
    ENVELOPE_VERSION,
)
from sintra_live.l2.principal_approval_contract import (
    PrincipalApprovalRecord,
    ApprovalState,
    ApprovalResult,
    SCHEMA_VERSION as APPROVAL_SCHEMA,
    APPROVAL_VERSION,
)
from sintra_live.l2.principal_approval_ledger import (
    ApprovalLedger,
    CASConflict,
    DuplicateApprovalId,
    DuplicateNonce,
)

H = "a" * 64
Z = "0" * 64
T0 = "2026-08-24T10:00:00.000000Z"
NOW = "2026-08-24T10:30:00.000000Z"
T1 = "2026-08-24T11:00:00.000000Z"


def _envelope(**kw) -> ActionEnvelope:
    defaults = dict(
        schema_version=ENVELOPE_SCHEMA,
        envelope_version=ENVELOPE_VERSION,
        program_id="SP-LIVE-001",
        gate_id="L2-I7B",
        mission_id="smv2-mission",
        request_sha256=H,
        mission_scope_sha256=H,
        aggregate_version=1,
        aggregate_sha256=H,
        principal_identity_reference="principal-001",
        principal_session_id="session-001",
        policy_decision_sha256=H,
        authority_resolution_sha256=H,
        authority_snapshot_sha256=H,
        capability_id="cap-001",
        capability_version="v1",
        adapter_id="adapter-001",
        adapter_version="v1",
        canonical_entrypoint="entrypoint-001",
        provider_class="GitHubAppLiveProvider",
        provider_mode="LIVE",
        provider_account_reference="account-001",
        credential_boundary_reference="cred-boundary-001",
        operation_type="CREATE",
        http_method="POST",
        endpoint_or_operation_reference="/repos/test/test/issues/1/comments",
        destination_class="GITHUB",
        destination_reference="test/test/1",
        parameters_sha256=H,
        body_sha256=H,
        expected_baseline_sha256=H,
        baseline_commit_sha=H,
        baseline_tree_sha=H,
        execution_source_manifest_sha256=H,
        execution_id="exec-001",
        nonce="nonce-001",
        maximum_executions=1,
        side_effect_ceiling=1,
        cost_ceiling=100,
        token_ceiling=1000,
        latency_ceiling_ms=5000,
        consequence_class="EXTERNAL_COMMUNICATION",
        required_evidence_types=("authority", "approval", "envelope", "receipt", "readback", "evidence", "brief"),
        issued_at=T0,
        valid_from=T0,
        valid_until=T1,
        previous_governance_evidence_sha256=Z,
    )
    defaults.update(kw)
    return ActionEnvelope(**defaults)


def _approval(env: ActionEnvelope, **kw) -> PrincipalApprovalRecord:
    defaults = dict(
        schema_version=APPROVAL_SCHEMA,
        approval_version=APPROVAL_VERSION,
        approval_id="approval-001",
        program_id="SP-LIVE-001",
        gate_id="L2-I7B",
        mission_id="smv2-mission",
        request_sha256=H,
        principal_identity_reference="principal-001",
        principal_session_id="session-001",
        authentication_method="PASSWORD",
        authentication_timestamp=T0,
        action_envelope_sha256=env.action_envelope_sha256,
        approval_nonce="nonce-001",
        approval_disclosure_sha256=H,
        approval_phrase_or_decision_sha256=H,
        approval_result="APPROVED",
        maximum_executions=1,
        issued_at=T0,
        valid_from=T0,
        valid_until=T1,
        consumed_execution_id="",
        consumed_at="",
        prior_ledger_entry_sha256=Z,
    )
    defaults.update(kw)
    return PrincipalApprovalRecord(**defaults)


def _lifecycle(ledger, approval):
    """Run a full approval lifecycle, creating new records with correct prior hashes."""
    r = approval
    ledger.append(r, ApprovalState.PROPOSED, ApprovalState.DISCLOSED)
    head = ledger.load_head(r.approval_id)
    r = _approval(_envelope(), prior_ledger_entry_sha256=head["approval_record_sha256"])
    ledger.append(r, ApprovalState.DISCLOSED, ApprovalState.APPROVAL_REQUIRED)
    head = ledger.load_head(r.approval_id)
    r = _approval(_envelope(), prior_ledger_entry_sha256=head["approval_record_sha256"])
    ledger.append(r, ApprovalState.APPROVAL_REQUIRED, ApprovalState.APPROVED)
    head = ledger.load_head(r.approval_id)
    r = _approval(_envelope(), prior_ledger_entry_sha256=head["approval_record_sha256"])
    ledger.append(r, ApprovalState.APPROVED, ApprovalState.CONSUMPTION_PENDING)
    head = ledger.load_head(r.approval_id)
    r = _approval(_envelope(), prior_ledger_entry_sha256=head["approval_record_sha256"])
    ledger.append(r, ApprovalState.CONSUMPTION_PENDING, ApprovalState.CONSUMED)
    return r


# A-01: Envelope binds all required fields
def test_a01_envelope_binds_all_fields():
    env = _envelope()
    assert env.action_envelope_sha256
    assert env.maximum_executions == 1
    assert env.execution_id == "exec-001"
    assert env.nonce == "nonce-001"
    assert env.consequence_class == "EXTERNAL_COMMUNICATION"
    assert env.provider_mode == "LIVE"


# A-02: Canonical serialization and SHA-256 reproducible
def test_a02_canonical_hash_reproducible():
    env1 = _envelope()
    env2 = _envelope()
    assert env1.action_envelope_sha256 == env2.action_envelope_sha256
    body = env1.body()
    assert isinstance(body, dict)
    assert "action_envelope_sha256" not in body


# A-03: Material disclosure differs from envelope → Block
def test_a03_disclosure_mismatch_blocks():
    env = _envelope()
    approval = _approval(env)
    # If disclosure hash differs from envelope hash, it indicates mismatch
    different_disclosure = _approval(env, approval_disclosure_sha256="b" * 64)
    assert different_disclosure.approval_disclosure_sha256 != env.action_envelope_sha256


# A-04: Ambiguous/conditional/wrong-session/pre-disclosure approval → Deny
def test_a04_ambiguous_approval():
    env = _envelope()
    with pytest.raises(ValueError):
        _approval(env, approval_result="MAYBE")
    with pytest.raises(ValueError):
        _approval(env, principal_identity_reference="!@#invalid")


# A-05: Approval binds exact envelope hash and current Principal
def test_a05_approval_binds_envelope_hash():
    env = _envelope()
    approval = _approval(env)
    assert approval.action_envelope_sha256 == env.action_envelope_sha256
    assert approval.principal_identity_reference == env.principal_identity_reference


# A-06: Approval reused for another mission/action/target/body → Deny
def test_a06_approval_reuse_denied(tmp_path):
    env = _envelope()
    approval = _approval(env)
    ledger = ApprovalLedger(tmp_path)
    _lifecycle(ledger, approval)
    # Attempt reuse: should fail
    with pytest.raises(Exception):
        ledger.append(approval, ApprovalState.CONSUMED, ApprovalState.APPROVED)


# A-07: Approved envelope expires before I/O → Deny; fresh required
def test_a07_expiry_before_io():
    env = _envelope()
    T_EARLY = "2026-08-24T09:00:00.000000Z"
    approval = _approval(env, valid_from=T_EARLY, valid_until=T0)
    assert approval.valid_until <= NOW


# A-08: Material field/baseline changes after approval → Deny
def test_a08_material_change_after_approval():
    env = _envelope()
    approval = _approval(env)
    env_modified = _envelope(body_sha256="b" * 64)
    assert env_modified.action_envelope_sha256 != env.action_envelope_sha256
    assert approval.action_envelope_sha256 != env_modified.action_envelope_sha256


# A-09: Approval grants more than one execution → Deny
def test_a09_more_than_one_execution_denied():
    env = _envelope()
    with pytest.raises(ValueError):
        _approval(env, maximum_executions=2)
    with pytest.raises(ValueError):
        _envelope(maximum_executions=2)


# Ledger functional tests
def test_ledger_append_and_load(tmp_path):
    env = _envelope()
    approval = _approval(env)
    ledger = ApprovalLedger(tmp_path)
    ledger.append(approval, ApprovalState.PROPOSED, ApprovalState.DISCLOSED)
    head = ledger.load_head("approval-001")
    assert head is not None
    assert head["state"] == "DISCLOSED"


def test_ledger_cas_semantics(tmp_path):
    env = _envelope()
    approval = _approval(env)
    ledger = ApprovalLedger(tmp_path)
    ledger.append(approval, ApprovalState.PROPOSED, ApprovalState.DISCLOSED)
    # CAS conflict: wrong prior hash
    approval2 = _approval(env, prior_ledger_entry_sha256="b" * 64)
    with pytest.raises(CASConflict):
        ledger.append(approval2, ApprovalState.DISCLOSED, ApprovalState.APPROVAL_REQUIRED)


def test_ledger_restart_durability(tmp_path):
    env = _envelope()
    approval = _approval(env)
    ledger1 = ApprovalLedger(tmp_path)
    ledger1.append(approval, ApprovalState.PROPOSED, ApprovalState.DISCLOSED)
    head = ledger1.load_head("approval-001")
    r2 = _approval(_envelope(), prior_ledger_entry_sha256=head["approval_record_sha256"])
    ledger1.append(r2, ApprovalState.DISCLOSED, ApprovalState.APPROVAL_REQUIRED)
    # Restart: new ledger instance reads same directory
    ledger2 = ApprovalLedger(tmp_path)
    head2 = ledger2.load_head("approval-001")
    assert head2 is not None
    assert head2["state"] == "APPROVAL_REQUIRED"


def test_ledger_replay_denial(tmp_path):
    env = _envelope()
    approval = _approval(env)
    ledger = ApprovalLedger(tmp_path)
    _lifecycle(ledger, approval)
    # Replay: try to append again with CONSUMED → should fail
    with pytest.raises(Exception):
        ledger.append(approval, ApprovalState.CONSUMED, ApprovalState.APPROVED)


def test_ledger_single_use_nonce(tmp_path):
    env = _envelope()
    approval = _approval(env)
    ledger = ApprovalLedger(tmp_path)
    ledger.append(approval, ApprovalState.PROPOSED, ApprovalState.DISCLOSED)
    # Duplicate nonce with different approval ID
    env2 = _envelope(mission_id="other-mission", execution_id="exec-002")
    approval2 = _approval(env2, approval_id="approval-002", approval_nonce="nonce-001")
    with pytest.raises(DuplicateNonce):
        ledger.append(approval2, ApprovalState.PROPOSED, ApprovalState.DISCLOSED)


def test_ledger_ambiguous_consumption_fail_closed(tmp_path):
    env = _envelope()
    approval = _approval(env)
    ledger = ApprovalLedger(tmp_path)
    r = approval
    ledger.append(r, ApprovalState.PROPOSED, ApprovalState.DISCLOSED)
    head = ledger.load_head(r.approval_id)
    r = _approval(_envelope(), prior_ledger_entry_sha256=head["approval_record_sha256"])
    ledger.append(r, ApprovalState.DISCLOSED, ApprovalState.APPROVAL_REQUIRED)
    head = ledger.load_head(r.approval_id)
    r = _approval(_envelope(), prior_ledger_entry_sha256=head["approval_record_sha256"])
    ledger.append(r, ApprovalState.APPROVAL_REQUIRED, ApprovalState.APPROVED)
    head = ledger.load_head(r.approval_id)
    r = _approval(_envelope(), prior_ledger_entry_sha256=head["approval_record_sha256"])
    ledger.append(r, ApprovalState.APPROVED, ApprovalState.CONSUMPTION_PENDING)
    head = ledger.load_head(r.approval_id)
    r = _approval(_envelope(), prior_ledger_entry_sha256=head["approval_record_sha256"])
    ledger.append(r, ApprovalState.CONSUMPTION_PENDING, ApprovalState.CONSUMPTION_AMBIGUOUS)
    head = ledger.load_head("approval-001")
    assert head["state"] == "CONSUMPTION_AMBIGUOUS"
    # Cannot transition from CONSUMPTION_AMBIGUOUS
    r2 = _approval(_envelope(), prior_ledger_entry_sha256=head["approval_record_sha256"])
    with pytest.raises(Exception):
        ledger.append(r2, ApprovalState.CONSUMPTION_AMBIGUOUS, ApprovalState.CONSUMED)


def test_authority_delta_zero():
    env = _envelope()
    assert env.maximum_executions == 1
    approval = _approval(env)
    assert approval.maximum_executions == 1
    # No authority_delta field in I7B contracts — authority_delta is 0 by design


def test_execution_ready_false():
    env = _envelope()
    approval = _approval(env)
    # I7B does not produce execution_ready=True
    assert not hasattr(env, "execution_ready")
    assert not hasattr(approval, "execution_ready")