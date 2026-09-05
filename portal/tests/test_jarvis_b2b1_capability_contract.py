"""B2-B1 CapabilityContract acceptance tests."""
from __future__ import annotations

from dataclasses import replace

import pytest

from portal.services.jarvis_capability_contract import (
    CANONICALIZATION_VERSION,
    CONTRACT_SCHEMA_VERSION,
    SUPPORTED_CANONICALIZATION_VERSIONS,
    SUPPORTED_CONTRACT_SCHEMA_VERSIONS,
    CapabilityContract,
)


def base(**overrides):
    values = {
        "capability_id": "github.issue.add_label",
        "capability_version": "1.0.0",
        "allowed_operations": ("github.issue.add_label",),
        "allowed_targets": ("github.issue:ihoward40/SintraPrime-Unified#188",),
        "risk": "low",
        "consequence": "reversible",
        "authority": "tenant_principal",
        "credential": "github_token",
        "executor_id": "jarvis_action_executor",
        "adapter_id": "github_label_adapter",
        "verification": "independent_refetch",
        "idempotency": "label_already_present",
        "reconciliation": "refetch_on_timeout",
        "rollback": "remove_label",
        "lease": "single_request",
        "revocation": "approval_consumed",
        "receipt": "hash_chain_append",
        "memory": "bounded_writeback",
        "brief": "governed action",
    }
    values.update(overrides)
    return CapabilityContract(**values)


def test_contract_is_immutable_and_versioned():
    contract = base()
    with pytest.raises(Exception):
        contract.capability_id = "other"  # type: ignore[misc]
    assert contract.contract_schema_version == CONTRACT_SCHEMA_VERSION == "1"
    assert contract.canonicalization_version == CANONICALIZATION_VERSION == "1"
    assert frozenset({"1"}) == SUPPORTED_CONTRACT_SCHEMA_VERSIONS
    assert frozenset({"1"}) == SUPPORTED_CANONICALIZATION_VERSIONS


def test_collection_order_is_semantic_set_order():
    assert base(allowed_operations=("b.op", "a.op"), allowed_targets=("b", "a")).contract_hash == base(
        allowed_operations=("a.op", "b.op"), allowed_targets=("a", "b")
    ).contract_hash


@pytest.mark.parametrize("field", ["allowed_operations", "allowed_targets"])
def test_collections_reject_empty_duplicate_null_blank_wildcard(field):
    for value in [(), ("a", "a"), (None,), ("",), ("a*",)]:
        with pytest.raises(ValueError):
            base(**{field: value})


@pytest.mark.parametrize("field", ["capability_id", "executor_id", "adapter_id"])
def test_identifiers_reject_ambiguous_or_mixed_case(field):
    for value in ["GitHub.Adapter", "bad value", ".leading", "trailing.", "a..b", "issue:188"]:
        with pytest.raises(ValueError):
            base(**{field: value})


def test_collision_inputs_are_not_accidentally_equivalent():
    assert base(allowed_targets=("issue:188",)).contract_hash != base(allowed_targets=("issue:0188",)).contract_hash
    assert base(allowed_operations=("github.issue.add_label",)).contract_hash != base(allowed_operations=("GitHub.Issue.Add_Label",)).contract_hash
    with pytest.raises(ValueError):
        base(allowed_targets=(None,))
    with pytest.raises(ValueError):
        base(allowed_targets=("",))
    with pytest.raises(ValueError):
        base(allowed_targets=())


@pytest.mark.parametrize("field", ["contract_schema_version", "canonicalization_version"])
def test_unknown_versions_rejected(field):
    with pytest.raises(ValueError):
        base(**{field: "2"})


def test_authority_change_changes_hash_and_runtime_downgrade_is_later_boundary():
    contract = base()
    assert replace(contract, risk="high").contract_hash != contract.contract_hash
    # Approved-vs-runtime equality belongs to B2-B5; B2-B1 rejects unsupported semantics.


@pytest.mark.parametrize("field_name", ["api_key", "token", "password", "secret", "authorization", "bearer", "private_key"])
def test_secret_like_field_names_are_not_contract_authority(field_name):
    # Unknown secret-bearing names are rejected before they can become authoritative.
    with pytest.raises(TypeError):
        CapabilityContract(**{**base().__dict__, field_name: "x"})


def test_secret_like_values_rejected():
    with pytest.raises(ValueError):
        base(brief="ghp_" + "a" * 40)
