"""
Legal Integrations FastAPI Router for SintraPrime-Unified.

Endpoints:
  POST /integrations/dms/connect       — connect to a DMS platform
  POST /integrations/dms/upload        — upload a document
  POST /integrations/court/file        — e-file a document
  GET  /integrations/court/status/{id} — filing status
  POST /integrations/research/search   — search all legal research sources
  GET  /integrations/financial/assets  — get asset report

Mount with:
    from legal_integrations.integrations_api import router
    app.include_router(router, prefix="/integrations", tags=["legal"])
"""

from __future__ import annotations

import io
import logging
import os
from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
except ImportError as exc:
    raise ImportError("Install fastapi and pydantic: pip install fastapi pydantic") from exc

from .court_efiling import (
    FilingDocument,
    FilingRequest,
    FilingStatus,
    calculate_filing_fee,
    get_efiling_system,
)
from .dms_connectors import get_dms_connector
from .financial_connectors import EDGARConnector, PlaidConnector
from .legal_research import UnifiedSearchResult, build_unified_search, validate_citation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Legal Integrations"])

# In-memory connector cache (keyed by platform name).
# In production, replace with a proper per-request auth flow.
_DMS_CONNECTORS: Dict[str, Any] = {}
_EFILING_SYSTEMS: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class DMSConnectRequest(BaseModel):
    platform: str = Field(..., description="DMS platform: netdocuments|imanage|worldox|clio|mycase|practicepanther")
    options: Dict[str, str] = Field(default_factory=dict, description="Extra options (injected as env vars)")


class DMSConnectResponse(BaseModel):
    platform: str
    connected: bool
    message: str


class DMSUploadResponse(BaseModel):
    doc_id: str
    name: str
    matter_id: Optional[str]
    platform: str


class CourtFileRequest(BaseModel):
    system: str = Field(..., description="E-filing system: pacer|tyler|file_serve_xpress|odyssey")
    case_number: str
    court_id: str
    filing_type: str
    filer_name: Optional[str] = None
    filer_bar_number: Optional[str] = None


class CourtFileResponse(BaseModel):
    filing_id: str
    case_number: str
    status: str
    confirmation_number: Optional[str]
    fee_charged: float
    documents_accepted: List[str]


class FilingStatusResponse(BaseModel):
    filing_id: str
    status: str
    message: Optional[str]


class ResearchSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    jurisdiction: Optional[str] = None
    sources: Optional[List[str]] = None
    limit_per_source: int = Field(default=10, ge=1, le=100)


class ResearchSearchResponse(BaseModel):
    query: str
    total_found: int
    results: List[Dict[str, Any]]
    errors: Dict[str, str]


class AssetReportResponse(BaseModel):
    report_id: str
    total_assets: float
    total_liabilities: float
    net_worth: float
    account_count: int


class CitationValidateRequest(BaseModel):
    citation: str


class CitationValidateResponse(BaseModel):
    citation: str
    is_valid: bool
    parsed: Dict[str, Any]


# ---------------------------------------------------------------------------
# DMS endpoints
# ---------------------------------------------------------------------------


@router.post("/dms/connect", response_model=DMSConnectResponse, status_code=status.HTTP_200_OK)
async def dms_connect(req: DMSConnectRequest) -> DMSConnectResponse:
    """Connect to a Document Management System."""
    # Inject any extra options as temporary env vars for this request
    for key, value in req.options.items():
        os.environ.setdefault(key, value)
    try:
        connector = get_dms_connector(req.platform)
        _DMS_CONNECTORS[req.platform] = connector
        return DMSConnectResponse(
            platform=req.platform,
            connected=True,
            message=f"Successfully connected to {req.platform}",
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to {req.platform}: {exc}",
        ) from exc


@router.post("/dms/upload", response_model=DMSUploadResponse, status_code=status.HTTP_201_CREATED)
async def dms_upload(
    platform: str = Form(...),
    matter_id: str = Form(...),
    file: UploadFile = File(...),
) -> DMSUploadResponse:
    """Upload a document to a connected DMS."""
    connector = _DMS_CONNECTORS.get(platform)
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not connected to '{platform}'. Call /dms/connect first.",
        )
    content = await file.read()
    try:
        doc = connector.upload_document(
            matter_id=matter_id,
            filename=file.filename or "document",
            content=io.BytesIO(content),
            content_type=file.content_type or "application/octet-stream",
        )
        return DMSUploadResponse(
            doc_id=doc.doc_id,
            name=doc.name,
            matter_id=doc.matter_id,
            platform=platform,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upload failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Court e-filing endpoints
# ---------------------------------------------------------------------------


@router.post("/court/file", response_model=CourtFileResponse, status_code=status.HTTP_201_CREATED)
async def court_file(
    system: str = Form(...),
    case_number: str = Form(...),
    court_id: str = Form(...),
    filing_type: str = Form(...),
    filer_name: Optional[str] = Form(None),
    filer_bar_number: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
) -> CourtFileResponse:
    """E-file documents with a court filing system."""
    # Build filing documents
    filing_docs: List[FilingDocument] = []
    for f in files:
        content = await f.read()
        filing_docs.append(
            FilingDocument(
                filename=f.filename or "document.pdf",
                content=content,
                content_type=f.content_type or "application/pdf",
            )
        )

    filing_request = FilingRequest(
        case_number=case_number,
        court_id=court_id,
        filing_type=filing_type,
        documents=filing_docs,
        filer_name=filer_name,
        filer_bar_number=filer_bar_number,
    )

    try:
        efiling = _EFILING_SYSTEMS.get(system)
        if efiling is None:
            efiling = get_efiling_system(system)
            _EFILING_SYSTEMS[system] = efiling
        confirmation = efiling.file_document(filing_request)
        return CourtFileResponse(
            filing_id=confirmation.filing_id,
            case_number=confirmation.case_number,
            status=confirmation.status.value,
            confirmation_number=confirmation.confirmation_number,
            fee_charged=confirmation.fee_charged,
            documents_accepted=confirmation.documents_accepted,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Filing failed: {exc}"
        ) from exc


@router.get("/court/status/{filing_id}", response_model=FilingStatusResponse)
async def court_status(filing_id: str, system: str = "pacer") -> FilingStatusResponse:
    """Check the status of a court filing."""
    efiling = _EFILING_SYSTEMS.get(system)
    if efiling is None:
        try:
            efiling = get_efiling_system(system)
            _EFILING_SYSTEMS[system] = efiling
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        result = efiling.check_filing_status(filing_id)
        return FilingStatusResponse(
            filing_id=result.filing_id,
            status=result.status.value,
            message=result.message,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Status check failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Legal research endpoint
# ---------------------------------------------------------------------------


@router.post("/research/search", response_model=ResearchSearchResponse)
async def research_search(req: ResearchSearchRequest) -> ResearchSearchResponse:
    """Search all available legal research sources simultaneously."""
    try:
        unified = build_unified_search(sources=req.sources)
        result: UnifiedSearchResult = unified.search(
            query=req.query,
            jurisdiction=req.jurisdiction,
            limit_per_source=req.limit_per_source,
        )
        return ResearchSearchResponse(
            query=result.query,
            total_found=result.total_found,
            results=[
                {
                    "source": r.source,
                    "result_id": r.result_id,
                    "title": r.title,
                    "citation": r.citation,
                    "court": r.court,
                    "date": r.date,
                    "snippet": r.snippet,
                    "url": r.url,
                    "score": r.score,
                }
                for r in result.results
            ],
            errors=result.errors,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Research search failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Financial endpoints
# ---------------------------------------------------------------------------


@router.get("/financial/assets", response_model=AssetReportResponse)
async def financial_assets(
    access_token: str,
    days_requested: int = 730,
) -> AssetReportResponse:
    """Generate and retrieve a Plaid asset report."""
    try:
        plaid = PlaidConnector()
        report_token = plaid.create_asset_report([access_token], days_requested=days_requested)
        report = plaid.get_asset_report(report_token)
        return AssetReportResponse(
            report_id=report.report_id,
            total_assets=report.total_assets,
            total_liabilities=report.total_liabilities,
            net_worth=report.net_worth,
            account_count=len(report.accounts),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing Plaid credentials: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Asset report failed: {exc}"
        ) from exc


@router.get("/financial/edgar/filings")
async def edgar_filings(
    company_name: Optional[str] = None,
    cik: Optional[str] = None,
    form_type: str = "10-K",
    limit: int = 10,
) -> JSONResponse:
    """Search SEC EDGAR filings."""
    if not company_name and not cik:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide company_name or cik",
        )
    edgar = EDGARConnector()
    try:
        filings = edgar.search_filings(
            company_name=company_name,
            cik=cik,
            form_type=form_type,
            limit=limit,
        )
        return JSONResponse(
            content={
                "count": len(filings),
                "filings": [
                    {
                        "accession_number": f.accession_number,
                        "company_name": f.company_name,
                        "cik": f.cik,
                        "form_type": f.form_type,
                        "filed_date": f.filed_date,
                        "filing_url": f.filing_url,
                    }
                    for f in filings
                ],
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"EDGAR search failed: {exc}"
        ) from exc


@router.post("/research/cite/validate", response_model=CitationValidateResponse)
async def validate_legal_citation(req: CitationValidateRequest) -> CitationValidateResponse:
    """Validate and parse a legal citation string."""
    is_valid, parsed = validate_citation(req.citation)
    return CitationValidateResponse(
        citation=req.citation,
        is_valid=is_valid,
        parsed={
            "volume": parsed.volume,
            "reporter": parsed.reporter,
            "page": parsed.page,
            "year": parsed.year,
            "court": parsed.court,
        },
    )
