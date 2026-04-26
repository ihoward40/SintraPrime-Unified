"""
Court E-Filing System Connectors for SintraPrime-Unified.

Supports:
  - PACER (federal courts) — extended with filing capabilities
  - Tyler Technologies (most common state e-filing)
  - File & Serve Xpress (CA, TX, etc.)
  - Odyssey eFile (IL, OH, etc.)

All credentials from environment variables only.
"""

from __future__ import annotations

import abc
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60  # seconds — court APIs can be slow


# ---------------------------------------------------------------------------
# Retry session
# ---------------------------------------------------------------------------


def _build_session(retries: int = 3) -> requests.Session:
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ---------------------------------------------------------------------------
# Enums & data models
# ---------------------------------------------------------------------------


class FilingStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PROCESSING = "processing"
    RETURNED = "returned"
    UNKNOWN = "unknown"


class DocumentFormat(str, Enum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    TXT = "text/plain"
    XML = "application/xml"
    TIFF = "image/tiff"


ACCEPTED_FILING_FORMATS = {DocumentFormat.PDF, DocumentFormat.DOCX, DocumentFormat.TXT, DocumentFormat.XML}

# Court fee schedule (simplified — real fees vary by court and document type)
FEE_SCHEDULE: Dict[str, float] = {
    "civil_complaint": 402.00,
    "civil_motion": 0.00,
    "bankruptcy_petition": 338.00,
    "criminal_notice": 0.00,
    "appeal": 505.00,
    "default": 50.00,
}


@dataclass
class FilingDocument:
    """Document to be e-filed."""

    filename: str
    content: bytes
    content_type: str = DocumentFormat.PDF
    document_type: str = "pleading"
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FilingRequest:
    """A complete e-filing request."""

    case_number: str
    court_id: str
    filing_type: str
    documents: List[FilingDocument] = field(default_factory=list)
    filer_name: Optional[str] = None
    filer_bar_number: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FilingConfirmation:
    """Confirmation returned after successful submission."""

    filing_id: str
    case_number: str
    status: FilingStatus
    confirmation_number: Optional[str] = None
    timestamp: Optional[datetime] = None
    fee_charged: float = 0.0
    documents_accepted: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FilingStatusResult:
    """Status of a previously submitted filing."""

    filing_id: str
    status: FilingStatus
    message: Optional[str] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AcceptedDocument:
    """A document type accepted by a given court."""

    code: str
    description: str
    formats: List[str] = field(default_factory=list)
    fee: float = 0.0


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_document_format(doc: FilingDocument) -> None:
    """Raise ValueError if *doc* has an unsupported content type."""
    if doc.content_type not in {f.value for f in ACCEPTED_FILING_FORMATS}:
        raise ValueError(
            f"Unsupported content type '{doc.content_type}'. "
            f"Accepted: {[f.value for f in ACCEPTED_FILING_FORMATS]}"
        )
    if not doc.content:
        raise ValueError(f"Document '{doc.filename}' has no content.")
    if doc.content_type == DocumentFormat.PDF and not doc.content.startswith(b"%PDF"):
        raise ValueError(f"Document '{doc.filename}' does not appear to be a valid PDF.")


def validate_filing_request(request: FilingRequest) -> List[str]:
    """Return a list of validation error messages (empty = valid)."""
    errors: List[str] = []
    if not request.case_number:
        errors.append("case_number is required")
    if not request.court_id:
        errors.append("court_id is required")
    if not request.documents:
        errors.append("At least one document is required")
    for doc in request.documents:
        try:
            validate_document_format(doc)
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def calculate_filing_fee(filing_type: str, document_count: int = 1) -> float:
    """Estimate filing fee based on filing type and document count."""
    base_fee = FEE_SCHEDULE.get(filing_type, FEE_SCHEDULE["default"])
    per_doc_fee = 0.50 * max(0, document_count - 1)
    return round(base_fee + per_doc_fee, 2)


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class EFilingSystem(abc.ABC):
    """Abstract base class for all e-filing system connectors."""

    name: str = "base"

    def __init__(self) -> None:
        self._session = _build_session()

    @abc.abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the e-filing system."""

    @abc.abstractmethod
    def file_document(self, request: FilingRequest) -> FilingConfirmation:
        """Submit a filing and return the confirmation."""

    @abc.abstractmethod
    def check_filing_status(self, filing_id: str) -> FilingStatusResult:
        """Check the status of a previously submitted filing."""

    @abc.abstractmethod
    def get_confirmation(self, filing_id: str) -> FilingConfirmation:
        """Retrieve the full confirmation for a filing."""

    @abc.abstractmethod
    def list_accepted_docs(self, court_id: str) -> List[AcceptedDocument]:
        """Return the list of document types accepted by *court_id*."""

    # ------------------------------------------------------------------
    # Shared utilities
    # ------------------------------------------------------------------

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self._session.get(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def _post(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self._session.post(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def _pre_validate(self, request: FilingRequest) -> None:
        """Validate request and raise ValueError with all issues if invalid."""
        errors = validate_filing_request(request)
        if errors:
            raise ValueError("Filing validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


# ---------------------------------------------------------------------------
# PACER (extended with filing)
# ---------------------------------------------------------------------------


class PACERFilingConnector(EFilingSystem):
    """
    PACER (Public Access to Court Electronic Records) — federal filing.

    Env vars:
        PACER_USERNAME
        PACER_PASSWORD
        PACER_CLIENT_CODE
        PACER_BASE_URL  (default https://ecf.uscourts.gov)
    """

    name = "pacer"
    _AUTH_URL = "https://pacer.login.uscourts.gov/services/cso-auth"

    def __init__(self) -> None:
        super().__init__()
        self._username = os.environ["PACER_USERNAME"]
        self._password = os.environ["PACER_PASSWORD"]
        self._client_code = os.getenv("PACER_CLIENT_CODE", "")
        self._base_url = os.getenv("PACER_BASE_URL", "https://ecf.uscourts.gov")
        self._token: Optional[str] = None

    def authenticate(self) -> None:
        resp = self._session.post(
            self._AUTH_URL,
            json={
                "loginId": self._username,
                "password": self._password,
                "clientCode": self._client_code,
                "redactFlag": "1",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        self._token = resp.json().get("nextGenCSO") or resp.headers.get("X-NEXT-GEN-CSO")
        self._session.headers.update({"X-NEXT-GEN-CSO": self._token, "Content-Type": "application/json"})
        logger.info("PACER: authenticated successfully")

    def file_document(self, request: FilingRequest) -> FilingConfirmation:
        self._pre_validate(request)
        fee = calculate_filing_fee(request.filing_type, len(request.documents))
        url = f"{self._base_url}/api/v1/cases/{request.case_number}/filings"
        files_payload = [
            ("documents", (doc.filename, doc.content, doc.content_type)) for doc in request.documents
        ]
        data = {
            "courtId": request.court_id,
            "filingType": request.filing_type,
            "filerName": request.filer_name or "",
            "barNumber": request.filer_bar_number or "",
        }
        resp = self._post(url, data=data, files=files_payload)
        result = resp.json()
        return FilingConfirmation(
            filing_id=result.get("filingId", ""),
            case_number=request.case_number,
            status=FilingStatus(result.get("status", FilingStatus.PENDING)),
            confirmation_number=result.get("confirmationNumber"),
            timestamp=datetime.utcnow(),
            fee_charged=fee,
            documents_accepted=[d.filename for d in request.documents],
            metadata=result,
        )

    def check_filing_status(self, filing_id: str) -> FilingStatusResult:
        url = f"{self._base_url}/api/v1/filings/{filing_id}/status"
        resp = self._get(url)
        data = resp.json()
        return FilingStatusResult(
            filing_id=filing_id,
            status=FilingStatus(data.get("status", FilingStatus.UNKNOWN)),
            message=data.get("message"),
            updated_at=datetime.utcnow(),
            metadata=data,
        )

    def get_confirmation(self, filing_id: str) -> FilingConfirmation:
        url = f"{self._base_url}/api/v1/filings/{filing_id}"
        resp = self._get(url)
        data = resp.json()
        return FilingConfirmation(
            filing_id=filing_id,
            case_number=data.get("caseNumber", ""),
            status=FilingStatus(data.get("status", FilingStatus.UNKNOWN)),
            confirmation_number=data.get("confirmationNumber"),
            fee_charged=float(data.get("fee", 0)),
            documents_accepted=data.get("documentsAccepted", []),
            metadata=data,
        )

    def list_accepted_docs(self, court_id: str) -> List[AcceptedDocument]:
        url = f"{self._base_url}/api/v1/courts/{court_id}/accepted-documents"
        resp = self._get(url)
        return [
            AcceptedDocument(
                code=item.get("code", ""),
                description=item.get("description", ""),
                formats=item.get("formats", ["application/pdf"]),
                fee=float(item.get("fee", 0)),
            )
            for item in resp.json().get("documents", [])
        ]


# ---------------------------------------------------------------------------
# Tyler Technologies
# ---------------------------------------------------------------------------


class TylerTechConnector(EFilingSystem):
    """
    Tyler Technologies e-filing (state courts).

    Env vars:
        TYLER_CLIENT_TOKEN
        TYLER_SERVER_URL        (jurisdiction-specific)
        TYLER_FIRM_ID
    """

    name = "tyler"

    def __init__(self) -> None:
        super().__init__()
        self._client_token = os.environ["TYLER_CLIENT_TOKEN"]
        self._server_url = os.environ["TYLER_SERVER_URL"].rstrip("/")
        self._firm_id = os.environ["TYLER_FIRM_ID"]

    def authenticate(self) -> None:
        self._session.headers.update(
            {
                "ClientToken": self._client_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        logger.info("Tyler Technologies: client token configured")

    def file_document(self, request: FilingRequest) -> FilingConfirmation:
        self._pre_validate(request)
        fee = calculate_filing_fee(request.filing_type, len(request.documents))
        # Tyler uses a multi-step submission: create envelope → attach docs → submit
        envelope_id = self._create_envelope(request)
        for doc in request.documents:
            self._attach_document(envelope_id, doc)
        result = self._submit_envelope(envelope_id)
        return FilingConfirmation(
            filing_id=envelope_id,
            case_number=request.case_number,
            status=FilingStatus(result.get("status", FilingStatus.PENDING)),
            confirmation_number=result.get("confirmationNumber"),
            timestamp=datetime.utcnow(),
            fee_charged=fee,
            documents_accepted=[d.filename for d in request.documents],
            metadata=result,
        )

    def _create_envelope(self, request: FilingRequest) -> str:
        url = f"{self._server_url}/EfmFirmService/efile/firm/{self._firm_id}/filing"
        payload = {
            "CaseNumber": request.case_number,
            "CourtID": request.court_id,
            "FilingType": request.filing_type,
        }
        resp = self._post(url, json=payload)
        return resp.json().get("EnvelopeID", "")

    def _attach_document(self, envelope_id: str, doc: FilingDocument) -> None:
        url = f"{self._server_url}/EfmFirmService/efile/firm/{self._firm_id}/filing/{envelope_id}/document"
        self._post(
            url,
            files={"file": (doc.filename, doc.content, doc.content_type)},
            data={"DocumentType": doc.document_type, "Description": doc.description or ""},
        )

    def _submit_envelope(self, envelope_id: str) -> Dict[str, Any]:
        url = f"{self._server_url}/EfmFirmService/efile/firm/{self._firm_id}/filing/{envelope_id}/submit"
        resp = self._post(url)
        return resp.json()

    def check_filing_status(self, filing_id: str) -> FilingStatusResult:
        url = f"{self._server_url}/EfmFirmService/efile/firm/{self._firm_id}/filing/{filing_id}/status"
        resp = self._get(url)
        data = resp.json()
        return FilingStatusResult(
            filing_id=filing_id,
            status=FilingStatus(data.get("FilingStatus", FilingStatus.UNKNOWN).lower()),
            message=data.get("StatusDescription"),
            updated_at=datetime.utcnow(),
            metadata=data,
        )

    def get_confirmation(self, filing_id: str) -> FilingConfirmation:
        url = f"{self._server_url}/EfmFirmService/efile/firm/{self._firm_id}/filing/{filing_id}"
        resp = self._get(url)
        data = resp.json()
        return FilingConfirmation(
            filing_id=filing_id,
            case_number=data.get("CaseNumber", ""),
            status=FilingStatus(data.get("FilingStatus", FilingStatus.UNKNOWN).lower()),
            confirmation_number=data.get("ConfirmationNumber"),
            fee_charged=float(data.get("FilingFee", 0)),
            documents_accepted=data.get("AcceptedDocuments", []),
            metadata=data,
        )

    def list_accepted_docs(self, court_id: str) -> List[AcceptedDocument]:
        url = f"{self._server_url}/EfmFirmService/efile/codes/court/{court_id}/filingcodes"
        resp = self._get(url)
        return [
            AcceptedDocument(
                code=item.get("EFMFilingCode", ""),
                description=item.get("Name", ""),
                formats=["application/pdf"],
                fee=float(item.get("Fee", 0)),
            )
            for item in resp.json().get("FilingCode", [])
        ]


# ---------------------------------------------------------------------------
# File & Serve Xpress
# ---------------------------------------------------------------------------


class FileServeXpressConnector(EFilingSystem):
    """
    File & Serve Xpress (California, Texas, etc.).

    Env vars:
        FSX_USERNAME
        FSX_PASSWORD
        FSX_BASE_URL  (default https://efile.fileandservexpress.com)
    """

    name = "file_serve_xpress"

    def __init__(self) -> None:
        super().__init__()
        self._username = os.environ["FSX_USERNAME"]
        self._password = os.environ["FSX_PASSWORD"]
        self._base_url = os.getenv("FSX_BASE_URL", "https://efile.fileandservexpress.com")
        self._session_token: Optional[str] = None

    def authenticate(self) -> None:
        resp = self._session.post(
            f"{self._base_url}/api/login",
            json={"username": self._username, "password": self._password},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        self._session_token = resp.json().get("authToken")
        self._session.headers.update(
            {"Authorization": f"Bearer {self._session_token}", "Accept": "application/json"}
        )
        logger.info("File & Serve Xpress: authenticated successfully")

    def file_document(self, request: FilingRequest) -> FilingConfirmation:
        self._pre_validate(request)
        fee = calculate_filing_fee(request.filing_type, len(request.documents))
        url = f"{self._base_url}/api/filing/submit"
        files_list = [
            ("files", (doc.filename, doc.content, doc.content_type)) for doc in request.documents
        ]
        data = {
            "caseNumber": request.case_number,
            "courtCode": request.court_id,
            "filingType": request.filing_type,
            "filerName": request.filer_name or "",
        }
        resp = self._post(url, data=data, files=files_list)
        result = resp.json()
        return FilingConfirmation(
            filing_id=result.get("filingId", ""),
            case_number=request.case_number,
            status=FilingStatus(result.get("status", FilingStatus.PENDING).lower()),
            confirmation_number=result.get("transactionId"),
            timestamp=datetime.utcnow(),
            fee_charged=fee,
            documents_accepted=[d.filename for d in request.documents],
            metadata=result,
        )

    def check_filing_status(self, filing_id: str) -> FilingStatusResult:
        url = f"{self._base_url}/api/filing/{filing_id}/status"
        resp = self._get(url)
        data = resp.json()
        return FilingStatusResult(
            filing_id=filing_id,
            status=FilingStatus(data.get("status", FilingStatus.UNKNOWN).lower()),
            message=data.get("message"),
            updated_at=datetime.utcnow(),
            metadata=data,
        )

    def get_confirmation(self, filing_id: str) -> FilingConfirmation:
        url = f"{self._base_url}/api/filing/{filing_id}"
        resp = self._get(url)
        data = resp.json()
        return FilingConfirmation(
            filing_id=filing_id,
            case_number=data.get("caseNumber", ""),
            status=FilingStatus(data.get("status", FilingStatus.UNKNOWN).lower()),
            confirmation_number=data.get("transactionId"),
            fee_charged=float(data.get("fee", 0)),
            documents_accepted=data.get("acceptedDocuments", []),
            metadata=data,
        )

    def list_accepted_docs(self, court_id: str) -> List[AcceptedDocument]:
        url = f"{self._base_url}/api/courts/{court_id}/documenttypes"
        resp = self._get(url)
        return [
            AcceptedDocument(
                code=item.get("code", ""),
                description=item.get("description", ""),
                formats=item.get("formats", ["application/pdf"]),
                fee=float(item.get("fee", 0)),
            )
            for item in resp.json().get("documentTypes", [])
        ]


# ---------------------------------------------------------------------------
# Odyssey eFile
# ---------------------------------------------------------------------------


class OdysseyEFileConnector(EFilingSystem):
    """
    Odyssey eFile (Illinois, Ohio, etc.).

    Env vars:
        ODYSSEY_API_KEY
        ODYSSEY_BASE_URL    (state-specific, e.g. https://il.tylertech.cloud)
        ODYSSEY_JURISDICTION
    """

    name = "odyssey_efile"

    def __init__(self) -> None:
        super().__init__()
        self._api_key = os.environ["ODYSSEY_API_KEY"]
        self._base_url = os.environ["ODYSSEY_BASE_URL"].rstrip("/")
        self._jurisdiction = os.environ["ODYSSEY_JURISDICTION"]

    def authenticate(self) -> None:
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._api_key}",
                "X-Jurisdiction": self._jurisdiction,
                "Accept": "application/json",
            }
        )
        logger.info("Odyssey eFile: API key configured")

    def file_document(self, request: FilingRequest) -> FilingConfirmation:
        self._pre_validate(request)
        fee = calculate_filing_fee(request.filing_type, len(request.documents))
        url = f"{self._base_url}/efile/api/submission"
        files_list = [
            ("documents", (doc.filename, doc.content, doc.content_type)) for doc in request.documents
        ]
        data = {
            "caseNumber": request.case_number,
            "courtId": request.court_id,
            "filingType": request.filing_type,
            "jurisdiction": self._jurisdiction,
        }
        resp = self._post(url, data=data, files=files_list)
        result = resp.json()
        return FilingConfirmation(
            filing_id=result.get("submissionId", ""),
            case_number=request.case_number,
            status=FilingStatus(result.get("status", FilingStatus.PENDING).lower()),
            confirmation_number=result.get("confirmationCode"),
            timestamp=datetime.utcnow(),
            fee_charged=fee,
            documents_accepted=[d.filename for d in request.documents],
            metadata=result,
        )

    def check_filing_status(self, filing_id: str) -> FilingStatusResult:
        url = f"{self._base_url}/efile/api/submission/{filing_id}"
        resp = self._get(url)
        data = resp.json()
        return FilingStatusResult(
            filing_id=filing_id,
            status=FilingStatus(data.get("status", FilingStatus.UNKNOWN).lower()),
            message=data.get("statusMessage"),
            updated_at=datetime.utcnow(),
            metadata=data,
        )

    def get_confirmation(self, filing_id: str) -> FilingConfirmation:
        url = f"{self._base_url}/efile/api/submission/{filing_id}/confirmation"
        resp = self._get(url)
        data = resp.json()
        return FilingConfirmation(
            filing_id=filing_id,
            case_number=data.get("caseNumber", ""),
            status=FilingStatus(data.get("status", FilingStatus.UNKNOWN).lower()),
            confirmation_number=data.get("confirmationCode"),
            fee_charged=float(data.get("fee", 0)),
            documents_accepted=data.get("acceptedDocuments", []),
            metadata=data,
        )

    def list_accepted_docs(self, court_id: str) -> List[AcceptedDocument]:
        url = f"{self._base_url}/efile/api/courts/{court_id}/filingcodes"
        resp = self._get(url)
        return [
            AcceptedDocument(
                code=item.get("code", ""),
                description=item.get("description", ""),
                formats=["application/pdf"],
                fee=float(item.get("fee", 0)),
            )
            for item in resp.json().get("codes", [])
        ]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_EFILING_REGISTRY: Dict[str, type] = {
    "pacer": PACERFilingConnector,
    "tyler": TylerTechConnector,
    "file_serve_xpress": FileServeXpressConnector,
    "odyssey": OdysseyEFileConnector,
}


def get_efiling_system(system: str) -> EFilingSystem:
    """
    Factory — return an authenticated EFilingSystem for *system*.

    Args:
        system: One of 'pacer', 'tyler', 'file_serve_xpress', 'odyssey'.

    Returns:
        Authenticated EFilingSystem instance.
    """
    cls = _EFILING_REGISTRY.get(system.lower())
    if cls is None:
        raise ValueError(f"Unknown e-filing system: {system!r}. Choices: {list(_EFILING_REGISTRY)}")
    connector: EFilingSystem = cls()
    connector.authenticate()
    return connector
