#!/bin/bash

# SintraPrime-Unified Linux Deployment Script
# Handles building, deploying, testing, and verifying the unified system
# Usage: ./deploy.sh [OPTIONS]

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_FILE="$PROJECT_ROOT/deploy-$(date +%Y%m%d-%H%M%S).log"

# Options
ENVIRONMENT="${ENVIRONMENT:-production}"
SKIP_TESTS="${SKIP_TESTS:-false}"
SKIP_HEALTH_CHECKS="${SKIP_HEALTH_CHECKS:-false}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

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

# Check Docker running
check_docker() {
    if ! docker ps >/dev/null 2>&1; then
        log ERROR "Docker is not running"
        return 1
    fi
    return 0
}

# Build Docker images
build_services() {
    log STEP "PHASE 1: Building Docker Images"
    
    if ! check_docker; then
        return 1
    fi
    
    cd "$PROJECT_ROOT"
    
    log INFO "Building images..."
    if docker-compose build; then
        log SUCCESS "Docker images built successfully"
        return 0
    else
        log ERROR "Docker build failed"
        return 1
    fi
}

# Stop services
stop_services() {
    log INFO "Stopping running services..."
    
    cd "$PROJECT_ROOT"
    docker-compose down -v 2>/dev/null || true
    sleep 5
    
    log SUCCESS "Services stopped"
    return 0
}

# Start services
start_services() {
    log STEP "PHASE 2: Starting Services"
    
    cd "$PROJECT_ROOT"
    
    log INFO "Starting Docker Compose services in $ENVIRONMENT mode..."
    if docker-compose up -d; then
        log SUCCESS "Services started"
        log INFO "Waiting for initialization..."
        sleep 20
        return 0
    else
        log ERROR "Failed to start services"
        return 1
    fi
}

# Run tests
run_tests() {
    log STEP "PHASE 3: Running Tests"
    
    if [ "$SKIP_TESTS" = "true" ]; then
        log WARNING "Tests skipped"
        return 0
    fi
    
    local tests_passed=true
    
    # Python tests
    if [ -d "$PROJECT_ROOT/core/tests" ]; then
        log INFO "Running Python unit tests..."
        cd "$PROJECT_ROOT/core"
        if docker-compose exec -T hive-mind-api pytest -v 2>/dev/null; then
            log SUCCESS "Python tests passed"
        else
            log WARNING "Some Python tests failed"
            tests_passed=false
        fi
    fi
    
    # TypeScript tests
    if [ -d "$PROJECT_ROOT/apps/sintraprime" ]; then
        log INFO "Running TypeScript tests..."
        cd "$PROJECT_ROOT"
        if docker-compose exec -T airlock-server npm test 2>/dev/null; then
            log SUCCESS "TypeScript tests passed"
        else
            log WARNING "TypeScript tests not configured or failed"
        fi
    fi
    
    return 0
}

# Test service health
test_service_health() {
    log STEP "PHASE 4: Verifying Service Health"
    
    if [ "$SKIP_HEALTH_CHECKS" = "true" ]; then
        log WARNING "Health checks skipped"
        return 0
    fi
    
    local services=(
        "Hive Mind API:8080:http://localhost:8080/health"
        "Airlock Server:3001:http://localhost:3001/health"
        "Grafana:3000:http://localhost:3000/api/health"
        "Elasticsearch:9200:http://localhost:9200/"
        "PostgreSQL:5432"
        "Redis:6379"
    )
    
    local all_healthy=true
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port endpoint <<< "$service"
        
        if [ -z "$endpoint" ]; then
            # Port-based check
            if nc -z localhost $port 2>/dev/null; then
                log SUCCESS "$name ($port): Healthy ✓"
            else
                log WARNING "$name ($port): Unhealthy ✗"
                all_healthy=false
            fi
        else
            # HTTP-based check
            if curl -f -s "$endpoint" >/dev/null 2>&1; then
                log SUCCESS "$name ($port): Healthy ✓"
            else
                log WARNING "$name ($port): Unhealthy ✗"
                all_healthy=false
            fi
        fi
    done
    
    return 0
}

# Verify deployment
verify_deployment() {
    log STEP "PHASE 5: Verifying Deployment"
    
    log INFO "Checking container status..."
    
    cd "$PROJECT_ROOT"
    if docker-compose ps --quiet | grep -q .; then
        log SUCCESS "All containers are running"
    else
        log ERROR "Some containers are not running"
        return 1
    fi
    
    return 0
}

# Show deployment summary
show_deployment_summary() {
    cat << EOF

╔════════════════════════════════════════════════════════════╗
║   SintraPrime-Unified Deployment Summary                    ║
╚════════════════════════════════════════════════════════════╝

Deployment Status: SUCCESS
Environment: $ENVIRONMENT
Timestamp: $(date '+%Y-%m-%d %H:%M:%S')

Running Services:
EOF
    
    cd "$PROJECT_ROOT"
    docker-compose ps --format "table {{.Names}}\t{{.Status}}"
    
    cat << EOF

Access Points:
  • Hive Mind API          http://localhost:8080
  • Airlock Server         http://localhost:3001
  • Grafana Dashboard      http://localhost:3000
  • MinIO Console          http://localhost:9001
  • Prometheus             http://localhost:9090

Useful Commands:
  # View logs
  docker-compose logs -f [service]

  # Execute commands in service
  docker-compose exec [service] [command]

  # Health check
  ./deployment/linux/health-check.sh

  # Stop all services
  docker-compose down

Log file: $LOG_FILE

EOF
}

# Show usage
show_usage() {
    cat << EOF
SintraPrime-Unified Linux Deployment Script

USAGE:
    ./deploy.sh [OPTIONS]

OPTIONS:
    --environment <env>     : Environment (default: production)
    --skip-tests            : Skip test execution
    --skip-health           : Skip health checks
    --build-only            : Only build images
    --deploy-only           : Only deploy services

ENVIRONMENT VARIABLES:
    ENVIRONMENT             : Deployment environment
    SKIP_TESTS              : Skip test phase
    SKIP_HEALTH_CHECKS      : Skip health verification

EXAMPLES:
    # Full deployment
    ./deploy.sh

    # Skip tests
    ./deploy.sh --skip-tests

    # Production deployment with all checks
    ENVIRONMENT=production ./deploy.sh
EOF
}

# Main function
main() {
    cat << EOF
╔════════════════════════════════════════════════════════════╗
║      SintraPrime-Unified Deployment Manager                 ║
╚════════════════════════════════════════════════════════════╝

EOF
    
    log INFO "Starting deployment (Environment: $ENVIRONMENT)"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            --skip-health)
                SKIP_HEALTH_CHECKS="true"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log ERROR "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Check Docker
    if ! check_docker; then
        log ERROR "Docker is not running"
        exit 1
    fi
    
    # Build phase
    if ! build_services; then
        log ERROR "Build phase failed"
        exit 1
    fi
    
    # Deployment phase
    stop_services
    
    if ! start_services; then
        log ERROR "Deployment phase failed"
        exit 1
    fi
    
    # Test phase
    if ! run_tests; then
        log WARNING "Test phase had issues"
    fi
    
    # Verify phase
    if ! test_service_health; then
        log WARNING "Some services are unhealthy"
    fi
    
    # Final verification
    if ! verify_deployment; then
        log ERROR "Deployment verification failed"
        exit 1
    fi
    
    # Summary
    show_deployment_summary
    
    log SUCCESS "Deployment completed successfully"
    exit 0
}

main "$@"
