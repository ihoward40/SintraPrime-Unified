"""
Criminal Defense Engine — SintraPrime Legal Intelligence System

Covers federal and state criminal matters including charge analysis, defense
strategy, Fourth Amendment suppression, plea analysis, and sentencing guidelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ChargeAnalysis:
    """
    Analysis of criminal charges including elements, sentences, and defenses.

    Example:
        >>> analysis = ChargeAnalysis(
        ...     charges=["18 U.S.C. § 1343 Wire Fraud"],
        ...     jurisdiction="federal",
        ...     elements={"wire_fraud": ["scheme to defraud", "material misrepresentation",
        ...                              "use of wire communications", "intent"]},
        ...     max_sentences={"wire_fraud": "20 years imprisonment"},
        ...     available_defenses=["Good faith belief", "Lack of intent"],
        ...     constitutional_issues=["4th Amendment — electronic surveillance warrant required"]
        ... )
    """
    charges: List[str]
    jurisdiction: str
    elements: Dict[str, List[str]]
    max_sentences: Dict[str, str]
    mandatory_minimums: Dict[str, str]
    available_defenses: List[str]
    constitutional_issues: List[str]
    collateral_consequences: List[str]
    severity_score: float = 0.0  # 0-100


@dataclass
class DefenseStrategy:
    """
    Complete defense strategy for a criminal matter.

    Example:
        >>> strategy = DefenseStrategy(
        ...     primary_defense="Fourth Amendment suppression",
        ...     affirmative_defenses=["Self-defense"],
        ...     procedural_defenses=["Brady violation"],
        ...     motions_to_file=["Motion to Suppress", "Motion to Dismiss"],
        ...     evidence_to_gather=["Surveillance footage", "Witness statements"],
        ...     plea_recommendation="Proceed to trial if suppression motion succeeds",
        ...     strength_assessment=0.65
        ... )
    """
    primary_defense: str
    affirmative_defenses: List[str]
    procedural_defenses: List[str]
    motions_to_file: List[str]
    evidence_to_gather: List[str]
    witnesses_to_identify: List[str]
    plea_recommendation: str
    strength_assessment: float  # 0.0 - 1.0 (client's chances)
    immediate_actions: List[str] = field(default_factory=list)
    constitutional_challenges: List[str] = field(default_factory=list)


@dataclass
class FourthAmendmentAnalysis:
    """
    Fourth Amendment search and seizure analysis.

    Example:
        >>> analysis = FourthAmendmentAnalysis(
        ...     search_was_unlawful=True,
        ...     basis="Warrantless search without applicable exception",
        ...     suppression_viable=True,
        ...     applicable_exceptions=[],
        ...     fruit_of_poisonous_tree=["Statements made after illegal search"],
        ...     key_cases=["Mapp v. Ohio (1961)", "Katz v. United States (1967)"]
        ... )
    """
    search_was_unlawful: bool
    basis: str
    suppression_viable: bool
    applicable_exceptions: List[str]
    fruit_of_poisonous_tree: List[str]
    key_cases: List[str]
    good_faith_exception_applies: bool = False
    independent_source_doctrine: bool = False
    inevitable_discovery: bool = False
    attenuation_doctrine: bool = False
    notes: str = ""


@dataclass
class PleaAnalysis:
    """
    Analysis of whether to accept a plea agreement.

    Example:
        >>> plea = PleaAnalysis(
        ...     should_accept=True,
        ...     recommended_plea="Accept — significant sentencing benefit",
        ...     trial_risk="Likely conviction; 10+ years",
        ...     plea_benefit="Reduces exposure to 2-3 years",
        ...     collateral_consequences=["Loss of professional license", "Deportation risk"],
        ...     negotiation_opportunities=["Request drug treatment program"]
        ... )
    """
    should_accept: bool
    recommended_plea: str
    trial_risk: str
    plea_benefit: str
    collateral_consequences: List[str]
    negotiation_opportunities: List[str]
    immigration_consequences: str = ""
    licensing_consequences: str = ""
    strength_of_case_against_client: float = 0.5  # 0-1.0


@dataclass
class SentencingRange:
    """
    Federal Sentencing Guidelines calculation result.

    Example:
        >>> sr = SentencingRange(
        ...     offense_level=22,
        ...     criminal_history_category="II",
        ...     guidelines_range_months=(46, 57),
        ...     guidelines_range_string="46-57 months",
        ...     statutory_maximum="20 years",
        ...     mandatory_minimum=None,
        ...     departure_grounds=["Substantial assistance", "Aberrant behavior"]
        ... )
    """
    offense_level: int
    criminal_history_category: str
    guidelines_range_months: Tuple[int, int]
    guidelines_range_string: str
    statutory_maximum: str
    mandatory_minimum: Optional[str]
    departure_grounds: List[str]
    variance_arguments: List[str] = field(default_factory=list)
    probation_eligible: bool = False


# ---------------------------------------------------------------------------
# Federal Criminal Charge Database
# ---------------------------------------------------------------------------

FEDERAL_CHARGES: Dict[str, Dict] = {
    "18 USC 1343 wire fraud": {
        "statute": "18 U.S.C. § 1343",
        "name": "Wire Fraud",
        "elements": [
            "Scheme to defraud",
            "Material misrepresentation or omission",
            "Specific intent to defraud",
            "Use of wire, radio, or television communication in furtherance of scheme",
        ],
        "max_sentence": "20 years (30 years if financial institution or federal disaster/emergency)",
        "mandatory_minimum": None,
        "base_offense_level_ussg": 7,
        "key_cases": ["Neder v. United States, 527 U.S. 1 (1999) — materiality required"],
        "defenses": ["Good faith", "Lack of intent to defraud", "Truth of representations"],
    },
    "18 USC 1341 mail fraud": {
        "statute": "18 U.S.C. § 1341",
        "name": "Mail Fraud",
        "elements": [
            "Scheme to defraud",
            "Material misrepresentation or omission",
            "Specific intent to defraud",
            "Use of United States mails in furtherance of scheme",
        ],
        "max_sentence": "20 years (30 years if financial institution)",
        "mandatory_minimum": None,
        "base_offense_level_ussg": 7,
        "defenses": ["Good faith", "No intent to defraud", "No use of mails in furtherance"],
    },
    "21 USC 841 drug distribution": {
        "statute": "21 U.S.C. § 841(a)(1)",
        "name": "Drug Distribution",
        "elements": [
            "Knowingly or intentionally",
            "Manufactured, distributed, dispensed, or possessed with intent to distribute",
            "Controlled substance",
        ],
        "max_sentence": "Varies by drug type and quantity; up to life for large quantities",
        "mandatory_minimum": "5-10 years depending on quantity (§ 841(b))",
        "note": "Mandatory minimums triggered by drug quantity findings",
        "key_cases": ["Alleyne v. United States, 570 U.S. 99 (2013) — mandatory min facts must go to jury"],
        "defenses": ["Lack of knowledge", "Entrapment", "Coercion/duress", "Lack of intent to distribute"],
    },
    "18 USC 922 felon in possession": {
        "statute": "18 U.S.C. § 922(g)(1)",
        "name": "Felon in Possession of Firearm",
        "elements": [
            "Defendant was previously convicted of crime punishable by imprisonment exceeding one year",
            "Defendant knowingly possessed a firearm or ammunition",
            "Firearm was in or affecting interstate or foreign commerce",
        ],
        "max_sentence": "15 years",
        "mandatory_minimum": None,
        "note": "ACCA (18 U.S.C. § 924(e)) — 15 year mandatory minimum if 3+ violent felony/drug priors",
        "key_cases": ["Rehaif v. United States, 588 U.S. ___ (2019) — government must prove knowledge of prohibited status"],
        "defenses": ["Did not knowingly possess", "Not convicted (prior conviction challenge)", "Rehaif — lacked knowledge of felon status"],
    },
    "18 USC 1956 money laundering": {
        "statute": "18 U.S.C. § 1956",
        "name": "Money Laundering",
        "elements": [
            "Financial transaction",
            "Involving proceeds of specified unlawful activity",
            "Knowledge that property represents proceeds of unlawful activity",
            "Intent to promote SUA, or knowledge transaction designed to conceal",
        ],
        "max_sentence": "20 years",
        "mandatory_minimum": None,
        "base_offense_level_ussg": 23,
        "defenses": ["Lack of knowledge", "No nexus to SUA", "Transaction not designed to conceal"],
    },
    "18 USC 371 conspiracy": {
        "statute": "18 U.S.C. § 371",
        "name": "Federal Conspiracy",
        "elements": [
            "Agreement between two or more persons",
            "To commit a federal offense",
            "An overt act in furtherance of conspiracy by at least one conspirator",
        ],
        "max_sentence": "5 years (or the penalty for the underlying offense if less)",
        "mandatory_minimum": None,
        "key_cases": ["Ocasio v. United States, 578 U.S. 282 (2016)"],
        "defenses": ["No agreement", "Withdrawal from conspiracy", "No overt act", "Impossibility (limited)"],
    },
    "18 USC 2 aiding and abetting": {
        "statute": "18 U.S.C. § 2",
        "name": "Aiding and Abetting",
        "elements": [
            "Principal committed the underlying offense",
            "Defendant associated with criminal venture",
            "Defendant participated to help it succeed",
            "Defendant shared criminal intent",
        ],
        "max_sentence": "Same as principal",
        "mandatory_minimum": None,
        "key_cases": ["Rosemond v. United States, 572 U.S. 65 (2014) — advance knowledge of crime required"],
        "defenses": ["No advance knowledge", "No intent to assist", "Mere presence insufficient"],
    },
}

STATE_CHARGES: Dict[str, Dict] = {
    "assault_battery": {
        "name": "Assault and/or Battery",
        "elements": {
            "assault": ["Intentional act", "Reasonable apprehension of imminent harmful contact"],
            "battery": ["Intentional harmful or offensive contact", "With person of victim"],
        },
        "max_sentence_range": "Misdemeanor: up to 1 year. Felony assault: 2-10+ years depending on state and aggravating factors.",
        "defenses": ["Self-defense", "Defense of others", "Consent (limited)", "Alibi", "Lack of intent"],
    },
    "dui_dwi": {
        "name": "DUI/DWI (Driving Under the Influence)",
        "elements": [
            "Operation of motor vehicle",
            "Under the influence of alcohol/drugs",
            "BAC ≥ 0.08% (per se DUI in most states)",
        ],
        "max_sentence_range": "First offense: 6 months - 1 year; Felony DUI: 1-10 years",
        "defenses": ["Invalid traffic stop (4th Amendment)", "Improper field sobriety test administration",
                     "Breathalyzer calibration issues", "Rising BAC defense", "Medical condition"],
        "key_issues": ["Implied consent warnings", "Chemical test refusal consequences",
                       "Administrative license suspension separate from criminal case"],
    },
    "theft_grand_larceny": {
        "name": "Theft / Grand Larceny",
        "elements": [
            "Taking and carrying away",
            "Property of another",
            "Without consent",
            "With intent to permanently deprive",
        ],
        "max_sentence_range": "Petty theft (misdemeanor): up to 1 year. Grand theft (felony): 1-10+ years by value and state.",
        "defenses": ["Claim of right / good faith ownership", "Lack of intent to permanently deprive",
                     "Mistaken identity", "Consent of owner"],
    },
    "domestic_violence": {
        "name": "Domestic Violence",
        "elements": [
            "Intentional act causing physical harm or fear",
            "Against domestic partner, family member, or cohabitant",
        ],
        "max_sentence_range": "Misdemeanor to felony depending on injury, weapon use, and prior offenses",
        "defenses": ["Self-defense", "False accusation", "Insufficient evidence", "Alibi"],
        "special_issues": [
            "Mandatory arrest laws in many states",
            "No-drop prosecution policies",
            "Domestic violence criminal conviction → federal firearms prohibition (18 U.S.C. § 922(g)(9))",
            "Protective/restraining orders issued",
        ],
    },
}

# ---------------------------------------------------------------------------
# Sentencing Guidelines Table (Simplified)
# ---------------------------------------------------------------------------

SENTENCING_GUIDELINES_TABLE: Dict[int, Dict[str, Tuple[int, int]]] = {
    # Offense Level → {Criminal History Category: (min months, max months)}
    1: {"I": (0, 6), "II": (0, 6), "III": (0, 6), "IV": (0, 6), "V": (0, 6), "VI": (0, 6)},
    8: {"I": (0, 6), "II": (2, 8), "III": (6, 12), "IV": (10, 16), "V": (15, 21), "VI": (21, 27)},
    12: {"I": (10, 16), "II": (15, 21), "III": (21, 27), "IV": (27, 33), "V": (33, 41), "VI": (41, 51)},
    16: {"I": (21, 27), "II": (27, 33), "III": (33, 41), "IV": (41, 51), "V": (51, 63), "VI": (63, 78)},
    20: {"I": (33, 41), "II": (37, 46), "III": (41, 51), "IV": (51, 63), "V": (63, 78), "VI": (70, 87)},
    22: {"I": (41, 51), "II": (46, 57), "III": (51, 63), "IV": (63, 78), "V": (77, 96), "VI": (84, 105)},
    24: {"I": (51, 63), "II": (57, 71), "III": (63, 78), "IV": (77, 96), "V": (92, 115), "VI": (100, 125)},
    26: {"I": (63, 78), "II": (70, 87), "III": (78, 97), "IV": (92, 115), "V": (110, 137), "VI": (120, 150)},
    30: {"I": (97, 121), "II": (108, 135), "III": (121, 151), "IV": (135, 168), "V": (151, 188), "VI": (168, 210)},
    35: {"I": (168, 210), "II": (188, 235), "III": (210, 262), "IV": (235, 293), "V": (262, 327), "VI": (292, 365)},
    43: {"I": (9999, 9999), "II": (9999, 9999), "III": (9999, 9999), "IV": (9999, 9999), "V": (9999, 9999), "VI": (9999, 9999)},  # Life imprisonment
}


# ---------------------------------------------------------------------------
# Criminal Defense Engine
# ---------------------------------------------------------------------------

class CriminalDefenseEngine:
    """
    Comprehensive criminal defense analysis covering federal and state matters.

    Analyzes charges, builds defense strategies, assesses Fourth Amendment
    issues, analyzes plea deals, and calculates sentencing ranges.

    Example:
        >>> engine = CriminalDefenseEngine()
        >>> analysis = engine.analyze_charges(
        ...     ["18 U.S.C. § 1343 Wire Fraud", "18 U.S.C. § 371 Conspiracy"],
        ...     "federal"
        ... )
        >>> "intent" in str(analysis.elements).lower()
        True
    """

    def __init__(self) -> None:
        self.federal_charges = FEDERAL_CHARGES
        self.state_charges = STATE_CHARGES

    def _match_charge(self, charge: str) -> Optional[Dict]:
        """Find charge data from database using fuzzy matching."""
        charge_lower = charge.lower()
        for key, data in {**self.federal_charges, **self.state_charges}.items():
            if any(k in charge_lower for k in key.replace("_", " ").split()):
                return data
            if data.get("statute", "").lower() in charge_lower:
                return data
            if data.get("name", "").lower() in charge_lower:
                return data
        return None

    def analyze_charges(self, charges: List[str], jurisdiction: str) -> ChargeAnalysis:
        """
        Analyze criminal charges — elements, sentences, defenses, constitutional issues.

        Args:
            charges: List of criminal charges (e.g., ["Wire Fraud", "Money Laundering"]).
            jurisdiction: "federal" or state name (e.g., "California").

        Returns:
            ChargeAnalysis with full analysis.

        Example:
            >>> engine = CriminalDefenseEngine()
            >>> analysis = engine.analyze_charges(["DUI", "Reckless Driving"], "California")
            >>> len(analysis.available_defenses) > 0
            True
        """
        elements = {}
        max_sentences = {}
        mandatory_minimums = {}
        all_defenses = set()
        constitutional_issues = []
        collateral_consequences = []

        for charge in charges:
            charge_data = self._match_charge(charge)

            if charge_data:
                charge_name = charge_data.get("name", charge)
                elements[charge_name] = charge_data.get("elements", ["Elements to be researched"])
                max_sentences[charge_name] = charge_data.get("max_sentence",
                                             charge_data.get("max_sentence_range", "Varies by jurisdiction"))
                if charge_data.get("mandatory_minimum"):
                    mandatory_minimums[charge_name] = charge_data["mandatory_minimum"]
                all_defenses.update(charge_data.get("defenses", []))
            else:
                elements[charge] = ["Research specific elements for this charge"]
                max_sentences[charge] = "Research applicable penalties"

        # Standard constitutional issues
        constitutional_issues = [
            "Fourth Amendment: Were searches conducted pursuant to valid warrant or recognized exception?",
            "Fifth Amendment: Were Miranda warnings given before custodial interrogation?",
            "Sixth Amendment: Was right to counsel honored from critical stage forward?",
            "Due Process: Is there any Brady material (exculpatory evidence) government must disclose?",
        ]

        # Collateral consequences
        collateral_consequences = [
            "Loss of voting rights (varies by state and felony/misdemeanor)",
            "Prohibition on firearm possession (18 U.S.C. § 922(g)) for felony convictions",
            "Immigration consequences — deportability for crimes of moral turpitude or aggravated felonies",
            "Professional licensing consequences (law, medicine, teaching, etc.)",
            "Sex offender registration (if applicable)",
            "Public housing eligibility",
            "Federal student loans (drug convictions)",
            "Employment background check impact",
        ]

        # Severity score
        severity = min(100.0, len(charges) * 15 + (30 if any("murder" in c.lower() or "rape" in c.lower() for c in charges) else 0))

        return ChargeAnalysis(
            charges=charges,
            jurisdiction=jurisdiction,
            elements=elements,
            max_sentences=max_sentences,
            mandatory_minimums=mandatory_minimums,
            available_defenses=list(all_defenses) or ["Insufficient evidence", "Reasonable doubt"],
            constitutional_issues=constitutional_issues,
            collateral_consequences=collateral_consequences,
            severity_score=severity,
        )

    def build_defense_strategy(self, case_facts: dict, charges: List[str]) -> DefenseStrategy:
        """
        Build a comprehensive defense strategy.

        Args:
            case_facts: Dict with case facts (e.g., {"search_warrant": False,
                        "miranda_warnings_given": False, "prior_record": "none"}).
            charges: List of criminal charges.

        Returns:
            DefenseStrategy with recommended approach.

        Example:
            >>> engine = CriminalDefenseEngine()
            >>> strategy = engine.build_defense_strategy(
            ...     {"search_warrant": False, "miranda_given": False},
            ...     ["Drug Possession"]
            ... )
            >>> "Suppress" in strategy.primary_defense or "suppress" in strategy.primary_defense.lower()
            True
        """
        affirmative_defenses = []
        procedural_defenses = []
        motions = []
        evidence_to_gather = []
        witnesses = []
        constitutional_challenges = []
        immediate_actions = [
            "CLIENT MUST NOT SPEAK TO POLICE OR PROSECUTORS WITHOUT COUNSEL PRESENT",
            "Preserve all communications, receipts, and physical evidence",
            "Identify and preserve surveillance footage (overwritten quickly)",
            "Obtain police reports and arrest records",
        ]

        # Assess Fourth Amendment
        if not case_facts.get("search_warrant", True):
            procedural_defenses.append("Fourth Amendment — suppression of illegally seized evidence")
            motions.append("Motion to Suppress Evidence (4th Amendment)")
            constitutional_challenges.append("Challenge validity of warrantless search")

        # Assess Fifth Amendment (Miranda)
        if not case_facts.get("miranda_given", True) or not case_facts.get("miranda_warnings_given", True):
            procedural_defenses.append("Miranda violation — suppress any custodial statements")
            motions.append("Motion to Suppress Statements (5th Amendment — Miranda)")
            constitutional_challenges.append("Government failed to give Miranda warnings before custodial interrogation")

        # Brady violation check
        if case_facts.get("exculpatory_evidence_possible", False):
            procedural_defenses.append("Brady violation — request all exculpatory and impeachment material")
            motions.append("Motion for Disclosure of Brady/Giglio Material")

        # Speedy trial
        if case_facts.get("detained_pretrial", False):
            procedural_defenses.append("Speedy Trial Act — assess 70-day clock under 18 U.S.C. § 3161")
            motions.append("Speedy Trial Act demand letter")

        # Affirmative defenses based on charges and facts
        if case_facts.get("self_defense", False):
            affirmative_defenses.append("Self-defense / defense of others")
        if case_facts.get("entrapment", False) or "undercover" in str(case_facts).lower():
            affirmative_defenses.append("Entrapment — government induced crime not otherwise committed")
        if case_facts.get("alibi", False):
            affirmative_defenses.append("Alibi defense")
        if case_facts.get("necessity", False):
            affirmative_defenses.append("Necessity / duress defense")

        # Default affirmative defense
        if not affirmative_defenses:
            affirmative_defenses.append("Insufficient evidence — reasonable doubt defense")

        # Evidence to gather
        evidence_to_gather = [
            "All police reports and incident reports",
            "Arrest video (body camera, dashcam, surveillance)",
            "Search warrant and supporting affidavit (if warrant issued)",
            "Chain of custody records for physical evidence",
            "Lab reports / expert analysis",
            "Witness contact information",
            "Criminal history of government witnesses (Giglio material)",
            "Any recorded statements (client's and witnesses')",
        ]

        # Witnesses
        witnesses = [
            "Eyewitnesses to incident",
            "Character witnesses",
            "Expert witnesses (forensic, medical, technical as applicable)",
            "Alibi witnesses (if applicable)",
        ]

        # Primary defense
        if motions:
            primary = f"Challenge evidence through suppression: {motions[0]}"
        elif affirmative_defenses:
            primary = affirmative_defenses[0]
        else:
            primary = "Reasonable doubt defense — challenge every element the government must prove"

        # Strength assessment
        strength = 0.5  # Default 50/50
        if not case_facts.get("search_warrant", True):
            strength += 0.15
        if not case_facts.get("miranda_given", True):
            strength += 0.10
        if case_facts.get("weak_evidence", False):
            strength += 0.20
        if case_facts.get("prior_record", "none") == "none":
            strength += 0.05

        strength = min(0.95, strength)

        # Plea recommendation
        if strength > 0.7:
            plea_rec = "Consider proceeding to trial — defense has significant strengths."
        elif strength > 0.5:
            plea_rec = "Evaluate plea offer carefully — case has some merit but risks remain."
        else:
            plea_rec = "Seriously consider plea agreement — trial risk appears high."

        return DefenseStrategy(
            primary_defense=primary,
            affirmative_defenses=affirmative_defenses,
            procedural_defenses=procedural_defenses,
            motions_to_file=motions or ["Motion to Dismiss for Insufficient Evidence"],
            evidence_to_gather=evidence_to_gather,
            witnesses_to_identify=witnesses,
            plea_recommendation=plea_rec,
            strength_assessment=strength,
            immediate_actions=immediate_actions,
            constitutional_challenges=constitutional_challenges,
        )

    def analyze_search_seizure(self, facts: dict) -> FourthAmendmentAnalysis:
        """
        Analyze Fourth Amendment search and seizure issues.

        Args:
            facts: Dict describing the search (e.g., {"warrant": False,
                   "consent_given": False, "in_car": True, "plain_view": False}).

        Returns:
            FourthAmendmentAnalysis with suppression viability.

        Example:
            >>> engine = CriminalDefenseEngine()
            >>> analysis = engine.analyze_search_seizure(
            ...     {"warrant": False, "consent_given": False, "exigent": False}
            ... )
            >>> analysis.suppression_viable
            True
        """
        warrant = facts.get("warrant", False)
        consent = facts.get("consent_given", False)
        exigent = facts.get("exigent_circumstances", facts.get("exigent", False))
        in_car = facts.get("in_car", facts.get("automobile", False))
        incident_to_arrest = facts.get("incident_to_arrest", False)
        plain_view = facts.get("plain_view", False)
        border_search = facts.get("border_search", False)
        inventory_search = facts.get("inventory", False)
        school_search = facts.get("school", False)
        probation_parole = facts.get("probation_or_parole", False)

        applicable_exceptions = []
        unlawful = not warrant

        if warrant:
            unlawful = False
            return FourthAmendmentAnalysis(
                search_was_unlawful=False,
                basis="Search conducted pursuant to warrant — presumptively valid.",
                suppression_viable=False,
                applicable_exceptions=["Search warrant"],
                fruit_of_poisonous_tree=[],
                key_cases=["Illinois v. Gates, 462 U.S. 213 (1983) — probable cause for warrant"],
                notes="Challenge warrant on: staleness, specificity, false affidavit (Franks v. Delaware), or Anticipatory warrant issues.",
            )

        # Warrantless — check exceptions
        if consent:
            applicable_exceptions.append("Consent exception (Schneckloth v. Bustamonte, 412 U.S. 218 (1973))")
            unlawful = False
            # But was consent voluntary?

        if exigent:
            applicable_exceptions.append("Exigent circumstances (hot pursuit, destruction of evidence, emergency)")
            unlawful = False

        if in_car:
            applicable_exceptions.append("Automobile exception — probable cause to search vehicle (Carroll v. United States (1925))")
            # If probable cause exists for car — not unlawful

        if incident_to_arrest:
            applicable_exceptions.append("Search incident to lawful arrest — Chimel v. California, 395 U.S. 752 (1969)")
            if facts.get("lawful_arrest", True):
                unlawful = False

        if plain_view:
            applicable_exceptions.append("Plain view doctrine — Coolidge v. New Hampshire, 403 U.S. 443 (1971)")
            if facts.get("lawful_vantage_point", True):
                unlawful = False

        if border_search:
            applicable_exceptions.append("Border search exception — no warrant required at international borders")
            unlawful = False

        if inventory_search:
            applicable_exceptions.append("Inventory search exception — South Dakota v. Opperman, 428 U.S. 364 (1976)")

        if school_search:
            applicable_exceptions.append("School search — reasonable suspicion standard (New Jersey v. T.L.O., 469 U.S. 325 (1985))")
            unlawful = False  # Lower standard

        if probation_parole:
            applicable_exceptions.append("Probation/parole search condition — Samson v. California, 547 U.S. 843 (2006)")
            unlawful = False

        # Good faith exception
        good_faith = facts.get("good_faith_reliance", False)
        if good_faith:
            if unlawful:
                # Leon good faith exception
                applicable_exceptions.append("Good faith exception — United States v. Leon, 468 U.S. 897 (1984)")
                unlawful = False  # Evidence may still come in

        suppression_viable = unlawful and len(applicable_exceptions) == 0

        key_cases = [
            "Mapp v. Ohio, 367 U.S. 643 (1961) — exclusionary rule applies to states",
            "Katz v. United States, 389 U.S. 347 (1967) — reasonable expectation of privacy",
            "Terry v. Ohio, 392 U.S. 1 (1968) — stop requires reasonable articulable suspicion",
            "Wong Sun v. United States, 371 U.S. 471 (1963) — fruit of the poisonous tree",
        ]

        fruit = []
        if suppression_viable:
            fruit = [
                "Any statements made after illegal search may be suppressible",
                "Physical evidence discovered as direct result of illegal search",
                "Leads developed from illegally obtained information",
            ]

        basis = (
            "Warrantless search with no applicable exception — search appears unlawful."
            if suppression_viable
            else f"Warrantless search justified by: {', '.join(applicable_exceptions) or 'warrant'}."
        )

        return FourthAmendmentAnalysis(
            search_was_unlawful=unlawful,
            basis=basis,
            suppression_viable=suppression_viable,
            applicable_exceptions=applicable_exceptions,
            fruit_of_poisonous_tree=fruit,
            key_cases=key_cases,
            good_faith_exception_applies=good_faith,
            notes="Assess: (1) was there a search? (2) did defendant have reasonable expectation of privacy? (3) does any exception apply?",
        )

    def plea_agreement_analyzer(self, offer: dict, case_strength: float) -> PleaAnalysis:
        """
        Analyze whether to accept a plea agreement.

        Args:
            offer: Dict describing the plea offer (e.g., {"charge": "Misdemeanor",
                   "sentence": "1 year probation", "original_charge": "Felony",
                   "max_trial_sentence": "5 years"}).
            case_strength: Float 0-1.0 representing client's likelihood of acquittal at trial.

        Returns:
            PleaAnalysis with recommendation.

        Example:
            >>> engine = CriminalDefenseEngine()
            >>> analysis = engine.plea_agreement_analyzer(
            ...     {"charge": "Misdemeanor DUI", "sentence": "30 days + probation",
            ...      "max_trial_sentence": "1 year", "original_charge": "Felony DUI"},
            ...     0.4
            ... )
            >>> isinstance(analysis.should_accept, bool)
            True
        """
        offered_charge = offer.get("charge", "Unknown charge")
        offered_sentence = offer.get("sentence", "Unknown")
        original_charge = offer.get("original_charge", offered_charge)
        max_trial = offer.get("max_trial_sentence", "Unknown")
        crime_type = offer.get("crime_type", "")

        # Calculate benefit
        felony_reduced = ("felony" in original_charge.lower() and
                          "misdemeanor" in offered_charge.lower())
        prison_avoided = ("prison" not in offered_sentence.lower() and
                          ("prison" in max_trial.lower() or "year" in max_trial.lower()))

        # Should they accept?
        # High case strength (0.7+) → lean toward trial
        # Low case strength (<0.4) → lean toward plea
        should_accept = case_strength < 0.5 or felony_reduced or prison_avoided

        # Immigration consequences
        immigration_risk = ""
        if "felony" in offered_charge.lower() or "moral turpitude" in str(offer).lower():
            immigration_risk = (
                "WARNING: Felony conviction and many misdemeanor convictions may result in "
                "deportation, inadmissibility, or bars to naturalization for non-citizens. "
                "Must consult immigration counsel BEFORE entering any plea."
            )

        # Licensing
        licensing = ""
        if crime_type in ("fraud", "financial", "drug"):
            licensing = (
                f"Professional licensing consequences: {crime_type.title()} convictions may result "
                f"in loss of professional licenses (law, medicine, finance, teaching). "
                f"Check with relevant licensing board."
            )

        # Collateral consequences
        collateral = [
            "Criminal record — employment background checks",
            "Federal firearms prohibition (18 U.S.C. § 922(g)) for felony convictions",
            "Jury service exclusion",
        ]

        if immigration_risk:
            collateral.append("IMMIGRATION: Possible deportation risk — consult immigration attorney")

        # Negotiation opportunities
        negotiation_ops = [
            "Request deferred prosecution or diversion program (avoid conviction)",
            "Request specific sentence recommendation from government",
            "Negotiate cooperation agreement for sentence reduction",
            "Request concurrent vs. consecutive sentences",
            "Request judicial recommendation of rehabilitation programs",
            "Argue for minor role adjustment (USSG § 3B1.2) if applicable",
        ]

        if case_strength >= 0.7:
            recommendation = (
                f"Defense has significant strengths ({case_strength:.0%} acquittal likelihood). "
                f"Strongly consider proceeding to trial. Reject or significantly improve plea offer."
            )
            should_accept = False
        elif case_strength >= 0.5:
            recommendation = (
                f"Case has some merit ({case_strength:.0%} acquittal likelihood). "
                f"{'Felony-to-misdemeanor reduction is valuable — consider accepting.' if felony_reduced else 'Negotiate improved terms before accepting.'}"
            )
        else:
            recommendation = (
                f"Trial risk is high ({1-case_strength:.0%} conviction likelihood). "
                f"{'Strong recommendation to accept — significant sentence reduction achieved.' if prison_avoided or felony_reduced else 'Seriously consider accepting to limit exposure.'}"
            )

        return PleaAnalysis(
            should_accept=should_accept,
            recommended_plea=recommendation,
            trial_risk=f"Estimated {(1-case_strength)*100:.0f}% conviction probability; exposure: {max_trial}",
            plea_benefit=f"Reduced to: {offered_charge}; sentence: {offered_sentence}",
            collateral_consequences=collateral,
            negotiation_opportunities=negotiation_ops,
            immigration_consequences=immigration_risk,
            licensing_consequences=licensing,
            strength_of_case_against_client=1 - case_strength,
        )

    def sentencing_guidelines_calculator(
        self,
        offense: str,
        criminal_history_points: int,
        adjustments: Optional[dict] = None
    ) -> SentencingRange:
        """
        Calculate federal sentencing guidelines range.

        Args:
            offense: Offense type (used to determine base offense level).
            criminal_history_points: Number of criminal history points.
            adjustments: Dict of adjustments (e.g., {"role_adjustment": -2, "acceptance": -3}).

        Returns:
            SentencingRange with guideline range and departure grounds.

        Example:
            >>> engine = CriminalDefenseEngine()
            >>> result = engine.sentencing_guidelines_calculator(
            ...     "wire fraud", 0, {"acceptance_of_responsibility": -3}
            ... )
            >>> result.offense_level > 0
            True
        """
        adjustments = adjustments or {}

        # Base offense levels by offense type
        base_offense_levels: Dict[str, int] = {
            "wire fraud": 7,
            "mail fraud": 7,
            "drug distribution": 24,
            "drug possession": 12,
            "money laundering": 20,
            "conspiracy": 20,
            "robbery": 20,
            "assault": 14,
            "theft": 6,
            "identity theft": 6,
            "tax evasion": 6,
            "bribery": 10,
            "felon in possession": 14,
            "immigration offense": 8,
            "sexual abuse": 30,
            "computer fraud": 6,
            "securities fraud": 7,
        }

        offense_lower = offense.lower()
        base_level = 10  # Default if not found

        for key, level in base_offense_levels.items():
            if key in offense_lower or offense_lower in key:
                base_level = level
                break

        # Apply specific offense characteristics
        loss_amount = adjustments.get("loss_amount", 0)
        if loss_amount > 0:
            if loss_amount > 9500000:
                base_level += 18
            elif loss_amount > 1500000:
                base_level += 14
            elif loss_amount > 250000:
                base_level += 10
            elif loss_amount > 40000:
                base_level += 6
            elif loss_amount > 6500:
                base_level += 2

        # Role adjustments
        role = adjustments.get("role_adjustment", 0)
        base_level += role

        # Obstruction of justice
        if adjustments.get("obstruction", False):
            base_level += 2

        # Acceptance of responsibility
        if adjustments.get("acceptance_of_responsibility", False):
            base_level -= 2
            if adjustments.get("timely_notification", False):
                base_level -= 1

        # Victim adjustments
        if adjustments.get("vulnerable_victim", False):
            base_level += 2
        if adjustments.get("mass_marketing", False):
            base_level += 2

        # Clamp to valid range
        base_level = max(1, min(43, base_level))

        # Criminal history category
        if criminal_history_points <= 1:
            ch_cat = "I"
        elif criminal_history_points <= 3:
            ch_cat = "II"
        elif criminal_history_points <= 6:
            ch_cat = "III"
        elif criminal_history_points <= 9:
            ch_cat = "IV"
        elif criminal_history_points <= 12:
            ch_cat = "V"
        else:
            ch_cat = "VI"

        # Find closest offense level in table
        closest_level = min(SENTENCING_GUIDELINES_TABLE.keys(), key=lambda x: abs(x - base_level))
        range_tuple = SENTENCING_GUIDELINES_TABLE[closest_level].get(ch_cat, (12, 18))

        if range_tuple[0] == range_tuple[1] == 0 and base_level == 43:
            range_str = "Life imprisonment"
        else:
            range_str = f"{range_tuple[0]}-{range_tuple[1]} months"

        # Departure grounds
        departures = [
            "Substantial assistance to government (USSG § 5K1.1) — can reduce below guidelines",
            "Safety valve (21 U.S.C. § 3553(f)) — for certain drug offenses, first offenders",
            "Aberrant behavior (USSG § 5K2.20) — single, spontaneous act",
            "Family circumstances (USSG § 5H1.6) — extraordinary family responsibilities",
            "Acceptance of responsibility and early cooperation",
            "Post-offense rehabilitation (Pepper v. United States, 562 U.S. 476 (2011))",
        ]

        variances = [
            "Section 3553(a) factors: nature of offense, history/characteristics of defendant",
            "Booker variance — guidelines are advisory (United States v. Booker, 543 U.S. 220 (2005))",
            "Below-guidelines sentence based on extraordinary cooperation or rehabilitation",
            "Above-guidelines sentence if guidelines inadequate to reflect seriousness",
        ]

        return SentencingRange(
            offense_level=base_level,
            criminal_history_category=ch_cat,
            guidelines_range_months=range_tuple,
            guidelines_range_string=range_str,
            statutory_maximum=f"Research statutory maximum for {offense}",
            mandatory_minimum=None,
            departure_grounds=departures,
            variance_arguments=variances,
            probation_eligible=base_level <= 10 and ch_cat in ("I", "II"),
        )
