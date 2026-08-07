import logging
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.orchestration import MemoryEntry
from .remediation_service import remediation

logger = logging.getLogger(__name__)

class OmniBrainMemoryVault:
    """
    Phase 9: OmniBrain Memory Vault (SP-MEMORY-001).
    Durable persistence of institutional intelligence.
    """
    async def store_memory(
        self, 
        session: AsyncSession,
        tenant_id: str, 
        content: Any, 
        memory_type: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Stores a new memory entry with redaction and timestamps."""
        # Apply remediation: redaction and timestamps
        safe_content = remediation.redact_boundaries(content)
        safe_metadata = remediation.redact_boundaries(metadata or {})
        
        memory_id = f"mem-{uuid.uuid4().hex[:8]}"
        entry = MemoryEntry(
            id=memory_id,
            tenant_id=tenant_id,
            type=memory_type,
            content=safe_content,
            metadata_json=safe_metadata,
            version=1,
            created_at=datetime.now(UTC)
        )
        
        session.add(entry)
        await session.flush()
        logger.info(f"[MEMORY_VAULT] Stored {memory_type} memory {memory_id} for tenant {tenant_id}")
        return memory_id

    async def retrieve_tenant_memory(
        self, session: AsyncSession, tenant_id: str, memory_type: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Retrieves memory entries using SQLAlchemy with RLS context."""
        query = select(MemoryEntry).where(MemoryEntry.tenant_id == tenant_id)
        if memory_type:
            query = query.where(MemoryEntry.type == memory_type)
        
        query = query.order_by(MemoryEntry.created_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

# Global instance
memory_vault = OmniBrainMemoryVault()
