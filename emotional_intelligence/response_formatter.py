"""
Response Formatter — Client-facing response formatting for legal communications.
Breaks complex concepts into digestible parts, creates clear action items,
and adds timelines, plain English summaries, and reassuring disclaimers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ActionItem:
    step_number: int
    action: str
    responsible_party: str  # "you" | "attorney" | "court" | "SintraPrime"
    deadline: Optional[str] = None
    priority: str = "normal"  # "urgent" | "high" | "normal" | "low"
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "step": self.step_number,
            "action": self.action,
            "responsible_party": self.responsible_party,
            "deadline": self.deadline,
            "priority": self.priority,
            "notes": self.notes,
        }


@dataclass
class Deadline:
    description: str
    date: str
    consequence: str = ""
    days_remaining: Optional[int] = None


# ──────────────────────────────────────────────────────────────
# Reassuring disclaimer templates
# ──────────────────────────────────────────────────────────────

_DISCLAIMERS: Dict[str, str] = {
    "general": (
        "*This information is provided to help you understand your situation — it is not a substitute "
        "for formal legal advice. If your situation involves specific deadlines or significant legal risk, "
        "please consult a licensed attorney.*"
    ),
    "bankruptcy": (
        "*Bankruptcy law provides real protections designed to help people in your situation. "
        "This information gives you a starting framework — a qualified bankruptcy attorney can help "
        "identify the best path for your specific circumstances.*"
    ),
    "criminal": (
        "*Understanding your rights is important. This information is general in nature. "
        "If you are facing criminal charges, please consult a criminal defense attorney — "
        "you have the right to legal representation.*"
    ),
    "custody": (
        "*Family law decisions are made in the best interest of children. "
        "This information explains the process — your specific outcome will depend on your circumstances. "
        "A family law attorney can advocate for your interests.*"
    ),
    "eviction": (
        "*Tenants have legal rights throughout the eviction process. "
        "This information helps you understand those rights. "
        "Legal aid organizations may be able to assist you at low or no cost.*"
    ),
    "estate": (
        "*Estate matters can be emotionally and legally complex. "
        "This information provides general guidance. "
        "An estate attorney can ensure everything is handled correctly and in accordance with local law.*"
    ),
    "immigration": (
        "*Immigration law is complex and changes frequently. "
        "This information is general. Please consult an immigration attorney immediately "
        "if you have deadlines or enforcement concerns.*"
    ),
}

# Progress stage descriptions
_PROCESS_STAGES: Dict[str, List[str]] = {
    "litigation": [
        "Initial consultation and case evaluation",
        "Filing of complaint/petition",
        "Service of process on opposing party",
        "Discovery phase — exchange of evidence",
        "Pre-trial motions",
        "Trial or hearing",
        "Judgment/decision",
        "Appeal period (if applicable)",
        "Enforcement of judgment",
    ],
    "bankruptcy": [
        "Initial financial assessment",
        "Credit counseling (required)",
        "Filing of bankruptcy petition",
        "Automatic stay goes into effect — collectors must stop",
        "Meeting of creditors (341 meeting)",
        "Objection period for creditors",
        "Discharge (Chapter 7) or confirmation of repayment plan (Chapter 13)",
        "Case closure and fresh start",
    ],
    "eviction": [
        "Notice to vacate served",
        "Cure period (if applicable)",
        "Eviction lawsuit filed",
        "Court hearing scheduled",
        "Hearing — you can present your defense",
        "Judge's decision",
        "If eviction ordered: lockout date set",
        "Appeals available within strict deadlines",
    ],
    "divorce": [
        "Initial consultation and strategy",
        "Petition for dissolution filed",
        "Temporary orders (if needed) — for custody, support, residence",
        "Discovery — financial disclosure",
        "Negotiation and mediation",
        "Settlement agreement (if reached)",
        "Contested hearing (if no agreement)",
        "Final decree of dissolution",
        "Implementation — asset transfer, support orders",
    ],
}


class ResponseFormatter:
    """
    Formats legal responses for clients in a clear, compassionate,
    and actionable way.
    """

    def format_legal_advice(
        self,
        advice: str,
        tone: str = "empathetic",
        user_profile: Any = None,
    ) -> str:
        """
        Produces a complete, client-ready formatted response.
        tone options: 'empathetic', 'professional', 'urgent', 'reassuring'
        """
        name = self._get_name(user_profile)

        if tone == "urgent":
            header = f"⚠️ **Important — Action Required{', ' + name if name else ''}**\n\n"
        elif tone == "reassuring":
            header = f"💙 {'Hi ' + name + ', ' if name else ''}I want to make sure you have a clear picture of your situation.\n\n"
        elif tone == "empathetic":
            header = f"{'Hi ' + name + ',' + chr(10) + chr(10) if name else ''}"
        else:
            header = f"{'Dear ' + name + ',' + chr(10) + chr(10) if name else ''}"

        body = self.structure_explanation(advice)
        disclaimer = _DISCLAIMERS["general"]

        return f"{header}{body}\n\n---\n{disclaimer}"

    def structure_explanation(self, complex_concept: str) -> str:
        """Breaks a complex legal concept into digestible parts."""
        # Split on existing paragraph breaks
        paragraphs = [p.strip() for p in complex_concept.split("\n\n") if p.strip()]

        if len(paragraphs) <= 1:
            # Try to split on sentences for very long single paragraphs
            sentences = re.split(r"(?<=[.!?])\s+", complex_concept)
            if len(sentences) > 4:
                # Group into readable chunks
                chunks = []
                chunk = []
                for i, sent in enumerate(sentences):
                    chunk.append(sent)
                    if (i + 1) % 3 == 0 or i == len(sentences) - 1:
                        chunks.append(" ".join(chunk))
                        chunk = []
                return "\n\n".join(chunks)

        return "\n\n".join(paragraphs)

    def create_action_items(self, advice: str) -> List[ActionItem]:
        """Extracts and creates clear next steps from advice text."""
        action_items = []
        step_num = 1

        # Look for explicit action language
        action_patterns = [
            r"you (?:should|must|need to|have to) (.+?)(?:\.|;|$)",
            r"(?:please|remember to|make sure to) (.+?)(?:\.|;|$)",
            r"(?:file|submit|contact|gather|document|call|visit|sign|review|provide) (.+?)(?:\.|;|$)",
            r"(?:step \d+|first|second|third|next|then|finally)[,:]?\s+(.+?)(?:\.|;|$)",
        ]

        found_actions = set()
        for pattern in action_patterns:
            matches = re.findall(pattern, advice, re.IGNORECASE)
            for match in matches:
                action = match.strip().rstrip(".,;")
                if len(action) > 10 and action not in found_actions:
                    found_actions.add(action)
                    priority = "high" if any(
                        w in action.lower() for w in ["immediately", "urgent", "deadline", "today", "asap"]
                    ) else "normal"
                    action_items.append(
                        ActionItem(
                            step_number=step_num,
                            action=action.capitalize(),
                            responsible_party="you",
                            priority=priority,
                        )
                    )
                    step_num += 1

        # Fallback if no actions detected
        if not action_items:
            action_items = [
                ActionItem(
                    step_number=1,
                    action="Review the information provided and note any questions",
                    responsible_party="you",
                ),
                ActionItem(
                    step_number=2,
                    action="Gather any relevant documents",
                    responsible_party="you",
                ),
                ActionItem(
                    step_number=3,
                    action="Follow up with your attorney for case-specific guidance",
                    responsible_party="you",
                ),
            ]

        return action_items

    def add_timeline(self, advice: str, deadlines: List[Deadline]) -> str:
        """Adds a visual timeline section with deadlines."""
        if not deadlines:
            return advice

        timeline_lines = ["\n\n📅 **Important Dates & Deadlines**\n"]
        for deadline in sorted(deadlines, key=lambda d: d.date):
            days_note = ""
            if deadline.days_remaining is not None:
                if deadline.days_remaining <= 0:
                    days_note = " ⚠️ **PASSED**"
                elif deadline.days_remaining <= 3:
                    days_note = f" 🚨 **{deadline.days_remaining} day(s) remaining**"
                elif deadline.days_remaining <= 7:
                    days_note = f" ⚠️ {deadline.days_remaining} days remaining"
                else:
                    days_note = f" ({deadline.days_remaining} days)"

            line = f"• **{deadline.date}** — {deadline.description}{days_note}"
            if deadline.consequence:
                line += f"\n  *Consequence if missed: {deadline.consequence}*"
            timeline_lines.append(line)

        return advice + "\n".join(timeline_lines)

    def plain_english_summary(self, legal_document: str) -> str:
        """Creates an ELI5 (Explain Like I'm 5) summary of a legal document."""
        # Extract key concepts
        word_count = len(legal_document.split())

        header = "📋 **Plain English Summary**\n\n"

        if word_count < 50:
            return header + legal_document

        # Identify document type
        doc_lower = legal_document.lower()
        doc_type = "document"
        if "complaint" in doc_lower or "petition" in doc_lower:
            doc_type = "complaint/petition"
        elif "agreement" in doc_lower or "contract" in doc_lower:
            doc_type = "agreement"
        elif "order" in doc_lower and "court" in doc_lower:
            doc_type = "court order"
        elif "notice" in doc_lower:
            doc_type = "notice"

        # Extract sentences with key info
        sentences = re.split(r"(?<=[.!?])\s+", legal_document)
        important = [
            s for s in sentences
            if any(kw in s.lower() for kw in [
                "shall", "must", "required", "deadline", "date", "amount",
                "payment", "rights", "obligation", "you are", "you must",
                "you have", "the court", "ordered"
            ])
        ][:5]

        summary_body = (
            f"This is a **{doc_type}**. Here's what it means in plain English:\n\n"
        )

        if important:
            for i, sent in enumerate(important, 1):
                # Very basic simplification
                simplified = sent.strip()
                simplified = re.sub(r"\bhereinafter\b", "from now on", simplified, flags=re.IGNORECASE)
                simplified = re.sub(r"\bpursuant to\b", "under", simplified, flags=re.IGNORECASE)
                simplified = re.sub(r"\bwhereas\b", "given that", simplified, flags=re.IGNORECASE)
                summary_body += f"{i}. {simplified}\n\n"
        else:
            summary_body += (
                "This document contains legal language that relates to your matter. "
                "I recommend reviewing the key dates, amounts, and obligations with your attorney."
            )

        return header + summary_body

    def reassuring_disclaimer(self, topic: str) -> str:
        """Returns a non-panic disclaimer for the given topic."""
        return _DISCLAIMERS.get(topic, _DISCLAIMERS["general"])

    def progress_report(
        self,
        matter_id: str,
        current_stage: str = "",
        process_type: str = "litigation",
        completed_stages: Optional[List[str]] = None,
    ) -> str:
        """Generates a progress report showing where we are in the process."""
        stages = _PROCESS_STAGES.get(process_type, _PROCESS_STAGES["litigation"])
        completed = completed_stages or []

        lines = [f"📊 **Progress Report — Matter {matter_id}**\n"]
        lines.append(f"Process: {process_type.replace('_', ' ').title()}\n")

        for i, stage in enumerate(stages, 1):
            if stage in completed:
                indicator = "✅"
            elif stage == current_stage:
                indicator = "▶️ **(Current Stage)**"
            else:
                indicator = "⏳"
            lines.append(f"{indicator} Step {i}: {stage}")

        return "\n".join(lines)

    def format_action_items_as_text(self, action_items: List[ActionItem]) -> str:
        """Formats action items as a readable checklist."""
        lines = ["**Your Next Steps:**\n"]
        for item in action_items:
            priority_icon = "🚨" if item.priority == "urgent" else "📌" if item.priority == "high" else "•"
            line = f"{priority_icon} **Step {item.step_number}**: {item.action}"
            if item.deadline:
                line += f" *(by {item.deadline})*"
            if item.notes:
                line += f"\n  {item.notes}"
            lines.append(line)
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    def _get_name(self, user_profile: Any) -> Optional[str]:
        if user_profile is None:
            return None
        if hasattr(user_profile, "display_name"):
            return user_profile.display_name
        if hasattr(user_profile, "preferred_name") and user_profile.preferred_name:
            return user_profile.preferred_name
        if hasattr(user_profile, "first_name"):
            return user_profile.first_name
        if isinstance(user_profile, dict):
            return user_profile.get("preferred_name") or user_profile.get("first_name")
        return None
