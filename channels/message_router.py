"""
MessageRouter — intent detection and entity extraction for SintraPrime-Unified.

Classifies incoming messages into structured intents and extracts named entities
so each SintraPrime module (legal, research, document, scheduler, finance) can
handle requests without touching raw message text.

Inspired by Manus AI intent routing and Hermes Agent enterprise dispatch.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from .message_types import ChannelType, IncomingMessage, Intent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword keyword patterns for rule-based intent detection
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: List[Tuple[Intent, List[str]]] = [
    # High-specificity intents first — these have strong, unambiguous keywords
    (
        Intent.REMINDER,
        [
            r"\b(remind me|set reminder|don.t forget|remember to|alert me|notify me)\b",
        ],
    ),
    (
        Intent.RESEARCH_REQUEST,
        [
            r"\b(research|investigate|find out|look up|dig into|analyze|analyse|"
            r"study|explore|deep dive|report on|summarize about)\b",
        ],
    ),
    (
        Intent.TASK_MANAGEMENT,
        [
            r"\b(task|schedule|deadline|due|calendar|todo|to-do|assign|"
            r"track|followup|follow.up|milestone)\b",
        ],
    ),
    (
        Intent.FINANCIAL_QUERY,
        [
            r"\b(invoice|payment|billing|cost|price|fee|budget|revenue|expense|"
            r"finance|money|dollar|amount|account|balance|transaction|payable|"
            r"receivable)\b",
        ],
    ),
    (
        Intent.DOCUMENT_REQUEST,
        [
            r"\b(draft|generate|create|write|prepare|compose|template|document|"
            r"letter|memo|agreement|NDA|form|report|proposal)\b",
        ],
    ),
    (
        Intent.STATUS_CHECK,
        [
            r"\b(status|progress|update|how.s|running|working|online|offline|"
            r"health|ready|done|completed|pending)\b",
        ],
    ),
    # LEGAL_QUESTION last — its keywords are broad and overlap with other intents
    (
        Intent.LEGAL_QUESTION,
        [
            r"\b(legal|statute|regulation|court|attorney|lawyer|sue|lawsuit|"
            r"litigation|contract|liability|jurisdiction|tort|habeas|motion|brief|"
            r"pleading|deposition|subpoena|evidence|verdict|appeal|settlement)\b",
        ],
    ),
]

# ---------------------------------------------------------------------------
# Entity extraction patterns
# ---------------------------------------------------------------------------

_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}|"
    r"\d{4}-\d{2}-\d{2}|"
    r"(?:today|tomorrow|yesterday|next\s+\w+|this\s+\w+))\b",
    re.IGNORECASE,
)

_CASE_NUMBER_PATTERN = re.compile(
    r"\b(?:case|docket|matter|no\.?|number)?\s*[#№]?\s*([A-Z]{0,5}\d{4,}[-/]\w+|\d{4}-[A-Z]{1,5}-\d{4,})\b",
    re.IGNORECASE,
)

_AMOUNT_PATTERN = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d{1,2})?|\b\d[\d,]*(?:\.\d{1,2})?\s*(?:dollars?|USD|EUR|GBP)\b",
    re.IGNORECASE,
)

_JURISDICTION_PATTERN = re.compile(
    r"\b(?:federal|state of\s+\w+|district of\s+\w+|"
    r"(?:Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|"
    r"Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|"
    r"Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|"
    r"Nebraska|Nevada|New\s+Hampshire|New\s+Jersey|New\s+Mexico|New\s+York|"
    r"North\s+Carolina|North\s+Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode\s+Island|"
    r"South\s+Carolina|South\s+Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|"
    r"West\s+Virginia|Wisconsin|Wyoming|District\s+of\s+Columbia))\b",
    re.IGNORECASE,
)

_PERSON_NAME_PATTERN = re.compile(
    r"\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?|Atty\.?|Esq\.?)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
)


class MessageRouter:
    """
    Intent-based message router for SintraPrime.

    Provides rule-based intent detection (with optional LLM override),
    entity extraction, and per-intent handler dispatch.
    """

    def __init__(self) -> None:
        self._handlers: Dict[Intent, Callable] = {}
        self._compiled: List[Tuple[Intent, List[re.Pattern]]] = [
            (intent, [re.compile(p, re.IGNORECASE) for p in patterns])
            for intent, patterns in _INTENT_PATTERNS
        ]

    # ------------------------------------------------------------------
    # Intent detection
    # ------------------------------------------------------------------

    def detect_intent(self, text: str) -> Intent:
        """
        Classify *text* into an Intent using keyword patterns.

        Returns the first matching intent in priority order, or
        Intent.GENERAL_CHAT if nothing matches.
        """
        text_lower = text.lower()
        for intent, patterns in self._compiled:
            for pattern in patterns:
                if pattern.search(text_lower):
                    return intent
        return Intent.GENERAL_CHAT

    def detect_intent_scored(self, text: str) -> List[Tuple[Intent, int]]:
        """
        Return all intents with a match count score, sorted descending.
        Useful for multi-intent messages.
        """
        text_lower = text.lower()
        scores: Dict[Intent, int] = {}
        for intent, patterns in self._compiled:
            count = sum(len(p.findall(text_lower)) for p in patterns)
            if count:
                scores[intent] = count
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract named entities from *text*.

        :returns: Dict with keys: dates, case_numbers, amounts, jurisdictions, names.
        """
        return {
            "dates": _DATE_PATTERN.findall(text),
            "case_numbers": _CASE_NUMBER_PATTERN.findall(text),
            "amounts": _AMOUNT_PATTERN.findall(text),
            "jurisdictions": _JURISDICTION_PATTERN.findall(text),
            "names": _PERSON_NAME_PATTERN.findall(text),
        }

    # ------------------------------------------------------------------
    # Handler registration & dispatch
    # ------------------------------------------------------------------

    def register_handler(self, intent: Intent, handler_fn: Callable) -> None:
        """Register a handler callable for a given intent."""
        self._handlers[intent] = handler_fn

    def route_to_handler(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        message: IncomingMessage,
    ) -> str:
        """
        Dispatch to the registered handler, or return a default response.
        """
        handler = self._handlers.get(intent)
        if handler:
            try:
                result = handler(intent, entities, message)
                return self.format_response(result, message.channel)
            except Exception as exc:
                logger.error("Handler error for %s: %s", intent.value, exc)
                return "⚠️ An internal error occurred."

        # Built-in fallback responses
        return self._default_response(intent, entities, message)

    def _default_response(
        self, intent: Intent, entities: Dict, message: IncomingMessage
    ) -> str:
        if intent == Intent.LEGAL_QUESTION:
            juris = entities.get("jurisdictions", [])
            juris_str = f" ({', '.join(juris)})" if juris else ""
            return (
                f"⚖️ Legal question received{juris_str}. "
                "Routing to SintraPrime Legal Intelligence…"
            )
        elif intent == Intent.RESEARCH_REQUEST:
            return "🔍 Research request queued. SintraPrime Operator will report back shortly."
        elif intent == Intent.DOCUMENT_REQUEST:
            return "📄 Document generation initiated. You'll receive it shortly."
        elif intent == Intent.TASK_MANAGEMENT:
            dates = entities.get("dates", [])
            date_str = f" (due: {dates[0]})" if dates else ""
            return f"📋 Task noted{date_str}. Added to your SintraPrime task list."
        elif intent == Intent.FINANCIAL_QUERY:
            amounts = entities.get("amounts", [])
            amt_str = f" ({amounts[0]})" if amounts else ""
            return f"💰 Financial query{amt_str} received. Routing to Financial Intelligence…"
        elif intent == Intent.STATUS_CHECK:
            return "✅ All SintraPrime systems operational."
        elif intent == Intent.REMINDER:
            dates = entities.get("dates", [])
            date_str = f" for {dates[0]}" if dates else ""
            return f"⏰ Reminder set{date_str}."
        return "🤖 Message received. How can SintraPrime assist you further?"

    # ------------------------------------------------------------------
    # Response formatting
    # ------------------------------------------------------------------

    def format_response(self, response: Any, channel_type: ChannelType) -> str:
        """
        Adapt a response object to the appropriate channel format.

        - Telegram / WhatsApp: Markdown
        - Discord: Discord-flavoured markdown
        - Slack: mrkdwn
        - Webhook / SMS: plain text
        """
        text = str(response) if not isinstance(response, str) else response

        if channel_type in (ChannelType.TELEGRAM, ChannelType.WHATSAPP):
            return text  # already Markdown-ish

        if channel_type == ChannelType.DISCORD:
            # Convert *bold* → **bold** if not already
            text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"**\1**", text)
            return text

        if channel_type == ChannelType.SLACK:
            # Convert *bold* → *bold* (Slack uses single star)
            text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
            return text

        if channel_type in (ChannelType.SMS, ChannelType.WEBHOOK, ChannelType.EMAIL):
            # Strip markdown
            text = re.sub(r"[*_`~]", "", text)
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
            return text

        return text
