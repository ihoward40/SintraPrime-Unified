# SintraPrime-Unified Quick Reference

> **Install Path:** `C:\SintraPrime-Unified`  
> **Version:** 2.0.0

---

## 🚀 Start / Stop

```powershell
# Start all services (detached)
docker-compose up -d

# Stop all services (preserve data)
docker-compose down

# Stop all services AND delete data volumes  ⚠️ destructive
docker-compose down -v

# Restart all services
docker-compose restart

# Restart single service
docker-compose restart api
docker-compose restart airlock-server
```

---

## 🌐 Service URLs

| Service | URL | Description |
|---|---|---|
| **Main App** | http://localhost:3001 | Airlock Server (primary UI) |
| **API** | http://localhost:8080 | SintraPrime Hive Mind API |
| **API Docs** | http://localhost:8080/docs | Interactive Swagger UI |
| **API Health** | http://localhost:8080/health | Health check endpoint |
| **Grafana** | http://localhost:3000 | Monitoring dashboards |
| **Prometheus** | http://localhost:9090 | Metrics (raw) |
| **Elasticsearch** | http://localhost:9200 | Search & analytics |
| **MinIO Console** | http://localhost:9001 | S3-compatible object storage |
| **MinIO API** | http://localhost:9000 | S3 API endpoint |
| **Twin Display** | ws://localhost:8765 | TUI WebSocket server |
| **Nginx Proxy** | http://localhost:80 | Reverse proxy (all services) |

---

## 🔑 Default Credentials

| Service | Username | Password | Notes |
|---|---|---|---|
| **Grafana** | admin | *(see .env GRAFANA_PASSWORD)* | Change in production |
| **MinIO** | minioadmin | *(see .env MINIO_PASSWORD)* | Change in production |
| **API Admin** | admin | admin | Change immediately! |
| **PostgreSQL** | sintraprime | *(see .env POSTGRES_PASSWORD)* | Auto-generated |

---

## 📋 Common Tasks

### View Logs
```powershell
# All services (follow)
docker-compose logs -f

# Single service
docker-compose logs -f api
docker-compose logs -f airlock-server
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 api
```

### Service Status
```powershell
# List all containers
docker-compose ps

# Detailed status (with health)
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Run health check script
.\health_check.ps1

# Watch health (auto-refresh)
.\health_check.ps1 -Watch
```

### Container Shell Access
```powershell
# Python API
docker exec -it sintraprime-api bash

# PostgreSQL
docker exec -it sintraprime-postgres psql -U sintraprime -d sintraprime_unified

# Redis
docker exec -it sintraprime-redis redis-cli

# Elasticsearch
docker exec -it sintraprime-elasticsearch bash
```

### Database Operations
```powershell
# Connect to PostgreSQL
docker exec -it sintraprime-postgres psql -U sintraprime -d sintraprime_unified

# PostgreSQL useful queries
# \dt          -- list tables
# \d agents    -- describe table
# \q           -- quit

# Redis operations
docker exec -it sintraprime-redis redis-cli
# PING           -- test connection
# KEYS *         -- list all keys
# DBSIZE         -- count keys
# FLUSHALL       -- clear all data (⚠️ destructive)
```

### Update / Rebuild
```powershell
# Pull latest images
docker-compose pull

# Rebuild custom images (after code changes)
docker-compose build --no-cache

# Full restart after rebuild
docker-compose down && docker-compose build && docker-compose up -d
```

---

## ⚙️ Configuration

### Edit Environment Variables
```powershell
# Open .env in Notepad
notepad .env

# After editing, restart affected services
docker-compose restart api
docker-compose restart airlock-server
```

### Add AI API Keys
Edit `.env` and add:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
```
Then restart: `docker-compose restart api airlock-server`

### Change Ports (if conflicts)
Edit `.env`:
```
API_PORT=8081          # Change from 8080
GRAFANA_PORT=3001      # Change from 3000
PROMETHEUS_PORT=9091   # Change from 9090
```
Then: `docker-compose down && docker-compose up -d`

---

## 🔧 Troubleshooting

### Services Won't Start
```powershell
# Check logs
docker-compose logs api
docker-compose logs postgres

# Check Docker resources
docker info

# Increase Docker memory in Docker Desktop:
# Settings > Resources > Memory > 4GB+
```

### Port Already in Use
```powershell
# Find what's using port 8080
netstat -ano | findstr :8080

# Kill the process (replace PID)
taskkill /PID 1234 /F

# Or change the port in .env (see Configuration section)
```

### Database Connection Error
```powershell
# Check PostgreSQL is healthy
docker inspect sintraprime-postgres --format "{{.State.Health.Status}}"

# View PostgreSQL logs
docker-compose logs postgres

# Force recreate PostgreSQL
docker-compose stop postgres
docker volume rm sintraPrime-unified_postgres_data
docker-compose up -d postgres
```

### Container Exits Immediately
```powershell
# Check exit code and logs
docker-compose logs api
docker inspect sintraprime-api --format "{{.State.ExitCode}}"

# Common fix: check .env has correct values
cat .env

# Rebuild the container
docker-compose build --no-cache api
docker-compose up -d api
```

### Out of Disk Space
```powershell
# Check disk usage
docker system df

# Clean up unused images/containers
docker system prune -a --volumes

# Only remove stopped containers
docker container prune
```

### Reset Everything (nuclear option)
```powershell
# ⚠️ THIS DELETES ALL DATA
docker-compose down -v
docker system prune -a
docker-compose up -d
```

---

## 🏗️ Architecture

```
Internet / Browser
      │
      ▼
  Nginx (:80)          ← Reverse proxy & routing
      │
  ┌───┴──────────┐
  │              │
  ▼              ▼
Airlock         API                 ← Application tier
(:3001)       (:8080)
  │              │
  └─────┬────────┘
        │
  ┌─────┼─────────────────────┐
  │     │                     │
  ▼     ▼                     ▼
Postgres  Redis          Elasticsearch  ← Data tier
(:5432) (:6379)            (:9200)

Prometheus (:9090) ← Scrapes metrics from all services
Grafana (:3000)    ← Visualizes Prometheus metrics
MinIO (:9000)      ← Object/file storage
Twin (:8765)       ← TUI WebSocket server
```

---

## 📁 File Structure

```
C:\SintraPrime-Unified\
├── docker-compose.yml        ← Service definitions
├── .env                      ← Your secrets (KEEP PRIVATE)
├── .env.example              ← Template for .env
├── SETUP_WINDOWS.ps1         ← This setup script
├── health_check.ps1          ← Service health checker
├── QUICK_REFERENCE.md        ← This file
├── core/                     ← Python FastAPI (Hive Mind API)
│   ├── Dockerfile
│   ├── universe/             ← Core agent logic
│   └── requirements.txt
├── apps/
│   ├── sintraprime/          ← TypeScript Airlock Server
│   └── ike-bot/              ← Discord/Slack bot
├── superintelligence/        ← Advanced AI modules
├── twin_layer/               ← TUI display system
├── shared/
│   ├── config/               ← Prometheus, Nginx, Grafana config
│   └── schemas/              ← Database schema SQL
└── deployment/
    ├── windows/              ← Windows-specific scripts
    └── linux/                ← Linux deployment scripts
```

---

## 📞 Support

- **Logs:** `docker-compose logs -f`
- **Health:** `.\health_check.ps1`
- **Docs:** http://localhost:8080/docs
- **Grafana:** http://localhost:3000

---

*SintraPrime-Unified v2.0 — Built for Windows with Docker*
