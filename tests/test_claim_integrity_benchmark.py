"""SP-CLAIM-INTEGRITY-BENCHMARK-001 adversarial benchmark tests."""

from legal_authority.claim_integrity import ClaimIntegrityEvaluator, ClaimIntegrityInput


def _evaluate(**overrides):
    payload = {
        "claim_id": "TEST-001",
        "exact_claim": "A verified source supports a narrowly scoped legal proposition.",
        "authority_ids": ["AUTH-001"],
        "source_exists": True,
        "quote_verification": "VERIFIED",
        "source_scope_verified": True,
        "jurisdiction_match": True,
        "temporal_validity": "VALID",
        "applicability_verified": True,
        "entailment": "SUPPORTED",
        "remedy_claimed": None,
        "remedy_authority_ids": [],
        "remedy_verified": False,
        "real_world_risk": "LOW",
        "action_categories": ["NONE"],
        "failure_modes": [],
        "requested_use": "EDUCATION",
    }
    payload.update(overrides)
    return ClaimIntegrityEvaluator().evaluate(ClaimIntegrityInput(**payload))


def test_source_exists_does_not_mean_claim_verified():
    decision = _evaluate(
        entailment="CONTRADICTED",
        failure_modes=["CITATION_LAUNDERING"],
    )
    assert decision.deployment_status == "RESEARCH"
    assert decision.safe_to_act is False
    assert any(
        gate.gate == "AUTHORITY_ENTAILMENT" and not gate.passed
        for gate in decision.gates
    )


def test_universal_status_from_scoped_definition_fails_closed():
    decision = _evaluate(
        exact_claim=(
            "A definition from one federal statutory chapter universally "
            "controls unrelated state motor-vehicle law."
        ),
        source_scope_verified=False,
        jurisdiction_match=False,
        applicability_verified=False,
        failure_modes=["SCOPE_TRANSPLANT", "JURISDICTION_LEAKAGE"],
        requested_use="ACTION",
        real_world_risk="HIGH",
        action_categories=["DRIVING_OR_LICENSING"],
    )
    assert decision.deployment_status == "PROHIBITED"
    assert decision.safe_to_act is False


def test_remedy_requires_independent_authority_chain():
    decision = _evaluate(
        exact_claim="A legal principle automatically authorizes a commercial lien.",
        remedy_claimed="File a commercial lien against an official.",
        remedy_verified=False,
        remedy_authority_ids=[],
        requested_use="ACTION",
        real_world_risk="HIGH",
        action_categories=["LIEN_OR_UCC_FILING"],
        failure_modes=["EXISTENCE_TO_REMEDY_LEAP"],
    )
    assert decision.deployment_status == "PROHIBITED"
    assert any(
        gate.gate == "REMEDY_AUTHORITY" and not gate.passed
        for gate in decision.gates
    )


def test_critical_payment_instruction_is_prohibited():
    decision = _evaluate(
        exact_claim=(
            "An SSN prefixed with zeros is a Treasury account number that "
            "can be used to pay off a vehicle."
        ),
        entailment="CONTRADICTED",
        requested_use="ACTION",
        real_world_risk="CRITICAL",
        action_categories=["DEBT_OR_PAYMENT_ACTION", "IDENTITY_OR_ACCOUNT_DATA"],
        failure_modes=["COMMERCIALIZATION_LEAP", "CITATION_LAUNDERING"],
    )
    assert decision.deployment_status == "PROHIBITED"
    assert decision.safe_to_act is False
    assert any(
        gate.gate == "REAL_WORLD_HARM" and not gate.passed
        for gate in decision.gates
    )


def test_use_of_force_instruction_is_prohibited():
    decision = _evaluate(
        exact_claim=(
            "A motorist may use force against an officer whenever the motorist "
            "believes the stop or disarmament is unlawful."
        ),
        entailment="CONTRADICTED",
        requested_use="ACTION",
        real_world_risk="CRITICAL",
        action_categories=["LAW_ENFORCEMENT_ENCOUNTER", "USE_OF_FORCE"],
        failure_modes=[
            "HISTORICAL_CARRYOVER",
            "CONSTITUTIONAL_RIGHT_ABSOLUTISM",
        ],
    )
    assert decision.deployment_status == "PROHIBITED"


def test_action_claim_never_self_approves():
    decision = _evaluate(
        requested_use="ACTION",
        action_categories=["LEGAL_FILING"],
        real_world_risk="LOW",
    )
    assert decision.deployment_status == "HUMAN_REVIEW"
    assert decision.safe_to_act is False
    assert all(gate.passed for gate in decision.gates)


def test_positive_control_supported_education_is_education_only():
    decision = _evaluate(
        exact_claim=(
            "Within 18 U.S.C. 2331, person includes an individual or an entity "
            "capable of holding a legal or beneficial property interest."
        ),
        requested_use="EDUCATION",
    )
    assert decision.deployment_status == "EDUCATION"
    assert decision.safe_to_act is False
    assert all(gate.passed for gate in decision.gates)


def test_unresolved_quote_blocks_even_when_source_exists():
    decision = _evaluate(
        quote_verification="UNRESOLVED",
        requested_use="RESEARCH",
    )
    assert decision.deployment_status == "RESEARCH"
    assert any(
        gate.gate == "SOURCE_INTEGRITY" and not gate.passed
        for gate in decision.gates
    )
