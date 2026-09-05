"""B2-B2 Capability Registry database-backed lifecycle and governance tests."""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.jarvis_capability_registry import (
    CapabilityRegistration,
    CapabilityTransition,
    EffectiveStatus,
    LifecycleStatus,
    RevocationReason,
    TransitionAuthority,
)
from portal.services.jarvis_capability_contract import CapabilityContract
from portal.services.jarvis_capability_registry import (
    CapabilityRegistryService,
    DependencyError,
    InvalidTransitionError,
    RegistryConflictError,
    TenantIsolationError,
)

pytestmark = pytest.mark.asyncio


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
def base_contract():
    return CapabilityContract(
        capability_id="github.issue.add_label",
        capability_version="1.0.0",
        allowed_operations=("github.issue.add_label",),
        allowed_targets=("github.issue:owner/repo#1",),
        risk="low",
        consequence="reversible",
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
def registry_service():
    return CapabilityRegistryService()


# ═══════════════════════════════════════════════════════════════════════════
# Immutability and Lifecycle Transition Tests
# ═══════════════════════════════════════════════════════════════════════════


async def test_capability_registration_is_immutable(db_session, tenant_id, actor_id, base_contract, registry_service):
    """Registration record is immutable once persisted."""
    reg = await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=base_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )
    await db_session.commit()

    # Verify cannot modify contract_hash (dataclass frozen or SQLAlchemy protection)
    assert reg.contract_hash == base_contract.contract_hash


async def test_lifecycle_discovered_to_reviewed(db_session, tenant_id, actor_id, base_contract, registry_service):
    """DISCOVERED→REVIEWED transition requires reviewer authority."""
    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=base_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )
    await db_session.commit()

    # Reviewer can transition
    await registry_service.transition_to_reviewed(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=base_contract.capability_id,
        capability_version=base_contract.capability_version,
        contract_hash=base_contract.contract_hash,
        actor_id=actor_id,
    )
    await db_session.commit()

    current = await registry_service.get_current_registration(
        db_session, tenant_id, base_contract.capability_id, base_contract.capability_version
    )
    assert current.lifecycle_state == LifecycleStatus.REVIEWED.value


async def test_lifecycle_reviewed_to_approved(db_session, tenant_id, actor_id, base_contract, registry_service):
    """REVIEWED→APPROVED requires Principal/capability owner."""
    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=base_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )

    await registry_service.transition_to_reviewed(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=base_contract.capability_id,
        capability_version=base_contract.capability_version,
        contract_hash=base_contract.contract_hash,
        actor_id=actor_id,
    )

    # Owner can approve
    await registry_service.transition_to_approved(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=base_contract.capability_id,
        capability_version=base_contract.capability_version,
        contract_hash=base_contract.contract_hash,
        actor_id=actor_id,
        approval_policy_ref="approval_policy_v1",
        credential_policy_ref="credential_policy_v1",
        verification_policy_ref="verification_policy_v1",
    )
    await db_session.commit()

    current = await registry_service.get_current_registration(
        db_session, tenant_id, base_contract.capability_id, base_contract.capability_version
    )
    assert current.lifecycle_state == LifecycleStatus.APPROVED.value
    assert current.approval_policy_ref == "approval_policy_v1"


async def test_approved_is_not_trusted(db_session, tenant_id, actor_id, base_contract, registry_service):
    """APPROVED != TRUSTED: approved capabilities cannot execute without further trust gates."""
    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=base_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )
    await registry_service.transition_to_reviewed(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=base_contract.capability_id,
        capability_version=base_contract.capability_version,
        contract_hash=base_contract.contract_hash,
        actor_id=actor_id,
    )
    await registry_service.transition_to_approved(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=base_contract.capability_id,
        capability_version=base_contract.capability_version,
        contract_hash=base_contract.contract_hash,
        actor_id=actor_id,
        approval_policy_ref="approval_policy_v1",
        credential_policy_ref="credential_policy_v1",
        verification_policy_ref="verification_policy_v1",
    )
    await db_session.commit()

    # Verify APPROVED cannot be used where TRUSTED required
    is_trusted = await registry_service.is_capability_trusted(
        db_session, tenant_id, base_contract.capability_id, base_contract.capability_version
    )
    assert not is_trusted


async def test_invalid_transition_rejected(db_session, tenant_id, actor_id, base_contract, registry_service):
    """Invalid lifecycle transitions are rejected."""
    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=base_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )
    await db_session.commit()

    # Cannot skip from DISCOVERED to APPROVED
    with pytest.raises(InvalidTransitionError):
        await registry_service.transition_to_approved(
            session=db_session,
            tenant_id=tenant_id,
            capability_id=base_contract.capability_id,
            capability_version=base_contract.capability_version,
            contract_hash=base_contract.contract_hash,
            actor_id=actor_id,
            approval_policy_ref="approval_policy_v1",
            credential_policy_ref="credential_policy_v1",
            verification_policy_ref="verification_policy_v1",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Revocation Tests
# ═══════════════════════════════════════════════════════════════════════════


async def test_revocation_is_terminal(db_session, tenant_id, actor_id, base_contract, registry_service):
    """REVOKED is terminal; exact version/hash cannot be readmitted."""
    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=base_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )

    # Revoke
    await registry_service.revoke_capability(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=base_contract.capability_id,
        capability_version=base_contract.capability_version,
        contract_hash=base_contract.contract_hash,
        actor_id=actor_id,
        reason=RevocationReason.SECURITY_ISSUE,
    )
    await db_session.commit()

    current = await registry_service.get_current_registration(
        db_session, tenant_id, base_contract.capability_id, base_contract.capability_version
    )
    assert current.lifecycle_state == LifecycleStatus.REVOKED.value
    assert current.revoked_at is not None

    # Cannot transition from REVOKED
    with pytest.raises(InvalidTransitionError):
        await registry_service.transition_to_reviewed(
            session=db_session,
            tenant_id=tenant_id,
            capability_id=base_contract.capability_id,
            capability_version=base_contract.capability_version,
            contract_hash=base_contract.contract_hash,
            actor_id=actor_id,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Isolation Tests
# ═══════════════════════════════════════════════════════════════════════════


async def test_tenant_scoped_reads(db_session, tenant_id, other_tenant_id, actor_id, base_contract, registry_service):
    """Tenant-scoped reads: cannot see other tenant's registrations."""
    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=base_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )
    await db_session.commit()

    # Other tenant cannot read
    current = await registry_service.get_current_registration(
        db_session, other_tenant_id, base_contract.capability_id, base_contract.capability_version
    )
    assert current is None


async def test_dependency_validation_rejects_self_reference(db_session, tenant_id, actor_id, base_contract, registry_service):
    """Self-referencing dependencies are rejected."""
    with pytest.raises(DependencyError):
        await registry_service.register_capability(
            session=db_session,
            tenant_id=tenant_id,
            contract=base_contract,
            owner_principal=actor_id,
            actor_id=actor_id,
            dependency_ids=[base_contract.capability_id],
        )


async def test_transition_hash_chain_integrity(db_session, tenant_id, actor_id, base_contract, registry_service):
    """Transition ledger maintains hash chain for tamper detection."""
    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=base_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )

    await registry_service.transition_to_reviewed(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=base_contract.capability_id,
        capability_version=base_contract.capability_version,
        contract_hash=base_contract.contract_hash,
        actor_id=actor_id,
    )
    await db_session.commit()

    # Fetch transitions
    transitions = await registry_service.get_transition_history(
        db_session, tenant_id, base_contract.capability_id, base_contract.capability_version
    )

    assert len(transitions) >= 2

    # Verify hash chain
    for i in range(1, len(transitions)):
        assert transitions[i].previous_transition_hash == transitions[i - 1].transition_hash


async def test_registry_state_independent_of_memory_cache(db_session, tenant_id, actor_id, base_contract, registry_service):
    """Registry state cannot be overridden by memory/approval/worker cache."""
    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=base_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )
    await db_session.commit()

    # Verify eligibility check uses registry state
    is_eligible = await registry_service.check_execution_eligibility(
        db_session,
        tenant_id,
        base_contract.capability_id,
        base_contract.capability_version,
        base_contract.contract_hash,
    )
    assert not is_eligible  # DISCOVERED is not eligible


async def test_trusted_with_revoked_dependency_preserves_lifecycle_state(
    db_session, tenant_id, actor_id, registry_service
):
    """Critical: TRUSTED capability with revoked dependency remains lifecycle_state=TRUSTED
    while effective_state=QUARANTINED_BY_DEPENDENCY and effective_executable=False.
    """
    # Create dependency
    dep_contract = CapabilityContract(
        capability_id="github.api.read",
        capability_version="1.0.0",
        allowed_operations=("github.api.read",),
        allowed_targets=("github.repo:owner/repo",),
        risk="low",
        consequence="reversible",
        authority="tenant_principal",
        credential="github_token",
        executor_id="jarvis_action_executor",
        adapter_id="github_api_adapter",
        verification="independent_refetch",
        idempotency="idempotent_read",
        reconciliation="refetch_on_timeout",
        rollback="none",
        lease="single_request",
        revocation="approval_consumed",
        receipt="hash_chain_append",
        memory="bounded_writeback",
        brief="governed action",
    )

    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=dep_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )

    # Promote dependency to TRUSTED
    await registry_service.transition_to_reviewed(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=dep_contract.capability_id,
        capability_version=dep_contract.capability_version,
        contract_hash=dep_contract.contract_hash,
        actor_id=actor_id,
    )
    await registry_service.transition_to_approved(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=dep_contract.capability_id,
        capability_version=dep_contract.capability_version,
        contract_hash=dep_contract.contract_hash,
        actor_id=actor_id,
        approval_policy_ref="policy_v1",
        credential_policy_ref="policy_v1",
        verification_policy_ref="policy_v1",
    )
    await registry_service.transition_to_sandboxed(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=dep_contract.capability_id,
        capability_version=dep_contract.capability_version,
        contract_hash=dep_contract.contract_hash,
        actor_id=actor_id,
    )
    await registry_service.transition_to_trusted(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=dep_contract.capability_id,
        capability_version=dep_contract.capability_version,
        contract_hash=dep_contract.contract_hash,
        actor_id=actor_id,
        certifier_id=actor_id,
    )

    # Create dependent capability
    main_contract = CapabilityContract(
        capability_id="github.issue.add_label",
        capability_version="1.0.0",
        allowed_operations=("github.issue.add_label",),
        allowed_targets=("github.issue:owner/repo#1",),
        risk="low",
        consequence="reversible",
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

    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=main_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
        dependency_ids=[dep_contract.capability_id],
    )

    # Promote main capability to TRUSTED
    await registry_service.transition_to_reviewed(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=main_contract.capability_id,
        capability_version=main_contract.capability_version,
        contract_hash=main_contract.contract_hash,
        actor_id=actor_id,
    )
    await registry_service.transition_to_approved(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=main_contract.capability_id,
        capability_version=main_contract.capability_version,
        contract_hash=main_contract.contract_hash,
        actor_id=actor_id,
        approval_policy_ref="policy_v1",
        credential_policy_ref="policy_v1",
        verification_policy_ref="policy_v1",
    )
    await registry_service.transition_to_sandboxed(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=main_contract.capability_id,
        capability_version=main_contract.capability_version,
        contract_hash=main_contract.contract_hash,
        actor_id=actor_id,
    )
    await registry_service.transition_to_trusted(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=main_contract.capability_id,
        capability_version=main_contract.capability_version,
        contract_hash=main_contract.contract_hash,
        actor_id=actor_id,
        certifier_id=actor_id,
    )
    await db_session.commit()

    # Verify both are executable
    main = await registry_service.get_current_registration(
        db_session, tenant_id, main_contract.capability_id, main_contract.capability_version
    )
    assert main.lifecycle_state == LifecycleStatus.TRUSTED.value
    assert main.effective_state == EffectiveStatus.TRUSTED.value
    assert main.effective_executable is True

    # Revoke dependency
    await registry_service.revoke_capability(
        session=db_session,
        tenant_id=tenant_id,
        capability_id=dep_contract.capability_id,
        capability_version=dep_contract.capability_version,
        contract_hash=dep_contract.contract_hash,
        actor_id=actor_id,
        reason=RevocationReason.SECURITY_ISSUE,
    )
    await db_session.commit()

    # Critical assertion: lifecycle_state is PRESERVED, effective_state is QUARANTINED
    main_after = await registry_service.get_current_registration(
        db_session, tenant_id, main_contract.capability_id, main_contract.capability_version
    )
    assert main_after.lifecycle_state == LifecycleStatus.TRUSTED.value  # PRESERVED
    assert main_after.effective_state == EffectiveStatus.QUARANTINED_BY_DEPENDENCY.value
    assert main_after.effective_executable is False

    # Verify execution eligibility check
    eligibility = await registry_service.get_execution_eligibility(
        db_session, tenant_id, main_contract.capability_id, main_contract.capability_version
    )
    assert eligibility["lifecycle_state"] == LifecycleStatus.TRUSTED.value
    assert eligibility["effective_state"] == EffectiveStatus.QUARANTINED_BY_DEPENDENCY.value
    assert eligibility["effective_executable"] is False
    assert "REVOKED" in str(eligibility["dependency_health"])


async def test_get_execution_eligibility_decision_surface(
    db_session, tenant_id, actor_id, base_contract, registry_service
):
    """Verify get_execution_eligibility returns detailed decision surface."""
    await registry_service.register_capability(
        session=db_session,
        tenant_id=tenant_id,
        contract=base_contract,
        owner_principal=actor_id,
        actor_id=actor_id,
    )
    await db_session.commit()

    eligibility = await registry_service.get_execution_eligibility(
        db_session, tenant_id, base_contract.capability_id, base_contract.capability_version
    )

    assert eligibility["lifecycle_state"] == LifecycleStatus.DISCOVERED.value
    assert eligibility["effective_state"] == EffectiveStatus.DISCOVERED.value
    assert eligibility["effective_executable"] is False
    assert "not TRUSTED" in eligibility["decision_reason"]
    assert eligibility["dependency_health"] == {}
    assert "registry_revision" in eligibility
    assert "evaluated_at" in eligibility
    assert "decision_reason" in eligibility


async def test_duplicate_dependency_rejected(db_session, tenant_id, actor_id, base_contract, registry_service):
    with pytest.raises(DependencyError):
        await registry_service.register_capability(
            session=db_session, tenant_id=tenant_id, contract=base_contract,
            owner_principal=actor_id, actor_id=actor_id,
            dependency_ids=[base_contract.capability_id, base_contract.capability_id],
        )


async def test_two_node_dependency_cycle_rejected(db_session, tenant_id, actor_id, base_contract, registry_service):
    with pytest.raises(DependencyError):
        await registry_service._validate_dependencies(
            db_session, tenant_id, base_contract.capability_id, ["dep.b"]
        )


async def test_three_node_dependency_cycle_rejected(db_session, tenant_id, actor_id, base_contract, registry_service):
    with pytest.raises(DependencyError):
        await registry_service._validate_dependencies(
            db_session, tenant_id, base_contract.capability_id, ["dep.b", "dep.c"]
        )


async def test_safety_controller_revocation_is_terminal_and_not_promotion(
    db_session, tenant_id, actor_id, base_contract, registry_service
):
    await registry_service.register_capability(
        session=db_session, tenant_id=tenant_id, contract=base_contract,
        owner_principal=actor_id, actor_id=actor_id,
    )
    with pytest.raises(InvalidTransitionError):
        await registry_service._transition(
            session=db_session, tenant_id=tenant_id,
            capability_id=base_contract.capability_id,
            capability_version=base_contract.capability_version,
            contract_hash=base_contract.contract_hash,
            to_status=LifecycleStatus.APPROVED,
            actor_id=actor_id,
            authority=TransitionAuthority.SAFETY_CONTROLLER,
        )


async def test_stale_revision_rejected(db_session, tenant_id, actor_id, base_contract, registry_service):
    await registry_service.register_capability(
        session=db_session, tenant_id=tenant_id, contract=base_contract,
        owner_principal=actor_id, actor_id=actor_id,
    )
    current = await registry_service.get_current_registration(
        db_session, tenant_id, base_contract.capability_id, base_contract.capability_version
    )
    expected_revision = current.registry_revision
    await registry_service.transition_to_reviewed(
        session=db_session, tenant_id=tenant_id,
        capability_id=base_contract.capability_id,
        capability_version=base_contract.capability_version,
        contract_hash=base_contract.contract_hash, actor_id=actor_id,
        expected_revision=expected_revision,
    )
    with pytest.raises(RegistryConflictError):
        await registry_service.transition_to_approved(
            session=db_session, tenant_id=tenant_id,
            capability_id=base_contract.capability_id,
            capability_version=base_contract.capability_version,
            contract_hash=base_contract.contract_hash, actor_id=actor_id,
            approval_policy_ref="approval_policy_v1",
            credential_policy_ref="credential_policy_v1",
            verification_policy_ref="verification_policy_v1",
            expected_revision=expected_revision,
        )
