import logging
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class MemoryType(str, Enum):
    LESSON_LEARNED = "LESSON_LEARNED"
    PROVEN_PROCEDURE = "PROVEN_PROCEDURE"
    INSTITUTIONAL_KNOWLEDGE = "INSTITUTIONAL_KNOWLEDGE"
    AUDIT_TRAIL = "AUDIT_TRAIL"

class MemoryEntry(BaseModel):
    id: str
    type: MemoryType
    content: Any
    metadata: Dict[str, Any]
    tenant_id: str
    created_at: datetime
    version: int

class OmniBrainMemoryVault:
    """
    Phase 9: OmniBrain Memory Vault (SP-MEMORY-001).
    Consolidates institutional intelligence, learned lessons, and proven procedures.
    """
    def __init__(self):
        self.vault: Dict[str, MemoryEntry] = {}
        self.index: Dict[str, List[str]] = {} # tenant_id -> list of memory_ids

    async def store_memory(
        self, 
        tenant_id: str, 
        content: Any, 
        memory_type: MemoryType, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Stores a new memory entry in the vault."""
        memory_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=memory_id,
            type=memory_type,
            content=content,
            metadata=metadata or {},
            tenant_id=tenant_id,
            created_at=datetime.now(UTC),
            version=1
        )
        
        self.vault[memory_id] = entry
        
        if tenant_id not in self.index:
            self.index[tenant_id] = []
        self.index[tenant_id].append(memory_id)
        
        logger.info(f"[MEMORY_VAULT] Stored {memory_type} memory {memory_id} for tenant {tenant_id}")
        return memory_id

    async def retrieve_tenant_memory(self, tenant_id: str, memory_type: Optional[MemoryType] = None) -> List[MemoryEntry]:
        """Retrieves memory entries for a specific tenant, optionally filtered by type."""
        if tenant_id not in self.index:
            return []
            
        memory_ids = self.index[tenant_id]
        entries = [self.vault[mid] for mid in memory_ids]
        
        if memory_type:
            entries = [e for e in entries if e.type == memory_type]
            
        return sorted(entries, key=lambda x: x.created_at, reverse=True)

    async def search_memory(self, tenant_id: str, query: str) -> List[MemoryEntry]:
        """Simple keyword-based memory search (mocked for foundation)."""
        entries = await self.retrieve_tenant_memory(tenant_id)
        # In a real implementation, this would use vector search or full-text index
        return [e for e in entries if query.lower() in str(e.content).lower()]

# Global instance
memory_vault = OmniBrainMemoryVault()
