"""L2-I8 functional acceptance tests: C-01 through C-10."""
from __future__ import annotations

import pytest

from sintra_live.l2.action_envelope_contract import (
    ActionEnvelope, SCHEMA_VERSION as ENV_SCHEMA, ENVELOPE_VERSION,
)
from sintra_live.l2.principal_approval_contract import (
    PrincipalApprovalRecord, ApprovalState,
    SCHEMA_VERSION as APPL_SCHEMA, APPROVAL_VERSION,
)
from sintra_live.l2.capability_registry_contract import (
    CapabilityRegistryEntry, CapabilityLookupRequest,
    CapabilityResolutionRecord, DenyReason, ResolutionResult,
    SCHEMA_VERSION as REG_SCHEMA,
)
from sintra_live.l2.capability_registry import CapabilityRegistry, CapabilityRegistryError
from sintra_live.l2.capability_resolution import resolve_capability
from sintra_live.l2.canonical_capability_executor import CanonicalCapabilityExecutor

H = "a" * 64
Z = "0" * 64
T0 = "2026-08-24T10:00:00.000000Z"
T1 = "2026-08-24T11:00:00.000000Z"


def _entry(**kw) -> CapabilityRegistryEntry:
    defaults = dict(
        schema_version=REG_SCHEMA, entry_version="v1",
        capability_id="cap-001", capability_version="v1",
        adapter_id="adapter-001", adapter_version="v1",
        canonical_entrypoint="entrypoint-001",
        provider_class="GitHubAppLiveProvider", provider_mode="LIVE",
        provider_account_reference="account-001",
        credential_boundary_reference="cred-001",
        operation_type="CREATE", http_method="POST",
        endpoint_or_operation_reference="/repos/test/test/issues/1/comments",
        destination_class="GITHUB", consequence_class="EXTERNAL_COMMUNICATION",
        certified=True, deprecated=False,
    )
    defaults.update(kw)
    return CapabilityRegistryEntry(**defaults)


def _envelope(**kw) -> ActionEnvelope:
    defaults = dict(
        schema_version=ENV_SCHEMA, envelope_version=ENVELOPE_VERSION,
        program_id="SP-LIVE-001", gate_id="L2-I8", mission_id="smv2-mission",
        request_sha256=H, mission_scope_sha256=H, aggregate_version=1,
        aggregate_sha256=H, principal_identity_reference="principal-001",
        principal_session_id="session-001", policy_decision_sha256=H,
        authority_resolution_sha256=H, authority_snapshot_sha256=H,
        capability_id="cap-001", capability_version="v1",
        adapter_id="adapter-001", adapter_version="v1",
        canonical_entrypoint="entrypoint-001",
        provider_class="GitHubAppLiveProvider", provider_mode="LIVE",
        provider_account_reference="account-001",
        credential_boundary_reference="cred-001",
        operation_type="CREATE", http_method="POST",
        endpoint_or_operation_reference="/repos/test/test/issues/1/comments",
        destination_class="GITHUB", destination_reference="test/test/1",
        parameters_sha256=H, body_sha256=H, expected_baseline_sha256=H,
        baseline_commit_sha=H, baseline_tree_sha=H, execution_source_manifest_sha256=H,
        execution_id="exec-001", nonce="nonce-001", maximum_executions=1,
        side_effect_ceiling=1, cost_ceiling=100, token_ceiling=1000,
        latency_ceiling_ms=5000, consequence_class="EXTERNAL_COMMUNICATION",
        required_evidence_types=("authority", "approval", "envelope", "receipt"),
        issued_at=T0, valid_from=T0, valid_until=T1,
        previous_governance_evidence_sha256=Z,
    )
    defaults.update(kw)
    return ActionEnvelope(**defaults)


def _approval(env: ActionEnvelope, **kw) -> PrincipalApprovalRecord:
    defaults = dict(
        schema_version=APPL_SCHEMA, approval_version=APPROVAL_VERSION,
        approval_id="approval-001", program_id="SP-LIVE-001", gate_id="L2-I8",
        mission_id="smv2-mission", request_sha256=H,
        principal_identity_reference="principal-001", principal_session_id="session-001",
        authentication_method="PASSWORD", authentication_timestamp=T0,
        action_envelope_sha256=env.action_envelope_sha256, approval_nonce="nonce-001",
        approval_disclosure_sha256=H, approval_phrase_or_decision_sha256=H,
        approval_result="APPROVED", maximum_executions=1, issued_at=T0,
        valid_from=T0, valid_until=T1, consumed_execution_id="", consumed_at="",
        prior_ledger_entry_sha256=Z,
    )
    defaults.update(kw)
    return PrincipalApprovalRecord(**defaults)


def _registry(**kw) -> CapabilityRegistry:
    return CapabilityRegistry((_entry(**kw),))


# C-01: exact capability/version/adapter/entrypoint/provider/account/boundary match
def test_c01_exact_match():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.result == "ALLOW"
    assert r.authority_delta == 0
    assert r.execution_ready is False
    assert r.matched_entry_sha256 != ""
    assert r.deny_reason == ""


# C-02: alias/similar/deprecated/alternate entrypoint denied
def test_c02_alias_denied():
    env = _envelope(capability_id="cap-002")
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.UNKNOWN_CAPABILITY.value


def test_c02_deprecated_denied():
    env = _envelope()
    ap = _approval(env)
    reg = _registry(deprecated=True)
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.DEPRECATED_CAPABILITY.value


def test_c02_alternate_entrypoint_denied():
    env = _envelope(canonical_entrypoint="entrypoint-002")
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.ENTRYPOINT_MISMATCH.value


# C-03: missing execution ID — envelope rejects empty at construction
def test_c03_missing_exec_id():
    with pytest.raises(ValueError, match="INVALID_IDENTIFIER"):
        _envelope(execution_id="")


# C-04: missing nonce — envelope rejects empty at construction
def test_c04_missing_nonce():
    with pytest.raises(ValueError, match="INVALID_IDENTIFIER"):
        _envelope(nonce="")


# C-05: execution ID / nonce mismatch
def test_c05_nonce_mismatch():
    env = _envelope(nonce="nonce-002")
    ap = _approval(_envelope(), approval_nonce="nonce-001")
    # But env.nonce differs from approval.approval_nonce
    ap2 = _approval(env, approval_nonce="different-nonce")
    reg = _registry()
    r = resolve_capability(env, reg, ap2)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.NONCE_MISMATCH.value


def test_c05_envelope_hash_mismatch():
    env = _envelope()
    ap = _approval(_envelope(body_sha256="b" * 64))  # different envelope
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.AUTHORITY_MISMATCH.value


# C-06: execution identity autogeneration denied — envelope rejects empty, resolver never auto-fills
def test_c06_autogeneration_denied():
    with pytest.raises(ValueError, match="INVALID_IDENTIFIER"):
        _envelope(execution_id="")
    with pytest.raises(ValueError, match="INVALID_IDENTIFIER"):
        _envelope(nonce="")


# C-07: mock/dry-run fallback denied
def test_c07_mock_fallback_denied():
    env = _envelope(provider_mode="MOCK")
    ap = _approval(env)
    reg = _registry(provider_mode="LIVE")
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.MOCK_FALLBACK.value


# C-08: account/boundary mismatch
def test_c08_account_mismatch():
    env = _envelope(provider_account_reference="account-002")
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.ACCOUNT_MISMATCH.value


def test_c08_credential_boundary_mismatch():
    env = _envelope(credential_boundary_reference="cred-002")
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.CREDENTIAL_BOUNDARY_MISMATCH.value


# C-09: baseline mismatch
def test_c09_baseline_commit_mismatch():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap, runtime_head="b" * 64)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.BASELINE_COMMIT_MISMATCH.value


def test_c09_baseline_tree_mismatch():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap, runtime_tree="b" * 64)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.BASELINE_TREE_MISMATCH.value


def test_c09_source_manifest_mismatch():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap, runtime_manifest="b" * 64)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.SOURCE_MANIFEST_MISMATCH.value


# C-10: target/duplicate/kill-switch
def test_c10_target_closed():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap, target_open=False)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.TARGET_CLOSED.value


def test_c10_target_missing():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap, target_exists=False)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.TARGET_MISSING.value


def test_c10_duplicate():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap, duplicate_exists=True)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.DUPLICATE_TARGET.value


def test_c10_kill_switch():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap, kill_switch=True)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.KILL_SWITCH.value


def test_c10_cancellation():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap, cancellation=True)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.CANCELLATION.value


# Authority and execution invariants
def test_authority_delta_zero():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.authority_delta == 0


def test_execution_ready_false():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.execution_ready is False


def test_executor_interface_contract():
    # Verify the protocol exists and is runtime_checkable
    assert hasattr(CanonicalCapabilityExecutor, "execute")


def test_missing_approval_denied():
    env = _envelope()
    reg = _registry()
    r = resolve_capability(env, reg, None)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.MISSING_APPROVAL.value


def test_expired_approval_denied():
    env = _envelope()
    ap = _approval(env, approval_result="EXPIRED")
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.EXPIRED_APPROVAL.value


def test_consumed_approval_denied():
    env = _envelope()
    ap = _approval(env, approval_result="CONSUMED")
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.CONSUMED_APPROVAL.value


def test_provider_class_mismatch():
    env = _envelope(provider_class="OtherProvider")
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.PROVIDER_CLASS_MISMATCH.value


def test_adapter_mismatch():
    env = _envelope(adapter_id="adapter-002")
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.ADAPTER_MISMATCH.value


def test_side_effect_ceiling_exceeded():
    env = _envelope()
    ap = _approval(env)
    reg = _registry()
    r = resolve_capability(env, reg, ap, side_effect_count=1)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.SIDE_EFFECT_CEILING_EXCEEDED.value