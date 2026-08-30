"""Governed, provider-neutral capabilities for SintraPrime agents.

External projects such as browser-use, Crawl4AI, Firecrawl, Mem0, RAGFlow,
and LocalAI can be integrated behind these contracts without granting them
execution authority inside the platform.
"""

from .contracts import (
    ActionDecision,
    ActionPolicy,
    BrowserAction,
    BrowserActor,
    CapabilityError,
    Citation,
    KnowledgeRetriever,
    MemoryRecord,
    MemoryStore,
    RetrievalResult,
    WebDocument,
    WebReader,
)
from .memory import GovernedMemoryStore
from .policy import DefaultActionPolicy

__all__ = [
    "ActionDecision",
    "ActionPolicy",
    "BrowserAction",
    "BrowserActor",
    "CapabilityError",
    "Citation",
    "DefaultActionPolicy",
    "GovernedMemoryStore",
    "KnowledgeRetriever",
    "MemoryRecord",
    "MemoryStore",
    "RetrievalResult",
    "WebDocument",
    "WebReader",
]
