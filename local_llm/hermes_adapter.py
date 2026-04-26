"""
Hermes Adapter — NousResearch Hermes-specific LLM adapter for SintraPrime.

Extends OllamaAdapter with:
  - ChatML / Hermes token format  (<|im_start|> / <|im_end|>)
  - Structured function-calling (Hermes JSON tool-call format)
  - Chain-of-thought reasoning prompts
  - Legal domain specialisation prompts
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Optional

from .ollama_adapter import OllamaAdapter
from .provider import LLMConfig, LLMResponse, ProviderRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Recommended Hermes model identifiers
# ---------------------------------------------------------------------------
HERMES_MODELS = {
    "hermes3": {
        "ollama_id": "hermes3",
        "description": "Hermes-3 — strong legal reasoning, function calling",
        "size_gb": 4.7,
    },
    "nous-hermes2": {
        "ollama_id": "nous-hermes2",
        "description": "Nous-Hermes-2 — general + legal, 7B",
        "size_gb": 7.3,
    },
    "hermes-2-pro": {
        "ollama_id": "hermes-2-pro-mistral",
        "description": "Hermes-2-Pro — complex reasoning & structured output",
        "size_gb": 4.7,
    },
}

# ---------------------------------------------------------------------------
# Hermes system-prompt templates
# ---------------------------------------------------------------------------

HERMES_LEGAL_SYSTEM = (
    "You are a highly knowledgeable legal expert specialising in trust law, "
    "estate planning, fiduciary duties, and related areas. "
    "Provide clear, accurate, and structured legal analysis. "
    "Always cite relevant legal principles and note jurisdictional differences. "
    "When uncertain, say so explicitly. This is for informational purposes only "
    "and does not constitute legal advice."
)

HERMES_TRUST_SYSTEM = (
    "You are a trust law specialist with deep expertise in: "
    "revocable and irrevocable trusts, testamentary trusts, special needs trusts, "
    "charitable remainder trusts, dynasty trusts, spendthrift provisions, "
    "trustee duties and liabilities, beneficiary rights, and trust administration. "
    "Analyse questions methodically, referencing the Uniform Trust Code (UTC) "
    "and common law principles where applicable."
)

HERMES_REASONING_SYSTEM = (
    "You are a rigorous analytical reasoner. "
    "Break every problem into clear steps. "
    "Show your chain of thought explicitly before reaching a conclusion. "
    "Label your reasoning steps as [STEP 1], [STEP 2], etc., "
    "and conclude with [CONCLUSION]."
)

HERMES_FUNCTION_SYSTEM = (
    "You are a helpful AI assistant with access to external tools. "
    "When a tool is needed, respond ONLY with a JSON object in the format:\n"
    '{"tool": "<tool_name>", "arguments": {<key>: <value>}}\n'
    "Do not include any other text when calling a tool."
)


def build_chatml_prompt(
    user_message: str,
    system_message: str = "",
    history: Optional[list[dict]] = None,
) -> str:
    """
    Build a ChatML-formatted prompt using Hermes <|im_start|> tokens.

    Format:
        <|im_start|>system
        {system}<|im_end|>
        <|im_start|>user
        {user}<|im_end|>
        <|im_start|>assistant
    """
    parts: list[str] = []

    if system_message:
        parts.append(f"<|im_start|>system\n{system_message}<|im_end|>")

    if history:
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")

    parts.append(f"<|im_start|>user\n{user_message}<|im_end|>")
    parts.append("<|im_start|>assistant")

    return "\n".join(parts)


def build_function_call_prompt(
    user_message: str,
    tools: list[dict],
    system_message: str = "",
) -> str:
    """
    Build a Hermes-format function-calling prompt.

    tools: list of dicts with keys: name, description, parameters (JSON Schema)
    """
    tools_json = json.dumps(tools, indent=2)
    tool_block = (
        f"You have access to the following tools:\n\n{tools_json}\n\n"
        "To use a tool, respond with:\n"
        '{"tool": "<name>", "arguments": {<params>}}\n'
    )
    combined_system = f"{system_message}\n\n{tool_block}".strip() if system_message else tool_block
    return build_chatml_prompt(user_message, system_message=combined_system)


def build_cot_prompt(question: str, context: str = "") -> str:
    """Build a chain-of-thought prompt for Hermes."""
    ctx_block = f"\n\nContext:\n{context}" if context else ""
    return build_chatml_prompt(
        user_message=(
            f"Question: {question}{ctx_block}\n\n"
            "Please reason through this step by step before giving your final answer."
        ),
        system_message=HERMES_REASONING_SYSTEM,
    )


@ProviderRegistry.register("hermes")
class HermesAdapter(OllamaAdapter):
    """
    Hermes-specific adapter built on top of OllamaAdapter.

    Automatically applies ChatML formatting and Hermes-optimised prompts.
    """

    def __init__(self, config: LLMConfig):
        # Default to hermes3 if caller hasn't specified a Hermes model
        if config.model not in HERMES_MODELS and not config.model.startswith("hermes"):
            logger.warning(
                "Model '%s' may not be a Hermes model. "
                "Recommended: %s",
                config.model,
                list(HERMES_MODELS.keys()),
            )
        super().__init__(config)

    # ------------------------------------------------------------------
    # Core overrides — apply ChatML formatting automatically
    # ------------------------------------------------------------------

    async def generate(self, prompt: str, system: str = "") -> LLMResponse:
        """Generate with automatic ChatML wrapping."""
        chatml_prompt = build_chatml_prompt(prompt, system_message=system or self.config.system_prompt)
        # Pass empty system to parent so it goes in the prompt instead
        return await super().generate(chatml_prompt, system="")

    async def stream(self, prompt: str, system: str = "") -> AsyncGenerator[str, None]:
        """Stream with automatic ChatML wrapping."""
        chatml_prompt = build_chatml_prompt(prompt, system_message=system or self.config.system_prompt)
        async for token in super().stream(chatml_prompt, system=""):
            yield token

    # ------------------------------------------------------------------
    # Hermes-specific high-level methods
    # ------------------------------------------------------------------

    async def legal_analysis(self, query: str, context: str = "") -> LLMResponse:
        """
        Perform legal analysis using the Hermes legal system prompt.
        Optionally include document context.
        """
        ctx_block = f"\n\nRelevant context:\n{context}" if context else ""
        prompt = f"{query}{ctx_block}"
        chatml = build_chatml_prompt(prompt, system_message=HERMES_LEGAL_SYSTEM)
        return await super().generate(chatml, system="")

    async def trust_law_expert(self, question: str) -> LLMResponse:
        """Answer a trust law question with the Hermes trust law specialist prompt."""
        chatml = build_chatml_prompt(question, system_message=HERMES_TRUST_SYSTEM)
        return await super().generate(chatml, system="")

    async def chain_of_thought(self, question: str, context: str = "") -> LLMResponse:
        """Use Hermes chain-of-thought reasoning for complex questions."""
        prompt = build_cot_prompt(question, context=context)
        return await super().generate(prompt, system="")

    async def function_call(
        self,
        user_message: str,
        tools: list[dict],
        system: str = "",
    ) -> dict:
        """
        Issue a function-call prompt and parse the JSON response.

        Returns a dict: {"tool": str, "arguments": dict} or {"error": str}
        """
        prompt = build_function_call_prompt(user_message, tools, system_message=system)
        response = await super().generate(prompt, system="")
        content = response.content.strip()
        # Strip any trailing ChatML tokens that slipped through
        if "<|im_end|>" in content:
            content = content.split("<|im_end|>")[0].strip()
        try:
            result = json.loads(content)
            if "tool" not in result:
                raise ValueError("Missing 'tool' key in response")
            return result
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse function-call response: %s | raw: %r", exc, content)
            return {"error": str(exc), "raw": content}

    async def summarise_legal_doc(self, document: str) -> LLMResponse:
        """Summarise a legal document with Hermes legal expertise."""
        prompt = (
            f"Please provide a structured summary of the following legal document.\n"
            f"Include: key parties, main provisions, important dates, and any risks.\n\n"
            f"Document:\n{document}"
        )
        chatml = build_chatml_prompt(prompt, system_message=HERMES_LEGAL_SYSTEM)
        return await super().generate(chatml, system="")

    async def compare_legal_clauses(self, clause_a: str, clause_b: str) -> LLMResponse:
        """Compare two legal clauses and highlight differences."""
        prompt = (
            "Compare these two legal clauses and identify key differences, "
            "implications, and which is more favourable (and for whom).\n\n"
            f"Clause A:\n{clause_a}\n\nClause B:\n{clause_b}"
        )
        chatml = build_chatml_prompt(prompt, system_message=HERMES_LEGAL_SYSTEM)
        return await super().generate(chatml, system="")

    @staticmethod
    def list_hermes_models() -> list[dict]:
        """Return metadata about available Hermes model variants."""
        return [
            {"id": k, **v} for k, v in HERMES_MODELS.items()
        ]
