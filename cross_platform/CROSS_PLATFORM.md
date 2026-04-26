# SintraPrime Cross-Platform Access Layer

Access SintraPrime Legal Intelligence from any device — iPhone, Android, desktop browser, or any phone with SSH.

---

## 📱 Installing SintraPrime as a PWA

### On iPhone (iOS Safari)

1. Open Safari and navigate to `https://your-sintra-server.com`
2. Tap the **Share** button (box with arrow pointing up)
3. Scroll down and tap **"Add to Home Screen"**
4. Name it **"SintraPrime"** and tap **Add**
5. The app icon appears on your home screen — tap to launch

> ℹ️ iOS PWAs work best in Safari. Chrome/Firefox on iOS cannot install PWAs.

**iOS Features Available:**
- ✅ Offline access (cached cases, deadlines)
- ✅ Push notifications (iOS 16.4+ in Safari)
- ✅ Full-screen standalone mode
- ✅ Background sync when reconnected
- ✅ IndexedDB local storage

### On Android (Chrome)

1. Open Chrome and navigate to `https://your-sintra-server.com`
2. Tap the **three-dot menu** (⋮) in the top-right
3. Tap **"Add to Home Screen"** or **"Install App"**
4. Confirm by tapping **Install**
5. Find the SintraPrime icon in your app drawer

**Android Features Available:**
- ✅ All iOS features, plus:
- ✅ Richer push notification actions
- ✅ Periodic background sync (deadline checks)
- ✅ Share target integration
- ✅ App shortcuts (long-press icon)

### Verifying Installation

The app should:
- Launch without browser chrome (no address bar)
- Show `⚖️ SintraPrime` in your app switcher
- Work when you toggle airplane mode (offline mode)

---

## 🔔 Setting Up Push Notifications

Push notifications alert you to court deadlines, new case law, and document signatures.

### Step 1: Generate VAPID Keys

```bash
cd /path/to/SintraPrime-Unified
python -c "
from cross_platform.push_notifications import VAPIDManager
mgr = VAPIDManager()
print('Public Key:', mgr.public_key)
print('Private Key:', mgr.private_key[:20], '...')
"
```

### Step 2: Update PWA Configuration

In `cross_platform/pwa/app.js`, replace the placeholder VAPID public key:

```javascript
const VAPID_PUBLIC_KEY = 'YOUR_VAPID_PUBLIC_KEY_HERE';
```

### Step 3: Start the API Gateway

```bash
cd /path/to/SintraPrime-Unified
pip install fastapi uvicorn pywebpush
uvicorn cross_platform.api_gateway:app --host 0.0.0.0 --port 8000
```

### Step 4: Enable Notifications in the PWA

1. Open SintraPrime in your browser/PWA
2. Go to **Settings** → **Push Notifications**
3. Toggle **ON** and accept the browser prompt
4. Notifications are now active

### Notification Types

| Type | When | Priority |
|------|------|----------|
| 🚨 Emergency | Time-sensitive legal matter | Critical |
| ⚖️ Court Deadline | 1 week / 72h / 24h before | High |
| 📄 Document Ready | When signature needed | High |
| 🤖 Agent Completed | AI task finished | Normal |
| 📖 Case Law Update | New relevant ruling | Normal |

### Sending Test Notifications

```python
import asyncio
from cross_platform.push_notifications import PushNotificationService
from datetime import datetime, timezone, timedelta

async def test():
    svc = PushNotificationService()
    # Send deadline reminder
    await svc.send_deadline_reminder(
        user_id="your_user_id",
        case_name="Smith v. Jones",
        deadline_title="Motion to Dismiss",
        deadline_date=datetime.now(timezone.utc) + timedelta(hours=24),
        case_id="case_001"
    )
    print("Notification sent!")

asyncio.run(test())
```

### Managing User Preferences

```python
from cross_platform.push_notifications import PushNotificationService, NotificationType

svc = PushNotificationService()

# Set quiet hours (no notifications 10pm–7am)
svc.update_preferences(
    "user_id",
    quiet_hours_start=22,
    quiet_hours_end=7,
)

# Disable case law updates
prefs = svc.get_preferences("user_id")
prefs.enabled_types.discard(NotificationType.CASE_LAW_UPDATE)
svc.preferences.set(prefs)
```

---

## 🔐 Connecting via SSH from Your Phone

Access the full SintraPrime TUI from any phone using an SSH client.

### Required Apps

| Platform | App | Free? |
|----------|-----|-------|
| iPhone/iPad | **Blink Shell** or **SSH Files** | Blink $20, SSH Files free |
| Android | **Termux** + ssh | Free |
| Android | **JuiceSSH** | Free |

### Setup (iPhone with Blink Shell)

1. Install Blink Shell from the App Store
2. Open Blink and create a new host:
   - **Host**: `your-server.com`
   - **Port**: `22`
   - **User**: `your_username`
3. Tap **Connect**
4. Once connected, run:

```bash
sintra-mobile
```

Or launch directly:

```bash
python /path/to/SintraPrime-Unified/cross_platform/mobile_tui.py
```

### Setup (Android with Termux)

```bash
# Install in Termux
pkg install openssh

# Connect to your server
ssh username@your-server.com

# Launch SintraPrime mobile TUI
sintra-mobile
```

### SSH Configuration (~/.ssh/config on your server)

```
Host sintra-mobile
    HostName your-server.com
    User your_username
    Port 22
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

### Terminal Optimization

The mobile TUI auto-detects your terminal width. For best results:

```bash
# Set terminal to 40-char width (mobile optimal)
export COLUMNS=40
sintra-mobile

# Or use the full width
sintra-mobile --desktop
```

### Mobile TUI Navigation

```
[1] Dashboard    [5] AI Agents
[2] Cases        [6] Documents
[3] Research     [7] Settings
[4] Deadlines    [8] Help
[0] Back/Quit

Swipe Right → Back
Swipe Left  → Forward
Swipe Up    → Scroll up
Swipe Down  → Scroll down
```

### Adding SSH Key Authentication

```bash
# On your phone (Termux or Blink)
ssh-keygen -t ed25519 -C "my-phone"

# Copy public key to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@your-server.com

# Now connect without password
ssh user@your-server.com
```

---

## ⚙️ API Gateway

The API gateway aggregates all SintraPrime modules into a single endpoint.

### Starting the Gateway

```bash
uvicorn cross_platform.api_gateway:app --host 0.0.0.0 --port 8000 --reload
```

### Generating API Keys

```bash
curl -X POST http://localhost:8000/api/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-mobile-app", "scopes": ["read", "write"]}'
```

### Using API Keys

```bash
curl http://localhost:8000/api/cases \
  -H "X-API-Key: sp_your_key_here"
```

### Rate Limits

- **100 requests/minute** per IP address
- **Unlimited** (configurable) per valid API key
- Rate limit headers in every response:
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health and module status |
| GET | `/api/cases` | List active cases |
| GET | `/api/deadlines` | Upcoming deadlines |
| GET | `/api/activity` | Recent system activity |
| POST | `/api/research/query` | Legal research search |
| GET | `/api/agents` | Running AI agents |
| GET | `/api/documents` | Document list |
| POST | `/api/push/subscribe` | Register push subscription |
| POST | `/api/keys` | Create API key |
| GET | `/api/keys` | List API keys |
| DELETE | `/api/keys/{key}` | Revoke API key |

---

## 🧪 Running Tests

```bash
cd /path/to/SintraPrime-Unified
pip install pytest pytest-asyncio fastapi httpx

# Run all cross-platform tests
python -m pytest cross_platform/tests/ -v

# Run specific test class
python -m pytest cross_platform/tests/ -v -k "TestPWAConfig"
python -m pytest cross_platform/tests/ -v -k "TestPushNotifications"
python -m pytest cross_platform/tests/ -v -k "TestAPIGateway"
python -m pytest cross_platform/tests/ -v -k "TestMobileTUI"
python -m pytest cross_platform/tests/ -v -k "TestPlatformDetector"
```

---

## 📁 File Structure

```
cross_platform/
├── pwa/
│   ├── manifest.json       # PWA manifest (icons, theme, display mode)
│   ├── service_worker.js   # Offline caching + push notifications
│   ├── index.html          # PWA app shell
│   ├── app.js              # Core app logic (IndexedDB, install, push)
│   └── styles.css          # Mobile-first responsive CSS
├── api_gateway.py          # FastAPI aggregator (rate limiting, API keys)
├── mobile_tui.py           # 40-char mobile TUI for SSH access
├── push_notifications.py   # VAPID + Web Push Protocol implementation
├── platform_detector.py    # OS/environment detection + feature flags
├── tests/
│   └── test_cross_platform.py  # 65+ tests
└── CROSS_PLATFORM.md       # This file
```

---

## 🔒 Security Notes

- VAPID private keys are stored in `.push_data/vapid_keys.json` — keep this secure
- API keys are stored in `.api_keys.json` — restrict file permissions: `chmod 600 .api_keys.json`
- Use HTTPS in production (required for PWA + Push Notifications)
- SSH keys are strongly preferred over passwords
- Push notification payloads are encrypted per RFC 8291 (AES-128-GCM)

---

*SintraPrime Cross-Platform Layer — Built for attorneys who need their legal intelligence everywhere.*
