"""
LegalRAG — High-level interface for SintraPrime's RAG engine.

Auto-ingests SintraPrime's knowledge base on first run and caches embeddings.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional

from .document_ingester import DocumentIngester, LegalDocument
from .embedder import EmbeddingProvider
from .rag_pipeline import RAGPipeline
from .retriever import LegalRetriever
from .vector_store import VectorEntry, VectorStore


# Directories SintraPrime auto-indexes (relative to SintraPrime-Unified root)
AUTO_INDEX_MODULES = [
    ("trust_law", "trust_law"),
    ("legal_intelligence", "legal_intelligence"),
    ("federal_agencies", "federal_agencies"),
    ("case_law", "case_law"),
    ("compliance", "compliance"),
    ("contract_intelligence", "contract_intelligence"),
    ("rag", "rag_source"),          # self-index the RAG module
]


class LegalRAG:
    """
    Main interface for SintraPrime's RAG Legal Intelligence Engine.

    Usage:
        rag = LegalRAG()
        await rag.initialize()
        result = await rag.ask("What are a trustee's fiduciary duties?")
        print(result["answer"])
    """

    CACHE_FILE_NAME = "index_cache.json"

    def __init__(
        self,
        base_path: Optional[str] = None,
        persist_path: Optional[str] = None,
        use_chroma: bool = False,
        llm_model: Optional[str] = None,
    ):
        """
        Args:
            base_path:    Root of SintraPrime-Unified repo. Auto-detected if None.
            persist_path: Where to store the vector index JSON.
            use_chroma:   Use ChromaDB for vector storage if available.
            llm_model:    Override LLM model name (e.g. "gpt-4-turbo").
        """
        self.base_path = Path(base_path or self._detect_base_path())
        rag_dir = self.base_path / "rag"
        self.persist_path = persist_path or str(rag_dir / "knowledge_base.json")
        self._cache_path = rag_dir / self.CACHE_FILE_NAME

        # Core components
        self.store = VectorStore(persist_path=self.persist_path, use_chroma=use_chroma)
        self.embedder = EmbeddingProvider()
        self.retriever = LegalRetriever(self.store, self.embedder)
        self.pipeline = RAGPipeline(self.retriever, self.embedder, llm_model=llm_model)
        self.ingester = DocumentIngester()

        self._initialized = False

    # ------------------------------------------------------------------ #
    #  Initialisation                                                      #
    # ------------------------------------------------------------------ #

    async def initialize(self, force_reindex: bool = False) -> dict:
        """
        Auto-index all SintraPrime legal modules.

        Skips re-indexing if a valid cache exists (unless force_reindex=True).

        Returns:
            {"documents": N, "chunks": N, "categories": [...], "elapsed": "Xs"}
        """
        start = time.perf_counter()

        # Try to load existing index
        if not force_reindex and self._load_cache():
            self._initialized = True
            elapsed = round(time.perf_counter() - start, 2)
            stats = self.store.stats()
            return {
                "status": "loaded_from_cache",
                "documents": stats["total_documents"],
                "categories": list(stats["categories"].keys()),
                "elapsed": f"{elapsed}s",
            }

        # Fresh index
        total_docs = 0
        total_chunks = 0
        categories: list[str] = []

        for module_dir, category in AUTO_INDEX_MODULES:
            module_path = self.base_path / module_dir
            if not module_path.exists():
                continue

            docs = self.ingester.ingest_directory(str(module_path), category)
            if not docs:
                continue

            # Batch embed all chunks
            all_texts: list[str] = []
            doc_chunk_map: list[tuple[LegalDocument, int]] = []  # (doc, chunk_idx)

            for doc in docs:
                for i, chunk in enumerate(doc.chunks):
                    all_texts.append(chunk)
                    doc_chunk_map.append((doc, i))

            if all_texts:
                embeddings = await self.embedder.embed_batch(all_texts)
                for (doc, chunk_idx), embedding in zip(doc_chunk_map, embeddings):
                    entry_id = f"{doc.id}_c{chunk_idx}"
                    meta = dict(doc.metadata)
                    meta["chunk_index"] = chunk_idx
                    meta["parent_doc_id"] = doc.id
                    entry = VectorEntry(
                        id=entry_id,
                        embedding=embedding,
                        content=doc.chunks[chunk_idx],
                        metadata=meta,
                    )
                    self.store.add(entry)
                    total_chunks += 1

            total_docs += len(docs)
            if category not in categories:
                categories.append(category)

        # Persist index
        self.store.save()
        self._save_cache(total_docs, total_chunks, categories)
        self.retriever.build_bm25_index()
        self._initialized = True

        elapsed = round(time.perf_counter() - start, 2)
        return {
            "status": "indexed",
            "documents": total_docs,
            "chunks": total_chunks,
            "categories": categories,
            "elapsed": f"{elapsed}s",
        }

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    async def ask(self, question: str, **kwargs) -> dict:
        """
        Ask any legal question. Initialises the knowledge base if needed.

        Args:
            question:     Natural language legal question.
            jurisdiction: Optional jurisdiction filter.
            top_k:        Number of passages to retrieve.

        Returns:
            Full RAGPipeline response dict.
        """
        await self._ensure_initialized()
        return await self.pipeline.ask(question, **kwargs)

    async def ask_trust_law(self, question: str) -> dict:
        """Specialised trust law Q&A."""
        await self._ensure_initialized()
        return await self.pipeline.ask_trust_law(question)

    async def analyze_document(self, document_text: str) -> dict:
        """Analyze an arbitrary legal document."""
        await self._ensure_initialized()
        return await self.pipeline.analyze_document(document_text)

    async def find_precedents(self, case_facts: str) -> dict:
        """Find relevant case law precedents."""
        await self._ensure_initialized()
        return await self.pipeline.find_precedents(case_facts)

    async def ingest(self, path: str, category: str = "user_document") -> int:
        """
        Ingest a new document (file or directory) into the knowledge base.

        Args:
            path:     Filesystem path to file or directory.
            category: Logical category for the document(s).

        Returns:
            Number of chunks ingested.
        """
        await self._ensure_initialized()

        p = Path(path)
        if p.is_dir():
            docs = self.ingester.ingest_directory(path, category)
        elif p.suffix.lower() == ".pdf":
            docs = self.ingester.ingest_pdf(path)
        elif p.suffix.lower() == ".json":
            data = json.loads(p.read_text(encoding="utf-8"))
            docs = [self.ingester.ingest_case_json(data)]
        else:
            content = p.read_text(encoding="utf-8", errors="replace")
            from .document_ingester import LegalDocument
            import hashlib
            doc_id = hashlib.sha1(path.encode()).hexdigest()[:12]
            meta = self.ingester.extract_legal_metadata(content)
            meta.update({"source": path, "category": category, "file_name": p.name})
            chunks = self.ingester.chunk_text(content, doc_id)
            docs = [LegalDocument(id=doc_id, content=content, metadata=meta, chunks=chunks)]

        if not docs:
            return 0

        all_texts: list[str] = []
        doc_chunk_map: list[tuple] = []
        for doc in docs:
            for i, chunk in enumerate(doc.chunks):
                all_texts.append(chunk)
                doc_chunk_map.append((doc, i))

        chunk_count = 0
        if all_texts:
            embeddings = await self.embedder.embed_batch(all_texts)
            for (doc, chunk_idx), embedding in zip(doc_chunk_map, embeddings):
                entry_id = f"{doc.id}_c{chunk_idx}"
                meta = dict(doc.metadata)
                meta["chunk_index"] = chunk_idx
                entry = VectorEntry(
                    id=entry_id,
                    embedding=embedding,
                    content=doc.chunks[chunk_idx],
                    metadata=meta,
                )
                self.store.add(entry)
                chunk_count += 1

        # Rebuild BM25 index and save
        self.retriever.build_bm25_index()
        self.store.save()

        return chunk_count

    def status(self) -> dict:
        """Return knowledge base statistics."""
        stats = self.store.stats()
        stats["initialized"] = self._initialized
        stats["embedder"] = {
            "provider": self.embedder.provider,
            "dim": self.embedder.dim,
        }
        stats["llm_backend"] = self.pipeline._llm_backend
        stats["base_path"] = str(self.base_path)
        return stats

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _ensure_initialized(self) -> None:
        """Lazy initialisation."""
        if not self._initialized:
            await self.initialize()

    def _detect_base_path(self) -> str:
        """Walk up from this file's location to find the repo root."""
        here = Path(__file__).parent        # .../SintraPrime-Unified/rag/
        candidate = here.parent             # .../SintraPrime-Unified/
        if (candidate / "rag").exists():
            return str(candidate)
        return str(here.parent)

    def _load_cache(self) -> bool:
        """Load from persisted vector store if cache is valid."""
        if not self._cache_path.exists():
            return False
        try:
            self.store.load()
            if len(self.store) > 0:
                self.retriever.build_bm25_index()
                return True
        except Exception as exc:
            print(f"[LegalRAG] Cache load failed: {exc}")
        return False

    def _save_cache(self, docs: int, chunks: int, categories: list[str]) -> None:
        """Write cache metadata."""
        try:
            self._cache_path.write_text(
                json.dumps(
                    {
                        "documents": docs,
                        "chunks": chunks,
                        "categories": categories,
                        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[LegalRAG] Could not save cache metadata: {exc}")

    def __repr__(self) -> str:
        return (
            f"<LegalRAG initialized={self._initialized} "
            f"docs={len(self.store)} "
            f"embedder={self.embedder.provider} "
            f"llm={self.pipeline._llm_backend}>"
        )
