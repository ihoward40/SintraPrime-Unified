"""L2-I8 deterministic capability resolution — C-01 through C-10, zero authority delta.

Resolves an ActionEnvelope against the CapabilityRegistry, verifying:
- exact capability/version/adapter/entrypoint/provider/account/boundary match (C-01)
- no alias/expansion (C-02)
- envelope-supplied execution_id (C-03)
- envelope-supplied nonce (C-04)
- execution_id/nonce binding (C-05)
- no auto-generation (C-06)
- no mock/dry-run fallback (C-07)
- account/boundary match (C-08)
- baseline integrity (C-09)
- target/duplicate/kill-switch (C-10)

No provider invocation, no credential access, no network, no side effects.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Optional

from sintra_live.l2.action_envelope_contract import ActionEnvelope
from sintra_live.l2.capability_registry import CapabilityRegistry, CapabilityRegistryError
from sintra_live.l2.capability_registry_contract import (
    CapabilityResolutionRecord,
    DenyReason,
    ResolutionResult,
    SCHEMA_VERSION,
)
from sintra_live.l2.principal_approval_contract import (
    ApprovalState,
    PrincipalApprovalRecord,
)


def _new_resolution_id() -> str:
    return f"capres-{uuid.uuid4().hex[:16]}"


def resolve_capability(
    envelope: ActionEnvelope,
    registry: CapabilityRegistry,
    approval: Optional[PrincipalApprovalRecord] = None,
    approval_state: Optional[ApprovalState] = None,
    runtime_head: Optional[str] = None,
    runtime_tree: Optional[str] = None,
    runtime_manifest: Optional[str] = None,
    target_open: bool = True,
    target_exists: bool = True,
    duplicate_exists: bool = False,
    kill_switch: bool = False,
    cancellation: bool = False,
    side_effect_count: int = 0,
) -> CapabilityResolutionRecord:
    """Deterministic capability resolution with C-01 through C-10 checks.

    Returns a CapabilityResolutionRecord with result ALLOW/DENY/INCOMPLETE.
    authority_delta is always 0. execution_ready is always False.
    """
    deny_reason = ""
    matched_sha = ""

    # C-03: missing execution ID
    if not envelope.execution_id:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.MISSING_EXECUTION_ID.value,
            matched_entry_sha256="",
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # C-04: missing nonce
    if not envelope.nonce:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.MISSING_NONCE.value,
            matched_entry_sha256="",
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # C-01/C-02: exact registry lookup (no alias expansion)
    try:
        entry = registry.lookup_exact(
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
        )
        matched_sha = entry.capability_entry_sha256
    except CapabilityRegistryError as exc:
        msg = str(exc)
        if "UNKNOWN" in msg:
            deny_reason = DenyReason.UNKNOWN_CAPABILITY.value
        elif "DEPRECATED" in msg:
            deny_reason = DenyReason.DEPRECATED_CAPABILITY.value
        elif "ADAPTER" in msg:
            deny_reason = DenyReason.ADAPTER_MISMATCH.value
        elif "ENTRYPOINT" in msg:
            deny_reason = DenyReason.ENTRYPOINT_MISMATCH.value
        else:
            deny_reason = DenyReason.INVALID_INPUT.value
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=deny_reason,
            matched_entry_sha256="",
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # C-07: mock/dry-run fallback denied
    if envelope.provider_mode != entry.provider_mode:
        if entry.provider_mode == "LIVE" and envelope.provider_mode in ("MOCK", "DRY_RUN"):
            deny_reason = DenyReason.MOCK_FALLBACK.value
        else:
            deny_reason = DenyReason.PROVIDER_MODE_MISMATCH.value
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=deny_reason,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # C-01: provider class match
    if envelope.provider_class != entry.provider_class:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.PROVIDER_CLASS_MISMATCH.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # C-08: account/boundary match
    if envelope.provider_account_reference != entry.provider_account_reference:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.ACCOUNT_MISMATCH.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    if envelope.credential_boundary_reference != entry.credential_boundary_reference:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.CREDENTIAL_BOUNDARY_MISMATCH.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # C-09: baseline integrity
    if runtime_head is not None and runtime_head != envelope.baseline_commit_sha:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.BASELINE_COMMIT_MISMATCH.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    if runtime_tree is not None and runtime_tree != envelope.baseline_tree_sha:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.BASELINE_TREE_MISMATCH.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    if runtime_manifest is not None and runtime_manifest != envelope.execution_source_manifest_sha256:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.SOURCE_MANIFEST_MISMATCH.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # C-10: target/duplicate/kill-switch
    if not target_exists:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.TARGET_MISSING.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    if not target_open:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.TARGET_CLOSED.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    if duplicate_exists:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.DUPLICATE_TARGET.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    if kill_switch:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.KILL_SWITCH.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    if cancellation:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.CANCELLATION.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # Side-effect ceiling check
    if side_effect_count >= envelope.side_effect_ceiling:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.SIDE_EFFECT_CEILING_EXCEEDED.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # Approval checks
    if approval is None:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.MISSING_APPROVAL.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # C-05: execution ID / nonce binding via approval
    if approval.action_envelope_sha256 != envelope.action_envelope_sha256:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.AUTHORITY_MISMATCH.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    if approval.approval_nonce != envelope.nonce:
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.NONCE_MISMATCH.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    if approval.approval_result == "EXPIRED":
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.EXPIRED_APPROVAL.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    if approval.approval_result == "CONSUMED":
        return CapabilityResolutionRecord(
            schema_version=SCHEMA_VERSION,
            resolution_id=_new_resolution_id(),
            capability_id=envelope.capability_id,
            capability_version=envelope.capability_version,
            result=ResolutionResult.DENY.value,
            deny_reason=DenyReason.CONSUMED_APPROVAL.value,
            matched_entry_sha256=matched_sha,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            canonical_entrypoint=envelope.canonical_entrypoint,
            provider_class=envelope.provider_class,
            provider_mode=envelope.provider_mode,
            provider_account_reference=envelope.provider_account_reference,
            credential_boundary_reference=envelope.credential_boundary_reference,
            authority_delta=0,
            execution_ready=False,
        )

    # C-01: ALLOW — all checks passed
    return CapabilityResolutionRecord(
        schema_version=SCHEMA_VERSION,
        resolution_id=_new_resolution_id(),
        capability_id=envelope.capability_id,
        capability_version=envelope.capability_version,
        result=ResolutionResult.ALLOW.value,
        deny_reason="",
        matched_entry_sha256=matched_sha,
        adapter_id=envelope.adapter_id,
        adapter_version=envelope.adapter_version,
        canonical_entrypoint=envelope.canonical_entrypoint,
        provider_class=envelope.provider_class,
        provider_mode=envelope.provider_mode,
        provider_account_reference=envelope.provider_account_reference,
        credential_boundary_reference=envelope.credential_boundary_reference,
        authority_delta=0,
        execution_ready=False,
    )


__all__ = ["resolve_capability"]