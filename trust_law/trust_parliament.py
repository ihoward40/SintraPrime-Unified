"""
Trust Parliament
================
A specialized multi-agent deliberation system for trust law decisions.
Six AI agents with distinct roles, biases, and expertise deliberate on
complex trust law questions to produce balanced, multi-perspective verdicts.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import random


# ── Agent Role Definitions ───────────────────────────────────────────────────

@dataclass
class AgentProfile:
    """Profile of a parliament agent."""
    role: str
    title: str
    expertise: List[str]
    bias_toward: str
    core_values: List[str]
    typical_concerns: List[str]
    signature_phrase: str


@dataclass
class Opinion:
    """An opinion from a parliament agent."""
    agent_role: str
    agent_title: str
    position: str           # "SUPPORT", "OPPOSE", "CONDITIONAL", "ABSTAIN"
    reasoning: str
    score: float            # 0-10 (10 = strongly support)
    key_concerns: List[str]
    conditions: List[str]   # If conditional: what conditions must be met
    signature_argument: str


@dataclass
class ParliamentVerdict:
    """The result of a parliament deliberation."""
    question: str
    majority_recommendation: str
    dissenting_views: List[str]
    confidence_score: float    # 0-100
    key_considerations: List[str]
    unanimous: bool
    debate_transcript: List[str]
    vote_tally: Dict[str, int]  # SUPPORT/OPPOSE/CONDITIONAL counts
    final_conditions: List[str]
    minority_report: Optional[str]


@dataclass
class StructureVerdict:
    """Verdict on a proposed trust structure."""
    proposed_structure: Dict[str, Any]
    overall_verdict: str    # "APPROVED", "APPROVED WITH CONDITIONS", "REJECTED", "NEEDS MORE INFO"
    approval_score: float   # 0-100
    required_modifications: List[str]
    warnings: List[str]
    agent_opinions: List[Opinion]
    implementation_prerequisites: List[str]


@dataclass
class JurisdictionVerdict:
    """Verdict on jurisdiction selection."""
    options_considered: List[str]
    recommended_jurisdiction: str
    runner_up: str
    consensus_level: str    # "UNANIMOUS", "MAJORITY", "SPLIT", "DIVIDED"
    jurisdiction_scores: Dict[str, float]
    dissenting_jurisdictions: List[str]
    rationale: str
    minority_preference: Optional[str]


class TrustParliament:
    """
    A multi-agent deliberation system for trust law decisions.
    Six specialized agents with distinct roles debate questions from their
    unique perspectives, producing balanced, multi-dimensional analysis.
    """

    # ── Define the Six Parliament Agents ────────────────────────────────────
    AGENTS: Dict[str, AgentProfile] = {
        "asset_protection_counsel": AgentProfile(
            role="asset_protection_counsel",
            title="Asset Protection Counsel",
            expertise=[
                "Domestic and offshore asset protection trusts",
                "Fraudulent transfer law (UVTA)",
                "Charging order protection",
                "LLC and LP structures",
                "Creditor remedies and defenses",
            ],
            bias_toward="Maximum creditor protection at all times",
            core_values=["Protection first", "Offshore when necessary", "Layer everything"],
            typical_concerns=[
                "Is the structure bulletproof against creditors?",
                "What happens if the client is sued tomorrow?",
                "Is there a fraudulent transfer risk?",
                "Is the offshore backup in place?",
            ],
            signature_phrase="The question is not IF they'll be sued, but WHEN.",
        ),
        "tax_strategist": AgentProfile(
            role="tax_strategist",
            title="Tax Strategist",
            expertise=[
                "Estate and gift tax planning",
                "Grantor trust rules (IRC §§671-679)",
                "Generation-skipping tax (GST)",
                "IDGT, SLAT, GRAT, QPRT techniques",
                "Foreign trust reporting (Form 3520, FBAR, FATCA)",
                "Charitable planning (CRT, CLT)",
            ],
            bias_toward="Tax efficiency above all — minimize transfer taxes and income taxes legally",
            core_values=["Tax minimization", "Use exemptions before they expire", "Every dollar saved is a dollar protected"],
            typical_concerns=[
                "What is the estate tax exposure?",
                "Is there a better tax structure?",
                "Are we using the current $13.61M exemption?",
                "What happens at the 2026 TCJA sunset?",
                "Is there a grantor trust risk?",
            ],
            signature_phrase="ACT NOW before the 2026 sunset takes away half the exemption.",
        ),
        "estate_planning_specialist": AgentProfile(
            role="estate_planning_specialist",
            title="Estate Planning Specialist",
            expertise=[
                "Revocable and irrevocable trusts",
                "Dynasty trusts and multi-generational planning",
                "Incapacity planning (powers of attorney, healthcare directives)",
                "Beneficiary designations",
                "Blended family and divorce planning",
                "Special needs planning",
            ],
            bias_toward="Long-term family harmony and smooth generational wealth transfer",
            core_values=["Family first", "Clear instructions prevent disputes", "Consider all generations"],
            typical_concerns=[
                "Will this create family conflict?",
                "Is the incapacity planning adequate?",
                "What happens to the surviving spouse?",
                "Are minor beneficiaries protected?",
                "Is there a no-contest clause?",
            ],
            signature_phrase="Wealth without a plan is inheritance without wisdom.",
        ),
        "compliance_officer": AgentProfile(
            role="compliance_officer",
            title="Compliance & Regulatory Officer",
            expertise=[
                "IRS and FinCEN compliance",
                "FBAR and FATCA requirements",
                "Foreign trust reporting (Forms 3520, 3520-A)",
                "Anti-money laundering (AML/BSA)",
                "Securities law compliance for trust interests",
                "State blue sky laws",
                "Trustee fiduciary duties and liability",
            ],
            bias_toward="Regulatory compliance — never cut corners",
            core_values=["Compliance is non-negotiable", "Document everything", "IRS is watching"],
            typical_concerns=[
                "Are all reporting requirements met?",
                "Is there an undisclosed foreign account?",
                "FBAR exposure for offshore structures",
                "Is the trustee properly licensed?",
                "What happens in an IRS audit?",
            ],
            signature_phrase="The IRS has a long memory and a longer statute of limitations.",
        ),
        "jurisdiction_expert": AgentProfile(
            role="jurisdiction_expert",
            title="Jurisdiction & Choice of Law Expert",
            expertise=[
                "All 50 US trust jurisdictions",
                "Offshore jurisdictions: Cook Islands, Nevis, Liechtenstein, Cayman",
                "Full faith and credit analysis",
                "Situs and governing law selection",
                "Trust migration and decanting",
                "Directed trust statutes",
                "Rule Against Perpetuities in all jurisdictions",
            ],
            bias_toward="Optimal jurisdiction selection — the right tool for the right job",
            core_values=["Jurisdiction is everything", "South Dakota first, offshore when necessary", "Know your state's laws cold"],
            typical_concerns=[
                "Is this the best jurisdiction?",
                "Will other states honor this trust?",
                "Is there a better state for this purpose?",
                "What is the SOL for fraudulent transfers here?",
                "Does the jurisdiction have directed trust statutes?",
            ],
            signature_phrase="Geography is destiny in trust law.",
        ),
        "beneficiary_advocate": AgentProfile(
            role="beneficiary_advocate",
            title="Beneficiary Rights Advocate",
            expertise=[
                "Beneficiary rights under UTC and common law",
                "Trustee accountability and removal",
                "Spendthrift and discretionary trust rights",
                "Special needs trust compliance",
                "Minor beneficiary protections",
                "Beneficiary information rights (UTC §813)",
            ],
            bias_toward="Protecting beneficiary interests and ensuring fairness",
            core_values=["Beneficiaries are the reason the trust exists", "Trustee accountability matters", "Fairness across generations"],
            typical_concerns=[
                "Can the beneficiary access funds when needed?",
                "Is the trustee truly independent?",
                "Are minority beneficiaries protected?",
                "What are the information rights?",
                "Is there a mechanism to remove a bad trustee?",
            ],
            signature_phrase="The trust exists for the beneficiaries, not the attorneys.",
        ),
    }

    def _generate_opinion(
        self,
        agent_key: str,
        question: str,
        context: Dict[str, Any],
        question_lower: str,
    ) -> Opinion:
        """Generate an opinion for a given agent based on their profile."""
        agent = self.AGENTS[agent_key]

        # Agent-specific logic for different question types
        if agent_key == "asset_protection_counsel":
            if any(kw in question_lower for kw in ["offshore", "cook islands", "nevis"]):
                position = "SUPPORT"
                score = 9.0
                reasoning = (
                    f"From an asset protection perspective, offshore structures provide maximum protection. "
                    f"Cook Islands and Nevis trusts have withstood US court challenges. "
                    f"My clients don't come to me after they're safe — they come when creditors are circling. "
                    f"This is the kind of protection that actually works. {agent.signature_phrase}"
                )
                concerns = [
                    "Must be pre-litigation — no transfers after suit is filed or threatened",
                    "Client must understand contempt risk if US court orders repatriation",
                    "Fraudulent transfer analysis required before any transfers",
                ]
                conditions = ["Transfer must be made while solvent and before any pending litigation"]
            elif any(kw in question_lower for kw in ["revocable", "simple", "basic"]):
                position = "OPPOSE"
                score = 2.0
                reasoning = (
                    "A revocable trust provides ZERO creditor protection. "
                    "The grantor's creditors can reach everything in a revocable trust. "
                    "This is estate planning, not asset protection. I cannot support recommending "
                    "this as an asset protection strategy. At minimum, add a DAPT overlay."
                )
                concerns = ["No protection against creditors", "Provides only probate avoidance benefit"]
                conditions = ["Add Nevada or South Dakota DAPT as minimum asset protection layer"]
            else:
                position = "CONDITIONAL"
                score = 6.0
                reasoning = (
                    f"From an asset protection standpoint, this structure has merit but needs strengthening. "
                    f"I recommend adding charging order protection at minimum. "
                    f"Domestic DAPT in Nevada or South Dakota should be the baseline. "
                    f"If the client has significant exposure, offshore backup is non-negotiable. "
                    f"{agent.signature_phrase}"
                )
                concerns = agent.typical_concerns[:2]
                conditions = ["Add Wyoming LLC or DAPT layer", "Conduct fraudulent transfer risk analysis"]

        elif agent_key == "tax_strategist":
            if any(kw in question_lower for kw in ["offshore", "foreign trust"]):
                position = "CONDITIONAL"
                score = 5.0
                reasoning = (
                    "The tax implications of offshore trusts are complex and significant. "
                    "Forms 3520, 3520-A, FBAR, and FATCA compliance are mandatory. "
                    "There is NO tax deferral benefit — grantor trust treatment means you still pay US tax. "
                    "The IRS has aggressive programs targeting undisclosed offshore assets. "
                    "I support the structure IF full compliance is maintained. "
                    f"{agent.signature_phrase}"
                )
                concerns = [
                    "FBAR: $10,000+ penalty per violation for failure to file",
                    "FATCA: Foreign institutions now report to IRS directly",
                    "Form 3520 penalties: up to 35% of gross reportable amount",
                ]
                conditions = [
                    "Retain qualified tax counsel experienced in offshore trust compliance",
                    "File all required forms annually without exception",
                    "Ensure trustee maintains proper records for US tax purposes",
                ]
            elif any(kw in question_lower for kw in ["estate tax", "exemption", "sunset", "gst", "dynasty"]):
                position = "SUPPORT"
                score = 9.5
                reasoning = (
                    "This is exactly what we should be doing. The current federal exemption of $13.61M "
                    "per person is set to sunset on December 31, 2025, potentially halving to $7M. "
                    "Every day of delay costs clients millions in potential estate taxes. "
                    "A dynasty trust with GST exemption allocation is the cornerstone of long-term tax planning. "
                    f"{agent.signature_phrase}"
                )
                concerns = ["Must allocate GST exemption properly at creation", "Ensure structure doesn't cause estate inclusion"]
                conditions = ["File gift tax return (Form 709) to allocate GST exemption"]
            else:
                position = "CONDITIONAL"
                score = 6.5
                reasoning = (
                    f"From a tax perspective, we need to evaluate whether this structure qualifies as a "
                    f"grantor trust, complex trust, or simple trust, as each has different tax treatment. "
                    f"Estate tax implications depend on the powers retained by the grantor. "
                    f"I can support this with proper tax structuring. {agent.signature_phrase}"
                )
                concerns = agent.typical_concerns[:2]
                conditions = ["Confirm grantor trust status", "Review retained powers for estate inclusion risk"]

        elif agent_key == "estate_planning_specialist":
            if any(kw in question_lower for kw in ["dynasty", "generation", "family"]):
                position = "SUPPORT"
                score = 8.5
                reasoning = (
                    "Dynasty trusts are the crown jewel of estate planning. "
                    "They allow wealth to compound across generations, bypass estate tax at each generation, "
                    "and provide the guardrails needed to prevent wealth dissipation. "
                    "The trust protector provision is critical — it provides flexibility across centuries. "
                    f"{agent.signature_phrase}"
                )
                concerns = [
                    "Trustee succession planning — who manages in 50 years?",
                    "Beneficiary needs change — discretionary distribution language must be flexible",
                    "No-contest clause recommended to prevent litigation",
                ]
                conditions = ["Include trust protector with power to modify administrative provisions"]
            elif any(kw in question_lower for kw in ["slat", "spouse", "married"]):
                position = "CONDITIONAL"
                score = 7.0
                reasoning = (
                    "SLATs are excellent planning tools for married couples, but the divorce risk is real. "
                    "If the beneficiary spouse divorces, the donor spouse loses indirect access to assets. "
                    "Two-SLAT strategies must be carefully differentiated to avoid reciprocal trust doctrine. "
                    "Recommend SLAT with different terms, trustees, and asset types. "
                    f"{agent.signature_phrase}"
                )
                concerns = ["Divorce risk", "Reciprocal trust doctrine", "Death of beneficiary spouse"]
                conditions = [
                    "Make SLATs materially different if doing cross-SLATs",
                    "Consider life insurance on beneficiary spouse",
                    "Ensure client understands the permanence of the transfer",
                ]
            else:
                position = "SUPPORT"
                score = 7.0
                reasoning = (
                    "From an estate planning perspective, this structure achieves the core objectives: "
                    "probate avoidance, incapacity protection, and efficient wealth transfer. "
                    "I recommend ensuring successor trustees are properly named and that "
                    "beneficiary designations on retirement accounts and insurance align with the plan. "
                    f"{agent.signature_phrase}"
                )
                concerns = agent.typical_concerns[:2]
                conditions = ["Update all beneficiary designations to align with trust plan"]

        elif agent_key == "compliance_officer":
            if any(kw in question_lower for kw in ["offshore", "foreign", "cook islands", "nevis", "liechtenstein"]):
                position = "CONDITIONAL"
                score = 4.5
                reasoning = (
                    "I have serious compliance concerns with this offshore structure. "
                    "The IRS FBAR penalty can be 50% of account balance per year for willful violations. "
                    "Form 3520 penalties can be up to 35% of the reportable amount. "
                    "FATCA means there is no hiding — foreign institutions report US persons directly to IRS. "
                    "I can only support this with FULL and ongoing compliance. "
                    f"{agent.signature_phrase}"
                )
                concerns = [
                    "FBAR: FinCEN Form 114 due April 15 (automatic Oct 15 extension)",
                    "Form 3520: Due date same as income tax return",
                    "Form 3520-A: Filed by the foreign trust (March 15 deadline)",
                    "FATCA: Form 8938 if assets exceed threshold",
                    "Criminal exposure for willful non-compliance",
                ]
                conditions = [
                    "Retain international tax counsel from day one",
                    "Establish FBAR calendar reminders before structure is funded",
                    "Ensure foreign trustee understands US reporting obligations",
                    "Annual review of all offshore reporting requirements",
                ]
            else:
                position = "SUPPORT"
                score = 8.0
                reasoning = (
                    "From a compliance standpoint, this domestic trust structure is sound. "
                    "Standard fiduciary requirements apply — trustee must maintain accounts, "
                    "file Form 1041 annually, and comply with state reporting requirements. "
                    "Ensure proper trust funding and asset re-titling. "
                    f"{agent.signature_phrase}"
                )
                concerns = ["Annual trust tax return (Form 1041) required", "State income tax filings may apply"]
                conditions = ["Retain CPA experienced in trust taxation from inception"]

        elif agent_key == "jurisdiction_expert":
            if "south dakota" in question_lower or "nevada" in question_lower:
                position = "SUPPORT"
                score = 9.0
                reasoning = (
                    "South Dakota and Nevada are the clear leaders in domestic trust law. "
                    f"{'South Dakota has abolished the Rule Against Perpetuities — unlimited trust duration.' if 'south dakota' in question_lower else 'Nevada has the shortest 2-year fraudulent transfer SOL in the US.'} "
                    "Both have no state income tax, strong self-settled trust statutes, and excellent directed trust laws. "
                    f"{agent.signature_phrase}"
                )
                concerns = ["Must maintain jurisdiction nexus — qualified trustee in the state"]
                conditions = ["Appoint qualified institutional trustee with state presence"]
            elif any(kw in question_lower for kw in ["offshore", "cook islands"]):
                position = "SUPPORT"
                score = 8.5
                reasoning = (
                    "Cook Islands represents the gold standard of offshore asset protection. "
                    "It does not recognize or enforce US court judgments. "
                    "A creditor must re-litigate entirely in the Cook Islands courts, "
                    "where the burden is beyond reasonable doubt for fraudulent transfer claims. "
                    "The 2-year SOL and the track record make this the most tested offshore jurisdiction. "
                    f"{agent.signature_phrase}"
                )
                concerns = [
                    "US grantor faces contempt risk if court orders repatriation and grantor controls assets",
                    "Must pair with domestic DAPT as backup",
                ]
                conditions = ["Domestic DAPT as first layer; Cook Islands as nuclear option"]
            else:
                position = "CONDITIONAL"
                score = 6.5
                reasoning = (
                    "The jurisdiction selection needs careful analysis. "
                    "For most clients, South Dakota offers the best combination: "
                    "no state income tax, unlimited dynasty duration, self-settled trusts, "
                    "decanting, directed trust statute, and 2-year SOL. "
                    "I recommend comparing SD vs. NV before making a final recommendation. "
                    f"{agent.signature_phrase}"
                )
                concerns = ["Consider full-faith-and-credit implications if client lives in another state"]
                conditions = ["Conduct jurisdiction analysis specific to trust type and client's home state"]

        else:  # beneficiary_advocate
            position = "CONDITIONAL"
            score = 6.0
            reasoning = (
                "I want to ensure beneficiary rights are protected in this structure. "
                "Beneficiaries should have access to trust information under UTC §813. "
                "There should be a mechanism to remove and replace the trustee if needed. "
                "Distribution standards should be clear enough to guide the trustee but flexible enough "
                "to meet changing needs. The trust protector should be an independent party. "
                f"{agent.signature_phrase}"
            )
            concerns = [
                "Are beneficiaries informed of trust existence and their rights?",
                "Is there a trust protector to oversee trustee conduct?",
                "Can beneficiaries compel distributions if trustee abuses discretion?",
                "Are minor beneficiaries independently represented?",
            ]
            conditions = [
                "Include trust protector with power to remove trustee",
                "Include UTC §813 information rights (or specify in trust)",
                "Consider including a distribution committee for large trusts",
            ]

        return Opinion(
            agent_role=agent_key,
            agent_title=agent.title,
            position=position,
            reasoning=reasoning,
            score=score,
            key_concerns=concerns,
            conditions=conditions,
            signature_argument=agent.signature_phrase,
        )

    def deliberate(self, question: str, context: Dict[str, Any]) -> ParliamentVerdict:
        """
        Full parliament deliberation on a trust law question.

        Args:
            question: The question to deliberate on
            context: Dict with relevant facts (client_profile, assets, threats, etc.)
        """
        question_lower = question.lower()
        debate_transcript = [
            f"══════════════════════════════════════════════════════════════",
            f"TRUST PARLIAMENT DELIBERATION",
            f"Question: {question}",
            f"══════════════════════════════════════════════════════════════",
            f"Context: {', '.join(f'{k}: {v}' for k, v in context.items())}",
            f"",
            f"Parliament is called to order. Six agents will now deliberate.",
            f"══════════════════════════════════════════════════════════════",
        ]

        opinions = []
        vote_tally = {"SUPPORT": 0, "OPPOSE": 0, "CONDITIONAL": 0, "ABSTAIN": 0}

        # Each agent deliberates
        for agent_key, agent_profile in self.AGENTS.items():
            debate_transcript.append(f"\n{'─'*60}")
            debate_transcript.append(f"AGENT: {agent_profile.title.upper()}")
            debate_transcript.append(f"Expertise: {', '.join(agent_profile.expertise[:2])}")
            debate_transcript.append(f"Bias: {agent_profile.bias_toward}")
            debate_transcript.append(f"{'─'*60}")

            opinion = self._generate_opinion(agent_key, question, context, question_lower)
            opinions.append(opinion)
            vote_tally[opinion.position] = vote_tally.get(opinion.position, 0) + 1

            debate_transcript.append(f"POSITION: {opinion.position} (Score: {opinion.score}/10)")
            debate_transcript.append(f"REASONING: {opinion.reasoning}")
            if opinion.key_concerns:
                debate_transcript.append(f"KEY CONCERNS:")
                for concern in opinion.key_concerns:
                    debate_transcript.append(f"  • {concern}")
            if opinion.conditions:
                debate_transcript.append(f"CONDITIONS:")
                for cond in opinion.conditions:
                    debate_transcript.append(f"  ✓ {cond}")

        # Determine majority recommendation
        debate_transcript.append(f"\n{'═'*60}")
        debate_transcript.append("VOTE TALLY AND VERDICT")
        debate_transcript.append(f"{'═'*60}")

        avg_score = sum(op.score for op in opinions) / len(opinions)
        max_votes = max(vote_tally, key=lambda k: vote_tally[k])
        unanimous = sum(1 for v in vote_tally.values() if v > 0) == 1

        if avg_score >= 7.5:
            majority_rec = "STRONGLY SUPPORTED — All key conditions should be met before implementation"
        elif avg_score >= 5.5:
            majority_rec = "CONDITIONALLY SUPPORTED — Implement with conditions and modifications noted"
        elif avg_score >= 4.0:
            majority_rec = "CAUTIOUSLY SUPPORTED — Significant concerns must be addressed first"
        else:
            majority_rec = "NOT RECOMMENDED — Structural deficiencies or risks outweigh benefits"

        for vote_type, count in vote_tally.items():
            debate_transcript.append(f"  {vote_type}: {count} vote(s)")
        debate_transcript.append(f"\nAVERAGE SCORE: {avg_score:.1f}/10")
        debate_transcript.append(f"VERDICT: {majority_rec}")

        # Dissenting views
        dissenting = []
        oppose_opinions = [op for op in opinions if op.position in ["OPPOSE"]]
        for op in oppose_opinions:
            dissenting.append(f"{op.agent_title} DISSENTS: {op.reasoning[:150]}...")

        # Key considerations (union of all key concerns, deduplicated)
        all_concerns = []
        for op in opinions:
            all_concerns.extend(op.key_concerns)
        key_considerations = list(dict.fromkeys(all_concerns))[:8]

        # Final conditions (all conditions from CONDITIONAL opinions)
        final_conditions = []
        for op in opinions:
            if op.position in ["CONDITIONAL", "SUPPORT"] and op.conditions:
                final_conditions.extend(op.conditions)
        final_conditions = list(dict.fromkeys(final_conditions))

        # Minority report
        minority_report = None
        if oppose_opinions:
            minority_report = f"MINORITY REPORT: {', '.join(op.agent_title for op in oppose_opinions)} dissent(s). Primary concern: " + "; ".join(op.reasoning[:100] for op in oppose_opinions)

        confidence_score = min(100.0, avg_score * 10)

        return ParliamentVerdict(
            question=question,
            majority_recommendation=majority_rec,
            dissenting_views=dissenting,
            confidence_score=confidence_score,
            key_considerations=key_considerations,
            unanimous=unanimous,
            debate_transcript=debate_transcript,
            vote_tally=vote_tally,
            final_conditions=final_conditions,
            minority_report=minority_report,
        )

    def deliberate_on_structure(self, proposed_structure: Dict[str, Any]) -> StructureVerdict:
        """
        Parliament deliberates on a proposed trust structure.

        Args:
            proposed_structure: Dict with: type, jurisdiction, trustee, beneficiaries,
                                assets, estimated_value, client_threats, goals
        """
        question = f"Should we implement: {proposed_structure.get('type', 'unnamed trust')} in {proposed_structure.get('jurisdiction', 'unknown jurisdiction')}?"
        context = proposed_structure

        opinions = []
        for agent_key in self.AGENTS:
            opinion = self._generate_opinion(agent_key, question, context, question.lower())
            opinions.append(opinion)

        avg_score = sum(op.score for op in opinions) / len(opinions)
        approval_score = avg_score * 10  # Convert to 0-100

        if approval_score >= 80:
            verdict = "APPROVED"
        elif approval_score >= 60:
            verdict = "APPROVED WITH CONDITIONS"
        elif approval_score >= 40:
            verdict = "NEEDS MAJOR MODIFICATIONS"
        else:
            verdict = "REJECTED"

        all_conditions = []
        warnings = []
        for op in opinions:
            all_conditions.extend(op.conditions)
            if op.position == "OPPOSE":
                warnings.append(f"⚠️ {op.agent_title}: {op.key_concerns[0] if op.key_concerns else 'Serious concerns'}")

        return StructureVerdict(
            proposed_structure=proposed_structure,
            overall_verdict=verdict,
            approval_score=approval_score,
            required_modifications=list(dict.fromkeys(all_conditions)),
            warnings=warnings,
            agent_opinions=opinions,
            implementation_prerequisites=[
                "Engage qualified trust attorney in target jurisdiction",
                "Conduct fraudulent transfer risk analysis before any transfers",
                "Obtain formal legal opinion on structure effectiveness",
                "Review all tax implications with qualified CPA",
                "Ensure all compliance requirements are calendared and budgeted",
            ],
        )

    def vote_on_jurisdiction(
        self, options: List[str], client_profile: Dict[str, Any]
    ) -> JurisdictionVerdict:
        """
        Parliament votes on the best jurisdiction from a list of options.

        Args:
            options: List of jurisdiction names (e.g., ["South Dakota", "Nevada", "Cook Islands"])
            client_profile: Dict with: threat_level, net_worth, goals, offshore_acceptable
        """
        jurisdiction_scores: Dict[str, float] = {}

        # Each agent scores each jurisdiction based on their expertise
        jurisdiction_preferences = {
            "asset_protection_counsel": {
                "cook islands": 10, "nevis": 9, "south dakota": 8, "nevada": 9, "wyoming": 8,
                "alaska": 7, "delaware": 7, "liechtenstein": 8,
            },
            "tax_strategist": {
                "south dakota": 10, "nevada": 9, "wyoming": 9, "alaska": 9, "delaware": 8,
                "cook islands": 5, "nevis": 5, "liechtenstein": 4,
            },
            "estate_planning_specialist": {
                "south dakota": 10, "delaware": 9, "nevada": 8, "wyoming": 8, "alaska": 8,
                "cook islands": 6, "nevis": 6, "liechtenstein": 7,
            },
            "compliance_officer": {
                "south dakota": 9, "nevada": 8, "delaware": 9, "wyoming": 8, "alaska": 8,
                "cook islands": 4, "nevis": 5, "liechtenstein": 3,
            },
            "jurisdiction_expert": {
                "south dakota": 10, "nevada": 9, "wyoming": 8, "alaska": 8, "delaware": 8,
                "cook islands": 9, "nevis": 8, "liechtenstein": 8,
            },
            "beneficiary_advocate": {
                "south dakota": 8, "nevada": 7, "delaware": 9, "wyoming": 7, "alaska": 7,
                "cook islands": 5, "nevis": 5, "liechtenstein": 6,
            },
        }

        for option in options:
            option_lower = option.lower()
            total = 0.0
            for agent_key, prefs in jurisdiction_preferences.items():
                matched = 0.0
                for jkey, score in prefs.items():
                    if jkey in option_lower:
                        matched = score
                        break
                total += matched if matched else 5.0  # Default 5 if not specifically rated
            jurisdiction_scores[option] = round(total / len(jurisdiction_preferences), 2)

        sorted_options = sorted(jurisdiction_scores.items(), key=lambda x: x[1], reverse=True)
        winner = sorted_options[0][0] if sorted_options else (options[0] if options else "South Dakota")
        runner_up = sorted_options[1][0] if len(sorted_options) > 1 else "Nevada"

        # Determine consensus level
        scores = list(jurisdiction_scores.values())
        score_range = max(scores) - min(scores) if scores else 0
        if score_range < 0.5:
            consensus = "UNANIMOUS"
        elif score_range < 1.5:
            consensus = "MAJORITY"
        elif score_range < 3.0:
            consensus = "SPLIT"
        else:
            consensus = "DIVIDED"

        # Find dissenting jurisdictions (any agent's top choice that isn't the winner)
        dissenting = []
        for agent_key, prefs in jurisdiction_preferences.items():
            best_for_agent = max(
                options,
                key=lambda o: prefs.get(o.lower(), 5),
                default=winner
            )
            if best_for_agent.lower() != winner.lower() and best_for_agent not in dissenting:
                dissenting.append(f"{self.AGENTS[agent_key].title} prefers: {best_for_agent}")

        minority_pref = dissenting[0] if dissenting else None

        return JurisdictionVerdict(
            options_considered=options,
            recommended_jurisdiction=winner,
            runner_up=runner_up,
            consensus_level=consensus,
            jurisdiction_scores=jurisdiction_scores,
            dissenting_jurisdictions=dissenting,
            rationale=(
                f"{winner} wins with a parliament score of {jurisdiction_scores.get(winner, 0):.1f}/10, "
                f"reflecting strong performance across asset protection, tax efficiency, and regulatory compliance dimensions. "
                f"Runner-up {runner_up} ({jurisdiction_scores.get(runner_up, 0):.1f}/10) is recommended as an alternative "
                f"or complementary jurisdiction for specific sub-structures."
            ),
            minority_preference=minority_pref,
        )
