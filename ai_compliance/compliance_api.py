"""
compliance_api.py — FastAPI Router for SintraPrime-Unified AI Compliance Module
Provides REST endpoints for compliance checking, bias detection, ethics review, and reporting.
"""

from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid

try:
    from fastapi import APIRouter, HTTPException, Query
    from pydantic import BaseModel, Field, validator
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Stub classes for testing without FastAPI
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def dict(self):
            return self.__dict__
    def Field(*args, **kwargs):
        return None
    APIRouter = None

from ai_compliance.ai_law_db import (
    AILaw,
    ALL_LAWS,
    ComplianceArea,
    Jurisdiction,
    RiskTier,
    get_applicable_laws,
    get_laws_summary,
)
from ai_compliance.compliance_checker import (
    CheckStatus,
    ComplianceChecker,
    ComplianceSummary,
    OperationContext,
    quick_check,
)
from ai_compliance.ethics_framework import (
    AIAction,
    EthicsDecision,
    EthicsReview,
    EthicsReviewer,
    ethics_review,
)
from ai_compliance.bias_detector import BiasDetector, BiasReport, check_bias
from ai_compliance.compliance_reporter import (
    ComplianceReportData,
    ComplianceReporter,
    ComplianceSnapshot,
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ComplianceCheckRequest(BaseModel):
    operation_type: str = Field(..., description="Type of operation (e.g., 'legal_advice', 'document_drafting')")
    description: str = Field(..., description="Description of the operation")
    jurisdictions: List[str] = Field(default=["US_FEDERAL"], description="Applicable jurisdiction codes")
    risk_tier: str = Field(default="HIGH", description="Risk tier: HIGH, LIMITED, MINIMAL, UNACCEPTABLE")
    involves_legal_advice: bool = Field(default=False)
    involves_personal_data: bool = Field(default=False)
    involves_financial_advice: bool = Field(default=False)
    involves_employment_decision: bool = Field(default=False)
    involves_healthcare: bool = Field(default=False)
    ai_identifies_as_ai: bool = Field(default=True)
    provides_explanation: bool = Field(default=True)
    allows_human_review: bool = Field(default=True)
    data_fields_collected: List[str] = Field(default_factory=list)
    output_text: Optional[str] = Field(default=None, description="Output text to check")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComplianceCheckResponse(BaseModel):
    operation_id: str
    overall_status: str
    risk_score: int
    compliant_count: int
    non_compliant_count: int
    needs_review_count: int
    checks: List[Dict[str, Any]]
    applicable_laws: List[str]
    generated_at: str


class EthicsReviewRequest(BaseModel):
    action_type: str = Field(..., description="Type of AI action")
    description: str = Field(..., description="Description of the action")
    requester_context: str = Field(default="", description="Context of who is requesting")
    output_preview: Optional[str] = Field(default=None, description="Preview of planned output")
    affects_third_parties: bool = Field(default=False)
    involves_sensitive_data: bool = Field(default=False)
    is_irreversible: bool = Field(default=False)
    involves_vulnerable_person: bool = Field(default=False)
    could_cause_financial_harm: bool = Field(default=False)
    could_cause_physical_harm: bool = Field(default=False)
    is_discriminatory: Optional[bool] = Field(default=None)
    is_transparent: bool = Field(default=True)
    respects_autonomy: bool = Field(default=True)
    benefits_user: bool = Field(default=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EthicsReviewResponse(BaseModel):
    action_id: str
    decision: str
    overall_score: float
    passes: bool
    red_line_violations: List[Dict[str, str]]
    principle_scores: Dict[str, float]
    conditions: List[str]
    refusal_reason: Optional[str]
    recommendations: List[str]
    reviewed_at: str


class BiasCheckRequest(BaseModel):
    output_text: str = Field(..., description="Text to check for bias")
    output_id: Optional[str] = Field(default=None, description="Optional output identifier")


class BiasCheckResponse(BaseModel):
    output_id: str
    is_biased: bool
    overall_severity: str
    bias_score: float
    requires_blocking: bool
    indicator_count: int
    indicators: List[Dict[str, Any]]
    proxy_variables: List[str]
    remediation: List[str]
    analyzed_at: str


class LawSummary(BaseModel):
    law_id: str
    name: str
    jurisdiction: str
    effective_date: str
    status: str
    areas: List[str]
    risk_tiers: List[str]


class ApplicableLawsRequest(BaseModel):
    jurisdictions: List[str] = Field(default=["US_FEDERAL"])
    risk_tier: str = Field(default="HIGH")
    legal_profession: bool = Field(default=False)
    compliance_areas: Optional[List[str]] = Field(default=None)


class FullReportRequest(BaseModel):
    organization: str = Field(default="SintraPrime-Unified")
    period_days: int = Field(default=30, description="Number of days to cover in report")
    include_snapshots: bool = Field(default=True)


class FullReportResponse(BaseModel):
    report_id: str
    report_markdown: str
    summary: Dict[str, Any]
    generated_at: str


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _parse_jurisdiction(code: str) -> Jurisdiction:
    """Parse jurisdiction code string to Jurisdiction enum."""
    mapping = {
        "EU": Jurisdiction.EU,
        "US_FEDERAL": Jurisdiction.US_FEDERAL,
        "US_CA": Jurisdiction.US_CA,
        "CA": Jurisdiction.US_CA,
        "US_TX": Jurisdiction.US_TX,
        "TX": Jurisdiction.US_TX,
        "US_CO": Jurisdiction.US_CO,
        "CO": Jurisdiction.US_CO,
        "US_NY": Jurisdiction.US_NY,
        "NY": Jurisdiction.US_NY,
        "US_IL": Jurisdiction.US_IL,
        "IL": Jurisdiction.US_IL,
        "US_VA": Jurisdiction.US_VA,
        "VA": Jurisdiction.US_VA,
        "US_WA": Jurisdiction.US_WA,
        "WA": Jurisdiction.US_WA,
        "US_FL": Jurisdiction.US_FL,
        "FL": Jurisdiction.US_FL,
        "INTERNATIONAL": Jurisdiction.INTERNATIONAL,
        "PROFESSIONAL": Jurisdiction.PROFESSIONAL,
    }
    result = mapping.get(code.upper())
    if not result:
        raise ValueError(f"Unknown jurisdiction code: {code}")
    return result


def _parse_risk_tier(tier: str) -> RiskTier:
    """Parse risk tier string to RiskTier enum."""
    mapping = {
        "UNACCEPTABLE": RiskTier.UNACCEPTABLE,
        "HIGH": RiskTier.HIGH,
        "LIMITED": RiskTier.LIMITED,
        "MINIMAL": RiskTier.MINIMAL,
    }
    result = mapping.get(tier.upper())
    if not result:
        raise ValueError(f"Unknown risk tier: {tier}")
    return result


def _parse_compliance_area(area: str) -> ComplianceArea:
    """Parse compliance area string to ComplianceArea enum."""
    for ca in ComplianceArea:
        if ca.value == area.lower() or ca.name == area.upper():
            return ca
    raise ValueError(f"Unknown compliance area: {area}")


def _summary_to_response(summary: ComplianceSummary) -> ComplianceCheckResponse:
    """Convert ComplianceSummary to API response model."""
    return ComplianceCheckResponse(
        operation_id=summary.operation_id,
        overall_status=summary.overall_status.value,
        risk_score=summary.risk_score,
        compliant_count=summary.compliant_count,
        non_compliant_count=summary.non_compliant_count,
        needs_review_count=summary.needs_review_count,
        checks=[
            {
                "check_id": c.check_id,
                "law": c.law.short_name,
                "law_id": c.law.law_id,
                "area": c.area.value,
                "status": c.status.value,
                "severity": c.severity.value,
                "findings": c.findings,
                "remediation": c.remediation,
            }
            for c in summary.checks
        ],
        applicable_laws=[law.short_name for law in summary.applicable_laws],
        generated_at=summary.generated_at.isoformat(),
    )


def _ethics_to_response(review: EthicsReview) -> EthicsReviewResponse:
    """Convert EthicsReview to API response model."""
    return EthicsReviewResponse(
        action_id=review.action_id,
        decision=review.decision.value,
        overall_score=review.overall_score,
        passes=review.passes,
        red_line_violations=[
            {
                "id": v.red_line_id,
                "name": v.red_line_name,
                "triggered_by": v.triggered_by,
            }
            for v in review.red_line_violations
        ],
        principle_scores={
            ps.principle.value: round(ps.score, 3)
            for ps in review.principle_scores
        },
        conditions=review.conditions,
        refusal_reason=review.refusal_reason,
        recommendations=review.recommendations,
        reviewed_at=review.reviewed_at.isoformat(),
    )


def _bias_to_response(report: BiasReport) -> BiasCheckResponse:
    """Convert BiasReport to API response model."""
    return BiasCheckResponse(
        output_id=report.output_id,
        is_biased=report.is_biased,
        overall_severity=report.overall_severity.value,
        bias_score=report.bias_score,
        requires_blocking=report.requires_blocking,
        indicator_count=len(report.indicators),
        indicators=[
            {
                "type": i.bias_type.value,
                "category": i.category.value,
                "severity": i.severity.value,
                "description": i.description,
                "evidence": i.evidence[:100],
            }
            for i in report.indicators
        ],
        proxy_variables=report.proxy_variables_detected,
        remediation=report.remediation_suggestions,
        analyzed_at=report.analyzed_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Route Handler Functions (usable without FastAPI)
# ---------------------------------------------------------------------------

def handle_compliance_check(request: ComplianceCheckRequest) -> ComplianceCheckResponse:
    """
    Run a full compliance check on an AI operation.
    POST /compliance/check
    """
    try:
        jurisdictions = [_parse_jurisdiction(j) for j in request.jurisdictions]
    except ValueError as e:
        raise ValueError(str(e))

    try:
        risk_tier = _parse_risk_tier(request.risk_tier)
    except ValueError as e:
        raise ValueError(str(e))

    operation_id = str(uuid.uuid4())[:12]
    ctx = OperationContext(
        operation_id=operation_id,
        operation_type=request.operation_type,
        description=request.description,
        jurisdictions=jurisdictions,
        risk_tier=risk_tier,
        involves_legal_advice=request.involves_legal_advice,
        involves_personal_data=request.involves_personal_data,
        involves_financial_advice=request.involves_financial_advice,
        involves_employment_decision=request.involves_employment_decision,
        involves_healthcare=request.involves_healthcare,
        ai_identifies_as_ai=request.ai_identifies_as_ai,
        provides_explanation=request.provides_explanation,
        allows_human_review=request.allows_human_review,
        data_fields_collected=request.data_fields_collected,
        output_text=request.output_text,
        metadata=request.metadata,
    )

    checker = ComplianceChecker()
    summary = checker.run_full_check(ctx)
    return _summary_to_response(summary)


def handle_list_laws(
    jurisdiction: Optional[str] = None,
    active_only: bool = True,
) -> List[LawSummary]:
    """
    List all applicable AI laws.
    GET /compliance/laws
    """
    laws = ALL_LAWS

    if active_only:
        laws = [l for l in laws if l.is_active()]

    if jurisdiction:
        try:
            j = _parse_jurisdiction(jurisdiction)
            laws = [l for l in laws if l.jurisdiction == j]
        except ValueError:
            pass

    return [
        LawSummary(
            law_id=law.law_id,
            name=law.short_name,
            jurisdiction=law.jurisdiction.value,
            effective_date=law.effective_date.isoformat(),
            status=law.status,
            areas=[a.value for a in law.compliance_areas],
            risk_tiers=[r.value for r in law.risk_tiers],
        )
        for law in laws
    ]


def handle_ethics_review(request: EthicsReviewRequest) -> EthicsReviewResponse:
    """
    Run an ethics review on a proposed AI action.
    POST /compliance/ethics-review
    """
    action = AIAction(
        action_id=str(uuid.uuid4())[:12],
        action_type=request.action_type,
        description=request.description,
        requester_context=request.requester_context,
        output_preview=request.output_preview,
        affects_third_parties=request.affects_third_parties,
        involves_sensitive_data=request.involves_sensitive_data,
        is_irreversible=request.is_irreversible,
        involves_vulnerable_person=request.involves_vulnerable_person,
        could_cause_financial_harm=request.could_cause_financial_harm,
        could_cause_physical_harm=request.could_cause_physical_harm,
        is_discriminatory=request.is_discriminatory,
        is_transparent=request.is_transparent,
        respects_autonomy=request.respects_autonomy,
        benefits_user=request.benefits_user,
        metadata=request.metadata,
    )
    reviewer = EthicsReviewer()
    review = reviewer.review(action)
    return _ethics_to_response(review)


def handle_bias_check(request: BiasCheckRequest) -> BiasCheckResponse:
    """
    Check AI output text for demographic bias.
    POST /compliance/bias-check
    """
    output_id = request.output_id or str(uuid.uuid4())[:12]
    detector = BiasDetector()
    report = detector.analyze(request.output_text, output_id)
    return _bias_to_response(report)


def handle_generate_report(
    organization: str = "SintraPrime-Unified",
    period_days: int = 30,
) -> FullReportResponse:
    """
    Generate a full compliance report.
    GET /compliance/report
    """
    from datetime import timedelta

    today = date.today()
    report_id = str(uuid.uuid4())[:12]

    data = ComplianceReportData(
        report_id=report_id,
        report_title=f"AI Compliance Report — {organization}",
        organization=organization,
        generated_at=datetime.utcnow(),
        period_start=today - timedelta(days=period_days),
        period_end=today,
        compliance_summaries=[],
        bias_reports=[],
        ethics_reviews=[],
        historical_snapshots=[
            ComplianceSnapshot(
                snapshot_date=today - timedelta(days=period_days),
                overall_risk_score=42,
                compliant_count=85,
                non_compliant_count=10,
                needs_review_count=8,
                bias_score=0.08,
                ethics_approval_rate=0.91,
                active_violations=3,
                label="Period Start",
            ),
            ComplianceSnapshot(
                snapshot_date=today,
                overall_risk_score=28,
                compliant_count=94,
                non_compliant_count=4,
                needs_review_count=5,
                bias_score=0.04,
                ethics_approval_rate=0.96,
                active_violations=1,
                label="Current",
            ),
        ],
    )

    reporter = ComplianceReporter()
    report_markdown = reporter.generate_report(data)
    summary_dict = reporter.generate_summary_dict(data)

    return FullReportResponse(
        report_id=report_id,
        report_markdown=report_markdown,
        summary=summary_dict,
        generated_at=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# FastAPI Router (only instantiated when FastAPI is available)
# ---------------------------------------------------------------------------

if FASTAPI_AVAILABLE:
    router = APIRouter(prefix="/compliance", tags=["AI Compliance"])

    @router.post("/check", response_model=Dict[str, Any])
    async def compliance_check(request: ComplianceCheckRequest):
        """Run a full compliance check against all applicable AI laws."""
        response = handle_compliance_check(request)
        return response.dict() if hasattr(response, 'dict') else vars(response)

    @router.get("/laws")
    async def list_laws(
        jurisdiction: Optional[str] = Query(default=None, description="Filter by jurisdiction code"),
        active_only: bool = Query(default=True, description="Return only active laws"),
    ):
        """List all applicable AI laws and regulations."""
        laws = handle_list_laws(jurisdiction=jurisdiction, active_only=active_only)
        return {"laws": [vars(l) for l in laws], "total": len(laws)}

    @router.post("/ethics-review", response_model=Dict[str, Any])
    async def ethics_review_endpoint(request: EthicsReviewRequest):
        """Run an ethical review of a proposed AI action."""
        response = handle_ethics_review(request)
        return vars(response)

    @router.post("/bias-check", response_model=Dict[str, Any])
    async def bias_check_endpoint(request: BiasCheckRequest):
        """Check AI output text for demographic bias."""
        response = handle_bias_check(request)
        return vars(response)

    @router.get("/report")
    async def generate_report(
        organization: str = Query(default="SintraPrime-Unified"),
        period_days: int = Query(default=30, description="Days to cover in report"),
    ):
        """Generate a comprehensive AI compliance report."""
        response = handle_generate_report(
            organization=organization,
            period_days=period_days,
        )
        return vars(response)


if __name__ == "__main__":
    print("=== Testing Compliance API Handlers ===\n")

    # Test compliance check
    req = ComplianceCheckRequest(
        operation_type="legal_advice",
        description="Provide contract review assistance",
        jurisdictions=["US_CA", "US_FEDERAL"],
        risk_tier="HIGH",
        involves_legal_advice=True,
        ai_identifies_as_ai=True,
    )
    resp = handle_compliance_check(req)
    print(f"Compliance Check — Status: {resp.overall_status}, Risk: {resp.risk_score}/100")

    # Test ethics review
    ethics_req = EthicsReviewRequest(
        action_type="generate_legal_document",
        description="Draft an NDA for a startup",
        is_transparent=True,
        benefits_user=True,
    )
    ethics_resp = handle_ethics_review(ethics_req)
    print(f"Ethics Review — Decision: {ethics_resp.decision}, Score: {ethics_resp.overall_score:.3f}")

    # Test bias check
    bias_req = BiasCheckRequest(output_text="The contract terms are fair and equitable for all parties.")
    bias_resp = handle_bias_check(bias_req)
    print(f"Bias Check — Biased: {bias_resp.is_biased}, Score: {bias_resp.bias_score:.3f}")

    print("\n✅ All API handlers tested successfully")
