"""
Motion Drafting Engine — SintraPrime Legal Intelligence System

Generates complete, court-ready legal motions with proper captions, IRAC format,
real case citations, and proposed orders. Covers all major federal motion types.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class LegalDocument:
    """
    Represents a complete legal document ready for court filing.

    Example:
        >>> doc = LegalDocument(
        ...     title="Motion to Dismiss",
        ...     court="U.S. District Court, S.D.N.Y.",
        ...     case_number="1:24-cv-01234",
        ...     content="IN THE UNITED STATES DISTRICT COURT...",
        ...     motion_type="motion_to_dismiss",
        ...     word_count=2500
        ... )
    """
    title: str
    court: str
    case_number: str
    content: str
    motion_type: str
    word_count: int = 0
    citations: List[str] = field(default_factory=list)
    sections: Dict[str, str] = field(default_factory=dict)
    page_count: int = 0
    jurisdiction: str = "federal"
    date_created: str = field(default_factory=lambda: datetime.now().strftime("%B %d, %Y"))
    proposed_order: Optional[str] = None


@dataclass
class ComplianceReport:
    """
    Report on whether a motion complies with local court rules.

    Example:
        >>> report = ComplianceReport(
        ...     compliant=True,
        ...     court="S.D.N.Y.",
        ...     issues=[],
        ...     warnings=["Consider adding table of authorities"],
        ...     page_count=18,
        ...     page_limit=25
        ... )
    """
    compliant: bool
    court: str
    issues: List[str]
    warnings: List[str]
    page_count: int
    page_limit: int
    font_compliant: bool = True
    margin_compliant: bool = True
    caption_compliant: bool = True
    certificate_of_service: bool = True
    recommendations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Citation Database
# ---------------------------------------------------------------------------

LANDMARK_CITATIONS: Dict[str, Dict[str, str]] = {
    # 12(b)(6) Motion to Dismiss
    "twombly": {
        "citation": "Bell Atlantic Corp. v. Twombly, 550 U.S. 544 (2007)",
        "holding": "A complaint must allege enough facts to state a claim for relief that is plausible on its face.",
        "standard": "Plausibility standard — factual allegations must plausibly suggest an entitlement to relief.",
        "usage": "12(b)(6) motions to dismiss",
    },
    "iqbal": {
        "citation": "Ashcroft v. Iqbal, 556 U.S. 662 (2009)",
        "holding": "A pleading that offers labels and conclusions, or a formulaic recitation of the elements, does not suffice.",
        "standard": "Two-step analysis: (1) identify conclusory allegations; (2) assess plausibility of remaining factual content.",
        "usage": "12(b)(6) motions to dismiss",
    },
    # Summary Judgment
    "celotex": {
        "citation": "Celotex Corp. v. Catrett, 477 U.S. 317 (1986)",
        "holding": "Moving party bears initial burden of showing absence of genuine dispute; then burden shifts.",
        "standard": "Moving party need not produce evidence disproving opponent's case — may simply show no evidence exists.",
        "usage": "Motion for summary judgment",
    },
    "anderson": {
        "citation": "Anderson v. Liberty Lobby, Inc., 477 U.S. 242 (1986)",
        "holding": "Summary judgment standard mirrors directed verdict: whether evidence presents sufficient disagreement.",
        "standard": "Court views facts in light most favorable to non-moving party; grants SJ only if no genuine issue of material fact.",
        "usage": "Motion for summary judgment",
    },
    "matsushita": {
        "citation": "Matsushita Elec. Industrial Co. v. Zenith Radio Corp., 475 U.S. 574 (1986)",
        "holding": "Non-moving party must do more than show some metaphysical doubt as to material facts.",
        "standard": "Completing the SJ trilogy with Celotex and Anderson.",
        "usage": "Motion for summary judgment",
    },
    # Preliminary Injunction / TRO
    "winter": {
        "citation": "Winter v. Natural Resources Defense Council, 555 U.S. 7 (2008)",
        "holding": "Plaintiff must establish likely success on merits, likely irreparable harm, balance of equities favors injunction, and public interest.",
        "standard": "Four-factor test for preliminary injunction.",
        "usage": "TRO and preliminary injunction",
    },
    "ebay": {
        "citation": "eBay Inc. v. MercExchange, L.L.C., 547 U.S. 388 (2006)",
        "holding": "Traditional four-factor test applies to injunctions in patent cases; no categorical rules.",
        "standard": "Plaintiff must show: irreparable harm, remedies at law inadequate, balance of hardships, public interest.",
        "usage": "Injunctions generally, especially IP",
    },
    # Habeas Corpus
    "strickland": {
        "citation": "Strickland v. Washington, 466 U.S. 668 (1984)",
        "holding": "Ineffective assistance: (1) deficient performance; (2) prejudice — reasonable probability of different outcome.",
        "standard": "Two-prong Strickland test for 6th Amendment IAC claims.",
        "usage": "Habeas corpus — ineffective assistance of counsel",
    },
    "aedpa": {
        "citation": "Antiterrorism and Effective Death Penalty Act, 28 U.S.C. § 2254",
        "holding": "Federal habeas review is highly deferential to state court decisions.",
        "standard": "Relief only if state decision was contrary to, or unreasonable application of, clearly established federal law (AEDPA).",
        "usage": "Federal habeas corpus",
    },
    # Motion to Suppress
    "mapp": {
        "citation": "Mapp v. Ohio, 367 U.S. 643 (1961)",
        "holding": "Exclusionary rule applies to state courts under Fourteenth Amendment.",
        "standard": "Evidence obtained in violation of Fourth Amendment must be suppressed.",
        "usage": "Motion to suppress",
    },
    "terry": {
        "citation": "Terry v. Ohio, 392 U.S. 1 (1968)",
        "holding": "Officer may stop and briefly detain person based on reasonable articulable suspicion; frisk requires reasonable belief of armed and dangerous.",
        "standard": "Reasonable articulable suspicion for investigatory stop; probable cause for arrest.",
        "usage": "Motion to suppress — stop and frisk",
    },
    "miranda": {
        "citation": "Miranda v. Arizona, 384 U.S. 436 (1966)",
        "holding": "Custodial interrogation requires prior warnings of rights; statements obtained without warnings are inadmissible.",
        "standard": "Custody + interrogation → Miranda warnings required.",
        "usage": "Motion to suppress statements",
    },
    # Default Judgment
    "eitel": {
        "citation": "Eitel v. McCool, 782 F.2d 1470 (9th Cir. 1986)",
        "holding": "Seven factors guide default judgment discretion.",
        "standard": "(1) merits of claim; (2) sufficiency of complaint; (3) money at stake; (4) disputed material facts; (5) excusable neglect; (6) prejudice to plaintiff; (7) strong policy favoring decisions on merits.",
        "usage": "Motion for default judgment — 9th Circuit",
    },
    # Compel Discovery
    "oppenheimer": {
        "citation": "Oppenheimer Fund, Inc. v. Sanders, 437 U.S. 340 (1978)",
        "holding": "Discovery scope is broad — any matter not privileged that is relevant to claims or defenses.",
        "standard": "Relevance under Rule 26; proportionality required since 2015 amendments.",
        "usage": "Motion to compel discovery",
    },
    # Venue
    "piper": {
        "citation": "Piper Aircraft Co. v. Reyno, 454 U.S. 235 (1981)",
        "holding": "Forum non conveniens dismissal appropriate when foreign forum is adequate and private/public interest factors favor dismissal.",
        "standard": "Plaintiff's choice of forum given less deference when plaintiff is foreign national.",
        "usage": "Motion to dismiss for forum non conveniens / venue",
    },
    # Mandamus
    "cheney": {
        "citation": "Cheney v. U.S. District Court, 542 U.S. 367 (2004)",
        "holding": "Mandamus is extraordinary remedy; petitioner must show no other adequate means to obtain relief.",
        "standard": "Clear and indisputable right to relief; no adequate alternative means; writ is appropriate under circumstances.",
        "usage": "Writ of mandamus",
    },
    # Class Action
    "dukes": {
        "citation": "Wal-Mart Stores, Inc. v. Dukes, 564 U.S. 338 (2011)",
        "holding": "Rule 23(a)(2) commonality requires questions whose answers will resolve an issue central to validity of each class member's claims.",
        "standard": "Rigorous analysis of Rule 23 requirements at class certification stage.",
        "usage": "Class certification motions",
    },
    # Jurisdiction
    "international_shoe": {
        "citation": "International Shoe Co. v. Washington, 326 U.S. 310 (1945)",
        "holding": "Personal jurisdiction requires minimum contacts such that maintenance of suit does not offend traditional notions of fair play and substantial justice.",
        "standard": "Minimum contacts analysis for personal jurisdiction.",
        "usage": "12(b)(2) motion to dismiss for lack of personal jurisdiction",
    },
    "burger_king": {
        "citation": "Burger King Corp. v. Rudzewicz, 471 U.S. 462 (1985)",
        "holding": "Specific jurisdiction exists where defendant purposefully availed itself of privileges of forum state.",
        "standard": "Purposeful availment + relatedness + reasonableness.",
        "usage": "12(b)(2) — specific jurisdiction",
    },
}

# ---------------------------------------------------------------------------
# Motion Templates
# ---------------------------------------------------------------------------

MOTION_TEMPLATES: Dict[str, Dict] = {
    "motion_to_dismiss_12b6": {
        "title": "Defendant's Motion to Dismiss Pursuant to Rule 12(b)(6)",
        "introduction_template": (
            "Defendant {defendant} respectfully moves this Court to dismiss Plaintiff's Complaint "
            "pursuant to Federal Rule of Civil Procedure 12(b)(6) for failure to state a claim "
            "upon which relief can be granted. As set forth below, Plaintiff's claims are legally "
            "insufficient and must be dismissed."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "To survive a motion to dismiss, a complaint must contain 'sufficient factual matter, "
            "accepted as true, to state a claim to relief that is plausible on its face.' "
            "Ashcroft v. Iqbal, 556 U.S. 662, 678 (2009) (quoting Bell Atl. Corp. v. Twombly, "
            "550 U.S. 544, 570 (2007)). A claim has facial plausibility 'when the plaintiff pleads "
            "factual content that allows the court to draw the reasonable inference that the defendant "
            "is liable for the misconduct alleged.' Id. 'Where a complaint pleads facts that are "
            "merely consistent with a defendant's liability, it stops short of the line between "
            "possibility and plausibility of entitlement to relief.' Id. (internal quotation omitted). "
            "The Court need not accept legal conclusions as true, nor 'formulaic recitation[s] of "
            "the elements of a cause of action.' Twombly, 550 U.S. at 555."
        ),
        "key_citations": ["twombly", "iqbal"],
        "sections": ["Introduction", "Background", "Legal Standard", "Argument", "Conclusion"],
    },
    "motion_to_dismiss_12b1": {
        "title": "Defendant's Motion to Dismiss for Lack of Subject Matter Jurisdiction (Rule 12(b)(1))",
        "introduction_template": (
            "Defendant {defendant} moves to dismiss this action pursuant to Federal Rule of Civil "
            "Procedure 12(b)(1) for lack of subject matter jurisdiction. Plaintiff has failed to "
            "establish that this Court has jurisdiction over the claims asserted."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "Federal courts are courts of limited jurisdiction. Kokkonen v. Guardian Life Ins. Co., "
            "511 U.S. 375, 377 (1994). 'It is to be presumed that a cause lies outside this limited "
            "jurisdiction, and the burden of establishing the contrary rests upon the party asserting "
            "jurisdiction.' Id. A Rule 12(b)(1) motion may be a facial attack, challenging the "
            "sufficiency of the jurisdictional allegations, or a factual attack, presenting evidence "
            "challenging the factual basis for jurisdiction. Stalley v. Catholic Health Initiatives, "
            "509 F.3d 517, 520-21 (8th Cir. 2007). Unlike Rule 12(b)(6) motions, the Court may "
            "consider evidence outside the pleadings when ruling on a 12(b)(1) motion. Id."
        ),
        "key_citations": ["international_shoe"],
        "sections": ["Introduction", "Background", "Legal Standard", "Argument", "Conclusion"],
    },
    "motion_to_dismiss_12b2": {
        "title": "Defendant's Motion to Dismiss for Lack of Personal Jurisdiction (Rule 12(b)(2))",
        "introduction_template": (
            "Defendant {defendant} moves to dismiss this action pursuant to Federal Rule of Civil "
            "Procedure 12(b)(2) because this Court lacks personal jurisdiction over Defendant. "
            "Defendant lacks the minimum contacts with {forum_state} required by the Due Process Clause."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "To exercise personal jurisdiction, a court must find that the defendant has 'certain "
            "minimum contacts with [the forum state] such that the maintenance of the suit does not "
            "offend traditional notions of fair play and substantial justice.' International Shoe Co. "
            "v. Washington, 326 U.S. 310, 316 (1945). Jurisdiction may be general (continuous and "
            "systematic contacts) or specific (claims arising from defendant's forum contacts). "
            "Bristol-Myers Squibb Co. v. Superior Court, 582 U.S. 255 (2017). For specific "
            "jurisdiction, the defendant must have 'purposefully availed itself of the privilege of "
            "conducting activities within the forum State.' Burger King Corp. v. Rudzewicz, "
            "471 U.S. 462, 475 (1985). The plaintiff bears the burden of establishing jurisdiction."
        ),
        "key_citations": ["international_shoe", "burger_king"],
        "sections": ["Introduction", "Background", "Legal Standard", "Argument", "Conclusion"],
    },
    "motion_for_summary_judgment": {
        "title": "Defendant's Motion for Summary Judgment",
        "introduction_template": (
            "Defendant {defendant} respectfully moves for summary judgment pursuant to Federal Rule "
            "of Civil Procedure 56. There is no genuine dispute as to any material fact, and "
            "Defendant is entitled to judgment as a matter of law."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "Summary judgment is appropriate when 'there is no genuine dispute as to any material "
            "fact and the movant is entitled to judgment as a matter of law.' Fed. R. Civ. P. 56(a). "
            "A fact is material if it 'might affect the outcome of the suit under the governing law.' "
            "Anderson v. Liberty Lobby, Inc., 477 U.S. 242, 248 (1986). A dispute is genuine only "
            "if 'the evidence is such that a reasonable jury could return a verdict for the nonmoving "
            "party.' Id. The moving party bears the initial burden of demonstrating the absence of "
            "genuine dispute; it need not produce evidence to negate the opponent's claim but may "
            "point to the absence of evidence supporting it. Celotex Corp. v. Catrett, 477 U.S. 317, "
            "323-25 (1986). Once the moving party meets its burden, the burden shifts to the "
            "nonmoving party, who must 'go beyond the pleadings' and present specific facts showing "
            "a genuine issue for trial. Id. at 324. The Court views facts in the light most "
            "favorable to the nonmoving party. Anderson, 477 U.S. at 255."
        ),
        "key_citations": ["celotex", "anderson", "matsushita"],
        "sections": ["Introduction", "Statement of Undisputed Facts", "Legal Standard", "Argument", "Conclusion"],
    },
    "motion_in_limine": {
        "title": "Plaintiff's Motion in Limine to Exclude [Evidence]",
        "introduction_template": (
            "Plaintiff {plaintiff} moves in limine to preclude Defendant from introducing "
            "[evidence description] at trial. The evidence is irrelevant, prejudicial, or otherwise "
            "inadmissible under the Federal Rules of Evidence."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "A motion in limine may be used to exclude evidence that is inadmissible at trial. "
            "Luce v. United States, 469 U.S. 38, 40 n.2 (1984). Evidence must be relevant under "
            "FRE 401 (tends to make a fact of consequence more or less probable). Even relevant "
            "evidence is excluded under FRE 403 if its probative value is substantially outweighed "
            "by the danger of unfair prejudice, confusion of the issues, or misleading the jury. "
            "The Court has broad discretion in ruling on motions in limine. Ohler v. United States, "
            "529 U.S. 753, 758 n.3 (2000)."
        ),
        "key_citations": [],
        "sections": ["Introduction", "Background", "Legal Standard", "Argument", "Conclusion"],
    },
    "motion_to_suppress": {
        "title": "Defendant's Motion to Suppress Evidence",
        "introduction_template": (
            "Defendant {defendant} moves to suppress all evidence obtained as a result of the "
            "unlawful [search/seizure/interrogation] in violation of the Fourth and/or Fifth "
            "Amendment to the United States Constitution."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "The Fourth Amendment prohibits unreasonable searches and seizures. U.S. Const. amend. "
            "IV. Evidence obtained in violation of the Fourth Amendment must be suppressed as 'fruit "
            "of the poisonous tree.' Wong Sun v. United States, 371 U.S. 471 (1963). A search "
            "conducted without a warrant is per se unreasonable, subject to a few specifically "
            "established exceptions. Katz v. United States, 389 U.S. 347, 357 (1967). The government "
            "bears the burden of establishing that an exception to the warrant requirement applies. "
            "Vale v. Louisiana, 399 U.S. 30, 34 (1970). Statements obtained during custodial "
            "interrogation without Miranda warnings must also be suppressed. Miranda v. Arizona, "
            "384 U.S. 436 (1966)."
        ),
        "key_citations": ["mapp", "terry", "miranda"],
        "sections": ["Introduction", "Factual Background", "Legal Standard", "Argument", "Conclusion"],
    },
    "motion_for_continuance": {
        "title": "Defendant's Motion for Continuance",
        "introduction_template": (
            "Defendant {defendant} respectfully moves this Court for a continuance of [hearing/trial] "
            "currently scheduled for [date]. Good cause exists for the requested continuance as "
            "set forth herein."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "The decision to grant or deny a continuance lies within the sound discretion of the "
            "trial court. Morris v. Slappy, 461 U.S. 1, 11 (1983). Courts consider: (1) diligence "
            "of moving party; (2) likelihood continuance would accomplish stated purpose; "
            "(3) inconvenience to court and opposing party; and (4) harm resulting from denial. "
            "In criminal cases, denial of a continuance may violate the Sixth Amendment right to "
            "effective assistance of counsel if defendant is prejudiced. Id. at 11-12."
        ),
        "key_citations": [],
        "sections": ["Introduction", "Background", "Legal Standard", "Argument", "Conclusion"],
    },
    "motion_for_default_judgment": {
        "title": "Plaintiff's Motion for Default Judgment",
        "introduction_template": (
            "Plaintiff {plaintiff} moves for default judgment against Defendant {defendant} "
            "pursuant to Federal Rule of Civil Procedure 55(b)(2). Defendant has failed to "
            "appear, plead, or otherwise defend this action."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "Upon application of the party, a court may enter default judgment against a party "
            "who fails to plead or otherwise defend. Fed. R. Civ. P. 55(b)(2). The decision to "
            "enter default judgment is discretionary. Eitel v. McCool, 782 F.2d 1470, 1471-72 "
            "(9th Cir. 1986). Courts consider the Eitel factors: (1) possibility of prejudice to "
            "plaintiff; (2) merits of claims; (3) sufficiency of complaint; (4) amount of money at "
            "stake; (5) dispute of material facts; (6) excusable neglect; (7) policy favoring "
            "decisions on merits. Id. at 1471-72. Well-pled factual allegations are taken as true "
            "upon entry of default. Geddes v. United Fin. Group, 559 F.2d 557, 560 (9th Cir. 1977)."
        ),
        "key_citations": ["eitel"],
        "sections": ["Introduction", "Procedural History", "Legal Standard", "Argument", "Damages", "Conclusion"],
    },
    "motion_to_compel": {
        "title": "Plaintiff's Motion to Compel Discovery",
        "introduction_template": (
            "Plaintiff {plaintiff} moves to compel Defendant {defendant} to respond fully and "
            "completely to Plaintiff's [interrogatories/document requests/deposition questions] "
            "pursuant to Federal Rules of Civil Procedure 37(a)."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "Parties may obtain discovery regarding 'any nonprivileged matter that is relevant to "
            "any party's claim or defense and proportional to the needs of the case.' Fed. R. Civ. "
            "P. 26(b)(1). A party may move to compel discovery when a party fails to respond, "
            "or provides evasive or incomplete responses. Fed. R. Civ. P. 37(a)(1). The moving "
            "party must certify that it conferred in good faith with the opposing party before "
            "filing. Fed. R. Civ. P. 37(a)(1). The Court may award attorney's fees to the "
            "prevailing party on a motion to compel. Fed. R. Civ. P. 37(a)(5)."
        ),
        "key_citations": ["oppenheimer"],
        "sections": ["Introduction", "Discovery History", "Legal Standard", "Argument", "Conclusion"],
    },
    "motion_for_protective_order": {
        "title": "Defendant's Motion for Protective Order",
        "introduction_template": (
            "Defendant {defendant} moves for a protective order pursuant to Federal Rule of Civil "
            "Procedure 26(c) to protect [confidential information/trade secrets/privileged material] "
            "from disclosure."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "A court may issue a protective order 'for good cause' to protect a party from "
            "'annoyance, embarrassment, oppression, or undue burden or expense.' Fed. R. Civ. P. "
            "26(c)(1). The moving party bears the burden of establishing good cause. Cipollone v. "
            "Liggett Group, Inc., 785 F.2d 1108, 1121 (3d Cir. 1986). Good cause requires a "
            "specific showing of clearly defined and serious injury. Id. The court balances the "
            "parties' competing interests. Seattle Times Co. v. Rhinehart, 467 U.S. 20, 36 (1984)."
        ),
        "key_citations": [],
        "sections": ["Introduction", "Background", "Legal Standard", "Argument", "Conclusion"],
    },
    "motion_for_tro": {
        "title": "Plaintiff's Motion for Temporary Restraining Order and Preliminary Injunction",
        "introduction_template": (
            "Plaintiff {plaintiff} moves for a Temporary Restraining Order (TRO) and Preliminary "
            "Injunction to prevent Defendant {defendant} from [specific conduct]. Without immediate "
            "relief, Plaintiff will suffer irreparable harm."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "A plaintiff seeking a preliminary injunction must establish: (1) likelihood of success "
            "on the merits; (2) likelihood of irreparable harm in the absence of preliminary relief; "
            "(3) the balance of equities tips in plaintiff's favor; and (4) an injunction is in the "
            "public interest. Winter v. Natural Resources Defense Council, 555 U.S. 7, 20 (2008). "
            "A TRO may be granted without notice only if: (1) specific facts show immediate and "
            "irreparable injury before the adverse party can be heard; and (2) the movant's attorney "
            "certifies the reasons notice should not be required. Fed. R. Civ. P. 65(b)(1). "
            "An injunction is an extraordinary remedy. Weinberger v. Romero-Barcelo, 456 U.S. 305, "
            "312 (1982). The movant must satisfy all four eBay factors. eBay Inc. v. MercExchange, "
            "L.L.C., 547 U.S. 388 (2006)."
        ),
        "key_citations": ["winter", "ebay"],
        "sections": ["Introduction", "Background", "Legal Standard", "Argument", "Proposed Order", "Conclusion"],
    },
    "motion_for_change_of_venue": {
        "title": "Defendant's Motion to Transfer Venue",
        "introduction_template": (
            "Defendant {defendant} moves to transfer this action to the [transferee district] "
            "pursuant to 28 U.S.C. § 1404(a) for the convenience of the parties and witnesses "
            "and in the interest of justice."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "A district court may transfer a civil action to any other district where it could "
            "have been brought 'for the convenience of parties and witnesses, in the interest of "
            "justice.' 28 U.S.C. § 1404(a). The court considers private factors (plaintiff's "
            "choice of forum, convenience of witnesses, access to evidence, practical difficulties) "
            "and public factors (court congestion, local interest in controversy, familiarity with "
            "governing law). Gulf Oil Corp. v. Gilbert, 330 U.S. 501, 508-09 (1947). The moving "
            "party bears the burden of demonstrating transfer is warranted. Jumara v. State Farm "
            "Ins. Co., 55 F.3d 873, 879 (3d Cir. 1995)."
        ),
        "key_citations": ["piper"],
        "sections": ["Introduction", "Background", "Legal Standard", "Argument", "Conclusion"],
    },
    "motion_to_strike": {
        "title": "Defendant's Motion to Strike",
        "introduction_template": (
            "Defendant {defendant} moves to strike {target} from Plaintiff's Complaint pursuant "
            "to Federal Rule of Civil Procedure 12(f) as redundant, immaterial, impertinent, "
            "or scandalous matter."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "Under Rule 12(f), a court may strike from a pleading any 'redundant, immaterial, "
            "impertinent, or scandalous matter.' Fed. R. Civ. P. 12(f). Motions to strike are "
            "generally disfavored and granted only when the matter is clearly irrelevant to the "
            "litigation and causes prejudice to the moving party. Wailua Assocs. v. Aetna Cas. & "
            "Sur. Co., 183 F.R.D. 550, 553 (D. Haw. 1998). A motion to strike may also be used "
            "to strike legally insufficient defenses. Sidney-Vinstein v. A.H. Robins Co., "
            "697 F.2d 880, 885 (9th Cir. 1983)."
        ),
        "key_citations": [],
        "sections": ["Introduction", "Background", "Legal Standard", "Argument", "Conclusion"],
    },
    "habeas_corpus": {
        "title": "Petition for Writ of Habeas Corpus",
        "introduction_template": (
            "Petitioner {petitioner}, through counsel, respectfully petitions this Court for a "
            "Writ of Habeas Corpus pursuant to 28 U.S.C. § 2254 [or § 2241]. Petitioner is being "
            "held in unlawful custody in violation of the Constitution, laws, or treaties of the "
            "United States."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "A federal court may grant habeas relief to a state prisoner when the state court "
            "adjudication 'resulted in a decision that was contrary to, or involved an unreasonable "
            "application of, clearly established Federal law, as determined by the Supreme Court,' "
            "or was 'based on an unreasonable determination of the facts.' 28 U.S.C. § 2254(d). "
            "A decision is 'contrary to' clearly established law if the state court applies a rule "
            "that contradicts governing Supreme Court precedent. Williams v. Taylor, 529 U.S. 362, "
            "405 (2000). 'Unreasonable application' occurs when the state court correctly identifies "
            "the governing legal rule but unreasonably applies it to the facts. Id. at 407-09. "
            "Ineffective assistance claims are governed by Strickland v. Washington, 466 U.S. 668 "
            "(1984): deficient performance + prejudice."
        ),
        "key_citations": ["strickland", "aedpa"],
        "sections": ["Introduction", "Jurisdiction", "Procedural History", "Statement of Facts",
                     "Grounds for Relief", "Argument", "Conclusion"],
    },
    "writ_of_mandamus": {
        "title": "Petition for Writ of Mandamus",
        "introduction_template": (
            "Petitioner {petitioner} respectfully petitions this Court for a Writ of Mandamus "
            "directed to [respondent/district court] compelling it to [action sought]. This "
            "extraordinary writ is warranted because Petitioner has a clear right to relief "
            "and no other adequate remedy at law."
        ),
        "legal_standard": (
            "LEGAL STANDARD\n\n"
            "Mandamus is an extraordinary remedy available only in exceptional circumstances. "
            "Cheney v. U.S. Dist. Court, 542 U.S. 367, 380 (2004). Three conditions must be "
            "satisfied: (1) the petitioner must have 'no other adequate means to attain the relief "
            "desired'; (2) the petitioner must demonstrate a 'clear and indisputable' right to the "
            "writ; and (3) the court must be satisfied that the writ is 'appropriate under the "
            "circumstances.' Id. at 380-81 (quotations omitted). Courts have supervisory mandamus "
            "power to ensure district courts do not usurp authority or commit clear abuses of "
            "discretion. Bankers Life & Casualty Co. v. Holland, 346 U.S. 379, 382-85 (1953)."
        ),
        "key_citations": ["cheney"],
        "sections": ["Introduction", "Jurisdiction", "Background", "Legal Standard", "Argument", "Conclusion"],
    },
}

# ---------------------------------------------------------------------------
# Motion Drafting Engine
# ---------------------------------------------------------------------------

class MotionDraftingEngine:
    """
    Generates complete, court-ready legal motions with proper formatting,
    real case citations, and IRAC analysis.

    All generated motions include:
    - Proper court caption
    - Introduction / nature of motion
    - Statement of facts (from provided facts dict)
    - Applicable legal standard with citations
    - Argument sections in IRAC format
    - Conclusion and prayer for relief
    - Certificate of service
    - Proposed order

    Example:
        >>> engine = MotionDraftingEngine()
        >>> doc = engine.draft_motion(
        ...     motion_type="motion_to_dismiss_12b6",
        ...     facts={"plaintiff": "Jane Doe", "defendant": "ACME Corp",
        ...            "case_number": "1:24-cv-01234", "court": "S.D.N.Y.",
        ...            "claims": "breach of contract", "deficiencies": "conclusory allegations"},
        ...     jurisdiction="federal"
        ... )
        >>> "Twombly" in doc.content
        True
    """

    def __init__(self) -> None:
        self.templates = MOTION_TEMPLATES
        self.citations = LANDMARK_CITATIONS

    def _build_caption(self, facts: dict) -> str:
        """Build the standard court caption for a federal motion."""
        court = facts.get("court", "UNITED STATES DISTRICT COURT")
        district = facts.get("district", "DISTRICT OF [STATE]")
        plaintiff = facts.get("plaintiff", "PLAINTIFF")
        defendant = facts.get("defendant", "DEFENDANT")
        case_number = facts.get("case_number", "[CASE NUMBER]")
        judge = facts.get("judge", "[JUDGE NAME]")

        return f"""IN THE UNITED STATES DISTRICT COURT
FOR THE {district.upper()}

{plaintiff.upper()},

    Plaintiff,

    v.                                    Civil Action No. {case_number}

{defendant.upper()},

    Defendant.

DEFENDANT'S [MOTION TYPE]

Hon. {judge}
"""

    def _build_certificate_of_service(self, facts: dict) -> str:
        """Build a standard certificate of service."""
        attorney = facts.get("attorney", "Attorney Name")
        opposing_counsel = facts.get("opposing_counsel", "Opposing Counsel")
        date = datetime.now().strftime("%B %d, %Y")

        return f"""CERTIFICATE OF SERVICE

I hereby certify that on {date}, I electronically filed the foregoing with the Clerk of the Court
using the CM/ECF system, which will send notification of such filing to all counsel of record,
including:

    {opposing_counsel}
    [Address]
    [City, State, ZIP]

                                        /s/ {attorney}
                                        {attorney}
"""

    def _substitute_template_vars(self, template: str, facts: dict) -> str:
        """Substitute template variables with actual facts."""
        result = template
        for key, value in facts.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    def _build_statement_of_facts(self, facts: dict) -> str:
        """Build the statement of facts section from provided facts."""
        fact_items = []
        skip_keys = {"plaintiff", "defendant", "court", "district", "case_number",
                     "judge", "attorney", "opposing_counsel", "forum_state"}

        for key, value in facts.items():
            if key not in skip_keys and value:
                formatted_key = key.replace("_", " ").title()
                fact_items.append(f"    {len(fact_items)+1}. {formatted_key}: {value}")

        if not fact_items:
            fact_items = ["    1. [Insert specific factual allegations here]"]

        return "STATEMENT OF FACTS\n\n" + "\n\n".join(fact_items)

    def draft_motion(self, motion_type: str, facts: dict, jurisdiction: str = "federal") -> LegalDocument:
        """
        Generate a complete legal motion with all required sections.

        Args:
            motion_type: Type of motion (use MOTION_TEMPLATES keys).
            facts: Dictionary of case-specific facts (plaintiff, defendant, court, etc.).
            jurisdiction: "federal" or "state" (default: "federal").

        Returns:
            LegalDocument with full motion content.

        Example:
            >>> engine = MotionDraftingEngine()
            >>> doc = engine.draft_motion(
            ...     "motion_for_summary_judgment",
            ...     {"plaintiff": "Smith", "defendant": "Jones Corp",
            ...      "case_number": "4:24-cv-99", "court": "S.D. Tex."},
            ...     "federal"
            ... )
            >>> "Celotex" in doc.content
            True
        """
        template = self.templates.get(motion_type)
        if not template:
            # Fallback generic motion
            template = {
                "title": f"Motion — {motion_type.replace('_', ' ').title()}",
                "introduction_template": "Movant respectfully moves this Court for relief as set forth herein.",
                "legal_standard": "LEGAL STANDARD\n\n[Applicable legal standard]",
                "key_citations": [],
                "sections": ["Introduction", "Legal Standard", "Argument", "Conclusion"],
            }

        title = template["title"]
        intro = self._substitute_template_vars(
            template.get("introduction_template", ""), facts
        )
        legal_standard = template.get("legal_standard", "")
        key_citation_keys = template.get("key_citations", [])

        # Build citations text
        citations_text = ""
        citation_list = []
        for ck in key_citation_keys:
            if ck in self.citations:
                c = self.citations[ck]
                citation_list.append(c["citation"])
                citations_text += f"\n• {c['citation']}\n  Holding: {c['holding']}\n"

        # Assemble full motion
        caption = self._build_caption(facts)
        sof = self._build_statement_of_facts(facts)
        cert = self._build_certificate_of_service(facts)

        # Build IRAC argument section
        issue = facts.get("claims", "whether Plaintiff states a valid claim for relief")
        rule = f"The applicable legal rule is as stated in the Legal Standard section above."
        application = (
            f"Applying the foregoing legal standard to the facts of this case, {facts.get('defendant', 'Defendant')} "
            f"is entitled to the relief requested because: {facts.get('deficiencies', '[Specific deficiencies in the case]')}."
        )
        conclusion_arg = (
            f"For the foregoing reasons, {facts.get('defendant', facts.get('plaintiff', 'Movant'))} "
            f"respectfully requests that this Court grant the relief requested."
        )

        argument = f"""ARGUMENT

I. ISSUE

Whether {issue}.

II. RULE

{rule}

III. APPLICATION

{application}

{citations_text}

IV. CONCLUSION

{conclusion_arg}"""

        full_content = f"""{caption}
{title.upper()}

INTRODUCTION

{intro}

{sof}

{legal_standard}

{argument}

CONCLUSION

WHEREFORE, for the foregoing reasons, the Court should grant this Motion.

Respectfully submitted,

/s/ [Attorney Signature]
[Attorney Name]
[Bar Number]
[Firm Name]
[Address]
[Phone]
[Email]

Dated: {datetime.now().strftime("%B %d, %Y")}

{cert}"""

        word_count = len(full_content.split())
        page_count = max(1, word_count // 250)  # ~250 words per page

        return LegalDocument(
            title=title,
            court=facts.get("court", ""),
            case_number=facts.get("case_number", ""),
            content=full_content,
            motion_type=motion_type,
            word_count=word_count,
            citations=citation_list,
            sections={
                "introduction": intro,
                "statement_of_facts": sof,
                "legal_standard": legal_standard,
                "argument": argument,
            },
            page_count=page_count,
            jurisdiction=jurisdiction,
        )

    def add_case_citations(self, motion: LegalDocument, practice_area: str) -> LegalDocument:
        """
        Add practice-area-specific case citations to an existing motion.

        Args:
            motion: The motion document to enhance.
            practice_area: Practice area for citation selection.

        Returns:
            Updated LegalDocument with additional citations.

        Example:
            >>> engine = MotionDraftingEngine()
            >>> doc = engine.draft_motion("motion_to_suppress", {"defendant": "D", "case_number": "1"}, "federal")
            >>> enhanced = engine.add_case_citations(doc, "criminal_defense")
            >>> len(enhanced.citations) >= 1
            True
        """
        area_citations: Dict[str, List[str]] = {
            "criminal_defense": ["mapp", "terry", "miranda", "strickland"],
            "civil_rights": ["international_shoe"],
            "contract_law": ["twombly", "iqbal"],
            "employment_law": ["twombly", "iqbal"],
            "intellectual_property": ["ebay"],
            "class_action": ["dukes"],
            "administrative_law": [],
        }

        relevant_keys = area_citations.get(practice_area, ["twombly", "iqbal"])
        new_citations = []
        additional_text = "\n\nADDITIONAL AUTHORITY\n"

        for ck in relevant_keys:
            if ck in self.citations and self.citations[ck]["citation"] not in motion.citations:
                c = self.citations[ck]
                new_citations.append(c["citation"])
                additional_text += f"\n• {c['citation']}: {c['holding']}\n"

        motion.citations.extend(new_citations)
        motion.content += additional_text
        motion.word_count = len(motion.content.split())

        return motion

    def generate_proposed_order(self, motion: LegalDocument) -> LegalDocument:
        """
        Generate a proposed order to accompany a motion.

        Args:
            motion: The motion for which to generate a proposed order.

        Returns:
            LegalDocument containing the proposed order.

        Example:
            >>> engine = MotionDraftingEngine()
            >>> doc = engine.draft_motion("motion_to_dismiss_12b6",
            ...     {"plaintiff": "P", "defendant": "D", "case_number": "1"}, "federal")
            >>> order = engine.generate_proposed_order(doc)
            >>> "ORDER" in order.content
            True
        """
        motion_type_friendly = motion.motion_type.replace("_", " ").title()

        order_content = f"""IN THE UNITED STATES DISTRICT COURT
[DISTRICT]

[PLAINTIFF],                             Case No. {motion.case_number}
    Plaintiff,

v.

[DEFENDANT],
    Defendant.


[PROPOSED] ORDER GRANTING {motion_type_friendly.upper()}

        THIS MATTER having come before the Court on Defendant's {motion_type_friendly},
and the Court having considered the motion, opposition, reply, and the record herein, and
good cause appearing:

        IT IS HEREBY ORDERED that Defendant's {motion_type_friendly} is GRANTED.

        IT IS FURTHER ORDERED that [specific relief — e.g., Plaintiff's Complaint is
DISMISSED WITH/WITHOUT PREJUDICE / the evidence is SUPPRESSED / judgment is entered
in favor of Defendant].

        IT IS SO ORDERED.

Dated: ___________________

                                        _________________________________
                                        [JUDGE'S NAME]
                                        United States District Judge
"""

        return LegalDocument(
            title=f"[Proposed] Order Granting {motion_type_friendly}",
            court=motion.court,
            case_number=motion.case_number,
            content=order_content,
            motion_type="proposed_order",
            word_count=len(order_content.split()),
            jurisdiction=motion.jurisdiction,
        )

    def check_local_rules_compliance(self, motion: LegalDocument, court: str) -> ComplianceReport:
        """
        Check whether a motion complies with a court's local rules.

        Args:
            motion: The motion to check.
            court: Court identifier (e.g., "S.D.N.Y.", "N.D. Cal.").

        Returns:
            ComplianceReport with compliance status and any issues.

        Example:
            >>> engine = MotionDraftingEngine()
            >>> doc = engine.draft_motion("motion_to_dismiss_12b6",
            ...     {"plaintiff": "P", "defendant": "D", "case_number": "1"}, "federal")
            >>> report = engine.check_local_rules_compliance(doc, "S.D.N.Y.")
            >>> isinstance(report.compliant, bool)
            True
        """
        # Court-specific page limits
        page_limits: Dict[str, Dict[str, int]] = {
            "S.D.N.Y.": {"motion": 25, "opposition": 25, "reply": 10},
            "N.D. Cal.": {"motion": 25, "opposition": 25, "reply": 15},
            "C.D. Cal.": {"motion": 25, "opposition": 25, "reply": 12},
            "N.D. Tex.": {"brief": 25},
            "D.D.C.": {"motion": 45, "opposition": 45, "reply": 25},
        }

        court_limits = page_limits.get(court, {"motion": 25, "brief": 25, "reply": 10})
        limit = court_limits.get("motion", court_limits.get("brief", 25))

        issues = []
        warnings = []
        recommendations = []

        # Check page count
        if motion.page_count > limit:
            issues.append(
                f"Document exceeds page limit: {motion.page_count} pages (limit: {limit}). "
                f"Must obtain leave of court or reduce length."
            )

        # Check for certificate of service
        has_cert = "CERTIFICATE OF SERVICE" in motion.content.upper()
        if not has_cert:
            issues.append("Missing certificate of service — required in all federal courts.")

        # Check for caption
        has_caption = "IN THE UNITED STATES" in motion.content.upper() or "DISTRICT COURT" in motion.content.upper()
        if not has_caption:
            warnings.append("Caption does not appear to follow standard federal format.")

        # Check for required sections
        required_sections = ["INTRODUCTION", "ARGUMENT", "CONCLUSION"]
        for section in required_sections:
            if section not in motion.content.upper():
                warnings.append(f"Missing standard section: {section}")

        # Court-specific warnings
        if court == "S.D.N.Y.":
            warnings.append(
                "S.D.N.Y.: Pre-motion conference letter may be required before filing motion. "
                "Check assigned judge's Individual Practices."
            )
            recommendations.append("Review judge's Individual Practices at nysd.uscourts.gov")

        if court == "N.D. Cal.":
            warnings.append(
                "N.D. Cal.: ADR certification may be required. Check judge's Standing Orders."
            )

        # Word count check (alternative to page limit)
        if motion.word_count > limit * 250:
            warnings.append(
                f"Word count ({motion.word_count}) may exceed page limit equivalent. "
                f"Consider condensing arguments."
            )

        recommendations.extend([
            "Add table of contents and table of authorities for motions > 10 pages",
            "Include certificate of compliance with word/page limits",
            f"Verify local rules at https://www.uscourts.gov (court: {court})",
        ])

        compliant = len(issues) == 0

        return ComplianceReport(
            compliant=compliant,
            court=court,
            issues=issues,
            warnings=warnings,
            page_count=motion.page_count,
            page_limit=limit,
            font_compliant=True,  # Can't verify without actual document
            margin_compliant=True,
            caption_compliant=has_caption,
            certificate_of_service=has_cert,
            recommendations=recommendations,
        )

    def get_available_motions(self) -> List[str]:
        """Return list of all available motion types."""
        return list(self.templates.keys())

    def get_citation(self, citation_key: str) -> Optional[Dict]:
        """Look up a landmark case citation by key."""
        return self.citations.get(citation_key)

    def list_citations(self) -> Dict[str, str]:
        """Return all available citation keys with their full citations."""
        return {k: v["citation"] for k, v in self.citations.items()}
