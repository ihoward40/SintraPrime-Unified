"""
Builder API — FastAPI Router for SintraPrime App Builder & Digital Twin
=======================================================================
Provides REST endpoints for building apps, managing templates,
and interacting with Digital Twin life models.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .app_builder import AppBuilder
from .app_types import (
    AppSpec, AppType, BuildResult, IntegrationType, LifeEvent,
)
from .digital_twin import DigitalTwin
from .template_library import TemplateLibrary


# ---------------------------------------------------------------------------
# Shared instances (in production, inject via dependency)
# ---------------------------------------------------------------------------
_builder = AppBuilder()
_twin = DigitalTwin()
_library = TemplateLibrary()

router = APIRouter(prefix="", tags=["app_builder"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class BuildFromDescriptionRequest(BaseModel):
    description: str
    deploy_target: Optional[str] = "local"


class BuildFromSpecRequest(BaseModel):
    spec: Dict[str, Any]
    deploy_target: Optional[str] = "local"


class LegalPortalRequest(BaseModel):
    client_name: str
    practice_areas: List[str]
    jurisdiction: str = "United States"


class FinancialDashboardRequest(BaseModel):
    user_profile: Dict[str, Any]


class TrustManagerRequest(BaseModel):
    trust_details: Dict[str, Any]


class CRMRequest(BaseModel):
    firm_details: Dict[str, Any]


class IterateRequest(BaseModel):
    feedback: str


class DeployRequest(BaseModel):
    target: str = "local"


class LifeEventRequest(BaseModel):
    event_id: Optional[str] = None
    event_type: str
    title: str
    description: str = ""
    date: str = ""
    impact_level: str = "low"
    data: Dict[str, Any] = {}


class CreateTwinRequest(BaseModel):
    name: str


class TemplateCustomizeRequest(BaseModel):
    overrides: Dict[str, Any] = {}
    deploy_target: Optional[str] = "local"


# ---------------------------------------------------------------------------
# App Builder Endpoints
# ---------------------------------------------------------------------------

@router.post("/builder/build", response_model=Dict[str, Any], summary="Build app from description or spec")
async def build_app(request: BuildFromDescriptionRequest) -> Dict[str, Any]:
    """
    Build a complete web app from a natural language description.

    Example:
    ```json
    {"description": "Build a law firm website for Smith & Associates specializing in estate planning in New Jersey"}
    ```
    """
    try:
        spec = _builder.build_from_description(request.description)
        result = _builder.build(spec)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/builder/build/legal-portal", response_model=Dict[str, Any], summary="Build legal portal")
async def build_legal_portal(request: LegalPortalRequest) -> Dict[str, Any]:
    """
    One-command legal portal builder.

    Creates a complete law firm website with:
    - Practice area pages
    - Attorney bios
    - Client intake forms
    - Document portal
    - Stripe billing
    - SEO optimization
    """
    try:
        result = _builder.build_legal_portal(
            request.client_name,
            request.practice_areas,
            request.jurisdiction,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/builder/build/financial-dashboard", response_model=Dict[str, Any], summary="Build financial dashboard")
async def build_financial_dashboard(request: FinancialDashboardRequest) -> Dict[str, Any]:
    """Build a personal finance dashboard from user profile."""
    try:
        result = _builder.build_financial_dashboard(request.user_profile)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/builder/build/trust-manager", response_model=Dict[str, Any], summary="Build trust management portal")
async def build_trust_manager(request: TrustManagerRequest) -> Dict[str, Any]:
    """Build a trust management portal."""
    try:
        result = _builder.build_trust_manager(request.trust_details)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/builder/build/client-crm", response_model=Dict[str, Any], summary="Build law firm CRM")
async def build_client_crm(request: CRMRequest) -> Dict[str, Any]:
    """Build a law firm client CRM."""
    try:
        result = _builder.build_client_crm(request.firm_details)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/builder/apps", response_model=List[Dict[str, Any]], summary="List built apps")
async def list_apps() -> List[Dict[str, Any]]:
    """List all built apps."""
    return _builder.list_apps()


@router.get("/builder/preview/{app_id}", response_class=HTMLResponse, summary="Preview app")
async def preview_app(app_id: str) -> str:
    """Get HTML preview of a built app."""
    spec = _builder.get_app(app_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")
    return _builder.preview(spec)


@router.post("/builder/deploy/{app_id}", response_model=Dict[str, str], summary="Deploy app")
async def deploy_app(app_id: str, request: DeployRequest) -> Dict[str, str]:
    """Deploy a built app to target environment."""
    spec = _builder.get_app(app_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")
    try:
        url = _builder.deploy(spec, request.target)
        return {"url": url, "target": request.target, "app_id": app_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/builder/iterate/{app_id}", response_model=Dict[str, Any], summary="Improve existing app")
async def iterate_app(app_id: str, request: IterateRequest) -> Dict[str, Any]:
    """
    Improve an existing app based on natural language feedback.

    Example feedback: "Add dark mode, improve the intake form, add Stripe payments"
    """
    try:
        result = _builder.iterate(app_id, request.feedback)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Template Endpoints
# ---------------------------------------------------------------------------

@router.get("/builder/templates", response_model=List[Dict[str, Any]], summary="List templates")
async def list_templates() -> List[Dict[str, Any]]:
    """List all available app templates."""
    return [
        {
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "app_type": t.app_type,
            "tags": t.tags,
        }
        for t in _library.list_templates()
    ]


@router.get("/builder/templates/{name}", response_model=Dict[str, Any], summary="Get template spec")
async def get_template(name: str) -> Dict[str, Any]:
    """Get the full spec for a named template."""
    try:
        spec = _library.get_template(name)
        return spec.to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/builder/templates/{name}/build", response_model=Dict[str, Any], summary="Build from template")
async def build_from_template(name: str, request: TemplateCustomizeRequest) -> Dict[str, Any]:
    """
    Build an app from a named template with optional customizations.

    Example:
    ```json
    {
        "overrides": {
            "name": "Smith & Associates",
            "styling": {"primary_color": "#1a4f2a"}
        }
    }
    ```
    """
    try:
        if request.overrides:
            spec = _library.customize_template(name, request.overrides)
        else:
            spec = _library.get_template(name)
        result = _builder.build(spec)
        return result.to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/builder/templates/{name}/preview", response_class=HTMLResponse, summary="Preview template")
async def preview_template(name: str) -> str:
    """Generate an HTML preview of a template."""
    try:
        spec = _library.get_template(name)
        return _builder.preview(spec)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Digital Twin Endpoints
# ---------------------------------------------------------------------------

@router.post("/twin/{user_id}", response_model=Dict[str, Any], summary="Create digital twin")
async def create_twin(user_id: str, request: CreateTwinRequest) -> Dict[str, Any]:
    """Create a new Digital Twin for a user."""
    _twin.create(user_id, request.name)
    return {"user_id": user_id, "name": request.name, "message": "Digital Twin created"}


@router.get("/twin/{user_id}", response_model=Dict[str, Any], summary="Get digital twin snapshot")
async def get_twin_snapshot(user_id: str) -> Dict[str, Any]:
    """
    Get a complete life snapshot from the Digital Twin.

    Returns all tracked life domains:
    - Legal matters
    - Financial profile (net worth, debts, credit)
    - Properties
    - Relationships
    - Health directives
    - Business interests
    - Digital assets
    """
    try:
        snapshot = _twin.life_snapshot(user_id)
        fp = snapshot.financial_profile
        return {
            "user_id": snapshot.user_id,
            "name": snapshot.name,
            "snapshot_date": snapshot.snapshot_date,
            "risk_score": snapshot.risk_score,
            "estate_readiness_score": snapshot.estate_readiness_score,
            "legal_matters_count": len(snapshot.legal_matters),
            "financial_profile": {
                "total_assets": fp.total_assets if fp else 0,
                "total_debts": fp.total_debts if fp else 0,
                "net_worth": fp.net_worth if fp else 0,
                "monthly_income": fp.monthly_income if fp else 0,
                "credit_score": fp.credit_score if fp else 0,
            },
            "properties_count": len(snapshot.properties),
            "relationships_count": len(snapshot.relationships),
            "health_directives_count": len(snapshot.health_directives),
            "business_interests_count": len(snapshot.business_interests),
            "digital_assets_count": len(snapshot.digital_assets),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/twin/{user_id}/event", response_model=Dict[str, str], summary="Update twin with life event")
async def update_twin(user_id: str, request: LifeEventRequest) -> Dict[str, str]:
    """
    Update a Digital Twin with a new life event.

    Event types: legal, financial, property, family, health, business, digital

    Example — adding a legal matter:
    ```json
    {
        "event_type": "legal",
        "title": "Estate Planning Initiated",
        "impact_level": "high",
        "data": {
            "legal_matter": {
                "matter_id": "M001",
                "title": "Thompson Family Trust",
                "matter_type": "trust",
                "status": "active",
                "jurisdiction": "New Jersey"
            }
        }
    }
    ```
    """
    import uuid as _uuid
    from datetime import datetime as _dt

    event = LifeEvent(
        event_id=request.event_id or str(_uuid.uuid4()),
        event_type=request.event_type,
        title=request.title,
        description=request.description,
        date=request.date or _dt.now().isoformat(),
        impact_level=request.impact_level,
        data=request.data,
    )
    try:
        _twin.update(user_id, event)
        return {"message": "Twin updated successfully", "event_id": event.event_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/twin/{user_id}/risks", response_model=Dict[str, Any], summary="Life risk assessment")
async def get_risk_assessment(user_id: str) -> Dict[str, Any]:
    """
    Get a comprehensive life risk assessment from the Digital Twin.

    Analyzes:
    - Debt-to-income ratio
    - Estate planning gaps
    - Missing legal directives
    - Digital asset vulnerabilities
    - Business risks
    - Active legal matter pressure
    """
    try:
        report = _twin.life_risk_assessment(user_id)
        return {
            "user_id": report.user_id,
            "overall_risk_score": report.overall_risk_score,
            "risk_level": report.risk_level,
            "vulnerabilities": report.vulnerabilities,
            "recommendations": report.recommendations,
            "critical_gaps": report.critical_gaps,
            "generated_at": report.generated_at,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/twin/{user_id}/estate", response_model=Dict[str, Any], summary="Estate readiness report")
async def get_estate_readiness(user_id: str) -> Dict[str, Any]:
    """
    Get estate readiness report — are you protected?

    Checks:
    - Last Will and Testament
    - Revocable Living Trust
    - Durable Power of Attorney
    - Healthcare Proxy / Living Will
    - Beneficiary designations
    - Document signing status
    """
    try:
        report = _twin.estate_readiness(user_id)
        return {
            "user_id": report.user_id,
            "readiness_score": report.readiness_score,
            "readiness_level": report.readiness_level,
            "has_will": report.has_will,
            "has_trust": report.has_trust,
            "has_poa": report.has_poa,
            "has_healthcare_directive": report.has_healthcare_directive,
            "beneficiaries_named": report.beneficiaries_named,
            "documents_signed": report.documents_signed,
            "missing_documents": report.missing_documents,
            "next_steps": report.next_steps,
            "generated_at": report.generated_at,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/twin/{user_id}/recommendations", response_model=List[Dict[str, Any]], summary="Governance recommendations")
async def get_recommendations(user_id: str) -> List[Dict[str, Any]]:
    """Get prioritized life governance recommendations."""
    try:
        recs = _twin.governance_recommendations(user_id)
        return [
            {
                "priority": r.priority,
                "category": r.category,
                "title": r.title,
                "description": r.description,
                "action_items": r.action_items,
                "estimated_cost": r.estimated_cost,
                "time_to_complete": r.time_to_complete,
            }
            for r in recs
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/twin/{user_id}/what-if", response_model=Dict[str, Any], summary="What-if scenario analysis")
async def what_if_scenario(user_id: str, scenario: str = Query(..., description="Scenario to analyze")) -> Dict[str, Any]:
    """
    Run a what-if scenario analysis.

    Examples:
    - "What if I start a business?"
    - "What if I get divorced?"
    - "What if I inherit $500,000?"
    - "What if I become disabled?"
    - "What if I move to Florida?"
    """
    try:
        analysis = _twin.what_if(user_id, scenario)
        return {
            "scenario": analysis.scenario,
            "current_state": analysis.current_state,
            "projected_state": analysis.projected_state,
            "risks": analysis.risks,
            "opportunities": analysis.opportunities,
            "recommended_actions": analysis.recommended_actions,
            "confidence_score": analysis.confidence_score,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/twin/{user_id}/portfolio", response_model=Dict[str, Any], summary="Export life portfolio")
async def export_portfolio(user_id: str) -> Dict[str, Any]:
    """
    Export a complete life portfolio — the full SintraPrime life document package.

    Includes:
    - Life snapshot
    - Risk assessment
    - Estate readiness report
    - Prioritized recommendations
    - Document manifest
    - Executive summary
    """
    try:
        portfolio = _twin.export_life_portfolio(user_id)
        return {
            "user_id": portfolio.user_id,
            "name": portfolio.name,
            "generated_at": portfolio.generated_at,
            "summary": portfolio.summary,
            "recommendations_count": len(portfolio.recommendations),
            "documents_manifest": portfolio.documents_manifest,
            "risk_level": portfolio.risk_report.risk_level if portfolio.risk_report else "unknown",
            "estate_readiness": portfolio.estate_report.readiness_level if portfolio.estate_report else "unknown",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/twin", response_model=List[Dict[str, str]], summary="List all digital twins")
async def list_twins() -> List[Dict[str, str]]:
    """List all known Digital Twins."""
    return _twin.list_twins()


@router.delete("/twin/{user_id}", response_model=Dict[str, str], summary="Delete digital twin")
async def delete_twin(user_id: str) -> Dict[str, str]:
    """Delete a Digital Twin and all associated data."""
    deleted = _twin.delete_twin(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Twin {user_id} not found")
    return {"message": f"Digital Twin for {user_id} deleted"}


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@router.get("/builder/health", response_model=Dict[str, str], summary="Health check")
async def health() -> Dict[str, str]:
    """App Builder health check."""
    return {
        "status": "ok",
        "service": "SintraPrime App Builder + Digital Twin",
        "version": "1.0.0",
        "templates_available": str(len(_library.TEMPLATES)),
    }
