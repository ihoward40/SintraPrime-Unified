from datetime import UTC, datetime, timedelta

import pytest

from portal.services.jarvis_authority_lease import AuthorityLease
from portal.services.jarvis_credential_broker import (
    CredentialBroker,
    CredentialDeniedError,
    CredentialRequest,
)


@pytest.fixture
def claimed_lease():
    lease = AuthorityLease.issue(
        tenant_id="tenant", principal_id="principal", capability_id="cap",
        capability_version="1", capability_contract_hash="hash", registry_revision=3,
        action_id="action", approval_id="approval", operation="op", target="target",
        params_hash="params", ttl=timedelta(minutes=5), now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return lease.claim(
        tenant_id="tenant", principal_id="principal", capability_id="cap",
        capability_version="1", capability_contract_hash="hash", registry_revision=3,
        action_id="action", approval_id="approval", operation="op", target="target",
        params_hash="params", now=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
    )


def request(lease, **overrides):
    value = {
        "broker_request_id": "request",
        "tenant_id": lease.tenant_id,
        "principal_id": lease.principal_id,
        "capability_id": lease.capability_id,
        "capability_version": lease.capability_version,
        "capability_contract_hash": lease.capability_contract_hash,
        "action_id": lease.action_id,
        "approval_id": lease.approval_id,
        "lease_id": lease.lease_id,
        "lease_revision": lease.revision,
        "provider_id": "fake-provider",
        "resource_scope": "fake-resource",
        "operation": lease.operation,
        "target": lease.target,
        "issued_at": datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
        "expires_at": datetime(2026, 1, 1, 0, 4, tzinfo=UTC),
        "nonce": "nonce-1",
    }
    value.update(overrides)
    return CredentialRequest(**value)


def test_grant_is_scoped_and_secret_safe(claimed_lease):
    broker = CredentialBroker()
    grant = broker.issue_scoped_grant(request=request(claimed_lease), lease=claimed_lease, now=datetime(2026, 1, 1, 0, 2, tzinfo=UTC))
    assert "FAKE_B2_SECRET" not in repr(grant)
    assert "FAKE_B2_SECRET" not in str(grant)
    assert grant.to_safe_dict()["secret_material"] == "REDACTED"
    assert grant.secret_material.reveal_for_adapter() == "FAKE_B2_SECRET"


def test_replay_denied_and_use_is_single_use(claimed_lease):
    broker = CredentialBroker()
    req = request(claimed_lease)
    grant = broker.issue_scoped_grant(request=req, lease=claimed_lease, now=datetime(2026, 1, 1, 0, 2, tzinfo=UTC))
    first = broker.validate_grant_use(grant=grant, lease=claimed_lease, request=req, now=datetime(2026, 1, 1, 0, 2, tzinfo=UTC))
    second = broker.validate_grant_use(grant=grant, lease=claimed_lease, request=req, now=datetime(2026, 1, 1, 0, 2, tzinfo=UTC))
    assert first.allowed is True
    assert second.allowed is False


@pytest.mark.parametrize("kwargs", [
    {"effective_executable": False},
    {"effective_state": "REVOKED"},
    {"effective_state": "QUARANTINED_BY_DEPENDENCY"},
    {"effective_state": "REVALIDATION_REQUIRED"},
    {"attestation_valid": False},
])
def test_denials_materialize_no_credential(claimed_lease, kwargs):
    broker = CredentialBroker()
    with pytest.raises(CredentialDeniedError):
        broker.issue_scoped_grant(request=request(claimed_lease), lease=claimed_lease, now=datetime(2026, 1, 1, 0, 2, tzinfo=UTC), **kwargs)


def test_binding_and_scope_mismatch_denied(claimed_lease):
    broker = CredentialBroker()
    with pytest.raises(CredentialDeniedError):
        broker.issue_scoped_grant(request=request(claimed_lease, tenant_id="other"), lease=claimed_lease, now=datetime(2026, 1, 1, 0, 2, tzinfo=UTC))
    with pytest.raises(CredentialDeniedError):
        broker.issue_scoped_grant(request=request(claimed_lease), lease=claimed_lease, resource_scope="other", now=datetime(2026, 1, 1, 0, 2, tzinfo=UTC))


def test_expired_grant_denied(claimed_lease):
    broker = CredentialBroker()
    req = request(claimed_lease)
    grant = broker.issue_scoped_grant(request=req, lease=claimed_lease, now=datetime(2026, 1, 1, 0, 2, tzinfo=UTC))
    result = broker.validate_grant_use(grant=grant, lease=claimed_lease, request=req, now=datetime(2026, 1, 1, 0, 5, tzinfo=UTC))
    assert result.allowed is False
