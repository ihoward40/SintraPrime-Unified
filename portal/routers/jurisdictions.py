"""Jurisdiction, legal authority, and governed review routes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from legal_authority.constants import REVIEWER_ROLES
from legal_authority.review_workflow import ReviewWorkflowError
from portal.services.jurisdiction_rule_service import JurisdictionRuleService

router = APIRouter(tags=["jurisdictions"])
service = JurisdictionRuleService()


class SubmitReviewRequest(BaseModel):
    findings: str | None = None


class RecordReviewRequest(BaseModel):
    review_status: str
    findings: str
    declared_credentials: str | None = None
    credential_verification_status: str = "NOT_VERIFIED"
    conditions: list[str] = Field(default_factory=list)
    reviewed_authorities: list[str] = Field(default_factory=list)
    rejected_authorities: list[str] = Field(default_factory=list)
    approval_scope: str | None = None
    effective_date: date | None = None
    expires_at: datetime | None = None
    digital_signature: str | None = None


class ChallengeRequest(BaseModel):
    challenge_type: str
    issue: str
    challenged_version: dict[str, Any] = Field(default_factory=dict)
    evidence_submitted: list[dict[str, Any]] = Field(default_factory=list)


class RefreshMetadataRequest(BaseModel):
    supplied_content: str | None = None
    supplied_hash: str | None = None
    source_available: bool = True
    reason: str | None = None


class UCCFilingEvaluationRequest(BaseModel):
    filing_jurisdiction: str
    filing_number: str | None = None
    filing_office: str | None = None
    filing_date: date
    debtor_type: str
    debtor_name: str
    secured_party: str | None = None
    collateral_summary: str
    security_agreement_available: bool = False
    value_evidence_available: bool = False
    debtor_rights_in_collateral: bool = False
    amendments: list[dict[str, Any]] = Field(default_factory=list)
    continuation_records: list[dict[str, Any]] = Field(default_factory=list)
    termination_status: str | None = None
    duration_exception: str | None = None


def _authorized_actor(
    x_reviewer_role: str | None = Header(default=None),
    x_reviewer_identity: str | None = Header(default=None),
) -> tuple[str, str]:
    if not x_reviewer_role or not x_reviewer_identity:
        raise HTTPException(status_code=403, detail="review authorization headers required")
    if x_reviewer_role not in REVIEWER_ROLES:
        raise HTTPException(status_code=403, detail="invalid reviewer role")
    return x_reviewer_role, x_reviewer_identity


@router.get("/federal/domains")
async def list_federal_domains():
    return service.federal_domains()


@router.get("/federal/rules")
async def list_federal_rules(domain: str | None = None, topic: str | None = None):
    return service.federal_rules(domain=domain, topic=topic)


@router.get("/federal/rules/{rule_id}")
async def get_federal_rule(rule_id: str, as_of_date: date | None = Query(default=None)):
    payload = service.get_rule("FED", rule_id, as_of_date=as_of_date)
    if payload is None:
        raise HTTPException(status_code=404, detail="federal rule not found")
    return payload


@router.get("/federal/authorities")
async def list_federal_authorities():
    return service.federal_authorities()


@router.get("/federal/conflicts")
async def list_federal_conflicts():
    return service.federal_conflicts()


@router.get("/jurisdictions")
async def list_jurisdictions():
    return service.list_jurisdictions()


@router.get("/jurisdictions/{code}")
async def get_jurisdiction(code: str):
    jurisdiction = service.get_jurisdiction(code)
    if jurisdiction is None:
        raise HTTPException(status_code=404, detail="unsupported jurisdiction")
    return jurisdiction


@router.get("/jurisdictions/{code}/coverage")
async def get_jurisdiction_coverage(code: str):
    coverage = service.get_coverage(code)
    if coverage is None:
        raise HTTPException(status_code=404, detail="unsupported jurisdiction")
    return coverage


@router.get("/jurisdictions/{code}/review-queue")
async def get_review_queue(
    code: str,
    x_reviewer_role: str | None = Header(default=None),
    x_reviewer_identity: str | None = Header(default=None),
):
    _authorized_actor(x_reviewer_role, x_reviewer_identity)
    queue = service.review_queue(code)
    if queue is None:
        raise HTTPException(status_code=404, detail="unsupported jurisdiction")
    return queue


@router.get("/jurisdictions/{code}/conflicts")
async def get_conflicts(code: str):
    conflicts = service.conflicts(code)
    if conflicts is None:
        raise HTTPException(status_code=404, detail="unsupported jurisdiction")
    return conflicts


@router.get("/jurisdictions/{code}/stale-authorities")
async def get_stale_authorities(code: str):
    authorities = service.stale_authorities(code)
    if authorities is None:
        raise HTTPException(status_code=404, detail="unsupported jurisdiction")
    return authorities


@router.get("/jurisdictions/{code}/rules")
async def list_jurisdiction_rules(
    code: str,
    domain: str | None = None,
    topic: str | None = None,
    status: str | None = None,
    effective_date: date | None = Query(default=None),
    verification_state: str | None = None,
    requires_human_review: bool | None = None,
):
    rules = service.list_rules(
        code,
        domain=domain,
        topic=topic,
        status=status,
        effective_date=effective_date,
        verification_state=verification_state,
        requires_human_review=requires_human_review,
    )
    if rules is None:
        raise HTTPException(status_code=404, detail="unsupported jurisdiction")
    return rules


@router.get("/jurisdictions/{code}/rules/{rule_id}")
async def get_jurisdiction_rule(
    code: str,
    rule_id: str,
    as_of_date: date | None = Query(default=None),
):
    rule = service.get_rule(code, rule_id, as_of_date=as_of_date)
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    return rule


@router.get("/legal-authorities/{authority_id}")
async def get_legal_authority(authority_id: str):
    authority = service.get_authority(authority_id)
    if authority is None:
        raise HTTPException(status_code=404, detail="authority not found")
    return authority


@router.post("/legal-authorities/{authority_id}/refresh-metadata")
async def refresh_authority_metadata(
    authority_id: str,
    payload: RefreshMetadataRequest,
    x_reviewer_role: str | None = Header(default=None),
    x_reviewer_identity: str | None = Header(default=None),
):
    role, identity = _authorized_actor(x_reviewer_role, x_reviewer_identity)
    try:
        return service.refresh_authority_metadata(
            authority_id,
            actor_role=role,
            actor_identity=identity,
            payload=payload.model_dump(),
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="authority not found") from None


@router.get("/legal-rules/compare")
async def compare_legal_rules(
    jurisdiction: str = "NJ",
    domain: str = "trust_law",
    topic: str = "revocable trust",
    jurisdictions: str | None = None,
    as_of_date: date | None = Query(default=None),
):
    parsed = None
    if jurisdictions:
        parsed = [item.strip().upper() for item in jurisdictions.split(",") if item.strip()]
    return service.compare(jurisdiction, domain, topic, as_of_date=as_of_date, jurisdictions=parsed)


@router.post("/ucc-filings/evaluate")
async def evaluate_ucc_filing(
    payload: UCCFilingEvaluationRequest,
    x_reviewer_role: str | None = Header(default=None),
    x_reviewer_identity: str | None = Header(default=None),
):
    role, identity = _authorized_actor(x_reviewer_role, x_reviewer_identity)
    try:
        return service.evaluate_ucc_filing(payload.model_dump(), role, identity)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/ucc-filings/{evaluation_id}")
async def get_ucc_filing_evaluation(evaluation_id: str):
    evaluation = service.get_ucc_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    return evaluation


@router.post("/legal-rules/{rule_id}/submit-review")
async def submit_rule_review(
    rule_id: str,
    payload: SubmitReviewRequest,
    x_reviewer_role: str | None = Header(default=None),
    x_reviewer_identity: str | None = Header(default=None),
):
    role, identity = _authorized_actor(x_reviewer_role, x_reviewer_identity)
    try:
        return service.submit_review(rule_id, role, identity, payload.findings)
    except ReviewWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/legal-rules/{rule_id}/reviews")
async def record_rule_review(
    rule_id: str,
    payload: RecordReviewRequest,
    x_reviewer_role: str | None = Header(default=None),
    x_reviewer_identity: str | None = Header(default=None),
):
    role, identity = _authorized_actor(x_reviewer_role, x_reviewer_identity)
    try:
        return service.record_review(rule_id, role, identity, payload.model_dump())
    except ReviewWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/legal-rules/{rule_id}/reviews")
async def list_rule_reviews(rule_id: str):
    reviews = service.reviews_for_rule(rule_id)
    if reviews is None:
        raise HTTPException(status_code=404, detail="rule not found")
    return reviews


@router.post("/legal-rules/{rule_id}/challenges")
async def submit_rule_challenge(
    rule_id: str,
    payload: ChallengeRequest,
    x_reviewer_role: str | None = Header(default=None),
    x_reviewer_identity: str | None = Header(default=None),
):
    role, identity = _authorized_actor(x_reviewer_role, x_reviewer_identity)
    try:
        return service.submit_challenge(rule_id, role, identity, payload.model_dump())
    except ReviewWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/legal-rules/{rule_id}/challenges")
async def list_rule_challenges(rule_id: str):
    challenges = service.challenges_for_rule(rule_id)
    if challenges is None:
        raise HTTPException(status_code=404, detail="rule not found")
    return challenges
