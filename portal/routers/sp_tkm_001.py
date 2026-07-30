"""SP-TKM-001 consumer evidence landing page — internal preview only.

This router is intentionally lightweight and mission-isolated. It serves the
static marketing/lead-capture preview for the IKE Solutions Consumer Evidence line.
It does not connect to payment processors, does not accept payment, and is not
production-deployed during Phase Two.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field

router = APIRouter()

# Path to the mission-isolated landing-page HTML
LANDING_PAGE_PATH = Path(__file__).resolve().parent.parent.parent / "mission-control-evidence" / "SP-TKM-001" / "offers" / "consumer-evidence" / "landing-page" / "index.html"


class InterestForm(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    topic: str = Field(default="", max_length=50)
    utm_source: str = Field(default="", max_length=100)
    utm_medium: str = Field(default="", max_length=100)
    utm_campaign: str = Field(default="", max_length=100)
    utm_content: str = Field(default="", max_length=100)


class AnalyticsEvent(BaseModel):
    event_name: str = Field(..., pattern=r"^[a-z_]{1,64}$")
    utm_source: str = Field(default="", max_length=100)
    utm_medium: str = Field(default="", max_length=100)
    utm_campaign: str = Field(default="", max_length=100)
    utm_content: str = Field(default="", max_length=100)
    url: str = Field(default="", max_length=2048)
    referrer: str = Field(default="", max_length=2048)


@router.get("/consumer-evidence", response_class=HTMLResponse)
async def consumer_evidence_page():
    """Serve the internal non-production landing page preview."""
    if not LANDING_PAGE_PATH.exists():
        return HTMLResponse(content="<h1>Landing page not found</h1>", status_code=404)
    return HTMLResponse(content=LANDING_PAGE_PATH.read_text(encoding="utf-8"))


@router.post("/api/v1/consumer-evidence/interest")
async def capture_interest(payload: InterestForm):
    """Placeholder lead-capture endpoint. No payment. No PII beyond name/email/topic."""
    # Phase Two: log or store lead record with UTM attribution.
    return JSONResponse({
        "status": "ok",
        "message": "Interest captured. Starter Sheet delivery email to be implemented.",
        "email": payload.email,
        "topic": payload.topic,
        "utm": {
            "source": payload.utm_source,
            "medium": payload.utm_medium,
            "campaign": payload.utm_campaign,
            "content": payload.utm_content,
        }
    })


@router.post("/api/v1/consumer-evidence/event")
async def capture_event(payload: AnalyticsEvent):
    """Placeholder analytics-event endpoint. No sensitive document or identifier capture."""
    # Phase Two: forward to analytics store.
    return JSONResponse({"status": "ok", "event": payload.event_name})
