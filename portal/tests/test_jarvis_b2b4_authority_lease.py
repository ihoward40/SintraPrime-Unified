from datetime import UTC, datetime, timedelta

import pytest

from portal.services.jarvis_authority_lease import (
    AuthorityLease,
    LeaseDeniedError,
    LeaseState,
    params_hash,
)


@pytest.fixture
def lease():
    return AuthorityLease.issue(
        tenant_id="tenant-a", principal_id="principal-a", capability_id="cap",
        capability_version="1", capability_contract_hash="hash", registry_revision=3,
        action_id="action", approval_id="approval", operation="op", target="target",
        params_hash="params", ttl=timedelta(minutes=5), now=datetime(2026, 1, 1, tzinfo=UTC),
    )


def context(**overrides):
    value = {
        "tenant_id": "tenant-a",
        "principal_id": "principal-a",
        "capability_id": "cap",
        "capability_version": "1",
        "capability_contract_hash": "hash",
        "registry_revision": 3,
        "action_id": "action",
        "approval_id": "approval",
        "operation": "op",
        "target": "target",
        "params_hash": "params",
        "now": datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
    }
    value.update(overrides)
    return value


def test_exact_lease_claim_and_single_consume(lease):
    claimed = lease.claim(**context())
    assert claimed.lease_state == LeaseState.CLAIMED
    consumed = claimed.consume(**context())
    assert consumed.lease_state == LeaseState.CONSUMED
    with pytest.raises(LeaseDeniedError):
        consumed.consume(**context())


@pytest.mark.parametrize("field", ["tenant_id", "principal_id", "capability_id", "capability_version", "capability_contract_hash", "registry_revision", "action_id", "approval_id", "operation", "target", "params_hash"])
def test_binding_mismatch_denied(lease, field):
    wrong = {field: 999 if field == "registry_revision" else "wrong"}
    with pytest.raises(LeaseDeniedError):
        lease.claim(**context(**wrong))


def test_expiry_revocation_and_dependency_states_denied(lease):
    with pytest.raises(LeaseDeniedError):
        lease.claim(**context(now=datetime(2026, 1, 1, 0, 6, tzinfo=UTC)))
    with pytest.raises(LeaseDeniedError):
        lease.claim(**context(effective_state="REVOKED"))
    with pytest.raises(LeaseDeniedError):
        lease.claim(**context(effective_state="QUARANTINED_BY_DEPENDENCY"))
    with pytest.raises(LeaseDeniedError):
        lease.claim(**context(effective_state="REVALIDATION_REQUIRED"))
    with pytest.raises(LeaseDeniedError):
        lease.claim(**context(effective_executable=False))


def test_non_transferability_and_revocation(lease):
    with pytest.raises(LeaseDeniedError):
        lease.claim(**context(principal_id="principal-b"))
    with pytest.raises(LeaseDeniedError):
        lease.claim(**context(tenant_id="tenant-b"))
    assert lease.revoke().lease_state == LeaseState.REVOKED


def test_params_hash_is_deterministic():
    assert params_hash({"issue": 1}) == params_hash({"issue": 1})
