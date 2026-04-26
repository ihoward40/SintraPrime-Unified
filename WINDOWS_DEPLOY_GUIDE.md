# SintraPrime-Unified: Windows Deployment Guide

> **Version 2.0** · Last updated April 2026  
> One-command deployment for the full SintraPrime platform on Windows 10/11

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 Minutes)](#quick-start-5-minutes)
3. [Full Stack Deployment (15 Minutes)](#full-stack-deployment-15-minutes)
4. [API Keys Required](#api-keys-required)
5. [Service Architecture](#service-architecture)
6. [Health Check](#health-check)
7. [Managing Services](#managing-services)
8. [Troubleshooting](#troubleshooting)
9. [Updating](#updating)

---

## Prerequisites

| Requirement | Minimum Version | Download |
|---|---|---|
| **Windows** | 10 (1903+) or 11 | — |
| **Python** | 3.10+ | [python.org](https://www.python.org/downloads/) or Microsoft Store |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) |
| **Git** | Any recent | [git-scm.com](https://git-scm.com/download/win) |
| **Docker Desktop** | 4.x (optional) | [docker.com](https://www.docker.com/products/docker-desktop/) |

> **Note:** Docker Desktop is only needed for the full-stack deployment (all 10 services).  
> For local Python-only development, Docker is optional.

### Before You Begin

1. **Enable WSL 2** (recommended for Docker Desktop):
   ```powershell
   wsl --install
   ```
2. **Set PowerShell execution policy** (run as Administrator):
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
3. **Verify tools are on PATH**:
   ```powershell
   python --version    # Should print 3.10+
   node --version      # Should print v18+
   git --version
   docker --version    # Optional
   ```

---

## Quick Start (5 Minutes)

This gets the API running locally **without Docker**.

### 1. Clone the Repository

```powershell
git clone https://github.com/ihoward40/SintraPrime-Unified.git
cd SintraPrime-Unified
```

### 2. Create Virtual Environment & Install Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Create Environment File

```powershell
Copy-Item .env.example .env
```

Open `.env` in your editor and set at minimum:
- `POSTGRES_PASSWORD` — a strong database password
- `SECRET_KEY` — generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- `JWT_SECRET` — generate with: `python -c "import secrets; print(secrets.token_hex(32))"`

### 4. Start the Hive Mind API

```powershell
cd core
python -m uvicorn universe.hive_mind_api:app --host 0.0.0.0 --port 8080 --reload
```

### 5. Verify

Open your browser to **http://localhost:8080/health** — you should see a JSON health response.

```powershell
Invoke-RestMethod http://localhost:8080/health
```

---

## Full Stack Deployment (15 Minutes)

This deploys all 10 services via Docker Compose using the automated setup script.

### Option A: One-Command Setup (Recommended)

Run the master setup script **as Administrator**:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\SETUP_WINDOWS.ps1
```

The script will:
1. ✅ Check all prerequisites (Python, Node.js, Git, Docker Desktop)
2. ✅ Generate secure `.env` from `.env.example` with random secrets
3. ✅ Build all Docker images
4. ✅ Start all 10 services
5. ✅ Run health checks on every endpoint
6. ✅ Display a summary dashboard

### Option B: Manual Docker Compose

```powershell
# 1. Copy environment template
Copy-Item .env.example .env

# 2. Edit .env — fill in passwords and API keys
notepad .env

# 3. Build images
docker compose build

# 4. Start all services (detached)
docker compose up -d

# 5. Watch logs
docker compose logs -f

# 6. Verify health
docker compose ps
```

### Option C: Step-by-Step Scripts

```powershell
# Setup (checks dependencies, creates .env)
PowerShell -ExecutionPolicy Bypass -File .\deployment\windows\setup.ps1 -Action check

# Deploy (builds & starts containers)
PowerShell -ExecutionPolicy Bypass -File .\deployment\windows\deploy.ps1

# Health check (monitors all services)
PowerShell -ExecutionPolicy Bypass -File .\deployment\windows\health-check.ps1
```

---

## API Keys Required

| Key | Required? | Where to Get | Used By |
|---|---|---|---|
| `POSTGRES_PASSWORD` | **Yes** | Self-chosen (16+ chars) | Database |
| `REDIS_PASSWORD` | **Yes** | Self-chosen | Cache |
| `SECRET_KEY` | **Yes** | `python -c "import secrets; print(secrets.token_hex(32))"` | App encryption |
| `JWT_SECRET` | **Yes** | `python -c "import secrets; print(secrets.token_hex(32))"` | Auth tokens |
| `ANTHROPIC_API_KEY` | Recommended | [console.anthropic.com](https://console.anthropic.com/) | Claude AI |
| `OPENAI_API_KEY` | Recommended | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | GPT models |
| `SLACK_BOT_TOKEN` | Optional | [api.slack.com/apps](https://api.slack.com/apps) | Slack integration |
| `SLACK_SIGNING_SECRET` | Optional | Same Slack app settings | Slack verification |
| `DISCORD_BOT_TOKEN` | Optional | [discord.com/developers](https://discord.com/developers/applications) | Discord bot |
| `GITHUB_TOKEN` | Optional | [github.com/settings/tokens](https://github.com/settings/tokens) | GitHub integration |
| `GHL_API_KEY` | Optional | GoHighLevel dashboard | CRM integration |
| `NOTION_TOKEN` | Optional | [notion.so/my-integrations](https://www.notion.so/my-integrations) | Notion sync |
| `GRAFANA_PASSWORD` | Optional | Self-chosen (default: `admin`) | Monitoring UI |
| `MINIO_PASSWORD` | Optional | Self-chosen (default: `minioadmin123`) | Object storage |

> **Tip:** The `SETUP_WINDOWS.ps1` script auto-generates `SECRET_KEY`, `JWT_SECRET`, `POSTGRES_PASSWORD`, and `REDIS_PASSWORD` with secure random values. You only need to manually add API keys for AI and integrations.

---

## Service Architecture

SintraPrime-Unified runs **10 services** orchestrated by Docker Compose:

| # | Service | Container | Port | Description |
|---|---|---|---|---|
| 1 | **Hive Mind API** | `sintraprime-api` | `8080` | Core FastAPI backend — AI agents, swarms, superintelligence engine |
| 2 | **Airlock Server** | `sintraprime-airlock` | `3001` | Node.js gateway — Slack, Discord, GitHub webhooks, client SDK |
| 3 | **PostgreSQL 15** | `sintraprime-postgres` | `5432` | Primary relational database (agents, users, memory, events) |
| 4 | **Redis 7** | `sintraprime-redis` | `6379` | Cache, pub/sub messaging, session store |
| 5 | **Elasticsearch 8** | `sintraprime-elastic` | `9200` | Full-text search, log aggregation, agent memory indexing |
| 6 | **Prometheus** | `sintraprime-prometheus` | `9090` | Metrics collection from all services |
| 7 | **Grafana** | `sintraprime-grafana` | `3000` | Monitoring dashboards (login: `admin` / your `GRAFANA_PASSWORD`) |
| 8 | **MinIO** | `sintraprime-minio` | `9000`/`9001` | S3-compatible object storage for files & artifacts |
| 9 | **Twin Display** | `sintraprime-twin` | `8765` | WebSocket server for real-time Twin TUI visualization |
| 10 | **Nginx** | `sintraprime-nginx` | `80` | Reverse proxy — routes traffic to API and Airlock |

### Network Topology

```
                 ┌─────────────┐
  Port 80  ────▶│    Nginx     │
                 └──────┬──────┘
                   ┌────┴────┐
                   ▼         ▼
              ┌────────┐ ┌────────┐
  Port 8080 ─│  API   │ │Airlock │─ Port 3001
              └───┬────┘ └───┬────┘
                  │          │
         ┌────────┼──────────┼────────┐
         ▼        ▼          ▼        ▼
     ┌───────┐ ┌──────┐ ┌───────┐ ┌──────┐
     │Postgre│ │Redis │ │Elastic│ │MinIO │
     │  SQL  │ │      │ │Search │ │      │
     └───────┘ └──────┘ └───────┘ └──────┘
      5432      6379      9200    9000/9001
```

---

## Health Check

### Quick Check

```powershell
# Check all containers are running
docker compose ps

# Hit the API health endpoint
Invoke-RestMethod http://localhost:8080/health

# Hit the Airlock health endpoint
Invoke-RestMethod http://localhost:3001/health
```

### Automated Health Check Script

```powershell
# One-time check
PowerShell -ExecutionPolicy Bypass -File .\deployment\windows\health-check.ps1

# Continuous monitoring (every 30 seconds)
PowerShell -ExecutionPolicy Bypass -File .\deployment\windows\health-check.ps1 -Continuous -IntervalSeconds 30
```

### Check Individual Services

```powershell
# PostgreSQL
docker exec sintraprime-postgres pg_isready -U sintraprime

# Redis
docker exec sintraprime-redis redis-cli ping

# Elasticsearch
Invoke-RestMethod http://localhost:9200/_cluster/health

# Grafana
Invoke-RestMethod http://localhost:3000/api/health

# Prometheus
Invoke-RestMethod http://localhost:9090/-/healthy

# MinIO
Invoke-RestMethod http://localhost:9000/minio/health/live
```

---

## Managing Services

### Start / Stop / Restart

```powershell
# Start all services
docker compose up -d

# Stop all services (preserves data)
docker compose down

# Restart a single service
docker compose restart api

# View logs (follow mode)
docker compose logs -f api airlock-server

# View last 100 lines for a service
docker compose logs --tail 100 api
```

### Rebuild After Code Changes

```powershell
# Rebuild and restart only the API
docker compose up -d --build api

# Rebuild everything
docker compose up -d --build

# Full clean rebuild (removes cached layers)
docker compose build --no-cache
docker compose up -d
```

### Data Management

```powershell
# Backup PostgreSQL
docker exec sintraprime-postgres pg_dump -U sintraprime sintraprime_unified > backup.sql

# Restore PostgreSQL
Get-Content backup.sql | docker exec -i sintraprime-postgres psql -U sintraprime sintraprime_unified

# Reset everything (⚠ destroys all data)
docker compose down -v
docker compose up -d
```

---

## Troubleshooting

### Docker Desktop Won't Start

| Symptom | Solution |
|---|---|
| "WSL 2 not installed" | Run `wsl --install` as Admin, then restart |
| "Hyper-V not enabled" | Enable in Windows Features or run: `Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All` |
| Docker hangs on startup | Restart Docker Desktop, or run `wsl --shutdown` then reopen |
| "Port already in use" | Find the process: `netstat -ano | findstr :8080` then `taskkill /PID <pid> /F` |

### Container Issues

| Symptom | Solution |
|---|---|
| `sintraprime-api` keeps restarting | Check logs: `docker compose logs api` — likely missing env vars or DB not ready |
| Elasticsearch exits with code 137 | Out of memory — increase Docker Desktop memory to 6 GB+ (Settings → Resources) |
| "connection refused" to PostgreSQL | Wait 30 seconds for DB init, or check: `docker compose ps postgres` |
| Redis auth errors | Ensure `REDIS_PASSWORD` in `.env` matches what services expect |

### Python / pip Issues

| Symptom | Solution |
|---|---|
| `pip install` fails on `psycopg2-binary` | Install Visual C++ Build Tools: [visualstudio.microsoft.com](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | Ensure venv is activated: `.\.venv\Scripts\Activate.ps1` |
| Wrong Python version | Check `python --version` — must be 3.10+. Use `py -3.12` if multiple versions installed |
| `execution policy` error | Run: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |

### Network Issues

| Symptom | Solution |
|---|---|
| Can't reach `localhost:8080` | Check Windows Firewall isn't blocking. Try `127.0.0.1:8080` instead |
| API can't connect to PostgreSQL | Services must be on the same Docker network — check `docker network ls` |
| Slow first startup | Initial Docker image pulls can take 5-10 min. Subsequent starts are fast |

### Common Fixes

```powershell
# Nuclear option: full reset
docker compose down -v --remove-orphans
docker system prune -af
docker compose up -d --build

# Check resource usage
docker stats

# Check which ports are in use
netstat -ano | findstr "LISTENING" | findstr "8080 3001 5432 6379 9200 3000 9090 80"
```

---

## Updating

### Pull Latest Code

```powershell
git pull origin main
docker compose up -d --build
```

### Update Python Dependencies

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade
```

### Full Re-deployment

```powershell
git pull origin main
PowerShell -ExecutionPolicy Bypass -File .\SETUP_WINDOWS.ps1
```

---

## File Reference

| File | Purpose |
|---|---|
| `SETUP_WINDOWS.ps1` | Master one-command setup script (run as Admin) |
| `deployment/windows/setup.ps1` | Dependency checking & environment setup |
| `deployment/windows/deploy.ps1` | Build, deploy, and verify containers |
| `deployment/windows/health-check.ps1` | Service health monitoring (one-shot & continuous) |
| `docker-compose.yml` | Docker Compose service definitions (10 services) |
| `.env.example` | Template for environment variables |
| `.env` | Your local config (git-ignored — never commit this!) |
| `requirements.txt` | Python dependencies for local development |
| `core/requirements.txt` | Python dependencies for the Docker API image |

---

## Support

- **Repository:** [github.com/ihoward40/SintraPrime-Unified](https://github.com/ihoward40/SintraPrime-Unified)
- **Issues:** [github.com/ihoward40/SintraPrime-Unified/issues](https://github.com/ihoward40/SintraPrime-Unified/issues)
- **Deployment Scripts:** `deployment/windows/` directory
