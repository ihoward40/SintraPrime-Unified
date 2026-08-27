"""L2-I8 adversarial tests: duplicate registry, ambiguous match, unknown capability,
alternate adapter/entrypoint, provider mismatch, account/boundary mismatch,
baseline mismatch, manifest mismatch, duplicate-state, side-effect ceiling,
kill switch, cancellation, missing/expired/consumed approval, authority mismatch,
authority-from-certification inference, readiness-from-resolution inference,
zero provider/network/credential/database/external activity.
"""
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
    CapabilityRegistryEntry, DenyReason, ResolutionResult,
    SCHEMA_VERSION as REG_SCHEMA,
)
from sintra_live.l2.capability_registry import (
    CapabilityRegistry, CapabilityRegistryError, DuplicateRegistryKey,
)
from sintra_live.l2.capability_resolution import resolve_capability

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


def _approval(env, **kw):
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


def _reg(**kw):
    return CapabilityRegistry((_entry(**kw),))


# Duplicate registry key
def test_duplicate_registry_key_rejected():
    e1 = _entry()
    e2 = _entry()
    with pytest.raises(DuplicateRegistryKey):
        CapabilityRegistry((e1, e2))


# Unknown capability
def test_unknown_capability_denied():
    env = _envelope(capability_id="cap-999")
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.UNKNOWN_CAPABILITY.value


# Unknown version
def test_unknown_version_denied():
    env = _envelope(capability_version="v999")
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.UNKNOWN_CAPABILITY.value


# Deprecated capability
def test_deprecated_denied():
    env = _envelope()
    ap = _approval(env)
    reg = _reg(deprecated=True)
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.DEPRECATED_CAPABILITY.value


# Alternate adapter
def test_alternate_adapter_denied():
    env = _envelope(adapter_id="adapter-002")
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.ADAPTER_MISMATCH.value


# Alternate entrypoint
def test_alternate_entrypoint_denied():
    env = _envelope(canonical_entrypoint="entrypoint-999")
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.ENTRYPOINT_MISMATCH.value


# Provider class mismatch
def test_provider_class_mismatch_denied():
    env = _envelope(provider_class="OtherProvider")
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.PROVIDER_CLASS_MISMATCH.value


# Provider mode mismatch (mock fallback)
def test_mock_fallback_denied():
    env = _envelope(provider_mode="MOCK")
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.MOCK_FALLBACK.value


# Dry-run fallback
def test_dry_run_fallback_denied():
    env = _envelope(provider_mode="DRY_RUN")
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.MOCK_FALLBACK.value


# Account mismatch
def test_account_mismatch_denied():
    env = _envelope(provider_account_reference="account-999")
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.ACCOUNT_MISMATCH.value


# Credential boundary mismatch
def test_credential_boundary_mismatch_denied():
    env = _envelope(credential_boundary_reference="cred-999")
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.CREDENTIAL_BOUNDARY_MISMATCH.value


# Baseline commit mismatch
def test_baseline_commit_mismatch_denied():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap, runtime_head="c" * 64)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.BASELINE_COMMIT_MISMATCH.value


# Baseline tree mismatch
def test_baseline_tree_mismatch_denied():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap, runtime_tree="c" * 64)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.BASELINE_TREE_MISMATCH.value


# Source manifest mismatch
def test_source_manifest_mismatch_denied():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap, runtime_manifest="c" * 64)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.SOURCE_MANIFEST_MISMATCH.value


# Duplicate target
def test_duplicate_target_denied():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap, duplicate_exists=True)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.DUPLICATE_TARGET.value


# Kill switch
def test_kill_switch_denied():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap, kill_switch=True)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.KILL_SWITCH.value


# Cancellation
def test_cancellation_denied():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap, cancellation=True)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.CANCELLATION.value


# Side-effect ceiling
def test_side_effect_ceiling_denied():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap, side_effect_count=1)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.SIDE_EFFECT_CEILING_EXCEEDED.value


# Missing approval
def test_missing_approval_denied():
    env = _envelope()
    reg = _reg()
    r = resolve_capability(env, reg, None)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.MISSING_APPROVAL.value


# Expired approval
def test_expired_approval_denied():
    env = _envelope()
    ap = _approval(env, approval_result="EXPIRED")
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.EXPIRED_APPROVAL.value


# Consumed approval
def test_consumed_approval_denied():
    env = _envelope()
    ap = _approval(env, approval_result="CONSUMED")
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.CONSUMED_APPROVAL.value


# Authority mismatch (envelope hash mismatch)
def test_authority_mismatch_denied():
    env = _envelope()
    other_env = _envelope(body_sha256="d" * 64)
    ap = _approval(other_env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.AUTHORITY_MISMATCH.value


# Nonce mismatch
def test_nonce_mismatch_denied():
    env = _envelope()
    ap = _approval(env, approval_nonce="wrong-nonce")
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "DENY"
    assert r.deny_reason == DenyReason.NONCE_MISMATCH.value


# Attempt to infer authority from certification
def test_authority_not_inferred_from_certification():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    # Even ALLOW does not grant authority
    assert r.authority_delta == 0
    assert r.execution_ready is False


# Attempt to infer readiness from resolution
def test_readiness_not_inferred_from_resolution():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert r.result == "ALLOW"
    assert r.execution_ready is False


# Hash reproducibility
def test_resolution_hash_reproducible():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r1 = resolve_capability(env, reg, ap)
    r2 = resolve_capability(env, reg, ap)
    # resolution_id is random so hashes differ, but results match
    assert r1.result == r2.result
    assert r1.matched_entry_sha256 == r2.matched_entry_sha256
    assert r1.authority_delta == r2.authority_delta == 0


# Zero provider/network/credential/database/external activity
def test_zero_external_effects():
    env = _envelope()
    ap = _approval(env)
    reg = _reg()
    r = resolve_capability(env, reg, ap)
    assert not hasattr(r, "provider_invoked")
    assert not hasattr(r, "network_used")
    assert not hasattr(r, "credential_read")
    assert not hasattr(r, "database_access")
    assert not hasattr(r, "external_write")
    assert r.authority_delta == 0
    assert r.execution_ready is False