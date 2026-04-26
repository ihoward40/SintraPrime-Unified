"""
Memory API — FastAPI router exposing memory engine endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, HTTPException, Query
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from .memory_engine import MemoryEngine
from .memory_types import MemoryType

# Singleton memory engine (can be replaced via dependency injection)
_engine: Optional[MemoryEngine] = None


def get_engine() -> MemoryEngine:
    global _engine
    if _engine is None:
        _engine = MemoryEngine()
    return _engine


def set_engine(engine: MemoryEngine) -> None:
    """Allow injection of a custom engine instance (useful for testing)."""
    global _engine
    _engine = engine


if FASTAPI_AVAILABLE:
    router = APIRouter(prefix="/memory", tags=["memory"])

    # ------------------------------------------------------------------ #
    #  Request / Response models                                            #
    # ------------------------------------------------------------------ #

    class StoreRequest(BaseModel):
        content: str = Field(..., min_length=1, description="Content to store")
        tags: List[str] = Field(default_factory=list)
        user_id: Optional[str] = None
        importance: Optional[float] = Field(None, ge=0.0, le=1.0)
        memory_type: Optional[str] = None

    class PreferenceUpdate(BaseModel):
        key: str
        value: Any

    class MemoryResponse(BaseModel):
        id: str
        content: str
        memory_type: str
        tags: List[str]
        importance: float
        created_at: str
        user_id: Optional[str]

    class RecallResponse(BaseModel):
        results: List[Dict[str, Any]]
        count: int
        query: str

    class StatsResponse(BaseModel):
        semantic: Dict[str, Any]
        episodic: Dict[str, Any]
        working: Dict[str, Any]
        profiles: Dict[str, Any]
        timestamp: str

    # ------------------------------------------------------------------ #
    #  Endpoints                                                            #
    # ------------------------------------------------------------------ #

    @router.get("/recall", response_model=RecallResponse, summary="Recall memories by query")
    async def recall_memories(
        query: str = Query(..., description="Search query"),
        user_id: Optional[str] = Query(None, description="Filter by user ID"),
        top_k: int = Query(10, ge=1, le=50, description="Max results"),
        memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    ):
        """Retrieve relevant memories using semantic similarity search."""
        engine = get_engine()
        types = None
        if memory_type:
            try:
                types = [MemoryType(memory_type)]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid memory_type. Options: {[t.value for t in MemoryType]}",
                )
        results = engine.recall(query=query, memory_types=types, user_id=user_id, top_k=top_k)
        return RecallResponse(
            results=[r.to_dict() for r in results],
            count=len(results),
            query=query,
        )

    @router.post("/store", response_model=MemoryResponse, status_code=201, summary="Store a memory")
    async def store_memory(req: StoreRequest):
        """Store new content in the memory engine."""
        engine = get_engine()
        mt = None
        if req.memory_type:
            try:
                mt = MemoryType(req.memory_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid memory_type. Options: {[t.value for t in MemoryType]}",
                )
        entry = engine.remember(
            content=req.content,
            user_id=req.user_id,
            memory_type=mt,
            tags=req.tags,
            importance=req.importance,
        )
        return MemoryResponse(
            id=entry.id,
            content=entry.content,
            memory_type=entry.memory_type.value,
            tags=entry.tags,
            importance=entry.importance,
            created_at=entry.created_at.isoformat(),
            user_id=entry.user_id,
        )

    @router.delete("/{entry_id}", summary="Delete a specific memory entry")
    async def delete_memory(entry_id: str):
        """Remove a memory entry by its ID."""
        engine = get_engine()
        success = engine.semantic.forget(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Memory entry '{entry_id}' not found.")
        return {"deleted": True, "entry_id": entry_id}

    @router.get("/profile/{user_id}", summary="Get user profile")
    async def get_profile(user_id: str):
        """Retrieve a user's persistent profile."""
        engine = get_engine()
        profile = engine.profiles.get_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile not found for user '{user_id}'.")
        return profile.to_dict()

    @router.put("/profile/{user_id}/preference", summary="Update user preference")
    async def update_preference(user_id: str, req: PreferenceUpdate):
        """Update a preference key in the user's profile."""
        engine = get_engine()
        profile = engine.profiles.update_preference(user_id, req.key, req.value)
        return {
            "updated": True,
            "user_id": user_id,
            "key": req.key,
            "value": req.value,
            "profile_updated_at": profile.updated_at.isoformat(),
        }

    @router.get("/export/{user_id}", summary="Export all user data (GDPR)")
    async def export_user_data(user_id: str):
        """Export all stored data for a user for GDPR compliance."""
        engine = get_engine()
        data = engine.export_user_data(user_id)
        return data

    @router.delete("/user/{user_id}", summary="Delete all user data (GDPR)")
    async def delete_user_data(user_id: str):
        """
        Permanently delete all data associated with a user.
        This action is irreversible and satisfies GDPR right-to-erasure.
        """
        engine = get_engine()
        stats = engine.forget_all(user_id)
        return {
            "deleted": True,
            "user_id": user_id,
            "stats": stats,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

    @router.get("/stats", response_model=StatsResponse, summary="Memory system statistics")
    async def memory_stats():
        """Return statistics about memory usage across all layers."""
        engine = get_engine()
        return engine.memory_stats()

    @router.get("/context", summary="Get relevant context for LLM prompt")
    async def get_context(
        query: str = Query(..., description="Query to build context around"),
        user_id: Optional[str] = Query(None),
        max_tokens: int = Query(4000, ge=100, le=16000),
    ):
        """Build a context string for injection into an LLM prompt."""
        engine = get_engine()
        context_str = engine.get_relevant_context(
            query=query, user_id=user_id, max_tokens=max_tokens
        )
        return {"context": context_str, "query": query, "user_id": user_id}

else:
    # Stub when FastAPI is not installed
    router = None  # type: ignore

    def recall_memories(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed. Run: pip install fastapi")

    def store_memory(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed.")
