"""B2-B3 admission gate: local, fail-closed, no provider integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from portal.models.jarvis_capability_registry import EffectiveStatus, LifecycleStatus
from portal.services.jarvis_capability_contract import CapabilityContract
from portal.services.jarvis_capability_registry import CapabilityRegistryService


@dataclass(frozen=True)
class AdmissionResult:
    approved: bool
    reason_code: str
    capability_id: str
    capability_version: str
    contract_hash: str
    tenant_id: str
    registry_revision: int | None
    provider_calls: int = 0


async def admit_for_approval(
    *,
    session: Any,
    tenant_id: Any,
    contract: CapabilityContract,
    expected_revision: int | None = None,
    registry_service: CapabilityRegistryService | None = None,
) -> AdmissionResult:
    """Admit a reviewed registry record for the approval pipeline.

    ADMISSION != EXECUTION AUTHORITY (INT-ADMISSION-COMPOSITION-001 correction):
    admission decides whether a REVIEWED capability may proceed toward
    approval; it does NOT require and does NOT confer execution authority.
    Execution eligibility remains separately enforced at TRUSTED via
    effective_executable in the B2-B4 lease/credential/receipt chain.

    CapabilityContract construction remains the single contract validator.
    This gate does not promote state or call a provider.
    """
    service = registry_service or CapabilityRegistryService()
    registration = await service.get_current_registration(
        session, tenant_id, contract.capability_id, contract.capability_version
    )
    if registration is None:
        return AdmissionResult(False, "TENANT_OR_CAPABILITY_NOT_FOUND", contract.capability_id, contract.capability_version, contract.contract_hash, str(tenant_id), None)
    if registration.contract_hash != contract.contract_hash:
        return AdmissionResult(False, "CONTRACT_HASH_MISMATCH", contract.capability_id, contract.capability_version, contract.contract_hash, str(tenant_id), registration.registry_revision)
    if expected_revision is not None and registration.registry_revision != expected_revision:
        return AdmissionResult(False, "STALE_REGISTRY_REVISION", contract.capability_id, contract.capability_version, contract.contract_hash, str(tenant_id), registration.registry_revision)
    if registration.lifecycle_state != LifecycleStatus.REVIEWED.value:
        return AdmissionResult(False, "LIFECYCLE_NOT_REVIEWED", contract.capability_id, contract.capability_version, contract.contract_hash, str(tenant_id), registration.registry_revision)
    # Admission-stage protections (INT-ADMISSION-COMPOSITION-001):
    # fail closed on revoked / dependency-quarantined / revalidation-required
    # states. effective_executable is deliberately NOT required here — at
    # REVIEWED it is always False by frozen registry semantics, and admission
    # does not confer execution authority (see invariant above).
    if registration.effective_state in {
        EffectiveStatus.REVOKED.value,
        EffectiveStatus.QUARANTINED_BY_DEPENDENCY.value,
        EffectiveStatus.REVALIDATION_REQUIRED.value,
    }:
        return AdmissionResult(False, "REGISTRY_NOT_ADMISSIBLE", contract.capability_id, contract.capability_version, contract.contract_hash, str(tenant_id), registration.registry_revision)
    return AdmissionResult(True, "ADMISSION_ELIGIBLE", contract.capability_id, contract.capability_version, contract.contract_hash, str(tenant_id), registration.registry_revision)
