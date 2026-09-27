from channels.trust_authority_router import build_trust_authority_route


def test_non_trust_message_is_not_routed():
    assert build_trust_authority_route("What is the weather today?") is None


def test_trust_research_uses_authority_stack():
    route = build_trust_authority_route(
        "Analyze trustee duties under the ISIAH TARIK HOWARD TRUST."
    )
    assert route is not None
    assert route["authority_order"] == [
        "trust-instrument-authority",
        "weisss-trustee-handbook",
        "current-law-verifier",
    ]
    assert route["current_law_status"] == "NOT_YET_VERIFIED"


def test_external_trust_execution_fails_closed():
    route = build_trust_authority_route(
        "File this trust amendment with the court and send it to the bank."
    )
    assert route is not None
    assert route["external_execution_requested"] is True
    assert route["fail_closed"] is True
    assert route["principal_approval"] is False
