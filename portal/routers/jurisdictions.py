"""Read-only jurisdiction and legal authority routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from portal.services.jurisdiction_rule_service import JurisdictionRuleService

router = APIRouter(tags=["jurisdictions"])
service = JurisdictionRuleService()


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


@router.get("/legal-rules/compare")
async def compare_legal_rules(
    jurisdiction: str,
    domain: str,
    topic: str,
    as_of_date: date | None = Query(default=None),
):
    return service.compare(jurisdiction, domain, topic, as_of_date=as_of_date)
