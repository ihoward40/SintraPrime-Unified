# SintraPrime Local Setup Instructions

## 🎯 Quick Start

Your SintraPrime installation has been configured with Make.com webhooks. Follow these steps to sync the configuration to your local machine at `C:/SintraPrime`.

---

## Step 1: Pull Latest Changes from GitHub

```bash
cd C:/SintraPrime
git pull origin master
```

This will download the new `WEBHOOK_CONFIGURATION.md` file with all webhook details.

---

## Step 2: Create Your Local `.env` File

Copy the `.env` file from this sandbox to your local machine:

### Option A: Manual Creation

Create `C:/SintraPrime/.env` with the following content:

```env
# SintraPrime Configuration
# Generated: February 13, 2026
# Make.com Webhook Integration

# Required for calling agents (webhook transport)
WEBHOOK_SECRET=your-webhook-secret-here

# Optional default webhook URL for sendMessage
WEBHOOK_URL=https://hook.us2.make.com/45bj82b9p6dw1wf211csn8iac7v7oxv9

# Recommended: separate agent endpoints
VALIDATION_WEBHOOK_URL=https://hook.us2.make.com/45bj82b9p6dw1wf211csn8iac7v7oxv9
PLANNER_WEBHOOK_URL=https://hook.us2.make.com/f5ccavrcs37t6any12dvvo1rhv4iwyvd
EXECUTOR_WEBHOOK_URL=https://hook.us2.make.com/ie54bdnpbztxhed5f1iuysvvanlum4u8

# Optional: persistence webhook
NOTION_RUNS_WEBHOOK=https://hook.us2.make.com/chae31714qi31ve3xw4l506fb1kpzgkl

# Optional: when set to 1, always append local receipts even if NOTION_RUNS_WEBHOOK is set
PERSIST_LOCAL_RECEIPTS=0

# Optional: tag receipts / audit records
PLAN_VERSION=ExecutionPlan@1

# Executor tuning
DEFAULT_STEP_TIMEOUT_MS=30000

### Tier-8 Autonomy
# OFF | READ_ONLY_AUTONOMY | PROPOSE_ONLY_AUTONOMY | APPROVAL_GATED_AUTONOMY
AUTONOMY_MODE=OFF

### Tier-8 Budgets (policy-enforced)
POLICY_MAX_STEPS=10
POLICY_MAX_RUNTIME_MS=30000
POLICY_MAX_RUNS_PER_DAY=50

### Autonomy runner state dir
AUTONOMY_STATE_DIR=runs/autonomy/state

### Tier-10.1 Live Notion Read (Read-only)
NOTION_API_BASE=https://api.notion.com
NOTION_API_VERSION=2022-06-28
NOTION_TOKEN=

# Keys to redact before artifacts (case-insensitive)
NOTION_REDACT_KEYS=title,name,email,phone,address,ssn,tin

### Tier-10.2 Live Notion Write (Approval-gated)
NOTION_LIVE_APPROVE_RECHECK=1

# Tier-22.2 — Probation success thresholds
PROBATION_SUCCESS_REQUIRED=3
PROBATION_WINDOW_HOURS=24

# Tier-∞.1 — Requalification Governor
REQUALIFY_TOKENS_PER_HOUR=2
REQUALIFY_MAX_CONCURRENT=1

# Tier-∞.1.1 — Activation governor
ACTIVATE_TOKENS_PER_HOUR=1
ACTIVATE_MAX_CONCURRENT=1

# Tier-23 — Confidence decay
CONFIDENCE_DECAY_HOURS=72
CONFIDENCE_MIN_SUCCESS=1

### Credit Monitoring System
NOTION_RUNS_LEDGER_DB_ID=
NOTION_CASES_DB_ID=

# Slack webhooks for alerts
SLACK_WEBHOOK_URL_SEV0=
SLACK_WEBHOOK_URL_SEV1=
SLACK_WEBHOOK_URL_DEFAULT=

# Baselines storage path
CREDIT_BASELINES_PATH=./config/credit-baselines.json

### Speech sinks
SPEECH_SINKS=console

### ElevenLabs (optional)
ELEVEN_API_KEY=YOUR_ELEVENLABS_KEY_HERE
ELEVEN_VOICE_DEFAULT=
ELEVEN_VOICE_DRAGON=
ELEVEN_VOICE_ANDROID=
ELEVEN_VOICE_JUDGE=
ELEVEN_VOICE_ORACLE=
ELEVEN_VOICE_WARRIOR=
ELEVEN_VOICE_NARRATOR=
ELEVEN_VOICE_PROSECUTOR=
ELEVEN_VOICE_SAGE=
ELEVEN_OUTPUT_DIR=runs/speech-elevenlabs
ELEVEN_AUTO_PLAY=0
ELEVEN_MODEL_ID=eleven_multilingual_v2
ELEVEN_STABILITY=0.5
ELEVEN_SIMILARITY_BOOST=0.5
ELEVEN_USE_SPEAKER_BOOST=1

### Kimi AI (Moonshot AI) Configuration
KIMI_API_KEY=your_moonshot_api_key_here
KIMI_API_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-32k
KIMI_MAX_TOKENS=4000
KIMI_TEMPERATURE=0.7
```

### Option B: Download from Sandbox

The `.env` file is available at:
- Sandbox path: `/home/ubuntu/SintraPrime/.env`
- Download it and place it at: `C:/SintraPrime/.env`

---

## Step 3: Generate Webhook Secret

Generate a secure webhook secret:

```bash
# On Windows (PowerShell)
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)

# Or use Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

Update the `WEBHOOK_SECRET` in your `.env` file with the generated value.

---

## Step 4: Install Dependencies

```bash
cd C:/SintraPrime
npm install
```

---

## Step 5: Test the Configuration

```bash
# Test that webhooks are accessible
npm test

# Or manually test a webhook
curl -X POST "https://hook.us2.make.com/45bj82b9p6dw1wf211csn8iac7v7oxv9" \
  -H "Content-Type: application/json" \
  -d '{"test": true, "message": "SintraPrime test"}'
```

Expected response:
```json
{"success": true, "scenario": "validator"}
```

---

## Step 6: Run SintraPrime

```bash
cd C:/SintraPrime
npm start
```

---

## 📋 Webhook URLs Summary

| Purpose | URL |
|---------|-----|
| Validator | `https://hook.us2.make.com/45bj82b9p6dw1wf211csn8iac7v7oxv9` |
| Planner | `https://hook.us2.make.com/f5ccavrcs37t6any12dvvo1rhv4iwyvd` |
| Executor | `https://hook.us2.make.com/ie54bdnpbztxhed5f1iuysvvanlum4u8` |
| Notion Logs | `https://hook.us2.make.com/chae31714qi31ve3xw4l506fb1kpzgkl` |

---

## 🔒 Security Checklist

- [x] Webhooks created and tested
- [x] `.env` file created (not committed to git)
- [ ] `WEBHOOK_SECRET` generated and set
- [ ] `NOTION_TOKEN` configured (if using Notion)
- [ ] Webhook URLs kept private
- [ ] `.env` file backed up securely

---

## 🐛 Troubleshooting

### Webhooks not responding
- Check that Make.com scenarios are active
- Verify webhook URLs are correct in `.env`
- Test webhooks directly with curl

### Authentication errors
- Ensure `WEBHOOK_SECRET` is set
- Verify `NOTION_TOKEN` if using Notion integration

### Module not found errors
- Run `npm install` to install dependencies
- Check Node.js version (requires Node 16+)

---

## 📚 Additional Resources

- [WEBHOOK_CONFIGURATION.md](./WEBHOOK_CONFIGURATION.md) - Detailed webhook documentation
- [README.md](./README.md) - SintraPrime overview
- [QUICK_START.md](./QUICK_START.md) - Quick start guide

---

**Setup Date**: February 13, 2026  
**Status**: Ready for Local Deployment  
**Next Steps**: Pull changes, create `.env`, and test
