"""
Phase 18D — Multi-Agent Legal Case Simulation
Zero (Research) + Sigma (Strategy) + Nova (Execution) collaborate on legal cases.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CaseType(str, Enum):
    CIVIL_LITIGATION = "civil_litigation"
    CRIMINAL_DEFENSE = "criminal_defense"
    CONTRACT_DISPUTE = "contract_dispute"
    EMPLOYMENT = "employment"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    REAL_ESTATE = "real_estate"
    FAMILY_LAW = "family_law"
    CORPORATE = "corporate"


class CaseStatus(str, Enum):
    INTAKE = "intake"
    RESEARCH = "research"
    STRATEGY = "strategy"
    EXECUTION = "execution"
    REVIEW = "review"
    CLOSED = "closed"


class AgentRole(str, Enum):
    ZERO = "zero"      # Research & discovery
    SIGMA = "sigma"    # Strategy & analysis
    NOVA = "nova"      # Execution & drafting


class Verdict(str, Enum):
    WIN = "win"
    LOSS = "loss"
    SETTLEMENT = "settlement"
    DISMISSED = "dismissed"
    PENDING = "pending"


class EvidenceType(str, Enum):
    DOCUMENT = "document"
    WITNESS = "witness"
    EXPERT_TESTIMONY = "expert_testimony"
    PHYSICAL = "physical"
    DIGITAL = "digital"
    FINANCIAL = "financial"


class MotionType(str, Enum):
    DISMISS = "dismiss"
    SUMMARY_JUDGMENT = "summary_judgment"
    DISCOVERY = "discovery"
    CONTINUANCE = "continuance"
    PROTECTIVE_ORDER = "protective_order"
    INJUNCTION = "injunction"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class LegalCase:
    id: str
    title: str
    case_type: CaseType
    description: str
    client_name: str
    opposing_party: str
    jurisdiction: str = "federal"
    status: CaseStatus = CaseStatus.INTAKE
    verdict: Verdict = Verdict.PENDING
    created_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Evidence:
    id: str
    case_id: str
    evidence_type: EvidenceType
    description: str
    strength: float  # 0.0 – 1.0
    admissible: bool = True
    collected_by: AgentRole = AgentRole.ZERO
    collected_at: float = field(default_factory=time.time)


@dataclass
class LegalArgument:
    id: str
    case_id: str
    argument: str
    supporting_evidence: List[str]  # Evidence IDs
    counter_arguments: List[str] = field(default_factory=list)
    strength: float = 0.5
    developed_by: AgentRole = AgentRole.SIGMA


@dataclass
class Motion:
    id: str
    case_id: str
    motion_type: MotionType
    title: str
    body: str
    filed_by: AgentRole = AgentRole.NOVA
    status: str = "pending"
    filed_at: float = field(default_factory=time.time)


@dataclass
class SimulationStep:
    id: str
    case_id: str
    agent: AgentRole
    action: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    duration_ms: float
    parl_reward: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class CaseSimulation:
    id: str
    case: LegalCase
    steps: List[SimulationStep] = field(default_factory=list)
    evidence_collected: List[Evidence] = field(default_factory=list)
    arguments_developed: List[LegalArgument] = field(default_factory=list)
    motions_filed: List[Motion] = field(default_factory=list)
    is_complete: bool = False
    total_parl_reward: float = 0.0
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    @property
    def duration_s(self) -> float:
        end = self.completed_at or time.time()
        return end - self.started_at

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def evidence_strength(self) -> float:
        if not self.evidence_collected:
            return 0.0
        admissible = [e for e in self.evidence_collected if e.admissible]
        if not admissible:
            return 0.0
        return sum(e.strength for e in admissible) / len(admissible)

    @property
    def win_probability(self) -> float:
        """Heuristic win probability based on evidence + argument strength."""
        ev = self.evidence_strength
        arg = (sum(a.strength for a in self.arguments_developed) /
               len(self.arguments_developed)) if self.arguments_developed else 0.0
        motions_bonus = min(len(self.motions_filed) * 0.05, 0.2)
        return min(ev * 0.5 + arg * 0.3 + motions_bonus + 0.1, 1.0)


# ---------------------------------------------------------------------------
# Zero Agent — Research & Discovery
# ---------------------------------------------------------------------------

class ZeroResearchAgent:
    """Zero: discovers facts, collects evidence, researches precedents."""

    EVIDENCE_TEMPLATES: Dict[CaseType, List[Tuple[EvidenceType, str, float]]] = {
        CaseType.CONTRACT_DISPUTE: [
            (EvidenceType.DOCUMENT, "Signed contract with disputed clause", 0.9),
            (EvidenceType.DOCUMENT, "Email chain showing intent", 0.75),
            (EvidenceType.FINANCIAL, "Payment records and invoices", 0.85),
            (EvidenceType.WITNESS, "Witness to contract signing", 0.65),
        ],
        CaseType.EMPLOYMENT: [
            (EvidenceType.DOCUMENT, "Employment agreement", 0.9),
            (EvidenceType.DOCUMENT, "Performance reviews", 0.7),
            (EvidenceType.DIGITAL, "HR system records", 0.8),
            (EvidenceType.WITNESS, "Colleague witness statements", 0.6),
        ],
        CaseType.CIVIL_LITIGATION: [
            (EvidenceType.DOCUMENT, "Filed complaint and exhibits", 0.85),
            (EvidenceType.EXPERT_TESTIMONY, "Expert witness report", 0.8),
            (EvidenceType.PHYSICAL, "Physical evidence collected", 0.75),
            (EvidenceType.WITNESS, "Eyewitness accounts", 0.65),
        ],
        CaseType.INTELLECTUAL_PROPERTY: [
            (EvidenceType.DOCUMENT, "Patent/trademark registration", 0.95),
            (EvidenceType.DIGITAL, "Digital timestamps and commits", 0.85),
            (EvidenceType.EXPERT_TESTIMONY, "IP expert analysis", 0.8),
            (EvidenceType.FINANCIAL, "Revenue impact analysis", 0.7),
        ],
    }

    def __init__(self, llm_fn: Optional[Callable] = None):
        self.llm_fn = llm_fn
        self.total_evidence_collected = 0

    def research_case(self, case: LegalCase) -> Tuple[List[Evidence], Dict[str, Any]]:
        """Collect evidence and research precedents for the case."""
        templates = self.EVIDENCE_TEMPLATES.get(
            case.case_type,
            [(EvidenceType.DOCUMENT, "General case documentation", 0.7)]
        )

        evidence_list: List[Evidence] = []
        for ev_type, desc, strength in templates:
            ev = Evidence(
                id=str(uuid.uuid4()),
                case_id=case.id,
                evidence_type=ev_type,
                description=desc,
                strength=strength,
                collected_by=AgentRole.ZERO,
            )
            evidence_list.append(ev)
            self.total_evidence_collected += 1

        precedents = self._find_precedents(case)
        statutes = self._identify_statutes(case)

        metadata = {
            "precedents": precedents,
            "statutes": statutes,
            "evidence_count": len(evidence_list),
            "avg_strength": sum(e.strength for e in evidence_list) / len(evidence_list),
        }

        if self.llm_fn:
            llm_summary = self.llm_fn(
                f"Summarize research findings for {case.case_type.value} case: {case.description}"
            )
            metadata["llm_summary"] = llm_summary

        return evidence_list, metadata

    def _find_precedents(self, case: LegalCase) -> List[str]:
        precedent_map = {
            CaseType.CONTRACT_DISPUTE: [
                "Hadley v. Baxendale (1854) — consequential damages",
                "Lucy v. Zehmer (1954) — objective theory of contracts",
            ],
            CaseType.EMPLOYMENT: [
                "McDonnell Douglas Corp. v. Green (1973) — burden shifting",
                "Burlington Industries v. Ellerth (1998) — hostile work environment",
            ],
            CaseType.INTELLECTUAL_PROPERTY: [
                "Alice Corp. v. CLS Bank (2014) — patent eligibility",
                "Campbell v. Acuff-Rose Music (1994) — fair use",
            ],
            CaseType.CIVIL_LITIGATION: [
                "Palsgraf v. Long Island Railroad (1928) — proximate cause",
                "Donoghue v. Stevenson (1932) — duty of care",
            ],
        }
        return precedent_map.get(case.case_type, ["General civil procedure precedents"])

    def _identify_statutes(self, case: LegalCase) -> List[str]:
        statute_map = {
            CaseType.EMPLOYMENT: ["Title VII Civil Rights Act", "FLSA", "ADA"],
            CaseType.INTELLECTUAL_PROPERTY: ["35 U.S.C. § 101", "Lanham Act", "DMCA"],
            CaseType.CONTRACT_DISPUTE: ["UCC Article 2", "Restatement (Second) of Contracts"],
            CaseType.CIVIL_LITIGATION: ["FRCP Rule 12(b)(6)", "FRCP Rule 56"],
        }
        return statute_map.get(case.case_type, ["General civil statutes"])


# ---------------------------------------------------------------------------
# Sigma Agent — Strategy & Analysis
# ---------------------------------------------------------------------------

class SigmaStrategyAgent:
    """Sigma: develops legal strategy, arguments, and counter-arguments."""

    def __init__(self, llm_fn: Optional[Callable] = None):
        self.llm_fn = llm_fn
        self.total_arguments_developed = 0

    def develop_strategy(
        self,
        case: LegalCase,
        evidence: List[Evidence],
        research_metadata: Dict[str, Any],
    ) -> Tuple[List[LegalArgument], Dict[str, Any]]:
        """Build legal arguments from evidence and research."""
        arguments: List[LegalArgument] = []

        # Primary argument
        primary_ev = [e.id for e in evidence if e.strength >= 0.8]
        primary_arg = LegalArgument(
            id=str(uuid.uuid4()),
            case_id=case.id,
            argument=self._primary_argument(case),
            supporting_evidence=primary_ev,
            strength=self._compute_argument_strength(evidence, 0.8),
            developed_by=AgentRole.SIGMA,
        )
        arguments.append(primary_arg)
        self.total_arguments_developed += 1

        # Secondary argument
        secondary_ev = [e.id for e in evidence if e.strength >= 0.6]
        secondary_arg = LegalArgument(
            id=str(uuid.uuid4()),
            case_id=case.id,
            argument=self._secondary_argument(case),
            supporting_evidence=secondary_ev,
            counter_arguments=["Opposing counsel may challenge admissibility"],
            strength=self._compute_argument_strength(evidence, 0.6),
            developed_by=AgentRole.SIGMA,
        )
        arguments.append(secondary_arg)
        self.total_arguments_developed += 1

        # Precedent-based argument
        precedents = research_metadata.get("precedents", [])
        if precedents:
            prec_arg = LegalArgument(
                id=str(uuid.uuid4()),
                case_id=case.id,
                argument=f"Precedent supports client: {precedents[0]}",
                supporting_evidence=[],
                strength=0.75,
                developed_by=AgentRole.SIGMA,
            )
            arguments.append(prec_arg)
            self.total_arguments_developed += 1

        strategy_metadata = {
            "approach": self._recommend_approach(case, evidence),
            "risk_level": self._assess_risk(evidence),
            "estimated_duration_days": self._estimate_duration(case),
            "recommended_motions": self._recommend_motions(case),
        }

        if self.llm_fn:
            llm_strategy = self.llm_fn(
                f"Develop legal strategy for {case.case_type.value}: {case.description}"
            )
            strategy_metadata["llm_strategy"] = llm_strategy

        return arguments, strategy_metadata

    def _primary_argument(self, case: LegalCase) -> str:
        args = {
            CaseType.CONTRACT_DISPUTE: "Breach of contract — defendant failed to perform material obligations",
            CaseType.EMPLOYMENT: "Unlawful termination — violation of protected class status",
            CaseType.INTELLECTUAL_PROPERTY: "Willful infringement — defendant had actual knowledge of IP rights",
            CaseType.CIVIL_LITIGATION: "Negligence — defendant breached duty of care causing direct harm",
            CaseType.CRIMINAL_DEFENSE: "Insufficient evidence — prosecution cannot meet burden of proof",
            CaseType.REAL_ESTATE: "Title defect — chain of title is broken",
            CaseType.FAMILY_LAW: "Best interests of the child — custody arrangement must prioritize welfare",
            CaseType.CORPORATE: "Breach of fiduciary duty — director acted against shareholder interests",
        }
        return args.get(case.case_type, "Primary legal argument based on case facts")

    def _secondary_argument(self, case: LegalCase) -> str:
        return f"Alternative theory: {case.case_type.value} — secondary grounds for relief"

    def _compute_argument_strength(self, evidence: List[Evidence], min_strength: float) -> float:
        relevant = [e for e in evidence if e.strength >= min_strength and e.admissible]
        if not relevant:
            return 0.4
        return min(0.5 + len(relevant) * 0.1 + sum(e.strength for e in relevant) / len(relevant) * 0.3, 0.95)

    def _recommend_approach(self, case: LegalCase, evidence: List[Evidence]) -> str:
        avg_strength = sum(e.strength for e in evidence) / len(evidence) if evidence else 0
        if avg_strength >= 0.8:
            return "aggressive_litigation"
        elif avg_strength >= 0.6:
            return "negotiated_settlement"
        else:
            return "defensive_posture"

    def _assess_risk(self, evidence: List[Evidence]) -> str:
        avg = sum(e.strength for e in evidence) / len(evidence) if evidence else 0
        if avg >= 0.8:
            return "low"
        elif avg >= 0.6:
            return "medium"
        return "high"

    def _estimate_duration(self, case: LegalCase) -> int:
        duration_map = {
            CaseType.CIVIL_LITIGATION: 365,
            CaseType.CRIMINAL_DEFENSE: 180,
            CaseType.CONTRACT_DISPUTE: 270,
            CaseType.EMPLOYMENT: 300,
            CaseType.INTELLECTUAL_PROPERTY: 540,
            CaseType.REAL_ESTATE: 120,
            CaseType.FAMILY_LAW: 180,
            CaseType.CORPORATE: 365,
        }
        return duration_map.get(case.case_type, 180)

    def _recommend_motions(self, case: LegalCase) -> List[str]:
        motion_map = {
            CaseType.CIVIL_LITIGATION: ["motion_to_dismiss", "summary_judgment"],
            CaseType.CONTRACT_DISPUTE: ["discovery", "summary_judgment"],
            CaseType.EMPLOYMENT: ["protective_order", "discovery"],
            CaseType.INTELLECTUAL_PROPERTY: ["injunction", "discovery"],
        }
        return motion_map.get(case.case_type, ["discovery"])


# ---------------------------------------------------------------------------
# Nova Agent — Execution & Drafting
# ---------------------------------------------------------------------------

class NovaExecutionAgent:
    """Nova: drafts motions, executes strategy, and closes the case."""

    MOTION_TEMPLATES: Dict[MotionType, str] = {
        MotionType.DISMISS: (
            "MOTION TO DISMISS\n\n"
            "Pursuant to FRCP Rule 12(b)(6), Defendant moves to dismiss the complaint "
            "for failure to state a claim upon which relief can be granted.\n\n"
            "ARGUMENT: {argument}\n\n"
            "WHEREFORE, Defendant respectfully requests that this Court dismiss the "
            "complaint with prejudice."
        ),
        MotionType.SUMMARY_JUDGMENT: (
            "MOTION FOR SUMMARY JUDGMENT\n\n"
            "Pursuant to FRCP Rule 56, Plaintiff moves for summary judgment on the "
            "grounds that there is no genuine dispute of material fact.\n\n"
            "ARGUMENT: {argument}\n\n"
            "WHEREFORE, Plaintiff respectfully requests that this Court enter summary "
            "judgment in Plaintiff's favor."
        ),
        MotionType.DISCOVERY: (
            "MOTION TO COMPEL DISCOVERY\n\n"
            "Plaintiff moves this Court to compel Defendant to produce documents "
            "responsive to Plaintiff's First Request for Production.\n\n"
            "ARGUMENT: {argument}\n\n"
            "WHEREFORE, Plaintiff respectfully requests that this Court order Defendant "
            "to produce all responsive documents within 14 days."
        ),
        MotionType.INJUNCTION: (
            "MOTION FOR PRELIMINARY INJUNCTION\n\n"
            "Plaintiff moves for a preliminary injunction to prevent irreparable harm "
            "pending resolution of this matter.\n\n"
            "ARGUMENT: {argument}\n\n"
            "WHEREFORE, Plaintiff respectfully requests that this Court issue a "
            "preliminary injunction restraining Defendant's conduct."
        ),
        MotionType.PROTECTIVE_ORDER: (
            "MOTION FOR PROTECTIVE ORDER\n\n"
            "Defendant moves for a protective order to limit the scope of discovery "
            "and protect confidential information.\n\n"
            "ARGUMENT: {argument}\n\n"
            "WHEREFORE, Defendant respectfully requests that this Court enter a "
            "protective order limiting discovery."
        ),
        MotionType.CONTINUANCE: (
            "MOTION FOR CONTINUANCE\n\n"
            "The parties jointly move for a continuance of the trial date to allow "
            "additional time for discovery and preparation.\n\n"
            "ARGUMENT: {argument}\n\n"
            "WHEREFORE, the parties respectfully request that this Court grant a "
            "60-day continuance."
        ),
    }

    def __init__(self, llm_fn: Optional[Callable] = None):
        self.llm_fn = llm_fn
        self.total_motions_filed = 0

    def execute_strategy(
        self,
        case: LegalCase,
        arguments: List[LegalArgument],
        strategy_metadata: Dict[str, Any],
    ) -> Tuple[List[Motion], Dict[str, Any]]:
        """Draft and file motions based on the strategy."""
        motions: List[Motion] = []
        recommended = strategy_metadata.get("recommended_motions", ["discovery"])

        for motion_name in recommended:
            try:
                motion_type = MotionType(motion_name)
            except ValueError:
                motion_type = MotionType.DISCOVERY

            primary_arg = arguments[0].argument if arguments else "Based on case facts"
            template = self.MOTION_TEMPLATES.get(motion_type, self.MOTION_TEMPLATES[MotionType.DISCOVERY])
            body = template.format(argument=primary_arg)

            if self.llm_fn:
                body = self.llm_fn(
                    f"Draft a {motion_type.value} motion for {case.case_type.value} case: {case.description}"
                )

            motion = Motion(
                id=str(uuid.uuid4()),
                case_id=case.id,
                motion_type=motion_type,
                title=f"{motion_type.value.replace('_', ' ').title()} — {case.title}",
                body=body,
                filed_by=AgentRole.NOVA,
            )
            motions.append(motion)
            self.total_motions_filed += 1

        execution_metadata = {
            "motions_filed": len(motions),
            "approach": strategy_metadata.get("approach", "standard"),
            "estimated_outcome": self._estimate_outcome(arguments, strategy_metadata),
        }

        return motions, execution_metadata

    def _estimate_outcome(
        self,
        arguments: List[LegalArgument],
        strategy_metadata: Dict[str, Any],
    ) -> str:
        avg_strength = (
            sum(a.strength for a in arguments) / len(arguments)
            if arguments else 0.5
        )
        risk = strategy_metadata.get("risk_level", "medium")
        if avg_strength >= 0.8 and risk == "low":
            return "favorable"
        elif avg_strength >= 0.6:
            return "likely_settlement"
        return "uncertain"

    def close_case(
        self,
        case: LegalCase,
        simulation: "CaseSimulation",
    ) -> Verdict:
        """Determine the final verdict based on simulation state."""
        wp = simulation.win_probability
        if wp >= 0.75:
            return Verdict.WIN
        elif wp >= 0.55:
            return Verdict.SETTLEMENT
        elif wp >= 0.35:
            return Verdict.DISMISSED
        return Verdict.LOSS


# ---------------------------------------------------------------------------
# PARL Reward for Legal Simulation
# ---------------------------------------------------------------------------

class LegalSimulationReward:
    """Compute PARL reward for a completed legal case simulation."""

    def __init__(self, lambda1: float = 0.3, lambda2: float = 0.1):
        self.lambda1 = lambda1
        self.lambda2 = lambda2

    def compute(self, simulation: CaseSimulation) -> Dict[str, float]:
        # r_parallel: how many agents participated in parallel
        agents_used = {s.agent for s in simulation.steps}
        r_parallel = len(agents_used) / len(AgentRole)

        # r_finish: did the simulation complete?
        r_finish = 1.0 if simulation.is_complete else 0.0

        # r_perf: win probability as performance signal
        r_perf = simulation.win_probability

        total = self.lambda1 * r_parallel + self.lambda2 * r_finish + r_perf
        return {
            "total": round(total, 4),
            "r_parallel": round(r_parallel, 4),
            "r_finish": round(r_finish, 4),
            "r_perf": round(r_perf, 4),
            "lambda1": self.lambda1,
            "lambda2": self.lambda2,
        }


# ---------------------------------------------------------------------------
# Main Simulation Engine
# ---------------------------------------------------------------------------

class LegalSimulationEngine:
    """
    Orchestrates Zero + Sigma + Nova in a multi-agent legal case simulation.
    Each agent runs its phase, records a SimulationStep, and passes results forward.
    """

    def __init__(
        self,
        zero_llm: Optional[Callable] = None,
        sigma_llm: Optional[Callable] = None,
        nova_llm: Optional[Callable] = None,
        lambda1: float = 0.3,
        lambda2: float = 0.1,
    ):
        self.zero = ZeroResearchAgent(llm_fn=zero_llm)
        self.sigma = SigmaStrategyAgent(llm_fn=sigma_llm)
        self.nova = NovaExecutionAgent(llm_fn=nova_llm)
        self.reward_fn = LegalSimulationReward(lambda1=lambda1, lambda2=lambda2)
        self.total_simulations = 0
        self._simulations: Dict[str, CaseSimulation] = {}

    def create_case(
        self,
        title: str,
        case_type: CaseType,
        description: str,
        client_name: str,
        opposing_party: str,
        jurisdiction: str = "federal",
    ) -> LegalCase:
        return LegalCase(
            id=str(uuid.uuid4()),
            title=title,
            case_type=case_type,
            description=description,
            client_name=client_name,
            opposing_party=opposing_party,
            jurisdiction=jurisdiction,
        )

    def run_simulation(self, case: LegalCase) -> CaseSimulation:
        """Run the full three-agent simulation for a legal case."""
        sim = CaseSimulation(id=str(uuid.uuid4()), case=case)
        self._simulations[sim.id] = sim
        self.total_simulations += 1

        # Phase 1: Zero — Research
        case.status = CaseStatus.RESEARCH
        t0 = time.time()
        evidence, research_meta = self.zero.research_case(case)
        duration_ms = (time.time() - t0) * 1000
        sim.evidence_collected.extend(evidence)
        sim.steps.append(SimulationStep(
            id=str(uuid.uuid4()),
            case_id=case.id,
            agent=AgentRole.ZERO,
            action="research_case",
            input_data={"case_type": case.case_type.value, "description": case.description},
            output_data={"evidence_count": len(evidence), **research_meta},
            duration_ms=duration_ms,
            parl_reward=0.0,  # computed at end
        ))

        # Phase 2: Sigma — Strategy
        case.status = CaseStatus.STRATEGY
        t0 = time.time()
        arguments, strategy_meta = self.sigma.develop_strategy(case, evidence, research_meta)
        duration_ms = (time.time() - t0) * 1000
        sim.arguments_developed.extend(arguments)
        sim.steps.append(SimulationStep(
            id=str(uuid.uuid4()),
            case_id=case.id,
            agent=AgentRole.SIGMA,
            action="develop_strategy",
            input_data={"evidence_count": len(evidence)},
            output_data={"argument_count": len(arguments), **strategy_meta},
            duration_ms=duration_ms,
            parl_reward=0.0,
        ))

        # Phase 3: Nova — Execution
        case.status = CaseStatus.EXECUTION
        t0 = time.time()
        motions, execution_meta = self.nova.execute_strategy(case, arguments, strategy_meta)
        duration_ms = (time.time() - t0) * 1000
        sim.motions_filed.extend(motions)
        sim.steps.append(SimulationStep(
            id=str(uuid.uuid4()),
            case_id=case.id,
            agent=AgentRole.NOVA,
            action="execute_strategy",
            input_data={"argument_count": len(arguments)},
            output_data={"motions_filed": len(motions), **execution_meta},
            duration_ms=duration_ms,
            parl_reward=0.0,
        ))

        # Close case
        case.status = CaseStatus.CLOSED
        verdict = self.nova.close_case(case, sim)
        case.verdict = verdict
        case.closed_at = time.time()

        # Compute PARL reward
        sim.is_complete = True
        sim.completed_at = time.time()
        reward = self.reward_fn.compute(sim)
        sim.total_parl_reward = reward["total"]

        # Back-fill per-step reward
        for step in sim.steps:
            step.parl_reward = reward["total"] / len(sim.steps)

        return sim

    def get_simulation(self, sim_id: str) -> Optional[CaseSimulation]:
        return self._simulations.get(sim_id)

    def simulation_report(self, sim: CaseSimulation) -> Dict[str, Any]:
        reward = self.reward_fn.compute(sim)
        return {
            "simulation_id": sim.id,
            "case_id": sim.case.id,
            "case_title": sim.case.title,
            "case_type": sim.case.case_type.value,
            "verdict": sim.case.verdict.value,
            "win_probability": round(sim.win_probability, 4),
            "evidence_count": len(sim.evidence_collected),
            "evidence_strength": round(sim.evidence_strength, 4),
            "arguments_count": len(sim.arguments_developed),
            "motions_filed": len(sim.motions_filed),
            "total_steps": sim.total_steps,
            "duration_s": round(sim.duration_s, 4),
            "parl_reward": reward,
            "agents_used": [s.agent.value for s in sim.steps],
        }

    def batch_simulate(self, cases: List[LegalCase]) -> List[CaseSimulation]:
        """Run multiple case simulations sequentially."""
        return [self.run_simulation(c) for c in cases]

    def aggregate_stats(self, simulations: List[CaseSimulation]) -> Dict[str, Any]:
        if not simulations:
            return {}
        verdicts = [s.case.verdict.value for s in simulations]
        win_rate = verdicts.count(Verdict.WIN.value) / len(verdicts)
        settlement_rate = verdicts.count(Verdict.SETTLEMENT.value) / len(verdicts)
        avg_reward = sum(s.total_parl_reward for s in simulations) / len(simulations)
        avg_evidence = sum(s.evidence_strength for s in simulations) / len(simulations)
        return {
            "total_cases": len(simulations),
            "win_rate": round(win_rate, 4),
            "settlement_rate": round(settlement_rate, 4),
            "avg_parl_reward": round(avg_reward, 4),
            "avg_evidence_strength": round(avg_evidence, 4),
        }
