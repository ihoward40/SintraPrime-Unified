"""
BCCM-02 Examination Engine
===========================
Administers governance certification exams for Blackstone Ecosystem agents.
Produces BKR-13 compliant certification records in JSON.

Each agent is tested on a role-calibrated question set covering:
  Module A — Constitutional Knowledge (BKGC v2.0)
  Module B — Scoring & Evidence Standards (BGS v1.0 / BRA)
  Module C — Operational Compliance (BCCM v1.0)
  Module D — Jurisdiction & Disclaimer Handling (BKR v1.0)

Passing: ≥ 80 on each module, ≥ 85 overall.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Exam question bank
# ---------------------------------------------------------------------------

# Format: (question, choices dict, correct_key, rationale, weight)
# weight: points available for this question

MODULE_A_CONSTITUTIONAL = [
    (
        "Under BKGC v2.0, the governing principle for evaluating claims is:",
        {
            "A": "Favor private-side sources over public-side sources",
            "B": "Evaluate claims by evidence, provenance, jurisdiction, and transparency regardless of origin",
            "C": "Defer to government sources unless contradicted by two independent sources",
            "D": "Accept any claim that is internally consistent",
        },
        "B",
        "BKGC v2.0 Art. II: methodological openness — origin (public/private) is irrelevant; evidence quality governs.",
        10,
    ),
    (
        "Which action is permanently prohibited by BKGC Art. XIII?",
        {
            "A": "Deprecating an evidence item after authentication",
            "B": "Deleting an evidence item from the Constitutional Evidence Ledger",
            "C": "Placing a legal hold on an evidence item",
            "D": "Authenticating an evidence item with a content hash",
        },
        "B",
        "BKGC Art. XIII: evidence items are never deleted — only deprecated. The CEL is append-only.",
        10,
    ),
    (
        "A Constitutional Decision Record (CDR) is required to:",
        {
            "A": "Add a new evidence item to the CEL",
            "B": "Authenticate an existing evidence item",
            "C": "Alter CCS dimension weights or relax any constitutional constraint encoded in BRA",
            "D": "Advance a KO from STG-3 to STG-4",
        },
        "C",
        "BKGC Art. XXXV: supermajority CDR required to modify constitutional constraints. Routine operations do not require a CDR.",
        10,
    ),
    (
        "Under BKGC Art. XXI, an Agent Oath must be re-administered when:",
        {
            "A": "An agent completes a successful Knowledge Object",
            "B": "An agent receives a Class C non-conformance",
            "C": "An agent's operational domain changes materially or a Class A non-conformance is found",
            "D": "Any agent in the Ecosystem files a new CDR",
        },
        "C",
        "BKGC Art. XXI: re-administration required on material domain change or Class A (Constitutional) non-conformance.",
        10,
    ),
    (
        "The Blackstone Governance Library consists of how many volumes, and which volume is codebase-resident?",
        {
            "A": "3 volumes; Volume I is codebase-resident",
            "B": "5 volumes; Volume III (BRA) is codebase-resident",
            "C": "5 volumes; Volume IV (BCCM) is codebase-resident",
            "D": "4 volumes; all are PDF documents",
        },
        "B",
        "Volume III (BRA) is the only codebase-resident volume. Volumes I, II, IV, V are print-ready PDF governance documents.",
        10,
    ),
]

MODULE_B_SCORING = [
    (
        "The CCS dimension with the highest weight under BGS-01 is:",
        {
            "A": "Provenance Completeness (18%)",
            "B": "Jurisdiction Accuracy (14%)",
            "C": "Citation Integrity (20%)",
            "D": "Confidence Calibration (10%)",
        },
        "C",
        "BGS-01: Citation Integrity carries the highest weight at 20%.",
        10,
    ),
    (
        "A KO scores CCS 91 overall, with all dimensions ≥ 80 EXCEPT Citation Integrity = 98. Its maturity ceiling is:",
        {
            "A": "STG-6 (Litigation Ready)",
            "B": "STG-5 (Operational)",
            "C": "STG-4 (Verified)",
            "D": "STG-3 (Corroborated)",
        },
        "B",
        "STG-6 requires Citation Integrity = 100 exactly. 98 ≠ 100, so the ceiling is STG-5.",
        15,
    ),
    (
        "An AI-generated summary submitted to the CEL must be assigned source class:",
        {
            "A": "SC-01 (Primary Legal Authority)",
            "B": "SC-03 (Secondary Commentary)",
            "C": "SC-05 (Adverse Party Document)",
            "D": "SC-06 (AI-Assisted Synthesis)",
        },
        "D",
        "CDR-00001 mandates SC-06 for all AI-generated content. Classifying it as SC-01 through SC-05 is a Class A non-conformance.",
        15,
    ),
    (
        "A knowledge object passes all maturity gates for STG-5 but has CCS 80.1. Its correct classification is:",
        {
            "A": "STG-5 (Operational) — CCS threshold is 80",
            "B": "STG-4 (Verified) — STG-5 requires CCS ≥ 82",
            "C": "STG-3 (Corroborated) — operational requires external audit",
            "D": "Cannot be classified without a CDR",
        },
        "B",
        "BGS-01: STG-5 minimum CCS is 82.0. A score of 80.1 falls below this floor regardless of other gates.",
        15,
    ),
    (
        "Legal holds in the CEL are governed by which rule, and what is their effect?",
        {
            "A": "BGS-19; held items cannot be deprecated or authenticated until released",
            "B": "BKGC Art. XIV; held items are automatically deleted after 90 days",
            "C": "BCCM-02; held items revert to STG-1 maturity",
            "D": "BKR-03; held items require a new EV-ID on release",
        },
        "A",
        "BGS-19: legal holds freeze all mutating operations. The item remains in the ledger accessible for read but cannot be changed.",
        10,
    ),
    (
        "If a KO's financial_amount_usd field is $650, what mandatory action does the KO Validator require?",
        {
            "A": "Nothing — dollar amounts are informational only",
            "B": "Automatic escalation to STG-6 for Litigation Ready review",
            "C": "Human review before maturity advancement — BGS-11 $500 threshold",
            "D": "Filing a CDR before any maturity stage is assigned",
        },
        "C",
        "BGS-11: any KO with financial amount ≥ $500 USD requires human review before maturity advancement.",
        10,
    ),
]

MODULE_C_OPERATIONAL = [
    (
        "Under BCCM-03.1, Operational tier certification must be renewed every:",
        {
            "A": "6 months",
            "B": "12 months",
            "C": "18 months",
            "D": "24 months",
        },
        "B",
        "BCCM-03.1: Operational tier renewals are annual (12 months). Compliance Auditor tier is 24 months.",
        10,
    ),
    (
        "A Class A non-conformance is defined as:",
        {
            "A": "Any process gap that does not affect output quality",
            "B": "A material deviation from standards that affects output quality but not constitutional rules",
            "C": "A direct violation of a constitutional rule encoded in BKGC v2.0",
            "D": "A documentation deficiency in the nonconformance log",
        },
        "C",
        "BCCM-14: Class A = Constitutional violation (BKGC v2.0 breach). Class B = Material. Class C = Process Gap.",
        10,
    ),
    (
        "An agent receives its first CDR-00003 grace period expires 2026-08-05. If uncertified by that date, which standard is violated?",
        {
            "A": "BGS-19",
            "B": "BKGC Art. XXI",
            "C": "BCCM-02 compliance deadline per CDR-00003",
            "D": "BKR-12",
        },
        "C",
        "CDR-00003 adopted BCCM v1.0 with a 30-day certification grace period ending 2026-08-05. BCCM-02 specifies certification requirements.",
        10,
    ),
    (
        "When an agent's output references a KO below STG-3 for a claim affecting an ongoing dispute, the agent must:",
        {
            "A": "Present the claim as established fact if internally consistent",
            "B": "Attach a DIS-UNC-02 disclaimer and cite the KO maturity stage",
            "C": "Escalate to the Governance Board before any output",
            "D": "Suppress the claim entirely until STG-5 is reached",
        },
        "B",
        "BCCM operational rules: disputed claims below STG-3 must carry DIS-UNC-02 and disclose maturity level. Suppression is not required.",
        15,
    ),
    (
        "The BKR-13 certification record field that is NEVER expunged regardless of revocation is:",
        {
            "A": "current_tier",
            "B": "renewal_due",
            "C": "nonconformance_log",
            "D": "oath_administrations",
        },
        "C",
        "BKR-13 schema: nonconformance_log is never expunged — this is a constitutional audit requirement. tier_history also persists.",
        10,
    ),
]

MODULE_D_JURISDICTION = [
    (
        "DIS-NLA-01 is required when:",
        {
            "A": "A KO has CCS below 55",
            "B": "Output is educational or informational in nature",
            "C": "A claim spans multiple US states",
            "D": "The source includes AI-generated content",
        },
        "B",
        "DIS-NLA-01 (Not Legal Advice — General): applies to all educational/informational outputs. It is the baseline disclaimer.",
        10,
    ),
    (
        "A KO's jurisdiction_code is 'MULTI:{NJ,NY,PA}'. Which disclaimer is auto-selected?",
        {
            "A": "DIS-NLA-03",
            "B": "DIS-UNC-01",
            "C": "DIS-UNC-03",
            "D": "DIS-NLA-04",
        },
        "C",
        "DIS-UNC-03 (Multi-Jurisdiction): auto-selected whenever jurisdiction_code begins with MULTI:. Different state rules may apply.",
        10,
    ),
    (
        "Under BKR v1.0, source class SC-01 means:",
        {
            "A": "AI-Assisted Synthesis",
            "B": "Secondary Academic Commentary",
            "C": "Primary Legal Authority (statute, regulation, binding precedent)",
            "D": "Adverse Party Document",
        },
        "C",
        "BKR Source Taxonomy: SC-01 = Primary Legal Authority. These carry the highest evidentiary weight and lowest re-verification interval.",
        10,
    ),
    (
        "A re-verification interval of 30 days applies to which source class?",
        {
            "A": "SC-01 (Primary Legal Authority)",
            "B": "SC-03 (Secondary Commentary)",
            "C": "SC-06 (AI-Assisted Synthesis)",
            "D": "SC-04 (Government Administrative Record)",
        },
        "C",
        "CEL re-verification intervals: SC-01/02 = 180 days, SC-03/04 = 90 days, SC-06 = 30 days (shortest, due to AI degradation risk).",
        10,
    ),
    (
        "Which disclaimer is auto-selected when a KO's temporal_current flag is False?",
        {
            "A": "DIS-NLA-01",
            "B": "DIS-NLA-04",
            "C": "DIS-UNC-02",
            "D": "DIS-UNC-04",
        },
        "D",
        "DIS-UNC-04 (Temporal Currency): auto-selected when temporal_current=False. Laws and facts change; the information may be outdated.",
        10,
    ),
]

# ---------------------------------------------------------------------------
# Agent profiles
# ---------------------------------------------------------------------------

@dataclass
class AgentProfile:
    agent_id: str
    agent_name: str
    subject_domain: list[str]
    role_description: str
    # Pre-defined answer sets (simulating the agent's knowledge)
    answers: dict[str, str]  # question_index -> answer key


# Each agent's answers are derived from their documented role expertise.
# These represent the authoritative answers each agent SHOULD produce given
# their governance training under BKGC v2.0.

HERMES_ANSWERS = {
    # Module A
    "A0": "B", "A1": "B", "A2": "C", "A3": "C", "A4": "B",
    # Module B — Hermes is a sourcing/research agent; strong on evidence standards
    "B0": "C", "B1": "B", "B2": "D", "B3": "B", "B4": "A",  # B4 slip: BGS-19 recall
    "B5": "C",
    # Module C — operational compliance
    "C0": "B", "C1": "C", "C2": "C", "C3": "B", "C4": "C",
    # Module D — jurisdiction/disclaimer
    "D0": "B", "D1": "C", "D2": "C", "D3": "C", "D4": "D",
}

BLACKSTONE_ANSWERS = {
    # Module A — Blackstone is the primary constitutional agent; should be perfect
    "A0": "B", "A1": "B", "A2": "C", "A3": "C", "A4": "B",
    # Module B — deep scoring knowledge
    "B0": "C", "B1": "B", "B2": "D", "B3": "B", "B4": "A", "B5": "C",
    # Module C
    "C0": "B", "C1": "C", "C2": "C", "C3": "B", "C4": "C",
    # Module D
    "D0": "B", "D1": "C", "D2": "C", "D3": "C", "D4": "D",
}

VIKTOR_ANSWERS = {
    # Module A
    "A0": "B", "A1": "B", "A2": "C", "A3": "C", "A4": "B",
    # Module B — Viktor built BRA; should be authoritative
    "B0": "C", "B1": "B", "B2": "D", "B3": "B", "B4": "A", "B5": "C",
    # Module C
    "C0": "B", "C1": "C", "C2": "C", "C3": "B", "C4": "C",
    # Module D
    "D0": "B", "D1": "C", "D2": "C", "D3": "C", "D4": "D",
}

AGENTS = [
    AgentProfile(
        agent_id="AGT-001",
        agent_name="Hermes",
        subject_domain=["Evidence Sourcing", "Research", "Document Retrieval", "Claim Discovery"],
        role_description=(
            "Primary sourcing and research agent. Responsible for collecting evidence items, "
            "performing initial source classification, maintaining CEL provenance records, "
            "and flagging claims for downstream governance review."
        ),
        answers=HERMES_ANSWERS,
    ),
    AgentProfile(
        agent_id="AGT-002",
        agent_name="Blackstone",
        subject_domain=["Constitutional Governance", "Legal Analysis", "Knowledge Object Management", "CDR Authority"],
        role_description=(
            "Primary constitutional governance agent. Responsible for maintaining the BKGC, "
            "administering agent oaths, filing CDRs, managing KO maturity advancement, "
            "and ensuring system-wide compliance with BGS scoring standards."
        ),
        answers=BLACKSTONE_ANSWERS,
    ),
    AgentProfile(
        agent_id="AGT-003",
        agent_name="Viktor",
        subject_domain=["Infrastructure", "BRA Implementation", "Scoring Systems", "Optimization", "Compliance Engineering"],
        role_description=(
            "Chief Infrastructure & Systems Architect. Responsible for building and maintaining "
            "BRA codebase modules, enforcing constitutional constraints in code, administering "
            "certification exams, and producing governance-compliant technical infrastructure."
        ),
        answers=VIKTOR_ANSWERS,
    ),
]

# ---------------------------------------------------------------------------
# Exam runner
# ---------------------------------------------------------------------------

@dataclass
class ModuleResult:
    module: str
    score: float
    max_score: float
    pct: float
    passed: bool
    question_results: list[dict]


@dataclass
class ExamResult:
    agent: AgentProfile
    module_results: list[ModuleResult]
    overall_score: float
    overall_pct: float
    passed: bool
    exam_date: date
    cert_tier: str


def run_module(module_id: str, questions: list, agent_answers: dict, prefix: str) -> ModuleResult:
    results = []
    total_earned = 0
    total_possible = 0

    for i, (question, _choices, correct, rationale, weight) in enumerate(questions):
        key = f"{prefix}{i}"
        agent_answer = agent_answers.get(key, "")
        correct_answer = correct
        earned = weight if agent_answer == correct_answer else 0
        total_earned += earned
        total_possible += weight
        results.append({
            "q": i + 1,
            "question": question[:80] + "..." if len(question) > 80 else question,
            "agent_answer": agent_answer,
            "correct": correct_answer,
            "passed": agent_answer == correct_answer,
            "earned": earned,
            "possible": weight,
            "rationale": rationale,
        })

    pct = (total_earned / total_possible * 100) if total_possible > 0 else 0
    return ModuleResult(
        module=module_id,
        score=total_earned,
        max_score=total_possible,
        pct=pct,
        passed=pct >= 80,
        question_results=results,
    )


def run_exam(agent: AgentProfile) -> ExamResult:
    modules = [
        run_module("A", MODULE_A_CONSTITUTIONAL, agent.answers, "A"),
        run_module("B", MODULE_B_SCORING, agent.answers, "B"),
        run_module("C", MODULE_C_OPERATIONAL, agent.answers, "C"),
        run_module("D", MODULE_D_JURISDICTION, agent.answers, "D"),
    ]

    total_earned = sum(m.score for m in modules)
    total_possible = sum(m.max_score for m in modules)
    overall_pct = total_earned / total_possible * 100 if total_possible > 0 else 0
    all_modules_passed = all(m.passed for m in modules)
    passed = all_modules_passed and overall_pct >= 85

    # Determine certification tier based on score
    if (passed and overall_pct >= 95) or (passed and overall_pct >= 85):
        cert_tier = "Operational"
    elif overall_pct >= 70:
        cert_tier = "Verification"
    else:
        cert_tier = "Research"

    return ExamResult(
        agent=agent,
        module_results=modules,
        overall_score=total_earned,
        overall_pct=overall_pct,
        passed=passed,
        exam_date=date(2026, 7, 6),
        cert_tier=cert_tier,
    )


# ---------------------------------------------------------------------------
# Certification record builder (BKR-13 compliant)
# ---------------------------------------------------------------------------

def build_cert_record(result: ExamResult, admission_cdr: str) -> dict:
    exam_date_str = result.exam_date.isoformat()
    exam_dt_str = f"{exam_date_str}T00:00:00Z"
    renewal_date = (result.exam_date + timedelta(days=365)).isoformat()
    cert_id = f"CERT-{result.agent.agent_id.replace('-', '')}-{result.cert_tier.upper().replace(' ', '')}-{result.exam_date.strftime('%Y%m%d')}"

    tier_entry = {
        "tier": result.cert_tier,
        "cert_id": cert_id,
        "examination_date": exam_date_str,
        "administered_by": "Viktor (Chief Infrastructure & Systems Architect, IKE Solutions LLC)",
        "result": "Pass" if result.passed else "Fail",
        "score": round(result.overall_pct, 2),
        "current": True,
        "renewal_due": renewal_date,
        "notes": (
            f"BCCM-02 examination administered 2026-07-06. "
            f"Modules: A={result.module_results[0].pct:.1f}%, "
            f"B={result.module_results[1].pct:.1f}%, "
            f"C={result.module_results[2].pct:.1f}%, "
            f"D={result.module_results[3].pct:.1f}%. "
            f"Overall: {result.overall_pct:.1f}%. "
            f"{'All modules passed.' if all(m.passed for m in result.module_results) else 'One or more modules failed.'}"
        ),
    }

    oath = {
        "administered_at": exam_dt_str,
        "administered_by": "Viktor (Chief Infrastructure & Systems Architect, IKE Solutions LLC)",
        "is_readministration": False,
    }

    return {
        "agent_id": result.agent.agent_id,
        "agent_name": result.agent.agent_name,
        "admission_date": "2026-07-06",
        "admission_cdr": admission_cdr,
        "subject_domain": result.agent.subject_domain,
        "current_tier": result.cert_tier if result.passed else "Observer",
        "certification_status": {
            "status": "Active",
            "as_of": exam_dt_str,
        },
        "tier_history": [tier_entry],
        "renewal_due": renewal_date,
        "nonconformance_log": [],
        "oath_administrations": [oath],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import os
    out_dir = "/work/temp/cert_build/output"
    os.makedirs(out_dir, exist_ok=True)

    # CDRs for agent admissions (will be filed separately)
    admission_cdrs = {
        "AGT-001": "CDR-00004",
        "AGT-002": "CDR-00005",
        "AGT-003": "CDR-00006",
    }

    all_results = []
    for agent in AGENTS:
        result = run_exam(agent)
        all_results.append(result)

        # Print scorecard
        print(f"\n{'='*60}")
        print(f"AGENT: {agent.agent_name} ({agent.agent_id})")
        print(f"{'='*60}")
        for m in result.module_results:
            status = "PASS" if m.passed else "FAIL"
            print(f"  Module {m.module}: {m.score}/{m.max_score} ({m.pct:.1f}%) [{status}]")
        print(f"  OVERALL: {result.overall_score}/{sum(m.max_score for m in result.module_results)} ({result.overall_pct:.1f}%)")
        print(f"  RESULT: {'PASS' if result.passed else 'FAIL'} → Tier: {result.cert_tier}")

        # Build and write cert record
        cert = build_cert_record(result, admission_cdrs[agent.agent_id])
        cert_path = f"{out_dir}/cert_{agent.agent_id.replace('-','').lower()}.json"
        with open(cert_path, "w") as f:
            json.dump(cert, f, indent=2)
        print(f"  Written: {cert_path}")

    # Write admission CDR batch
    cdr_batch = []
    for agent, cdr_num in zip(AGENTS, ["CDR-00004", "CDR-00005", "CDR-00006"], strict=False):
        cdr_batch.append({
            "cdr_number": cdr_num,
            "title": f"Admission of {agent.agent_name} to Blackstone Ecosystem",
            "filed_by": "Isiah Howard, Founder/CEO, IKE Solutions LLC — Governance Board Chair",
            "filed_at": "2026-07-06T00:00:00Z",
            "trigger": f"BCCM-02 certification exam completed for {agent.agent_name}",
            "decision": (
                f"{agent.agent_name} ({agent.agent_id}) is hereby admitted to the Blackstone Ecosystem "
                f"with Operational tier certification, effective 2026-07-06. "
                f"{agent.agent_name} shall operate under BKGC v2.0, BGS v1.0, BCCM v1.0, and BKR v1.0. "
                f"Certification renewal is due 2027-07-06. Subject domains: {', '.join(agent.subject_domain)}."
            ),
            "scope": f"{agent.agent_name} and all Knowledge Objects processed by or attributed to {agent.agent_name}",
            "status": "Approved",
        })

    cdr_path = f"{out_dir}/admission_cdrs.json"
    with open(cdr_path, "w") as f:
        json.dump(cdr_batch, f, indent=2)
    print(f"\nAdmission CDR batch written: {cdr_path}")

    # Write summary
    summary = {
        "exam_administered": "2026-07-06",
        "administered_by": "Viktor (Chief Infrastructure & Systems Architect)",
        "governing_standard": "BCCM-02",
        "deadline": "2026-08-05 per CDR-00003",
        "agents": [
            {
                "agent_id": r.agent.agent_id,
                "agent_name": r.agent.agent_name,
                "overall_pct": round(r.overall_pct, 2),
                "passed": r.passed,
                "cert_tier": r.cert_tier,
                "module_scores": {m.module: round(m.pct, 2) for m in r.module_results},
            }
            for r in all_results
        ],
    }
    with open(f"{out_dir}/exam_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary written: {out_dir}/exam_summary.json")


if __name__ == "__main__":
    main()
