"""
Test-only approval provider for integration tests.

NEVER imported by production composition. This module lives in the test
support package to enforce that boundary.

TestApprovalProvider returns controlled approvals only when explicitly
configured. It defaults to deny, requires authenticated test principals,
and records each resolution for assertions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from portal.services.approval_provider import ApprovalResolution


@dataclass
class TestApprovalProvider:
    __test__ = False  # Prevent pytest from collecting this as a test class
    """Test-only approval provider for integration tests.

    Requirements:
      - Must be explicitly injected by test fixtures.
      - Requires authenticated test PrincipalContext (authentication_method="test").
      - Contains an explicit allowlist of (principal_id, action) combinations.
      - Defaults to deny.
      - Records each resolution for test assertions.
      - No mutable global state; each instance is independent.

    Usage in tests:

        provider = TestApprovalProvider(
            allowed={
                ("test-admin", "kill_switch.clear"),
                ("test-admin", "identity.action"),
            }
        )
        # Pass via dependency injection:
        decision = await ExecutionGuard.evaluate(
            session=db,
            action=ExecutionAction.KILL_SWITCH_CLEAR,
            principal_context=admin_principal,
            approval_provider=provider,
        )
    """

    allowed: frozenset[tuple[str, str]] = frozenset()
    _resolutions: list[ApprovalResolution] = field(default_factory=list)
    _queries: list[dict] = field(default_factory=list)

    def __post_init__(self):
        # Ensure allowed is immutable
        if not isinstance(self.allowed, frozenset):
            object.__setattr__(self, "allowed", frozenset(self.allowed))

    @property
    def resolutions(self) -> list[ApprovalResolution]:
        """Record of all resolution decisions for test assertions."""
        return list(self._resolutions)

    @property
    def queries(self) -> list[dict]:
        """Record of all queries received for test assertions."""
        return list(self._queries)

    async def resolve(
        self,
        *,
        session: AsyncSession,
        action: str,
        mission_id: Optional[str],
        governance_gate: Optional[str],
        principal_context: object,
    ) -> ApprovalResolution:
        from portal.services.execution_guard import PrincipalContext

        query_record = {
            "action": action,
            "mission_id": mission_id,
            "governance_gate": governance_gate,
            "principal_subject_id": (
                getattr(principal_context, "subject_id", None)
                if principal_context else None
            ),
            "principal_authenticated": (
                getattr(principal_context, "is_authenticated", False)
                if principal_context else False
            ),
        }
        self._queries.append(query_record)

        # ── Deny unauthenticated principals ──
        if not isinstance(principal_context, PrincipalContext):
            resolution = ApprovalResolution(
                approved=False,
                reason="TestApprovalProvider: principal_context is not PrincipalContext",
            )
            self._resolutions.append(resolution)
            return resolution

        if not principal_context.is_authenticated:
            resolution = ApprovalResolution(
                approved=False,
                reason=(
                    f"TestApprovalProvider: principal "
                    f"'{principal_context.subject_id}' is not authenticated"
                ),
            )
            self._resolutions.append(resolution)
            return resolution

        if principal_context.authentication_method != "test":
            resolution = ApprovalResolution(
                approved=False,
                reason=(
                    f"TestApprovalProvider: principal "
                    f"'{principal_context.subject_id}' authentication_method "
                    f"is '{principal_context.authentication_method}', "
                    f"expected 'test'"
                ),
            )
            self._resolutions.append(resolution)
            return resolution

        # ── Check explicit allowlist ──
        key = (principal_context.subject_id, action)
        if key in self.allowed:
            resolution = ApprovalResolution(
                approved=True,
                approval_id=f"test-approval-{action}",
                scope="test",
                reason=(
                    f"TestApprovalProvider: explicitly approved "
                    f"action '{action}' for principal '{principal_context.subject_id}'"
                ),
            )
            self._resolutions.append(resolution)
            return resolution

        # ── Default: deny ──
        resolution = ApprovalResolution(
            approved=False,
            reason=(
                f"TestApprovalProvider: action '{action}' not in allowlist "
                f"for principal '{principal_context.subject_id}'"
            ),
        )
        self._resolutions.append(resolution)
        return resolution