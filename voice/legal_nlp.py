"""LegalNLPProcessor: Intent classification, entity extraction, and legal analysis.

Identifies user intent from queries (25+ legal intents), extracts named entities
(names, dates, amounts, case numbers, statutes), scores complexity, identifies
urgency, and classifies practice areas.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class Intent(Enum):
    """Legal/financial intents."""
    # Criminal
    DEFENSE_ADVICE = "defense_advice"
    EXPLAIN_CHARGES = "explain_charges"
    BAIL_BOND = "bail_bond"
    PLEA_AGREEMENT = "plea_agreement"
    SENTENCING = "sentencing"
    APPEAL = "appeal"
    
    # Civil/Litigation
    DRAFT_COMPLAINT = "draft_complaint"
    NEGOTIATE_SETTLEMENT = "negotiate_settlement"
    DISCOVERY_REQUEST = "discovery_request"
    DEPOSITION_PREP = "deposition_prep"
    
    # Contract/Corporate
    REVIEW_CONTRACT = "review_contract"
    DRAFT_MOTION = "draft_motion"
    CORPORATE_SETUP = "corporate_setup"
    MERGER_ACQUISITION = "merger_acquisition"
    
    # Family Law
    DIVORCE_GUIDANCE = "divorce_guidance"
    CUSTODY_DETERMINATION = "custody_determination"
    CHILD_SUPPORT = "child_support"
    SPOUSAL_SUPPORT = "spousal_support"
    ADOPTION = "adoption"
    
    # Estate Planning
    WILL_CREATION = "will_creation"
    TRUST_SETUP = "trust_setup"
    PROBATE_GUIDANCE = "probate_guidance"
    ESTATE_TAX_PLANNING = "estate_tax_planning"
    
    # Financial
    DEBT_MANAGEMENT = "debt_management"
    CREDIT_REPAIR = "credit_repair"
    BANKRUPTCY_OPTIONS = "bankruptcy_options"
    INVESTMENT_COMPLIANCE = "investment_compliance"
    
    # General
    LEGAL_RESEARCH = "legal_research"
    STATUTE_EXPLANATION = "statute_explanation"
    CASE_LAW_RESEARCH = "case_law_research"
    URGENT_HELP = "urgent_help"
    GENERAL_INQUIRY = "general_inquiry"


class PracticeArea(Enum):
    """Legal practice areas."""
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
    LITIGATION = "litigation"
    OTHER = "other"


class EntityType(Enum):
    """Named entity types in legal context."""
    PERSON = "person"
    ORGANIZATION = "organization"
    DATE = "date"
    DOLLAR_AMOUNT = "dollar_amount"
    CASE_NUMBER = "case_number"
    STATUTE = "statute"
    COURT = "court"
    LOCATION = "location"
    CASE_NAME = "case_name"
    TIME_REFERENCE = "time_reference"


@dataclass
class Entity:
    """Named entity extracted from text."""
    text: str
    entity_type: EntityType
    start_pos: int
    end_pos: int
    confidence: float = 0.8
    normalized_value: Optional[str] = None


@dataclass
class IntentResult:
    """Result of intent classification."""
    primary_intent: Intent
    secondary_intents: List[Intent] = field(default_factory=list)
    confidence: float = 0.0
    practice_area: PracticeArea = PracticeArea.OTHER


@dataclass
class NLPResult:
    """Complete NLP processing result."""
    original_text: str
    intent: IntentResult
    entities: List[Entity] = field(default_factory=list)
    complexity_score: float = 5.0  # 1-10 scale
    practice_area: PracticeArea = PracticeArea.OTHER
    urgency_level: str = "normal"  # low, normal, high, critical
    jurisdiction: Optional[str] = None
    has_legal_questions: bool = False
    has_financial_questions: bool = False
    key_phrases: List[str] = field(default_factory=list)


class IntentClassifier:
    """Classifies user intent from text."""

    # Keyword patterns for each intent
    INTENT_PATTERNS = {
        Intent.DEFENSE_ADVICE: [
            r"arrest", r"charged", r"facing charges", r"police", r"defend",
            r"defense", r"criminal", r"lawyer need", r"legal help",
        ],
        Intent.EXPLAIN_CHARGES: [
            r"what.*charges", r"what.*count", r"felony.*or.*misdemeanor",
            r"what.*crime", r"explain.*charge",
        ],
        Intent.BAIL_BOND: [
            r"bail", r"bond", r"release.*custody", r"pending trial",
        ],
        Intent.PLEA_AGREEMENT: [
            r"plea.*deal", r"negotiate.*plea", r"guilty.*plea",
        ],
        Intent.SENTENCING: [
            r"sentence", r"prison.*time", r"probation", r"parole",
        ],
        Intent.APPEAL: [
            r"appeal", r"appellate", r"overturn.*conviction", r"resentencing",
        ],
        Intent.DRAFT_COMPLAINT: [
            r"file.*lawsuit", r"sue.*for", r"claim.*for", r"damages",
            r"complaint", r"civil case",
        ],
        Intent.NEGOTIATE_SETTLEMENT: [
            r"settle", r"settlement", r"reach.*agreement", r"resolve",
        ],
        Intent.DISCOVERY_REQUEST: [
            r"discovery", r"request.*documents", r"interrogatory",
        ],
        Intent.DEPOSITION_PREP: [
            r"deposition", r"testimony", r"prepare.*deposition",
        ],
        Intent.REVIEW_CONTRACT: [
            r"review.*contract", r"read.*contract", r"terms.*agreement",
            r"contract.*terms", r"sign.*contract",
        ],
        Intent.DRAFT_MOTION: [
            r"motion", r"file.*motion", r"court.*filing",
        ],
        Intent.CORPORATE_SETUP: [
            r"business.*formation", r"incorporate", r"LLC", r"partnership",
            r"entity.*formation",
        ],
        Intent.MERGER_ACQUISITION: [
            r"merge", r"acquisition", r"buyout", r"take.*over", r"acquire",
        ],
        Intent.DIVORCE_GUIDANCE: [
            r"divorce", r"separation", r"dissolve.*marriage", r"split",
        ],
        Intent.CUSTODY_DETERMINATION: [
            r"custody", r"parental.*rights", r"visitation", r"guardianship",
        ],
        Intent.CHILD_SUPPORT: [
            r"child.*support", r"alimony", r"spousal.*support",
        ],
        Intent.SPOUSAL_SUPPORT: [
            r"spousal.*support", r"alimony", r"maintenance",
        ],
        Intent.ADOPTION: [
            r"adopt", r"adoption", r"foster.*care",
        ],
        Intent.WILL_CREATION: [
            r"will", r"testament", r"estate.*plan", r"legacy",
        ],
        Intent.TRUST_SETUP: [
            r"trust", r"trustee", r"living.*trust", r"revocable.*trust",
        ],
        Intent.PROBATE_GUIDANCE: [
            r"probate", r"executor", r"inherit", r"estate.*administration",
        ],
        Intent.ESTATE_TAX_PLANNING: [
            r"estate.*tax", r"gift.*tax", r"inheritance.*tax",
        ],
        Intent.DEBT_MANAGEMENT: [
            r"debt", r"creditor", r"repayment", r"payment.*plan",
        ],
        Intent.CREDIT_REPAIR: [
            r"credit.*score", r"credit.*report", r"disputing", r"fraud",
        ],
        Intent.BANKRUPTCY_OPTIONS: [
            r"bankruptcy", r"chapter.*7", r"chapter.*13", r"financial.*fresh start",
        ],
        Intent.INVESTMENT_COMPLIANCE: [
            r"investment", r"securities", r"regulation", r"compliance",
        ],
        Intent.LEGAL_RESEARCH: [
            r"research", r"look.*up", r"find.*law", r"statute",
        ],
        Intent.STATUTE_EXPLANATION: [
            r"what.*statute", r"what.*section", r"explain.*law",
        ],
        Intent.CASE_LAW_RESEARCH: [
            r"case", r"precedent", r"court.*decision", r"ruling",
        ],
        Intent.URGENT_HELP: [
            r"urgent", r"emergency", r"right now", r"immediately",
            r"today", r"tomorrow", r"hearing.*today",
        ],
    }

    def __init__(self):
        """Initialize intent classifier."""
        self.compiled_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        for intent, patterns in self.INTENT_PATTERNS.items():
            self.compiled_patterns[intent] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def classify_intent(self, text: str) -> IntentResult:
        """Classify primary and secondary intents.
        
        Args:
            text: Input text
            
        Returns:
            IntentResult with primary/secondary intents
        """
        intent_scores = {}

        for intent, patterns in self.compiled_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(text):
                    score += 1
            
            if score > 0:
                intent_scores[intent] = score

        if not intent_scores:
            return IntentResult(
                primary_intent=Intent.GENERAL_INQUIRY,
                confidence=0.0,
            )

        # Sort by score
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        
        primary_intent = sorted_intents[0][0]
        primary_confidence = sorted_intents[0][1] / len(text.split())

        secondary_intents = [intent for intent, _ in sorted_intents[1:4]]

        return IntentResult(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            confidence=min(primary_confidence, 0.95),
        )


class EntityExtractor:
    """Extracts named entities from legal text."""

    # Patterns for entity extraction
    ENTITY_PATTERNS = {
        EntityType.PERSON: r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b",
        EntityType.DOLLAR_AMOUNT: r"\$[\d,]+(?:\.\d{2})?|\b[\d,]+\s(?:dollars?|USD)\b",
        EntityType.CASE_NUMBER: r"\b\d{2}-[A-Z]{2}-\d{4,}\b",
        EntityType.DATE: r"\b(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
        EntityType.STATUTE: r"\b(?:Section|§|U\.S\.C\.|U\.S\.A\.|Code|Law)\s+[\d\w\.\-]+\b",
        EntityType.COURT: r"\b(?:Supreme Court|Court of Appeals|District Court|Circuit Court|County Court|Federal Court)\b",
        EntityType.LOCATION: r"\b(?:New York|California|Texas|Florida|Pennsylvania|Illinois|Ohio|Georgia|North Carolina|Michigan)\b",
    }

    def __init__(self):
        """Initialize entity extractor."""
        self.compiled_patterns = {}
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            self.compiled_patterns[entity_type] = re.compile(pattern)

    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text.
        
        Args:
            text: Input text
            
        Returns:
            List of extracted entities
        """
        entities = []

        for entity_type, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(text):
                entity = Entity(
                    text=match.group(),
                    entity_type=entity_type,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.85,
                    normalized_value=self._normalize_entity(match.group(), entity_type),
                )
                entities.append(entity)

        # Sort by position
        entities.sort(key=lambda e: e.start_pos)
        return entities

    def _normalize_entity(self, text: str, entity_type: EntityType) -> Optional[str]:
        """Normalize entity to standard form.
        
        Args:
            text: Entity text
            entity_type: Type of entity
            
        Returns:
            Normalized value or None
        """
        if entity_type == EntityType.DOLLAR_AMOUNT:
            # Extract just the number
            match = re.search(r"[\d,]+(?:\.\d{2})?", text)
            return match.group() if match else None
        
        elif entity_type == EntityType.DATE:
            # Would parse to ISO format
            return text
        
        elif entity_type == EntityType.STATUTE:
            # Normalize statute reference
            return text.strip()
        
        return None


class ComplexityScorer:
    """Scores legal question complexity."""

    COMPLEXITY_FACTORS = {
        # Keywords that increase complexity
        "high_complexity": [
            "federal", "securities", "international", "multi-party",
            "precedent", "appellate", "appeal", "constitutional",
            "complex", "intricate", "novel", "jurisdictional",
            "merger", "acquisition", "bankruptcy", "tax",
        ],
        "medium_complexity": [
            "contract", "dispute", "claim", "liability",
            "settlement", "discovery", "trial", "estate",
        ],
        "low_complexity": [
            "question", "explain", "general", "basic",
            "simple", "straightforward", "understand",
        ],
    }

    def score_complexity(self, text: str, entity_count: int,
                        intent: Intent) -> float:
        """Score complexity of legal question (1-10).
        
        Args:
            text: Input text
            entity_count: Number of entities extracted
            intent: Classified intent
            
        Returns:
            Complexity score 1-10
        """
        score = 5.0  # Base score

        # Check for complexity keywords
        text_lower = text.lower()
        
        for keyword in self.COMPLEXITY_FACTORS["high_complexity"]:
            if keyword in text_lower:
                score += 1.5

        for keyword in self.COMPLEXITY_FACTORS["medium_complexity"]:
            if keyword in text_lower:
                score += 0.5

        for keyword in self.COMPLEXITY_FACTORS["low_complexity"]:
            if keyword in text_lower:
                score -= 0.5

        # Entities add to complexity
        score += (entity_count * 0.3)

        # Intent-based adjustments
        complex_intents = [
            Intent.MERGER_ACQUISITION,
            Intent.APPEAL,
            Intent.BANKRUPTCY_OPTIONS,
            Intent.ESTATE_TAX_PLANNING,
        ]
        
        if intent in complex_intents:
            score += 1.5

        return min(max(score, 1.0), 10.0)


class UrgencyDetector:
    """Detects urgency level from text."""

    CRITICAL_KEYWORDS = [
        "emergency", "urgent", "immediately", "right now",
        "today", "tomorrow", "deadline", "court date",
        "this week", "this month", "expiring", "expires",
        "imminent", "dying", "deceased", "jail",
    ]

    CRITICAL_INTENTS = [
        Intent.BAIL_BOND,
        Intent.APPEAL,
        Intent.URGENT_HELP,
        Intent.DEFENSE_ADVICE,
    ]

    def detect_urgency(self, text: str, intent: Intent) -> str:
        """Detect urgency level.
        
        Args:
            text: Input text
            intent: Primary intent
            
        Returns:
            Urgency level: "low", "normal", "high", "critical"
        """
        text_lower = text.lower()
        keyword_count = sum(1 for kw in self.CRITICAL_KEYWORDS if kw in text_lower)

        if intent in self.CRITICAL_INTENTS or keyword_count >= 2:
            return "critical"

        if keyword_count >= 1:
            return "high"

        # Check for near-future time references
        if re.search(r"\b(?:next\s+week|this\s+week|this\s+month)\b", text_lower):
            return "high"

        return "normal"


class PracticeAreaClassifier:
    """Classifies legal practice area."""

    AREA_KEYWORDS = {
        PracticeArea.CRIMINAL: ["arrest", "charge", "defense", "plea", "sentence", "prison"],
        PracticeArea.FAMILY: ["divorce", "custody", "adoption", "spouse", "child", "marriage"],
        PracticeArea.CORPORATE: ["business", "incorporation", "shareholder", "board", "merger"],
        PracticeArea.INTELLECTUAL_PROPERTY: ["patent", "trademark", "copyright", "invention"],
        PracticeArea.REAL_ESTATE: ["property", "deed", "mortgage", "landlord", "tenant"],
        PracticeArea.TRUSTS_ESTATES: ["will", "trust", "probate", "inherit", "executor"],
        PracticeArea.EMPLOYMENT: ["employment", "discrimination", "wage", "termination", "workplace"],
        PracticeArea.BANKRUPTCY: ["bankruptcy", "debt", "creditor", "insolvency"],
        PracticeArea.FINANCIAL: ["investment", "securities", "wealth", "financial", "portfolio"],
        PracticeArea.TAX: ["tax", "deduction", "IRS", "return", "filing"],
    }

    def classify_area(self, text: str, intent: Intent) -> PracticeArea:
        """Classify primary practice area.
        
        Args:
            text: Input text
            intent: Primary intent
            
        Returns:
            Practice area classification
        """
        text_lower = text.lower()
        area_scores = {}

        for area, keywords in self.AREA_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                area_scores[area] = score

        if not area_scores:
            return PracticeArea.OTHER

        return max(area_scores, key=area_scores.get)


class LegalNLPProcessor:
    """Main NLP processor combining classification, extraction, and analysis."""

    def __init__(self):
        """Initialize LegalNLPProcessor."""
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.complexity_scorer = ComplexityScorer()
        self.urgency_detector = UrgencyDetector()
        self.area_classifier = PracticeAreaClassifier()

    def process(self, text: str) -> NLPResult:
        """Process text through full NLP pipeline.
        
        Args:
            text: Input text to process
            
        Returns:
            Complete NLPResult with all analyses
        """
        # Classify intent
        intent_result = self.intent_classifier.classify_intent(text)

        # Extract entities
        entities = self.entity_extractor.extract_entities(text)

        # Classify practice area
        practice_area = self.area_classifier.classify_area(text, intent_result.primary_intent)

        # Score complexity
        complexity = self.complexity_scorer.score_complexity(
            text, len(entities), intent_result.primary_intent
        )

        # Detect urgency
        urgency = self.urgency_detector.detect_urgency(text, intent_result.primary_intent)

        # Extract jurisdiction
        jurisdiction = self._extract_jurisdiction(text, entities)

        # Detect question types
        has_legal = self._has_legal_questions(text)
        has_financial = self._has_financial_questions(text)

        # Extract key phrases
        key_phrases = self._extract_key_phrases(text)

        return NLPResult(
            original_text=text,
            intent=intent_result,
            entities=entities,
            complexity_score=complexity,
            practice_area=practice_area,
            urgency_level=urgency,
            jurisdiction=jurisdiction,
            has_legal_questions=has_legal,
            has_financial_questions=has_financial,
            key_phrases=key_phrases,
        )

    def _extract_jurisdiction(self, text: str, entities: List[Entity]) -> Optional[str]:
        """Extract jurisdiction from text and entities."""
        jurisdictions = ["New York", "California", "Texas", "Federal", "State"]
        for entity in entities:
            if entity.entity_type == EntityType.LOCATION:
                return entity.text
        
        for jurisdiction in jurisdictions:
            if jurisdiction in text:
                return jurisdiction
        
        return None

    def _has_legal_questions(self, text: str) -> bool:
        """Detect if text contains legal questions."""
        legal_keywords = ["law", "legal", "statute", "court", "judge", "attorney"]
        return any(kw in text.lower() for kw in legal_keywords)

    def _has_financial_questions(self, text: str) -> bool:
        """Detect if text contains financial questions."""
        financial_keywords = ["money", "dollar", "payment", "cost", "fee", "debt", "credit"]
        return any(kw in text.lower() for kw in financial_keywords)

    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text."""
        phrases = []
        # Simple extraction: multi-word chunks
        words = text.split()
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if len(phrase) > 6:
                phrases.append(phrase)
        
        return list(set(phrases[:5]))  # Return unique, max 5


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
