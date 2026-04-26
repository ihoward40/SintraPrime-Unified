"""
Contract Reviewer Skill

Extracts key terms, obligations, risk flags, and metadata from contract text.
Identifies parties, effective dates, payment terms, termination clauses, and more.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..skill_types import SkillCategory, SkillTemplate


# ---------------------------------------------------------------------------
# Risk flag patterns
# ---------------------------------------------------------------------------

RISK_PATTERNS: List[Tuple[str, str, str]] = [
    # (pattern, flag_name, severity)
    (r"unlimited liability", "Unlimited Liability", "high"),
    (r"indemnif\w+\s+all\s+claims", "Broad Indemnification", "high"),
    (r"perpetual\s+license|irrevocable\s+license", "Perpetual/Irrevocable License", "medium"),
    (r"automatic\s+renewal|auto-renew", "Auto-Renewal Clause", "medium"),
    (r"liquidated\s+damages", "Liquidated Damages", "medium"),
    (r"non-compete|non\s+compete", "Non-Compete Clause", "medium"),
    (r"waiver\s+of\s+jury\s+trial", "Jury Trial Waiver", "high"),
    (r"mandatory\s+arbitration|binding\s+arbitration", "Mandatory Arbitration", "medium"),
    (r"unilateral\s+(right|ability)\s+to\s+(amend|modify|change)", "Unilateral Modification Right", "high"),
    (r"sole\s+discretion", "Sole Discretion Clause", "low"),
    (r"consequential\s+damages\s+waiver|waiver\s+of\s+consequential", "Consequential Damages Waiver", "medium"),
    (r"intellectual\s+property\s+assignment|ip\s+assignment", "IP Assignment", "medium"),
    (r"exclusivity|exclusive\s+agreement", "Exclusivity Clause", "low"),
]

# Party identification patterns
PARTY_PATTERNS = [
    r'(?:between|by and between)\s+"?([A-Z][^"]+?)"?\s+(?:\("?\w+"?\))?\s+and\s+"?([A-Z][^"]+?)"?',
    r'(?:BETWEEN|BY AND BETWEEN)\s+([A-Z][A-Z\s,\.]+?)\s+AND\s+([A-Z][A-Z\s,\.]+?)\n',
]

# Date patterns
DATE_PATTERNS = [
    r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
    r'\bas\s+of\s+([A-Z][a-z]+ \d{1,2},? \d{4})',
]


class ContractReviewerSkill(SkillTemplate):
    """Extracts key terms, obligations, and risk flags from contract text."""

    @property
    def skill_id(self) -> str:
        return "builtin_contract_reviewer"

    @property
    def name(self) -> str:
        return "contract_reviewer"

    @property
    def description(self) -> str:
        return "Extracts key terms, obligations, risk flags, and metadata from contract text."

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.LEGAL

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "contract_text": {"type": "str", "required": True, "description": "Full contract text"},
            "focus_areas": {
                "type": "list",
                "required": False,
                "default": [],
                "description": "Optional list of specific areas to focus on",
            },
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Perform a comprehensive review of the contract text."""
        contract_text = kwargs.get("contract_text", "")
        focus_areas = kwargs.get("focus_areas", [])

        if not contract_text:
            return {"error": "contract_text is required", "success": False}

        return {
            "parties": self.extract_parties(contract_text),
            "dates": self.extract_dates(contract_text),
            "risk_flags": self.identify_risk_flags(contract_text),
            "payment_terms": self.extract_payment_terms(contract_text),
            "termination_clauses": self.extract_termination(contract_text),
            "governing_law": self.extract_governing_law(contract_text),
            "key_obligations": self.extract_obligations(contract_text),
            "summary": self.generate_summary(contract_text),
            "word_count": len(contract_text.split()),
            "reviewed_at": datetime.utcnow().isoformat(),
            "success": True,
        }

    def extract_parties(self, text: str) -> List[str]:
        parties = []
        for pattern in PARTY_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    parties.extend([m.strip() for m in match if m.strip()])
                else:
                    parties.append(match.strip())
        # Also look for defined terms like ("Company") or ("Client")
        defined = re.findall(r'"([A-Z][^"]{1,50})"\s*\(the\s*"(\w+)"\)', text)
        for full_name, short_name in defined:
            parties.append(f"{full_name.strip()} ('{short_name}')")
        return list(dict.fromkeys(parties))[:10]  # Deduplicate, limit 10

    def extract_dates(self, text: str) -> Dict[str, List[str]]:
        all_dates = []
        for pattern in DATE_PATTERNS:
            found = re.findall(pattern, text)
            all_dates.extend(found if isinstance(found[0], str) else [" ".join(f) for f in found] if found else [])

        # Separate effective date
        effective = re.findall(
            r'(?:effective|made and entered into)\s+(?:as of\s+)?([A-Z][a-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            text, re.IGNORECASE
        )

        return {
            "effective_date": effective[0] if effective else None,
            "all_dates_found": list(dict.fromkeys(all_dates))[:10],
        }

    def identify_risk_flags(self, text: str) -> List[Dict[str, str]]:
        flags = []
        text_lower = text.lower()
        for pattern, flag_name, severity in RISK_PATTERNS:
            if re.search(pattern, text_lower):
                flags.append({"flag": flag_name, "severity": severity})
        return flags

    def extract_payment_terms(self, text: str) -> Dict[str, Any]:
        amount_pattern = r'\$\s*[\d,]+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*(?:USD|dollars?)'
        amounts = re.findall(amount_pattern, text, re.IGNORECASE)

        net_terms = re.findall(r'net\s*(\d+)', text, re.IGNORECASE)
        due_on = re.findall(r'(?:due|payable)\s+(?:on|within|by)\s+([^\.]{5,50})', text, re.IGNORECASE)

        return {
            "amounts_mentioned": amounts[:5],
            "payment_terms_net": [f"Net {d}" for d in net_terms[:3]],
            "due_date_language": [d.strip() for d in due_on[:3]],
        }

    def extract_termination(self, text: str) -> List[str]:
        termination_sections = re.findall(
            r'(?:termination|cancellation)[^\n]*\n(?:[^\n]+\n){0,5}',
            text, re.IGNORECASE
        )
        clauses = []
        for section in termination_sections[:3]:
            clean = " ".join(section.split())[:300]
            clauses.append(clean)
        return clauses

    def extract_governing_law(self, text: str) -> Optional[str]:
        patterns = [
            r'governed by\s+(?:the\s+)?laws?\s+of\s+(?:the\s+)?(?:State\s+of\s+)?([A-Z][a-zA-Z\s]{2,30})',
            r'jurisdiction\s+(?:of|in)\s+([A-Z][a-zA-Z\s]{2,30})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def extract_obligations(self, text: str) -> List[str]:
        """Extract SHALL/MUST obligation sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        obligations = []
        for sentence in sentences:
            if re.search(r'\b(shall|must|agrees?\s+to|is\s+required\s+to)\b', sentence, re.IGNORECASE):
                clean = " ".join(sentence.split())[:200]
                obligations.append(clean)
        return obligations[:10]

    def generate_summary(self, text: str) -> str:
        """Generate a brief summary of the contract."""
        parties = self.extract_parties(text)
        governing = self.extract_governing_law(text)
        flags = self.identify_risk_flags(text)
        word_count = len(text.split())

        party_str = " and ".join(parties[:2]) if parties else "Unidentified parties"
        gov_str = f" Governed by {governing} law." if governing else ""
        risk_str = f" {len(flags)} risk flag(s) identified." if flags else " No major risk flags detected."

        return (
            f"Contract between {party_str} ({word_count} words).{gov_str}{risk_str}"
        )
