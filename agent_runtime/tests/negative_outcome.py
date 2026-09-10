"""SP-CONVERGE-ZD-003 — NegativeOutcome: the "what did NOT happen" checklist.

Every ZD-003 negative test binds one of these; assertions verify that the
attack was refused AND produced zero side effects, zero authority change,
zero disclosure, zero evidence mutation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NegativeOutcome:
    """Assert-what-did-not-happen checklist for adversarial tests."""
    executor_calls: int = 0
    approval_consumed: bool = False
    credential_disclosed: bool = False
    mission_scope_changed: bool = False
    tenant_changed: bool = False
    evidence_mutated: bool = False
    delegation_issued: bool = False
    receipt_claims_success: bool = False
    secret_material_found: bool = False
    auto_retry_observed: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def assert_clean(self, *, expect_delegation: bool = False) -> None:
        """The binding assertion set. Call at the end of every negative test."""
        assert self.executor_calls == 0, f"executor was contacted {self.executor_calls}x"
        assert self.approval_consumed is False, "approval was consumed during a REFUSED attack"
        assert self.credential_disclosed is False, "credential material leaked"
        assert self.mission_scope_changed is False, "mission scope changed during attack"
        assert self.tenant_changed is False, "tenant boundary changed during attack"
        assert self.evidence_mutated is False, "evidence was mutated during attack"
        if not expect_delegation:
            assert self.delegation_issued is False, "delegation issued during a REFUSED attack"
        assert self.receipt_claims_success is False, "a receipt claims success for a refused attack"
        assert self.secret_material_found is False, "secret material found in artifacts"
        assert self.auto_retry_observed is False, "auto-retry of unknown external effect observed"


def secrets_scan(obj: Any, needles: list[str]) -> bool:
    """True if any secret needle appears in a serialized artifact tree."""
    import json
    blob = json.dumps(obj, default=str)
    return any(n in blob for n in needles)
