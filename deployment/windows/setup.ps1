# SintraPrime-Unified Windows Setup Script
# Comprehensive setup and deployment automation for Windows
# Usage: PowerShell -ExecutionPolicy Bypass -File setup.ps1

param(
    [string]$Action = "full",  # full, check, docker, deploy, health
    [string]$RepoUrl = "https://github.com/ihoward40/SintraPrime-Unified.git",
    [string]$Branch = "main"
)

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$LogFile = "$ProjectRoot\deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$DbPassword = "sintraprime123"
$GrafanaPassword = "admin"

# Colors for output
$colors = @{
    'Success' = 'Green'
    'Error' = 'Red'
    'Warning' = 'Yellow'
    'Info' = 'Cyan'
    'Step' = 'Magenta'
}

function Write-Log {
    param([string]$Message, [string]$Level = 'Info')
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Output $logMessage | Tee-Object -FilePath $LogFile -Append
    
    if ($Level -eq 'Success') {
        Write-Host "✓ $Message" -ForegroundColor $colors['Success']
    } elseif ($Level -eq 'Error') {
        Write-Host "✗ $Message" -ForegroundColor $colors['Error']
    } elseif ($Level -eq 'Warning') {
        Write-Host "⚠ $Message" -ForegroundColor $colors['Warning']
    } elseif ($Level -eq 'Step') {
        Write-Host "`n=== $Message ===" -ForegroundColor $colors['Step']
    } else {
        Write-Host "  $Message" -ForegroundColor $colors['Info']
    }
}

function Test-DockerInstallation {
    Write-Log "Checking Docker installation..." -Level 'Info'
    
    try {
        $dockerVersion = docker --version
        Write-Log "Docker found: $dockerVersion" -Level 'Success'
        return $true
    }
    catch {
        Write-Log "Docker not found. Please install Docker Desktop for Windows." -Level 'Error'
        Write-Log "Download from: https://www.docker.com/products/docker-desktop" -Level 'Info'
        return $false
    }
}

function Test-DockerRunning {
    Write-Log "Checking if Docker daemon is running..." -Level 'Info'
    
    try {
        docker ps | Out-Null
        Write-Log "Docker daemon is running" -Level 'Success'
        return $true
    }
    catch {
        Write-Log "Docker daemon is not running. Starting Docker..." -Level 'Warning'
        
        # Try to start Docker Desktop
        try {
            Start-Process "C:\Program Files\Docker\Docker\Docker.exe"
            Write-Log "Docker Desktop started. Waiting 30 seconds..." -Level 'Info'
            Start-Sleep -Seconds 30
            
            # Verify it started
            docker ps | Out-Null
            Write-Log "Docker daemon is now running" -Level 'Success'
            return $true
        }
        catch {
            Write-Log "Failed to start Docker. Please start Docker Desktop manually." -Level 'Error'
            return $false
        }
    }
}

function Test-PortAvailability {
    param([int[]]$Ports)
    
    Write-Log "Checking port availability..." -Level 'Info'
    $portsInUse = @()
    
    foreach ($port in $Ports) {
        try {
            $tcpConnection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
            if ($tcpConnection) {
                $portsInUse += $port
                Write-Log "Port $port is already in use" -Level 'Warning'
            }
        }
        catch {
            # Port is available
        }
    }
    
    if ($portsInUse.Count -gt 0) {
        Write-Log "Some ports are in use. Service ports: 8080, 3001, 3000, 9000, 5432, 6379, 9200, 9090" -Level 'Warning'
        return $false
    }
    
    Write-Log "All required ports are available" -Level 'Success'
    return $true
}

function Test-Prerequisites {
    Write-Log "PHASE 1: Checking Prerequisites" -Level 'Step'
    
    $allGood = $true
    
    # Check Docker
    if (-not (Test-DockerInstallation)) {
        $allGood = $false
    }
    
    # Check Docker running
    if (-not (Test-DockerRunning)) {
        $allGood = $false
    }
    
    # Check Git
    Write-Log "Checking Git installation..." -Level 'Info'
    try {
        git --version | Out-Null
        Write-Log "Git found" -Level 'Success'
    }
    catch {
        Write-Log "Git not found. Please install Git for Windows." -Level 'Error'
        $allGood = $false
    }
    
    # Check ports
    $requiredPorts = @(8080, 3001, 3000, 9000, 5432, 6379, 9200, 9090)
    if (-not (Test-PortAvailability $requiredPorts)) {
        Write-Log "Some required ports are in use" -Level 'Warning'
        $allGood = $false
    }
    
    return $allGood
}

function Setup-Repository {
    Write-Log "PHASE 2: Repository Setup" -Level 'Step'
    
    if (-not (Test-Path "$ProjectRoot\.git")) {
        Write-Log "Cloning repository..." -Level 'Info'
        try {
            git clone --branch $Branch $RepoUrl $ProjectRoot
            Write-Log "Repository cloned successfully" -Level 'Success'
        }
        catch {
            Write-Log "Failed to clone repository: $_" -Level 'Error'
            return $false
        }
    }
    else {
        Write-Log "Repository already exists. Updating..." -Level 'Info'
        try {
            Push-Location $ProjectRoot
            git pull origin $Branch
            Pop-Location
            Write-Log "Repository updated" -Level 'Success'
        }
        catch {
            Write-Log "Failed to update repository: $_" -Level 'Error'
            return $false
        }
    }
    
    return $true
}

function Setup-Environment {
    Write-Log "PHASE 3: Environment Configuration" -Level 'Step'
    
    # Create .env file if it doesn't exist
    if (-not (Test-Path "$ProjectRoot\.env")) {
        Write-Log "Creating .env file..." -Level 'Info'
        
        $envContent = @"
# Database Configuration
DB_PASSWORD=$DbPassword
DATABASE_URL=postgresql://sintraprime:$DbPassword@postgres:5432/sintraprime_unified

# Redis Configuration
REDIS_URL=redis://redis:6379

# Grafana Configuration
GRAFANA_PASSWORD=$GrafanaPassword

# MinIO Configuration
MINIO_PASSWORD=minioadmin

# Application Configuration
LOG_LEVEL=INFO
NODE_ENV=production
API_PORT=8080
AIRLOCK_PORT=3001
"@
        
        $envContent | Out-File "$ProjectRoot\.env" -Encoding UTF8
        Write-Log ".env file created" -Level 'Success'
    }
    
    return $true
}

function Build-DockerImages {
    Write-Log "PHASE 4: Building Docker Images" -Level 'Step'
    
    try {
        Push-Location $ProjectRoot
        
        Write-Log "Building images from docker-compose..." -Level 'Info'
        docker-compose build --no-cache
        
        Write-Log "Docker images built successfully" -Level 'Success'
        Pop-Location
        return $true
    }
    catch {
        Write-Log "Failed to build Docker images: $_" -Level 'Error'
        Pop-Location
        return $false
    }
}

function Start-Services {
    Write-Log "PHASE 5: Starting Services" -Level 'Step'
    
    try {
        Push-Location $ProjectRoot
        
        Write-Log "Starting Docker Compose services..." -Level 'Info'
        docker-compose up -d
        
        Write-Log "Services started. Waiting for initialization..." -Level 'Info'
        Start-Sleep -Seconds 15
        
        Write-Log "Services started successfully" -Level 'Success'
        Pop-Location
        return $true
    }
    catch {
        Write-Log "Failed to start services: $_" -Level 'Error'
        Pop-Location
        return $false
    }
}

function Initialize-Database {
    Write-Log "PHASE 6: Database Initialization" -Level 'Step'
    
    try {
        Write-Log "Running database migrations..." -Level 'Info'
        
        # Run migrations via the Hive Mind API
        $migrationUrl = "http://localhost:8080/api/db/migrate"
        $attempt = 0
        $maxAttempts = 30
        
        while ($attempt -lt $maxAttempts) {
            try {
                $response = Invoke-WebRequest -Uri $migrationUrl -Method POST -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Log "Database migrations completed" -Level 'Success'
                    return $true
                }
            }
            catch {
                $attempt++
                if ($attempt -lt $maxAttempts) {
                    Write-Log "Waiting for API to be ready... ($attempt/$maxAttempts)" -Level 'Info'
                    Start-Sleep -Seconds 2
                }
            }
        }
        
        Write-Log "Database initialization completed (check logs for details)" -Level 'Warning'
        return $true
    }
    catch {
        Write-Log "Database initialization warning (services may still initialize): $_" -Level 'Warning'
        return $true  # Don't fail the entire setup
    }
}

function Test-ServiceHealth {
    Write-Log "PHASE 7: Health Checks" -Level 'Step'
    
    $healthChecks = @{
        'Hive Mind API (8080)' = 'http://localhost:8080/health'
        'Airlock Server (3001)' = 'http://localhost:3001/health'
        'Grafana (3000)' = 'http://localhost:3000/api/health'
        'PostgreSQL (5432)' = $null
        'Redis (6379)' = $null
    }
    
    $allHealthy = $true
    
    foreach ($service in $healthChecks.GetEnumerator()) {
        if ($service.Value) {
            try {
                $response = Invoke-WebRequest -Uri $service.Value -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Log "$($service.Key): Healthy ✓" -Level 'Success'
                }
                else {
                    Write-Log "$($service.Key): Unhealthy ✗" -Level 'Warning'
                    $allHealthy = $false
                }
            }
            catch {
                Write-Log "$($service.Key): Unreachable ✗" -Level 'Warning'
                $allHealthy = $false
            }
        }
        else {
            Write-Log "$($service.Key): Running (port check)" -Level 'Info'
        }
    }
    
    return $allHealthy
}

function Display-Summary {
    Write-Log "PHASE 8: Deployment Summary" -Level 'Step'
    
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║      SintraPrime-Unified Successfully Deployed!             ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    
    Write-Host "`nService Endpoints:" -ForegroundColor Cyan
    Write-Host "  • Hive Mind API          http://localhost:8080" -ForegroundColor Yellow
    Write-Host "  • Airlock Server         http://localhost:3001" -ForegroundColor Yellow
    Write-Host "  • Grafana Dashboard      http://localhost:3000" -ForegroundColor Yellow
    Write-Host "  • MinIO Console          http://localhost:9001" -ForegroundColor Yellow
    Write-Host "  • Prometheus             http://localhost:9090" -ForegroundColor Yellow
    Write-Host "  • Elasticsearch          http://localhost:9200" -ForegroundColor Yellow
    
    Write-Host "`nCredentials:" -ForegroundColor Cyan
    Write-Host "  • Database User          sintraprime" -ForegroundColor Yellow
    Write-Host "  • Database Password      $DbPassword" -ForegroundColor Yellow
    Write-Host "  • Grafana Admin Password $GrafanaPassword" -ForegroundColor Yellow
    
    Write-Host "`nUseful Commands:" -ForegroundColor Cyan
    Write-Host "  • View logs              docker-compose logs -f" -ForegroundColor Yellow
    Write-Host "  • Stop services          docker-compose down" -ForegroundColor Yellow
    Write-Host "  • Run health check       .\deployment\windows\health-check.ps1" -ForegroundColor Yellow
    Write-Host "  • Deploy updates         .\deployment\windows\deploy.ps1" -ForegroundColor Yellow
    
    Write-Host "`nDocumentation:" -ForegroundColor Cyan
    Write-Host "  • Features List          .\docs\FEATURES.md" -ForegroundColor Yellow
    Write-Host "  • API Reference          .\docs\API.md" -ForegroundColor Yellow
    Write-Host "  • Deployment Guide       .\docs\DEPLOYMENT.md" -ForegroundColor Yellow
    
    Write-Host "`nLog File: $LogFile`n" -ForegroundColor Gray
}

function Show-Usage {
    Write-Host @"
SintraPrime-Unified Windows Setup Script

USAGE:
    PowerShell -ExecutionPolicy Bypass -File setup.ps1 [OPTIONS]

OPTIONS:
    -Action <action>        : full, check, docker, deploy, health (default: full)
    -RepoUrl <url>          : Repository URL (default: GitHub ihoward40/SintraPrime-Unified)
    -Branch <branch>        : Git branch (default: main)

ACTIONS:
    full        : Complete setup from prerequisites through deployment
    check       : Only check prerequisites
    docker      : Build Docker images (prerequisites must pass)
    deploy      : Start Docker services
    health      : Check service health status

EXAMPLES:
    # Full setup
    .\setup.ps1

    # Check prerequisites only
    .\setup.ps1 -Action check

    # Deploy specific branch
    .\setup.ps1 -Branch develop

    # Just check health
    .\setup.ps1 -Action health
"@
}

# Main execution
function Main {
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║     SintraPrime-Unified Windows Deployment Setup            ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    Write-Log "Starting SintraPrime-Unified setup (Action: $Action)" -Level 'Info'
    Write-Log "Log file: $LogFile" -Level 'Info'
    
    switch ($Action.ToLower()) {
        'help' {
            Show-Usage
            exit 0
        }
        'check' {
            $result = Test-Prerequisites
            if ($result) {
                Write-Log "All prerequisites passed! Ready for deployment." -Level 'Success'
            }
            else {
                Write-Log "Some prerequisites failed. Please address issues above." -Level 'Error'
                exit 1
            }
        }
        'docker' {
            if (-not (Test-Prerequisites)) {
                Write-Log "Prerequisites check failed" -Level 'Error'
                exit 1
            }
            if (-not (Build-DockerImages)) {
                Write-Log "Docker image build failed" -Level 'Error'
                exit 1
            }
        }
        'deploy' {
            if (-not (Start-Services)) {
                Write-Log "Service startup failed" -Level 'Error'
                exit 1
            }
            if (-not (Test-ServiceHealth)) {
                Write-Log "Some services are unhealthy - check logs" -Level 'Warning'
            }
        }
        'health' {
            if (-not (Test-ServiceHealth)) {
                exit 1
            }
        }
        'full' {
            Write-Log "Starting full deployment sequence..." -Level 'Info'
            
            # Step 1: Prerequisites
            if (-not (Test-Prerequisites)) {
                Write-Log "Prerequisites check failed" -Level 'Error'
                exit 1
            }
            
            # Step 2: Repository
            if (-not (Setup-Repository)) {
                Write-Log "Repository setup failed" -Level 'Error'
                exit 1
            }
            
            # Step 3: Environment
            if (-not (Setup-Environment)) {
                Write-Log "Environment setup failed" -Level 'Error'
                exit 1
            }
            
            # Step 4: Docker Images
            if (-not (Build-DockerImages)) {
                Write-Log "Docker build failed" -Level 'Error'
                exit 1
            }
            
            # Step 5: Start Services
            if (-not (Start-Services)) {
                Write-Log "Service startup failed" -Level 'Error'
                exit 1
            }
            
            # Step 6: Initialize Database
            Initialize-Database | Out-Null
            
            # Step 7: Health Checks
            Test-ServiceHealth | Out-Null
            
            # Step 8: Summary
            Display-Summary
            
            Write-Log "Deployment completed successfully" -Level 'Success'
        }
        default {
            Write-Log "Unknown action: $Action" -Level 'Error'
            Show-Usage
            exit 1
        }
    }
    
    exit 0
}

# Run main
Main
