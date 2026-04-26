"""
SintraPrime RAG Legal Intelligence Engine
=========================================
Retrieval-Augmented Generation over SintraPrime's complete legal knowledge base.
"""

from .legal_rag import LegalRAG
from .document_ingester import DocumentIngester, LegalDocument
from .vector_store import VectorStore, VectorEntry
from .retriever import LegalRetriever
from .rag_pipeline import RAGPipeline
from .embedder import EmbeddingProvider

__all__ = [
    "LegalRAG",
    "DocumentIngester",
    "LegalDocument",
    "VectorStore",
    "VectorEntry",
    "LegalRetriever",
    "RAGPipeline",
    "EmbeddingProvider",
]

__version__ = "1.0.0"
__author__ = "SintraPrime — Sierra-3 RAG Engine"
