"""Controlled JSON and PDF exports for persistent matter intelligence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..schemas.matter_export import MatterExportRequest
from ..services.matter_export_service import MatterExportError, MatterExportService

router = APIRouter(prefix="/api/v1/matters", tags=["matter-exports"])
service = MatterExportService()


@router.post("/{matter_id}/exports")
async def export_matter_packet(
    matter_id: str,
    body: MatterExportRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_EXPORT)),
    db: AsyncSession = Depends(get_db),
):
    """Return a redacted, hash-addressed matter packet in JSON or PDF form."""
    try:
        result = await service.build_packet(
            db,
            matter_id=matter_id,
            tenant_id=current_user.tenant_id,
            actor_id=current_user.user_id,
            actor_role=current_user.role.value,
            export_format=body.format,
        )
    except MatterExportError as exc:
        status_code = 404 if str(exc) == "matter not found" else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    media_type = "application/json" if result.format == "JSON" else "application/pdf"
    suffix = "json" if result.format == "JSON" else "pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="matter-{matter_id}-export.{suffix}"',
        "X-Matter-Export-Id": result.export_id,
        "X-Matter-Packet-Hash": result.packet_hash,
        "X-Matter-Manifest-Hash": result.redacted_manifest_hash,
        "X-Matter-Audit-Event-Id": result.audit_event_id,
    }
    return Response(content=result.content, media_type=media_type, headers=headers)
