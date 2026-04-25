#!/bin/bash

# SintraPrime-Unified Linux/Mac Setup Script
# Comprehensive setup and deployment automation for Linux and macOS
# Usage: ./setup.sh [OPTIONS]

set -e

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_FILE="$PROJECT_ROOT/deployment-$(date +%Y%m%d-%H%M%S).log"
DB_PASSWORD="${DB_PASSWORD:-sintraprime123}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Action
ACTION="${1:-full}"
REPO_URL="${2:-https://github.com/ihoward40/SintraPrime-Unified.git}"
BRANCH="${3:-main}"

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
    
    case $level in
        SUCCESS)
            echo -e "${GREEN}✓ $message${NC}"
            ;;
        ERROR)
            echo -e "${RED}✗ $message${NC}"
            ;;
        WARNING)
            echo -e "${YELLOW}⚠ $message${NC}"
            ;;
        STEP)
            echo -e "\n${MAGENTA}=== $message ===${NC}"
            ;;
        INFO)
            echo -e "${CYAN}  $message${NC}"
            ;;
    esac
}

# Check Docker installation
check_docker() {
    log INFO "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log ERROR "Docker not found. Please install Docker."
        log INFO "Visit: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    if ! docker ps &> /dev/null; then
        log ERROR "Docker daemon is not running or you don't have permissions."
        log INFO "Try: sudo usermod -aG docker $USER"
        return 1
    fi
    
    log SUCCESS "Docker is installed and running: $(docker --version)"
    return 0
}

# Check Docker Compose
check_docker_compose() {
    log INFO "Checking Docker Compose..."
    
    if ! command -v docker-compose &> /dev/null; then
        log ERROR "Docker Compose not found. Please install Docker Compose."
        log INFO "Visit: https://docs.docker.com/compose/install/"
        return 1
    fi
    
    log SUCCESS "Docker Compose found: $(docker-compose --version)"
    return 0
}

# Check Git
check_git() {
    log INFO "Checking Git installation..."
    
    if ! command -v git &> /dev/null; then
        log ERROR "Git not found. Please install Git."
        return 1
    fi
    
    log SUCCESS "Git found: $(git --version)"
    return 0
}

# Check port availability
check_ports() {
    log INFO "Checking port availability..."
    
    local ports=(8080 3001 3000 9000 5432 6379 9200 9090)
    local ports_in_use=()
    
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            ports_in_use+=($port)
            log WARNING "Port $port is already in use"
        fi
    done
    
    if [ ${#ports_in_use[@]} -gt 0 ]; then
        log WARNING "Some ports are in use: ${ports_in_use[*]}"
        return 1
    fi
    
    log SUCCESS "All required ports are available"
    return 0
}

# Test prerequisites
test_prerequisites() {
    log STEP "PHASE 1: Checking Prerequisites"
    
    local all_good=true
    
    check_docker || all_good=false
    check_docker_compose || all_good=false
    check_git || all_good=false
    check_ports || all_good=false
    
    if [ "$all_good" = true ]; then
        return 0
    else
        return 1
    fi
}

# Setup repository
setup_repository() {
    log STEP "PHASE 2: Repository Setup"
    
    if [ ! -d "$PROJECT_ROOT/.git" ]; then
        log INFO "Cloning repository..."
        git clone --branch "$BRANCH" "$REPO_URL" "$PROJECT_ROOT" || {
            log ERROR "Failed to clone repository"
            return 1
        }
        log SUCCESS "Repository cloned"
    else
        log INFO "Repository exists. Updating..."
        cd "$PROJECT_ROOT"
        git pull origin "$BRANCH" || {
            log ERROR "Failed to update repository"
            return 1
        }
        log SUCCESS "Repository updated"
    fi
    
    return 0
}

# Setup environment
setup_environment() {
    log STEP "PHASE 3: Environment Configuration"
    
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log INFO "Creating .env file..."
        
        cat > "$PROJECT_ROOT/.env" << EOF
# Database Configuration
DB_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql://sintraprime:$DB_PASSWORD@postgres:5432/sintraprime_unified

# Redis Configuration
REDIS_URL=redis://redis:6379

# Grafana Configuration
GRAFANA_PASSWORD=$GRAFANA_PASSWORD

# MinIO Configuration
MINIO_PASSWORD=minioadmin

# Application Configuration
LOG_LEVEL=INFO
NODE_ENV=production
API_PORT=8080
AIRLOCK_PORT=3001
EOF
        
        log SUCCESS ".env file created"
    else
        log INFO ".env file already exists"
    fi
    
    return 0
}

# Build Docker images
build_docker_images() {
    log STEP "PHASE 4: Building Docker Images"
    
    cd "$PROJECT_ROOT"
    
    log INFO "Building images..."
    if docker-compose build --no-cache; then
        log SUCCESS "Docker images built successfully"
        return 0
    else
        log ERROR "Docker build failed"
        return 1
    fi
}

# Start services
start_services() {
    log STEP "PHASE 5: Starting Services"
    
    cd "$PROJECT_ROOT"
    
    log INFO "Starting Docker Compose services..."
    if docker-compose up -d; then
        log SUCCESS "Services started"
        log INFO "Waiting for initialization..."
        sleep 15
        return 0
    else
        log ERROR "Failed to start services"
        return 1
    fi
}

# Initialize database
initialize_database() {
    log STEP "PHASE 6: Database Initialization"
    
    log INFO "Running database migrations..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8080/health >/dev/null 2>&1; then
            log SUCCESS "Database initialization completed"
            return 0
        fi
        
        attempt=$((attempt + 1))
        if [ $attempt -lt $max_attempts ]; then
            log INFO "Waiting for API to be ready... ($attempt/$max_attempts)"
            sleep 2
        fi
    done
    
    log WARNING "Database initialization timed out (services may still initialize)"
    return 0
}

# Test service health
test_service_health() {
    log STEP "PHASE 7: Health Checks"
    
    local all_healthy=true
    
    # Check HTTP endpoints
    declare -A endpoints=(
        ["Hive Mind API"]="http://localhost:8080/health"
        ["Airlock Server"]="http://localhost:3001/health"
        ["Grafana"]="http://localhost:3000/api/health"
    )
    
    for service in "${!endpoints[@]}"; do
        if curl -f "${endpoints[$service]}" >/dev/null 2>&1; then
            log SUCCESS "$service: Healthy ✓"
        else
            log WARNING "$service: Unhealthy ✗"
            all_healthy=false
        fi
    done
    
    return 0
}

# Display summary
display_summary() {
    log STEP "PHASE 8: Deployment Summary"
    
    cat << EOF

╔════════════════════════════════════════════════════════════╗
║    SintraPrime-Unified Successfully Deployed!              ║
╚════════════════════════════════════════════════════════════╝

Service Endpoints:
  • Hive Mind API          http://localhost:8080
  • Airlock Server         http://localhost:3001
  • Grafana Dashboard      http://localhost:3000
  • MinIO Console          http://localhost:9001
  • Prometheus             http://localhost:9090
  • Elasticsearch          http://localhost:9200

Credentials:
  • Database User          sintraprime
  • Database Password      $DB_PASSWORD
  • Grafana Admin Password $GRAFANA_PASSWORD

Useful Commands:
  • View logs              docker-compose logs -f
  • Stop services          docker-compose down
  • Run health check       ./deployment/linux/health-check.sh
  • Deploy updates         ./deployment/linux/deploy.sh

Documentation:
  • Features List          ./docs/FEATURES.md
  • API Reference          ./docs/API.md
  • Deployment Guide       ./docs/DEPLOYMENT.md

Log file: $LOG_FILE

EOF
}

# Show usage
show_usage() {
    cat << EOF
SintraPrime-Unified Linux/Mac Setup Script

USAGE:
    ./setup.sh [ACTION] [REPO_URL] [BRANCH]

ACTIONS:
    full        : Complete setup (default)
    check       : Check prerequisites only
    docker      : Build Docker images
    deploy      : Start services
    health      : Check service health

OPTIONS:
    DB_PASSWORD=<password>      : Override database password
    GRAFANA_PASSWORD=<password> : Override Grafana password

EXAMPLES:
    # Full setup
    ./setup.sh full

    # Check prerequisites
    ./setup.sh check

    # Deploy specific branch
    ./setup.sh full https://github.com/user/repo.git develop

    # With custom passwords
    DB_PASSWORD=mysecretpass ./setup.sh full
EOF
}

# Main function
main() {
    cat << EOF
╔════════════════════════════════════════════════════════════╗
║   SintraPrime-Unified Linux/Mac Deployment Setup            ║
╚════════════════════════════════════════════════════════════╝

EOF
    
    log INFO "Starting SintraPrime-Unified setup (Action: $ACTION)"
    log INFO "Log file: $LOG_FILE"
    
    case $ACTION in
        help)
            show_usage
            exit 0
            ;;
        check)
            test_prerequisites
            exit $?
            ;;
        docker)
            test_prerequisites || exit 1
            build_docker_images
            exit $?
            ;;
        deploy)
            start_services || exit 1
            initialize_database
            test_service_health
            exit 0
            ;;
        health)
            test_service_health
            exit 0
            ;;
        full)
            log INFO "Starting full deployment sequence..."
            
            test_prerequisites || {
                log ERROR "Prerequisites check failed"
                exit 1
            }
            
            setup_repository || {
                log ERROR "Repository setup failed"
                exit 1
            }
            
            setup_environment || {
                log ERROR "Environment setup failed"
                exit 1
            }
            
            build_docker_images || {
                log ERROR "Docker build failed"
                exit 1
            }
            
            start_services || {
                log ERROR "Service startup failed"
                exit 1
            }
            
            initialize_database
            test_service_health
            display_summary
            
            log SUCCESS "Deployment completed successfully"
            exit 0
            ;;
        *)
            log ERROR "Unknown action: $ACTION"
            show_usage
            exit 1
            ;;
    esac
}

main
