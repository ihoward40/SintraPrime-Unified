"""Local LLM Provider — SintraPrime offline intelligence."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for a local LLM provider."""
    model: str = "hermes3"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 4096
    context_window: int = 8192
    stream: bool = True
    system_prompt: str = ""
    timeout: int = 120
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    seed: Optional[int] = None

    def to_ollama_options(self) -> dict:
        """Convert config to Ollama API options dict."""
        opts = {
            "temperature": self.temperature,
            "num_predict": self.max_tokens,
            "num_ctx": self.context_window,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
        }
        if self.seed is not None:
            opts["seed"] = self.seed
        return opts


@dataclass
class LLMResponse:
    """Standardised response object from any local LLM provider."""
    content: str
    model: str
    tokens_used: int = 0
    finish_reason: str = "stop"
    metadata: dict = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return self.finish_reason in ("stop", "length", "eos")

    def __str__(self) -> str:
        return self.content


class LocalLLMProvider(ABC):
    """Abstract base class for all local LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def generate(self, prompt: str, system: str = "") -> LLMResponse:
        """Generate a complete response for the given prompt."""

    @abstractmethod
    async def stream(self, prompt: str, system: str = "") -> AsyncGenerator[str, None]:
        """Stream response tokens as they are generated."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the backend is reachable and a model is loaded."""

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.
        Not all providers support embeddings — raises NotImplementedError by default.
        """
        raise NotImplementedError(f"Embedding not supported by {self.__class__.__name__}")

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        """
        OpenAI-compatible chat interface.
        Converts a list of {'role': ..., 'content': ...} dicts into a prompt.
        """
        system = ""
        user_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system = content
            elif role == "assistant":
                user_parts.append(f"Assistant: {content}")
            else:
                user_parts.append(f"User: {content}")
        prompt = "\n".join(user_parts)
        return await self.generate(prompt, system=system)


class ProviderRegistry:
    """Registry for all available local LLM providers."""

    _providers: dict[str, type] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a provider class under a string key."""
        def decorator(klass):
            cls._providers[name] = klass
            logger.debug("Registered LLM provider: %s -> %s", name, klass.__name__)
            return klass
        return decorator

    @classmethod
    def get(cls, name: str, config: LLMConfig) -> "LocalLLMProvider":
        """Instantiate and return the named provider with the given config."""
        if name not in cls._providers:
            available = list(cls._providers.keys())
            raise ValueError(
                f"Unknown provider: '{name}'. Available providers: {available}"
            )
        return cls._providers[name](config)

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return the names of all registered providers."""
        return list(cls._providers.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._providers
