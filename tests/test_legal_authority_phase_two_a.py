from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from legal_authority.models import JurisdictionRule, LegalChallenge, ProfessionalReview
from legal_authority.repository import LegalAuthorityRepository
from legal_authority.review_workflow import ReviewWorkflow, ReviewWorkflowError
from legal_authority.source_monitor import SourceMonitor


def _temp_repo(tmp_path: Path) -> LegalAuthorityRepository:
    root = tmp_path / "repo"
    shutil.copytree(Path.cwd() / "data" / "jurisdictions", root / "data" / "jurisdictions")
    return LegalAuthorityRepository(root=root)


def test_phase_2a_rule_categories_and_new_jersey_depth_rules_load():
    repo = LegalAuthorityRepository()
    checks = {
        "NJ-CREDITOR-WAGE-EXECUTION-LIMITS": "EXEMPTION_RULE",
        "NJ-CREDITOR-BANK-LEVY-TURNOVER": "PROCEDURAL_RULE",
        "NJ-CREDITOR-EXEMPT-BENEFITS-DEPOSIT-ACCOUNTS": "FEDERAL_OVERLAY",
        "NJ-BANKRUPTCY-TRUST-ASSET-EXPOSURE": "BANKRUPTCY_ONLY_RULE",
        "NJ-UCC-NJAC-17-33-OFFICIAL-SOURCE-LIMITATION": "PROCEDURAL_RULE",
    }
    for rule_id, category in checks.items():
        rule = repo.get_rule(rule_id)
        assert rule is not None
        assert rule.rule_category == category
        assert rule.requires_human_review is True
        assert rule.authority_ids


def test_new_jersey_depth_authorities_preserve_locator_limitations():
    repo = LegalAuthorityRepository()
    ucc_locator = repo.get_authority("NJ-NJAC-17-33-UCC-RULES")
    assert ucc_locator.verification_status == "PRIMARY_SOURCE_LOCATED"
    assert "locator" in " ".join(ucc_locator.limitations).lower()

    special_needs = repo.get_authority("NJ-MEDICAID-TRUSTS-NJAC-10-71-4-11")
    assert special_needs.source_classification == "SECONDARY_LEGAL_SOURCE"
    assert special_needs.source_availability_status == "LOCATOR_ONLY"
    assert special_needs.manual_review_status == "QUEUED"


@pytest.mark.parametrize(
    ("rule_id", "authority_id"),
    [
        ("NJ-CREDITOR-WAGE-EXECUTION-LIMITS", "NJ-EXEC-WAGE-2A17-56"),
        ("NJ-CREDITOR-BANK-LEVY-TURNOVER", "NJ-COURTS-JUDGMENT-COLLECTION"),
        ("NJ-CREDITOR-RETIREMENT-PENSION-PROTECTION", "NJ-PENSION-EXEMPTIONS-43-8A-20-43-19-17"),
        ("NJ-TRUST-DECANTING-UNSUPPORTED", "NJ-UTC-NJSA-3B31-11-26-34"),
        ("NJ-TRUST-VIRTUAL-REPRESENTATION-NJSA", "NJ-UTC-LIABILITY-3B31-70-81"),
        ("NJ-UCC-NJAC-17-33-OFFICIAL-SOURCE-LIMITATION", "NJ-TREASURY-UCC-RULE-ADOPTION-2023"),
    ],
)
def test_new_jersey_depth_rules_keep_required_provenance(rule_id, authority_id):
    rule = LegalAuthorityRepository().get_rule(rule_id)
    assert rule is not None
    assert authority_id in rule.authority_ids


def test_professional_review_submission_creates_audit_event(tmp_path):
    repo = _temp_repo(tmp_path)
    workflow = ReviewWorkflow(repo)
    review = workflow.submit_rule_review(
        "NJ-TRUST-CERTIFICATION",
        actor_role="LEGAL_RESEARCHER",
        actor_identity="researcher@example.test",
    )
    assert review.review_status == "SUBMITTED"
    assert review.audit_event_id in repo.audit_events


def test_non_attorney_cannot_approve_legal_rule(tmp_path):
    workflow = ReviewWorkflow(_temp_repo(tmp_path))
    with pytest.raises(ReviewWorkflowError, match="licensed attorneys"):
        workflow.record_rule_review(
            "NJ-TRUST-CERTIFICATION",
            reviewer_role="LEGAL_RESEARCHER",
            reviewer_identity="researcher@example.test",
            review_status="APPROVED",
            findings="Looks good.",
            digital_signature="sig",
        )


def test_attorney_approval_gate_and_expiration(tmp_path):
    repo = _temp_repo(tmp_path)
    workflow = ReviewWorkflow(repo)
    missing = workflow.production_eligibility("NJ-TRUST-CERTIFICATION")
    assert missing["production_eligible"] is False
    assert "licensed-attorney approval is missing" in missing["blockers"]

    workflow.record_rule_review(
        "NJ-TRUST-CERTIFICATION",
        reviewer_role="LICENSED_ATTORNEY",
        reviewer_identity="attorney@example.test",
        review_status="APPROVED",
        findings="Approved for Phase 2A test scope.",
        declared_credentials="NJ attorney self-declaration for test fixture",
        credential_verification_status="SELF_DECLARED",
        approval_scope="NJ trust certification issue-spotting rule",
        effective_date=datetime.now(UTC).date(),
        expires_at=datetime.now(UTC) + timedelta(days=30),
        digital_signature="authenticated-test-event",
    )
    approved = workflow.production_eligibility("NJ-TRUST-CERTIFICATION")
    assert approved["production_eligible"] is True

    workflow.record_rule_review(
        "NJ-TRUST-CERTIFICATION",
        reviewer_role="LICENSED_ATTORNEY",
        reviewer_identity="attorney@example.test",
        review_status="APPROVED",
        findings="Expired test approval.",
        declared_credentials="NJ attorney self-declaration for test fixture",
        credential_verification_status="SELF_DECLARED",
        approval_scope="expired",
        effective_date=datetime.now(UTC).date(),
        expires_at=datetime.now(UTC) - timedelta(days=1),
        digital_signature="expired-authenticated-test-event",
    )
    expired_gate = workflow.production_eligibility("NJ-TRUST-CERTIFICATION")
    assert expired_gate["production_eligible"] is False
    assert "licensed-attorney review is expired" in expired_gate["blockers"]


def test_conditional_rejected_conflict_and_source_gates_deny_production(tmp_path):
    repo = _temp_repo(tmp_path)
    workflow = ReviewWorkflow(repo)
    workflow.record_rule_review(
        "NJ-CREDITOR-WAGE-EXECUTION-LIMITS",
        reviewer_role="LICENSED_ATTORNEY",
        reviewer_identity="attorney@example.test",
        review_status="APPROVED_WITH_CONDITIONS",
        findings="Conditionally approved only after official statute check.",
        conditions=["verify official compiled statute"],
        digital_signature="conditional-test-event",
    )
    gate = workflow.production_eligibility("NJ-CREDITOR-WAGE-EXECUTION-LIMITS")
    assert gate["production_eligible"] is False
    assert "review conditions remain unsatisfied" in gate["blockers"]
    assert any("not primary-source verified" in blocker for blocker in gate["blockers"])

    conflict_gate = workflow.production_eligibility("NJ-ENGINE-CONFLICT-A")
    assert conflict_gate["production_eligible"] is False
    assert "unresolved conflicting rule relationship" in conflict_gate["blockers"]


def test_review_model_rejects_non_attorney_approval():
    with pytest.raises(ValueError):
        ProfessionalReview(
            id="review-test",
            object_type="JurisdictionRule",
            object_id="NJ-TRUST-CERTIFICATION",
            jurisdiction="NJ",
            domain="trust_law",
            reviewer_role="LEGAL_RESEARCHER",
            reviewer_identity="researcher@example.test",
            review_status="APPROVED",
            findings="No.",
            digital_signature="sig",
        )


def test_challenge_preserves_original_and_challenged_versions(tmp_path):
    repo = _temp_repo(tmp_path)
    workflow = ReviewWorkflow(repo)
    challenge = workflow.submit_challenge(
        "NJ-UCC-DEBTOR-NAMING-TRUSTS",
        challenge_type="CITATION_ACCURACY",
        issue="Citation should be checked against current Article 9 text.",
        submitted_by_role="LICENSED_ATTORNEY",
        submitted_by_identity="attorney@example.test",
        challenged_version={"citation": "proposed corrected citation"},
        evidence_submitted=[{"url": "https://example.test/evidence"}],
    )
    assert challenge.challenge_state == "OPEN"
    assert challenge.original_snapshot["id"] == "NJ-UCC-DEBTOR-NAMING-TRUSTS"
    assert challenge.challenged_version["citation"] == "proposed corrected citation"
    assert challenge.audit_event_ids[0] in repo.audit_events


def test_challenge_model_rejects_invalid_state():
    repo = LegalAuthorityRepository()
    rule = repo.get_rule("NJ-TRUST-CERTIFICATION")
    with pytest.raises(ValueError):
        LegalChallenge(
            id="challenge-test",
            object_type="JurisdictionRule",
            object_id=rule.id,
            jurisdiction="NJ",
            domain="trust_law",
            challenge_type="CITATION_ACCURACY",
            challenge_state="DONE",
            submitted_by_role="LICENSED_ATTORNEY",
            issue="bad state",
            original_snapshot=rule.model_dump(mode="json"),
            challenged_version={},
            created_at="2026-08-03T00:00:00Z",
            updated_at="2026-08-03T00:00:00Z",
        )


def test_stale_source_hash_change_and_unavailable_source_create_review_queue(tmp_path):
    repo = _temp_repo(tmp_path)
    authority = repo.get_authority("NJ-UTC-2015-276")
    repo.replace_authority(authority.model_copy(update={"content_hash": "old-hash"}))
    result = SourceMonitor(repo).refresh_authority_metadata(
        "NJ-UTC-2015-276",
        actor_role="LEGAL_RESEARCHER",
        actor_identity="researcher@example.test",
        supplied_hash="new-hash",
        source_available=False,
        reason="manual Phase 2A refresh test",
    )
    assert result.hash_changed is True
    assert result.source_available is False
    assert result.review_required is True
    refreshed = repo.get_authority("NJ-UTC-2015-276")
    assert refreshed.change_detected is True
    assert refreshed.verification_status == "HUMAN_REVIEW_REQUIRED"
    assert refreshed.manual_review_status == "INVALIDATED_PENDING_REVIEW"


def test_containment_blocks_private_claim_approval(tmp_path):
    repo = _temp_repo(tmp_path)
    workflow = ReviewWorkflow(repo)
    with pytest.raises(ReviewWorkflowError):
        workflow.record_rule_review(
            "NJ-CONTAIN-UNSUPPORTED-BANK-CARD",
            reviewer_role="LICENSED_ATTORNEY",
            reviewer_identity="attorney@example.test",
            review_status="APPROVED",
            findings="Attempted approval.",
            digital_signature="sig",
        )
    gate = workflow.production_eligibility("NJ-CONTAIN-UNSUPPORTED-BANK-CARD")
    assert gate["production_eligible"] is False
    assert any("unsupported private claim" in blocker for blocker in gate["blockers"])


def test_rule_model_rejects_invalid_rule_category():
    repo = LegalAuthorityRepository()
    raw = repo.get_rule("NJ-TRUST-CERTIFICATION").model_dump(mode="json")
    raw["rule_category"] = "MIXED_ALL_PURPOSE"
    with pytest.raises(ValueError):
        JurisdictionRule.model_validate(raw)
