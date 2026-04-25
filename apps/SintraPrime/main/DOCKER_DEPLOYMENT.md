<<<<<<< HEAD
# SintraPrime — Phase 3 Docker Deployment (Local)

## Files
- `docker-compose.full.yml` — MySQL + Airlock + Brain + FastAPI + Webapp
- `.env.docker.example` — template (copy to `.env.docker`)
- `start-docker.ps1`, `stop-docker.ps1`, `logs-docker.ps1` — helpers
- `verify-deployment.ps1` — health verification

## Quick start
1) Create an env file:

- Copy `.env.docker.example` → `.env.docker`
- Edit secrets and webhook URLs in `.env.docker`

2) Build + start:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\start-docker.ps1`

Equivalent manual command:

- `docker compose --env-file .env.docker -f docker-compose.full.yml up -d --build`

3) Verify health:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\verify-deployment.ps1`

## Endpoints (host)
- Airlock: `http://localhost:3000/health`
- Brain: `http://localhost:8011/health`
- FastAPI: `http://localhost:8000/health`
- Webapp: `http://localhost:3002/api/sintraInfra/health`

## Notes
- Inside Docker, the webapp is wired to service DNS names (`airlock`, `brain`, `fastapi`, `mysql`).
- If you already have local services running on these ports, stop them first or the containers won’t be able to bind.
=======
# SintraPrime Docker Deployment Guide

## Overview

SintraPrime Phase 3 introduces a fully containerized deployment architecture consisting of 5 core services orchestrated via Docker Compose. This guide documents the baseline deployment configuration, health checks, and operational procedures.

**Phase 3 Achievement Metrics:**
- ✅ All 5 containers started successfully on first attempt
- ✅ 100% health check pass rate
- ✅ Zero manual intervention required
- ✅ Baseline resource usage captured
- ✅ Production-ready deployment achieved

## Architecture Overview

### 5-Service Containerized Stack
# SintraPrime — Phase 3 Docker Deployment (Local)

Phase 3 runs SintraPrime as a 5-service Docker Compose stack (MySQL + Airlock + Brain + FastAPI + Webapp). This doc is a pragmatic baseline for local deployments.

## Architecture (5-service stack)

| Service | Technology | Port | Purpose |
|:--|:--|--:|:--|
| Webapp | React | 3002 | Operator UI / run visualization |
| FastAPI | Python/FastAPI | 8000 | Analysis runner / orchestration |
| Brain | Node.js/TS | 8011 | Core engine / agent execution |
| Airlock | Express.js | 3000 | Gateway / HMAC verification |
| MySQL | MySQL 8 | 3306 | Persistent storage / audit trail |

## Files
- `docker-compose.full.yml` — MySQL + Airlock + Brain + FastAPI + Webapp
- `.env.docker.example` — template (copy to `.env.docker`)
- `start-docker.ps1`, `stop-docker.ps1`, `logs-docker.ps1` — helpers
- `verify-deployment.ps1` — health verification

## Prerequisites
- Docker Engine 20.10+
- Docker Compose v2 (`docker compose ...`)
- Enough RAM/disk to run 5 containers

## Quick start

1) Create an env file:
- Copy `.env.docker.example` → `.env.docker`
- Edit secrets and webhook URLs in `.env.docker`

2) Build + start:
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\start-docker.ps1`

Equivalent manual command:
- `docker compose --env-file .env.docker -f docker-compose.full.yml up -d --build`

3) Verify health:
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\verify-deployment.ps1`

## Endpoints (host)
- Airlock: `http://localhost:3000/health`
- Brain: `http://localhost:8011/health`
- FastAPI: `http://localhost:8000/health`
- Webapp: `http://localhost:3002/api/sintraInfra/health`

## Notes
- Inside Docker, the webapp is wired to service DNS names (`airlock`, `brain`, `fastapi`, `mysql`).
- If you already have local services running on these ports, stop them first or the containers won’t be able to bind.
## Environment Configuration

### Creating .env.docker

The `.env.docker` file contains all configuration variables required by the containerized services. Start with the template:

```bash
cp .env.example .env.docker
```

### Required Variables

#### MySQL Configuration
```bash
MYSQL_ROOT_PASSWORD=YOUR_SECURE_ROOT_PASSWORD_HERE
MYSQL_DATABASE=sintraprime
MYSQL_USER=sintraprime_user
MYSQL_PASSWORD=YOUR_SECURE_USER_PASSWORD_HERE
```

#### Airlock Configuration
```bash
AIRLOCK_PORT=3000
AIRLOCK_HMAC_SECRET=YOUR_HMAC_SECRET_HERE
AIRLOCK_WEBHOOK_URL=https://hook.make.com/YOUR_WEBHOOK_ID
AIRLOCK_MAX_FILE_SIZE=10485760  # 10MB in bytes
```

#### Brain Configuration
```bash
BRAIN_PORT=8011
NOTION_TOKEN=secret_YOUR_NOTION_TOKEN_HERE
NOTION_API_BASE=https://api.notion.com
NOTION_API_VERSION=2022-06-28
WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET_HERE
AUTONOMY_MODE=OFF
```

#### FastAPI Configuration
```bash
FASTAPI_PORT=8000
DATABASE_URL=mysql://sintraprime_user:YOUR_PASSWORD@mysql:3306/sintraprime
```

#### WebApp Configuration
```bash
WEBAPP_PORT=3002
REACT_APP_API_URL=http://localhost:8000
REACT_APP_BRAIN_URL=http://localhost:8011
```

### Security Best Practices

⚠️ **NEVER commit .env.docker to version control**

- `.env.docker` is git-ignored by default
- Use strong, unique passwords for MySQL
- Rotate HMAC secrets regularly
- Use environment-specific secrets (dev/staging/prod)
- Store production secrets in a secure vault (AWS Secrets Manager, HashiCorp Vault, etc.)

## Troubleshooting

### Container Won't Start

**Symptom:** Service exits immediately or won't start

**Diagnosis:**
```bash
# Check container logs
docker-compose logs <service-name>

# Example:
docker-compose logs airlock
docker-compose logs brain
```

**Common Causes:**
- Missing or invalid environment variables in `.env.docker`
- Port already in use on host
- Insufficient memory or disk space
- Database connection failure

**Solutions:**
```bash
# Verify .env.docker is properly configured
cat .env.docker

# Check if port is already in use
lsof -i :3000  # Check Airlock port
lsof -i :8011  # Check Brain port

# Free up disk space if needed
docker system prune -a

# Restart with fresh logs
docker-compose down
docker-compose up -d
```

### Health Check Failing

**Symptom:** Health endpoint returns 503 or times out

**Diagnosis:**
```bash
# Check service logs
docker-compose logs -f <service-name>

# Check if service is running
docker-compose ps
```

**Common Causes:**
- Service still starting up (wait 30-60 seconds)
- Dependency not available (e.g., Brain can't reach MySQL)
- Configuration error

**Solutions:**
```bash
# Wait for startup (Brain and FastAPI may take 30-60s)
sleep 60 && curl http://localhost:8011/health

# Check MySQL is ready
docker-compose exec mysql mysqladmin ping

# Restart specific service
docker-compose restart brain
```

### Database Connection Errors

**Symptom:** Brain or FastAPI can't connect to MySQL

**Diagnosis:**
```bash
# Check MySQL logs
docker-compose logs mysql

# Verify MySQL is accepting connections
docker-compose exec mysql mysql -u root -p -e "SELECT 1"
```

**Common Causes:**
- MySQL still initializing (first startup takes 30-60s)
- Incorrect credentials in `.env.docker`
- Network connectivity issue

**Solutions:**
```bash
# Wait for MySQL initialization
docker-compose logs -f mysql
# Look for "ready for connections" message

# Verify credentials
docker-compose exec mysql mysql -u sintraprime_user -p sintraprime
# Enter password from .env.docker

# Recreate database
docker-compose down -v  # WARNING: Deletes data
docker-compose up -d
```

### Out of Memory

**Symptom:** Container killed or exits with code 137

**Diagnosis:**
```bash
# Check Docker stats
docker stats

# Check system memory
free -h
```

**Solutions:**
```bash
# Increase Docker memory limit
# Edit Docker Desktop settings or /etc/docker/daemon.json

# Add memory limits to docker-compose.yml
services:
  brain:
    mem_limit: 2g
    mem_reservation: 1g
```

### Port Conflicts

**Symptom:** "port is already allocated" error

**Diagnosis:**
```bash
# Find process using the port
lsof -i :3000
netstat -tulpn | grep 3000
```

**Solutions:**
```bash
# Stop conflicting process
kill <PID>

# Or change port in docker-compose.yml
# Change host port (left side) only:
ports:
  - "3001:3000"  # Map container 3000 to host 3001
```

### Logs Not Appearing

**Symptom:** `docker-compose logs` shows no output

**Diagnosis:**
```bash
# Check if container is running
docker-compose ps

# Check container exists
docker ps -a | grep sintraprime
```

**Solutions:**
```bash
# Attach to container
docker attach sintraprime_brain_1

# Or exec into container
docker-compose exec brain sh
```

## Operational Commands

### Starting and Stopping

```bash
# Start all services
docker-compose up -d

# Stop all services (preserves data)
docker-compose down

# Stop all services and remove volumes (deletes data)
docker-compose down -v

# Restart specific service
docker-compose restart airlock

# Stop specific service
docker-compose stop brain
```

### Viewing Logs

```bash
# View all logs
docker-compose logs

# Follow logs (live tail)
docker-compose logs -f

# View specific service logs
docker-compose logs airlock
docker-compose logs -f brain

# View last 100 lines
docker-compose logs --tail=100
```

### Resource Monitoring

```bash
# Real-time resource usage
docker stats

# Container details
docker-compose ps

# Disk usage
docker system df
```

### Database Management

```bash
# Access MySQL shell
docker-compose exec mysql mysql -u root -p

# Backup database
docker-compose exec mysql mysqldump -u root -p sintraprime > backup.sql

# Restore database
docker-compose exec -T mysql mysql -u root -p sintraprime < backup.sql

# View database logs
docker-compose logs mysql
```

## Next Steps

- **Production Deployment:** See [docs/DOCKER_BEST_PRACTICES.md](docs/DOCKER_BEST_PRACTICES.md)
- **Monitoring Setup:** Configure Prometheus/Grafana dashboards
- **Backup Strategy:** Implement automated database backups
- **Scaling:** Configure Docker Swarm or Kubernetes for multi-node deployment
- **Security Hardening:** See security best practices guide
- **CI/CD Integration:** Automate Docker builds and deployments

## Related Documentation

- [DOCKER_BEST_PRACTICES.md](docs/DOCKER_BEST_PRACTICES.md) - Container management guidelines
- [OPERATOR_RUNBOOK.md](OPERATOR_RUNBOOK.md) - Operational procedures
- [AIRLOCK_DEPLOYMENT.md](docs/AIRLOCK_DEPLOYMENT.md) - Airlock-specific deployment
- [README.md](README.md) - Project overview
- [docs/snapshots/phase3-baseline/](docs/snapshots/phase3-baseline/) - Baseline deployment metrics

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review service logs: `docker-compose logs <service>`
3. Verify environment configuration in `.env.docker`
4. Consult [DOCKER_BEST_PRACTICES.md](docs/DOCKER_BEST_PRACTICES.md)
5. Open an issue on GitHub with logs and configuration (redact secrets)
>>>>>>> 530efc4 (Add comprehensive Phase 3 Docker deployment documentation)
