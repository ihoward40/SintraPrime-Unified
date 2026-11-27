# Inspired by vectorize-io/hindsight (MIT License) — https://github.com/vectorize-io/hindsight
"""
Memory API — FastAPI router exposing memory engine endpoints.

Includes the learning-memory endpoints (retain / recall / reflect,
banks, knowledge pages) adapted from vectorize-io/hindsight.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, HTTPException, Query
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from .learning import KnowledgePage, LearningMemory, MemoryBank, Reflection
from .memory_engine import MemoryEngine
from .memory_types import MemoryType

# Singleton memory engine (can be replaced via dependency injection)
_engine: Optional[MemoryEngine] = None

# Singleton learning layer built on the engine above
_learning: Optional[LearningMemory] = None


def get_engine() -> MemoryEngine:
    global _engine
    if _engine is None:
        _engine = MemoryEngine()
    return _engine


def set_engine(engine: MemoryEngine) -> None:
    """Allow injection of a custom engine instance (useful for testing)."""
    global _engine
    _engine = engine
    # Reset the learning layer so it is rebuilt on the new engine.
    set_learning(None)


def get_learning() -> LearningMemory:
    global _learning
    if _learning is None:
        _learning = LearningMemory(get_engine())
    return _learning


def set_learning(learning: Optional[LearningMemory]) -> None:
    """Allow injection of a custom learning layer (useful for testing)."""
    global _learning
    _learning = learning


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

    # ----- Learning-memory models (retain / recall / reflect) ------------- #

    class BankCreateRequest(BaseModel):
        name: str = Field(..., min_length=1, description="Bank name (e.g. 'Legal')")
        description: str = Field("", description="What this bank partitions")
        purpose: str = Field("", description="Why this bank exists")

    class BankResponse(BaseModel):
        bank_id: str
        name: str
        description: str
        purpose: str
        created_at: str

    class LearningRetainRequest(BaseModel):
        content: str = Field(..., min_length=1, description="Fact to retain")
        bank_id: Optional[str] = Field(None, description="Bank to retain into")
        tags: List[str] = Field(default_factory=list)
        user_id: Optional[str] = None
        importance: Optional[float] = Field(None, ge=0.0, le=1.0)
        memory_type: Optional[str] = None

    class ReflectionResponse(BaseModel):
        query: str
        bank_id: Optional[str]
        summary: str
        key_themes: List[Dict[str, Any]]
        memory_count: int
        knowledge_pages: List[Dict[str, Any]]
        reflected_at: str

    class KnowledgePageResponse(BaseModel):
        page_id: str
        title: str
        domain: str
        bank_id: Optional[str]
        summary: str
        key_points: List[str]
        supporting_entry_ids: List[str]
        confidence: float
        created_at: str
        updated_at: str

    def _memory_response_from_entry(entry) -> MemoryResponse:
        return MemoryResponse(
            id=entry.id,
            content=entry.content,
            memory_type=entry.memory_type.value,
            tags=entry.tags,
            importance=entry.importance,
            created_at=entry.created_at.isoformat(),
            user_id=entry.user_id,
        )

    def _bank_response_from_bank(bank: MemoryBank) -> BankResponse:
        return BankResponse(
            bank_id=bank.bank_id,
            name=bank.name,
            description=bank.description,
            purpose=bank.purpose,
            created_at=bank.created_at.isoformat(),
        )

    def _page_response_from_page(page: KnowledgePage) -> KnowledgePageResponse:
        return KnowledgePageResponse(
            page_id=page.page_id,
            title=page.title,
            domain=page.domain,
            bank_id=page.bank_id,
            summary=page.summary,
            key_points=page.key_points,
            supporting_entry_ids=page.supporting_entry_ids,
            confidence=page.confidence,
            created_at=page.created_at.isoformat(),
            updated_at=page.updated_at.isoformat(),
        )

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

    # ------------------------------------------------------------------ #
    #  Learning-memory endpoints (retain / recall / reflect)                #
    #  Adapted from vectorize-io/hindsight's core operations.              #
    # ------------------------------------------------------------------ #

    @router.post("/learning/banks", response_model=BankResponse, status_code=201,
                 summary="Create a memory bank")
    async def create_bank(req: BankCreateRequest):
        """Create a named bank that partitions memory by domain or purpose."""
        learning = get_learning()
        bank = learning.create_bank(
            name=req.name, description=req.description, purpose=req.purpose
        )
        return _bank_response_from_bank(bank)

    @router.get("/learning/banks", response_model=List[BankResponse],
                summary="List memory banks")
    async def list_banks():
        """List all registered memory banks."""
        learning = get_learning()
        return [_bank_response_from_bank(b) for b in learning.list_banks()]

    @router.post("/learning/retain", response_model=MemoryResponse, status_code=201,
                 summary="Retain a fact in learning memory")
    async def learning_retain(req: LearningRetainRequest):
        """Retain a durable, reusable fact, optionally scoped to a bank."""
        learning = get_learning()
        mt = None
        if req.memory_type:
            try:
                mt = MemoryType(req.memory_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid memory_type. Options: {[t.value for t in MemoryType]}",
                )
        try:
            entry = learning.retain(
                content=req.content,
                bank_id=req.bank_id,
                user_id=req.user_id,
                importance=req.importance,
                memory_type=mt,
                tags=req.tags,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return _memory_response_from_entry(entry)

    @router.get("/learning/recall", response_model=RecallResponse,
                summary="Recall from learning memory")
    async def learning_recall(
        query: str = Query(..., description="Search query"),
        bank_id: Optional[str] = Query(None, description="Scope to a bank"),
        user_id: Optional[str] = Query(None, description="Filter by user ID"),
        top_k: int = Query(10, ge=1, le=50, description="Max results"),
    ):
        """Recall relevant retained memories, optionally scoped to a bank."""
        learning = get_learning()
        try:
            results = learning.recall(
                query=query, bank_id=bank_id, user_id=user_id, top_k=top_k
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return RecallResponse(
            results=[r.to_dict() for r in results],
            count=len(results),
            query=query,
        )

    @router.get("/learning/reflect", response_model=ReflectionResponse,
                summary="Reflect over learning memory")
    async def learning_reflect(
        query: str = Query(..., description="Topic to reflect on"),
        bank_id: Optional[str] = Query(None, description="Scope to a bank"),
        user_id: Optional[str] = Query(None, description="Filter by user ID"),
        top_k: int = Query(10, ge=1, le=50, description="Memories to synthesize"),
    ):
        """Reflect over recalled memories and distill knowledge pages."""
        learning = get_learning()
        try:
            reflection = learning.reflect(
                query=query, bank_id=bank_id, user_id=user_id, top_k=top_k
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return ReflectionResponse(
            query=reflection.query,
            bank_id=reflection.bank_id,
            summary=reflection.summary,
            key_themes=reflection.key_themes,
            memory_count=reflection.memory_count,
            knowledge_pages=[p.to_dict() for p in reflection.knowledge_pages],
            reflected_at=reflection.reflected_at.isoformat(),
        )

    @router.post("/learning/cycle", summary="Run a learning consolidation cycle")
    async def learning_cycle(
        bank_id: Optional[str] = Query(None, description="Scope to a bank"),
        user_id: Optional[str] = Query(None),
    ):
        """Reflect over all retained memories in a bank and refresh knowledge pages."""
        learning = get_learning()
        try:
            pages = learning.run_learning_cycle(bank_id=bank_id, user_id=user_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {
            "pages_refreshed": len(pages),
            "bank_id": bank_id,
            "pages": [p.to_dict() for p in pages],
        }

    @router.get("/learning/pages", response_model=List[KnowledgePageResponse],
                summary="List knowledge pages")
    async def list_knowledge_pages(
        bank_id: Optional[str] = Query(None, description="Scope to a bank"),
        user_id: Optional[str] = Query(None),
    ):
        """List distilled knowledge pages (mental models)."""
        learning = get_learning()
        try:
            pages = learning.get_knowledge_pages(bank_id=bank_id, user_id=user_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return [_page_response_from_page(p) for p in pages]

    @router.get("/learning/pages/{page_id}", response_model=KnowledgePageResponse,
                summary="Get a knowledge page")
    async def get_knowledge_page(page_id: str):
        """Retrieve one knowledge page by its page_id."""
        learning = get_learning()
        page = learning.get_knowledge_page(page_id)
        if page is None:
            raise HTTPException(
                status_code=404, detail=f"Knowledge page '{page_id}' not found."
            )
        return _page_response_from_page(page)

else:
    # Stub when FastAPI is not installed
    router = None  # type: ignore

    def recall_memories(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed. Run: pip install fastapi")

    def store_memory(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed.")

    def create_bank(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed.")

    def list_banks(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed.")

    def learning_retain(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed.")

    def learning_recall(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed.")

    def learning_reflect(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed.")

    def learning_cycle(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed.")

    def list_knowledge_pages(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed.")

    def get_knowledge_page(*args, **kwargs):
        raise RuntimeError("FastAPI is not installed.")
