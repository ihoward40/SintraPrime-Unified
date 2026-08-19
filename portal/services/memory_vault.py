import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration import MemoryEntry
from .remediation_service import remediation

logger = logging.getLogger(__name__)


class OmniBrainMemoryVault:
    """Durable persistence of tenant-scoped institutional intelligence."""

    async def store_memory(
        self,
        session: AsyncSession,
        tenant_id: str,
        content: Any,
        memory_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a new memory entry with redaction and timestamps."""
        safe_content = remediation.redact_boundaries(content)
        safe_metadata = remediation.redact_boundaries(metadata or {})

        # MemoryEntry.id is a native UUID column; keep the service representation
        # compatible with the ORM/database contract.
        memory_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=memory_id,
            tenant_id=tenant_id,
            type=memory_type,
            content=safe_content,
            metadata_json=safe_metadata,
            version=1,
            created_at=datetime.now(UTC),
        )

        session.add(entry)
        await session.flush()
        logger.info(
            "[MEMORY_VAULT] Stored %s memory %s for tenant %s",
            memory_type,
            memory_id,
            tenant_id,
        )
        return memory_id

    async def retrieve_tenant_memory(
        self,
        session: AsyncSession,
        tenant_id: str,
        memory_type: str | None = None,
    ) -> list[MemoryEntry]:
        """Retrieve memory entries using SQLAlchemy with RLS context."""
        query = select(MemoryEntry).where(MemoryEntry.tenant_id == tenant_id)
        if memory_type:
            query = query.where(MemoryEntry.type == memory_type)

        query = query.order_by(MemoryEntry.created_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())


memory_vault = OmniBrainMemoryVault()
