# SintraPrime-Unified Deployment Guide

Complete deployment instructions for Windows, Linux, macOS, and cloud platforms.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Windows Deployment](#windows-deployment)
3. [Linux/macOS Deployment](#linuxmacos-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Cloud Deployment](#cloud-deployment)
7. [Post-Deployment](#post-deployment)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### One-Command Deployment

**Windows:**
```powershell
PowerShell -ExecutionPolicy Bypass -File deployment\windows\setup.ps1
```

**Linux/macOS:**
```bash
chmod +x deployment/linux/setup.sh
./deployment/linux/setup.sh
```

### Verify Deployment

**Windows:**
```powershell
.\deployment\windows\health-check.ps1
```

**Linux/macOS:**
```bash
./deployment/linux/health-check.sh
```

---

## Windows Deployment

### System Requirements

- **OS:** Windows 10/11 Pro, Enterprise, or Server 2016+
- **RAM:** 16GB minimum (32GB recommended)
- **Disk:** 50GB available space
- **CPU:** 4 cores minimum (8+ recommended)
- **Network:** Stable internet connection

### Step 1: Prerequisites Installation

1. **Install Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop
   - Ensure WSL 2 backend is installed
   - Allocate 8GB+ RAM to Docker in settings

2. **Install Git for Windows**
   - Download from: https://git-scm.com/download/win
   - Use default installation settings

3. **Enable PowerShell Execution Policy**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

### Step 2: Run Setup Script

```powershell
cd C:\your\project\path
PowerShell -ExecutionPolicy Bypass -File deployment\windows\setup.ps1
```

The script will:
- ✓ Check all prerequisites
- ✓ Clone/update the repository
- ✓ Create environment configuration
- ✓ Build Docker images
- ✓ Start all services
- ✓ Run database migrations
- ✓ Perform health checks

### Step 3: Verify Services

```powershell
# Check container status
docker-compose ps

# View service logs
docker-compose logs -f

# Run health check
.\deployment\windows\health-check.ps1 -Continuous
```

### Step 4: Access Services

| Service | URL |
|---------|-----|
| Hive Mind API | http://localhost:8080 |
| Airlock Server | http://localhost:3001 |
| Grafana Dashboard | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Elasticsearch | http://localhost:9200 |
| MinIO Console | http://localhost:9001 |

### Useful Commands

```powershell
# Deploy updates
.\deployment\windows\deploy.ps1

# Stop all services
docker-compose down

# Remove all data (WARNING: deletes databases)
docker-compose down -v

# View service logs
docker-compose logs -f [service-name]

# Execute command in service
docker-compose exec hive-mind-api python -m pytest

# Rebuild images
docker-compose build --no-cache
```

---

## Linux/macOS Deployment

### System Requirements

- **OS:** Ubuntu 20.04+ / CentOS 8+ / macOS 11+
- **RAM:** 16GB minimum (32GB recommended)
- **Disk:** 50GB available space
- **CPU:** 4 cores minimum (8+ recommended)
- **Network:** Stable internet connection

### Step 1: Prerequisites Installation

**Ubuntu/Debian:**
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo apt-get install -y git

# Install other utilities
sudo apt-get install -y curl wget net-tools lsof
```

**macOS:**
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Install Docker Compose
brew install docker-compose

# Install Git
brew install git

# Install utilities
brew install curl wget netcat-openbsd lsof
```

**CentOS/RHEL:**
```bash
# Install Docker
sudo dnf install -y docker docker-compose git curl

# Enable Docker service
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### Step 2: Configure Docker Permissions

```bash
# Log out and log back in, or use:
newgrp docker

# Verify Docker access
docker ps
```

### Step 3: Run Setup Script

```bash
cd /path/to/project
chmod +x deployment/linux/setup.sh
./deployment/linux/setup.sh full
```

Options:
- `full` - Complete setup (default)
- `check` - Check prerequisites only
- `docker` - Build images
- `deploy` - Start services
- `health` - Check health

### Step 4: Verify Services

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f

# Health check (continuous)
./deployment/linux/health-check.sh --continuous
```

### Useful Commands

```bash
# Deploy updates
./deployment/linux/deploy.sh

# Stop services
docker-compose down

# Remove all data
docker-compose down -v

# View specific service logs
docker-compose logs -f [service-name]

# Execute command in container
docker-compose exec hive-mind-api pytest core/tests -v

# Rebuild images
docker-compose build --no-cache

# Check resource usage
docker stats
```

---

## Docker Deployment

### Direct Docker Compose

```bash
# Clone repository
git clone https://github.com/ihoward40/SintraPrime-Unified.git
cd SintraPrime-Unified

# Create environment file
cp .env.example .env

# Build and start
docker-compose up -d

# Check status
docker-compose ps
```

### Docker Compose with Custom Configuration

```bash
# Start with specific environment
ENVIRONMENT=production docker-compose up -d

# Start with custom port
EXTERNAL_API_PORT=9080 docker-compose up -d

# Start specific services only
docker-compose up -d postgres redis hive-mind-api
```

### Scaling Services

```bash
# Scale Airlock server to 3 instances
docker-compose up -d --scale airlock-server=3

# Scale Hive Mind API
docker-compose up -d --scale hive-mind-api=2
```

### Monitoring

```bash
# Real-time metrics
docker stats

# Detailed service logs
docker-compose logs --tail=100 -f hive-mind-api

# View container processes
docker top sintraprime-hive-mind

# Inspect container
docker inspect sintraprime-postgres
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster 1.20+
- kubectl configured
- Helm 3+ (optional but recommended)

### Step 1: Create Kubernetes Manifests

```bash
# Create namespace
kubectl create namespace sintraprime

# Create config maps
kubectl create configmap sintraprime-config \
  --from-file=shared/config/ \
  -n sintraprime

# Create secrets
kubectl create secret generic sintraprime-secrets \
  --from-literal=db-password=YOUR_PASSWORD \
  --from-literal=grafana-password=YOUR_PASSWORD \
  -n sintraprime
```

### Step 2: Deploy Services

```bash
# Apply manifests (create these from docker-compose)
kubectl apply -f k8s/postgresql.yaml -n sintraprime
kubectl apply -f k8s/redis.yaml -n sintraprime
kubectl apply -f k8s/hive-mind-api.yaml -n sintraprime
kubectl apply -f k8s/airlock-server.yaml -n sintraprime
kubectl apply -f k8s/elasticsearch.yaml -n sintraprime
kubectl apply -f k8s/grafana.yaml -n sintraprime
kubectl apply -f k8s/prometheus.yaml -n sintraprime
```

### Step 3: Verify Deployment

```bash
# Check pod status
kubectl get pods -n sintraprime

# Check services
kubectl get svc -n sintraprime

# View logs
kubectl logs -n sintraprime -f pod/hive-mind-api-xxx

# Port forward for access
kubectl port-forward -n sintraprime svc/hive-mind-api 8080:8080
```

### Step 4: Setup Ingress

```bash
# Install Nginx Ingress (if not present)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.5.1/deploy/static/provider/cloud/deploy.yaml

# Apply SintraPrime ingress
kubectl apply -f k8s/ingress.yaml -n sintraprime
```

---

## Cloud Deployment

### AWS Deployment (ECS)

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name sintraprime-unified

# Create task definition from docker-compose
ecs-cli compose --file docker-compose.yml create

# Launch service
ecs-cli compose --file docker-compose.yml service up

# View status
ecs-cli compose --file docker-compose.yml service ps
```

### Google Cloud Deployment (Cloud Run + CloudSQL)

```bash
# Build and push images
gcloud builds submit --tag gcr.io/YOUR_PROJECT/hive-mind-api

# Deploy to Cloud Run
gcloud run deploy hive-mind-api \
  --image gcr.io/YOUR_PROJECT/hive-mind-api \
  --platform managed \
  --region us-central1

# Create CloudSQL instance
gcloud sql instances create sintraprime-db \
  --database-version POSTGRES_13 \
  --tier db-custom-2-8192
```

### Azure Deployment (ACI + Database)

```bash
# Create resource group
az group create --name sintraprime --location eastus

# Create container registry
az acr create --resource-group sintraprime \
  --name sintraprime --sku Basic

# Create PostgreSQL
az postgres server create \
  --resource-group sintraprime \
  --name sintraprime-db \
  --admin-user sintraprime

# Deploy containers
az container create --resource-group sintraprime \
  --name hive-mind-api \
  --image sintraprime.azurecr.io/hive-mind-api:latest
```

---

## Post-Deployment

### Step 1: Initial Configuration

1. **Access Grafana Dashboard**
   - URL: http://localhost:3000
   - Default credentials: admin / admin
   - Change password immediately

2. **Configure Data Source**
   - Add Prometheus data source
   - Configure alerts and dashboards

3. **Setup Database Backups**
   ```bash
   # Create backup
   docker-compose exec postgres pg_dump -U sintraprime sintraprime_unified > backup.sql
   
   # Restore backup
   docker-compose exec postgres psql -U sintraprime sintraprime_unified < backup.sql
   ```

### Step 2: Security Hardening

1. **Update Passwords**
   - Change database password in `.env`
   - Change Grafana admin password
   - Regenerate API keys

2. **SSL/TLS Setup**
   ```bash
   # Generate self-signed certificate
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
   
   # Configure in nginx.conf or Kubernetes Ingress
   ```

3. **Firewall Configuration**
   - Restrict access to management ports (3000, 9090)
   - Allow only trusted IPs to API ports
   - Enable WAF rules for cloud deployments

### Step 3: Monitoring Setup

1. **Configure Prometheus**
   - Review scrape configs in `shared/config/prometheus.yml`
   - Add custom metrics if needed

2. **Setup Alerts**
   - Configure alert rules
   - Setup notification channels (email, Slack, etc.)

3. **Enable Log Aggregation**
   ```bash
   # Enable ELK stack (optional)
   docker-compose -f docker-compose.elk.yml up -d
   ```

### Step 4: Data Migration (if upgrading)

```bash
# Backup existing data
docker-compose exec postgres pg_dump -U sintraprime sintraprime_unified > old-backup.sql

# Run migrations
docker-compose exec hive-mind-api alembic upgrade head

# Verify migration
docker-compose exec postgres psql -U sintraprime -c "\dt"
```

---

## Troubleshooting

### Services Won't Start

**Symptom:** Services fail to start or exit immediately

**Solutions:**
```bash
# Check logs
docker-compose logs

# Verify .env file
cat .env

# Check port conflicts
# Windows: Get-NetTCPConnection -LocalPort 5432
# Linux: lsof -i :5432

# Rebuild images
docker-compose build --no-cache

# Full reset (WARNING: deletes data)
docker-compose down -v
docker-compose up -d
```

### Database Connection Errors

**Symptom:** "Connection refused" or "Connection timed out"

**Solutions:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Verify credentials
echo "SELECT 1" | docker-compose exec -T postgres psql -U sintraprime -d sintraprime_unified

# Check logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
# Wait for initialization
```

### API Not Responding

**Symptom:** HTTP 503 or timeout

**Solutions:**
```bash
# Check API logs
docker-compose logs hive-mind-api

# Verify API health
curl http://localhost:8080/health

# Check dependencies
docker-compose ps

# Check resource limits
docker stats

# Increase memory if needed
# Edit docker-compose.yml and add:
# deploy:
#   resources:
#     limits:
#       memory: 4G
```

### High Memory/CPU Usage

**Symptom:** Services using excessive resources

**Solutions:**
```bash
# Check which containers use most resources
docker stats

# View detailed resource stats
docker ps --format "{{.Names}}" | xargs docker inspect --format='{{.Name}} - Memory: {{.HostConfig.Memory}}'

# Optimize settings in shared/config/unified.config.json
# - Reduce worker threads
# - Enable caching
# - Adjust batch sizes

# Restart services with new settings
docker-compose up -d
```

### Network Connectivity Issues

**Symptom:** Services can't communicate with each other

**Solutions:**
```bash
# Check network
docker network ls
docker network inspect sintraprime-unified_sintraprime_network

# Verify service names resolve
docker-compose exec hive-mind-api ping postgres

# Check DNS in containers
docker-compose exec hive-mind-api cat /etc/resolv.conf

# Recreate network
docker-compose down
docker-compose up -d
```

### Permission Denied Errors

**Symptom:** "Permission denied" when accessing volumes

**Solutions:**
```bash
# Fix volume permissions (Linux)
docker-compose down
sudo chown -R $USER:$USER shared/
docker-compose up -d

# Check SELinux (if enabled)
getenforce
# If enforcing, add to docker-compose.yml:
# volumes:
#   - ./shared:/app/shared:Z
```

---

## Health Checks

### Manual Health Verification

**Windows:**
```powershell
.\deployment\windows\health-check.ps1 -Verbose
.\deployment\windows\health-check.ps1 -Continuous -IntervalSeconds 30
```

**Linux/macOS:**
```bash
./deployment/linux/health-check.sh --verbose
./deployment/linux/health-check.sh --continuous
```

### Expected Responses

| Service | Endpoint | Expected |
|---------|----------|----------|
| Hive Mind | GET /health | 200 OK |
| Airlock | GET /health | 200 OK |
| PostgreSQL | Port 5432 | LISTEN |
| Redis | Port 6379 | LISTEN |
| Elasticsearch | GET / | 200 OK |
| Grafana | GET /api/health | 200 OK |

---

## Backup & Disaster Recovery

### Automated Backups

```bash
# Create daily backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U sintraprime sintraprime_unified > $BACKUP_DIR/database.sql

# Backup volumes
docker run --rm -v sintraprime-unified_postgres_data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar czf /backup/postgres.tar.gz /data

# Backup config
cp -r shared/config $BACKUP_DIR/config

echo "Backup complete: $BACKUP_DIR"
EOF

chmod +x backup.sh

# Schedule daily backup (crontab -e)
# 0 2 * * * /path/to/backup.sh
```

### Restore from Backup

```bash
# Restore database
docker-compose exec postgres psql -U sintraprime sintraprime_unified < backups/20240422/database.sql

# Restore volumes
docker run --rm -v sintraprime-unified_postgres_data:/data -v $(pwd)/backups/20240422:/backup alpine tar xzf /backup/postgres.tar.gz

# Verify restoration
docker-compose down && docker-compose up -d
```

---

## Performance Tuning

### Database Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM your_table;

-- Create indexes for slow queries
CREATE INDEX idx_column_name ON table_name(column_name);

-- Vacuum and analyze
VACUUM ANALYZE;
```

### Cache Configuration

```json
// In shared/config/unified.config.json
{
  "redis": {
    "max_memory": "2gb",
    "max_memory_policy": "allkeys-lru",
    "timeout": 300
  }
}
```

### API Scaling

```yaml
# In docker-compose.yml
services:
  hive-mind-api:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## Next Steps

1. Review API documentation: `docs/API.md`
2. Explore features: `docs/FEATURES.md`
3. Configure integrations: `shared/config/integrations.json`
4. Setup monitoring dashboards in Grafana
5. Configure backup and disaster recovery

---

**Last Updated:** 2026-04-22
**Version:** 1.0.0
**Support:** https://github.com/ihoward40/SintraPrime-Unified/issues
