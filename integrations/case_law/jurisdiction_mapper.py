"""
Jurisdiction Mapper
===================
Maps legal questions and fact patterns to applicable jurisdictions.

Features:
- Determine applicable federal vs. state jurisdiction
- Map courts to binding/persuasive authority hierarchy
- Diversity jurisdiction analysis
- Federal question jurisdiction detection
- Subject matter jurisdiction mapping
- Venue determination
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class JurisdictionAnalysis:
    """Complete jurisdiction analysis for a legal matter."""

    matter_description: str
    primary_jurisdiction: str           # "federal" or "state"
    applicable_states: List[str]        # State abbreviations
    federal_basis: Optional[str]        # "federal question", "diversity", "admiralty", etc.
    subject_matter: str                 # what the case is about
    venue_courts: List[str]             # CourtListener court IDs where case can be filed
    binding_authorities: List[str]      # Courts that bind the applicable forum
    persuasive_authorities: List[str]   # Courts with persuasive authority
    conflict_of_laws_risk: bool         # Whether multiple states may apply
    preemption_issues: List[str]        # Federal statutes that may preempt state law
    notes: str = ""


@dataclass
class DiversityAnalysis:
    """Analysis of federal diversity jurisdiction."""

    plaintiff_state: Optional[str]
    defendant_state: Optional[str]
    amount_in_controversy: Optional[float]
    meets_diversity: bool
    complete_diversity: bool
    amount_meets_threshold: bool
    notes: str = ""


@dataclass
class FederalQuestionAnalysis:
    """Analysis of federal question jurisdiction."""

    has_federal_question: bool
    federal_statutes: List[str]
    constitutional_claims: List[str]
    federal_common_law: bool
    well_pleaded_complaint: bool
    notes: str = ""


# ---------------------------------------------------------------------------
# Jurisdiction taxonomy
# ---------------------------------------------------------------------------

# Federal statutes that create federal question jurisdiction
FEDERAL_QUESTION_STATUTES = {
    "42 U.S.C. 1983": "Civil rights violations under color of state law",
    "28 U.S.C. 1331": "General federal question jurisdiction",
    "28 U.S.C. 1332": "Diversity of citizenship",
    "28 U.S.C. 1333": "Admiralty and maritime",
    "28 U.S.C. 1334": "Bankruptcy",
    "28 U.S.C. 1338": "Patent, copyright, trademark",
    "28 U.S.C. 1343": "Civil rights",
    "15 U.S.C. 1": "Sherman Antitrust Act",
    "29 U.S.C. 185": "LMRA - Labor relations",
    "ERISA": "Employee benefits",
    "RICO": "Racketeering",
    "FCRA": "Fair Credit Reporting",
    "FDCPA": "Fair Debt Collection",
    "ADA": "Disability discrimination",
    "Title VII": "Employment discrimination",
    "ADEA": "Age discrimination",
    "FLSA": "Wage and hour",
    "FMLA": "Family and medical leave",
    "Section 10(b)": "Securities fraud",
    "HIPAA": "Healthcare privacy",
}

# Federal statutes with preemptive effect on state law
PREEMPTION_STATUTES = {
    "ERISA": "Preempts most state laws relating to employee benefit plans",
    "NLRA": "Preempts state laws governing labor relations",
    "Copyright Act": "Preempts state copyright claims",
    "Patent Act": "Preempts state patent claims",
    "Airline Deregulation Act": "Preempts state rate/service regulation of airlines",
    "FDCA": "Partially preempts state food and drug claims",
    "FIFRA": "Preempts state pesticide labeling laws",
    "RICO": "Does not preempt state RICO analogs",
    "Magnuson-Moss": "Partially preempts state warranty claims",
}

# State-specific areas where state law typically governs
STATE_LAW_DOMAINS = [
    "tort law",
    "contract law",
    "property law",
    "family law",
    "probate",
    "real estate",
    "state criminal law",
    "corporate governance (non-securities)",
    "professional licensing",
    "insurance (non-federal)",
    "workers compensation",
    "landlord-tenant",
]

# Court hierarchy for federal system
FEDERAL_COURT_HIERARCHY: Dict[str, int] = {
    "scotus": 100,
    "cadc": 80, "cafc": 80,
    "ca1": 75, "ca2": 75, "ca3": 75, "ca4": 75, "ca5": 75,
    "ca6": 75, "ca7": 75, "ca8": 75, "ca9": 75, "ca10": 75, "ca11": 75,
    # District courts
    "nysd": 50, "cacd": 50, "txnd": 50,
}

# State abbreviation to district court mapping (primary)
STATE_TO_DISTRICT: Dict[str, List[str]] = {
    "NY": ["nysd", "nyed", "nynd", "nywd"],
    "CA": ["cacd", "cand", "casd", "caed"],
    "TX": ["txsd", "txnd", "txed", "txwd"],
    "FL": ["flsd", "flnd", "flmd"],
    "IL": ["ilnd", "ilsd", "ilcd"],
    "PA": ["paed", "pawd", "pamd"],
    "GA": ["gand", "gamd", "gasd"],
    "OH": ["ohnd", "ohsd"],
    "MA": ["mad"],
    "WA": ["wawd", "waed"],
    "DC": ["dcd"],
    "VA": ["vaed", "vawd"],
    "NC": ["ncmd", "nced", "ncwd"],
    "MI": ["mied", "miwd"],
    "NJ": ["njd"],
    "CO": ["cod"],
    "AZ": ["azd"],
    "MN": ["mnd"],
    "MO": ["moed", "mowd"],
    "TN": ["tned", "tnmd", "tnwd"],
    "OR": ["ord"],
    "CT": ["ctd"],
    "MD": ["mdd"],
    "WI": ["wied", "wiwd"],
    "IN": ["innd", "insd"],
    "KY": ["kyed", "kywd"],
    "LA": ["laed", "lamd", "lawd"],
    "AL": ["aled", "almd", "alnd"],
    "NV": ["nvd"],
    "UT": ["utd"],
    "KS": ["ksd"],
    "NE": ["ned"],
    "OK": ["oked", "oknd", "okwd"],
    "IA": ["iasd", "iand"],
    "AR": ["ared", "arwd"],
    "MS": ["msnd", "mssd"],
    "SC": ["scd"],
    "WV": ["wvnd", "wvsd"],
    "NH": ["nhd"],
    "ME": ["med"],
    "RI": ["rid"],
    "VT": ["vtd"],
    "HI": ["hid"],
    "AK": ["akd"],
    "ID": ["idd"],
    "MT": ["mtd"],
    "ND": ["ndd"],
    "SD": ["sdd"],
    "WY": ["wyd"],
    "NM": ["nmd"],
    "DE": ["ded"],
}

# State to circuit mapping
STATE_TO_CIRCUIT: Dict[str, str] = {
    "ME": "ca1", "NH": "ca1", "MA": "ca1", "RI": "ca1", "CT": "ca1", "PR": "ca1",
    "NY": "ca2", "VT": "ca2", "CT": "ca2",
    "PA": "ca3", "NJ": "ca3", "DE": "ca3", "VI": "ca3",
    "MD": "ca4", "VA": "ca4", "WV": "ca4", "NC": "ca4", "SC": "ca4",
    "TX": "ca5", "LA": "ca5", "MS": "ca5",
    "KY": "ca6", "TN": "ca6", "OH": "ca6", "MI": "ca6",
    "WI": "ca7", "IL": "ca7", "IN": "ca7",
    "MN": "ca8", "IA": "ca8", "MO": "ca8", "AR": "ca8", "NE": "ca8", "SD": "ca8", "ND": "ca8",
    "CA": "ca9", "OR": "ca9", "WA": "ca9", "AK": "ca9", "HI": "ca9", "ID": "ca9", "MT": "ca9", "NV": "ca9", "AZ": "ca9",
    "CO": "ca10", "WY": "ca10", "UT": "ca10", "KS": "ca10", "OK": "ca10", "NM": "ca10",
    "GA": "ca11", "AL": "ca11", "FL": "ca11",
    "DC": "cadc",
}


class JurisdictionMapper:
    """
    Maps legal matters to applicable jurisdictions and court systems.

    Usage:
        mapper = JurisdictionMapper()
        analysis = mapper.analyze(
            description="Employee fired for religious accommodation request",
            states=["CA", "TX"],
            involves_federal_agency=False,
        )
        # Returns JurisdictionAnalysis with venue, binding authority, etc.
    """

    def analyze(
        self,
        description: str,
        states: Optional[List[str]] = None,
        plaintiff_state: Optional[str] = None,
        defendant_state: Optional[str] = None,
        amount_in_controversy: Optional[float] = None,
        involves_federal_agency: bool = False,
    ) -> JurisdictionAnalysis:
        """
        Analyze jurisdiction for a legal matter.

        Args:
            description: Description of the legal issue/fact pattern.
            states: States where relevant facts occurred.
            plaintiff_state: Plaintiff's state of citizenship.
            defendant_state: Defendant's state of citizenship.
            amount_in_controversy: Dollar amount at stake.
            involves_federal_agency: Whether a federal agency is involved.

        Returns:
            JurisdictionAnalysis with complete jurisdiction mapping.
        """
        desc_lower = description.lower()
        states = states or []

        # Detect federal question
        fq_analysis = self.analyze_federal_question(desc_lower)

        # Detect diversity
        div_analysis = self.analyze_diversity(
            plaintiff_state, defendant_state, amount_in_controversy
        )

        # Determine primary jurisdiction
        if fq_analysis.has_federal_question or involves_federal_agency:
            primary_jurisdiction = "federal"
            federal_basis = "federal question"
        elif div_analysis.meets_diversity:
            primary_jurisdiction = "federal"
            federal_basis = "diversity of citizenship"
        else:
            primary_jurisdiction = "state"
            federal_basis = None

        # Determine subject matter
        subject_matter = self._classify_subject_matter(desc_lower)

        # Determine venue courts
        venue_courts = self._determine_venue_courts(states, primary_jurisdiction)

        # Determine binding/persuasive authority
        binding, persuasive = self._determine_authority(venue_courts)

        # Check preemption
        preemption_issues = self._check_preemption(desc_lower)

        # Conflict of laws risk
        conflict_risk = len(states) > 1

        return JurisdictionAnalysis(
            matter_description=description,
            primary_jurisdiction=primary_jurisdiction,
            applicable_states=states,
            federal_basis=federal_basis,
            subject_matter=subject_matter,
            venue_courts=venue_courts,
            binding_authorities=binding,
            persuasive_authorities=persuasive,
            conflict_of_laws_risk=conflict_risk,
            preemption_issues=preemption_issues,
            notes=self._generate_notes(fq_analysis, div_analysis, preemption_issues),
        )

    def analyze_federal_question(self, text: str) -> FederalQuestionAnalysis:
        """Detect federal question jurisdiction from case description."""
        text_lower = text.lower()
        federal_statutes = []
        constitutional_claims = []

        for statute, desc in FEDERAL_QUESTION_STATUTES.items():
            if statute.lower() in text_lower:
                federal_statutes.append(statute)

        const_keywords = [
            "first amendment", "second amendment", "fourth amendment",
            "fifth amendment", "sixth amendment", "eighth amendment",
            "fourteenth amendment", "due process", "equal protection",
            "free speech", "establishment clause", "free exercise",
        ]
        for kw in const_keywords:
            if kw in text_lower:
                constitutional_claims.append(kw.title())

        has_federal_question = bool(federal_statutes or constitutional_claims)

        return FederalQuestionAnalysis(
            has_federal_question=has_federal_question,
            federal_statutes=federal_statutes,
            constitutional_claims=constitutional_claims,
            federal_common_law="maritime" in text_lower or "admiralty" in text_lower,
            well_pleaded_complaint=has_federal_question,
            notes="Federal question established by statute" if federal_statutes else "",
        )

    def analyze_diversity(
        self,
        plaintiff_state: Optional[str],
        defendant_state: Optional[str],
        amount: Optional[float],
    ) -> DiversityAnalysis:
        """Analyze diversity of citizenship jurisdiction."""
        THRESHOLD = 75_000.00

        complete_diversity = bool(
            plaintiff_state and defendant_state
            and plaintiff_state.upper() != defendant_state.upper()
        )
        amount_meets = (amount or 0) > THRESHOLD

        meets_diversity = complete_diversity and amount_meets

        return DiversityAnalysis(
            plaintiff_state=plaintiff_state,
            defendant_state=defendant_state,
            amount_in_controversy=amount,
            meets_diversity=meets_diversity,
            complete_diversity=complete_diversity,
            amount_meets_threshold=amount_meets,
            notes=(
                f"Diversity: {plaintiff_state} vs {defendant_state}, ${amount:,.0f}"
                if complete_diversity else "Insufficient diversity"
            ),
        )

    def _classify_subject_matter(self, text: str) -> str:
        """Classify the subject matter of the legal dispute."""
        classifications = {
            "employment discrimination": ["discriminat", "title vii", "adea", "ada", "wrongful terminat"],
            "civil rights": ["civil rights", "section 1983", "constitutional"],
            "intellectual property": ["patent", "copyright", "trademark"],
            "securities fraud": ["securities", "sec ", "insider trading"],
            "antitrust": ["antitrust", "monopoly", "sherman"],
            "environmental": ["environmental", "epa", "clean air", "clean water"],
            "bankruptcy": ["bankruptcy", "chapter 11", "chapter 7"],
            "immigration": ["immigration", "deportation", "asylum"],
            "criminal": ["criminal", "indictment", "prosecution", "guilty"],
            "contract dispute": ["contract", "breach", "damages"],
            "personal injury": ["negligence", "tort", "injury", "accident"],
            "real property": ["property", "real estate", "landlord", "tenant"],
        }
        for subject, keywords in classifications.items():
            if any(kw in text for kw in keywords):
                return subject
        return "general civil"

    def _determine_venue_courts(
        self, states: List[str], primary_jurisdiction: str
    ) -> List[str]:
        """Determine valid venue courts."""
        courts = []
        if primary_jurisdiction == "federal":
            for state in states:
                district_courts = STATE_TO_DISTRICT.get(state.upper(), [])
                courts.extend(district_courts[:2])  # limit to 2 per state
        else:
            # State courts - use state abbreviation as proxy
            for state in states:
                courts.append(f"{state.lower()}_state_courts")
        return list(set(courts))[:6]

    def _determine_authority(
        self, venue_courts: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Determine binding and persuasive authority for venue courts."""
        binding = ["scotus"]  # SCOTUS always binding
        persuasive = []

        for court in venue_courts:
            # Find the circuit for this district court
            for state, district_list in STATE_TO_DISTRICT.items():
                if court in district_list:
                    circuit = STATE_TO_CIRCUIT.get(state)
                    if circuit and circuit not in binding:
                        binding.append(circuit)
                    break

        # All other circuits are persuasive
        all_circuits = ["ca1", "ca2", "ca3", "ca4", "ca5", "ca6", "ca7",
                        "ca8", "ca9", "ca10", "ca11", "cadc", "cafc"]
        for c in all_circuits:
            if c not in binding:
                persuasive.append(c)

        return binding, persuasive

    def _check_preemption(self, text: str) -> List[str]:
        """Check for potential federal preemption issues."""
        issues = []
        for statute, description in PREEMPTION_STATUTES.items():
            if statute.lower() in text:
                issues.append(f"{statute}: {description}")
        return issues

    def _generate_notes(
        self,
        fq: FederalQuestionAnalysis,
        div: DiversityAnalysis,
        preemption: List[str],
    ) -> str:
        """Generate analysis notes."""
        notes = []
        if fq.has_federal_question:
            notes.append(f"Federal question jurisdiction: {', '.join(fq.federal_statutes[:3])}")
        if fq.constitutional_claims:
            notes.append(f"Constitutional claims: {', '.join(fq.constitutional_claims[:3])}")
        if div.meets_diversity:
            notes.append(f"Diversity jurisdiction available ({div.plaintiff_state} vs {div.defendant_state})")
        if preemption:
            notes.append(f"Preemption risk: {preemption[0]}")
        return " | ".join(notes)

    def get_circuit_for_state(self, state: str) -> Optional[str]:
        """Get the federal circuit court for a state."""
        return STATE_TO_CIRCUIT.get(state.upper())

    def get_district_courts_for_state(self, state: str) -> List[str]:
        """Get federal district courts for a state."""
        return STATE_TO_DISTRICT.get(state.upper(), [])

    def is_binding_on(self, source_court: str, forum_court: str) -> bool:
        """Determine if source_court's opinions bind forum_court."""
        if source_court == "scotus":
            return True
        if source_court == forum_court:
            return False  # same court doesn't "bind" itself

        # Check if source is the circuit for forum's district
        for state, districts in STATE_TO_DISTRICT.items():
            if forum_court in districts:
                circuit = STATE_TO_CIRCUIT.get(state)
                if circuit == source_court:
                    return True
        return False
