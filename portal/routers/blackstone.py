"""
Blackstone router for the SintraPrime portal.

Exposes governance evaluation endpoints on top of the BRA engines.
This is a lightweight integration point; it does not require a database
and operates on in-memory governance objects.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from blackstone.engines import BlackstoneOrchestrator
from blackstone.models import (
    Claim,
    Confidence,
    EvidenceItem,
    Jurisdiction,
    Risk,
    Source,
    SourceClassification,
)
from portal.database import get_db
from portal.services.blackstone_service import BlackstoneEvaluationService, EvidenceLedgerService

router = APIRouter(prefix="/api/v1/blackstone", tags=["blackstone"])

# Shared orchestrator instance (simple stateful service for demo/evaluation)
_orchestrator = BlackstoneOrchestrator(agents=["AGENT-HERMES-2-0", "AGENT-BLACKSTONE-2-0"])

# Pre-register common jurisdiction
_orchestrator.register_jurisdiction(Jurisdiction(name="United States", level="federal"))


class SourcePayload(BaseModel):
    id: str
    citation: str
    classification: SourceClassification
    publisher: str | None = None
    url: str | None = None


class EvidencePayload(BaseModel):
    id: str
    source_id: str
    claim_text: str
    quotation: str = ""
    context: str = ""
    confidence: Confidence = Confidence.MODERATE


class ClaimPayload(BaseModel):
    id: str
    text: str
    subject: str
    assumptions: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RiskPayload(BaseModel):
    id: str
    category: str
    description: str
    likelihood: str = "insufficient"
    impact: str = "insufficient"
    controls: list[str] = Field(default_factory=list)
    owner: str = ""
    tags: list[str] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    question: str
    sources: list[SourcePayload]
    evidence: list[EvidencePayload]
    claim: ClaimPayload
    counter_evidence: list[EvidencePayload] = Field(default_factory=list)
    case_id: str | None = None
    tenant_id: str | None = None


class EvaluateResponse(BaseModel):
    claim_id: str
    status: str
    confidence: str
    recommendation: str
    rationale: str
    controlling_authority: dict | None
    conflicts: list[dict]
    provenance_verified: bool
    agents: list[str]
    evaluation_id: str | None = None


class CaseIntakeRequest(BaseModel):
    case_id: str
    tenant_id: str | None = None
    title: str
    question: str
    claim: ClaimPayload
    sources: list[SourcePayload]
    evidence: list[EvidencePayload]
    counter_evidence: list[EvidencePayload] = Field(default_factory=list)
    risks: list[RiskPayload] = Field(default_factory=list)


class CaseIntakeResponse(BaseModel):
    case_id: str
    evaluation_id: str
    status: str
    confidence: str
    recommendation: str
    rationale: str
    provenance_verified: bool
    ledger_entries: int


class CaseStatusResponse(BaseModel):
    case_id: str
    evaluations: list[EvaluateResponse]
    total_evaluations: int
    latest_status: str
    latest_confidence: str
    ledger_entries: int


@router.post("/cases", response_model=CaseIntakeResponse, status_code=status.HTTP_201_CREATED)
async def intake_case(
    request: CaseIntakeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Intake a new case: register sources, add evidence, evaluate the claim,
    and persist the evaluation snapshot plus the full provenance chain.
    """
    orchestrator = BlackstoneOrchestrator(agents=["AGENT-HERMES-2-0", "AGENT-BLACKSTONE-2-0"])
    orchestrator.register_jurisdiction(Jurisdiction(name="United States", level="federal"))

    source_map = {}
    for s in request.sources:
        source = Source(
            id=s.id,
            citation=s.citation,
            classification=s.classification,
            publisher=s.publisher,
            url=s.url,
        )
        orchestrator.register_source(source)
        source_map[s.id] = source

    def _to_evidence(ev: EvidencePayload) -> EvidenceItem:
        src = source_map.get(ev.source_id)
        if not src:
            raise HTTPException(status_code=400, detail=f"Unknown source_id: {ev.source_id}")
        return EvidenceItem(
            id=ev.id,
            source=src,
            claim_text=ev.claim_text,
            quotation=ev.quotation,
            context=ev.context,
            confidence=ev.confidence,
        )

    claim = Claim(
        id=request.claim.id,
        text=request.claim.text,
        subject=request.claim.subject,
        assumptions=request.claim.assumptions,
        missing_evidence=request.claim.missing_evidence,
        tags=request.claim.tags,
    )

    for ev in request.evidence:
        evidence = _to_evidence(ev)
        orchestrator.add_evidence(evidence, actor="AGENT-BLACKSTONE-2-0")
        claim.evidence.append(evidence)

    for ev in request.counter_evidence:
        evidence = _to_evidence(ev)
        orchestrator.add_evidence(evidence, actor="AGENT-BLACKSTONE-2-0")
        claim.counter_evidence.append(evidence)

    for rp in request.risks:
        orchestrator.add_risk(
            Risk(
                id=rp.id,
                category=rp.category,
                description=rp.description,
                likelihood=Confidence(rp.likelihood),
                impact=Confidence(rp.impact),
                controls=rp.controls,
                owner=rp.owner,
                actor="AGENT-BLACKSTONE-2-0",
                tags=rp.tags,
            ),
            actor="AGENT-BLACKSTONE-2-0",
        )

    orchestrator.add_claim(claim)

    result = orchestrator.evaluate(
        request.claim.id, question=request.question, actor="AGENT-BLACKSTONE-2-0"
    )

    # Persist evaluation snapshot and provenance ledger entries
    snapshot = await BlackstoneEvaluationService.save(
        db=db,
        claim_id=request.claim.id,
        evaluation=result,
        case_id=request.case_id,
        tenant_id=request.tenant_id,
    )

    ledger_count = 0
    for entry in orchestrator.provenance.chain(request.claim.id):
        await EvidenceLedgerService.record(
            db=db,
            object_type=entry.object_type,
            object_id=entry.object_id,
            action=entry.action,
            actor=entry.actor,
            payload={"prior_hash": entry.prior_hash, "record_hash": entry.record_hash, **entry.payload},
            parent_id=entry.prior_hash or None,
            provenance_hash=entry.record_hash,
            tenant_id=request.tenant_id,
        )
        ledger_count += 1

    # Record the case intake event itself
    await EvidenceLedgerService.record(
        db=db,
        object_type="case",
        object_id=request.case_id,
        action="INTAKE",
        actor="AGENT-BLACKSTONE-2-0",
        payload={"title": request.title, "claim_id": request.claim.id},
        tenant_id=request.tenant_id,
    )
    ledger_count += 1

    await db.commit()

    return CaseIntakeResponse(
        case_id=request.case_id,
        evaluation_id=str(snapshot.id),
        status=result["claim"]["status"],
        confidence=result["claim"]["confidence"],
        recommendation=result["recommendation"]["recommendation"],
        rationale=result["recommendation"]["rationale"],
        provenance_verified=result["provenance"]["verified"],
        ledger_entries=ledger_count,
    )


@router.get("/cases/{case_id}", response_model=CaseStatusResponse)
async def get_case_status(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str | None = None,
):
    """
    Retrieve all Blackstone evaluations and ledger entries for a case.
    """
    evaluations = await BlackstoneEvaluationService.get_by_case(db, case_id=case_id, tenant_id=tenant_id)
    chain = await EvidenceLedgerService.get_chain(db, object_type="case", object_id=case_id, tenant_id=tenant_id)

    eval_responses = [
        EvaluateResponse(
            claim_id=evaluation.claim_id,
            status=evaluation.status,
            confidence=evaluation.confidence,
            recommendation=evaluation.recommendation,
            rationale=evaluation.rationale,
            controlling_authority=evaluation.controlling_authority,
            conflicts=evaluation.conflicts,
            provenance_verified=True,
            agents=evaluation.agents,
            evaluation_id=str(evaluation.id),
        )
        for evaluation in evaluations
    ]

    latest = evaluations[0] if evaluations else None
    return CaseStatusResponse(
        case_id=case_id,
        evaluations=eval_responses,
        total_evaluations=len(evaluations),
        latest_status=latest.status if latest else "unknown",
        latest_confidence=latest.confidence if latest else "unknown",
        ledger_entries=len(chain),
    )


@router.post("/evaluate", response_model=EvaluateResponse, status_code=status.HTTP_200_OK)
async def evaluate_claim(
    request: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluate a claim against provided evidence using the Blackstone engines.
    """
    orchestrator = BlackstoneOrchestrator(agents=["AGENT-HERMES-2-0", "AGENT-BLACKSTONE-2-0"])
    orchestrator.register_jurisdiction(Jurisdiction(name="United States", level="federal"))

    source_map = {}
    for s in request.sources:
        source = Source(
            id=s.id,
            citation=s.citation,
            classification=s.classification,
            publisher=s.publisher,
            url=s.url,
        )
        orchestrator.register_source(source)
        source_map[s.id] = source

    def _to_evidence(ev: EvidencePayload) -> EvidenceItem:
        src = source_map.get(ev.source_id)
        if not src:
            raise HTTPException(status_code=400, detail=f"Unknown source_id: {ev.source_id}")
        return EvidenceItem(
            id=ev.id,
            source=src,
            claim_text=ev.claim_text,
            quotation=ev.quotation,
            context=ev.context,
            confidence=ev.confidence,
        )

    claim = Claim(
        id=request.claim.id,
        text=request.claim.text,
        subject=request.claim.subject,
        assumptions=request.claim.assumptions,
        missing_evidence=request.claim.missing_evidence,
        tags=request.claim.tags,
    )

    for ev in request.evidence:
        evidence = _to_evidence(ev)
        orchestrator.add_evidence(evidence, actor="AGENT-BLACKSTONE-2-0")
        claim.evidence.append(evidence)

    for ev in request.counter_evidence:
        evidence = _to_evidence(ev)
        orchestrator.add_evidence(evidence, actor="AGENT-BLACKSTONE-2-0")
        claim.counter_evidence.append(evidence)

    orchestrator.add_claim(claim)

    result = orchestrator.evaluate(request.claim.id, question=request.question, actor="AGENT-BLACKSTONE-2-0")

    # Persist evaluation snapshot and provenance ledger entries
    snapshot = await BlackstoneEvaluationService.save(
        db=db,
        claim_id=request.claim.id,
        evaluation=result,
        case_id=request.case_id,
        tenant_id=request.tenant_id,
    )
    for entry in orchestrator.provenance.chain(request.claim.id):
        await EvidenceLedgerService.record(
            db=db,
            object_type=entry.object_type,
            object_id=entry.object_id,
            action=entry.action,
            actor=entry.actor,
            payload={"prior_hash": entry.prior_hash, "record_hash": entry.record_hash, **entry.payload},
            parent_id=entry.prior_hash or None,
            provenance_hash=entry.record_hash,
            tenant_id=request.tenant_id,
        )
    await db.commit()

    return EvaluateResponse(
        claim_id=request.claim.id,
        status=result["claim"]["status"],
        confidence=result["claim"]["confidence"],
        recommendation=result["recommendation"]["recommendation"],
        rationale=result["recommendation"]["rationale"],
        controlling_authority=result["authority"]["controlling_authority"],
        conflicts=result["authority"]["conflicts"],
        provenance_verified=result["provenance"]["verified"],
        agents=result["recommendation"]["agents"],
        evaluation_id=str(snapshot.id),
    )


@router.get("/health")
async def blackstone_health():
    """Health check for the Blackstone governance endpoint."""
    return {"status": "ok", "service": "blackstone", "version": "2.0"}
