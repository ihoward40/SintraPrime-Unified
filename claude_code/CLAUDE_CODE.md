# Claude Code Integration for SintraPrime

## Overview

SintraPrime's Claude Code integration brings AI-powered code generation, analysis, and legal
automation to the platform. Using Anthropic's Claude Opus model, this module enables:

- **Code Generation**: Create legal automation scripts from natural language
- **Code Analysis**: Detect bugs, security issues, and improvements
- **Legal Compliance Review**: Jurisdiction-specific code compliance checking
- **API Integration Generation**: Auto-generate integrations for any external service
- **Module Scaffolding**: Generate complete SintraPrime modules on demand

---

## Installation

```bash
pip install anthropic
export ANTHROPIC_API_KEY=your_key_here
```

---

## Quick Start

```python
import asyncio
from claude_code import ClaudeCodeEngine, LegalCodeAssistant, CodeGenerator

async def main():
    engine = ClaudeCodeEngine()
    
    # Generate a legal automation script
    result = await engine.generate_legal_script(
        "Create a script that parses California trust documents and extracts beneficiaries"
    )
    print(result["code"])
    
    # Analyze existing code
    analysis = await engine.analyze_code(your_code, "python")
    print(analysis["analysis"])
    
    # Debug an error
    fix = await engine.debug(broken_code, "AttributeError: 'NoneType' has no attribute 'name'")
    print(fix["debug_result"])

asyncio.run(main())
```

---

## ClaudeCodeEngine

The core engine for general-purpose code intelligence.

### Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `analyze_code(code, language)` | Analyze for bugs, security, improvements | `dict` |
| `generate_legal_script(description)` | Generate script from natural language | `dict` |
| `debug(code, error)` | Debug code given an error message | `dict` |
| `generate_api_integration(api_docs, task)` | Generate API integration code | `str` |
| `review_legal_automation(code)` | Review for correctness and compliance | `dict` |
| `explain_code(code)` | Plain English explanation for lawyers | `str` |

---

## LegalCodeAssistant

Specialized tools for legal document processing and automation.

### Methods

| Method | Description |
|--------|-------------|
| `generate_trust_parser(sample_document)` | Generate parser for trust document format |
| `generate_contract_analyzer(contract_type)` | Build contract analysis tool (NDA, LLC, Trust, etc.) |
| `generate_court_filing_script(jurisdiction, filing_type)` | Automate court document preparation |
| `explain_legal_code(code)` | Attorney-friendly code explanation |
| `code_review_for_compliance(code, jurisdiction)` | Jurisdiction-specific compliance review |
| `generate_trust_accounting_script(trust_type)` | Financial calculation scripts |

### Supported Contract Types
`NDA`, `LLC`, `Trust`, `Lease`, `Employment`, `Partnership`, `Service`

### Example: Generate a Trust Parser

```python
assistant = LegalCodeAssistant()

with open("sample_trust.pdf") as f:
    sample = f.read()

parser_code = await assistant.generate_trust_parser(sample)
# Returns complete Python class ready to use
```

---

## CodeGenerator

Generate complete SintraPrime modules from plain English descriptions.

### Methods

| Method | Description |
|--------|-------------|
| `generate_module(description)` | Generate complete module with tests |
| `generate_integration(service, task)` | Integration with external service |
| `generate_test_suite(module_code)` | Auto-generate comprehensive tests |
| `scaffold_fastapi_endpoint(resource, operations)` | Generate FastAPI router |

### Example: Generate a New Module

```python
generator = CodeGenerator()

result = await generator.generate_module(
    "Add a module to track all my UCC financing statements, "
    "including debtor info, secured party, collateral description, and filing dates"
)

# Write generated files
for filename, content in result["files"].items():
    with open(f"modules/{filename}", "w") as f:
        f.write(content)

print("Integration steps:")
for step in result["integration_steps"]:
    print(f"  - {step}")
```

---

## Running Tests

```bash
cd SintraPrime-Unified/
pytest claude_code/tests/ -v --asyncio-mode=auto
```

Expected output: 22+ tests passing, all mocked (no API calls).

---

## Architecture

```
claude_code/
├── __init__.py              # Package exports
├── engine.py                # Core ClaudeCodeEngine
├── legal_code_assistant.py  # Legal-specific assistant
├── code_generator.py        # Module/integration generator
├── tests/
│   ├── __init__.py
│   └── test_claude_code.py  # 22+ tests (all mocked)
└── CLAUDE_CODE.md           # This file
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Required |

---

## Model Configuration

All engines use `claude-opus-4-5` by default. To use a different model:

```python
engine = ClaudeCodeEngine()
engine.model = "claude-opus-4-5"  # or claude-3-5-sonnet-20241022 for faster/cheaper
```

---

## Legal Disclaimer

Code generated by Claude Code is for assistance purposes only. All legal automation code
must be reviewed by a licensed attorney before use in production legal matters. SintraPrime
and Ike Solutions LLC are not responsible for errors in generated legal code.
