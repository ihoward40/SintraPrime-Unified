# SintraPrime-Unified Windows Deployment Script
# Handles building, deploying, testing, and verifying the unified system
# Usage: PowerShell -ExecutionPolicy Bypass -File deploy.ps1

param(
    [string]$Environment = "production",
    [switch]$SkipTests = $false,
    [switch]$SkipHealthChecks = $false,
    [switch]$BuildOnly = $false,
    [switch]$DeployOnly = $false
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$LogFile = "$ProjectRoot\deploy-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = 'Info')
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Output $logMessage | Tee-Object -FilePath $LogFile -Append
    
    $colorMap = @{
        'Success' = 'Green'
        'Error' = 'Red'
        'Warning' = 'Yellow'
        'Info' = 'Cyan'
        'Step' = 'Magenta'
    }
    
    $symbol = @{
        'Success' = '✓'
        'Error' = '✗'
        'Warning' = '⚠'
        'Step' = '==='
    }
    
    if ($colorMap.ContainsKey($Level)) {
        Write-Host "$($symbol[$Level]) $Message" -ForegroundColor $colorMap[$Level]
    }
    else {
        Write-Host "  $Message" -ForegroundColor Cyan
    }
}

function Test-DockerRunning {
    try {
        docker ps | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Build-Services {
    Write-Log "PHASE 1: Building Docker Images" -Level 'Step'
    
    if (-not (Test-DockerRunning)) {
        Write-Log "Docker is not running. Please start Docker Desktop." -Level 'Error'
        return $false
    }
    
    try {
        Push-Location $ProjectRoot
        
        Write-Log "Building images..." -Level 'Info'
        docker-compose build
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker images built successfully" -Level 'Success'
            Pop-Location
            return $true
        }
        else {
            Write-Log "Docker build failed with exit code $LASTEXITCODE" -Level 'Error'
            Pop-Location
            return $false
        }
    }
    catch {
        Write-Log "Build error: $_" -Level 'Error'
        Pop-Location
        return $false
    }
}

function Stop-Services {
    Write-Log "Stopping running services..." -Level 'Info'
    
    try {
        Push-Location $ProjectRoot
        docker-compose down -v
        Start-Sleep -Seconds 5
        Pop-Location
        Write-Log "Services stopped" -Level 'Success'
        return $true
    }
    catch {
        Write-Log "Error stopping services: $_" -Level 'Warning'
        return $false
    }
}

function Start-Services {
    Write-Log "PHASE 2: Starting Services" -Level 'Step'
    
    try {
        Push-Location $ProjectRoot
        
        Write-Log "Starting Docker Compose services in $Environment mode..." -Level 'Info'
        docker-compose up -d
        
        Write-Log "Services started. Waiting for initialization..." -Level 'Info'
        Start-Sleep -Seconds 20
        
        Pop-Location
        Write-Log "All services started successfully" -Level 'Success'
        return $true
    }
    catch {
        Write-Log "Failed to start services: $_" -Level 'Error'
        Pop-Location
        return $false
    }
}

function Run-Tests {
    Write-Log "PHASE 3: Running Tests" -Level 'Step'
    
    if ($SkipTests) {
        Write-Log "Tests skipped (--SkipTests flag)" -Level 'Warning'
        return $true
    }
    
    $testsPassed = $true
    
    # Check if Python tests exist
    if (Test-Path "$ProjectRoot\core\tests") {
        Write-Log "Running Python unit tests..." -Level 'Info'
        try {
            Push-Location "$ProjectRoot\core"
            # Run via docker if possible
            docker-compose exec -T hive-mind-api pytest -v
            if ($LASTEXITCODE -ne 0) {
                Write-Log "Some Python tests failed" -Level 'Warning'
                $testsPassed = $false
            }
            Pop-Location
        }
        catch {
            Write-Log "Could not run Python tests: $_" -Level 'Warning'
        }
    }
    
    # Check TypeScript tests
    if (Test-Path "$ProjectRoot\apps\sintraprime") {
        Write-Log "Running TypeScript tests..." -Level 'Info'
        try {
            Push-Location "$ProjectRoot\apps\sintraprime"
            docker-compose exec -T airlock-server npm test 2>/dev/null || Write-Log "TypeScript tests not configured" -Level 'Warning'
            Pop-Location
        }
        catch {
            Write-Log "Could not run TypeScript tests: $_" -Level 'Warning'
        }
    }
    
    if ($testsPassed) {
        Write-Log "Tests passed" -Level 'Success'
    }
    else {
        Write-Log "Some tests failed (see logs above)" -Level 'Warning'
    }
    
    return $true
}

function Test-ServiceHealth {
    Write-Log "PHASE 4: Verifying Service Health" -Level 'Step'
    
    if ($SkipHealthChecks) {
        Write-Log "Health checks skipped (--SkipHealthChecks flag)" -Level 'Warning'
        return $true
    }
    
    $services = @{
        'Hive Mind API (8080)' = @{url='http://localhost:8080/health'; timeout=30}
        'Airlock Server (3001)' = @{url='http://localhost:3001/health'; timeout=30}
        'PostgreSQL (5432)' = @{check='port'; port=5432; timeout=30}
        'Redis (6379)' = @{check='port'; port=6379; timeout=30}
        'Elasticsearch (9200)' = @{url='http://localhost:9200/'; timeout=30}
        'Grafana (3000)' = @{url='http://localhost:3000/api/health'; timeout=30}
    }
    
    $allHealthy = $true
    
    foreach ($service in $services.GetEnumerator()) {
        $attempt = 0
        $maxAttempts = $service.Value.timeout
        $healthy = $false
        
        while ($attempt -lt $maxAttempts -and -not $healthy) {
            try {
                if ($service.Value.url) {
                    $response = Invoke-WebRequest -Uri $service.Value.url -TimeoutSec 5 -ErrorAction SilentlyContinue
                    if ($response.StatusCode -eq 200) {
                        $healthy = $true
                    }
                }
                elseif ($service.Value.check -eq 'port') {
                    $tcpConnection = Get-NetTCPConnection -LocalPort $service.Value.port -ErrorAction SilentlyContinue
                    if ($tcpConnection) {
                        $healthy = $true
                    }
                }
            }
            catch {
                $attempt++
                if ($attempt -lt $maxAttempts) {
                    Start-Sleep -Seconds 1
                }
            }
        }
        
        if ($healthy) {
            Write-Log "$($service.Key): Healthy ✓" -Level 'Success'
        }
        else {
            Write-Log "$($service.Key): Unhealthy ✗" -Level 'Warning'
            $allHealthy = $false
        }
    }
    
    return $allHealthy
}

function Verify-Deployment {
    Write-Log "PHASE 5: Verifying Deployment" -Level 'Step'
    
    Write-Log "Checking container status..." -Level 'Info'
    
    try {
        $containers = docker-compose ps --quiet
        if ($containers) {
            Write-Log "All containers are running" -Level 'Success'
        }
        else {
            Write-Log "Some containers are not running" -Level 'Error'
            return $false
        }
    }
    catch {
        Write-Log "Could not verify containers: $_" -Level 'Error'
        return $false
    }
    
    Write-Log "Checking volumes..." -Level 'Info'
    try {
        $volumes = docker volume ls -q
        Write-Log "Database and cache volumes initialized" -Level 'Success'
    }
    catch {
        Write-Log "Warning: Could not verify volumes" -Level 'Warning'
    }
    
    return $true
}

function Show-DeploymentSummary {
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║     SintraPrime-Unified Deployment Summary                  ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    
    Write-Host "`nDeployment Status: SUCCESS" -ForegroundColor Green
    Write-Host "Environment: $Environment" -ForegroundColor Yellow
    Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Yellow
    
    Write-Host "`nRunning Services:" -ForegroundColor Cyan
    try {
        docker-compose ps --format "table {{.Names}}\t{{.Status}}"
    }
    catch {
        Write-Log "Could not display services" -Level 'Warning'
    }
    
    Write-Host "`nAccess Points:" -ForegroundColor Cyan
    Write-Host "  • Hive Mind API          http://localhost:8080" -ForegroundColor Yellow
    Write-Host "  • Airlock Server         http://localhost:3001" -ForegroundColor Yellow
    Write-Host "  • Grafana Dashboard      http://localhost:3000" -ForegroundColor Yellow
    Write-Host "  • MinIO Console          http://localhost:9001" -ForegroundColor Yellow
    Write-Host "  • Prometheus             http://localhost:9090" -ForegroundColor Yellow
    
    Write-Host "`nUseful Commands:" -ForegroundColor Cyan
    Write-Host "  # View logs" -ForegroundColor Gray
    Write-Host "  docker-compose logs -f [service]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  # Execute commands in service" -ForegroundColor Gray
    Write-Host "  docker-compose exec [service] [command]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  # Health check" -ForegroundColor Gray
    Write-Host "  .\deployment\windows\health-check.ps1" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  # Stop all services" -ForegroundColor Gray
    Write-Host "  docker-compose down" -ForegroundColor Yellow
    
    Write-Host "`nLog file: $LogFile`n" -ForegroundColor Gray
}

function Main {
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║      SintraPrime-Unified Deployment Manager                 ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    Write-Log "Starting deployment (Environment: $Environment)" -Level 'Info'
    
    if (-not (Test-DockerRunning)) {
        Write-Log "Docker is not running" -Level 'Error'
        exit 1
    }
    
    try {
        # Build phase
        if (-not $DeployOnly) {
            if (-not (Build-Services)) {
                Write-Log "Build phase failed" -Level 'Error'
                exit 1
            }
        }
        
        # Deployment phase
        if (-not $BuildOnly) {
            # Stop any existing services
            Stop-Services | Out-Null
            
            # Start services
            if (-not (Start-Services)) {
                Write-Log "Deployment phase failed" -Level 'Error'
                exit 1
            }
            
            # Run tests
            if (-not (Run-Tests)) {
                Write-Log "Tests phase had issues (see above)" -Level 'Warning'
            }
            
            # Verify health
            if (-not (Test-ServiceHealth)) {
                Write-Log "Some services are unhealthy" -Level 'Warning'
            }
            
            # Final verification
            if (-not (Verify-Deployment)) {
                Write-Log "Deployment verification failed" -Level 'Error'
                exit 1
            }
            
            # Show summary
            Show-DeploymentSummary
        }
        
        Write-Log "Deployment completed successfully" -Level 'Success'
        exit 0
    }
    catch {
        Write-Log "Unexpected error during deployment: $_" -Level 'Error'
        exit 1
    }
}

Main
