"""
SintraPrime Local LLM Integration Module
Provides offline intelligence via Hermes, Llama, Mistral, and any Ollama-compatible model.
"""

from .provider import LocalLLMProvider, LLMConfig, LLMResponse, ProviderRegistry
from .hermes_adapter import HermesAdapter
from .ollama_adapter import OllamaAdapter
from .model_manager import ModelManager
from .sintra_llm_bridge import SintraLLMBridge

__all__ = [
    "LocalLLMProvider",
    "LLMConfig",
    "LLMResponse",
    "ProviderRegistry",
    "HermesAdapter",
    "OllamaAdapter",
    "ModelManager",
    "SintraLLMBridge",
]

__version__ = "1.0.0"
__author__ = "SintraPrime Team"
