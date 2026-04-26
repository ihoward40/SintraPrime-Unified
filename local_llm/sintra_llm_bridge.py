"""
SintraLLMBridge — Drop-in replacement for OpenAI/Claude calls in SintraPrime.

Priority chain:
  1. Local LLM (Ollama / Hermes) — if SINTRA_LOCAL_LLM=true and reachable
  2. OpenAI                       — if OPENAI_API_KEY is set
  3. Claude (Anthropic)           — if ANTHROPIC_API_KEY is set
  4. Fallback                     — static error message, never raises

Environment variables:
  SINTRA_LOCAL_LLM        = "true"                   Enable local mode
  SINTRA_LOCAL_MODEL      = "hermes3"                Model name
  SINTRA_LOCAL_URL        = "http://localhost:11434"  Ollama URL
  SINTRA_LOCAL_FALLBACK   = "true"                   Fall back to cloud if local fails
  SINTRA_LLM_PROVIDER     = "hermes" | "ollama"      Which adapter to use
"""
from __future__ import annotations

import logging
import os
from typing import AsyncGenerator, Optional

from .hermes_adapter import (
    HERMES_LEGAL_SYSTEM,
    HERMES_TRUST_SYSTEM,
    HermesAdapter,
    build_chatml_prompt,
)
from .model_manager import ModelManager
from .ollama_adapter import OllamaAdapter
from .provider import LLMConfig, LLMResponse, LocalLLMProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _env_bool(key: str, default: bool = False) -> bool:
    return os.environ.get(key, str(default)).lower() in ("1", "true", "yes")


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


# ---------------------------------------------------------------------------
# Fallback response when no LLM is available
# ---------------------------------------------------------------------------

_FALLBACK_MSG = (
    "I'm unable to process your request at this time: "
    "no LLM backend is available (local Ollama is unreachable and no cloud API key is set). "
    "Please start Ollama with `ollama serve` or set OPENAI_API_KEY."
)


class SintraLLMBridge:
    """
    Unified LLM interface for SintraPrime.

    Automatically selects the best available backend and provides
    both a generic OpenAI-compatible chat API and specialised legal methods.
    """

    def __init__(
        self,
        local_llm: Optional[LocalLLMProvider] = None,
        force_local: Optional[bool] = None,
    ):
        self._use_local = force_local if force_local is not None else _env_bool("SINTRA_LOCAL_LLM")
        self._local_fallback = _env_bool("SINTRA_LOCAL_FALLBACK", default=True)
        self._local_model = _env_str("SINTRA_LOCAL_MODEL", "hermes3")
        self._local_url = _env_str("SINTRA_LOCAL_URL", "http://localhost:11434")
        self._provider_name = _env_str("SINTRA_LLM_PROVIDER", "hermes")

        # Allow injecting a pre-built provider (useful for testing)
        self._local_llm: Optional[LocalLLMProvider] = local_llm
        self._model_manager: Optional[ModelManager] = None

    # ------------------------------------------------------------------
    # Provider access
    # ------------------------------------------------------------------

    def _build_local_provider(self) -> LocalLLMProvider:
        """Construct the local LLM provider from env config."""
        config = LLMConfig(
            model=self._local_model,
            base_url=self._local_url,
        )
        if self._provider_name == "hermes":
            return HermesAdapter(config)
        return OllamaAdapter(config)

    async def _get_local(self) -> Optional[LocalLLMProvider]:
        """Return the local provider if it is reachable, else None."""
        if not self._use_local:
            return None
        if self._local_llm is None:
            self._local_llm = self._build_local_provider()
        try:
            if await self._local_llm.health_check():
                return self._local_llm
            logger.warning("Local LLM health check failed — not available.")
        except Exception as exc:
            logger.warning("Local LLM unavailable: %s", exc)
        return None

    async def is_local_available(self) -> bool:
        """Return True if the local LLM backend is reachable."""
        provider = await self._get_local()
        return provider is not None

    @property
    def model_manager(self) -> ModelManager:
        if self._model_manager is None:
            self._model_manager = ModelManager(base_url=self._local_url)
        return self._model_manager

    # ------------------------------------------------------------------
    # OpenAI-compatible chat interface
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict],
        **kwargs,
    ) -> str:
        """
        OpenAI-compatible chat interface.

        Args:
            messages: List of {"role": str, "content": str} dicts.
            **kwargs: Ignored (for drop-in compatibility).

        Returns:
            The assistant's reply as a plain string.
        """
        provider = await self._get_local()
        if provider is not None:
            try:
                response = await provider.chat(messages)
                return response.content
            except Exception as exc:
                logger.error("Local LLM chat failed: %s", exc)
                if not self._local_fallback:
                    return f"[Local LLM error] {exc}"

        # Cloud fallback
        cloud_response = await self._cloud_chat(messages)
        if cloud_response is not None:
            return cloud_response

        return _FALLBACK_MSG

    async def stream_chat(
        self,
        messages: list[dict],
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream chat tokens using the best available backend."""
        provider = await self._get_local()
        if provider is not None:
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
            try:
                async for token in provider.stream(prompt, system=system):
                    yield token
                return
            except Exception as exc:
                logger.error("Local LLM stream failed: %s", exc)
                if not self._local_fallback:
                    yield f"[Local LLM error] {exc}"
                    return

        # No local or fallback available
        yield _FALLBACK_MSG

    # ------------------------------------------------------------------
    # Specialised legal methods
    # ------------------------------------------------------------------

    async def legal_analysis(self, query: str, context: str = "") -> str:
        """
        Specialised legal reasoning.
        Uses Hermes legal system prompt when local LLM is available.
        """
        provider = await self._get_local()
        if provider is not None and isinstance(provider, HermesAdapter):
            try:
                response = await provider.legal_analysis(query, context=context)
                return response.content
            except Exception as exc:
                logger.error("Hermes legal analysis failed: %s", exc)
                if not self._local_fallback:
                    return f"[Local LLM error] {exc}"

        # Generic fallback using system prompt
        messages = [
            {"role": "system", "content": HERMES_LEGAL_SYSTEM},
            {"role": "user", "content": f"{query}\n\nContext: {context}" if context else query},
        ]
        return await self.chat(messages)

    async def trust_law_expert(self, question: str) -> str:
        """
        Trust law expert answer.
        Uses Hermes trust law system prompt.
        """
        provider = await self._get_local()
        if provider is not None and isinstance(provider, HermesAdapter):
            try:
                response = await provider.trust_law_expert(question)
                return response.content
            except Exception as exc:
                logger.error("Hermes trust law expert failed: %s", exc)
                if not self._local_fallback:
                    return f"[Local LLM error] {exc}"

        messages = [
            {"role": "system", "content": HERMES_TRUST_SYSTEM},
            {"role": "user", "content": question},
        ]
        return await self.chat(messages)

    async def chain_of_thought(self, question: str, context: str = "") -> str:
        """Multi-step reasoning with explicit chain of thought."""
        provider = await self._get_local()
        if provider is not None and isinstance(provider, HermesAdapter):
            try:
                response = await provider.chain_of_thought(question, context=context)
                return response.content
            except Exception as exc:
                logger.error("Hermes CoT failed: %s", exc)

        messages = [
            {
                "role": "system",
                "content": "Think step by step. Show your reasoning before your conclusion.",
            },
            {"role": "user", "content": question},
        ]
        return await self.chat(messages)

    async def summarise(self, text: str, instructions: str = "") -> str:
        """Summarise a piece of text, optionally with specific instructions."""
        directive = instructions or "Provide a concise and accurate summary."
        messages = [
            {"role": "system", "content": directive},
            {"role": "user", "content": f"Please summarise:\n\n{text}"},
        ]
        return await self.chat(messages)

    # ------------------------------------------------------------------
    # Cloud fallback stubs
    # (These would be filled in by the cloud-integration module)
    # ------------------------------------------------------------------

    async def _cloud_chat(self, messages: list[dict]) -> Optional[str]:
        """
        Try cloud providers in priority order: OpenAI → Claude.
        Returns None if no cloud provider is configured.
        """
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                return await self._openai_chat(messages, openai_key)
            except Exception as exc:
                logger.warning("OpenAI fallback failed: %s", exc)

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                return await self._claude_chat(messages, anthropic_key)
            except Exception as exc:
                logger.warning("Claude fallback failed: %s", exc)

        return None

    async def _openai_chat(self, messages: list[dict], api_key: str) -> str:
        """Call OpenAI chat completions API."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": messages,
                        "max_tokens": 2048,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except ImportError:
            raise RuntimeError("httpx required for OpenAI fallback")

    async def _claude_chat(self, messages: list[dict], api_key: str) -> str:
        """Call Anthropic Claude API."""
        try:
            import httpx

            system_msg = ""
            user_messages = []
            for m in messages:
                if m["role"] == "system":
                    system_msg = m["content"]
                else:
                    user_messages.append(m)

            payload: dict = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 2048,
                "messages": user_messages,
            }
            if system_msg:
                payload["system"] = system_msg

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"]
        except ImportError:
            raise RuntimeError("httpx required for Claude fallback")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def close(self) -> None:
        if self._local_llm and hasattr(self._local_llm, "close"):
            await self._local_llm.close()  # type: ignore[attr-defined]
        if self._model_manager:
            await self._model_manager.close()

    async def __aenter__(self) -> "SintraLLMBridge":
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()
