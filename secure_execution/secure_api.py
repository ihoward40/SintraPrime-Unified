"""
secure_api.py — Secure FastAPI Router

Exposes a secured REST API for vault, attestation, zero-trust, and audit
operations.  Integrates DocumentVault, RemoteAttestationProtocol, and
ZeroTrustGateway.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover
    FASTAPI_AVAILABLE = False
    APIRouter = None  # type: ignore
    BaseModel = object  # type: ignore

from secure_execution.document_vault import DocumentVault, DocumentAccessLog, TemporaryTokenStore
from secure_execution.attestation import (
    RemoteAttestationProtocol,
    AttestationReport,
    AttestationType,
)
from secure_execution.zero_trust import (
    ZeroTrustGateway,
    PolicyDecision,
    PolicyRule,
    TrustLevel,
)
from secure_execution.tee_manager import SecureEnclaveContext, TEEProviderFactory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared service singletons (injected in production via DI)
# ---------------------------------------------------------------------------

_vault = DocumentVault()
_attestation = RemoteAttestationProtocol()
_gateway = ZeroTrustGateway()
_enclave = SecureEnclaveContext()

# Add a permissive default rule for demo purposes
_gateway.add_policy_rule(PolicyRule(
    description="Allow authenticated users with 'user' role",
    required_roles=["user"],
    decision=PolicyDecision.ALLOW,
    priority=10,
))
_gateway.add_policy_rule(PolicyRule(
    description="Allow admin role full access",
    required_roles=["admin"],
    decision=PolicyDecision.ALLOW,
    priority=5,
))


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

if FASTAPI_AVAILABLE:
    class StoreDocumentRequest(BaseModel):
        name: str = Field(..., description="Human-readable document name")
        owner: str = Field(..., description="Document owner identifier")
        password: str = Field(..., min_length=8, description="Master password for key derivation")
        content_b64: str = Field(..., description="Base64-encoded document bytes")
        content_type: str = Field("application/octet-stream")
        tags: List[str] = Field(default_factory=list)
        expires_in_seconds: Optional[float] = None

    class RetrieveDocumentRequest(BaseModel):
        doc_id: str
        password: str
        subject: str
        temp_token_id: Optional[str] = None

    class VerifyIdentityRequest(BaseModel):
        token: str
        resource: str
        action: str
        cert_thumbprint: Optional[str] = None

    class StoreDocumentResponse(BaseModel):
        doc_id: str
        message: str

    class RetrieveDocumentResponse(BaseModel):
        doc_id: str
        content_b64: str
        name: str
        content_type: str

    class AttestationReportResponse(BaseModel):
        enclave_id: str
        measurement: str
        timestamp: float
        attestation_type: str
        platform_id: str
        valid: bool

    class VerifyIdentityResponse(BaseModel):
        decision: str
        reason: str
        request_id: str

    class AuditLogResponse(BaseModel):
        entries: List[Dict[str, Any]]
        total: int


# ---------------------------------------------------------------------------
# Helper: extract Bearer token from Authorization header
# ---------------------------------------------------------------------------

def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format — expected: Bearer <token>",
        )
    return parts[1]


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------

def create_secure_router() -> "APIRouter":
    """Return a FastAPI APIRouter with all secure endpoints mounted."""

    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required: pip install fastapi")

    import base64

    router = APIRouter(prefix="/secure", tags=["Secure Execution"])

    # ------------------------------------------------------------------
    # POST /vault/store
    # ------------------------------------------------------------------

    @router.post(
        "/vault/store",
        response_model=StoreDocumentResponse,
        summary="Encrypt and store a document",
        status_code=201,
    )
    async def vault_store(
        req: StoreDocumentRequest,
        authorization: Optional[str] = Header(None),
    ):
        token = _extract_bearer(authorization)
        decision = _gateway.verify_request(token, "vault", "write")
        if decision.decision != PolicyDecision.ALLOW:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {decision.reason}",
            )

        try:
            raw_bytes = base64.b64decode(req.content_b64)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="content_b64 is not valid Base64",
            )

        expires_at = time.time() + req.expires_in_seconds if req.expires_in_seconds else None

        doc_id = _vault.store(
            plaintext=raw_bytes,
            name=req.name,
            owner=req.owner,
            password=req.password,
            content_type=req.content_type,
            tags=req.tags,
            expires_at=expires_at,
        )

        return StoreDocumentResponse(
            doc_id=doc_id,
            message="Document encrypted and stored successfully.",
        )

    # ------------------------------------------------------------------
    # POST /vault/retrieve
    # ------------------------------------------------------------------

    @router.post(
        "/vault/retrieve",
        response_model=RetrieveDocumentResponse,
        summary="Decrypt and retrieve a document",
    )
    async def vault_retrieve(
        req: RetrieveDocumentRequest,
        authorization: Optional[str] = Header(None),
    ):
        token = _extract_bearer(authorization)
        decision = _gateway.verify_request(token, "vault", "read")
        if decision.decision != PolicyDecision.ALLOW:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {decision.reason}",
            )

        try:
            plaintext = _vault.retrieve(
                doc_id=req.doc_id,
                password=req.password,
                subject=req.subject,
                temp_token_id=req.temp_token_id,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        meta = _vault.get_metadata(req.doc_id)

        return RetrieveDocumentResponse(
            doc_id=req.doc_id,
            content_b64=base64.b64encode(plaintext).decode(),
            name=meta.name if meta else req.doc_id,
            content_type=meta.content_type if meta else "application/octet-stream",
        )

    # ------------------------------------------------------------------
    # GET /attestation/report
    # ------------------------------------------------------------------

    @router.get(
        "/attestation/report",
        response_model=AttestationReportResponse,
        summary="Get current platform attestation report",
    )
    async def get_attestation_report():
        measurement = _enclave.platform_measurement
        caps = _enclave.capabilities
        report = _attestation.get_current_report(
            enclave_id=str(uuid.uuid4()),
            measurement=measurement,
            platform_id=caps.platform_id,
        )
        challenge = _attestation.issue_challenge()
        challenge_obj = list(_attestation._active_challenges.values())[-1]
        verification = _attestation.verify_response(challenge_obj, report, measurement)

        return AttestationReportResponse(
            enclave_id=report.enclave_id,
            measurement=report.measurement,
            timestamp=report.timestamp,
            attestation_type=report.attestation_type,
            platform_id=report.platform_id,
            valid=(verification.status.value == "valid"),
        )

    # ------------------------------------------------------------------
    # POST /zerotrust/verify
    # ------------------------------------------------------------------

    @router.post(
        "/zerotrust/verify",
        response_model=VerifyIdentityResponse,
        summary="Verify identity against zero-trust policy",
    )
    async def zerotrust_verify(req: VerifyIdentityRequest):
        decision = _gateway.verify_request(
            token=req.token,
            resource=req.resource,
            action=req.action,
            cert_thumbprint=req.cert_thumbprint,
        )
        return VerifyIdentityResponse(
            decision=decision.decision.value,
            reason=decision.reason,
            request_id=decision.request_id,
        )

    # ------------------------------------------------------------------
    # GET /audit/access-log
    # ------------------------------------------------------------------

    @router.get(
        "/audit/access-log",
        response_model=AuditLogResponse,
        summary="Get document access audit log",
    )
    async def get_audit_log(
        limit: int = 100,
        authorization: Optional[str] = Header(None),
    ):
        token = _extract_bearer(authorization)
        decision = _gateway.verify_request(token, "audit", "read")
        if decision.decision != PolicyDecision.ALLOW:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {decision.reason}",
            )

        from dataclasses import asdict
        entries = _vault.access_log.query(limit=limit)
        return AuditLogResponse(
            entries=[asdict(e) for e in entries],
            total=_vault.access_log.entry_count(),
        )

    # ------------------------------------------------------------------
    # Expose singletons for testing / DI
    # ------------------------------------------------------------------

    router.vault = _vault  # type: ignore
    router.gateway = _gateway  # type: ignore
    router.attestation = _attestation  # type: ignore

    return router
