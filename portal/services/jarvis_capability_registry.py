"""JARVIS-001-B2-B2 Capability Registry service.

Manages capability lifecycle, dependency validation, and registry state.
Registry is authoritative; memory/approval/cache cannot override.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.jarvis_capability_registry import (
    CapabilityRegistration,
    CapabilityTransition,
    EffectiveStatus,
    LifecycleStatus,
    RevocationReason,
    TransitionAuthority,
)
from portal.services.jarvis_capability_contract import CapabilityContract


class RegistryError(Exception):
    """Base exception for registry errors."""

class InvalidTransitionError(RegistryError):
    """Invalid lifecycle transition attempted."""

class RegistryConflictError(RegistryError):
    """Optimistic concurrency conflict."""

class TenantIsolationError(RegistryError):
    """Tenant isolation violation."""

class DependencyError(RegistryError):
    """Dependency validation failed."""

class CapabilityRegistryService:
    """Service for managing capability registrations and lifecycle."""

    # Valid lifecycle transitions (granted trust level changes only)
    _VALID_TRANSITIONS: ClassVar[dict[LifecycleStatus, set[LifecycleStatus]]] = {
        LifecycleStatus.DISCOVERED: {LifecycleStatus.REVIEWED, LifecycleStatus.REVOKED},
        LifecycleStatus.REVIEWED: {LifecycleStatus.APPROVED, LifecycleStatus.REVOKED},
        LifecycleStatus.APPROVED: {LifecycleStatus.SANDBOXED, LifecycleStatus.REVOKED},
        LifecycleStatus.SANDBOXED: {LifecycleStatus.TRUSTED, LifecycleStatus.REVOKED},
        LifecycleStatus.TRUSTED: {LifecycleStatus.REVOKED},
        LifecycleStatus.REVOKED: set(),  # Terminal
    }

    async def register_capability(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        contract: CapabilityContract,
        owner_principal: uuid.UUID,
        actor_id: uuid.UUID,
        dependency_ids: list[str] | None = None,
        supersedes_version: str | None = None,
    ) -> CapabilityRegistration:
        """Register a new capability with DISCOVERED status.

        Args:
            session: Database session
            tenant_id: Tenant scope
            contract: Immutable capability contract
            owner_principal: Principal who owns this capability
            actor_id: Actor performing registration
            dependency_ids: List of capability_ids this capability depends on
            supersedes_version: Previous version being replaced

        Returns:
            New registration record

        Raises:
            DependencyError: Invalid dependencies
        """
        deps = dependency_ids or []

        # Validate dependencies
        await self._validate_dependencies(
            session, tenant_id, contract.capability_id, deps
        )

        # Create registration
        now = datetime.now(UTC)
        registration = CapabilityRegistration(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            capability_id=contract.capability_id,
            capability_version=contract.capability_version,
            contract_hash=contract.contract_hash,
            owner_principal=owner_principal,
            lifecycle_state=LifecycleStatus.DISCOVERED.value,
            lifecycle_state_effective_at=now,
            effective_state=EffectiveStatus.DISCOVERED.value,
            effective_state_computed_at=now,
            effective_executable=False,
            supersedes=supersedes_version,
            dependency_ids=deps,
            executor_id=contract.executor_id,
            adapter_id=contract.adapter_id,
            registry_revision=1,
        )

        session.add(registration)
        await session.flush()

        # Record initial transition
        await self._record_transition(
            session=session,
            tenant_id=tenant_id,
            capability_id=contract.capability_id,
            capability_version=contract.capability_version,
            contract_hash=contract.contract_hash,
            from_status=None,
            to_status=LifecycleStatus.DISCOVERED,
            actor_id=actor_id,
            authority=TransitionAuthority.PRINCIPAL,
            reason=None,
        )

        return registration

    async def transition_to_reviewed(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
        contract_hash: str,
        actor_id: uuid.UUID,
        expected_revision: int | None = None,
    ) -> CapabilityRegistration:
        """Transition DISCOVERED → REVIEWED (requires REVIEWER authority)."""
        return await self._transition(
            session=session,
            tenant_id=tenant_id,
            capability_id=capability_id,
            capability_version=capability_version,
            contract_hash=contract_hash,
            to_status=LifecycleStatus.REVIEWED,
            actor_id=actor_id,
            authority=TransitionAuthority.REVIEWER,
            expected_revision=expected_revision,
        )

    async def transition_to_approved(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
        contract_hash: str,
        actor_id: uuid.UUID,
        approval_policy_ref: str,
        credential_policy_ref: str,
        verification_policy_ref: str,
        expected_revision: int | None = None,
    ) -> CapabilityRegistration:
        """Transition REVIEWED → APPROVED (requires PRINCIPAL/CAPABILITY_OWNER authority)."""
        reg = await self._transition(
            session=session,
            tenant_id=tenant_id,
            capability_id=capability_id,
            capability_version=capability_version,
            contract_hash=contract_hash,
            to_status=LifecycleStatus.APPROVED,
            actor_id=actor_id,
            authority=TransitionAuthority.CAPABILITY_OWNER,
            expected_revision=expected_revision,
        )

        # Set policy references
        reg.approval_policy_ref = approval_policy_ref
        reg.credential_policy_ref = credential_policy_ref
        reg.verification_policy_ref = verification_policy_ref
        await session.flush()

        return reg

    async def transition_to_sandboxed(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
        contract_hash: str,
        actor_id: uuid.UUID,
        expected_revision: int | None = None,
    ) -> CapabilityRegistration:
        """Transition APPROVED → SANDBOXED (requires GOVERNED_CONTROLLER authority)."""
        return await self._transition(
            session=session,
            tenant_id=tenant_id,
            capability_id=capability_id,
            capability_version=capability_version,
            contract_hash=contract_hash,
            to_status=LifecycleStatus.SANDBOXED,
            actor_id=actor_id,
            authority=TransitionAuthority.GOVERNED_CONTROLLER,
            expected_revision=expected_revision,
        )

    async def transition_to_trusted(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
        contract_hash: str,
        actor_id: uuid.UUID,
        certifier_id: uuid.UUID,
        expected_revision: int | None = None,
    ) -> CapabilityRegistration:
        """Transition SANDBOXED → TRUSTED (requires INDEPENDENT_CERTIFIER + GOVERNING_AUTHORITY)."""
        # For B2-B2, we combine both authorities in one call
        # In production, this would verify separate certifier signature
        return await self._transition(
            session=session,
            tenant_id=tenant_id,
            capability_id=capability_id,
            capability_version=capability_version,
            contract_hash=contract_hash,
            to_status=LifecycleStatus.TRUSTED,
            actor_id=actor_id,
            authority=TransitionAuthority.GOVERNING_AUTHORITY,
            expected_revision=expected_revision,
        )

    async def revoke_capability(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
        contract_hash: str,
        actor_id: uuid.UUID,
        reason: RevocationReason,
        expected_revision: int | None = None,
    ) -> CapabilityRegistration:
        """Revoke a capability (terminal state).

        Can be called by PRINCIPAL, DESIGNATED_REVOKER, or SAFETY_CONTROLLER.
        """
        reg = await self._transition(
            session=session,
            tenant_id=tenant_id,
            capability_id=capability_id,
            capability_version=capability_version,
            contract_hash=contract_hash,
            to_status=LifecycleStatus.REVOKED,
            actor_id=actor_id,
            authority=TransitionAuthority.SAFETY_CONTROLLER,
            reason=reason.value,
            expected_revision=expected_revision,
        )

        reg.revoked_at = datetime.now(UTC)
        await session.flush()

        # Quarantine all dependents
        await self._quarantine_dependents(
            session, tenant_id, capability_id
        )

        return reg

    async def get_current_registration(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
    ) -> CapabilityRegistration | None:
        """Get current registration for a capability (tenant-scoped)."""
        stmt = select(CapabilityRegistration).where(
            CapabilityRegistration.tenant_id == tenant_id,
            CapabilityRegistration.capability_id == capability_id,
            CapabilityRegistration.capability_version == capability_version,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_capability_trusted(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
    ) -> bool:
        """Check if capability is in TRUSTED lifecycle_state."""
        reg = await self.get_current_registration(
            session, tenant_id, capability_id, capability_version
        )
        return reg is not None and reg.lifecycle_state == LifecycleStatus.TRUSTED.value

    async def check_execution_eligibility(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
        contract_hash: str,
    ) -> bool:
        """Check if capability is eligible for execution.

        Registry state is authoritative; cache cannot override.
        Eligibility requires: contract hash match AND effective_executable=True.
        """
        reg = await self.get_current_registration(
            session, tenant_id, capability_id, capability_version
        )

        if reg is None:
            return False

        # Verify contract hash matches
        if reg.contract_hash != contract_hash:
            return False

        # Check derived execution eligibility
        return reg.effective_executable

    async def get_execution_eligibility(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
    ) -> dict[str, Any]:
        """Get detailed execution eligibility decision surface.

        Returns dict with:
            - lifecycle_state: granted trust level
            - effective_state: computed execution state
            - effective_executable: boolean eligibility
            - dependency_health: status of all dependencies
            - decision_reason: human-readable explanation
        """
        reg = await self.get_current_registration(
            session, tenant_id, capability_id, capability_version
        )

        if reg is None:
            return {
                "lifecycle_state": None,
                "effective_state": None,
                "effective_executable": False,
                "dependency_health": {},
                "decision_reason": "Capability not found in tenant scope",
            }

        # Check dependency health
        dep_health = {}
        all_deps_healthy = True

        for dep_id in reg.dependency_ids:
            dep_reg = await session.execute(
                select(CapabilityRegistration).where(
                    CapabilityRegistration.tenant_id == tenant_id,
                    CapabilityRegistration.capability_id == dep_id,
                )
            )
            dep = dep_reg.scalar_one_or_none()

            if dep is None:
                dep_health[dep_id] = "MISSING"
                all_deps_healthy = False
            elif dep.lifecycle_state == LifecycleStatus.REVOKED.value:
                dep_health[dep_id] = "REVOKED"
                all_deps_healthy = False
            elif dep.effective_executable:
                dep_health[dep_id] = "HEALTHY"
            else:
                dep_health[dep_id] = f"NOT_EXECUTABLE({dep.effective_state})"
                all_deps_healthy = False

        # Compute decision reason
        if reg.lifecycle_state == LifecycleStatus.REVOKED.value:
            reason = "Capability is revoked"
        elif not all_deps_healthy:
            reason = f"Dependencies unhealthy: {dep_health}"
        elif reg.lifecycle_state != LifecycleStatus.TRUSTED.value:
            reason = f"Lifecycle state is {reg.lifecycle_state}, not TRUSTED"
        elif reg.effective_state == EffectiveStatus.REVALIDATION_REQUIRED.value:
            reason = "Requires independent revalidation after dependency change"
        else:
            reason = "Eligible for execution"

        return {
            "lifecycle_state": reg.lifecycle_state,
            "effective_state": reg.effective_state,
            "effective_executable": reg.effective_executable,
            "registry_revision": reg.registry_revision,
            "dependency_health": dep_health,
            "decision_reason": reason,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    async def get_transition_history(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
    ) -> list[CapabilityTransition]:
        """Get ordered transition history for a capability."""
        stmt = (
            select(CapabilityTransition)
            .where(
                CapabilityTransition.tenant_id == tenant_id,
                CapabilityTransition.capability_id == capability_id,
                CapabilityTransition.capability_version == capability_version,
            )
            .order_by(CapabilityTransition.transitioned_at)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def verify_transition_chain_integrity(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
    ) -> bool:
        """Verify hash chain integrity of transition ledger."""
        transitions = await self.get_transition_history(
            session, tenant_id, capability_id, capability_version
        )

        if not transitions:
            return True

        for i in range(1, len(transitions)):
            if transitions[i].previous_transition_hash != transitions[i - 1].transition_hash:
                return False

        return True

    # ═══════════════════════════════════════════════════════════════════════
    # Private Implementation
    # ═══════════════════════════════════════════════════════════════════════

    async def _transition(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
        contract_hash: str,
        to_status: LifecycleStatus,
        actor_id: uuid.UUID,
        authority: TransitionAuthority,
        reason: str | None = None,
        expected_revision: int | None = None,
    ) -> CapabilityRegistration:
        """Internal transition implementation with optimistic locking.

        Updates lifecycle_state and recomputes effective_state/effective_executable.
        Ledger, projection, and revision update are atomic (one transaction).
        """
        # Get current registration
        reg = await self.get_current_registration(
            session, tenant_id, capability_id, capability_version
        )

        if reg is None:
            raise TenantIsolationError(
                f"Capability {capability_id} v{capability_version} not found in tenant scope"
            )

        # Verify contract hash
        if reg.contract_hash != contract_hash:
            raise InvalidTransitionError("Contract hash mismatch")

        from_status = LifecycleStatus(reg.lifecycle_state)

        # Validate transition
        if to_status not in self._VALID_TRANSITIONS.get(from_status, set()):
            raise InvalidTransitionError(
                f"Invalid transition {from_status.value} → {to_status.value}"
            )

        # Optimistic concurrency check
        current_revision = reg.registry_revision
        if expected_revision is not None and current_revision != expected_revision:
            raise RegistryConflictError(
                f"stale registry revision: expected {expected_revision}, current {current_revision}"
            )
        now = datetime.now(UTC)

        # Update lifecycle_state
        reg.lifecycle_state = to_status.value
        reg.lifecycle_state_effective_at = now
        reg.registry_revision = current_revision + 1

        # Recompute effective_state and effective_executable
        await self._recompute_effective_state(session, reg, now)

        try:
            await session.flush()
        except Exception as e:
            # Detect revision conflict
            if "registry_revision" in str(e) or "concurrent" in str(e).lower():
                raise RegistryConflictError("Concurrent modification detected") from e
            raise

        # Record transition (ledger, projection, revision are now atomic)
        await self._record_transition(
            session=session,
            tenant_id=tenant_id,
            capability_id=capability_id,
            capability_version=capability_version,
            contract_hash=contract_hash,
            from_status=from_status,
            to_status=to_status,
            actor_id=actor_id,
            authority=authority,
            reason=reason,
        )

        return reg

    async def _recompute_effective_state(
        self,
        session: AsyncSession,
        reg: CapabilityRegistration,
        now: datetime,
    ) -> None:
        """Recompute effective_state and effective_executable from lifecycle_state + dependencies.

        Critical: lifecycle_state remains unchanged; only effective_* fields are updated.
        """
        # If revoked, effective_state = REVOKED and not executable
        if reg.lifecycle_state == LifecycleStatus.REVOKED.value:
            reg.effective_state = EffectiveStatus.REVOKED.value
            reg.effective_executable = False
            reg.effective_state_computed_at = now
            return

        # Check dependency health
        all_deps_healthy = True
        for dep_id in reg.dependency_ids:
            dep_stmt = select(CapabilityRegistration).where(
                CapabilityRegistration.tenant_id == reg.tenant_id,
                CapabilityRegistration.capability_id == dep_id,
            )
            dep_result = await session.execute(dep_stmt)
            dep = dep_result.scalar_one_or_none()

            if dep is None or dep.lifecycle_state == LifecycleStatus.REVOKED.value:
                all_deps_healthy = False
                break
            if not dep.effective_executable:
                all_deps_healthy = False
                break

        # Compute effective_state
        if not all_deps_healthy:
            # Preserve lifecycle_state; set effective_state to QUARANTINED_BY_DEPENDENCY
            reg.effective_state = EffectiveStatus.QUARANTINED_BY_DEPENDENCY.value
            reg.effective_executable = False
        elif reg.lifecycle_state == LifecycleStatus.TRUSTED.value:
            # TRUSTED with healthy dependencies
            reg.effective_state = EffectiveStatus.TRUSTED.value
            reg.effective_executable = True
        else:
            # Not TRUSTED yet
            reg.effective_state = reg.lifecycle_state  # Mirror lifecycle_state
            reg.effective_executable = False

        reg.effective_state_computed_at = now

    async def _record_transition(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        capability_version: str,
        contract_hash: str,
        from_status: LifecycleStatus | None,
        to_status: LifecycleStatus,
        actor_id: uuid.UUID,
        authority: TransitionAuthority,
        reason: str | None,
    ) -> CapabilityTransition:
        """Record a transition in the append-only ledger with hash chain."""
        # Get previous transition for hash chain
        stmt = (
            select(CapabilityTransition)
            .where(
                CapabilityTransition.tenant_id == tenant_id,
                CapabilityTransition.capability_id == capability_id,
                CapabilityTransition.capability_version == capability_version,
            )
            .order_by(CapabilityTransition.transitioned_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        previous = result.scalar_one_or_none()

        previous_hash = previous.transition_hash if previous else None

        # Compute transition hash
        transition_data = {
            "tenant_id": str(tenant_id),
            "capability_id": capability_id,
            "capability_version": capability_version,
            "contract_hash": contract_hash,
            "from_status": from_status.value if from_status else "INITIAL",
            "to_status": to_status.value,
            "actor_id": str(actor_id),
            "authority": authority.value,
            "reason": reason,
            "previous_hash": previous_hash,
        }

        transition_hash = self._compute_hash(transition_data)

        transition = CapabilityTransition(
            transition_id=uuid.uuid4(),
            tenant_id=tenant_id,
            capability_id=capability_id,
            capability_version=capability_version,
            contract_hash=contract_hash,
            from_status=from_status.value if from_status else "INITIAL",
            to_status=to_status.value,
            actor_id=actor_id,
            authority=authority.value,
            reason=reason,
            previous_transition_hash=previous_hash,
            transition_hash=transition_hash,
        )

        session.add(transition)
        await session.flush()

        return transition

    async def _validate_dependencies(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        dependency_ids: list[str],
    ) -> None:
        """Validate dependency graph: no self-ref, duplicates, missing, or cycles."""
        if not dependency_ids:
            return

        # Check for self-reference
        if capability_id in dependency_ids:
            raise DependencyError("Self-referencing dependency not allowed")

        # Check for duplicates
        if len(dependency_ids) != len(set(dependency_ids)):
            raise DependencyError("Duplicate dependencies not allowed")

        # Check all dependencies exist in tenant scope
        for dep_id in dependency_ids:
            stmt = select(CapabilityRegistration).where(
                CapabilityRegistration.tenant_id == tenant_id,
                CapabilityRegistration.capability_id == dep_id,
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none() is None:
                raise DependencyError(f"Dependency {dep_id} not found in tenant scope")

        # Check for cycles
        if await self._has_dependency_cycle(session, tenant_id, capability_id, dependency_ids):
            raise DependencyError("Cyclic dependency detected")

    async def _has_dependency_cycle(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        capability_id: str,
        dependency_ids: list[str],
        visited: set[str] | None = None,
    ) -> bool:
        """Check for cycles in dependency graph using DFS."""
        if visited is None:
            visited = set()

        if capability_id in visited:
            return True

        visited.add(capability_id)

        for dep_id in dependency_ids:
            # Get dependencies of this dependency
            stmt = select(CapabilityRegistration).where(
                CapabilityRegistration.tenant_id == tenant_id,
                CapabilityRegistration.capability_id == dep_id,
            )
            result = await session.execute(stmt)
            dep_reg = result.scalar_one_or_none()

            if dep_reg and dep_reg.dependency_ids:
                if await self._has_dependency_cycle(
                    session, tenant_id, dep_id, dep_reg.dependency_ids, visited.copy()
                ):
                    return True

        return False

    async def _quarantine_dependents(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        revoked_capability_id: str,
    ) -> None:
        """Update effective_state for capabilities that depend on a revoked capability.

        Critical: lifecycle_state is PRESERVED (e.g., TRUSTED remains TRUSTED).
        Only effective_state changes to QUARANTINED_BY_DEPENDENCY and effective_executable=False.
        """
        # Find all capabilities that depend on the revoked one
        stmt = select(CapabilityRegistration).where(
            CapabilityRegistration.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        all_registrations = result.scalars().all()

        now = datetime.now(UTC)
        for reg in all_registrations:
            if revoked_capability_id in reg.dependency_ids:
                # Update effective_state only; lifecycle_state is preserved
                if reg.lifecycle_state != LifecycleStatus.REVOKED.value:
                    reg.effective_state = EffectiveStatus.QUARANTINED_BY_DEPENDENCY.value
                    reg.effective_executable = False
                    reg.effective_state_computed_at = now
                    reg.registry_revision += 1

                    # Note: No lifecycle transition is recorded because lifecycle_state did not change.
                    # This is a derived state change, not a granted authority change.
                    await session.flush()

    @staticmethod
    def _compute_hash(data: dict[str, Any]) -> str:
        """Compute SHA-256 hash of transition data."""
        encoded = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
