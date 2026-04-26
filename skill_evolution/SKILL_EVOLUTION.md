# Skill Evolution System — SintraPrime-Unified

> **Tango-3 Component** — Self-learning, continuously evolving skill ecosystem

---

## Overview

The Skill Evolution System is the autonomous learning layer of SintraPrime-Unified. Inspired by the best ideas from:

| System | Inspiration Taken |
|---|---|
| **Hermes Agent** | Procedural memory: capture successful tasks as reusable skills; auto-improve from failure |
| **OpenClaw** | Modular community skills marketplace; hottest skills leaderboard |
| **CrewAI** | Role-based skill specialization by domain (legal, financial, research…) |
| **GPT-5.5 Spud** | Iterative self-improvement: each execution makes the system smarter |

---

## Architecture

```
skill_evolution/
├── __init__.py              # Public API exports
├── skill_types.py           # Data models (Skill, SkillExecution, etc.)
├── skill_library.py         # SQLite-backed skill registry
├── skill_runner.py          # Safe sandboxed execution engine
├── skill_evolver.py         # Self-learning & auto-improvement engine
├── auto_skill_creator.py    # Autonomous skill generation
├── skill_marketplace.py     # Community skills marketplace
├── builtin_skills/          # Pre-built legal & financial skills
│   ├── legal_research.py
│   ├── document_drafter.py
│   ├── financial_analyzer.py
│   ├── court_monitor.py
│   ├── contract_reviewer.py
│   └── deadline_calculator.py
└── tests/
    └── test_skill_evolution.py   # 100 tests
```

---

## How the Self-Learning Loop Works

```
┌─────────────┐    Execute     ┌──────────────┐    Log Result   ┌─────────────────┐
│  SkillRunner │ ──────────── ▶ │  Sandbox Exec │ ──────────────▶ │  ExecutionDB    │
└─────────────┘                └──────────────┘                 └────────┬────────┘
                                                                         │
                                                                   Every 24h
                                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            SkillEvolver.watch_and_evolve()                      │
│                                                                                  │
│  1. analyze_failures(skill_id)   → identify error patterns                      │
│  2. suggest_improvements()       → rank improvement proposals                   │
│  3. auto_improve()               → apply best patch, bump version               │
│  4. evolution_report()           → weekly summary for review                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Failure Pattern Detection

The evolver uses **regex pattern matching** (no LLM required) against these known error categories:

| Pattern | Detection | Auto-Fix |
|---|---|---|
| `KeyError` | Missing dict key | Wrap in `try/except`, add `.get()` hint |
| `AttributeError` | Wrong attribute | Add `hasattr()` guard |
| `TypeError` | Type mismatch | Add `isinstance()` conversion |
| `ValueError` | Invalid value | Add input validation |
| `IndexError` | Out-of-range access | Add length check |
| `TimeoutError` | Execution too slow | Add caching hint |
| `ImportError` | Missing module | Remove/replace import |

---

## How Skills Are Created Automatically From Tasks

Inspired by Hermes Agent's **procedural memory**:

When an agent completes a task successfully, the code path used is captured as a new skill:

```python
from skill_evolution import SkillEvolver, SkillLibrary

library = SkillLibrary()
evolver = SkillEvolver(library)

# After completing a task manually or with another tool...
new_skill = evolver.create_from_task(
    task_description="Extract party names from NDA documents",
    task_outcome="Successfully extracted 3 parties from 12 NDAs",
    code_used="""
        import re
        text = params['document']
        parties = re.findall(r'"([A-Z][^"]+?)"\s+\("(\w+)"\)', text)
        result = {'parties': parties}
    """,
    category=SkillCategory.LEGAL,
)

print(f"Created skill: {new_skill.name} (ID: {new_skill.id})")
```

The system:
1. Extracts keywords from the task description → used as skill name and tags
2. Stores the successful code verbatim
3. Marks the skill as `EXPERIMENTAL` until it accumulates enough successful executions
4. Upgrades to `ACTIVE` once success rate exceeds 80% after 10+ uses

---

## Skill Categories

| Category | Description | Built-in Skills |
|---|---|---|
| `LEGAL` | Case law, documents, court monitoring | legal_research, doc_draft, case_summary, court_monitor, contract_reviewer |
| `FINANCIAL` | Budget, credit, ratios | financial_calc |
| `RESEARCH` | Information gathering | (extend via marketplace) |
| `COMMUNICATION` | Email, notifications | (extend via marketplace) |
| `DATA` | Extraction, transformation | (extend via marketplace) |
| `AUTOMATION` | Workflows, pipelines | (default for auto-created skills) |
| `CODING` | Code generation, review | (extend via marketplace) |
| `ANALYSIS` | Pattern recognition | (extend via marketplace) |

---

## Built-in Skill Library

### `legal_research`
Searches case law, statutes, and regulations by keyword + jurisdiction.

```python
from skill_evolution.builtin_skills import LegalResearchSkill
result = LegalResearchSkill().execute(query="miranda rights", jurisdiction="federal")
# {'results': [...], 'total_found': 2, 'success': True}
```

### `doc_draft`
Generates legal documents from templates.

```python
from skill_evolution.builtin_skills import DocumentDrafterSkill
result = DocumentDrafterSkill().execute(
    template_name="demand_letter",
    context={"sender_name": "Alice LLC", "amount": "$10,000", ...}
)
# {'document': '...full letter text...', 'success': True}
```

Available templates: `demand_letter`, `retainer_agreement`, `motion_to_dismiss`, `nda`

### `financial_calc`
Budget analysis, credit scoring, financial ratios.

```python
from skill_evolution.builtin_skills import FinancialAnalyzerSkill
result = FinancialAnalyzerSkill().execute(
    data={"income": 8000, "expenses": {"rent": 2000, "food": 500}},
    analysis_type="budget"
)
# {'net_surplus_deficit': 5500, 'savings_rate_pct': 68.75, ...}
```

Analysis types: `budget`, `credit_score`, `ratios`, `liquidity`, `solvency`

### `court_monitor`
Search court dockets by case number or party name.

```python
from skill_evolution.builtin_skills import CourtMonitorSkill
result = CourtMonitorSkill().execute(court="all", party_name="Acme")
# {'cases_found': 1, 'cases': [...], ...}
```

### `contract_reviewer`
Extracts key terms and risk flags from contract text.

```python
from skill_evolution.builtin_skills import ContractReviewerSkill
result = ContractReviewerSkill().execute(contract_text="...full contract...")
# {'parties': [...], 'risk_flags': [{'flag': 'Unlimited Liability', 'severity': 'high'}], ...}
```

### `deadline_calculator`
Computes legal deadlines with weekend/holiday adjustment.

```python
from skill_evolution.builtin_skills import DeadlineCalculatorSkill
result = DeadlineCalculatorSkill().execute(filing_date="2024-03-01", deadline_type="response")
# {'deadline_date': '2024-03-28', 'days_remaining_from_today': 45, 'status': 'future'}
```

Deadline types: `response`, `appeal`, `discovery_close`, `statute_of_limitations_personal_injury`, and 8 more.

---

## How to Write Custom Skills

Every skill is a Python snippet that sets a `result` variable. Parameters are available via `params` dict.

### Simple example

```python
# skill code (stored as string in SkillLibrary)
amount = float(params.get('amount', 0))
tax_rate = float(params.get('tax_rate', 0.085))
tax = amount * tax_rate
result = {
    'amount': amount,
    'tax': round(tax, 2),
    'total': round(amount + tax, 2),
}
```

### Register and run

```python
from skill_evolution import SkillLibrary, SkillRunner
from skill_evolution.skill_types import Skill, SkillCategory

library = SkillLibrary()
runner = SkillRunner(library)

skill = Skill(
    name="tax_calculator",
    description="Calculates sales tax on an amount.",
    category=SkillCategory.FINANCIAL,
    code=my_skill_code,
    parameters={
        "amount": {"type": "float", "required": True},
        "tax_rate": {"type": "float", "required": False, "default": 0.085},
    },
    author="your_name",
    tags=["finance", "tax"],
)

library.register(skill)
execution = runner.execute(skill.id, {"amount": 1000})
print(execution.output)  # {'amount': 1000.0, 'tax': 85.0, 'total': 1085.0}
```

### Inherit from SkillTemplate

For built-in skills, inherit from `SkillTemplate` for structured parameter validation:

```python
from skill_evolution.skill_types import SkillTemplate, SkillCategory

class MyCustomSkill(SkillTemplate):
    @property
    def skill_id(self): return "custom_my_skill"
    @property
    def name(self): return "my_custom_skill"
    @property
    def description(self): return "Does something useful."
    @property
    def category(self): return SkillCategory.AUTOMATION

    @property
    def parameter_schema(self):
        return {"input": {"type": "str", "required": True}}

    def execute(self, **kwargs):
        data = kwargs["input"]
        return {"processed": data.upper(), "success": True}
```

---

## Marketplace (OpenClaw-Inspired)

The marketplace enables community skill sharing:

```python
from skill_evolution import SkillMarketplace, SkillLibrary

library = SkillLibrary()
market = SkillMarketplace(library)

# Publish your skill
ms = market.publish("my_skill_id", author_info={"name": "Alice", "org": "IKE Solutions"})

# Browse community skills
skills = market.browse(min_rating=4.0)

# See what's trending
trending = market.get_trending(limit=5)

# Community top 10 (like OpenClaw's hottest skills)
top10 = market.community_top_10()

# Install a community skill
installed = market.install(ms.marketplace_id)

# Rate a skill
market.rate(ms.marketplace_id, score=5.0, feedback="Works perfectly!")
```

---

## Comparison: Hermes Agent vs. SintraPrime Skill Evolution

| Feature | Hermes Agent | SintraPrime Skill Evolution |
|---|---|---|
| Skill Storage | In-memory procedural memory | SQLite, persistent + versioned |
| Skill Creation | From task outcomes | From tasks, examples, workflows, patterns |
| Self-Improvement | LLM-guided rewriting | Pattern-based + LLM-optional |
| Community Skills | No | Yes, marketplace with ratings |
| Sandbox Execution | Tool-based | Restricted Python exec() sandbox |
| Failure Analysis | Basic | 7-pattern error classification |
| Background Learning | Event-driven | Thread-based watcher (configurable interval) |
| Role Specialization | No | Yes, via SkillCategory |

---

## Comparison: OpenClaw vs. SintraPrime Skill Marketplace

| Feature | OpenClaw | SintraPrime Marketplace |
|---|---|---|
| Skill Discovery | Web UI + API | browse(), search(), get_trending() |
| Community Rating | Star ratings | 1-5 stars + text feedback |
| Trending List | Hottest skills | community_top_10(), get_trending() |
| Installation | Clone/install | install(marketplace_id) |
| Storage Backend | Cloud registry | Local JSON + optional GitHub Gists |
| Domain Focus | General | Legal/Financial specialization |

---

## Running Tests

```bash
cd SintraPrime-Unified
python -m pytest skill_evolution/tests/test_skill_evolution.py -v
```

Expected: **100 tests**, all passing.

---

## Quick Start

```python
from skill_evolution import SkillLibrary, SkillRunner, SkillEvolver

# Initialize
library = SkillLibrary()
runner = SkillRunner(library)
evolver = SkillEvolver(library)

# Use built-in skills
from skill_evolution.builtin_skills import LegalResearchSkill
results = LegalResearchSkill().execute(query="employment discrimination", jurisdiction="federal")

# Start continuous improvement
evolver.watch_and_evolve(interval_hours=24)

# Generate weekly report
report = evolver.evolution_report()
print(f"Skills improved this week: {report['improvements_applied']}")
```

---

*SintraPrime-Unified Skill Evolution System — Tango-3 Component*
*Inspired by Hermes Agent, OpenClaw, CrewAI, and GPT-5.5 Spud*
