# SintraPrime Airlock Server

Production-ready HMAC-verified gateway between portal automation scripts and Make.com workflows. Part of the "ManusLite" stack that replaces paid Manus credits with owned infrastructure.

## Quick Start

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure environment (copy `.env.example` to `.env`):
   ```bash
   cp .env.example .env
   # Edit .env with your secrets and webhook URL
   ```

3. Start the server:
   ```bash
   npm start
   ```

4. Test health check:
   ```bash
   curl http://localhost:3000/health
   ```

## Architecture

```
┌─────────────┐      HMAC-verified      ┌──────────┐      HMAC-verified      ┌──────────┐
│   Portal    │────────────────────────>│ Airlock  │────────────────────────>│ Make.com │
│ Automation  │     + File Payload      │  Server  │    Sanitized Receipt    │ Scenario │
└─────────────┘                         └──────────┘                         └──────────┘
                                             │
                                             │ Temp File Storage
                                             ↓
                                        ┌──────────┐
                                        │  Files   │←────── Make downloads
                                        │ /tmp/*   │        via /files/:id/:name
                                        └──────────┘
```

## Features

- ✅ **HMAC Signature Verification** - Validates sender authenticity
- ✅ **Payload Validation** - Checks structure, file hashes (SHA-256), size limits
- ✅ **Security Guardrails** - Requires `no_submit_pay: true` flag
- ✅ **Temporary File Storage** - Files available for Make.com to download
- ✅ **Receipt Sanitization** - Strips base64 data before forwarding
- ✅ **Health Check Endpoint** - `/health` for monitoring
- ✅ **CORS Support** - Configurable origin filtering
- ✅ **Size Limits** - Max 10MB payload (configurable)

## Endpoints

### `POST /manus/webhook`
Main webhook endpoint for receiving payloads from automation scripts.

**Headers:**
- `x-manus-timestamp` - Unix timestamp (seconds)
- `x-manus-signature` - HMAC-SHA256(`${timestamp}.${json_body}`)

**Payload:**
```json
{
  "task_id": "TASK-123",
  "task_title": "My Task",
  "portal": "court_portal",
  "no_submit_pay": true,
  "files": [
    {
      "name": "document.pdf",
      "mime": "application/pdf",
      "bytes": 12345,
      "sha256": "a1b2c3...",
      "data_b64": "base64-encoded-data"
    }
  ]
}
```

### `GET /health`
Health check endpoint for Render and monitoring tools.

**Response:**
```json
{
  "status": "healthy",
  "service": "sintraprime-airlock",
  "version": "1.1.0",
  "timestamp": "2026-01-27T12:00:00.000Z"
}
```

### `GET /files/:task_id/:filename`
File download endpoint for Make.com to retrieve uploaded files.

### `GET /dev/files` (Dev Only)
Lists all stored files by task ID. Only enabled when `ALLOW_DEV_ROUTES=true`.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MANUS_SHARED_SECRET` | ✅ | - | HMAC signing secret (shared with sender) |
| `MAKE_WEBHOOK_URL` | ✅ | - | Make.com webhook URL |
| `AIRLOCK_SHARED_SECRET` | ✅ | - | Secondary HMAC secret for Airlock→Make |
| `PORT` | ❌ | `3000` | Server port |
| `ACCEPT_ORIGIN` | ❌ | `*` | CORS origin filter |
| `MAX_BODY_BYTES` | ❌ | `10485760` | Max payload size (10MB) |
| `ALLOW_DEV_ROUTES` | ❌ | `false` | Enable `/dev/*` endpoints |

## Deployment

See comprehensive deployment guide: [docs/AIRLOCK_DEPLOYMENT.md](../docs/AIRLOCK_DEPLOYMENT.md)

**Quick steps:**
1. Deploy to Render.com
2. Set environment variables
3. Configure Make.com scenario (see [docs/MAKE_SCENARIO_SETUP.md](../docs/MAKE_SCENARIO_SETUP.md))
4. Test with `scripts/send_to_airlock.mjs`

## Testing

Use the test script to send sample PDFs:

```bash
export AIRLOCK_URL=https://your-airlock.onrender.com
export MANUS_SHARED_SECRET=your-secret
node ../scripts/send_to_airlock.mjs ./test-pdfs
```

## Security

- **HMAC Verification** - All requests must have valid signatures
- **Timestamp Validation** - Requests older than 5 minutes are rejected
- **File Hash Validation** - SHA-256 hashes verified on upload
- **Size Limits** - Max 10 files, max 10MB total payload
- **no_submit_pay Guardrail** - Must be explicitly set to `true`

## Development

Run in watch mode:
```bash
npm run dev
```

Enable dev routes for debugging:
```bash
ALLOW_DEV_ROUTES=true npm run dev
```

## Support

For issues or questions:
1. Check [AIRLOCK_DEPLOYMENT.md](../docs/AIRLOCK_DEPLOYMENT.md) troubleshooting section
2. Review server logs
3. Test with `send_to_airlock.mjs`
4. Open GitHub issue

---

**Version**: 1.1.0  
**Node.js**: >=18  
**License**: Part of SintraPrime
