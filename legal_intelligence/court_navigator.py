"""
Court Navigator Module — SintraPrime Legal Intelligence System

Complete knowledge of the US court system and major international tribunals.
Guides clients to the correct court, filing requirements, and appellate paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
try:
    from legal_intelligence.practice_areas import LegalMatter, PracticeArea
except ImportError:
    from practice_areas import LegalMatter, PracticeArea


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class CourtRecommendation:
    """
    Recommendation for which court to file in.

    Example:
        >>> rec = CourtRecommendation(
        ...     court="U.S. District Court, S.D.N.Y.",
        ...     court_type="federal_district",
        ...     basis="Federal question jurisdiction — 28 U.S.C. § 1331",
        ...     confidence=0.95,
        ...     alternative_courts=["New York Supreme Court (state)"],
        ...     notes="Diversity jurisdiction also available if amount > $75,000"
        ... )
    """
    court: str
    court_type: str
    basis: str
    confidence: float
    alternative_courts: List[str] = field(default_factory=list)
    notes: str = ""
    filing_deadline_days: Optional[int] = None


@dataclass
class FilingRequirements:
    """
    Court-specific filing requirements and rules.

    Example:
        >>> req = FilingRequirements(
        ...     court="U.S. District Court, S.D.N.Y.",
        ...     filing_fee=402.0,
        ...     page_limits={"motion": 25, "brief": 25, "reply": 10},
        ...     font_requirements="12-point Times New Roman or Courier",
        ...     margin_requirements="1 inch all sides",
        ...     electronic_filing=True
        ... )
    """
    court: str
    filing_fee: float
    page_limits: Dict[str, int]
    font_requirements: str
    margin_requirements: str
    electronic_filing: bool
    deadlines: Dict[str, str] = field(default_factory=dict)
    special_requirements: List[str] = field(default_factory=list)
    local_rules_url: str = ""


@dataclass
class TimelineEstimate:
    """
    Realistic case duration estimate by court and matter type.

    Example:
        >>> est = TimelineEstimate(
        ...     court="U.S. District Court",
        ...     matter_type="employment_discrimination",
        ...     min_months=18,
        ...     max_months=36,
        ...     median_months=24,
        ...     key_milestones=["Initial disclosures: 14 days", "Discovery: 6 months"]
        ... )
    """
    court: str
    matter_type: str
    min_months: int
    max_months: int
    median_months: int
    key_milestones: List[str] = field(default_factory=list)
    factors_that_extend: List[str] = field(default_factory=list)


@dataclass
class JurisdictionAnalysis:
    """
    Analysis of whether federal or state court has jurisdiction.

    Example:
        >>> analysis = JurisdictionAnalysis(
        ...     has_federal_jurisdiction=True,
        ...     jurisdictional_basis=["Federal question (28 U.S.C. § 1331)"],
        ...     diversity_jurisdiction=False,
        ...     amount_in_controversy=50000.0,
        ...     recommended_forum="Federal",
        ...     state_court_viable=True
        ... )
    """
    has_federal_jurisdiction: bool
    jurisdictional_basis: List[str]
    diversity_jurisdiction: bool
    amount_in_controversy: float
    recommended_forum: str  # "Federal" | "State" | "Either"
    state_court_viable: bool
    federal_question_basis: str = ""
    supplemental_jurisdiction: bool = False
    notes: str = ""


@dataclass
class CourtFiling:
    """
    Tracks an active court filing and its status.

    Example:
        >>> filing = CourtFiling(
        ...     court="U.S. District Court, N.D. Cal.",
        ...     docket_number="5:24-cv-01234-EJD",
        ...     filing_date="2024-03-15",
        ...     deadline="2024-04-15",
        ...     status="pending_service",
        ...     next_action="Complete service of process within 90 days"
        ... )
    """
    court: str
    docket_number: str
    filing_date: str
    deadline: str
    status: str
    next_action: str
    assigned_judge: str = ""
    case_type: str = ""
    parties: Dict[str, str] = field(default_factory=dict)
    pending_motions: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Court Data
# ---------------------------------------------------------------------------

FEDERAL_CIRCUITS: Dict[str, Dict] = {
    "1st_circuit": {
        "name": "U.S. Court of Appeals for the First Circuit",
        "states": ["Maine", "Massachusetts", "New Hampshire", "Rhode Island", "Puerto Rico"],
        "location": "Boston, MA",
        "judges": 6,
        "district_courts": ["D. Me.", "D. Mass.", "D.N.H.", "D.R.I.", "D.P.R."],
    },
    "2nd_circuit": {
        "name": "U.S. Court of Appeals for the Second Circuit",
        "states": ["Connecticut", "New York", "Vermont"],
        "location": "New York, NY",
        "judges": 13,
        "district_courts": ["D. Conn.", "E.D.N.Y.", "N.D.N.Y.", "S.D.N.Y.", "W.D.N.Y.", "D. Vt."],
    },
    "3rd_circuit": {
        "name": "U.S. Court of Appeals for the Third Circuit",
        "states": ["Delaware", "New Jersey", "Pennsylvania", "Virgin Islands"],
        "location": "Philadelphia, PA",
        "judges": 14,
        "district_courts": ["D. Del.", "D.N.J.", "E.D. Pa.", "M.D. Pa.", "W.D. Pa.", "D.V.I."],
    },
    "4th_circuit": {
        "name": "U.S. Court of Appeals for the Fourth Circuit",
        "states": ["Maryland", "North Carolina", "South Carolina", "Virginia", "West Virginia"],
        "location": "Richmond, VA",
        "judges": 15,
        "district_courts": ["D. Md.", "E.D.N.C.", "M.D.N.C.", "W.D.N.C.", "D.S.C.", "E.D. Va.",
                            "W.D. Va.", "N.D.W. Va.", "S.D.W. Va."],
    },
    "5th_circuit": {
        "name": "U.S. Court of Appeals for the Fifth Circuit",
        "states": ["Louisiana", "Mississippi", "Texas"],
        "location": "New Orleans, LA",
        "judges": 17,
        "district_courts": ["E.D. La.", "M.D. La.", "W.D. La.", "N.D. Miss.", "S.D. Miss.",
                            "E.D. Tex.", "N.D. Tex.", "S.D. Tex.", "W.D. Tex."],
    },
    "6th_circuit": {
        "name": "U.S. Court of Appeals for the Sixth Circuit",
        "states": ["Kentucky", "Michigan", "Ohio", "Tennessee"],
        "location": "Cincinnati, OH",
        "judges": 16,
        "district_courts": ["E.D. Ky.", "W.D. Ky.", "E.D. Mich.", "W.D. Mich.", "N.D. Ohio",
                            "S.D. Ohio", "E.D. Tenn.", "M.D. Tenn.", "W.D. Tenn."],
    },
    "7th_circuit": {
        "name": "U.S. Court of Appeals for the Seventh Circuit",
        "states": ["Illinois", "Indiana", "Wisconsin"],
        "location": "Chicago, IL",
        "judges": 11,
        "district_courts": ["C.D. Ill.", "N.D. Ill.", "S.D. Ill.", "N.D. Ind.", "S.D. Ind.",
                            "E.D. Wis.", "W.D. Wis."],
    },
    "8th_circuit": {
        "name": "U.S. Court of Appeals for the Eighth Circuit",
        "states": ["Arkansas", "Iowa", "Minnesota", "Missouri", "Nebraska", "North Dakota", "South Dakota"],
        "location": "St. Louis, MO",
        "judges": 11,
        "district_courts": ["E.D. Ark.", "W.D. Ark.", "N.D. Iowa", "S.D. Iowa", "D. Minn.",
                            "E.D. Mo.", "W.D. Mo.", "D. Neb.", "D.N.D.", "D.S.D."],
    },
    "9th_circuit": {
        "name": "U.S. Court of Appeals for the Ninth Circuit",
        "states": ["Alaska", "Arizona", "California", "Hawaii", "Idaho", "Montana",
                   "Nevada", "Oregon", "Washington", "Guam", "Northern Mariana Islands"],
        "location": "San Francisco, CA",
        "judges": 29,
        "district_courts": ["D. Alaska", "D. Ariz.", "C.D. Cal.", "E.D. Cal.", "N.D. Cal.",
                            "S.D. Cal.", "D. Haw.", "D. Idaho", "D. Mont.", "D. Nev.",
                            "D. Or.", "E.D. Wash.", "W.D. Wash.", "D. Guam", "D. N. Mar. I."],
    },
    "10th_circuit": {
        "name": "U.S. Court of Appeals for the Tenth Circuit",
        "states": ["Colorado", "Kansas", "New Mexico", "Oklahoma", "Utah", "Wyoming"],
        "location": "Denver, CO",
        "judges": 12,
        "district_courts": ["D. Colo.", "D. Kan.", "D.N.M.", "E.D. Okla.", "N.D. Okla.",
                            "W.D. Okla.", "D. Utah", "D. Wyo."],
    },
    "11th_circuit": {
        "name": "U.S. Court of Appeals for the Eleventh Circuit",
        "states": ["Alabama", "Florida", "Georgia"],
        "location": "Atlanta, GA",
        "judges": 12,
        "district_courts": ["M.D. Ala.", "N.D. Ala.", "S.D. Ala.", "M.D. Fla.", "N.D. Fla.",
                            "S.D. Fla.", "M.D. Ga.", "N.D. Ga.", "S.D. Ga."],
    },
    "dc_circuit": {
        "name": "U.S. Court of Appeals for the D.C. Circuit",
        "states": ["District of Columbia"],
        "location": "Washington, D.C.",
        "judges": 11,
        "district_courts": ["D.D.C."],
        "note": "Primary court for federal agency review",
    },
    "federal_circuit": {
        "name": "U.S. Court of Appeals for the Federal Circuit",
        "states": ["Nationwide"],
        "location": "Washington, D.C.",
        "judges": 12,
        "district_courts": ["Subject matter jurisdiction: patents, trade, federal claims"],
        "note": "Patents, international trade, government contracts, Merit Systems Protection Board",
    },
}

SPECIALIZED_FEDERAL_COURTS: Dict[str, Dict] = {
    "us_tax_court": {
        "name": "United States Tax Court",
        "location": "Washington, D.C.",
        "jurisdiction": "Federal tax disputes; no jury; 19 judges",
        "filing_fee": 60.0,
        "typical_timeline_months": (12, 36),
        "filing_deadline": "90 days from IRS notice of deficiency (150 days if abroad)",
        "small_case_limit": 50000,
        "url": "https://www.ustaxcourt.gov",
    },
    "us_court_of_federal_claims": {
        "name": "U.S. Court of Federal Claims",
        "location": "Washington, D.C.",
        "jurisdiction": "Money claims against federal government over $10,000; government contracts",
        "filing_fee": 402.0,
        "typical_timeline_months": (18, 48),
        "appeal_to": "Federal Circuit",
        "url": "https://www.uscfc.uscourts.gov",
    },
    "us_court_of_international_trade": {
        "name": "U.S. Court of International Trade",
        "location": "New York, NY",
        "jurisdiction": "Customs, tariffs, import/export disputes",
        "filing_fee": 350.0,
        "typical_timeline_months": (12, 36),
        "appeal_to": "Federal Circuit",
        "url": "https://www.cit.uscourts.gov",
    },
    "us_bankruptcy_court": {
        "name": "U.S. Bankruptcy Court",
        "location": "Each federal district",
        "jurisdiction": "Title 11 bankruptcy proceedings",
        "filing_fee": {
            "chapter_7": 338.0,
            "chapter_11": 1738.0,
            "chapter_13": 313.0,
        },
        "appeal_to": "District Court or Bankruptcy Appellate Panel (BAP)",
        "url": "https://www.uscourts.gov/court-locator/court-type/us-bankruptcy-courts",
    },
    "foreign_intelligence_surveillance_court": {
        "name": "Foreign Intelligence Surveillance Court (FISC)",
        "location": "Washington, D.C.",
        "jurisdiction": "Foreign intelligence surveillance warrants",
        "note": "Secret court; government applies ex parte",
    },
    "us_court_of_appeals_for_armed_forces": {
        "name": "U.S. Court of Appeals for the Armed Forces",
        "location": "Washington, D.C.",
        "jurisdiction": "Military justice; reviews Courts-Martial",
        "appeal_to": "Supreme Court (certiorari)",
    },
}

ADMINISTRATIVE_TRIBUNALS: Dict[str, Dict] = {
    "nlrb": {
        "name": "National Labor Relations Board",
        "jurisdiction": "Unfair labor practices; union elections",
        "filing_deadline": "6 months from unfair labor practice",
        "process": "Regional Director investigation → ALJ hearing → Board review → Circuit Court",
        "url": "https://www.nlrb.gov",
    },
    "eeoc": {
        "name": "Equal Employment Opportunity Commission",
        "jurisdiction": "Employment discrimination (Title VII, ADA, ADEA, EPA)",
        "filing_deadline": "180 days (300 days in deferral states)",
        "process": "Charge → Investigation → Mediation/Conciliation → Right-to-Sue",
        "url": "https://www.eeoc.gov",
    },
    "ssa_alj": {
        "name": "Social Security Administration ALJ Hearings",
        "jurisdiction": "SSDI and SSI disability appeals",
        "filing_deadline": "60 days from denial + 5 days mail",
        "process": "Initial denial → Reconsideration → ALJ Hearing → Appeals Council → Federal Court",
        "url": "https://www.ssa.gov/appeals",
    },
    "va_board": {
        "name": "Board of Veterans' Appeals",
        "jurisdiction": "VA disability, benefits, and pension appeals",
        "filing_deadline": "1 year from denial notice",
        "process": "VBA denial → BVA appeal → CAVC → Federal Circuit → SCOTUS",
        "url": "https://www.bva.va.gov",
    },
    "ptab": {
        "name": "Patent Trial and Appeal Board (USPTO)",
        "jurisdiction": "Patent validity challenges; IPR, PGR, CBM proceedings",
        "filing_deadline": "IPR: 1 year from service of infringement complaint",
        "process": "Petition → Institution decision → Trial → Final Written Decision → Federal Circuit",
        "url": "https://www.uspto.gov/patents/ptab",
    },
    "ftc_alj": {
        "name": "Federal Trade Commission ALJ",
        "jurisdiction": "Antitrust, consumer protection enforcement",
        "process": "Complaint → ALJ hearing → Commission review → Circuit Court",
        "url": "https://www.ftc.gov",
    },
    "sec_alj": {
        "name": "SEC Administrative Law Judges",
        "jurisdiction": "Securities enforcement actions",
        "note": "After Lucia v. SEC (2018), SEC restructured appointment of ALJs",
        "url": "https://www.sec.gov/alj",
    },
    "irs_appeals": {
        "name": "IRS Independent Office of Appeals",
        "jurisdiction": "Tax audit disputes, collections, lien/levy",
        "process": "Exam → 30/90-day letter → Appeals → Tax Court/District Court",
        "url": "https://www.irs.gov/appeals",
    },
    "eoir": {
        "name": "Executive Office for Immigration Review (Immigration Court)",
        "jurisdiction": "Removal proceedings; asylum; withholding",
        "process": "NTA → Master Calendar → Merits Hearing → BIA → Circuit Court",
        "url": "https://www.justice.gov/eoir",
    },
    "mspb": {
        "name": "Merit Systems Protection Board",
        "jurisdiction": "Federal employee adverse actions, whistleblower retaliation",
        "filing_deadline": "30 days from effective date of action",
        "process": "Initial appeal → AJ decision → Board review → Federal Circuit",
        "url": "https://www.mspb.gov",
    },
}

INTERNATIONAL_TRIBUNALS: Dict[str, Dict] = {
    "icc": {
        "name": "International Criminal Court",
        "location": "The Hague, Netherlands",
        "jurisdiction": "Genocide, crimes against humanity, war crimes, aggression",
        "standard_of_proof": "Beyond reasonable doubt",
        "url": "https://www.icc-cpi.int",
    },
    "icj": {
        "name": "International Court of Justice",
        "location": "The Hague, Netherlands",
        "jurisdiction": "State-to-state disputes; advisory opinions",
        "note": "Only states can be parties; consent-based jurisdiction",
        "url": "https://www.icj-cij.org",
    },
    "wto_dsb": {
        "name": "WTO Dispute Settlement Body",
        "location": "Geneva, Switzerland",
        "jurisdiction": "International trade disputes between WTO members",
        "process": "Consultations → Panel → Appellate Body → Arbitration",
        "url": "https://www.wto.org/dispute",
    },
    "icsid": {
        "name": "International Centre for Settlement of Investment Disputes",
        "location": "Washington, D.C.",
        "jurisdiction": "Investment treaty arbitration between investors and states",
        "url": "https://icsid.worldbank.org",
    },
    "echr": {
        "name": "European Court of Human Rights",
        "location": "Strasbourg, France",
        "jurisdiction": "Human rights violations by Council of Europe member states",
        "note": "US is not a member; relevant for cases involving European nations",
        "url": "https://www.echr.coe.int",
    },
    "iachr": {
        "name": "Inter-American Court of Human Rights",
        "location": "San José, Costa Rica",
        "jurisdiction": "Human rights in Americas (OAS member states)",
        "url": "https://www.corteidh.or.cr",
    },
    "pca": {
        "name": "Permanent Court of Arbitration",
        "location": "The Hague, Netherlands",
        "jurisdiction": "International arbitration — states, state entities, private parties",
        "url": "https://www.pca-cpa.org",
    },
}

# ---------------------------------------------------------------------------
# Local Rules Data
# ---------------------------------------------------------------------------

COURT_LOCAL_RULES: Dict[str, Dict] = {
    "S.D.N.Y.": {
        "name": "Southern District of New York",
        "local_rules_url": "https://www.nysd.uscourts.gov/rules",
        "page_limits": {"motion": 25, "opposition": 25, "reply": 10},
        "font": "12-point Times New Roman",
        "margins": "1 inch all sides",
        "line_spacing": "Double-spaced",
        "electronic_filing": True,
        "cm_ecf": True,
        "individual_judge_rules": "Each judge maintains Individual Practices — MUST consult",
        "pre_motion_conference": "Required for most motions per Judge's Individual Rules",
        "note": "Individual Practice Rules are mandatory; check judge's page on court website",
    },
    "N.D. Cal.": {
        "name": "Northern District of California",
        "local_rules_url": "https://www.cand.uscourts.gov/rules",
        "page_limits": {"motion": 25, "opposition": 25, "reply": 15},
        "font": "12-point font",
        "margins": "1 inch all sides",
        "electronic_filing": True,
        "standing_orders": "Each judge has standing orders — mandatory review",
        "adr": "ADR multi-option program mandatory",
    },
    "N.D. Tex.": {
        "name": "Northern District of Texas",
        "local_rules_url": "https://www.txnd.uscourts.gov/local-rules",
        "page_limits": {"brief": 25},
        "font": "12-point font",
        "margins": "1 inch all sides",
        "electronic_filing": True,
        "note": "Certificate of Conference required for discovery disputes",
    },
    "D.D.C.": {
        "name": "District of Columbia District Court",
        "local_rules_url": "https://www.dcd.uscourts.gov/local-rules-and-orders",
        "page_limits": {"motion": 45, "opposition": 45, "reply": 25},
        "font": "12-point font",
        "margins": "1 inch all sides",
        "electronic_filing": True,
        "note": "Important for APA/federal agency cases",
    },
    "C.D. Cal.": {
        "name": "Central District of California",
        "local_rules_url": "https://www.cacd.uscourts.gov/local-rules",
        "page_limits": {"motion": 25, "opposition": 25, "reply": 12},
        "font": "14-point",
        "margins": "1 inch all sides",
        "electronic_filing": True,
        "note": "Strict page limits; no footnote workarounds",
    },
}


# ---------------------------------------------------------------------------
# Court Navigator
# ---------------------------------------------------------------------------

class CourtNavigator:
    """
    Complete knowledge of the US court system and major international tribunals.

    Routes clients to the correct court, explains filing requirements, maps
    appellate paths, and estimates realistic case timelines.

    Example:
        >>> nav = CourtNavigator()
        >>> try:
    from legal_intelligence.practice_areas import LegalMatter, PracticeArea
except ImportError:
    from practice_areas import LegalMatter, PracticeArea
        >>> matter = LegalMatter(
        ...     description="Patent infringement",
        ...     practice_area=PracticeArea.INTELLECTUAL_PROPERTY,
        ...     confidence=0.9
        ... )
        >>> rec = nav.find_correct_court(matter, state="California")
        >>> "District" in rec.court or "Federal" in rec.court
        True
    """

    FEDERAL_PRACTICE_AREAS = {
        PracticeArea.IMMIGRATION,
        PracticeArea.BANKRUPTCY,
        PracticeArea.INTELLECTUAL_PROPERTY,
        PracticeArea.SECURITIES_LAW,
        PracticeArea.ENVIRONMENTAL_LAW,
        PracticeArea.CONSTITUTIONAL_LAW,
        PracticeArea.ADMINISTRATIVE_LAW,
        PracticeArea.TAX_LAW,
        PracticeArea.INTERNATIONAL_LAW,
        PracticeArea.CRIMINAL_DEFENSE,
    }

    STATE_CIRCUIT_MAP: Dict[str, str] = {
        # Map state → circuit
        "Maine": "1st", "Massachusetts": "1st", "New Hampshire": "1st",
        "Rhode Island": "1st", "Puerto Rico": "1st",
        "Connecticut": "2nd", "New York": "2nd", "Vermont": "2nd",
        "Delaware": "3rd", "New Jersey": "3rd", "Pennsylvania": "3rd",
        "Maryland": "4th", "North Carolina": "4th", "South Carolina": "4th",
        "Virginia": "4th", "West Virginia": "4th",
        "Louisiana": "5th", "Mississippi": "5th", "Texas": "5th",
        "Kentucky": "6th", "Michigan": "6th", "Ohio": "6th", "Tennessee": "6th",
        "Illinois": "7th", "Indiana": "7th", "Wisconsin": "7th",
        "Arkansas": "8th", "Iowa": "8th", "Minnesota": "8th",
        "Missouri": "8th", "Nebraska": "8th", "North Dakota": "8th", "South Dakota": "8th",
        "Alaska": "9th", "Arizona": "9th", "California": "9th", "Hawaii": "9th",
        "Idaho": "9th", "Montana": "9th", "Nevada": "9th", "Oregon": "9th",
        "Washington": "9th",
        "Colorado": "10th", "Kansas": "10th", "New Mexico": "10th",
        "Oklahoma": "10th", "Utah": "10th", "Wyoming": "10th",
        "Alabama": "11th", "Florida": "11th", "Georgia": "11th",
        "District of Columbia": "DC",
    }

    def find_correct_court(self, matter: LegalMatter, state: Optional[str] = None) -> CourtRecommendation:
        """
        Recommend the correct court to file in based on the matter and state.

        Args:
            matter: Classified legal matter.
            state: State where the plaintiff/action is located.

        Returns:
            CourtRecommendation with court name, basis, and alternatives.

        Example:
            >>> nav = CourtNavigator()
            >>> try:
    from legal_intelligence.practice_areas import LegalMatter, PracticeArea
except ImportError:
    from practice_areas import LegalMatter, PracticeArea
            >>> matter = LegalMatter("Tax dispute with IRS", PracticeArea.TAX_LAW, 0.9)
            >>> rec = nav.find_correct_court(matter)
            >>> "Tax Court" in rec.court or "District" in rec.court
            True
        """
        area = matter.practice_area

        # Specialized court routing
        if area == PracticeArea.TAX_LAW:
            return CourtRecommendation(
                court="United States Tax Court",
                court_type="specialized_federal",
                basis="Tax Court has exclusive jurisdiction over pre-payment deficiency challenges (26 U.S.C. § 6213).",
                confidence=0.92,
                alternative_courts=[
                    "U.S. District Court (pay tax first, then sue for refund)",
                    "U.S. Court of Federal Claims (pay tax first)",
                ],
                notes="File within 90 days of IRS Notice of Deficiency. Small Tax Case procedure available for disputes ≤ $50,000.",
            )

        if area == PracticeArea.BANKRUPTCY:
            circuit = self.STATE_CIRCUIT_MAP.get(state or "", "9th")
            return CourtRecommendation(
                court=f"U.S. Bankruptcy Court ({state or 'your district'})",
                court_type="specialized_federal",
                basis="Exclusive federal jurisdiction over bankruptcy proceedings. 28 U.S.C. § 1334.",
                confidence=0.99,
                notes="File in district where debtor's domicile, residence, or principal assets are located for 180 days prior.",
            )

        if area == PracticeArea.INTELLECTUAL_PROPERTY:
            return CourtRecommendation(
                court=f"U.S. District Court ({state or 'your district'}) — Patent/IP Division",
                court_type="federal_district",
                basis="Patent, copyright, and trademark claims arise under federal law (28 U.S.C. § 1338).",
                confidence=0.95,
                alternative_courts=[
                    "ITC (International Trade Commission) for import-related patent cases",
                    "USPTO PTAB for patent validity challenges",
                ],
                notes="Federal Circuit has exclusive appellate jurisdiction over patent cases.",
            )

        if area == PracticeArea.IMMIGRATION:
            return CourtRecommendation(
                court="Immigration Court (EOIR) — Executive Office for Immigration Review",
                court_type="administrative",
                basis="Removal proceedings are before EOIR immigration courts under 8 U.S.C. § 1229a.",
                confidence=0.95,
                alternative_courts=[
                    "USCIS (for affirmative applications)",
                    "Federal District Court (habeas corpus)",
                    f"{self.STATE_CIRCUIT_MAP.get(state or '', '9th')}th Circuit Court of Appeals (BIA appeals)",
                ],
                notes="BIA appeal → Circuit Court of Appeals → SCOTUS certiorari.",
            )

        if area == PracticeArea.SECURITIES_LAW:
            return CourtRecommendation(
                court=f"U.S. District Court, {state or 'S.D.N.Y.'} (preferred for securities litigation)",
                court_type="federal_district",
                basis="Securities Exchange Act § 27 provides exclusive federal jurisdiction for most securities fraud claims.",
                confidence=0.90,
                alternative_courts=["SEC Administrative Proceeding (enforcement only)"],
                notes="PSLRA requires early lead plaintiff motion within 60 days of first notice.",
            )

        if area == PracticeArea.ADMINISTRATIVE_LAW:
            return CourtRecommendation(
                court="U.S. District Court, District of Columbia (D.D.C.)",
                court_type="federal_district",
                basis="APA review of federal agency action. 5 U.S.C. § 706. D.C. Circuit preferred for agency cases.",
                confidence=0.85,
                alternative_courts=[
                    "Circuit Court of Appeals (direct review for some agencies)",
                    "Court of Federal Claims (money damages against government)",
                ],
                notes="Exhaust administrative remedies first. 6-year APA statute of limitations.",
            )

        # Civil rights — often federal but can be state
        if area == PracticeArea.CIVIL_RIGHTS:
            circuit = self.STATE_CIRCUIT_MAP.get(state or "", "9th")
            return CourtRecommendation(
                court=f"U.S. District Court ({state or 'your district'})",
                court_type="federal_district",
                basis="42 U.S.C. § 1983 claims arise under federal law; 28 U.S.C. § 1331 federal question jurisdiction.",
                confidence=0.88,
                alternative_courts=[f"{state} state court (§ 1983 can be filed in state court)"],
                notes=f"Located in {circuit}th Circuit. File in district where violation occurred.",
            )

        # Employment — must exhaust EEOC first
        if area == PracticeArea.EMPLOYMENT_LAW:
            return CourtRecommendation(
                court=f"U.S. District Court ({state or 'your district'}) or State Court",
                court_type="federal_or_state",
                basis="Title VII/ADA/ADEA — federal question after EEOC right-to-sue. State law claims may be in state court.",
                confidence=0.82,
                alternative_courts=[
                    "EEOC (must file charge first for federal claims)",
                    f"{state} state employment agency / state court",
                ],
                notes="Must obtain EEOC right-to-sue before filing federal employment discrimination lawsuit.",
                filing_deadline_days=90,
            )

        # Criminal — depends on federal vs. state charges
        if area == PracticeArea.CRIMINAL_DEFENSE:
            return CourtRecommendation(
                court=f"{'U.S. District Court' if matter.federal_jurisdiction else (state or 'State') + ' Superior/Circuit Court'}",
                court_type="federal_district" if matter.federal_jurisdiction else "state_trial",
                basis="Federal charges → U.S. District Court. State charges → State trial court.",
                confidence=0.90,
                alternative_courts=[],
                notes="Check whether charges are federal (indictment by grand jury) or state (information or indictment).",
            )

        # Default: state court with potential federal diversity
        state_court = f"{state or 'Your State'} Superior Court / Circuit Court"
        return CourtRecommendation(
            court=state_court,
            court_type="state_trial",
            basis="State law claims default to state court. Federal diversity jurisdiction may be available.",
            confidence=0.70,
            alternative_courts=[
                f"U.S. District Court ({state or 'your district'}) if diversity jurisdiction applies (>$75,000 + diverse parties)",
            ],
            notes="Assess whether federal diversity jurisdiction applies based on amount and parties.",
        )

    def get_filing_requirements(self, court: str) -> FilingRequirements:
        """
        Return filing requirements for a specific court.

        Args:
            court: Court identifier (e.g., "S.D.N.Y.", "N.D. Cal.").

        Returns:
            FilingRequirements with fees, page limits, font requirements, and deadlines.

        Example:
            >>> nav = CourtNavigator()
            >>> req = nav.get_filing_requirements("S.D.N.Y.")
            >>> req.filing_fee
            402.0
        """
        local = COURT_LOCAL_RULES.get(court, {})

        # Standard federal district court defaults
        defaults = FilingRequirements(
            court=court,
            filing_fee=402.0,
            page_limits=local.get("page_limits", {"motion": 25, "opposition": 25, "reply": 10}),
            font_requirements=local.get("font", "12-point Times New Roman or Courier New"),
            margin_requirements=local.get("margins", "1 inch all sides"),
            electronic_filing=local.get("electronic_filing", True),
            deadlines={
                "answer": "21 days from service (FRCP 12(a)(1)(A)(i))",
                "motion_to_dismiss": "21 days from service",
                "reply": "14 days after opposition filed",
                "discovery_close": "Set by scheduling order",
                "summary_judgment": "Per scheduling order or 30 days before trial",
            },
            special_requirements=local.get("special_requirements", [
                "Caption must include court, case number, parties, document title",
                "Certificate of service required",
                "Table of contents and authorities for briefs > 10 pages",
                "Certificate of compliance with word/page limits",
            ]),
            local_rules_url=local.get("local_rules_url", f"https://www.uscourts.gov/court-locator"),
        )

        # Specialized courts
        if "Tax Court" in court:
            return FilingRequirements(
                court=court,
                filing_fee=60.0,
                page_limits={"petition": 5, "brief": 75},
                font_requirements="12-point",
                margin_requirements="1 inch",
                electronic_filing=True,
                deadlines={
                    "petition": "90 days from IRS Notice of Deficiency",
                    "answer": "60 days from service of petition",
                },
                special_requirements=[
                    "Must attach copy of IRS Notice of Deficiency",
                    "Small Tax Case election available for ≤ $50,000 disputes",
                    "Pro se petitioners may represent themselves",
                ],
                local_rules_url="https://www.ustaxcourt.gov/rules",
            )

        if "Bankruptcy" in court:
            return FilingRequirements(
                court=court,
                filing_fee=338.0,  # Chapter 7 default
                page_limits={"motion": 20, "objection": 20},
                font_requirements="12-point",
                margin_requirements="1 inch",
                electronic_filing=True,
                deadlines={
                    "automatic_stay": "Immediate upon filing",
                    "meeting_of_creditors": "21-40 days after filing",
                    "discharge": "Chapter 7: ~60-90 days after 341 meeting",
                },
                special_requirements=[
                    "Credit counseling certificate required (180 days before filing)",
                    "Means test calculation required (Chapter 7/13)",
                    "Complete schedules: A/B, C, D, E/F, G, H, I, J",
                    "Statement of Financial Affairs",
                    "Statement of Intention (Chapter 7)",
                ],
                local_rules_url="https://www.uscourts.gov/court-locator",
            )

        if "Immigration" in court or "EOIR" in court:
            return FilingRequirements(
                court=court,
                filing_fee=0.0,
                page_limits={"brief": 50, "motion": 15},
                font_requirements="12-point, double-spaced",
                margin_requirements="1 inch",
                electronic_filing=False,
                deadlines={
                    "master_calendar_response": "At master calendar hearing",
                    "application_for_relief": "Set at master calendar or by IJ order",
                    "appeal_to_bia": "30 days from IJ decision",
                },
                special_requirements=[
                    "All foreign language documents must have certified English translation",
                    "Certificate of service by mail or personal service",
                    "Form EOIR-28 (Notice of Entry of Appearance) required",
                ],
                local_rules_url="https://www.justice.gov/eoir",
            )

        return defaults

    def get_appellate_path(self, court: str) -> List[str]:
        """
        Return the complete appellate chain from trial court to SCOTUS.

        Args:
            court: Starting court identifier.

        Returns:
            Ordered list of courts from trial → appellate → supreme.

        Example:
            >>> nav = CourtNavigator()
            >>> path = nav.get_appellate_path("S.D.N.Y.")
            >>> "Supreme Court" in path[-1]
            True
        """
        appellate_paths: Dict[str, List[str]] = {
            # Federal District Courts → Circuit → SCOTUS
            "S.D.N.Y.": [
                "U.S. District Court, Southern District of New York (S.D.N.Y.)",
                "U.S. Court of Appeals for the Second Circuit",
                "U.S. Supreme Court (certiorari — granted in ~1-2% of cases)",
            ],
            "N.D. Cal.": [
                "U.S. District Court, Northern District of California (N.D. Cal.)",
                "U.S. Court of Appeals for the Ninth Circuit",
                "U.S. Supreme Court (certiorari)",
            ],
            "N.D. Tex.": [
                "U.S. District Court, Northern District of Texas (N.D. Tex.)",
                "U.S. Court of Appeals for the Fifth Circuit",
                "U.S. Supreme Court (certiorari)",
            ],
            "D.D.C.": [
                "U.S. District Court for the District of Columbia (D.D.C.)",
                "U.S. Court of Appeals for the D.C. Circuit",
                "U.S. Supreme Court (certiorari)",
            ],
            # Specialized courts
            "Tax Court": [
                "United States Tax Court",
                "U.S. Court of Appeals (circuit where taxpayer resides)",
                "U.S. Supreme Court (certiorari)",
            ],
            "Bankruptcy Court": [
                "U.S. Bankruptcy Court",
                "U.S. District Court (or Bankruptcy Appellate Panel)",
                "U.S. Court of Appeals (applicable circuit)",
                "U.S. Supreme Court (certiorari)",
            ],
            "EOIR Immigration Court": [
                "Immigration Court (EOIR)",
                "Board of Immigration Appeals (BIA)",
                "U.S. Court of Appeals (circuit where removal hearing held)",
                "U.S. Supreme Court (certiorari)",
            ],
            "EEOC": [
                "EEOC Charge and Investigation",
                "EEOC Mediation / Right-to-Sue Letter",
                "U.S. District Court",
                "U.S. Court of Appeals (applicable circuit)",
                "U.S. Supreme Court (certiorari)",
            ],
            "SSA ALJ": [
                "Social Security ALJ Hearing",
                "SSA Appeals Council",
                "U.S. District Court",
                "U.S. Court of Appeals (applicable circuit)",
                "U.S. Supreme Court (certiorari)",
            ],
            "BVA": [
                "Board of Veterans' Appeals",
                "U.S. Court of Appeals for Veterans Claims (CAVC)",
                "U.S. Court of Appeals for the Federal Circuit",
                "U.S. Supreme Court (certiorari)",
            ],
            "PTAB": [
                "USPTO Patent Trial and Appeal Board (PTAB)",
                "U.S. Court of Appeals for the Federal Circuit",
                "U.S. Supreme Court (certiorari)",
            ],
        }

        # Try to find exact match
        for key, path in appellate_paths.items():
            if key.lower() in court.lower() or court.lower() in key.lower():
                return path

        # Default federal path based on state
        return [
            f"U.S. District Court ({court})",
            "U.S. Court of Appeals (applicable circuit)",
            "U.S. Supreme Court (certiorari — roughly 80 cases/year granted)",
        ]

    def estimate_timeline(self, court: str, matter_type: str) -> TimelineEstimate:
        """
        Estimate realistic case duration by court and matter type.

        Args:
            court: Court identifier.
            matter_type: Type of case (e.g., "employment_discrimination", "patent").

        Returns:
            TimelineEstimate with min/max/median months and key milestones.

        Example:
            >>> nav = CourtNavigator()
            >>> est = nav.estimate_timeline("S.D.N.Y.", "employment_discrimination")
            >>> est.min_months > 0
            True
        """
        timelines: Dict[str, Dict[str, TimelineEstimate]] = {
            "employment": TimelineEstimate(
                court=court, matter_type=matter_type,
                min_months=18, max_months=42, median_months=28,
                key_milestones=[
                    "EEOC charge: 0-10 months investigation",
                    "Right-to-sue: file within 90 days",
                    "Initial disclosures: 14 days after Rule 26(f)",
                    "Discovery: 6-9 months",
                    "Summary judgment: 3-6 months after discovery",
                    "Trial: 6-12 months after SJ ruling",
                ],
                factors_that_extend=["Complex damages", "Multiple defendants", "Class action"],
            ),
            "patent": TimelineEstimate(
                court=court, matter_type=matter_type,
                min_months=24, max_months=60, median_months=36,
                key_milestones=[
                    "Claim construction (Markman) hearing: 6-12 months",
                    "Discovery: 12-18 months",
                    "Expert reports: 2-3 months",
                    "Summary judgment: 2-4 months",
                    "Trial: 6-12 months after SJ",
                ],
                factors_that_extend=["IPR proceedings", "Multiple patents", "Complex technology"],
            ),
            "criminal": TimelineEstimate(
                court=court, matter_type=matter_type,
                min_months=6, max_months=36, median_months=14,
                key_milestones=[
                    "Arraignment: within days of indictment",
                    "Speedy Trial Act: 70 days from indictment to trial (18 U.S.C. § 3161)",
                    "Discovery: 2-6 months",
                    "Suppression motions: 2-4 months",
                    "Plea negotiations: ongoing",
                    "Trial: varies",
                ],
                factors_that_extend=["Complexity of charges", "Multiple defendants", "Foreign evidence"],
            ),
            "immigration": TimelineEstimate(
                court=court, matter_type=matter_type,
                min_months=12, max_months=60, median_months=30,
                key_milestones=[
                    "Master Calendar Hearing: 1-6 months",
                    "Application for relief filed: at or after MCH",
                    "Merits hearing: 6-24 months",
                    "BIA appeal: 12-24 months",
                    "Circuit Court: 12-24 additional months",
                ],
                factors_that_extend=["Government backlog", "BIA appeals", "Circuit Court review"],
            ),
            "contract": TimelineEstimate(
                court=court, matter_type=matter_type,
                min_months=12, max_months=36, median_months=20,
                key_milestones=[
                    "Initial disclosures: 2 weeks after conference",
                    "Discovery: 4-8 months",
                    "Summary judgment: 3-4 months",
                    "Trial: 6-12 months after SJ",
                ],
                factors_that_extend=["Complex damages calculations", "International parties", "Multiple contracts"],
            ),
            "bankruptcy": TimelineEstimate(
                court=court, matter_type=matter_type,
                min_months=3, max_months=36, median_months=6,
                key_milestones=[
                    "Chapter 7 discharge: 3-6 months from filing",
                    "Chapter 13 plan confirmation: 3-6 months",
                    "Chapter 13 completion: 3-5 years",
                    "Chapter 11 plan confirmation: 12-36 months",
                ],
                factors_that_extend=["Creditor objections", "Asset sales", "Litigation in case"],
            ),
        }

        for key, estimate in timelines.items():
            if key in matter_type.lower():
                return TimelineEstimate(
                    court=court,
                    matter_type=matter_type,
                    min_months=estimate.min_months,
                    max_months=estimate.max_months,
                    median_months=estimate.median_months,
                    key_milestones=estimate.key_milestones,
                    factors_that_extend=estimate.factors_that_extend,
                )

        # Generic federal civil timeline
        return TimelineEstimate(
            court=court, matter_type=matter_type,
            min_months=12, max_months=36, median_months=22,
            key_milestones=[
                "Rule 26(f) conference: within 21 days of defendant's appearance",
                "Initial disclosures: 14 days after Rule 26(f)",
                "Discovery close: typically 6-9 months from scheduling order",
                "Summary judgment: 2-4 months after discovery",
                "Pretrial conference: 30-60 days before trial",
                "Trial: per judge's schedule",
            ],
            factors_that_extend=[
                "Multiple parties",
                "Complex facts",
                "Expert witnesses",
                "International discovery",
                "Judge's docket congestion",
            ],
        )

    def get_local_rules(self, court: str) -> dict:
        """
        Return local rules and practice notes for a specific court.

        Args:
            court: Court identifier.

        Returns:
            dict with local rules information.

        Example:
            >>> nav = CourtNavigator()
            >>> rules = nav.get_local_rules("S.D.N.Y.")
            >>> "page_limits" in rules
            True
        """
        # Try exact match first
        if court in COURT_LOCAL_RULES:
            return COURT_LOCAL_RULES[court]

        # Try partial match
        for key, rules in COURT_LOCAL_RULES.items():
            if key in court or court in key:
                return rules

        # Return generic federal rules
        return {
            "note": f"Specific local rules for {court} not in database.",
            "general_resource": "https://www.uscourts.gov/court-locator",
            "page_limits": {"motion": 25, "opposition": 25, "reply": 10},
            "font": "12-point font",
            "margins": "1 inch all sides",
            "electronic_filing": True,
            "individual_judge_rules": "Always check the assigned judge's individual practices",
            "frcp": "Federal Rules of Civil Procedure apply in all federal district courts",
        }

    def check_jurisdiction(
        self,
        plaintiff_state: str,
        defendant_state: str,
        amount: float,
        federal_question: bool = False,
        federal_question_basis: str = "",
    ) -> JurisdictionAnalysis:
        """
        Analyze whether federal jurisdiction exists over a dispute.

        Covers:
        - Diversity jurisdiction (28 U.S.C. § 1332) — different states + >$75,000
        - Federal question jurisdiction (28 U.S.C. § 1331)
        - Supplemental jurisdiction (28 U.S.C. § 1367)

        Args:
            plaintiff_state: State where plaintiff is domiciled.
            defendant_state: State where defendant is domiciled.
            amount: Amount in controversy.
            federal_question: Whether a federal question is involved.
            federal_question_basis: The federal law or constitutional provision.

        Returns:
            JurisdictionAnalysis with basis, recommendation, and notes.

        Example:
            >>> nav = CourtNavigator()
            >>> analysis = nav.check_jurisdiction("California", "New York", 100000.0)
            >>> analysis.diversity_jurisdiction
            True
        """
        bases = []
        diversity = False
        federal = federal_question

        # Check diversity jurisdiction
        if plaintiff_state.lower() != defendant_state.lower():
            if amount > 75000:
                diversity = True
                federal = True
                bases.append(
                    f"Diversity jurisdiction: 28 U.S.C. § 1332 — plaintiff ({plaintiff_state}) "
                    f"and defendant ({defendant_state}) are from different states; amount in "
                    f"controversy ${amount:,.2f} exceeds $75,000 threshold."
                )
            else:
                bases.append(
                    f"Diversity exists (different states) but amount in controversy "
                    f"(${amount:,.2f}) does NOT exceed $75,000 — no diversity jurisdiction. "
                    f"Must file in state court or establish federal question."
                )
        else:
            bases.append(
                f"No diversity: plaintiff and defendant both from {plaintiff_state}."
            )

        # Federal question
        if federal_question:
            federal = True
            bases.append(
                f"Federal question jurisdiction: 28 U.S.C. § 1331 — {federal_question_basis or 'claim arises under federal law'}."
            )

        # Supplemental jurisdiction
        supplemental = federal and not diversity  # State claims can be appended
        if federal and supplemental:
            bases.append(
                "Supplemental jurisdiction available for state law claims: 28 U.S.C. § 1367."
            )

        # Recommend forum
        if federal:
            recommended = "Federal"
            notes = "Federal court offers advantages: discovery rules, federal judges, FRCP uniformity."
        else:
            recommended = "State"
            notes = "No federal jurisdiction established. Must file in state court."

        if diversity and amount > 75000:
            notes += " Defendant may remove from state court to federal court within 30 days of service."

        return JurisdictionAnalysis(
            has_federal_jurisdiction=federal,
            jurisdictional_basis=bases,
            diversity_jurisdiction=diversity,
            amount_in_controversy=amount,
            recommended_forum=recommended,
            state_court_viable=True,
            federal_question_basis=federal_question_basis,
            supplemental_jurisdiction=supplemental,
            notes=notes,
        )

    def get_all_federal_circuits(self) -> Dict[str, Dict]:
        """Return information about all 13 federal circuit courts."""
        return FEDERAL_CIRCUITS

    def get_administrative_tribunals(self) -> Dict[str, Dict]:
        """Return information about major federal administrative tribunals."""
        return ADMINISTRATIVE_TRIBUNALS

    def get_international_tribunals(self) -> Dict[str, Dict]:
        """Return information about major international tribunals."""
        return INTERNATIONAL_TRIBUNALS

    def get_specialized_courts(self) -> Dict[str, Dict]:
        """Return information about specialized federal courts."""
        return SPECIALIZED_FEDERAL_COURTS

    def get_circuit_for_state(self, state: str) -> str:
        """Return the federal circuit court of appeals for a given state."""
        circuit = self.STATE_CIRCUIT_MAP.get(state, "Unknown")
        if circuit == "DC":
            return "U.S. Court of Appeals for the D.C. Circuit"
        if circuit == "Unknown":
            return f"Circuit not found for state: {state}"
        return f"U.S. Court of Appeals for the {circuit}th Circuit"
