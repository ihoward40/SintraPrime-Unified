# SintraPrime Multi-Channel Messaging Hub

> **Tango-5 Module** — Unified access to SintraPrime across Telegram, Discord, Slack, WhatsApp, and custom webhooks.

---

## Overview

The SintraPrime Multi-Channel Messaging Hub (`channels/`) provides a single intelligent interface for users to interact with the SintraPrime AI agent system from any messaging platform. It is inspired by leading AI agent channel systems:

| Agent System | Channels Supported |
|---|---|
| **Manus AI** | Telegram, WhatsApp, Slack, LINE |
| **OpenClaw** | Discord, Telegram, WeChat |
| **Hermes Agent** | WeChat Work, WhatsApp Business |
| **Claude Code Channels** | Telegram, Discord (coding focus) |
| **ChatGPT Connected Apps** | Slack, Google Drive, Notion |
| **SintraPrime (this)** | Telegram, Discord, Slack, WhatsApp, Webhooks (n8n, Zapier, Make.com) |

---

## Architecture

```
ChannelHub (channel_hub.py)
├── TelegramChannel  (telegram_channel.py)
├── DiscordChannel   (discord_channel.py)
├── SlackChannel     (slack_channel.py)
├── WhatsAppChannel  (whatsapp_channel.py)
└── WebhookChannel   (webhook_channel.py)
         │
    MessageRouter (message_router.py)
         │
    FastAPI Layer (channel_api.py)
```

---

## Setup Guide

### 1. Telegram Bot

**Step 1: Create Bot**
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow prompts
3. Copy the bot token (format: `123456:ABC-DEF1234...`)

**Step 2: Configure**
```python
from channels import TelegramChannel, ChannelConfig, ChannelHub, ChannelType

config = ChannelConfig(
    token="YOUR_BOT_TOKEN",
    allowed_users=["your_telegram_user_id"],  # get via @userinfobot
    admin_users=["your_telegram_user_id"],
    max_message_length=4096,
    rate_limit_per_minute=20,
)

hub = ChannelHub()
hub.register_channel(ChannelType.TELEGRAM, config, TelegramChannel(config))
```

**Step 3: Set Webhook (production) or use Polling (dev)**
```python
# Polling (development)
await hub.start_listening()

# Webhook (production) — point Telegram to your FastAPI endpoint
# POST https://api.telegram.org/bot{TOKEN}/setWebhook
# url: https://yourserver.com/channels/webhook/telegram
```

---

### 2. Discord Bot

**Step 1: Create Application**
1. Visit [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application → Add Bot
3. Enable "Message Content Intent" in Bot settings
4. Copy Bot Token

**Step 2: Invite Bot to Server**
Generate OAuth2 URL with scopes: `bot`, `applications.commands`
Required permissions: `Send Messages`, `Read Message History`, `Create Threads`

**Step 3: Configure**
```python
from channels import DiscordChannel, ChannelConfig, ChannelType

config = ChannelConfig(
    token="YOUR_DISCORD_BOT_TOKEN",
    admin_users=["your_discord_user_id"],
)
hub.register_channel(ChannelType.DISCORD, config, DiscordChannel(config))
```

**Step 4: Register Slash Commands**
```bash
# Use Discord REST API or discord.py to register /sintra commands
# Commands: /sintra ask, /sintra research, /sintra legal, /sintra status, /sintra task
```

**Roles Required:**
| Role | Access Level |
|---|---|
| `sintra-admin` | Full access to all commands |
| `attorney` | Legal queries, research, all standard commands |
| `client` | Ask, status, task management only |

---

### 3. Slack Workspace

**Step 1: Create Slack App**
1. Visit [api.slack.com/apps](https://api.slack.com/apps) → Create New App
2. Choose "From scratch" → name it "SintraPrime"

**Step 2: Configure Permissions**
OAuth Scopes (Bot Token):
- `chat:write` — send messages
- `files:write` — upload documents
- `commands` — slash commands
- `app_mentions:read` — respond to @mentions

**Step 3: Enable Socket Mode** (recommended)
- Under "Socket Mode" → Enable Socket Mode
- Generate an App-Level Token (`xapp-...`)

**Step 4: Add Slash Commands**
| Command | Description |
|---|---|
| `/sintra ask` | Ask SintraPrime anything |
| `/sintra research` | Autonomous deep research |
| `/sintra legal` | Legal analysis |
| `/sintra status` | System status |
| `/sintra task` | Manage tasks |
| `/legal-question` | Quick legal query |
| `/schedule-task` | Schedule a task |

**Step 5: Configure**
```python
config = ChannelConfig(
    token="xoxb-YOUR-BOT-TOKEN",
    webhook_secret="YOUR_SIGNING_SECRET",
    extra={"app_token": "xapp-YOUR-APP-TOKEN"},
)
hub.register_channel(ChannelType.SLACK, config, SlackChannel(config))
```

---

### 4. WhatsApp Business

**Option A: Twilio (Easiest — Sandbox available)**
1. Create [Twilio account](https://www.twilio.com)
2. Enable WhatsApp Sandbox under Messaging → Try WhatsApp
3. Get Account SID and Auth Token

```python
config = ChannelConfig(
    token="YOUR_AUTH_TOKEN",
    extra={
        "account_sid": "YOUR_ACCOUNT_SID",
        "from_number": "+14155238886",  # Twilio sandbox number
    },
)
hub.register_channel(ChannelType.WHATSAPP, config, WhatsAppChannel(config, backend="twilio"))
```

**Option B: Meta WhatsApp Business Cloud API**
1. Create Meta Business account and WhatsApp Business App
2. Get Phone Number ID and permanent access token

```python
config = ChannelConfig(
    token="YOUR_META_ACCESS_TOKEN",
    extra={
        "phone_number_id": "YOUR_PHONE_NUMBER_ID",
    },
)
hub.register_channel(ChannelType.WHATSAPP, config, WhatsAppChannel(config, backend="meta"))
```

**Legal Notification Templates:**
| Template | Use Case |
|---|---|
| `case_update` | Status changes on active cases |
| `hearing_reminder` | Court date / hearing reminders |
| `document_ready` | Notify when documents are generated |
| `payment_due` | Invoice / payment reminders |

---

### 5. Webhooks (n8n, Zapier, Make.com, Custom)

```python
from channels import WebhookChannel, ChannelConfig, ChannelType

config = ChannelConfig(webhook_secret="your-hmac-secret")
wh = WebhookChannel(config)

# Register handlers
async def handle_n8n(payload):
    print("n8n triggered:", payload)

wh.register_endpoint("/hooks/n8n", handle_n8n, secret="n8n-secret")

hub.register_channel(ChannelType.WEBHOOK, config, wh)
```

**Outbound webhooks** (call external services):
```python
await wh.send(
    url="https://hooks.zapier.com/hooks/catch/12345/abcdef/",
    payload={"event": "research_complete", "result": "..."},
    sign_secret="zapier-secret",
)
```

---

## Available Commands Per Channel

### Telegram
```
/ask [question]       — Ask SintraPrime anything
/research [topic]     — Autonomous deep research
/status               — System and task status
/remind [when] [what] — Schedule a reminder
/doc [type]           — Generate a document
/help                 — Show command menu
```

### Discord Slash Commands
```
/sintra ask [question]    — Query the AI
/sintra research [topic]  — Deep research (attorney/admin only)
/sintra legal [question]  — Legal analysis (attorney/admin only)
/sintra status            — System status
/sintra task [desc]       — Manage tasks
```

### Slack
```
/sintra ask [question]     — Ask anything
/sintra research [topic]   — Deep research
/sintra legal [question]   — Legal analysis
/sintra status             — System status
/sintra task [description] — Task management
/legal-question [q]        — Direct legal query
/schedule-task [desc]      — Schedule task
```

### WhatsApp
```
"Ask: [question]"          — Question answering
"Research: [topic]"        — Research request
"Status"                   — System check
"Document: [type]"         — Generate document
```
*(Intent detection is automatic — no slash commands needed)*

---

## Using the FastAPI REST API

```bash
# Send message to Telegram
curl -X POST https://your-server.com/channels/send \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello!", "channels": ["telegram"], "recipient": "123456789"}'

# Broadcast to all channels
curl -X POST https://your-server.com/channels/broadcast \
  -d '{"text": "System maintenance in 10 minutes."}'

# Check channel status
curl https://your-server.com/channels/status
```

---

## Intent Detection

The `MessageRouter` automatically classifies incoming messages:

| Intent | Example Message | Routed To |
|---|---|---|
| `legal_question` | "Can I sue for breach of contract?" | Legal Intelligence Module |
| `research_request` | "Research antitrust law in California" | Operator Web Researcher |
| `document_request` | "Draft an NDA for our partnership" | Document Generator |
| `task_management` | "Remind me to file the brief by Friday" | Scheduler |
| `financial_query` | "What's the status of invoice #12345?" | Financial Intelligence |
| `status_check` | "Is the system running?" | System Monitor |
| `reminder` | "Remind me tomorrow at 9am" | Scheduler |
| `general_chat` | "Hello, good morning!" | General AI Response |

---

## Example Use Cases

### Ask SintraPrime a Legal Question from your Phone via Telegram

1. Open Telegram → find your SintraPrime bot
2. Type: `/ask Can my landlord terminate my lease without 30 days notice in New York?`
3. SintraPrime detects intent: `legal_question`, jurisdiction: `New York`
4. Routes to Legal Intelligence module
5. Responds with relevant statutes and analysis directly in Telegram

### Research Request via Discord

1. In your Discord server, type:
   ```
   /sintra research The impact of GDPR on US companies operating in Europe
   ```
2. SintraPrime creates a new thread: "Research: GDPR Impact"
3. Operator web researcher begins autonomous research
4. Posts a structured research report in the thread within minutes

### WhatsApp Legal Notification to Client

```python
await whatsapp.send_template(
    to="+15551234567",
    template_name="hearing_reminder",
    params=["Smith v. Jones", "March 15, 2025", "9:00 AM"],
)
```
Client receives: *"Reminder: Your hearing for case Smith v. Jones is scheduled for March 15, 2025 at 9:00 AM."*

---

## Comparison: SintraPrime vs Other AI Agent Channel Systems

| Feature | Manus AI | OpenClaw | Hermes Agent | Claude Code | **SintraPrime** |
|---|---|---|---|---|---|
| Telegram | ✅ | ✅ | ❌ | ✅ | ✅ |
| Discord | ❌ | ✅ | ❌ | ✅ | ✅ |
| Slack | ✅ | ❌ | ❌ | ❌ | ✅ |
| WhatsApp | ✅ | ❌ | ✅ | ❌ | ✅ |
| WeChat / LINE | ✅ | ✅ | ✅ | ❌ | 🔜 Planned |
| Custom Webhooks | ❌ | ❌ | ❌ | ❌ | ✅ |
| Legal Intent Routing | ❌ | ❌ | ❌ | ❌ | ✅ |
| Role-Based Access | ❌ | Partial | ✅ | ❌ | ✅ |
| Message Templates | ❌ | ❌ | ✅ | ❌ | ✅ |
| HMAC Verification | ❌ | ❌ | ❌ | ❌ | ✅ |
| Entity Extraction | ❌ | ❌ | ❌ | ❌ | ✅ |
| Multi-backend WhatsApp | ❌ | ❌ | Partial | ❌ | ✅ (Twilio+Meta) |

---

## Dependencies

```
aiohttp>=3.9.0
fastapi>=0.110.0
pydantic>=2.0.0
discord.py>=2.3.0   # optional, for Discord
slack-bolt>=1.18.0  # optional, for Slack Socket Mode
twilio>=8.0.0       # optional, for WhatsApp via Twilio
```

Install all:
```bash
pip install aiohttp fastapi pydantic discord.py slack-bolt twilio
```

---

## Running Tests

```bash
# From repository root
pytest channels/tests/test_channels.py -v

# With coverage
pytest channels/tests/test_channels.py --cov=channels --cov-report=term-missing
```

---

*SintraPrime Tango-5 — Multi-Channel Messaging Hub v1.0.0*
*IKE Solutions © 2026*
