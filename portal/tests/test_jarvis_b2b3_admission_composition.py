"""INT-ADMISSION-COMPOSITION-001 corrective certification suite.

Proves the corrected admission gate:
  admission_allowed(REVIEWED)  = TRUE   (proceeds toward approval)
  admission_allowed(DISCOVERED/APPROVED/SANDBOXED/TRUSTED/REVOKED/
                    QUARANTINED_BY_DEPENDENCY/REVALIDATION_REQUIRED) = FALSE

Permanent invariants asserted here:
  ADMISSION != EXECUTION AUTHORITY
    ADMISSION_ELIGIBLE does NOT create a lease, does NOT create a credential
    grant, does NOT make the capability executable, provider calls = 0,
    external effects = 0.
  Contract identity binding: an admission result is bound to the exact
  (capability_id, capability_version, contract_hash, tenant_id). Contract
  identity drift invalidates prior admission evidence and requires
  re-review / re-admission.

State machine (frozen, asserted permanently):
  DISCOVERED -> REVIEWED -> ADMISSION -> APPROVED -> SANDBOXED -> TRUSTED -> EXECUTION
  admission_allowed(REVIEWED)  = TRUE,  execution_allowed(REVIEWED)  = FALSE
  admission_allowed(TRUSTED)   = FALSE, execution_allowed(TRUSTED)   = TRUE
"""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.jarvis_b2_durability import (
    JarvisAuthorityLeaseRecord,
    JarvisCredentialStateRecord,
)
from portal.models.jarvis_capability_registry import (
    EffectiveStatus,
    LifecycleStatus,
    RevocationReason,
)
from portal.services.jarvis_capability_admission import admit_for_approval
from portal.services.jarvis_capability_contract import CapabilityContract
from portal.services.jarvis_capability_registry import CapabilityRegistryService

pytestmark = pytest.mark.asyncio


def _contract(
    capability_id: str = "github.issue.add_label",
    consequence: str = "reversible",
) -> CapabilityContract:
    """Valid contract; hash is computed internally from content, so any
    content difference (e.g. consequence) yields a different contract_hash."""
    return CapabilityContract(
        capability_id=capability_id,
        capability_version="1.0.0",
        allowed_operations=("github.issue.add_label",),
        allowed_targets=("github.issue:owner/repo#1",),
        risk="low",
        consequence=consequence,
        authority="tenant_principal",
        credential="github_token",
        executor_id="jarvis_action_executor",
        adapter_id="github_label_adapter",
        verification="independent_refetch",
        idempotency="label_already_present",
        reconciliation="refetch_on_timeout",
        rollback="remove_label",
        lease="single_request",
        revocation="approval_consumed",
        receipt="hash_chain_append",
        memory="bounded_writeback",
        brief="governed action",
    )


@pytest.fixture
async def db_session():
    """Provide an in-memory SQLite session for testing."""
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def other_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def actor_id():
    return uuid.uuid4()


@pytest.fixture
def registry_service():
    return CapabilityRegistryService()


async def _register_and_review(session, tenant, actor, contract, service):
    await service.register_capability(
        session=session, tenant_id=tenant, contract=contract,
        owner_principal=actor, actor_id=actor,
    )
    await session.flush()
    await service.transition_to_reviewed(
        session=session, tenant_id=tenant,
        capability_id=contract.capability_id,
        capability_version=contract.capability_version,
        contract_hash=contract.contract_hash,
        actor_id=actor,
    )
    await session.flush()


# ═══════════════════════════════════════════════════════════════════════
# Corrected admission matrix
# ═══════════════════════════════════════════════════════════════════════


async def test_reviewed_capability_is_admissible(db_session, tenant_id, actor_id, registry_service):
    contract = _contract()
    await _register_and_review(db_session, tenant_id, actor_id, contract, registry_service)
    result = await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=contract)
    assert result.approved is True
    assert result.reason_code == "ADMISSION_ELIGIBLE"
    assert result.capability_id == contract.capability_id
    assert result.capability_version == contract.capability_version
    assert result.contract_hash == contract.contract_hash
    assert result.provider_calls == 0


async def test_discovered_is_denied(db_session, tenant_id, actor_id, registry_service):
    contract = _contract()
    await registry_service.register_capability(
        session=db_session, tenant_id=tenant_id, contract=contract,
        owner_principal=actor_id, actor_id=actor_id,
    )
    await db_session.flush()
    result = await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=contract)
    assert result.approved is False
    assert result.reason_code == "LIFECYCLE_NOT_REVIEWED"


async def test_approved_is_denied_by_admission_stage_check(db_session, tenant_id, actor_id, registry_service):
    contract = _contract()
    await _register_and_review(db_session, tenant_id, actor_id, contract, registry_service)
    await registry_service.transition_to_approved(
        session=db_session, tenant_id=tenant_id,
        capability_id=contract.capability_id,
        capability_version=contract.capability_version,
        contract_hash=contract.contract_hash,
        actor_id=actor_id,
        approval_policy_ref="approval_policy_v1",
        credential_policy_ref="credential_policy_v1",
        verification_policy_ref="verification_policy_v1",
    )
    await db_session.flush()
    result = await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=contract)
    assert result.approved is False
    assert result.reason_code == "LIFECYCLE_NOT_REVIEWED"


async def test_trusted_is_denied_by_admission_stage_check(db_session, tenant_id, actor_id, registry_service):
    contract = _contract()
    await _register_and_review(db_session, tenant_id, actor_id, contract, registry_service)
    await registry_service.transition_to_approved(
        session=db_session, tenant_id=tenant_id,
        capability_id=contract.capability_id,
        capability_version=contract.capability_version,
        contract_hash=contract.contract_hash,
        actor_id=actor_id,
        approval_policy_ref="approval_policy_v1",
        credential_policy_ref="credential_policy_v1",
        verification_policy_ref="verification_policy_v1",
    )
    await registry_service.transition_to_sandboxed(
        session=db_session, tenant_id=tenant_id,
        capability_id=contract.capability_id,
        capability_version=contract.capability_version,
        contract_hash=contract.contract_hash,
        actor_id=actor_id,
    )
    await registry_service.transition_to_trusted(
        session=db_session, tenant_id=tenant_id,
        capability_id=contract.capability_id,
        capability_version=contract.capability_version,
        contract_hash=contract.contract_hash,
        actor_id=actor_id, certifier_id=actor_id,
    )
    await db_session.flush()
    result = await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=contract)
    assert result.approved is False
    assert result.reason_code == "LIFECYCLE_NOT_REVIEWED"


async def test_revoked_is_denied(db_session, tenant_id, actor_id, registry_service):
    contract = _contract()
    await _register_and_review(db_session, tenant_id, actor_id, contract, registry_service)
    await registry_service.revoke_capability(
        session=db_session, tenant_id=tenant_id,
        capability_id=contract.capability_id,
        capability_version=contract.capability_version,
        contract_hash=contract.contract_hash,
        actor_id=actor_id,
        reason=RevocationReason.MANUAL_REVOCATION,
    )
    await db_session.flush()
    result = await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=contract)
    assert result.approved is False
    assert result.reason_code == "LIFECYCLE_NOT_REVIEWED"


async def test_quarantined_by_dependency_is_denied(db_session, tenant_id, actor_id, registry_service):
    dependency = _contract()
    await _register_and_review(db_session, tenant_id, actor_id, dependency, registry_service)

    dependent = _contract(capability_id="github.issue.close")
    await registry_service.register_capability(
        session=db_session, tenant_id=tenant_id, contract=dependent,
        owner_principal=actor_id, actor_id=actor_id,
        dependency_ids=["github.issue.add_label"],
    )
    await db_session.flush()
    await registry_service.transition_to_reviewed(
        session=db_session, tenant_id=tenant_id,
        capability_id=dependent.capability_id,
        capability_version=dependent.capability_version,
        contract_hash=dependent.contract_hash,
        actor_id=actor_id,
    )
    await db_session.flush()

    await registry_service.revoke_capability(
        session=db_session, tenant_id=tenant_id,
        capability_id=dependency.capability_id,
        capability_version=dependency.capability_version,
        contract_hash=dependency.contract_hash,
        actor_id=actor_id,
        reason=RevocationReason.DEPENDENCY_FAILURE,
    )
    await db_session.flush()

    reg = await registry_service.get_current_registration(
        db_session, tenant_id, dependent.capability_id, dependent.capability_version
    )
    assert reg.lifecycle_state == LifecycleStatus.REVIEWED.value
    assert reg.effective_state == EffectiveStatus.QUARANTINED_BY_DEPENDENCY.value
    result = await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=dependent)
    assert result.approved is False
    assert result.reason_code == "REGISTRY_NOT_ADMISSIBLE"


async def test_revalidation_required_is_denied(db_session, tenant_id, actor_id, registry_service):
    contract = _contract()
    await _register_and_review(db_session, tenant_id, actor_id, contract, registry_service)
    # REVALIDATION_REQUIRED has no public transition path (frozen semantics);
    # seed the derived state directly the way an operator flag would land it.
    reg = await registry_service.get_current_registration(
        db_session, tenant_id, contract.capability_id, contract.capability_version
    )
    reg.effective_state = EffectiveStatus.REVALIDATION_REQUIRED.value
    await db_session.flush()
    result = await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=contract)
    assert result.approved is False
    assert result.reason_code == "REGISTRY_NOT_ADMISSIBLE"


async def test_tenant_mismatch_is_denied(db_session, tenant_id, other_tenant_id, actor_id, registry_service):
    contract = _contract()
    await _register_and_review(db_session, tenant_id, actor_id, contract, registry_service)
    result = await admit_for_approval(session=db_session, tenant_id=other_tenant_id, contract=contract)
    assert result.approved is False
    assert result.reason_code == "TENANT_OR_CAPABILITY_NOT_FOUND"


# ═══════════════════════════════════════════════════════════════════════
# ADMISSION != EXECUTION AUTHORITY
# ═══════════════════════════════════════════════════════════════════════


async def test_admission_confers_no_execution_authority(db_session, tenant_id, actor_id, registry_service):
    contract = _contract()
    await _register_and_review(db_session, tenant_id, actor_id, contract, registry_service)
    result = await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=contract)
    assert result.approved is True

    reg = await registry_service.get_current_registration(
        db_session, tenant_id, contract.capability_id, contract.capability_version
    )
    assert reg.lifecycle_state == LifecycleStatus.REVIEWED.value
    assert reg.effective_executable is False
    assert await registry_service.check_execution_eligibility(
        db_session, tenant_id, contract.capability_id,
        contract.capability_version, contract.contract_hash,
    ) is False

    leases = (await db_session.execute(select(JarvisAuthorityLeaseRecord))).scalars().all()
    credentials = (await db_session.execute(select(JarvisCredentialStateRecord))).scalars().all()
    assert leases == []
    assert credentials == []
    assert result.provider_calls == 0


async def test_state_machine_admission_vs_execution_is_permanent(db_session, tenant_id, actor_id, registry_service):
    contract = _contract()
    await _register_and_review(db_session, tenant_id, actor_id, contract, registry_service)

    async def _admission():
        return await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=contract)

    async def _execution():
        return await registry_service.check_execution_eligibility(
            db_session, tenant_id, contract.capability_id,
            contract.capability_version, contract.contract_hash,
        )

    reg_stage = await registry_service.get_current_registration(
        db_session, tenant_id, contract.capability_id, contract.capability_version
    )
    assert reg_stage is not None
    assert reg_stage.lifecycle_state == LifecycleStatus.REVIEWED.value
    assert (await _admission()).approved is True
    assert (await _execution()) is False

    await registry_service.transition_to_approved(
        session=db_session, tenant_id=tenant_id,
        capability_id=contract.capability_id,
        capability_version=contract.capability_version,
        contract_hash=contract.contract_hash,
        actor_id=actor_id,
        approval_policy_ref="approval_policy_v1",
        credential_policy_ref="credential_policy_v1",
        verification_policy_ref="verification_policy_v1",
    )
    await db_session.flush()
    assert (await _admission()).approved is False
    assert (await _execution()) is False

    await registry_service.transition_to_sandboxed(
        session=db_session, tenant_id=tenant_id,
        capability_id=contract.capability_id,
        capability_version=contract.capability_version,
        contract_hash=contract.contract_hash,
        actor_id=actor_id,
    )
    await registry_service.transition_to_trusted(
        session=db_session, tenant_id=tenant_id,
        capability_id=contract.capability_id,
        capability_version=contract.capability_version,
        contract_hash=contract.contract_hash,
        actor_id=actor_id, certifier_id=actor_id,
    )
    await db_session.flush()
    assert (await _admission()).approved is False
    assert (await _execution()) is True


# ═══════════════════════════════════════════════════════════════════════
# Historical identity continuity
# ═══════════════════════════════════════════════════════════════════════


async def test_historical_admission_binding_and_contract_identity_drift(
    db_session, tenant_id, actor_id, registry_service,
):
    contract = _contract()
    await _register_and_review(db_session, tenant_id, actor_id, contract, registry_service)

    admitted = await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=contract)
    assert admitted.approved is True
    assert admitted.capability_id == contract.capability_id
    assert admitted.capability_version == contract.capability_version
    assert admitted.contract_hash == contract.contract_hash
    assert admitted.tenant_id == str(tenant_id)

    reg = await registry_service.get_current_registration(
        db_session, tenant_id, contract.capability_id, contract.capability_version
    )
    assert reg.contract_hash == admitted.contract_hash

    # Contract identity drift: same id/version, different content →
    # different hash → prior admission evidence is INVALID for the new
    # contract; re-review / re-admission is required.
    drifted = _contract(consequence="reversible-v2")
    assert drifted.capability_id == contract.capability_id
    assert drifted.capability_version == contract.capability_version
    assert drifted.contract_hash != contract.contract_hash
    drift_result = await admit_for_approval(session=db_session, tenant_id=tenant_id, contract=drifted)
    assert drift_result.approved is False
    assert drift_result.reason_code == "CONTRACT_HASH_MISMATCH"
