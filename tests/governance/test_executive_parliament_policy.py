from governance.runtime import GovernancePolicy


def test_viktor_can_inventory_without_approval():
    decision = GovernancePolicy().evaluate("viktor_magnus", "inventory")
    assert decision.allowed
    assert not decision.requires_principal_approval


def test_viktor_cannot_push_without_principal_approval():
    decision = GovernancePolicy().evaluate("viktor_magnus", "push")
    assert not decision.allowed
    assert decision.requires_principal_approval


def test_approved_gated_action_is_explicitly_marked():
    decision = GovernancePolicy().evaluate(
        "viktor_magnus", "push", principal_approved=True
    )
    assert decision.allowed
    assert decision.requires_principal_approval


def test_tasklet_cannot_make_financial_decision():
    decision = GovernancePolicy().evaluate(
        "tasklet_commander", "financial_decision"
    )
    assert not decision.allowed
    assert decision.requires_principal_approval


def test_legacy_engine_is_read_only_by_default():
    policy = GovernancePolicy()
    assert policy.evaluate("legacy_engine", "retrieve").allowed
    assert not policy.evaluate("legacy_engine", "persistent_memory").allowed


def test_confidential_data_is_blocked_from_public_repo_even_with_approval():
    decision = GovernancePolicy().evaluate(
        "legacy_engine",
        "confidential_ingestion",
        principal_approved=True,
        confidential=True,
        public_repository=True,
    )
    assert not decision.allowed


def test_unknown_officer_fails_closed():
    decision = GovernancePolicy().evaluate("unregistered_agent", "research")
    assert not decision.allowed


def test_unknown_action_fails_closed():
    decision = GovernancePolicy().evaluate("hermes_prime", "self_expand_authority")
    assert not decision.allowed
