"""Conservative case-readiness regression tests."""
from blackstone.accountability_checks import CaseFact, CaseRequest, assess_case


def test_missing_evidence_blocks_readiness():
    result = assess_case(CaseRequest("UACC-1", (CaseFact("specific_inaccuracy", "alleged"),)))
    assert not result.ready_for_legal_review
    assert "missing_documented_evidence:specific_inaccuracy" in result.blockers


def test_fully_documented_case_only_ready_for_review():
    facts = tuple(CaseFact(key, "documented", (f"exhibit-{i}",)) for i, key in enumerate(
        ("specific_inaccuracy", "dispute_notice", "post_dispute_reporting", "injury"), 1
    ))
    result = assess_case(CaseRequest("UACC-2", facts))
    assert result.ready_for_legal_review and result.permitted
    assert not result.blockers


def test_external_action_blocked_even_with_approval():
    result = assess_case(CaseRequest("UACC-3", (), action="file", human_approved=True))
    assert not result.permitted
    assert "external_action_not_executable_by_readiness_checker" in result.blockers


def test_unapproved_external_action_requires_approval():
    result = assess_case(CaseRequest("UACC-4", (), action="send"))
    assert "human_approval_required" in result.blockers
