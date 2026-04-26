"""
cookbook.py — SintraPrime-Unified Interactive Cookbook
25+ real-world scenarios with runnable Python code examples.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# CookbookScenario dataclass
# ---------------------------------------------------------------------------

@dataclass
class CookbookScenario:
    id: str
    title: str
    description: str
    code: str
    expected_output: str
    tags: list[str] = field(default_factory=list)
    difficulty: str = "beginner"  # beginner | intermediate | advanced


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------

SCENARIOS: list[CookbookScenario] = []


def register(scenario: CookbookScenario) -> CookbookScenario:
    SCENARIOS.append(scenario)
    return scenario


# ---------------------------------------------------------------------------
# Scenario 1: Create a Living Trust
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="trust-001",
    title="Help me create a living trust",
    description=(
        "Full end-to-end workflow: gather grantor info, add assets, add "
        "beneficiaries, generate the trust document, and fund it."
    ),
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

# Step 1: Create the trust
trust_payload = {
    "grantor_name": "John Smith",
    "co_grantor_name": "Jane Smith",
    "state": "CA",
    "trust_name": "The Smith Family Living Trust",
    "successor_trustee": "Robert Smith",
    "beneficiaries": [
        {"name": "Alice Smith", "relationship": "daughter", "share_percent": 50},
        {"name": "Bob Smith", "relationship": "son", "share_percent": 50},
    ],
}
resp = requests.post(f"{BASE_URL}/trust/living-trust/create", json=trust_payload, headers=HEADERS)
trust = resp.json()
trust_id = trust["trust_id"]
print(f"Trust created: {trust_id} — status: {trust['status']}")

# Step 2: Add primary residence asset
asset_payload = {
    "description": "Primary Residence - 123 Main St, Sacramento CA",
    "asset_type": "real_estate",
    "value": 850000,
}
resp = requests.post(f"{BASE_URL}/trust/{trust_id}/assets", json=asset_payload, headers=HEADERS)
asset = resp.json()
print(f"Asset added: {asset['asset_id']} — transfer status: {asset['transfer_status']}")

# Step 3: Add investment account
investment = {
    "description": "Fidelity Brokerage #****1234",
    "asset_type": "investment",
    "value": 320000,
}
requests.post(f"{BASE_URL}/trust/{trust_id}/assets", json=investment, headers=HEADERS)

# Step 4: Verify assets
resp = requests.get(f"{BASE_URL}/trust/{trust_id}/assets", headers=HEADERS)
data = resp.json()
print(f"Total trust assets: ${data['total_value']:,.2f}")
print(f"Number of assets: {len(data['assets'])}")
''',
    expected_output='''Trust created: trust_abc123 — status: draft
Asset added: asset_xyz456 — transfer status: pending
Total trust assets: $1,170,000.00
Number of assets: 2''',
    tags=["trust", "estate-planning", "legal"],
    difficulty="beginner",
))


# ---------------------------------------------------------------------------
# Scenario 2: Analyze Credit Report
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="banking-001",
    title="Analyze my credit report",
    description=(
        "Pull credit report via Plaid, run AI analysis to identify "
        "negative items, get dispute letter templates, and improvement tips."
    ),
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

# Step 1: Create Plaid link token
link_resp = requests.post(
    f"{BASE_URL}/banking/plaid/link",
    json={"user_id": "user_123", "products": ["credit_details", "liabilities"]},
    headers=HEADERS,
)
link_token = link_resp.json()["link_token"]
print(f"Plaid link token: {link_token[:30]}...")

# Step 2: (After user completes Plaid Link flow, exchange for access token)
# In a real app this step happens client-side then you receive the public_token
# Simulating with mock credit report data here:
credit_report_data = {
    "score": 620,
    "accounts": [
        {"creditor": "CapitalOne", "type": "credit_card", "balance": 4200, "limit": 5000, "status": "current"},
        {"creditor": "MedStar Health", "type": "collection", "balance": 890, "status": "collection"},
        {"creditor": "Chase Auto", "type": "auto_loan", "balance": 12000, "status": "30_days_late"},
    ],
}

# Step 3: Run AI credit analysis
analysis_resp = requests.post(
    f"{BASE_URL}/banking/credit-report/analyze",
    json={"report_data": credit_report_data, "dispute_items": ["MedStar Health collection"]},
    headers=HEADERS,
)
analysis = analysis_resp.json()
print(f"Credit Score: {analysis['score']}")
print(f"Negative items found: {len(analysis['negative_items'])}")
print("\\nImprovement Tips:")
for tip in analysis["improvement_tips"]:
    print(f"  • {tip}")
print("\\nDispute Recommendations:")
for rec in analysis["dispute_recommendations"]:
    print(f"  ✓ {rec}")
''',
    expected_output='''Plaid link token: link-sandbox-af1a37b...
Credit Score: 620
Negative items found: 2

Improvement Tips:
  • Pay down CapitalOne to below 30% utilization ($1,500)
  • Dispute MedStar Health collection — may be time-barred
  • Set up autopay on Chase Auto loan immediately

Dispute Recommendations:
  ✓ Send FCRA Section 609 dispute letter to Equifax, Experian, TransUnion
  ✓ Request debt validation letter from MedStar Health collection agency''',
    tags=["banking", "credit", "plaid", "financial"],
    difficulty="intermediate",
))


# ---------------------------------------------------------------------------
# Scenario 3: Research Case Law for Landlord-Tenant Dispute
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="legal-001",
    title="Research case law for landlord-tenant dispute",
    description=(
        "Search California case law for security deposit disputes, "
        "filter by court level, and get a summary of key rulings."
    ),
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN"}

# Search case law
resp = requests.get(
    f"{BASE_URL}/legal/case-law/search",
    params={
        "query": "landlord tenant security deposit wrongful withholding",
        "jurisdiction": "CA",
        "court_level": "appellate",
        "date_from": "2018-01-01",
        "per_page": 5,
    },
    headers=HEADERS,
)
results = resp.json()
print(f"Found {results['pagination']['total']} relevant cases\\n")

for case in results["cases"]:
    print(f"📋 {case['title']} ({case['date']})")
    print(f"   Court: {case['court']}")
    print(f"   Relevance: {case['relevance_score']:.0%}")
    print(f"   Summary: {case['summary'][:100]}...")
    print()

# Get full text of most relevant case
top_case_id = results["cases"][0]["id"]
full_case = requests.get(f"{BASE_URL}/legal/case-law/{top_case_id}", headers=HEADERS).json()
print(f"\\nKey citations in top case:")
for citation in full_case.get("citations", [])[:3]:
    print(f"  → {citation}")
''',
    expected_output='''Found 23 relevant cases

📋 Green v. Superior Court (2022-03-14)
   Court: California Court of Appeal, 1st District
   Relevance: 97%
   Summary: Landlord must return security deposit within 21 days. Failure creates...

📋 Granberry v. Islay Investments (2021-07-22)
   Court: California Court of Appeal, 2nd District
   Relevance: 94%
   Summary: Tenant entitled to two times wrongfully withheld deposit plus attorney fees...

Key citations in top case:
  → Cal. Civ. Code § 1950.5
  → Green v. Superior Court (1974) 10 Cal.3d 616
  → Granberry v. Islay Investments (1995) 9 Cal.4th 738''',
    tags=["legal", "case-law", "landlord-tenant", "research"],
    difficulty="beginner",
))


# ---------------------------------------------------------------------------
# Scenario 4: Set Up Automated Court Deadline Monitoring
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="legal-002",
    title="Set up automated court deadline monitoring",
    description=(
        "Create a deadline monitor for a civil case with multiple deadlines "
        "and configure email alerts 7 and 1 day before each deadline."
    ),
    code='''
import requests
from datetime import date, timedelta

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

today = date.today()

monitor_payload = {
    "case_number": "23STCV01234",
    "court": "Los Angeles Superior Court",
    "deadlines": [
        {
            "name": "Response to Complaint",
            "date": str(today + timedelta(days=30)),
            "alert_days_before": 7,
        },
        {
            "name": "Discovery Cutoff",
            "date": str(today + timedelta(days=90)),
            "alert_days_before": 14,
        },
        {
            "name": "Motion for Summary Judgment",
            "date": str(today + timedelta(days=120)),
            "alert_days_before": 21,
        },
        {
            "name": "Trial Date",
            "date": str(today + timedelta(days=180)),
            "alert_days_before": 30,
        },
    ],
    "notification_email": "attorney@lawfirm.com",
}

resp = requests.post(
    f"{BASE_URL}/legal/deadline/monitor",
    json=monitor_payload,
    headers=HEADERS,
)
monitor = resp.json()
print(f"✅ Deadline monitor created: {monitor['monitor_id']}")
print(f"   Case: {monitor['case_number']}")
print(f"   Status: {monitor['status']}")
print(f"   Next deadline: {monitor['next_deadline']}")
print(f"\\n📧 Email alerts configured for attorney@lawfirm.com")
''',
    expected_output='''✅ Deadline monitor created: mon_abc789
   Case: 23STCV01234
   Status: active
   Next deadline: 2026-05-26

📧 Email alerts configured for attorney@lawfirm.com''',
    tags=["legal", "deadlines", "court", "monitoring", "automation"],
    difficulty="beginner",
))


# ---------------------------------------------------------------------------
# Scenario 5: Create Business Formation Checklist
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="trust-002",
    title="Create a business formation checklist",
    description=(
        "Generate a step-by-step LLC formation checklist for California "
        "with estimated costs and required forms at each step."
    ),
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

payload = {
    "business_type": "LLC",
    "state": "CA",
    "business_name": "Acme Tech Solutions LLC",
    "owners": [
        {"name": "Alice Johnson", "ownership_percent": 60},
        {"name": "Bob Chen", "ownership_percent": 40},
    ],
}

resp = requests.post(f"{BASE_URL}/trust/business-formation/checklist", json=payload, headers=HEADERS)
checklist = resp.json()

print(f"📋 {checklist['business_type']} Formation Checklist — {checklist['state']}")
print(f"   Estimated time: {checklist['estimated_time_days']} days")
print(f"   Estimated cost: ${checklist['total_estimated_cost']:,.2f}\\n")

for step in checklist["steps"]:
    forms = ", ".join(step.get("required_forms", [])) or "None"
    print(f"Step {step['step']}: {step['title']}")
    print(f"  {step['description']}")
    print(f"  Forms: {forms}")
    print(f"  Cost: ${step.get('estimated_cost', 0):,.2f}\\n")
''',
    expected_output='''📋 LLC Formation Checklist — CA
   Estimated time: 14 days
   Estimated cost: $870.00

Step 1: Name Availability Search
  Check that "Acme Tech Solutions LLC" is available in CA
  Forms: None
  Cost: $0.00

Step 2: File Articles of Organization
  Submit Form LLC-1 to CA Secretary of State
  Forms: LLC-1
  Cost: $70.00

Step 3: Publish Formation Notice
  Publish in approved newspaper for 4 consecutive weeks (some counties)
  Forms: None
  Cost: $300.00

Step 4: Create Operating Agreement
  Draft member agreement covering ownership, voting, distributions
  Forms: None
  Cost: $0.00

Step 5: Obtain EIN from IRS
  Apply online at IRS.gov (free, immediate)
  Forms: SS-4
  Cost: $0.00

Step 6: Register with CA FTB
  Pay $800 annual minimum franchise tax
  Forms: 3522
  Cost: $800.00''',
    tags=["business", "formation", "LLC", "legal", "trust"],
    difficulty="beginner",
))


# ---------------------------------------------------------------------------
# Scenario 6: Negotiate Debt Settlement
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="banking-002",
    title="Negotiate debt settlement",
    description=(
        "Analyze multiple debts, get optimal negotiation strategy, "
        "and generate sample settlement letters for each creditor."
    ),
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

payload = {
    "debts": [
        {"creditor": "Chase Bank", "balance": 8500, "interest_rate": 24.99, "months_delinquent": 6},
        {"creditor": "Midland Credit", "balance": 3200, "interest_rate": 0, "months_delinquent": 18},
        {"creditor": "Portfolio Recovery", "balance": 1100, "interest_rate": 0, "months_delinquent": 30},
    ],
    "available_lump_sum": 5000,
    "monthly_budget": 300,
}

resp = requests.post(f"{BASE_URL}/banking/debt/negotiate", json=payload, headers=HEADERS)
result = resp.json()

print(f"🎯 Recommended Strategy: {result['strategy'].upper()}")
print(f"💰 Estimated savings: ${result['estimated_savings']:,.2f}\\n")
print("Settlement Offers:")
for offer in result["settlement_offers"]:
    print(f"  {offer['creditor']}: Offer ${offer['offer_amount']:,.2f} "
          f"(was ${offer['original_balance']:,.2f} — {offer['savings_pct']:.0f}% savings)")
print("\\n📝 Sample Letters Generated:")
for letter_name in result["sample_letters"]:
    print(f"  • {letter_name}")
''',
    expected_output='''🎯 Recommended Strategy: SETTLEMENT
💰 Estimated savings: $7,350.00

Settlement Offers:
  Chase Bank: Offer $3,000 (was $8,500 — 65% savings)
  Midland Credit: Offer $1,200 (was $3,200 — 63% savings)
  Portfolio Recovery: Offer $350 (was $1,100 — 68% savings)

📝 Sample Letters Generated:
  • Chase_Bank_Settlement_Offer.txt
  • Midland_Credit_Settlement_Offer.txt
  • Portfolio_Recovery_Settlement_Offer.txt''',
    tags=["banking", "debt", "negotiation", "financial"],
    difficulty="intermediate",
))


# ---------------------------------------------------------------------------
# Scenario 7: Review a Contract for Red Flags
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="legal-003",
    title="Review a contract for red flags",
    description=(
        "Submit a lease agreement for AI analysis, get severity-ranked "
        "red flags, missing clauses, and risk score."
    ),
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

lease_text = """
LEASE AGREEMENT

Landlord may enter premises at any time without notice for any reason.
Tenant waives all rights to habitability warranty.
Landlord may terminate lease with 3-day written notice for any reason.
Security deposit of $3,000 non-refundable under any circumstances.
Tenant responsible for all repairs exceeding $50 regardless of cause.
Late fee of $200 per day after 1st of month.
Tenant waives right to jury trial for all disputes.
"""

resp = requests.post(
    f"{BASE_URL}/legal/contract/analyze",
    json={"text": lease_text, "contract_type": "lease", "party_role": "tenant"},
    headers=HEADERS,
)
analysis = resp.json()

severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
print(f"⚠️  Contract Risk Score: {analysis['risk_score']:.0%}\\n")
print("RED FLAGS:")
for flag in analysis["red_flags"]:
    emoji = severity_emoji.get(flag["severity"], "⚪")
    print(f"  {emoji} [{flag['severity'].upper()}] {flag['clause']}")
    print(f"       → {flag['explanation']}\\n")

print("MISSING CLAUSES:")
for clause in analysis["missing_clauses"]:
    print(f"  ❌ {clause}")

print("\\nRECOMMENDATIONS:")
for rec in analysis["recommendations"]:
    print(f"  ✓ {rec}")
''',
    expected_output='''⚠️  Contract Risk Score: 95%

RED FLAGS:
  🔴 [HIGH] "non-refundable security deposit"
       → CA Civil Code §1950.5 prohibits non-refundable security deposits

  🔴 [HIGH] "enter premises at any time without notice"
       → CA law requires 24-hour written notice (Civil Code §1954)

  🔴 [HIGH] "waives right to jury trial"
       → Jury trial waiver clauses are generally unenforceable in CA

  🟡 [MEDIUM] "$200 late fee per day"
       → Late fees must be reasonable; $200/day likely constitutes a penalty

MISSING CLAUSES:
  ❌ Lead paint disclosure (required for pre-1978 buildings)
  ❌ Mold disclosure
  ❌ Move-in inspection checklist

RECOMMENDATIONS:
  ✓ Negotiate removal of all HIGH severity clauses before signing
  ✓ Request CA standard lease form (CAR form LR)
  ✓ Consult with tenant rights organization before signing''',
    tags=["legal", "contract", "lease", "review"],
    difficulty="beginner",
))


# ---------------------------------------------------------------------------
# Scenario 8: File Federal Agency Complaint
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="legal-004",
    title="File federal agency complaint",
    description=(
        "Submit a CFPB complaint about a predatory lending practice "
        "with supporting evidence and track the complaint status."
    ),
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

complaint_payload = {
    "agency": "CFPB",
    "description": (
        "Lender charged undisclosed origination fees of $2,500 not shown on "
        "Loan Estimate. Changed APR from 6.5% to 8.9% at closing without "
        "providing revised disclosure 3 business days before closing as required "
        "under TRID regulations. Refused to delay closing to allow review."
    ),
    "complainant_name": "Maria Rodriguez",
    "respondent_name": "FastClose Mortgage LLC",
    "date_of_incident": "2026-04-01",
    "evidence_urls": [
        "https://storage.example.com/loan-estimate-original.pdf",
        "https://storage.example.com/closing-disclosure-altered.pdf",
        "https://storage.example.com/email-thread.pdf",
    ],
}

resp = requests.post(f"{BASE_URL}/legal/complaint/file", json=complaint_payload, headers=HEADERS)
result = resp.json()

print(f"✅ Complaint filed successfully!")
print(f"   Complaint ID: {result['complaint_id']}")
print(f"   Agency: {result['agency']}")
print(f"   Confirmation #: {result['confirmation_number']}")
print(f"   Status: {result['status']}")
print(f"   Expected response within: {result['estimated_response_days']} days")
print(f"\\n📧 Confirmation sent to complainant email on file.")
''',
    expected_output='''✅ Complaint filed successfully!
   Complaint ID: cfpb_2026_00445_abc
   Agency: CFPB
   Confirmation #: CFPB-2026-0445789
   Status: submitted
   Expected response within: 60 days

📧 Confirmation sent to complainant email on file.''',
    tags=["legal", "complaint", "CFPB", "regulatory", "federal"],
    difficulty="intermediate",
))


# ---------------------------------------------------------------------------
# Scenario 9: Predict Case Outcome Before Filing
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="legal-005",
    title="Predict case outcome before filing",
    description=(
        "Use AI to predict probability of winning a wage theft case "
        "based on facts and similar precedents."
    ),
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

payload = {
    "case_type": "wage_theft",
    "facts_summary": (
        "Employer misclassified plaintiff as independent contractor for 2 years "
        "despite controlling schedule, providing equipment, and forbidding outside "
        "work. Plaintiff worked 55 hours/week, received no overtime, and was denied "
        "meal/rest breaks. Employer had 47 other workers in same situation. "
        "Written texts show employer knew classification was wrong."
    ),
    "jurisdiction": "CA",
    "similar_cases": ["Dynamex Operations West v. Superior Court", "Garcia v. Border Transportation"],
}

resp = requests.post(f"{BASE_URL}/legal/predict/outcome", json=payload, headers=HEADERS)
prediction = resp.json()

print(f"📊 Case Outcome Prediction")
print(f"   Win Probability: {prediction['win_probability']:.0%}")
print(f"   Confidence: {prediction['confidence']:.0%}\\n")
print("Key Factors:")
for factor in prediction["key_factors"]:
    print(f"  + {factor}")
print(f"\\nRecommended Strategy: {prediction['recommended_strategy']}")
print("\\nSimilar Cases Outcome:")
for case in prediction["similar_cases_outcome"]:
    print(f"  → {case['title']}: {case['outcome']} (${case['award']:,})")
''',
    expected_output='''📊 Case Outcome Prediction
   Win Probability: 89%
   Confidence: 82%

Key Factors:
  + ABC test under Dynamex strongly favors employee classification
  + Written evidence of employer intent highly valuable
  + Class action potential with 47 similarly situated workers
  + CA PAGA claims create significant additional liability for employer

Recommended Strategy: File PAGA representative action + individual wage claim. Demand mediation first given high win probability.

Similar Cases Outcome:
  → Garcia v. Border Transportation: Plaintiff won ($2,100,000)
  → Olson v. Lyft Inc.: Settled ($27,000,000 class)''',
    tags=["legal", "prediction", "AI", "wage-theft", "employment"],
    difficulty="advanced",
))


# ---------------------------------------------------------------------------
# Scenario 10: Set Up Multi-Agent Swarm for Complex Litigation
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="mcp-001",
    title="Set up multi-agent swarm for complex litigation",
    description=(
        "Launch a coordinated swarm of specialized AI agents to handle "
        "all aspects of a complex multi-party litigation."
    ),
    code='''
import requests
import time

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

# Launch swarm
swarm_payload = {
    "task": (
        "Complex multi-party IP infringement litigation: research prior art, "
        "analyze patents, draft complaint, identify expert witnesses, "
        "prepare discovery requests, and predict defendant litigation strategy."
    ),
    "num_agents": 6,
    "agent_types": [
        "patent_researcher",
        "case_law_analyst",
        "document_drafter",
        "discovery_specialist",
        "expert_identifier",
        "strategy_advisor",
    ],
    "coordination_strategy": "hierarchical",
}

resp = requests.post(f"{BASE_URL}/mcp/agents/swarm", json=swarm_payload, headers=HEADERS)
swarm = resp.json()

print(f"🤖 Multi-Agent Swarm Launched!")
print(f"   Swarm ID: {swarm['swarm_id']}")
print(f"   Status: {swarm['status']}")
print(f"   Agents: {len(swarm['agents'])}")
print(f"   Estimated completion: {swarm['estimated_completion_seconds']}s\\n")
print("Agent Roster:")
for agent in swarm["agents"]:
    print(f"  [{agent['type']}] {agent['name']} — role: {agent['role']}")

# Check status
time.sleep(2)
print(f"\\n✅ Swarm running. Poll /mcp/agents/swarm/{swarm['swarm_id']}/status for updates.")
''',
    expected_output='''🤖 Multi-Agent Swarm Launched!
   Swarm ID: swarm_lit_2026_001
   Status: running
   Agents: 6
   Estimated completion: 180s

Agent Roster:
  [patent_researcher] Agent-PR-01 — role: prior art research
  [case_law_analyst] Agent-CL-02 — role: precedent analysis
  [document_drafter] Agent-DD-03 — role: complaint drafting
  [discovery_specialist] Agent-DS-04 — role: discovery requests
  [expert_identifier] Agent-EI-05 — role: expert witness search
  [strategy_advisor] Agent-SA-06 — role: litigation strategy

✅ Swarm running. Poll /mcp/agents/swarm/swarm_lit_2026_001/status for updates.''',
    tags=["mcp", "swarm", "agents", "litigation", "advanced"],
    difficulty="advanced",
))


# ---------------------------------------------------------------------------
# Scenario 11: Run Compliance Check (GDPR)
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="compliance-001",
    title="Run GDPR compliance audit",
    description="Check a web application's data practices against GDPR requirements.",
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

payload = {
    "framework": "GDPR",
    "data": {
        "data_collected": ["email", "name", "ip_address", "behavioral_tracking", "location"],
        "retention_days": 730,
        "consent_mechanism": "pre_checked_box",
        "privacy_policy": True,
        "dpo_appointed": False,
        "breach_response_plan": False,
        "data_transfers": ["US", "India"],
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "right_to_deletion": True,
        "right_to_portability": False,
    },
    "scope": ["consent", "data_retention", "cross_border_transfer", "dpo", "breach_response"],
}

resp = requests.post(f"{BASE_URL}/compliance/check", json=payload, headers=HEADERS)
result = resp.json()

severity_icon = {"critical": "🚨", "high": "🔴", "medium": "🟡", "low": "🟢"}
print(f"GDPR Compliance Score: {result['score']:.0%} — {result['status'].upper()}")
print(f"\\nViolations ({len(result['violations'])}):")
for v in result["violations"]:
    icon = severity_icon.get(v["severity"], "⚪")
    print(f"  {icon} [{v['severity'].upper()}] {v['rule']}")
    print(f"     {v['description']}")
print("\\nTop Recommendations:")
for rec in result["recommendations"][:5]:
    print(f"  ✓ {rec}")
''',
    expected_output='''GDPR Compliance Score: 42% — NON_COMPLIANT

Violations (4):
  🚨 [CRITICAL] Pre-checked consent boxes
     Art. 7 requires freely given, specific, informed, unambiguous consent
  🔴 [HIGH] No Data Protection Officer appointed
     Art. 37 requires DPO for large-scale behavioral tracking
  🔴 [HIGH] US/India transfers without adequacy decision
     Art. 46 requires SCCs or other safeguards for non-EEA transfers
  🟡 [MEDIUM] No documented breach response plan
     Art. 33/34 requires 72-hour notification capability

Top Recommendations:
  ✓ Replace pre-checked boxes with explicit opt-in consent
  ✓ Appoint or contract a DPO immediately
  ✓ Execute Standard Contractual Clauses with US/India processors
  ✓ Create and test data breach response procedure
  ✓ Implement data portability export feature''',
    tags=["compliance", "GDPR", "privacy", "regulatory"],
    difficulty="intermediate",
))


# ---------------------------------------------------------------------------
# Scenario 12: Execute MCP Tool
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="mcp-002",
    title="Execute MCP legal research tool",
    description="Use the MCP server to run a specialized legal research tool with arguments.",
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

# First, list available tools
tools_resp = requests.get(f"{BASE_URL}/mcp/tools", headers=HEADERS)
tools = tools_resp.json()["tools"]
print(f"Available MCP tools: {len(tools)}")
for tool in tools[:5]:
    print(f"  • {tool['name']}: {tool['description']}")

# Execute a specific tool
exec_resp = requests.post(
    f"{BASE_URL}/mcp/execute",
    json={
        "tool_name": "legal_statute_lookup",
        "arguments": {"statute": "Cal. Civ. Code § 1950.5", "include_history": True},
        "timeout_seconds": 15,
    },
    headers=HEADERS,
)
result = exec_resp.json()
print(f"\\nTool: {result['tool_name']}")
print(f"Status: {result['status']}")
print(f"Execution time: {result['execution_ms']}ms")
print(f"Result: {result['result']['text'][:200]}...")
''',
    expected_output='''Available MCP tools: 47
  • legal_statute_lookup: Look up current text and history of any statute
  • case_law_search: Full-text search across 50M+ legal cases
  • court_filing_check: Check filing requirements for any US court
  • deadline_calculator: Calculate litigation deadlines with jurisdiction rules
  • document_analyzer: Extract key terms and clauses from legal documents

Tool: legal_statute_lookup
Status: success
Execution time: 342ms
Result: Cal. Civ. Code § 1950.5 — Security Deposits. (a) This section applies to security for a rental agreement for residential property...''',
    tags=["mcp", "tools", "legal", "research"],
    difficulty="beginner",
))


# ---------------------------------------------------------------------------
# Scenario 13: Emotional Intelligence — Adapt Stressful Communication
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="ei-001",
    title="Adapt stressful client communication",
    description=(
        "Detect a client's emotional state from their message and "
        "generate an empathetic, adapted response."
    ),
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

client_message = """
I am FURIOUS. It has been THREE MONTHS and nothing has happened with my case.
Every time I call I get put on hold or transferred. I paid $5,000 upfront and
you people have done NOTHING. I want answers NOW or I am reporting you to the
bar association and disputing the credit card charge. This is UNACCEPTABLE.
"""

# Step 1: Analyze sentiment
sentiment_resp = requests.post(
    f"{BASE_URL}/ei/sentiment/analyze",
    json={"text": client_message, "context": "attorney_client"},
    headers=HEADERS,
)
sentiment = sentiment_resp.json()
print(f"Detected emotions: {sentiment['primary_emotion']}")
print(f"Stress level: {sentiment['stress_level']:.0%}")
print(f"Recommended response tone: {sentiment['recommended_tone']}\\n")

# Step 2: Generate adapted response
adapt_resp = requests.post(
    f"{BASE_URL}/ei/communication/adapt",
    json={
        "message": "We are working on your case and will provide an update shortly.",
        "target_sentiment": "calm_and_reassured",
        "audience_type": "frustrated_client",
    },
    headers=HEADERS,
)
adapted = adapt_resp.json()
print(f"Original: {adapted['changes_made'][0]['original']}")
print(f"\\nAdapted Response:")
print(adapted["adapted_message"])
''',
    expected_output='''Detected emotions: anger
Stress level: 94%
Recommended response tone: deeply_empathetic_and_accountable

Original: We are working on your case and will provide an update shortly.

Adapted Response:
I hear you, and I want to sincerely apologize for the frustration and silence you have experienced. Three months without clear communication is unacceptable, and you deserve better. I am personally reviewing your file right now and will call you within the next 2 hours with a full status update and a concrete action plan. Thank you for not giving up on us — we will make this right.''',
    tags=["emotional-intelligence", "communication", "client", "empathy"],
    difficulty="intermediate",
))


# ---------------------------------------------------------------------------
# Scenario 14: Build and Deploy a Legal Intake App
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="appbuilder-001",
    title="Build a legal intake app",
    description="Generate a legal intake form web app from a spec and deploy to staging.",
    code='''
import requests
import time

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

# Build the app
build_resp = requests.post(
    f"{BASE_URL}/appbuilder/apps",
    json={
        "name": "Legal Intake Portal",
        "tech_stack": "react",
        "spec": {
            "title": "Free Legal Consultation Intake",
            "fields": [
                {"name": "full_name", "type": "text", "required": True},
                {"name": "email", "type": "email", "required": True},
                {"name": "phone", "type": "tel"},
                {"name": "case_type", "type": "select", "options": ["landlord_tenant", "employment", "family", "criminal", "civil"]},
                {"name": "description", "type": "textarea", "required": True},
                {"name": "income_level", "type": "select", "options": ["under_25k", "25k_50k", "50k_100k", "over_100k"]},
            ],
            "on_submit": "route_to_attorney_queue",
        },
    },
    headers=HEADERS,
)
job = build_resp.json()
print(f"Build job: {job['job_id']} — App ID: {job['app_id']}")
print(f"Estimated build time: {job['estimated_seconds']}s")

# Wait and deploy
time.sleep(3)
deploy_resp = requests.post(
    f"{BASE_URL}/appbuilder/apps/{job['app_id']}/deploy",
    json={"environment": "staging"},
    headers=HEADERS,
)
deploy = deploy_resp.json()
print(f"\\n✅ Deployed to {deploy['environment']}: {deploy['url']}")
print(f"Deployed at: {deploy['deployed_at']}")
''',
    expected_output='''Build job: build_789xyz — App ID: app_intake_001
Estimated build time: 45s

✅ Deployed to staging: https://staging-apps.sintraprime.io/legal-intake-001
Deployed at: 2026-04-26T09:30:00Z''',
    tags=["app-builder", "deployment", "legal", "intake"],
    difficulty="intermediate",
))


# ---------------------------------------------------------------------------
# Scenario 15: Monitor System Observability
# ---------------------------------------------------------------------------

register(CookbookScenario(
    id="obs-001",
    title="Monitor system observability dashboard",
    description="Check system health, pull metrics for the legal API, and inspect traces.",
    code='''
import requests

BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN"}

# Health check
health = requests.get(f"{BASE_URL}/observability/health", headers=HEADERS).json()
status_icon = {"ok": "✅", "degraded": "⚠️", "down": "❌"}.get(health["status"], "❓")
print(f"{status_icon} System Health: {health['status'].upper()}")
print(f"   Version: {health['version']} | Uptime: {health['uptime_seconds'] // 3600}h\\n")

# Pull metrics
metrics_resp = requests.get(
    f"{BASE_URL}/observability/metrics",
    params={"service": "legal-intelligence-api"},
    headers=HEADERS,
)
metrics = metrics_resp.json()
print(f"📊 Metrics for: {metrics['service']}")
for m in metrics["metrics"]:
    print(f"   {m['name']}: {m['value']:.2f} {m['unit']}")

# Inspect a trace
trace_resp = requests.get(
    f"{BASE_URL}/observability/traces",
    params={"trace_id": "abc123def456"},
    headers=HEADERS,
)
trace = trace_resp.json()
total_ms = sum(s["duration_ms"] for s in trace["spans"])
print(f"\\n🔍 Trace {trace['trace_id']}: {len(trace['spans'])} spans | Total: {total_ms}ms")
for span in trace["spans"]:
    status_icon = "✅" if span["status"] == "ok" else "❌"
    print(f"   {status_icon} {span['operation']}: {span['duration_ms']}ms")
''',
    expected_output='''✅ System Health: OK
   Version: 2.0.0 | Uptime: 24h

📊 Metrics for: legal-intelligence-api
   requests_per_second: 127.50 req/s
   p99_latency_ms: 342.00 ms
   error_rate: 0.12 %
   cache_hit_rate: 87.40 %

🔍 Trace abc123def456: 4 spans | Total: 456ms
   ✅ http_request: 2ms
   ✅ auth_check: 45ms
   ✅ case_law_search: 389ms
   ✅ response_format: 20ms''',
    tags=["observability", "monitoring", "metrics", "tracing"],
    difficulty="beginner",
))


# ---------------------------------------------------------------------------
# Scenarios 16–25: Additional Scenarios
# ---------------------------------------------------------------------------

ADDITIONAL_SCENARIOS = [
    CookbookScenario(
        id="legal-006",
        title="Eviction defense strategy",
        description="Research eviction defense options and generate a response to unlawful detainer.",
        code='''
import requests
BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

# Search eviction defense case law
results = requests.get(
    f"{BASE_URL}/legal/case-law/search",
    params={"query": "unlawful detainer affirmative defenses habitability", "jurisdiction": "CA"},
    headers=HEADERS,
).json()

print(f"Found {results['pagination']['total']} eviction defense cases")
for case in results["cases"][:3]:
    print(f"  • {case['title']} ({case['date']}): {case['summary'][:80]}...")

# Predict outcome
prediction = requests.post(
    f"{BASE_URL}/legal/predict/outcome",
    json={
        "case_type": "eviction_defense",
        "facts_summary": "Landlord failed to repair mold for 6 months. Tenant withheld rent.",
        "jurisdiction": "CA",
    },
    headers=HEADERS,
).json()
print(f"\\nDefense win probability: {prediction['win_probability']:.0%}")
print(f"Strategy: {prediction['recommended_strategy']}")
''',
        expected_output='''Found 31 eviction defense cases
  • Green v. Superior Court (2022-01-10): Implied warranty of habitability is a complete defense to...
  • Park v. Townhome (2021-05-22): Mold constitutes substandard conditions under Health & Safety Code...
  • Hicks v. Landlord LLC (2020-11-03): Repair and deduct remedy available for conditions affecting health...

Defense win probability: 73%
Strategy: Assert habitability defense and file cross-complaint for breach of warranty''',
        tags=["legal", "eviction", "defense", "landlord-tenant"],
        difficulty="intermediate",
    ),
    CookbookScenario(
        id="governance-001",
        title="Create agent governance policy",
        description="Define governance rules for AI agents and register a new compliant agent.",
        code='''
import requests
BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

# Create policy
policy = requests.post(
    f"{BASE_URL}/governance/policies",
    json={
        "name": "Legal AI Safety Policy v1",
        "description": "Rules governing legal AI agent behavior",
        "rules": [
            {"id": "R01", "name": "No unauthorized legal advice", "action": "block"},
            {"id": "R02", "name": "Require attorney review for filings", "action": "require_approval"},
            {"id": "R03", "name": "Log all case-related queries", "action": "audit_log"},
        ],
        "category": "legal_compliance",
    },
    headers=HEADERS,
).json()
print(f"Policy created: {policy['policy_id']} — {policy['name']}")

# Register agent under policy
agent = requests.post(
    f"{BASE_URL}/governance/agents/register",
    json={
        "agent_name": "LegalResearchBot-v2",
        "agent_type": "research",
        "capabilities": ["case_law_search", "document_analysis", "deadline_tracking"],
        "policy_ids": [policy["policy_id"]],
    },
    headers=HEADERS,
).json()
print(f"Agent registered: {agent['agent_id']} — Status: {agent['status']}")
''',
        expected_output='''Policy created: pol_legal_001 — Legal AI Safety Policy v1
Agent registered: agent_lrb_001 — Status: active''',
        tags=["governance", "agents", "policy", "compliance"],
        difficulty="intermediate",
    ),
    CookbookScenario(
        id="workflow-001",
        title="Create automated legal intake workflow",
        description="Build a multi-step workflow that routes legal intake forms to the right attorney.",
        code='''
import requests
BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

workflow = requests.post(
    f"{BASE_URL}/workflows",
    json={
        "name": "Legal Intake Router",
        "trigger": "intake_form_submitted",
        "steps": [
            {"id": "s1", "type": "sentiment_analysis", "tool": "ei.sentiment.analyze"},
            {"id": "s2", "type": "case_classification", "tool": "legal.classify"},
            {"id": "s3", "type": "attorney_match", "tool": "legal.match_attorney", "depends_on": ["s2"]},
            {"id": "s4", "type": "send_notification", "tool": "notify.email", "depends_on": ["s3"]},
            {"id": "s5", "type": "create_deadline_monitor", "tool": "legal.deadline.monitor", "depends_on": ["s3"]},
        ],
    },
    headers=HEADERS,
).json()
print(f"Workflow created: {workflow['workflow_id']} — {workflow['name']}")
print(f"Steps: {len(workflow['steps'])} | Trigger: {workflow['trigger']}")

# Execute with sample data
execution = requests.post(
    f"{BASE_URL}/workflows/{workflow['workflow_id']}/execute",
    json={"inputs": {"intake_id": "intake_2026_001", "case_type": "employment"}},
    headers=HEADERS,
).json()
print(f"\\nExecution started: {execution['execution_id']} — {execution['status']}")
''',
        expected_output='''Workflow created: wf_intake_router_001 — Legal Intake Router
Steps: 5 | Trigger: intake_form_submitted

Execution started: exec_abc123 — running''',
        tags=["workflow", "automation", "intake", "legal"],
        difficulty="intermediate",
    ),
    CookbookScenario(
        id="banking-003",
        title="Link bank account and categorize transactions",
        description="Use Plaid to link a bank account and automatically categorize transactions for legal billing.",
        code='''
import requests
BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

# List transactions
transactions = requests.get(
    f"{BASE_URL}/banking/transactions",
    params={"account_id": "acc_checking_001", "start_date": "2026-04-01", "end_date": "2026-04-30"},
    headers=HEADERS,
).json()

categories = {}
for txn in transactions["transactions"]:
    cat = txn["category"][0] if txn["category"] else "Uncategorized"
    categories[cat] = categories.get(cat, 0) + abs(txn["amount"])

print(f"April 2026 Transactions ({transactions['total_count']} total):")
print("\\nSpending by Category:")
for cat, total in sorted(categories.items(), key=lambda x: x[1], reverse=True):
    print(f"  {cat}: ${total:,.2f}")
''',
        expected_output='''April 2026 Transactions (47 total):

Spending by Category:
  Food and Drink: $1,234.56
  Transfer: $3,000.00
  Service: $589.99
  Travel: $1,100.00
  Shopping: $445.23''',
        tags=["banking", "plaid", "transactions", "financial"],
        difficulty="beginner",
    ),
    CookbookScenario(
        id="legal-007",
        title="Prepare interrogatories for discovery",
        description="Use MCP tools to generate discovery interrogatories for a civil case.",
        code='''
import requests
BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

result = requests.post(
    f"{BASE_URL}/mcp/execute",
    json={
        "tool_name": "discovery_generator",
        "arguments": {
            "case_type": "breach_of_contract",
            "jurisdiction": "CA",
            "party": "plaintiff",
            "num_interrogatories": 10,
        },
    },
    headers=HEADERS,
).json()

print(f"Generated {len(result['result']['interrogatories'])} interrogatories")
for i, q in enumerate(result["result"]["interrogatories"][:5], 1):
    print(f"\\nInterrogatory No. {i}:")
    print(f"  {q}")
''',
        expected_output='''Generated 10 interrogatories

Interrogatory No. 1:
  State the full legal name, address, and capacity of each person who has or may have knowledge of the facts alleged in this action.

Interrogatory No. 2:
  Identify all written contracts, amendments, or modifications between the parties related to the subject matter of this lawsuit.

Interrogatory No. 3:
  State all facts that support each affirmative defense asserted in your Answer.

Interrogatory No. 4:
  Identify all communications (email, text, letter) between the parties from January 1, 2025 to present.

Interrogatory No. 5:
  Describe in detail all damages you claim and how each amount was calculated.''',
        tags=["legal", "discovery", "mcp", "litigation"],
        difficulty="intermediate",
    ),
    CookbookScenario(
        id="compliance-002",
        title="HIPAA compliance check for health app",
        description="Run a HIPAA compliance audit on a healthcare application's data practices.",
        code='''
import requests
BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

result = requests.post(
    f"{BASE_URL}/compliance/check",
    json={
        "framework": "HIPAA",
        "data": {
            "phi_collected": True,
            "encryption_at_rest": True,
            "encryption_in_transit": True,
            "baa_signed": False,
            "access_controls": True,
            "audit_logging": True,
            "breach_notification_plan": False,
            "minimum_necessary_standard": True,
            "employee_training": False,
        },
    },
    headers=HEADERS,
).json()

print(f"HIPAA Score: {result['score']:.0%} — {result['status']}")
print(f"\\nCritical Gaps:")
for v in [x for x in result["violations"] if x["severity"] in ["critical", "high"]]:
    print(f"  ⚠️  {v['rule']}: {v['description']}")
''',
        expected_output='''HIPAA Score: 58% — PARTIAL

Critical Gaps:
  ⚠️  Missing Business Associate Agreement: All PHI processors require signed BAA
  ⚠️  No breach notification procedure: Required 60-day notification plan missing
  ⚠️  Employee training not documented: Annual HIPAA training must be documented''',
        tags=["compliance", "HIPAA", "healthcare", "privacy"],
        difficulty="intermediate",
    ),
    CookbookScenario(
        id="trust-003",
        title="Irrevocable special needs trust",
        description="Create a special needs trust to preserve government benefit eligibility.",
        code='''
import requests
BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

trust = requests.post(
    f"{BASE_URL}/trust/living-trust/create",
    json={
        "grantor_name": "Patricia Williams",
        "state": "TX",
        "trust_name": "The Williams Special Needs Trust",
        "successor_trustee": "National Special Needs Network",
        "beneficiaries": [{"name": "Michael Williams", "relationship": "son", "share_percent": 100, "condition": "special_needs_beneficiary"}],
        "assets": [{"description": "Inheritance", "asset_type": "bank_account", "value": 250000}],
    },
    headers=HEADERS,
).json()
print(f"Special Needs Trust created: {trust['trust_id']}")
print(f"Status: {trust['status']}")
print(f"Document: {trust['document_url']}")
print("\\nKey benefit: Trust assets do not count toward SSI/Medicaid asset limits")
''',
        expected_output='''Special Needs Trust created: trust_snt_2026_001
Status: draft
Document: https://docs.sintraprime.io/trust_snt_2026_001.pdf

Key benefit: Trust assets do not count toward SSI/Medicaid asset limits''',
        tags=["trust", "special-needs", "estate-planning"],
        difficulty="advanced",
    ),
    CookbookScenario(
        id="ei-002",
        title="Detect client deception risk in communications",
        description="Analyze client communications to identify inconsistencies and potential deception.",
        code='''
import requests
BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

messages = [
    "I was definitely at home all day on March 15th.",
    "I mean, I was mostly home, except for a short errand.",
    "Actually I think I had a doctor's appointment that day.",
    "I don't really remember where I was, honestly.",
]

print("Analyzing communication consistency...\\n")
for i, msg in enumerate(messages, 1):
    result = requests.post(
        f"{BASE_URL}/ei/sentiment/analyze",
        json={"text": msg, "context": "deposition_prep"},
        headers=HEADERS,
    ).json()
    print(f"Statement {i}: '{msg[:50]}...'")
    print(f"  Stress: {result['stress_level']:.0%} | Emotion: {result['primary_emotion']}")

print("\\n⚠️  Inconsistency detected: Location story changed 3 times")
print("Recommend: Prepare client with consistent, accurate timeline")
''',
        expected_output='''Analyzing communication consistency...

Statement 1: 'I was definitely at home all day on March 15th.'
  Stress: 15% | Emotion: confident
Statement 2: 'I mean, I was mostly home, except for a short errand.'
  Stress: 42% | Emotion: uncertain
Statement 3: 'Actually I think I had a doctor\'s appointment that day.'
  Stress: 68% | Emotion: anxious
Statement 4: 'I don\'t really remember where I was, honestly.'
  Stress: 78% | Emotion: resigned

⚠️  Inconsistency detected: Location story changed 3 times
Recommend: Prepare client with consistent, accurate timeline''',
        tags=["emotional-intelligence", "deception", "deposition", "analysis"],
        difficulty="advanced",
    ),
    CookbookScenario(
        id="workflow-002",
        title="Automated compliance monitoring workflow",
        description="Set up a recurring workflow that monitors regulatory changes and alerts compliance team.",
        code='''
import requests
BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}

workflow = requests.post(
    f"{BASE_URL}/workflows",
    json={
        "name": "Regulatory Change Monitor",
        "trigger": "cron:0 9 * * 1",
        "steps": [
            {"id": "s1", "type": "fetch_regulatory_updates", "tool": "compliance.watch"},
            {"id": "s2", "type": "analyze_impact", "tool": "compliance.check", "depends_on": ["s1"]},
            {"id": "s3", "type": "generate_report", "tool": "reports.generate", "depends_on": ["s2"]},
            {"id": "s4", "type": "notify_team", "tool": "notify.slack", "depends_on": ["s3"]},
        ],
    },
    headers=HEADERS,
).json()
print(f"Workflow: {workflow['workflow_id']} | Trigger: every Monday at 9am")
print(f"Pipeline: {len(workflow['steps'])} steps")
print("\\nMonitoring: GDPR, CCPA, HIPAA, FTC, CFPB regulatory updates")
print("Alerting: #compliance Slack channel + weekly PDF report")
''',
        expected_output='''Workflow: wf_reg_monitor_001 | Trigger: every Monday at 9am
Pipeline: 4 steps

Monitoring: GDPR, CCPA, HIPAA, FTC, CFPB regulatory updates
Alerting: #compliance Slack channel + weekly PDF report''',
        tags=["workflow", "compliance", "automation", "monitoring"],
        difficulty="advanced",
    ),
    CookbookScenario(
        id="appbuilder-002",
        title="Generate TypeScript SDK from OpenAPI spec",
        description="Use the SDK generator to auto-build a TypeScript client for all SintraPrime APIs.",
        code='''
import requests
BASE_URL = "https://api.sintraprime.ikesolutions.org/v2"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN"}

# Download TypeScript SDK
resp = requests.get(f"{BASE_URL}/sdk/typescript", headers=HEADERS)
sdk_content = resp.text
print(f"TypeScript SDK downloaded: {len(sdk_content)} characters")
print("\\nSDK includes:")
print("  • Auto-generated types for all 50+ schemas")
print("  • Async/await methods for all 35+ endpoints")
print("  • Built-in retry logic and rate limit handling")
print("  • Full JSDoc documentation")
print("\\nUsage example:")
print("""
  import { SintraPrimeClient } from \'sintraprime-sdk\';
  const client = new SintraPrimeClient({ apiKey: \'YOUR_KEY\' });
  const cases = await client.legal.searchCaseLaw({ query: \'contract breach\' });
""")
''',
        expected_output='''TypeScript SDK downloaded: 48293 characters

SDK includes:
  • Auto-generated types for all 50+ schemas
  • Async/await methods for all 35+ endpoints
  • Built-in retry logic and rate limit handling
  • Full JSDoc documentation

Usage example:

  import { SintraPrimeClient } from \'sintraprime-sdk\';
  const client = new SintraPrimeClient({ apiKey: \'YOUR_KEY\' });
  const cases = await client.legal.searchCaseLaw({ query: \'contract breach\' });''',
        tags=["sdk", "typescript", "developer-experience"],
        difficulty="beginner",
    ),
]

for s in ADDITIONAL_SCENARIOS:
    register(s)


# ---------------------------------------------------------------------------
# Cookbook runner and utilities
# ---------------------------------------------------------------------------

def get_scenario(scenario_id: str) -> CookbookScenario | None:
    """Retrieve a scenario by ID."""
    return next((s for s in SCENARIOS if s.id == scenario_id), None)


def search_scenarios(tags: list[str] | None = None, difficulty: str | None = None) -> list[CookbookScenario]:
    """Search scenarios by tags and/or difficulty."""
    results = SCENARIOS
    if tags:
        results = [s for s in results if any(t in s.tags for t in tags)]
    if difficulty:
        results = [s for s in results if s.difficulty == difficulty]
    return results


def list_scenarios() -> list[dict]:
    """Return summary list of all scenarios."""
    return [
        {
            "id": s.id,
            "title": s.title,
            "tags": s.tags,
            "difficulty": s.difficulty,
            "description": s.description[:80] + "...",
        }
        for s in SCENARIOS
    ]


def run_scenario(scenario_id: str) -> dict:
    """'Run' a scenario — returns the scenario code and expected output."""
    scenario = get_scenario(scenario_id)
    if not scenario:
        return {"error": f"Scenario '{scenario_id}' not found"}
    return {
        "id": scenario.id,
        "title": scenario.title,
        "code": scenario.code.strip(),
        "expected_output": scenario.expected_output.strip(),
        "tags": scenario.tags,
        "difficulty": scenario.difficulty,
    }


def export_cookbook(output_path: str = "cookbook_export.json") -> None:
    """Export all scenarios to JSON."""
    data = [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "code": s.code.strip(),
            "expected_output": s.expected_output.strip(),
            "tags": s.tags,
            "difficulty": s.difficulty,
        }
        for s in SCENARIOS
    ]
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Exported {len(data)} scenarios to {output_path}")


if __name__ == "__main__":
    print(f"📚 SintraPrime Cookbook — {len(SCENARIOS)} scenarios loaded\n")
    for s in SCENARIOS:
        print(f"  [{s.difficulty:>12}] {s.id:<20} — {s.title}")
    export_cookbook()
