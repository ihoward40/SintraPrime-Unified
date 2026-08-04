"""Professional review, challenge, and production-gate workflow."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from legal_authority.models import AuditEvent, LegalChallenge, ProfessionalReview
from legal_authority.repository import LegalAuthorityRepository


class ReviewWorkflowError(ValueError):
    """Raised when a governed review action violates Phase 2A gates."""


class ReviewWorkflow:
    """Evaluates legal review state without bypassing professional gates."""

    def __init__(self, repository: LegalAuthorityRepository | None = None) -> None:
        self.repository = repository or LegalAuthorityRepository()

    def submit_rule_review(
        self,
        rule_id: str,
        actor_role: str,
        actor_identity: str | None,
        findings: str = "Submitted for professional legal review.",
    ) -> ProfessionalReview:
        rule = self._require_reviewable_rule(rule_id)
        now = datetime.now(UTC)
        event = self._audit_event(
            "REVIEW_SUBMITTED",
            "JurisdictionRule",
            rule_id,
            actor_role,
            actor_identity,
            "Rule submitted for review.",
            {"rule_status": rule.status},
            now,
        )
        review = ProfessionalReview(
            id=f"review-{uuid4()}",
            object_type="JurisdictionRule",
            object_id=rule.id,
            jurisdiction=rule.jurisdiction,
            domain=rule.domain,
            reviewer_role=actor_role,
            reviewer_identity=actor_identity,
            declared_credentials=None,
            credential_verification_status="NOT_VERIFIED",
            review_status="SUBMITTED",
            findings=findings,
            conditions=[],
            reviewed_authorities=[],
            rejected_authorities=[],
            approval_scope=None,
            effective_date=None,
            expires_at=None,
            digital_signature=None,
            audit_event_id=event.id,
            reviewed_at=None,
        )
        self.repository.append_audit_event(rule.jurisdiction, event)
        self.repository.append_review(review)
        return review

    def record_rule_review(
        self,
        rule_id: str,
        reviewer_role: str,
        reviewer_identity: str | None,
        review_status: str,
        findings: str,
        declared_credentials: str | None = None,
        credential_verification_status: str = "NOT_VERIFIED",
        conditions: list[str] | None = None,
        reviewed_authorities: list[str] | None = None,
        rejected_authorities: list[str] | None = None,
        approval_scope: str | None = None,
        effective_date: date | None = None,
        expires_at: datetime | None = None,
        digital_signature: str | None = None,
    ) -> ProfessionalReview:
        rule = self._require_reviewable_rule(rule_id)
        if review_status in {"APPROVED", "APPROVED_WITH_CONDITIONS"}:
            authorities = self.repository.authorities_for_rule(rule)
            if rule.status == "QUARANTINED" or any(
                authority.source_classification == "UNVERIFIED_PRIVATE_LAW_CLAIM"
                for authority in authorities
            ):
                raise ReviewWorkflowError(
                    "unsupported private claims must be reclassified before approval"
                )
            if reviewer_role != "LICENSED_ATTORNEY" and rule.domain != "accounting":
                raise ReviewWorkflowError("only licensed attorneys may approve legal rules")
            if reviewer_role == "CPA" and rule.domain != "accounting":
                raise ReviewWorkflowError("CPA approval is limited to accounting rules")
            if not digital_signature:
                raise ReviewWorkflowError(
                    "approved legal reviews require authenticated approval event"
                )
        now = datetime.now(UTC)
        event = self._audit_event(
            "REVIEW_RECORDED",
            "JurisdictionRule",
            rule_id,
            reviewer_role,
            reviewer_identity,
            "Professional review recorded.",
            {"review_status": review_status, "approval_scope": approval_scope},
            now,
        )
        review = ProfessionalReview(
            id=f"review-{uuid4()}",
            object_type="JurisdictionRule",
            object_id=rule.id,
            jurisdiction=rule.jurisdiction,
            domain=rule.domain,
            reviewer_role=reviewer_role,
            reviewer_identity=reviewer_identity,
            declared_credentials=declared_credentials,
            credential_verification_status=credential_verification_status,
            review_status=review_status,
            findings=findings,
            conditions=conditions or [],
            reviewed_authorities=reviewed_authorities or rule.authority_ids,
            rejected_authorities=rejected_authorities or [],
            approval_scope=approval_scope,
            effective_date=effective_date,
            expires_at=expires_at,
            digital_signature=digital_signature,
            audit_event_id=event.id,
            reviewed_at=now,
        )
        self.repository.append_audit_event(rule.jurisdiction, event)
        self.repository.append_review(review)
        return review

    def submit_challenge(
        self,
        rule_id: str,
        challenge_type: str,
        issue: str,
        submitted_by_role: str,
        submitted_by_identity: str | None,
        challenged_version: dict,
        evidence_submitted: list[dict] | None = None,
    ) -> LegalChallenge:
        rule = self.repository.get_rule(rule_id)
        if rule is None:
            raise ReviewWorkflowError("cannot challenge nonexistent rule")
        now = datetime.now(UTC)
        event = self._audit_event(
            "CHALLENGE_SUBMITTED",
            "JurisdictionRule",
            rule_id,
            submitted_by_role,
            submitted_by_identity,
            issue,
            {"challenge_type": challenge_type},
            now,
        )
        challenge = LegalChallenge(
            id=f"challenge-{uuid4()}",
            object_type="JurisdictionRule",
            object_id=rule.id,
            jurisdiction=rule.jurisdiction,
            domain=rule.domain,
            challenge_type=challenge_type,
            challenge_state="OPEN",
            submitted_by_role=submitted_by_role,
            submitted_by_identity=submitted_by_identity,
            issue=issue,
            original_snapshot=rule.model_dump(mode="json"),
            challenged_version=challenged_version,
            evidence_submitted=evidence_submitted or [],
            reviewer_decision=None,
            corrected_version=None,
            audit_event_ids=[event.id],
            created_at=now,
            updated_at=now,
            resolved_at=None,
        )
        self.repository.append_audit_event(rule.jurisdiction, event)
        self.repository.append_challenge(challenge)
        return challenge

    def production_eligibility(self, rule_id: str, as_of_date: date | None = None) -> dict:
        rule = self.repository.get_rule(rule_id)
        if rule is None:
            raise ReviewWorkflowError("rule not found")
        query_date = as_of_date or datetime.now(UTC).date()
        blockers: list[str] = []
        warnings: list[str] = []
        authorities = self.repository.authorities_for_rule(rule)
        if rule.status != "ACTIVE":
            blockers.append("rule is not active")
        if rule.effective_from is None:
            blockers.append("effective date is unknown")
        elif rule.effective_from > query_date:
            blockers.append("rule is future-effective")
        if rule.effective_to is not None and rule.effective_to <= query_date:
            blockers.append("rule is no longer effective")
        if rule.critical_deficiencies:
            blockers.extend(rule.critical_deficiencies)
        if rule.conflicting_rule_ids:
            blockers.append("unresolved conflicting rule relationship")
        if any(
            authority.verification_status != "PRIMARY_SOURCE_VERIFIED" for authority in authorities
        ):
            blockers.append("all controlling authorities are not primary-source verified")
        if any(authority.verification_status == "SUPERSEDED" for authority in authorities):
            blockers.append("one or more authorities are superseded")
        if any(authority.change_detected for authority in authorities):
            blockers.append("source change detected pending review")
        if any(
            authority.source_classification == "UNVERIFIED_PRIVATE_LAW_CLAIM"
            for authority in authorities
        ):
            blockers.append("unsupported private claim cannot support production eligibility")
        approved_reviews = [
            review
            for review in self.repository.reviews_for_rule(rule_id)
            if review.review_status in {"APPROVED", "APPROVED_WITH_CONDITIONS"}
            and review.reviewer_role == "LICENSED_ATTORNEY"
        ]
        if not approved_reviews:
            blockers.append("licensed-attorney approval is missing")
        else:
            latest = max(
                approved_reviews,
                key=lambda review: review.reviewed_at or datetime.min.replace(tzinfo=UTC),
            )
            if latest.expires_at and latest.expires_at <= datetime.now(UTC):
                blockers.append("licensed-attorney review is expired")
            if latest.review_status == "APPROVED_WITH_CONDITIONS" and latest.conditions:
                blockers.append("review conditions remain unsatisfied")
            if latest.rejected_authorities:
                blockers.append("review rejected one or more cited authorities")
        open_challenges = [
            challenge
            for challenge in self.repository.challenges_for_rule(rule_id)
            if challenge.challenge_state not in {"REJECTED", "RESOLVED"}
        ]
        if open_challenges:
            blockers.append("open professional challenge exists")
        eligible = not blockers
        if not eligible:
            warnings.append(
                "Educational and issue-spotting output only. This is not a legal opinion."
            )
        return {
            "rule_id": rule_id,
            "production_eligible": eligible,
            "as_of_date": query_date.isoformat(),
            "blockers": sorted(set(blockers)),
            "warnings": warnings,
            "review_count": len(self.repository.reviews_for_rule(rule_id)),
            "challenge_count": len(open_challenges),
        }

    def _require_reviewable_rule(self, rule_id: str):
        rule = self.repository.get_rule(rule_id)
        if rule is None:
            raise ReviewWorkflowError("rule not found")
        if rule.status == "SUPERSEDED":
            raise ReviewWorkflowError("superseded rules require explicit historical handling")
        return rule

    @staticmethod
    def _audit_event(
        event_type: str,
        object_type: str,
        object_id: str,
        actor_role: str,
        actor_identity: str | None,
        reason: str | None,
        payload: dict,
        created_at: datetime,
    ) -> AuditEvent:
        return AuditEvent(
            id=f"audit-{uuid4()}",
            event_type=event_type,
            object_type=object_type,
            object_id=object_id,
            actor_role=actor_role,
            actor_identity=actor_identity,
            reason=reason,
            payload=payload,
            created_at=created_at,
        )
