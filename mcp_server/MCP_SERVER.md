# SintraPrime MCP Server

> **The most capable MCP server for legal and financial AI** — connecting Claude, Cursor, ChatGPT, and any MCP-compatible tool to SintraPrime's full legal, financial, and research capabilities.

[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen)](https://python.org)
[![Tools](https://img.shields.io/badge/Tools-24-orange)](./sintra_tools.py)
[![Resources](https://img.shields.io/badge/Resources-11-purple)](./sintra_resources.py)
[![Prompts](https://img.shields.io/badge/Prompts-6-red)](./sintra_prompts.py)

---

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard (launched by Anthropic in 2024) that lets AI assistants like Claude connect to external tools, data sources, and workflows. Think of it as a universal plug for AI capabilities.

By 2026, MCP has become the dominant standard for AI tool integration — with thousands of MCP servers covering every domain. SintraPrime's MCP server is **the definitive server for legal and financial professionals**.

---

## Why SintraPrime MCP?

| Feature | SintraPrime MCP | Generic MCP Servers |
|---------|----------------|---------------------|
| Legal research tools | ✅ 7 tools | ❌ None |
| Financial analysis | ✅ 5 tools | ❌ None |
| Document drafting | ✅ Jurisdiction-aware | ❌ None |
| Trust law analysis | ✅ Comprehensive | ❌ None |
| Prompt templates | ✅ 6 legal/financial | ❌ Generic |
| Resources (data) | ✅ 11 data sources | ❌ None |
| Agent scheduling | ✅ Yes | ❌ None |

---

## Quick Start

### Connect Claude Desktop

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/ihoward40/SintraPrime-Unified.git
   cd SintraPrime-Unified
   ```

2. **Auto-install** (recommended):
   ```bash
   python -m mcp_server.mcp_config install
   ```

3. **Or manually** — copy `claude_desktop_config.json` to:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`
   
   Update `cwd` to your actual installation path.

4. **Restart Claude Desktop**

5. **Verify** — look for the 🔨 (hammer) icon in Claude Desktop. Click it to see 24 SintraPrime tools.

---

### Connect Cursor IDE

1. Create `.cursor/mcp.json` in your project root:
   ```bash
   python -m mcp_server.mcp_config show cursor > .cursor/mcp.json
   ```

2. Update the `cwd` path in `.cursor/mcp.json`

3. Restart Cursor — SintraPrime tools appear in the AI panel

---

### Connect VS Code

1. Generate VS Code config:
   ```bash
   python -m mcp_server.mcp_config show vscode
   ```

2. Merge the output into `.vscode/settings.json`

3. Install the VS Code MCP extension and restart

---

### Run Server Manually (Testing)

```bash
# Start in stdio mode (standard MCP mode)
python -m mcp_server

# Start HTTP mode (remote access)
python -c "
from mcp_server.mcp_transport import HTTPTransport
from mcp_server.mcp_server import SintraMCPServer
import asyncio
server = SintraMCPServer(transport=HTTPTransport(port=8765))
asyncio.run(server.start_async())
"
```

---

## Available Tools (24 Total)

### 🏛️ Legal Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `legal_research` | Search case law + statutes across federal and state databases | `query`, `jurisdiction` |
| `analyze_contract` | Extract key terms, risks, and obligations from any contract | `contract_text` |
| `draft_document` | Generate NDA, LLC agreements, trusts, and any legal document | `doc_type`, `parties`, `terms` |
| `check_statute` | Look up statute text and annotations by citation | `statute_citation` |
| `find_precedent` | Find relevant case law for a legal issue | `legal_issue`, `jurisdiction` |
| `calculate_deadline` | Compute statutes of limitations, appeal deadlines, etc. | `event`, `deadline_type`, `jurisdiction` |
| `trust_analysis` | Full trust law analysis with tax implications | `trust_document_text` |

**Example — Legal Research:**
```json
{
  "name": "legal_research",
  "arguments": {
    "query": "breach of fiduciary duty LLC manager",
    "jurisdiction": "Delaware"
  }
}
```

---

### 💰 Financial Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `credit_analysis` | Creditworthiness assessment with DTI, borrowing capacity | `financial_data` |
| `budget_optimizer` | Financial planning with 50/30/20 analysis and goal tracking | `income`, `expenses`, `goals` |
| `business_entity_advisor` | LLC vs S-Corp vs C-Corp recommendation by state | `goals`, `state` |
| `tax_strategy` | Tax optimization including QBI, Augusta Rule, depreciation | `income`, `expenses`, `situation` |
| `funding_sources` | SBA loans, grants, revenue-based financing options | `business_type`, `stage`, `amount` |

**Example — Tax Strategy:**
```json
{
  "name": "tax_strategy",
  "arguments": {
    "income": 250000,
    "expenses": {"office": 15000, "software": 5000},
    "situation": "LLC consulting business, married filing jointly"
  }
}
```

---

### 🔍 Research Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `web_research` | Autonomous multi-depth web research with synthesis | `query`, `depth` |
| `case_law_search` | Legal database search by court and date range | `query`, `court`, `date_range` |
| `regulatory_lookup` | Federal/state regulations by agency and topic | `agency`, `topic` |
| `news_monitor` | Legal and financial news monitoring | `topics`, `since_date` |

---

### 📄 Document Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `generate_report` | Structured reports in markdown, HTML, or text | `topic`, `format`, `data` |
| `summarize_document` | Document summarization with compression ratio | `text`, `max_length` |
| `extract_entities` | Extract names, dates, amounts, legal citations | `text` |
| `compare_documents` | Side-by-side document comparison with diff analysis | `doc1`, `doc2` |

---

### 🤖 Agent Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `schedule_task` | Schedule autonomous background tasks | `description`, `when` |
| `get_task_status` | Check task progress and status | `task_id` |
| `recall_memory` | Semantic search across agent memory | `query`, `user_id` |
| `execute_skill` | Run a skill from the SintraPrime skill library | `skill_name`, `params` |

---

## Available Resources (11 Total)

Resources are data sources AI clients can read as context:

| URI | Description |
|-----|-------------|
| `sintra://legal/statutes/federal` | Federal statute database |
| `sintra://legal/statutes/{jurisdiction}` | State statute database |
| `sintra://legal/cases/{citation}` | Case law by citation |
| `sintra://templates/nda` | NDA template |
| `sintra://templates/llc_operating_agreement` | LLC agreement template |
| `sintra://templates/trust` | Revocable living trust template |
| `sintra://templates/{doc_type}` | Any document template |
| `sintra://skills/{skill_name}` | Skill definitions |
| `sintra://memory/{user_id}/recent` | Recent agent memories |
| `sintra://tasks/active` | Active scheduled tasks |
| `sintra://reports/{report_id}` | Generated reports |

**Example — Reading a Resource:**
```
Read sintra://templates/nda
→ Returns NDA template with variable placeholders
```

---

## Prompt Templates (6 Total)

Prompts are reusable conversation starters optimized for SintraPrime workflows:

### `legal_intake`
Full client intake questionnaire for any legal matter.

**Arguments:** `client_name`, `matter_type`, `jurisdiction`

### `contract_review`
Systematic 6-phase contract review protocol.

**Arguments:** `contract_type`, `client_role`, `priority`

### `trust_setup_consultation`
Complete trust planning consultation with tax analysis.

**Arguments:** `client_name`, `estate_size`, `family_situation`

### `financial_planning`
6-module comprehensive financial planning session.

**Arguments:** `client_name`, `life_stage`, `primary_goal`

### `case_strategy`
5-phase litigation strategy from assessment to trial.

**Arguments:** `case_type`, `client_position`, `jurisdiction`

### `regulatory_compliance`
Full compliance audit across federal and state regulations.

**Arguments:** `industry`, `business_size`, `jurisdictions`

---

## Adding Custom Tools

```python
from mcp_server.mcp_server import SintraMCPServer
from mcp_server.mcp_types import MCPTool, ToolResult

server = SintraMCPServer()

# Define your tool
my_tool = MCPTool(
    name="my_custom_tool",
    description="Does something amazing",
    input_schema={
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Your input"}
        },
        "required": ["input"]
    },
    handler_fn=lambda input: ToolResult.text(f"Processed: {input}")
)

# Register it
server.register_tool(my_tool)

# Start the server
server.start()
```

---

## Architecture

```
mcp_server/
├── __init__.py           # Package exports
├── mcp_server.py         # Core server (JSON-RPC dispatch)
├── mcp_types.py          # Protocol type definitions
├── mcp_transport.py      # Stdio / HTTP / WebSocket transports
├── mcp_config.py         # Config generation + installation
├── sintra_tools.py       # 24 SintraPrime tools
├── sintra_resources.py   # 11 data resources
├── sintra_prompts.py     # 6 prompt templates
├── claude_desktop_config.json  # Ready-to-use config
└── tests/
    └── test_mcp_server.py  # 66-test suite
```

### Transport Options

| Transport | Best For | Port |
|-----------|---------|------|
| `StdioTransport` | Claude Desktop, Cursor (default) | stdio |
| `HTTPTransport` | Remote access, APIs | 8765 |
| `WebSocketTransport` | Browser clients, real-time | 8766 |

---

## Validation

```bash
# Check if properly installed
python -m mcp_server.mcp_config validate

# Run tests
pytest mcp_server/tests/ -v

# Show all configs
python -m mcp_server.mcp_config show all
```

---

## Comparison: SintraPrime vs. Other Legal AI MCP Servers

| Capability | SintraPrime | Harvey AI | Lexis+ AI | Westlaw AI |
|-----------|-------------|-----------|-----------|------------|
| MCP Integration | ✅ Full | ❌ None | ❌ None | ❌ None |
| Trust Law | ✅ | ✅ | ✅ | ✅ |
| Financial Planning | ✅ | ❌ | ❌ | ❌ |
| Agent Scheduling | ✅ | ❌ | ❌ | ❌ |
| Open Source | ✅ | ❌ | ❌ | ❌ |
| Claude Desktop | ✅ | ❌ | ❌ | ❌ |
| Cursor Support | ✅ | ❌ | ❌ | ❌ |
| Custom Tools | ✅ | ❌ | ❌ | ❌ |

**SintraPrime is the only MCP server combining legal research, financial planning, document drafting, and autonomous agent capabilities in a single open-source package.**

---

## Support

- **GitHub Issues**: [github.com/ihoward40/SintraPrime-Unified/issues](https://github.com/ihoward40/SintraPrime-Unified/issues)
- **Website**: [ikesolutions.org](https://ikesolutions.org)
- **MCP Specification**: [modelcontextprotocol.io](https://modelcontextprotocol.io)

---

*SintraPrime MCP Server v1.0.0 — Built for the 2026 AI ecosystem*
