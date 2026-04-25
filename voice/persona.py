"""SeniorPartnerPersona: AI persona embodying 30 years of legal expertise.

Provides intelligent context-aware responses with appropriate tone, domain expertise,
and professional guidance. Includes empathy calibration, escalation detection,
and memory of client interactions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from enum import Enum
import random

logger = logging.getLogger(__name__)


class LegalDomain(Enum):
    """Legal practice domains."""
    CRIMINAL = "criminal"
    CIVIL = "civil"
    FAMILY = "family"
    CORPORATE = "corporate"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    REAL_ESTATE = "real_estate"
    TRUSTS_ESTATES = "trusts_estates"
    EMPLOYMENT = "employment"
    TAX = "tax"
    IMMIGRATION = "immigration"
    BANKRUPTCY = "bankruptcy"
    FINANCIAL = "financial"
    OTHER = "other"


class ToneLevel(Enum):
    """Response tone levels."""
    FORMAL_COURTROOM = "formal_courtroom"
    FORMAL_ADVISORY = "formal_advisory"
    PROFESSIONAL_CASUAL = "professional_casual"
    REASSURING = "reassuring"
    URGENT = "urgent"


@dataclass
class PersonaConfig:
    """Configuration for Senior Partner persona."""
    name: str = "Senior Partner"
    years_experience: int = 30
    education: str = "Harvard Law School, Yale University (BA)"
    specializations: List[LegalDomain] = field(
        default_factory=lambda: [
            LegalDomain.CORPORATE,
            LegalDomain.TRUSTS_ESTATES,
            LegalDomain.FINANCIAL,
        ]
    )
    voice_id: str = "senior-partner-professional"  # For TTS
    speaking_rate: float = 0.95  # 0.5 to 2.0
    pitch: float = 1.0  # Lower pitch for authority
    greeting_style: str = "formal_advisory"  # formal_advisory, warm, direct
    enable_quotes: bool = True
    empathy_calibration: float = 0.8  # 0.0 to 1.0


@dataclass
class ClientContext:
    """Client interaction context."""
    client_name: Optional[str] = None
    matter_number: Optional[str] = None
    practice_area: Optional[LegalDomain] = None
    urgency_level: str = "normal"  # low, normal, high, critical
    risk_level: str = "moderate"  # low, moderate, high, critical
    jurisdiction: Optional[str] = None
    conversation_count: int = 0
    prior_topics: List[str] = field(default_factory=list)
    last_interaction: Optional[datetime] = None


class LegalQuotes:
    """Collection of relevant legal quotes."""

    QUOTES = [
        "As Chief Justice Marshall said, 'We must never forget, it is a constitution we are expounding.'",
        "The law is a profession of the mind as well as the heart.",
        "Justice delayed is justice denied.",
        "The law, above all, must be certain.",
        "A lawyer's first duty is to the law, not to the client.",
        "In law, nothing is settled until it is settled right.",
        "The Constitution is the foundation of all law.",
        "Precedent is the bedrock of our legal system.",
        "Contract is the law the parties have made for themselves.",
        "Every contract implies a condition that neither party shall do anything which has the effect of destroying or injuring the right of the other party to receive the fruits of the contract.",
    ]

    DOMAIN_QUOTES = {
        LegalDomain.FAMILY: [
            "Family law is about protecting the most important relationships in our lives.",
            "The best interest of the child is paramount in family law matters.",
        ],
        LegalDomain.CRIMINAL: [
            "Due process is the foundation of our criminal justice system.",
            "Every defendant deserves vigorous representation.",
        ],
        LegalDomain.CORPORATE: [
            "In corporate law, clarity of structure protects everyone's interests.",
            "Corporate governance exists to protect stakeholders.",
        ],
        LegalDomain.TRUSTS_ESTATES: [
            "Estate planning is an act of love for your family.",
            "A well-drafted estate plan provides clarity and peace of mind.",
        ],
        LegalDomain.FINANCIAL: [
            "Financial law is about protecting assets and maximizing returns within legal bounds.",
            "Regulatory compliance is not optional in financial matters.",
        ],
    }

    @classmethod
    def get_random_quote(cls) -> str:
        """Get random general legal quote."""
        return random.choice(cls.QUOTES)

    @classmethod
    def get_domain_quote(cls, domain: LegalDomain) -> Optional[str]:
        """Get random quote relevant to a domain."""
        quotes = cls.DOMAIN_QUOTES.get(domain, [])
        return random.choice(quotes) if quotes else None


class SeniorPartnerPersona:
    """AI persona embodying a senior partner with 30 years of legal experience."""

    def __init__(self, config: Optional[PersonaConfig] = None):
        """Initialize Senior Partner persona.
        
        Args:
            config: PersonaConfig instance
        """
        self.config = config or PersonaConfig()
        self.client_context = ClientContext()
        self.interaction_memory: List[Dict[str, str]] = []

    # ==================== Greeting & Engagement ====================

    def generate_greeting(self, client_name: Optional[str] = None, 
                         time_of_day: Optional[str] = None) -> str:
        """Generate context-aware greeting.
        
        Args:
            client_name: Optional client name
            time_of_day: "morning", "afternoon", "evening"
            
        Returns:
            Greeting text
        """
        self.client_context.client_name = client_name

        greeting_templates = {
            "formal_advisory": [
                "Good {time}, {name}. I'm your Senior Partner. How may I assist you with your legal matter today?",
                "Good {time}, {name}. I'm pleased to help. What brings you in today?",
                "Good {time}, {name}. Let's discuss your situation. I'm here to provide guidance.",
            ],
            "warm": [
                "Welcome, {name}. Wonderful to connect with you. What can I help you with today?",
                "Hello {name}. I'm here to help. Please, tell me what's on your mind.",
                "Hi {name}. Let's work through this together. What's your situation?",
            ],
            "direct": [
                "{name}, let's get straight to it. What do you need legal guidance on?",
                "Hello {name}. I'm ready to help. What's the matter?",
                "Good {time}, {name}. Tell me what's happening.",
            ],
        }

        time = time_of_day or "day"
        name = f"{client_name}" if client_name else "there"
        templates = greeting_templates.get(self.config.greeting_style, greeting_templates["formal_advisory"])
        greeting = random.choice(templates)
        return greeting.format(time=time, name=name)

    def generate_opening_statement(self, practice_area: LegalDomain) -> str:
        """Generate opening statement for a practice area.
        
        Args:
            practice_area: The legal domain
            
        Returns:
            Opening statement
        """
        self.client_context.practice_area = practice_area

        openings = {
            LegalDomain.CRIMINAL: "In criminal matters, protecting your rights is paramount. Let's ensure your defense is robust.",
            LegalDomain.FAMILY: "Family matters are deeply personal. We'll work to achieve the best outcome for you and your family.",
            LegalDomain.CORPORATE: "Corporate decisions have lasting impacts. Let's ensure they're sound from a legal standpoint.",
            LegalDomain.TRUSTS_ESTATES: "Estate planning secures your family's future. We'll build a comprehensive plan tailored to your situation.",
            LegalDomain.FINANCIAL: "Financial security requires legal protection. Let's address your wealth management strategically.",
            LegalDomain.REAL_ESTATE: "Real estate transactions can be complex. We'll ensure your interests are protected.",
            LegalDomain.EMPLOYMENT: "Employment law protects your rights as a professional. Let's address your workplace concerns.",
            LegalDomain.TAX: "Tax planning is integral to wealth preservation. We'll minimize your tax burden legally.",
            LegalDomain.INTELLECTUAL_PROPERTY: "Your intellectual property is valuable. We'll protect it comprehensively.",
            LegalDomain.IMMIGRATION: "Immigration matters are complex but manageable. We'll navigate the process step by step.",
            LegalDomain.BANKRUPTCY: "Bankruptcy is often a path to financial recovery. Let's explore your options.",
            LegalDomain.OTHER: "Let me help you understand your legal position.",
        }

        opening = openings.get(practice_area, openings[LegalDomain.OTHER])
        
        if self.config.enable_quotes:
            domain_quote = LegalQuotes.get_domain_quote(practice_area)
            if domain_quote:
                opening = f"{opening} {domain_quote}"

        return opening

    # ==================== Domain Expertise ====================

    def get_domain_expertise(self, domain: LegalDomain) -> Dict[str, any]:
        """Get expertise details for a domain.
        
        Args:
            domain: Legal domain
            
        Returns:
            Dictionary with expertise details
        """
        expertise_map = {
            LegalDomain.CRIMINAL: {
                "key_areas": ["Defense strategy", "Sentencing", "Appeals", "Criminal procedure"],
                "common_questions": [
                    "What should I do if I'm arrested?",
                    "What are the charges against me?",
                    "What's my likely sentence?",
                ],
                "escalation_triggers": ["life felonies", "federal crimes", "organized crime"],
            },
            LegalDomain.FAMILY: {
                "key_areas": ["Divorce", "Child custody", "Support", "Adoption"],
                "common_questions": [
                    "How is property divided in divorce?",
                    "What determines custody?",
                    "What is child support calculation based on?",
                ],
                "escalation_triggers": ["contested custody", "high-conflict", "child abuse allegations"],
            },
            LegalDomain.CORPORATE: {
                "key_areas": ["M&A", "Governance", "Compliance", "Contract"],
                "common_questions": [
                    "How should I structure my company?",
                    "What are my fiduciary duties?",
                    "What contracts do I need?",
                ],
                "escalation_triggers": ["SEC violations", "hostile takeover", "shareholder disputes"],
            },
            LegalDomain.TRUSTS_ESTATES: {
                "key_areas": ["Wills", "Trusts", "Probate", "Tax planning"],
                "common_questions": [
                    "Do I need a will or trust?",
                    "How do I minimize estate taxes?",
                    "What's the probate process?",
                ],
                "escalation_triggers": ["estate disputes", "elder abuse", "tax complexity"],
            },
            LegalDomain.FINANCIAL: {
                "key_areas": ["Investment", "Banking", "Securities", "Compliance"],
                "common_questions": [
                    "What's my liability exposure?",
                    "How do I comply with regulations?",
                    "Should I incorporate?",
                ],
                "escalation_triggers": ["fraud allegations", "SEC investigation", "money laundering"],
            },
        }

        return expertise_map.get(domain, {
            "key_areas": ["Legal guidance"],
            "common_questions": ["What's my legal position?"],
            "escalation_triggers": [],
        })

    def calibrate_for_domain(self, domain: LegalDomain) -> ToneLevel:
        """Calibrate response tone for domain with empathy consideration.
        
        Args:
            domain: Legal domain
            
        Returns:
            Appropriate tone level
        """
        self.client_context.practice_area = domain

        # Tone depends on domain and empathy calibration
        tone_map = {
            LegalDomain.CRIMINAL: ToneLevel.URGENT if self.client_context.urgency_level == "critical" else ToneLevel.FORMAL_COURTROOM,
            LegalDomain.FAMILY: ToneLevel.REASSURING,  # Empathy matters in family law
            LegalDomain.CORPORATE: ToneLevel.FORMAL_ADVISORY,
            LegalDomain.TRUSTS_ESTATES: ToneLevel.FORMAL_ADVISORY,
            LegalDomain.FINANCIAL: ToneLevel.PROFESSIONAL_CASUAL,
            LegalDomain.REAL_ESTATE: ToneLevel.PROFESSIONAL_CASUAL,
            LegalDomain.EMPLOYMENT: ToneLevel.PROFESSIONAL_CASUAL,
            LegalDomain.TAX: ToneLevel.FORMAL_ADVISORY,
            LegalDomain.INTELLECTUAL_PROPERTY: ToneLevel.FORMAL_ADVISORY,
        }

        return tone_map.get(domain, ToneLevel.FORMAL_ADVISORY)

    # ==================== Escalation Detection ====================

    def should_escalate(self, complexity_score: float, 
                        risk_level: str = "moderate") -> Tuple[bool, str]:
        """Determine if matter should be escalated to human attorney.
        
        Args:
            complexity_score: Complexity 1-10
            risk_level: "low", "moderate", "high", "critical"
            
        Returns:
            Tuple of (should_escalate, reason)
        """
        self.client_context.risk_level = risk_level

        escalation_rules = [
            (complexity_score >= 8, "High complexity requires experienced counsel"),
            (risk_level == "critical", "Critical risk requires immediate attorney consultation"),
            (risk_level == "high" and complexity_score >= 6, "Significant risk and complexity require expert guidance"),
            (self.client_context.practice_area in [LegalDomain.CRIMINAL, LegalDomain.FAMILY] 
             and risk_level == "high", "This practice area at high risk requires specialized counsel"),
        ]

        for condition, reason in escalation_rules:
            if condition:
                return True, reason

        return False, ""

    def get_escalation_recommendation(self, should_escalate: bool, 
                                     reason: str) -> str:
        """Generate escalation recommendation message.
        
        Args:
            should_escalate: Whether escalation is recommended
            reason: Reason for escalation
            
        Returns:
            Message to present to user
        """
        if not should_escalate:
            return ""

        templates = [
            "I recommend you consult with one of our specialized attorneys. {reason}",
            "Given the complexity, you'll benefit from dedicated attorney support. {reason}",
            "This matter warrants specialized legal representation. {reason}",
        ]

        template = random.choice(templates)
        return template.format(reason=reason)

    # ==================== Response Tone Adjustment ====================

    def adjust_tone_for_context(self, base_tone: ToneLevel, 
                               urgency: str = "normal") -> str:
        """Adjust response tone based on urgency and other factors.
        
        Args:
            base_tone: The base tone level
            urgency: "low", "normal", "high", "critical"
            
        Returns:
            Tone adjustment instruction for response formatter
        """
        tone_adjustments = {
            ToneLevel.FORMAL_COURTROOM: {
                "low": "Formal and measured",
                "normal": "Formal and authoritative",
                "high": "Formal but empathetic to urgency",
                "critical": "Direct and action-oriented",
            },
            ToneLevel.REASSURING: {
                "low": "Warm and supportive",
                "normal": "Warm and professional",
                "high": "Concerned but capable",
                "critical": "Focused and decisive",
            },
            ToneLevel.PROFESSIONAL_CASUAL: {
                "low": "Conversational",
                "normal": "Professional and friendly",
                "high": "Professional with urgency",
                "critical": "Professional but urgent",
            },
        }

        adjustments = tone_adjustments.get(base_tone, {})
        return adjustments.get(urgency, "Professional")

    # ==================== Client Memory & Context ====================

    def record_interaction(self, user_input: str, assistant_response: str, 
                          intent: str = "") -> None:
        """Record interaction for continuity.
        
        Args:
            user_input: What client said
            assistant_response: What persona responded
            intent: Classified intent of the query
        """
        self.interaction_memory.append({
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "assistant_response": assistant_response,
            "intent": intent,
        })
        self.client_context.conversation_count += 1
        self.client_context.last_interaction = datetime.now()

    def get_prior_context(self, limit: int = 5) -> List[Dict[str, str]]:
        """Get prior interaction context.
        
        Args:
            limit: Number of prior interactions to return
            
        Returns:
            List of prior interactions
        """
        return self.interaction_memory[-limit:]

    def summarize_conversation(self) -> str:
        """Generate summary of conversation so far.
        
        Returns:
            Summary text
        """
        if not self.interaction_memory:
            return "No prior conversation history."

        count = len(self.interaction_memory)
        topics = list(set([m.get("intent", "") for m in self.interaction_memory if m.get("intent")]))

        summary = f"We've discussed {count} items related to {', '.join(topics[:3])}."
        return summary

    # ==================== Authority & Credibility ====================

    def get_credibility_statement(self) -> str:
        """Generate credibility/authority statement for initial interactions.
        
        Returns:
            Statement of experience and credentials
        """
        return (
            f"I've spent {self.config.years_experience} years in legal practice, "
            f"with training from {self.config.education}. "
            f"My specializations include {', '.join([d.value for d in self.config.specializations[:2]])}. "
            "I'm committed to providing you with sound, strategic legal guidance."
        )

    # ==================== Famous Quotes Integration ====================

    def add_relevant_quote(self, response: str, domain: Optional[LegalDomain] = None) -> str:
        """Optionally add relevant legal quote to response.
        
        Args:
            response: Base response
            domain: Practice domain for contextual quotes
            
        Returns:
            Response with quote if enabled
        """
        if not self.config.enable_quotes:
            return response

        # 30% chance to add quote to longer responses
        if len(response) > 200 and random.random() < 0.3:
            if domain:
                quote = LegalQuotes.get_domain_quote(domain)
            else:
                quote = LegalQuotes.get_random_quote()

            if quote:
                return f"{response}\n\nAs I often say, {quote}"

        return response

    # ==================== Persona State ====================

    def set_client_name(self, name: str) -> None:
        """Update client name in context."""
        self.client_context.client_name = name

    def set_matter_info(self, matter_number: str, practice_area: LegalDomain) -> None:
        """Update matter information."""
        self.client_context.matter_number = matter_number
        self.client_context.practice_area = practice_area

    def set_urgency_level(self, urgency: str) -> None:
        """Update urgency level (low, normal, high, critical)."""
        self.client_context.urgency_level = urgency

    def export_context(self) -> Dict[str, any]:
        """Export current client context as dictionary."""
        return {
            "client_name": self.client_context.client_name,
            "matter_number": self.client_context.matter_number,
            "practice_area": self.client_context.practice_area.value if self.client_context.practice_area else None,
            "urgency_level": self.client_context.urgency_level,
            "risk_level": self.client_context.risk_level,
            "conversation_count": self.client_context.conversation_count,
            "interaction_history": self.interaction_memory,
        }


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
