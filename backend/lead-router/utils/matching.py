"""
AI Matching Algorithm for Lead Routing.
Scores leads on legal, financial, and urgency dimensions.
"""

import re
from typing import Tuple
from models.lead import IntakeData, AgentType, RoutingResult


# Keyword dictionaries for scoring
LEGAL_KEYWORDS = {
    "high": [
        "trust", "estate", "will", "probate", "guardianship", "power of attorney",
        "business formation", "llc", "corporation", "partnership", "contract",
        "litigation", "lawsuit", "dispute", "liability", "asset protection",
        "inheritance", "succession", "testamentary", "fiduciary", "beneficiary",
        "copyright", "trademark", "patent", "intellectual property", "nda",
        "divorce", "custody", "adoption", "family law", "prenup",
        "real estate", "property", "deed", "mortgage", "title",
    ],
    "medium": [
        "legal", "attorney", "lawyer", "compliance", "regulatory", "license",
        "insurance", "liability", "protection", "agreement", "negotiation",
        "structure", "planning", "strategy", "risk", "obligation",
    ],
}

FINANCIAL_KEYWORDS = {
    "high": [
        "debt", "credit card", "loan", "bankruptcy", "foreclosure", "collection",
        "credit score", "credit report", "defaulted", "late payments",
        "asset allocation", "investment", "portfolio", "stock", "bond",
        "tax", "irs", "deduction", "capital gains", "w2", "1099",
        "payroll", "business income", "revenue", "cash flow", "accounting",
        "restructuring", "consolidation", "refinance", "payment plan",
        "retirement", "401k", "ira", "pension", "social security",
        "inheritance", "wealth", "net worth", "savings", "budgeting",
    ],
    "medium": [
        "financial", "money", "income", "expense", "budget", "savings",
        "investment", "planning", "growth", "strategy", "analysis",
        "credit", "loan", "mortgage", "interest", "payment", "rate",
        "wealth", "asset", "liability", "account", "transfer",
    ],
}

URGENCY_KEYWORDS = {
    "high": [
        "immediately", "urgent", "emergency", "critical", "asap", "crisis",
        "today", "this week", "deadline", "court date", "imminent",
        "foreclosure", "eviction", "lawsuit", "irs action", "collection",
        "default", "late", "overdue", "at risk", "threatened",
        "immediately action", "now", "urgent need",
    ],
    "medium": [
        "soon", "soon as possible", "quickly", "important", "time sensitive",
        "this month", "within weeks", "coming up", "approaching",
    ],
}


def extract_keywords(text: str) -> list[str]:
    """Extract and normalize keywords from text."""
    if not text:
        return []
    
    # Normalize to lowercase and split into words/phrases
    text_lower = text.lower()
    keywords = []
    
    # Check all keyword sets
    for keyword_dict in [LEGAL_KEYWORDS, FINANCIAL_KEYWORDS, URGENCY_KEYWORDS]:
        for intensity, words in keyword_dict.items():
            for word in words:
                # Use word boundaries for exact matching
                pattern = r"\b" + re.escape(word) + r"\b"
                if re.search(pattern, text_lower):
                    keywords.append(word)
    
    return list(set(keywords))  # Remove duplicates


def calculate_legal_score(intake: IntakeData) -> float:
    """
    Calculate legal relevance score (0-100).
    
    Factors:
    - Presence of legal keywords in legal_situation
    - Presence of legal keywords in goals
    - Mention of business/entity structure
    """
    score = 0
    
    # Text analysis
    legal_text = (intake.legal_situation or "") + " " + (intake.goals or "")
    
    # Count legal keywords
    for keyword in LEGAL_KEYWORDS["high"]:
        if keyword in legal_text.lower():
            score += 15
    
    for keyword in LEGAL_KEYWORDS["medium"]:
        if keyword in legal_text.lower():
            score += 5
    
    # Business/entity signals
    if intake.company_name or intake.industry:
        score += 10
    
    # Check if provided keywords match
    if intake.legal_keywords:
        score += len(intake.legal_keywords) * 3
    
    # Cap at 100
    return min(100, score)


def calculate_financial_score(intake: IntakeData) -> float:
    """
    Calculate financial relevance score (0-100).
    
    Factors:
    - Presence of financial keywords in financial_snapshot
    - Presence of financial keywords in goals
    - Asset/debt mentions
    """
    score = 0
    
    # Text analysis
    financial_text = (intake.financial_snapshot or "") + " " + (intake.goals or "")
    
    # Count financial keywords
    for keyword in FINANCIAL_KEYWORDS["high"]:
        if keyword in financial_text.lower():
            score += 15
    
    for keyword in FINANCIAL_KEYWORDS["medium"]:
        if keyword in financial_text.lower():
            score += 5
    
    # Check if provided keywords match
    if intake.financial_keywords:
        score += len(intake.financial_keywords) * 3
    
    # Cap at 100
    return min(100, score)


def calculate_urgency_score(intake: IntakeData) -> float:
    """
    Calculate urgency/timeline score (0-100).
    
    Factors:
    - Timeline mentions (immediate, soon, etc.)
    - Crisis keywords (foreclosure, lawsuit, etc.)
    - Urgency signals in text
    """
    score = 0
    
    # Analyze all text
    all_text = (
        intake.legal_situation + " " +
        intake.financial_snapshot + " " +
        intake.goals + " " +
        (intake.timeline or "")
    ).lower()
    
    # High urgency keywords
    for keyword in URGENCY_KEYWORDS["high"]:
        if keyword in all_text:
            score += 20
    
    # Medium urgency keywords
    for keyword in URGENCY_KEYWORDS["medium"]:
        if keyword in all_text:
            score += 10
    
    # Timeline analysis
    if intake.timeline:
        if "immediate" in intake.timeline.lower() or "today" in intake.timeline.lower():
            score += 30
        elif "week" in intake.timeline.lower():
            score += 20
        elif "month" in intake.timeline.lower():
            score += 10
    
    # Cap at 100
    return min(100, score)


def route_lead(intake: IntakeData) -> RoutingResult:
    """
    Main routing algorithm.
    Determines best agent specialization based on scoring.
    
    Algorithm:
    if legal_score > 70 AND financial_score < 40:
        → legal-specialist (Zero)
    elif financial_score > 70 AND legal_score < 40:
        → financial-specialist (Sigma)
    elif legal_score > 50 AND financial_score > 50:
        → combined-specialist (Nova)
    else:
        → general-inquiry (manual review)
    """
    # Calculate dimension scores
    legal_score = calculate_legal_score(intake)
    financial_score = calculate_financial_score(intake)
    urgency_score = calculate_urgency_score(intake)
    
    # Determine assigned agent
    if legal_score > 70 and financial_score < 40:
        assigned_agent = AgentType.LEGAL_SPECIALIST
        confidence = min(100, legal_score + urgency_score * 0.2)
        reasoning = f"Strong legal focus (legal_score: {legal_score}). Recommend legal specialist (Zero)."
    
    elif financial_score > 70 and legal_score < 40:
        assigned_agent = AgentType.FINANCIAL_SPECIALIST
        confidence = min(100, financial_score + urgency_score * 0.2)
        reasoning = f"Strong financial focus (financial_score: {financial_score}). Recommend financial specialist (Sigma)."
    
    elif legal_score > 50 and financial_score > 50:
        assigned_agent = AgentType.COMBINED_SPECIALIST
        confidence = min(100, (legal_score + financial_score) / 2 + urgency_score * 0.1)
        reasoning = f"Balanced legal/financial needs (legal: {legal_score}, financial: {financial_score}). Recommend hybrid specialist (Nova)."
    
    else:
        assigned_agent = AgentType.GENERAL_INQUIRY
        confidence = max(legal_score, financial_score)
        reasoning = f"General inquiry requiring manual review (legal: {legal_score}, financial: {financial_score})."
    
    # Boost confidence based on urgency
    if urgency_score > 70:
        confidence = min(100, confidence + 10)
        reasoning += f" Urgent: {urgency_score} urgency score."
    
    return RoutingResult(
        assigned_agent=assigned_agent,
        legal_score=legal_score,
        financial_score=financial_score,
        urgency_score=urgency_score,
        confidence=round(confidence, 2),
        reasoning=reasoning,
    )


def calculate_qualification_score(
    legal_score: float,
    financial_score: float,
    urgency_score: float,
) -> float:
    """
    Calculate overall lead quality/qualification score.
    High scores = qualified leads, low scores = low-quality leads.
    """
    # Weight components
    weighted_score = (
        legal_score * 0.35 +
        financial_score * 0.35 +
        urgency_score * 0.30
    )
    
    return round(weighted_score, 2)


def get_agent_display_name(agent_type: AgentType) -> str:
    """Get human-readable name for agent type."""
    names = {
        AgentType.LEGAL_SPECIALIST: "Zero (Legal Specialist)",
        AgentType.FINANCIAL_SPECIALIST: "Sigma (Financial Specialist)",
        AgentType.COMBINED_SPECIALIST: "Nova (Combined Specialist)",
        AgentType.GENERAL_INQUIRY: "General Inquiry Queue",
    }
    return names.get(agent_type, str(agent_type))
