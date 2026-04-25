# ClawdBot Installation Guide

**Quick link to install ClawdBot software in SintraPrime**

## What is This?

ClawdBot is a self-hosted AI assistant gateway with multi-platform chat integration. This repository now includes a complete, governance-compliant integration package.

## Quick Start

### For Operators (5 minutes)

```bash
cd clawdbot-integration
./install.sh
```

See: [`clawdbot-integration/QUICK_START.md`](./clawdbot-integration/QUICK_START.md)

### For the Full Story

- **Integration Package:** [`clawdbot-integration/`](./clawdbot-integration/)
- **Status Document:** [`CLAWDBOT_STATUS.md`](./CLAWDBOT_STATUS.md)
- **Governance Policies:** [`docs/policy/clawdbot-agent-policy-snippets.v1.md`](./docs/policy/clawdbot-agent-policy-snippets.v1.md)

## What's Included

The integration package in `/clawdbot-integration/` contains:

### Documentation
- **README.md** - Complete integration guide (9KB)
- **QUICK_START.md** - 5-minute setup guide (9KB)
- **GOVERNANCE_COMPLIANCE.md** - Compliance checklist (10KB)
- **SKILLS_CONFIG.md** - Skills configuration guide (10KB)
- **MONITORING_INTEGRATION.md** - Make.com integration (13KB)

### Configuration
- **.env.example** - Environment template with all variables
- **package.json** - npm scripts for ClawdBot commands
- **install.sh** - Automated installation with governance checks

## Three Laws of ClawdBot Governance

Before installing, understand these principles:

1. **Isolation** - Run on dedicated machine/VPS, NOT your daily computer
2. **Least Privilege** - Use service accounts with minimal scopes
3. **Execute Requires Consent** - Receipts and approval for all actions

## Installation Options

### Option 1: Guided Installation (Recommended)
```bash
cd clawdbot-integration && ./install.sh
```

### Option 2: Global Installation
```bash
npm install -g clawdbot
cd clawdbot-integration
cp .env.example ~/.clawdbot/.env
# Edit .env with your keys
clawdbot onboard --install-daemon
```

### Option 3: Local Installation
```bash
cd clawdbot-integration
npm install clawdbot
cp .env.example .env
# Edit .env with your keys
npx clawdbot onboard
```

## Prerequisites

- Node.js 22+
- Dedicated machine or VPS (policy requirement)
- API keys from service accounts (NOT personal)
- Anthropic Claude or OpenAI API access

## Next Steps After Installation

1. **Test in Research Mode** (48 hours minimum)
2. **Set up monitoring** (Make.com integration)
3. **Configure skills** (read-only first)
4. **Review logs** (ensure governance compliance)
5. **Only then enable Execute Mode** (with receipts)

## Documentation Map

```
clawdbot-integration/
├── QUICK_START.md              # Start here (5-minute setup)
├── README.md                    # Complete integration guide
├── GOVERNANCE_COMPLIANCE.md     # Compliance checklist (mandatory)
├── SKILLS_CONFIG.md             # Skills setup and configuration
├── MONITORING_INTEGRATION.md    # Make.com monitoring setup
├── install.sh                   # Automated installer
├── .env.example                 # Configuration template
└── package.json                 # npm scripts

docs/
├── policy/
│   └── clawdbot-agent-policy-snippets.v1.md  # 14 governance policies
└── external-notes/
    └── clawdbot-pattern-brief.v1.md          # Architecture patterns

CLAWDBOT_STATUS.md              # Current status and overview
```

## Support

- **Installation Issues:** See `clawdbot-integration/QUICK_START.md` troubleshooting
- **Governance Questions:** See `docs/policy/clawdbot-agent-policy-snippets.v1.md`
- **Integration Help:** See `clawdbot-integration/README.md`
- **Official Docs:** https://getclawdbot.org/docs/

## Important Warnings

⚠️ **DO NOT install on your primary computer** (Policy SP-AGENT-ENV-001)  
⚠️ **DO NOT use personal accounts** (Policy SP-AGENT-ACCT-002)  
⚠️ **DO NOT enable Execute Mode without receipts** (Policy SP-AGENT-EXEC-004)  
⚠️ **DO start in Research Mode** (Policy SP-AGENT-MODE-003)

## Status

- ✅ Integration package complete
- ✅ Governance policies defined
- ✅ Installation scripts ready
- ✅ Monitoring integration designed
- ⏳ ClawdBot software installation (awaits operator)

---

**For the full story, see:** [`CLAWDBOT_STATUS.md`](./CLAWDBOT_STATUS.md)  
**To get started now, see:** [`clawdbot-integration/QUICK_START.md`](./clawdbot-integration/QUICK_START.md)
