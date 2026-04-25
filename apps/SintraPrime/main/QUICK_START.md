# SintraPrime - Quick Start Guide

Get up and running with SintraPrime in 5 minutes!

## Prerequisites

- Node.js v20 or later
- npm v10 or later
- Git

## Installation

```bash
# Clone the repository
git clone https://github.com/ihoward40/SintraPrime.git
cd SintraPrime

# Install dependencies
npm install

# Build the project
npm run build
```

## Configuration

1. **Create environment file:**

```bash
cp .env.example .env
```

2. **Generate encryption key:**

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

3. **Edit `.env` and add your credentials:**

```env
# Required
SINTRAPRIME_ENCRYPTION_KEY=<your-64-char-hex-key>

# Optional (add as needed)
OPENAI_API_KEY=<your-openai-key>
SHOPIFY_SHOP=<your-store>.myshopify.com
SHOPIFY_ACCESS_TOKEN=<your-shopify-token>
META_ADS_ACCESS_TOKEN=<your-meta-token>
META_ADS_AD_ACCOUNT_ID=act_<your-account-id>
GOOGLE_DRIVE_ACCESS_TOKEN=<your-gdrive-token>
GMAIL_ACCESS_TOKEN=<your-gmail-token>
```

## First Run

```bash
# Run in development mode
npm run dev

# Or run the built version
npm start
```

## Test the System

### 1. Submit a Simple Task

```bash
npm run dev -- "/task submit --prompt 'Generate a daily report'"
```

### 2. Check Job Status

```bash
npm run dev -- "/jobs list"
```

### 3. View Reports

```bash
npm run dev -- "/reports daily"
```

## Next Steps

1. **Read the User Guide:** `docs/USER_GUIDE.md`
2. **Configure Connectors:** Add API credentials for the services you want to use
3. **Set Up Approvals:** Configure the approval workflow for high-risk actions
4. **Schedule Jobs:** Set up recurring tasks with the scheduler
5. **Deploy to Production:** Follow `docs/DEPLOYMENT_GUIDE.md`

## Common Issues

### "Module not found" errors

Make sure you've run `npm install` and `npm run build`.

### "Authentication failed" errors

Check that your API credentials in `.env` are correct and have the necessary permissions.

### "Permission denied" errors

Make sure the `runs` and `screenshots` directories are writable.

## Getting Help

- **Documentation:** Check the `docs/` directory
- **GitHub Issues:** https://github.com/ihoward40/SintraPrime/issues
- **Discussions:** https://github.com/ihoward40/SintraPrime/discussions

## What's Next?

- **Customize the Howard Trust Navigator:** Edit `src/agents/howardTrustNavigator.ts` with your trust details
- **Add Custom Connectors:** Create new connectors in `src/connectors/`
- **Build a Web UI:** Create a user-friendly interface for task management
- **Set Up Monitoring:** Integrate with your monitoring tools

---

**Ready to automate?** Start submitting tasks and let SintraPrime handle the rest!
