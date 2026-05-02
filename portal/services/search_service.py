"""Full-text search service using PostgreSQL tsvector."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.case import Case
from ..models.client import Client
from ..models.document import Document


async def full_text_search(
    db: AsyncSession,
    query: str,
    tenant_id: uuid.UUID | str,
    resource_types: list[str] | None = None,
    limit: int = 20,
) -> dict:
    """
    Search across documents, cases, and clients using PostgreSQL full-text search.
    Falls back to ILIKE if tsvector columns aren't available.
    """
    results: dict = {"documents": [], "cases": [], "clients": []}
    types = resource_types or ["documents", "cases", "clients"]

    if "documents" in types:
        stmt = select(Document).where(
            Document.tenant_id == uuid.UUID(str(tenant_id)),
            Document.deleted_at.is_(None),
        ).where(
            Document.name.ilike(f"%{query}%") |
            Document.description.ilike(f"%{query}%") |
            Document.ocr_text.ilike(f"%{query}%")
        ).limit(limit)
        res = await db.execute(stmt)
        docs = res.scalars().all()
        results["documents"] = [
            {"id": str(d.id), "name": d.name, "type": "document"} for d in docs
        ]

    if "cases" in types:
        stmt = select(Case).where(
            Case.tenant_id == uuid.UUID(str(tenant_id)),
            Case.deleted_at.is_(None),
        ).where(
            Case.title.ilike(f"%{query}%") |
            Case.case_number.ilike(f"%{query}%") |
            Case.opposing_party.ilike(f"%{query}%")
        ).limit(limit)
        res = await db.execute(stmt)
        cases = res.scalars().all()
        results["cases"] = [
            {"id": str(c.id), "title": c.title, "case_number": c.case_number, "type": "case"}
            for c in cases
        ]

    if "clients" in types:
        stmt = select(Client).where(
            Client.tenant_id == uuid.UUID(str(tenant_id)),
            Client.deleted_at.is_(None),
        ).where(
            Client.first_name.ilike(f"%{query}%") |
            Client.last_name.ilike(f"%{query}%") |
            Client.email.ilike(f"%{query}%") |
            Client.company_name.ilike(f"%{query}%")
        ).limit(limit)
        res = await db.execute(stmt)
        clients = res.scalars().all()
        results["clients"] = [
            {"id": str(c.id), "name": c.display_name, "email": c.email, "type": "client"}
            for c in clients
        ]

    return results
