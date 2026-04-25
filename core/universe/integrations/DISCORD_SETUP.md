# Discord Bot Setup Guide

Quick start guide for deploying the SintraPrime UniVerse Discord bot.

## Step 1: Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**
3. Enter name: `SintraPrime UniVerse`
4. Accept the terms and click **Create**

## Step 2: Create Bot User

1. In your application, go to **Bot** section
2. Click **Add Bot**
3. Under the bot's name, click **Copy** to copy the token
4. Save the token securely (keep it secret!)

## Step 3: Configure Intents

In the **Bot** section, enable the following Intents:

Required Intents:
- ✅ **Message Content Intent** (for reading command content)
- ✅ **Server Members Intent** (for permission checking)
- ✅ **Guild Members Intent** (for user tracking)

Recommended Intents:
- ✅ **Guilds** (track servers)
- ✅ **Guild Messages** (read messages)
- ✅ **Direct Messages** (DM support)
- ✅ **Message Reactions** (reaction handlers)

## Step 4: Set Bot Permissions

In the **OAuth2** → **URL Generator** section:

**Scopes:**
- ✅ `bot`
- ✅ `applications.commands`

**Permissions:**
- ✅ Read Messages/View Channels
- ✅ Send Messages
- ✅ Embed Links
- ✅ Attach Files
- ✅ Read Message History
- ✅ Add Reactions
- ✅ Use Slash Commands
- ✅ Manage Messages

Copy the generated OAuth2 URL.

## Step 5: Install Bot to Server

1. Visit the OAuth2 URL you copied
2. Select the Discord server to add the bot to
3. Authorize the permissions
4. The bot should now appear in your server

## Step 6: Configure Environment

Create `.env` file:

```env
DISCORD_BOT_TOKEN=YOUR_TOKEN_HERE
DISCORD_PREFIX=!
AGENT_FRAMEWORK_URL=http://localhost:8000
SKILL_REGISTRY_URL=http://localhost:8001
DATABASE_URL=postgresql://user:pass@localhost/discord_db
```

Or set environment variables:

```bash
export DISCORD_BOT_TOKEN="YOUR_TOKEN_HERE"
export DISCORD_PREFIX="!"
```

## Step 7: Install Dependencies

```bash
pip install discord.py aiohttp
pip install python-dotenv  # For .env support
```

## Step 8: Initialize Database

```bash
# Create database (PostgreSQL example)
createdb discord_universe

# Run schema
psql discord_universe < universe/integrations/discord_schema.sql
```

## Step 9: Start the Bot

```python
import os
from dotenv import load_dotenv
from universe.integrations import create_discord_bot

# Load environment variables
load_dotenv()

# Get token
token = os.getenv("DISCORD_BOT_TOKEN")

# Create and start bot
bot = create_discord_bot(
    token=token,
    agent_framework=your_agent_framework,  # Pass your framework instance
    event_hub=your_event_hub               # Pass your event hub instance
)

# Connect to Discord
import asyncio
asyncio.run(bot.connect())
```

Or run as a service:

```bash
python -m universe.integrations.discord_service start
```

## Step 10: Test the Bot

In any Discord channel with the bot:

```
!help
```

You should see the help embed with all available commands.

Try a command:

```
!status
```

## Troubleshooting

### Bot Won't Start

```
Error: "Token is invalid"
```

**Solution:** Verify the token is correct. Copy from Developer Portal again.

### Commands Not Responding

```
Error: "Missing permissions"
```

**Solution:** 
1. Check bot has appropriate permissions in the channel
2. Check bot role is above user roles (in role settings)
3. Verify intents are enabled

### Slash Commands Not Appearing

**Solution:**
1. Ensure `applications.commands` scope is used in OAuth2 URL
2. Reload the server (F5) in Discord
3. Wait a few minutes for Discord to sync commands

### Database Connection Error

**Solution:**
1. Verify PostgreSQL is running
2. Check DATABASE_URL is correct
3. Ensure database is created
4. Run schema again

## Configuration Guide

### Per-Server Settings

After bot is online, you can configure each server:

```
!help config
```

Available settings:
- Command prefix: `!config prefix ?`
- Features: `!config feature slash_commands on`
- Roles: `!config role moderator @ModRole`
- Channels: `!config channel logs #agent-logs`

### Production Deployment

For production, use a process manager:

**Using systemd:**

```ini
[Unit]
Description=SintraPrime Discord Bot
After=network.target

[Service]
Type=simple
User=discord_bot
WorkingDirectory=/opt/universe
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 -m universe.integrations.discord_service
Restart=always

[Install]
WantedBy=multi-user.target
```

**Using Docker:**

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY universe/ ./universe/
ENV DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}

CMD ["python", "-m", "universe.integrations.discord_service"]
```

## Security Best Practices

1. **Never commit your token** to version control
2. **Use environment variables** for secrets
3. **Enable audit logging** for all operations
4. **Regularly rotate tokens** (Developer Portal)
5. **Monitor for unusual activity** in logs
6. **Keep dependencies updated** (especially discord.py)
7. **Use TLS/HTTPS** for all external API calls
8. **Validate user input** on all commands

## Monitoring

Check bot health:

```
!status
```

View logs:

```bash
tail -f /var/log/discord_bot.log
```

Monitor database:

```sql
SELECT COUNT(*) FROM discord_commands 
WHERE executed_at > NOW() - INTERVAL '1 hour';
```

## Additional Resources

- [Discord Developer Portal](https://discord.com/developers/)
- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [SintraPrime Documentation](https://docs.sintraprime.com/)
- [Integration Guide](./DISCORD_INTEGRATION_GUIDE.md)
- [API Reference](./DISCORD_INTEGRATION_GUIDE.md#api-reference)

## Support

For issues or questions:

1. Check the [Integration Guide](./DISCORD_INTEGRATION_GUIDE.md#troubleshooting)
2. Review Discord bot logs
3. Check database logs
4. Contact support: support@sintraprime.com

---

**Deployment Date:** April 21, 2026
**Status:** Ready for Production
