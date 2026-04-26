"""
model_playground.py — SintraPrime Model Playground
Test different LLM backends against SintraPrime prompts.
Supports: OpenAI GPT-4o, Claude 3.5, Ollama (local), DeepSeek, Hermes
Features: benchmarking, A/B testing, 50+ prompt templates
"""

from __future__ import annotations
import time
import json
import random
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    HERMES = "hermes"


@dataclass
class ModelConfig:
    provider: ModelProvider
    model_id: str
    display_name: str
    context_window: int
    cost_per_1k_input: float   # USD
    cost_per_1k_output: float  # USD
    max_tokens: int = 4096
    supports_streaming: bool = True
    notes: str = ""


SUPPORTED_MODELS: dict[str, ModelConfig] = {
    "gpt-4o": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o",
        display_name="OpenAI GPT-4o",
        context_window=128000,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        notes="Best for complex legal reasoning and document analysis",
    ),
    "gpt-4o-mini": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o-mini",
        display_name="OpenAI GPT-4o Mini",
        context_window=128000,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        notes="Good for high-volume, cost-sensitive tasks",
    ),
    "claude-3-5-sonnet": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-3-5-sonnet-20241022",
        display_name="Claude 3.5 Sonnet",
        context_window=200000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        notes="Excellent context window, great for long document analysis",
    ),
    "claude-3-haiku": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-3-haiku-20240307",
        display_name="Claude 3 Haiku",
        context_window=200000,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        notes="Fastest Anthropic model, good for quick lookups",
    ),
    "ollama-llama3": ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_id="llama3:8b",
        display_name="Llama 3 8B (Local)",
        context_window=8192,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        notes="Free local inference, good for privacy-sensitive data",
    ),
    "ollama-mistral": ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_id="mistral:7b",
        display_name="Mistral 7B (Local)",
        context_window=8192,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        notes="Strong instruction following at 7B scale",
    ),
    "deepseek-chat": ModelConfig(
        provider=ModelProvider.DEEPSEEK,
        model_id="deepseek-chat",
        display_name="DeepSeek Chat",
        context_window=32000,
        cost_per_1k_input=0.0002,
        cost_per_1k_output=0.0002,
        notes="Excellent value for reasoning tasks",
    ),
    "deepseek-coder": ModelConfig(
        provider=ModelProvider.DEEPSEEK,
        model_id="deepseek-coder",
        display_name="DeepSeek Coder",
        context_window=16000,
        cost_per_1k_input=0.0002,
        cost_per_1k_output=0.0002,
        notes="Best for code generation in SDK scenarios",
    ),
    "hermes-3": ModelConfig(
        provider=ModelProvider.HERMES,
        model_id="NousResearch/Hermes-3-Llama-3.1-8B",
        display_name="Hermes 3 Llama 3.1 8B",
        context_window=8192,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        notes="Specialized in function calling and agent tasks",
    ),
}


# ---------------------------------------------------------------------------
# Prompt Templates Library (50+)
# ---------------------------------------------------------------------------

@dataclass
class PromptTemplate:
    id: str
    name: str
    category: str
    system_prompt: str
    user_template: str
    variables: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


PROMPT_TEMPLATES: list[PromptTemplate] = [
    # --- Legal Analysis ---
    PromptTemplate(
        id="legal-001", name="Case Law Summarizer", category="legal",
        system_prompt="You are an expert legal researcher. Summarize case law clearly and concisely, focusing on holdings and practical implications.",
        user_template="Summarize the key legal holding and practical implications of: {case_citation}",
        variables=["case_citation"], tags=["legal", "case-law"],
    ),
    PromptTemplate(
        id="legal-002", name="Contract Red Flag Detector", category="legal",
        system_prompt="You are a contract review attorney. Identify problematic clauses that harm the specified party, citing specific legal issues.",
        user_template="Review this {contract_type} contract for a {party_role} and identify all red flags:\n\n{contract_text}",
        variables=["contract_type", "party_role", "contract_text"], tags=["legal", "contract"],
    ),
    PromptTemplate(
        id="legal-003", name="Statute Interpreter", category="legal",
        system_prompt="You are a statutory interpretation expert. Analyze statutes using textualist, purposivist, and practical approaches.",
        user_template="Interpret {statute} as applied to the following scenario: {scenario}",
        variables=["statute", "scenario"], tags=["legal", "statutory"],
    ),
    PromptTemplate(
        id="legal-004", name="Demand Letter Drafter", category="legal",
        system_prompt="You are an attorney drafting a formal demand letter. Be firm, legally precise, and include a clear deadline and consequences.",
        user_template="Draft a demand letter for: {client_name} demanding {demand_amount} from {respondent} for {cause_of_action}",
        variables=["client_name", "demand_amount", "respondent", "cause_of_action"], tags=["legal", "drafting"],
    ),
    PromptTemplate(
        id="legal-005", name="Case Outcome Predictor", category="legal",
        system_prompt="You are a legal AI analyst. Predict case outcomes based on similar precedents and provide probability estimates with key factors.",
        user_template="Predict the outcome probability for a {case_type} case in {jurisdiction} with these facts: {facts}",
        variables=["case_type", "jurisdiction", "facts"], tags=["legal", "prediction"],
    ),
    PromptTemplate(
        id="legal-006", name="Discovery Request Generator", category="legal",
        system_prompt="You are a litigation specialist. Generate thorough discovery requests that maximize information gathering while complying with procedural rules.",
        user_template="Generate {num_requests} interrogatories for a {case_type} case in {jurisdiction} for the {party} party",
        variables=["num_requests", "case_type", "jurisdiction", "party"], tags=["legal", "discovery"],
    ),
    PromptTemplate(
        id="legal-007", name="Affirmative Defense Identifier", category="legal",
        system_prompt="You are a defense attorney expert. Identify all viable affirmative defenses based on the facts presented.",
        user_template="What affirmative defenses apply in this {case_type} case? Facts: {facts}",
        variables=["case_type", "facts"], tags=["legal", "defense"],
    ),
    PromptTemplate(
        id="legal-008", name="Legal Research Memo", category="legal",
        system_prompt="You are a senior associate at a law firm. Draft a formal legal research memo with IRAC structure.",
        user_template="Write a legal research memo on: {research_question} in {jurisdiction}",
        variables=["research_question", "jurisdiction"], tags=["legal", "research", "memo"],
    ),
    PromptTemplate(
        id="legal-009", name="Plea Deal Evaluator", category="legal",
        system_prompt="You are a criminal defense attorney. Evaluate plea deals objectively, weighing risks of trial versus plea terms.",
        user_template="Evaluate this plea deal for {charge}: Offer is {plea_offer}. Trial risk factors: {risk_factors}",
        variables=["charge", "plea_offer", "risk_factors"], tags=["legal", "criminal", "plea"],
    ),
    PromptTemplate(
        id="legal-010", name="Jurisdiction Analyzer", category="legal",
        system_prompt="You are a conflict of laws expert. Analyze which jurisdiction's law applies and any procedural issues.",
        user_template="Which jurisdiction applies to a dispute between {party_a} in {state_a} and {party_b} in {state_b} regarding {contract_type}?",
        variables=["party_a", "state_a", "party_b", "state_b", "contract_type"], tags=["legal", "jurisdiction"],
    ),
    # --- Financial ---
    PromptTemplate(
        id="fin-001", name="Debt Negotiation Strategist", category="financial",
        system_prompt="You are a debt settlement expert. Develop optimal negotiation strategies based on creditor type, debt age, and available funds.",
        user_template="Create a debt settlement strategy for ${amount} owed to {creditor}, {months_delinquent} months delinquent, with ${available_funds} available.",
        variables=["amount", "creditor", "months_delinquent", "available_funds"], tags=["financial", "debt"],
    ),
    PromptTemplate(
        id="fin-002", name="Credit Dispute Letter", category="financial",
        system_prompt="You are a consumer credit attorney. Draft FCRA-compliant dispute letters that maximize removal chances.",
        user_template="Write a credit dispute letter to {bureau} disputing a {item_type} from {creditor} on the grounds of {dispute_reason}",
        variables=["bureau", "item_type", "creditor", "dispute_reason"], tags=["financial", "credit"],
    ),
    PromptTemplate(
        id="fin-003", name="Budget Optimizer", category="financial",
        system_prompt="You are a certified financial planner. Create actionable budget optimization plans based on income, expenses, and goals.",
        user_template="Optimize a budget with monthly income of ${income}, fixed expenses ${fixed}, variable expenses ${variable}, goals: {goals}",
        variables=["income", "fixed", "variable", "goals"], tags=["financial", "budget"],
    ),
    PromptTemplate(
        id="fin-004", name="Investment Risk Analyzer", category="financial",
        system_prompt="You are a portfolio manager. Analyze investment portfolios for risk concentration, asset allocation, and rebalancing needs.",
        user_template="Analyze investment risk for portfolio: {portfolio_description} with risk tolerance: {risk_tolerance}",
        variables=["portfolio_description", "risk_tolerance"], tags=["financial", "investment"],
    ),
    PromptTemplate(
        id="fin-005", name="Mortgage Affordability Calculator", category="financial",
        system_prompt="You are a mortgage advisor. Calculate true affordability including all costs and provide clear guidance.",
        user_template="Calculate mortgage affordability for income ${income}, debts ${monthly_debts}, down payment ${down_payment}, in {state}",
        variables=["income", "monthly_debts", "down_payment", "state"], tags=["financial", "mortgage"],
    ),
    # --- Trust & Estate ---
    PromptTemplate(
        id="estate-001", name="Estate Planning Advisor", category="estate",
        system_prompt="You are an estate planning attorney. Provide comprehensive estate planning recommendations based on assets, family situation, and goals.",
        user_template="Create an estate plan recommendation for: assets ${total_assets}, family: {family_situation}, state: {state}, concerns: {concerns}",
        variables=["total_assets", "family_situation", "state", "concerns"], tags=["estate", "trust"],
    ),
    PromptTemplate(
        id="estate-002", name="Trust vs Will Analyzer", category="estate",
        system_prompt="You are a trust and estate attorney. Objectively compare trust vs will options for a client's specific situation.",
        user_template="Should {client_name} use a living trust or will? Assets: ${assets}, state: {state}, situation: {situation}",
        variables=["client_name", "assets", "state", "situation"], tags=["estate", "trust", "will"],
    ),
    PromptTemplate(
        id="estate-003", name="Beneficiary Designation Reviewer", category="estate",
        system_prompt="You are an estate planning expert. Review beneficiary designations for common mistakes and conflicts with overall estate plan.",
        user_template="Review beneficiary designations for: {accounts_description} in context of estate plan: {estate_plan_summary}",
        variables=["accounts_description", "estate_plan_summary"], tags=["estate", "beneficiary"],
    ),
    # --- Compliance ---
    PromptTemplate(
        id="comp-001", name="GDPR Gap Analyzer", category="compliance",
        system_prompt="You are a GDPR compliance expert (CIPP/E certified). Identify specific compliance gaps and actionable remediation steps.",
        user_template="Analyze GDPR compliance gaps for: {company_description} that collects {data_types} and processes {processing_activities}",
        variables=["company_description", "data_types", "processing_activities"], tags=["compliance", "GDPR"],
    ),
    PromptTemplate(
        id="comp-002", name="Privacy Policy Generator", category="compliance",
        system_prompt="You are a privacy attorney. Draft CCPA and GDPR compliant privacy policies that are clear and comprehensive.",
        user_template="Draft a privacy policy for a {business_type} company in {state} that collects {data_types}",
        variables=["business_type", "state", "data_types"], tags=["compliance", "privacy"],
    ),
    PromptTemplate(
        id="comp-003", name="Terms of Service Drafter", category="compliance",
        system_prompt="You are a tech attorney specializing in platform agreements. Draft clear, enforceable terms of service.",
        user_template="Draft terms of service for a {platform_type} platform with these key requirements: {requirements}",
        variables=["platform_type", "requirements"], tags=["compliance", "terms"],
    ),
    PromptTemplate(
        id="comp-004", name="HIPAA Risk Assessment", category="compliance",
        system_prompt="You are a HIPAA compliance officer. Conduct thorough risk assessments identifying vulnerabilities in PHI handling.",
        user_template="Conduct a HIPAA risk assessment for a {entity_type} that handles {phi_types} with these current controls: {controls}",
        variables=["entity_type", "phi_types", "controls"], tags=["compliance", "HIPAA"],
    ),
    # --- Governance ---
    PromptTemplate(
        id="gov-001", name="AI Agent Policy Drafter", category="governance",
        system_prompt="You are an AI governance expert. Draft comprehensive policies governing AI agent behavior, safety, and accountability.",
        user_template="Draft an AI governance policy for {agent_type} agents used in {use_case} with risk level: {risk_level}",
        variables=["agent_type", "use_case", "risk_level"], tags=["governance", "ai", "policy"],
    ),
    PromptTemplate(
        id="gov-002", name="Audit Trail Analyzer", category="governance",
        system_prompt="You are a governance and compliance auditor. Analyze audit logs to identify patterns, anomalies, and compliance issues.",
        user_template="Analyze these audit log entries for anomalies and compliance issues: {audit_log_summary}",
        variables=["audit_log_summary"], tags=["governance", "audit"],
    ),
    # --- Business ---
    PromptTemplate(
        id="biz-001", name="Business Formation Guide", category="business",
        system_prompt="You are a business attorney and CPA. Provide comprehensive business formation guidance covering legal, tax, and operational aspects.",
        user_template="Guide me through forming a {business_type} in {state} for {business_purpose} with {num_owners} owners",
        variables=["business_type", "state", "business_purpose", "num_owners"], tags=["business", "formation"],
    ),
    PromptTemplate(
        id="biz-002", name="Operating Agreement Drafter", category="business",
        system_prompt="You are a business attorney specializing in LLC agreements. Draft comprehensive operating agreements tailored to member needs.",
        user_template="Draft key provisions for an LLC operating agreement for {business_name} with members: {members_description}",
        variables=["business_name", "members_description"], tags=["business", "LLC", "agreement"],
    ),
    PromptTemplate(
        id="biz-003", name="IP Protection Advisor", category="business",
        system_prompt="You are an intellectual property attorney. Advise on comprehensive IP protection strategies for businesses.",
        user_template="Advise on IP protection for: {ip_description} in the {industry} industry targeting {markets}",
        variables=["ip_description", "industry", "markets"], tags=["business", "IP", "trademark"],
    ),
    # --- Emotional Intelligence ---
    PromptTemplate(
        id="ei-001", name="Empathetic Response Generator", category="emotional",
        system_prompt="You are an emotionally intelligent communicator. Generate warm, empathetic responses that acknowledge feelings and provide support.",
        user_template="Generate an empathetic response to this distressed message: {message}",
        variables=["message"], tags=["emotional", "empathy"],
    ),
    PromptTemplate(
        id="ei-002", name="Conflict De-escalator", category="emotional",
        system_prompt="You are a conflict resolution expert and mediator. De-escalate conflicts by acknowledging all parties and finding common ground.",
        user_template="De-escalate this conflict between {party_a} and {party_b}: {conflict_description}",
        variables=["party_a", "party_b", "conflict_description"], tags=["emotional", "conflict", "mediation"],
    ),
    PromptTemplate(
        id="ei-003", name="Difficult News Communicator", category="emotional",
        system_prompt="You are an expert in compassionate communication. Help deliver difficult news with empathy, clarity, and appropriate support.",
        user_template="Help communicate this difficult news to {recipient}: {news} Consider their situation: {context}",
        variables=["recipient", "news", "context"], tags=["emotional", "communication"],
    ),
    # --- MCP / Agent ---
    PromptTemplate(
        id="agent-001", name="Agent Task Decomposer", category="agent",
        system_prompt="You are an expert at breaking complex tasks into clear, parallel, executable subtasks for AI agent swarms.",
        user_template="Decompose this complex task into 5-8 parallel subtasks for an AI swarm: {task}",
        variables=["task"], tags=["agent", "mcp", "decomposition"],
    ),
    PromptTemplate(
        id="agent-002", name="Tool Selection Advisor", category="agent",
        system_prompt="You are an AI systems architect. Recommend the optimal MCP tools for a given task, explaining tradeoffs.",
        user_template="Which MCP tools should I use for: {task}? Available tools: {available_tools}",
        variables=["task", "available_tools"], tags=["agent", "mcp", "tools"],
    ),
    PromptTemplate(
        id="agent-003", name="Prompt Optimizer", category="agent",
        system_prompt="You are a prompt engineering expert. Optimize prompts for clarity, specificity, and better model performance.",
        user_template="Optimize this prompt for {model_name}: {original_prompt}",
        variables=["model_name", "original_prompt"], tags=["agent", "prompting"],
    ),
    # --- Workflow ---
    PromptTemplate(
        id="wf-001", name="Workflow Designer", category="workflow",
        system_prompt="You are a process automation expert. Design efficient, fault-tolerant workflows with clear step dependencies.",
        user_template="Design a workflow for: {process_description}. Must handle: {edge_cases}",
        variables=["process_description", "edge_cases"], tags=["workflow", "automation"],
    ),
    PromptTemplate(
        id="wf-002", name="SLA Optimizer", category="workflow",
        system_prompt="You are a workflow optimization specialist. Identify bottlenecks and suggest improvements to meet SLA targets.",
        user_template="Optimize this workflow for a {sla_target} SLA: {workflow_description}. Current bottlenecks: {bottlenecks}",
        variables=["sla_target", "workflow_description", "bottlenecks"], tags=["workflow", "SLA", "optimization"],
    ),
    # --- Extra prompts to reach 50+ ---
    PromptTemplate(id="legal-011", name="Mediation Brief Writer", category="legal",
        system_prompt="You are a mediator. Write concise, balanced mediation briefs that fairly represent all parties.",
        user_template="Write a mediation brief for {case_type} dispute. Plaintiff position: {plaintiff}. Defendant position: {defendant}",
        variables=["case_type", "plaintiff", "defendant"], tags=["legal", "mediation"]),
    PromptTemplate(id="legal-012", name="Settlement Agreement Drafter", category="legal",
        system_prompt="You are a settlement attorney. Draft comprehensive settlement agreements that protect all parties.",
        user_template="Draft settlement agreement terms for {case_type}: Amount ${amount}, from {payer} to {payee}. Terms: {terms}",
        variables=["case_type", "amount", "payer", "payee", "terms"], tags=["legal", "settlement"]),
    PromptTemplate(id="legal-013", name="Appellate Brief Outliner", category="legal",
        system_prompt="You are an appellate attorney. Create detailed appellate brief outlines focusing on strongest arguments.",
        user_template="Outline an appellate brief challenging: {lower_court_ruling} on grounds: {grounds_of_appeal}",
        variables=["lower_court_ruling", "grounds_of_appeal"], tags=["legal", "appellate"]),
    PromptTemplate(id="fin-006", name="Tax Strategy Advisor", category="financial",
        system_prompt="You are a tax strategist (CPA/JD). Identify tax minimization strategies for the given situation.",
        user_template="Recommend tax strategies for: income ${income}, business type {business_type}, state {state}, goals: {tax_goals}",
        variables=["income", "business_type", "state", "tax_goals"], tags=["financial", "tax"]),
    PromptTemplate(id="fin-007", name="Bankruptcy Evaluator", category="financial",
        system_prompt="You are a bankruptcy attorney. Objectively evaluate whether bankruptcy makes sense and which chapter applies.",
        user_template="Evaluate bankruptcy for: debts ${debts}, assets ${assets}, income ${income}, situation: {situation}",
        variables=["debts", "assets", "income", "situation"], tags=["financial", "bankruptcy"]),
    PromptTemplate(id="estate-004", name="Gift Tax Planner", category="estate",
        system_prompt="You are an estate planning attorney specializing in gift tax strategies and intergenerational wealth transfer.",
        user_template="Plan gift tax strategy for transferring ${gift_amount} to {recipients} with estate size ${estate_size}",
        variables=["gift_amount", "recipients", "estate_size"], tags=["estate", "gift-tax"]),
    PromptTemplate(id="comp-005", name="Incident Response Plan", category="compliance",
        system_prompt="You are a cybersecurity and compliance expert. Create actionable data breach incident response plans.",
        user_template="Create a data breach incident response plan for a {company_type} with {data_types} breach affecting {num_affected} records",
        variables=["company_type", "data_types", "num_affected"], tags=["compliance", "security", "breach"]),
    PromptTemplate(id="biz-004", name="NDA Reviewer", category="business",
        system_prompt="You are a business attorney. Review NDAs to identify unfair provisions and suggest balanced alternatives.",
        user_template="Review this NDA for {party_role}: {nda_text}",
        variables=["party_role", "nda_text"], tags=["business", "NDA", "contract"]),
    PromptTemplate(id="biz-005", name="Franchise Agreement Analyzer", category="business",
        system_prompt="You are a franchise law specialist. Analyze franchise agreements for key risks and obligations.",
        user_template="Analyze this franchise agreement for a {franchise_type} franchise: key terms {terms}, FDD disclosure: {fdd_summary}",
        variables=["franchise_type", "terms", "fdd_summary"], tags=["business", "franchise"]),
    PromptTemplate(id="gov-003", name="Whistleblower Policy Drafter", category="governance",
        system_prompt="You are a corporate governance attorney. Draft comprehensive whistleblower protection policies.",
        user_template="Draft a whistleblower policy for a {company_type} with {employee_count} employees in {industry}",
        variables=["company_type", "employee_count", "industry"], tags=["governance", "whistleblower"]),
    PromptTemplate(id="ei-004", name="Client Retention Message", category="emotional",
        system_prompt="You are a client relationship expert. Craft personalized retention messages that rebuild trust after service failures.",
        user_template="Write a client retention message for {client_name} who complained about {issue} after {relationship_length} as a client",
        variables=["client_name", "issue", "relationship_length"], tags=["emotional", "retention", "client"]),
    PromptTemplate(id="agent-004", name="System Prompt Generator", category="agent",
        system_prompt="You are a prompt engineer. Create detailed system prompts that give AI agents clear personas and behavioral guardrails.",
        user_template="Generate a system prompt for an AI agent that {agent_role} in the {domain} domain with constraints: {constraints}",
        variables=["agent_role", "domain", "constraints"], tags=["agent", "system-prompt"]),
    PromptTemplate(id="wf-003", name="API Integration Designer", category="workflow",
        system_prompt="You are an API integration architect. Design robust integration patterns between systems.",
        user_template="Design integration between {system_a} and {system_b} for use case: {use_case}. Constraints: {constraints}",
        variables=["system_a", "system_b", "use_case", "constraints"], tags=["workflow", "api", "integration"]),
    PromptTemplate(id="legal-014", name="Mediation Strategy Advisor", category="legal",
        system_prompt="You are a certified mediator with expertise in dispute resolution. Provide practical mediation strategies that maximize settlement probability while protecting client interests.",
        user_template="Advise on mediation strategy for a {dispute_type} dispute. My position: {my_position}. Other party: {other_position}. Key issues: {key_issues}",
        variables=["dispute_type", "my_position", "other_position", "key_issues"], tags=["legal", "mediation", "dispute-resolution"]),
    PromptTemplate(id="fin-008", name="Investment Risk Assessment", category="financial",
        system_prompt="You are a Registered Investment Advisor. Assess investment risk objectively and provide risk-adjusted recommendations aligned with client goals.",
        user_template="Assess the investment risk for {investment_type} given: client age {client_age}, risk tolerance {risk_tolerance}, time horizon {time_horizon}, and current portfolio {portfolio_summary}",
        variables=["investment_type", "client_age", "risk_tolerance", "time_horizon", "portfolio_summary"], tags=["financial", "investment", "risk"]),
]


# ---------------------------------------------------------------------------
# Benchmark result dataclass
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    model_id: str
    prompt_id: str
    response: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    quality_score: float  # 0-1, simulated
    error: str | None = None


@dataclass
class ABTestResult:
    model_a: str
    model_b: str
    prompt_id: str
    result_a: BenchmarkResult
    result_b: BenchmarkResult
    winner: str  # model_id or "tie"
    comparison_summary: str


# ---------------------------------------------------------------------------
# Model client simulators (production would call real APIs)
# ---------------------------------------------------------------------------

class ModelClient:
    """Base class for model clients."""

    def __init__(self, config: ModelConfig, api_key: str = ""):
        self.config = config
        self.api_key = api_key

    def complete(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        """Call the model and return result dict."""
        raise NotImplementedError


class OpenAIClient(ModelClient):
    """OpenAI API client."""

    def complete(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            start = time.time()
            response = client.chat.completions.create(
                model=self.config.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=self.config.max_tokens,
            )
            latency_ms = (time.time() - start) * 1000
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = (input_tokens / 1000 * self.config.cost_per_1k_input +
                    output_tokens / 1000 * self.config.cost_per_1k_output)
            return {
                "response": content,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
            }
        except ImportError:
            return self._mock_response(system_prompt, user_message)
        except Exception as e:
            return {"error": str(e)}

    def _mock_response(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        """Return simulated response when openai package not available."""
        mock_latency = random.uniform(800, 2500)
        mock_tokens_in = len(user_message.split()) * 1.3
        mock_tokens_out = random.randint(200, 800)
        cost = (mock_tokens_in / 1000 * self.config.cost_per_1k_input +
                mock_tokens_out / 1000 * self.config.cost_per_1k_output)
        return {
            "response": f"[Mock {self.config.display_name}] Response to: {user_message[:50]}...",
            "latency_ms": mock_latency,
            "input_tokens": int(mock_tokens_in),
            "output_tokens": mock_tokens_out,
            "cost_usd": cost,
        }


class AnthropicClient(ModelClient):
    """Anthropic Claude API client."""

    def complete(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            start = time.time()
            response = client.messages.create(
                model=self.config.model_id,
                max_tokens=self.config.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            latency_ms = (time.time() - start) * 1000
            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (input_tokens / 1000 * self.config.cost_per_1k_input +
                    output_tokens / 1000 * self.config.cost_per_1k_output)
            return {
                "response": content,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
            }
        except ImportError:
            return self._mock_response(user_message)
        except Exception as e:
            return {"error": str(e)}

    def _mock_response(self, user_message: str) -> dict[str, Any]:
        mock_latency = random.uniform(600, 2000)
        mock_tokens_in = len(user_message.split()) * 1.3
        mock_tokens_out = random.randint(200, 700)
        cost = (mock_tokens_in / 1000 * self.config.cost_per_1k_input +
                mock_tokens_out / 1000 * self.config.cost_per_1k_output)
        return {
            "response": f"[Mock {self.config.display_name}] Thoughtful response to: {user_message[:50]}...",
            "latency_ms": mock_latency,
            "input_tokens": int(mock_tokens_in),
            "output_tokens": mock_tokens_out,
            "cost_usd": cost,
        }


class OllamaClient(ModelClient):
    """Ollama local inference client."""

    def __init__(self, config: ModelConfig, base_url: str = "http://localhost:11434"):
        super().__init__(config)
        self.base_url = base_url

    def complete(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        try:
            import urllib.request
            import urllib.error
            payload = json.dumps({
                "model": self.config.model_id,
                "prompt": f"System: {system_prompt}\n\nUser: {user_message}",
                "stream": False,
            }).encode()
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            start = time.time()
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            latency_ms = (time.time() - start) * 1000
            return {
                "response": data.get("response", ""),
                "latency_ms": latency_ms,
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
                "cost_usd": 0.0,
            }
        except Exception as e:
            return self._mock_response(user_message)

    def _mock_response(self, user_message: str) -> dict[str, Any]:
        mock_latency = random.uniform(3000, 12000)  # Local inference is slower
        mock_tokens_out = random.randint(100, 500)
        return {
            "response": f"[Mock Ollama {self.config.model_id}] Local response: {user_message[:50]}...",
            "latency_ms": mock_latency,
            "input_tokens": len(user_message.split()),
            "output_tokens": mock_tokens_out,
            "cost_usd": 0.0,
        }


class DeepSeekClient(ModelClient):
    """DeepSeek API client (OpenAI-compatible)."""

    def complete(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com/v1",
            )
            start = time.time()
            response = client.chat.completions.create(
                model=self.config.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=self.config.max_tokens,
            )
            latency_ms = (time.time() - start) * 1000
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = (input_tokens / 1000 * self.config.cost_per_1k_input +
                    output_tokens / 1000 * self.config.cost_per_1k_output)
            return {
                "response": content,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
            }
        except Exception:
            return self._mock_response(user_message)

    def _mock_response(self, user_message: str) -> dict[str, Any]:
        mock_latency = random.uniform(500, 1800)
        mock_tokens_out = random.randint(200, 600)
        return {
            "response": f"[Mock DeepSeek] Analytical response to: {user_message[:50]}...",
            "latency_ms": mock_latency,
            "input_tokens": len(user_message.split()),
            "output_tokens": mock_tokens_out,
            "cost_usd": mock_tokens_out / 1000 * self.config.cost_per_1k_output,
        }


def get_client(model_id: str, api_key: str = "", **kwargs) -> ModelClient:
    """Factory function to get the appropriate model client."""
    config = SUPPORTED_MODELS.get(model_id)
    if not config:
        raise ValueError(f"Unknown model: {model_id}. Available: {list(SUPPORTED_MODELS.keys())}")
    if config.provider == ModelProvider.OPENAI:
        return OpenAIClient(config, api_key)
    elif config.provider == ModelProvider.ANTHROPIC:
        return AnthropicClient(config, api_key)
    elif config.provider == ModelProvider.OLLAMA:
        return OllamaClient(config, **kwargs)
    elif config.provider in (ModelProvider.DEEPSEEK, ModelProvider.HERMES):
        return DeepSeekClient(config, api_key)
    raise ValueError(f"No client for provider: {config.provider}")


# ---------------------------------------------------------------------------
# Benchmark engine
# ---------------------------------------------------------------------------

class PlaygroundBenchmark:
    """Run benchmarks across models and prompt templates."""

    def __init__(self, api_keys: dict[str, str] | None = None):
        self.api_keys = api_keys or {}

    def run_single(
        self,
        model_id: str,
        template_id: str,
        variables: dict[str, str] | None = None,
    ) -> BenchmarkResult:
        """Run a single model against a single prompt template."""
        template = next((t for t in PROMPT_TEMPLATES if t.id == template_id), None)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")

        variables = variables or {}
        user_message = template.user_template
        for var in template.variables:
            user_message = user_message.replace(f"{{{var}}}", variables.get(var, f"[{var}]"))

        if model_id not in SUPPORTED_MODELS:
            raise ValueError(f"Unknown model: {model_id}. Available: {list(SUPPORTED_MODELS.keys())}")
        config = SUPPORTED_MODELS[model_id]
        provider_key = config.provider.value
        api_key = self.api_keys.get(provider_key, self.api_keys.get(model_id, ""))
        client = get_client(model_id, api_key)

        raw = client.complete(template.system_prompt, user_message)
        if "error" in raw:
            return BenchmarkResult(
                model_id=model_id, prompt_id=template_id,
                response="", latency_ms=0, input_tokens=0,
                output_tokens=0, cost_usd=0, quality_score=0,
                error=raw["error"],
            )

        quality_score = self._estimate_quality(raw["response"], template)
        return BenchmarkResult(
            model_id=model_id,
            prompt_id=template_id,
            response=raw["response"],
            latency_ms=raw["latency_ms"],
            input_tokens=raw["input_tokens"],
            output_tokens=raw["output_tokens"],
            cost_usd=raw["cost_usd"],
            quality_score=quality_score,
        )

    def _estimate_quality(self, response: str, template: PromptTemplate) -> float:
        """Heuristic quality estimation (0-1). Production would use LLM-as-judge."""
        score = 0.5
        if len(response) > 200:
            score += 0.2
        if len(response) > 500:
            score += 0.1
        # Check for structured output
        if any(marker in response for marker in ["1.", "•", "-", "**", "##"]):
            score += 0.1
        # Legal template quality signals
        if "legal" in template.tags and any(word in response.lower() for word in ["statute", "court", "law", "legal", "rights"]):
            score += 0.1
        return min(score, 1.0)

    def run_suite(
        self,
        model_ids: list[str],
        template_ids: list[str],
        variables: dict[str, str] | None = None,
    ) -> list[BenchmarkResult]:
        """Run multiple models against multiple templates."""
        results = []
        for model_id in model_ids:
            for template_id in template_ids:
                result = self.run_single(model_id, template_id, variables)
                results.append(result)
        return results

    def ab_test(
        self,
        model_a: str,
        model_b: str,
        template_id: str,
        variables: dict[str, str] | None = None,
    ) -> ABTestResult:
        """Compare two models head-to-head."""
        result_a = self.run_single(model_a, template_id, variables)
        result_b = self.run_single(model_b, template_id, variables)

        # Determine winner based on weighted score
        def weighted_score(r: BenchmarkResult) -> float:
            latency_norm = max(0, 1 - r.latency_ms / 10000)
            return r.quality_score * 0.6 + latency_norm * 0.2 + (1 - min(r.cost_usd * 100, 1)) * 0.2

        score_a = weighted_score(result_a)
        score_b = weighted_score(result_b)

        if abs(score_a - score_b) < 0.05:
            winner = "tie"
        elif score_a > score_b:
            winner = model_a
        else:
            winner = model_b

        summary = (
            f"{SUPPORTED_MODELS[model_a].display_name}: "
            f"quality={result_a.quality_score:.0%}, "
            f"latency={result_a.latency_ms:.0f}ms, "
            f"cost=${result_a.cost_usd:.4f}\n"
            f"{SUPPORTED_MODELS[model_b].display_name}: "
            f"quality={result_b.quality_score:.0%}, "
            f"latency={result_b.latency_ms:.0f}ms, "
            f"cost=${result_b.cost_usd:.4f}\n"
            f"Winner: {winner}"
        )
        return ABTestResult(
            model_a=model_a,
            model_b=model_b,
            prompt_id=template_id,
            result_a=result_a,
            result_b=result_b,
            winner=winner,
            comparison_summary=summary,
        )

    def cost_estimate(self, model_id: str, estimated_input_tokens: int, estimated_output_tokens: int) -> dict:
        """Estimate cost for a given volume of requests."""
        config = SUPPORTED_MODELS[model_id]
        cost_per_request = (
            estimated_input_tokens / 1000 * config.cost_per_1k_input +
            estimated_output_tokens / 1000 * config.cost_per_1k_output
        )
        return {
            "model": config.display_name,
            "cost_per_request_usd": cost_per_request,
            "cost_1000_requests_usd": cost_per_request * 1000,
            "cost_10000_requests_usd": cost_per_request * 10000,
            "cost_1m_requests_usd": cost_per_request * 1_000_000,
        }

    def leaderboard(self, results: list[BenchmarkResult]) -> list[dict]:
        """Generate leaderboard from benchmark results."""
        model_stats: dict[str, dict] = {}
        for r in results:
            if r.model_id not in model_stats:
                model_stats[r.model_id] = {
                    "model_id": r.model_id,
                    "display_name": SUPPORTED_MODELS[r.model_id].display_name,
                    "quality_scores": [],
                    "latencies": [],
                    "costs": [],
                    "errors": 0,
                }
            stats = model_stats[r.model_id]
            if r.error:
                stats["errors"] += 1
            else:
                stats["quality_scores"].append(r.quality_score)
                stats["latencies"].append(r.latency_ms)
                stats["costs"].append(r.cost_usd)

        leaderboard = []
        for stats in model_stats.values():
            qs = stats["quality_scores"]
            ls = stats["latencies"]
            cs = stats["costs"]
            entry = {
                "model": stats["display_name"],
                "avg_quality": sum(qs) / len(qs) if qs else 0,
                "avg_latency_ms": sum(ls) / len(ls) if ls else 0,
                "avg_cost_usd": sum(cs) / len(cs) if cs else 0,
                "error_count": stats["errors"],
                "test_count": len(qs),
            }
            entry["overall_score"] = (
                entry["avg_quality"] * 0.5 +
                max(0, 1 - entry["avg_latency_ms"] / 10000) * 0.3 +
                max(0, 1 - entry["avg_cost_usd"] * 10) * 0.2
            )
            leaderboard.append(entry)

        return sorted(leaderboard, key=lambda x: x["overall_score"], reverse=True)


# ---------------------------------------------------------------------------
# Quick-access functions
# ---------------------------------------------------------------------------

def list_models() -> list[dict]:
    """List all supported models."""
    return [
        {
            "id": k,
            "display_name": v.display_name,
            "provider": v.provider.value,
            "context_window": v.context_window,
            "cost_per_1k_input": v.cost_per_1k_input,
            "cost_per_1k_output": v.cost_per_1k_output,
            "notes": v.notes,
        }
        for k, v in SUPPORTED_MODELS.items()
    ]


def list_templates(category: str | None = None, tags: list[str] | None = None) -> list[dict]:
    """List prompt templates with optional filtering."""
    templates = PROMPT_TEMPLATES
    if category:
        templates = [t for t in templates if t.category == category]
    if tags:
        templates = [t for t in templates if any(tag in t.tags for tag in tags)]
    return [
        {
            "id": t.id,
            "name": t.name,
            "category": t.category,
            "variables": t.variables,
            "tags": t.tags,
        }
        for t in templates
    ]


def get_template(template_id: str) -> PromptTemplate | None:
    """Get a specific template by ID."""
    return next((t for t in PROMPT_TEMPLATES if t.id == template_id), None)


if __name__ == "__main__":
    print(f"🎮 SintraPrime Model Playground")
    print(f"   Supported models: {len(SUPPORTED_MODELS)}")
    print(f"   Prompt templates: {len(PROMPT_TEMPLATES)}\n")

    print("Models:")
    for m in list_models():
        print(f"  {m['display_name']:<30} ${m['cost_per_1k_input']:.4f}/1K in | ${m['cost_per_1k_output']:.4f}/1K out")

    print(f"\nTemplate categories: {sorted(set(t.category for t in PROMPT_TEMPLATES))}")

    # Example A/B test (dry run)
    bench = PlaygroundBenchmark()
    ab = bench.ab_test("gpt-4o", "claude-3-5-sonnet", "legal-001", {"case_citation": "Marbury v. Madison"})
    print(f"\nA/B Test:\n{ab.comparison_summary}")
