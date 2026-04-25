#Requires -Version 5.1
<#
.SYNOPSIS
    SintraPrime-Unified Windows Setup Script
    One-command deployment for Windows with Docker Desktop

.DESCRIPTION
    This script installs and starts the full SintraPrime-Unified platform:
      - PostgreSQL 15        (port 5432)
      - Redis 7              (port 6379)
      - SintraPrime API      (port 8080)
      - Elasticsearch        (port 9200)
      - Grafana              (port 3000)
      - Prometheus           (port 9090)
      - Airlock Server       (port 3001)
      - MinIO                (port 9000/9001)
      - Twin Display         (port 8765)
      - Nginx Reverse Proxy  (port 80)

.PARAMETER InstallPath
    Target installation directory. Default: C:\SintraPrime-Unified

.PARAMETER SkipDockerCheck
    Skip Docker Desktop availability checks (for CI/automated environments)

.PARAMETER SkipDependencies
    Skip dependency checks (Node.js, Python, Git)

.PARAMETER SkipBuild
    Skip docker-compose build step (use cached images only)

.PARAMETER Verbose
    Enable verbose output

.EXAMPLE
    .\SETUP_WINDOWS.ps1
    .\SETUP_WINDOWS.ps1 -InstallPath "D:\Apps\SintraPrime"
    .\SETUP_WINDOWS.ps1 -SkipDependencies -Verbose

.NOTES
    Must be run as Administrator.
    Requires Docker Desktop for Windows.
    Author: SintraPrime Team
    Version: 2.0.0
#>

param(
    [string]$InstallPath = "C:\SintraPrime-Unified",
    [switch]$SkipDockerCheck,
    [switch]$SkipDependencies,
    [switch]$SkipBuild,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ============================================================
# CONSTANTS & CONFIGURATION
# ============================================================
$SCRIPT_VERSION = "2.0.0"
$SCRIPT_NAME    = "SintraPrime-Unified Setup"
$LOG_FILE       = "$env:TEMP\sintraprime-setup-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$SOURCE_PATH    = $PSScriptRoot

$SERVICES = @{
    "api"            = @{ Port = 8080; URL = "http://localhost:8080";  HealthPath = "/health"   }
    "airlock"        = @{ Port = 3001; URL = "http://localhost:3001";  HealthPath = "/health"   }
    "grafana"        = @{ Port = 3000; URL = "http://localhost:3000";  HealthPath = "/api/health" }
    "prometheus"     = @{ Port = 9090; URL = "http://localhost:9090";  HealthPath = "/-/healthy" }
    "elasticsearch"  = @{ Port = 9200; URL = "http://localhost:9200";  HealthPath = "/_cluster/health" }
    "minio"          = @{ Port = 9001; URL = "http://localhost:9001";  HealthPath = "" }
}

# ============================================================
# HELPER FUNCTIONS — Colors & Logging
# ============================================================
function Write-Banner {
    param([string]$Text, [ConsoleColor]$Color = "Cyan")
    $line = "=" * 70
    Write-Host ""
    Write-Host $line -ForegroundColor $Color
    Write-Host "  $Text" -ForegroundColor $Color
    Write-Host $line -ForegroundColor $Color
    Write-Host ""
}

function Write-Step {
    param([int]$Number, [string]$Total = "15", [string]$Text)
    Write-Host "  [Step $Number/$Total] " -NoNewline -ForegroundColor DarkCyan
    Write-Host $Text -ForegroundColor White
    Add-Content -Path $LOG_FILE -Value "[$(Get-Date -Format 'HH:mm:ss')] STEP $Number: $Text" -ErrorAction SilentlyContinue
}

function Write-OK {
    param([string]$Text)
    Write-Host "    [OK] " -NoNewline -ForegroundColor Green
    Write-Host $Text
}

function Write-WARN {
    param([string]$Text)
    Write-Host "  [WARN] " -NoNewline -ForegroundColor Yellow
    Write-Host $Text
}

function Write-FAIL {
    param([string]$Text)
    Write-Host "  [FAIL] " -NoNewline -ForegroundColor Red
    Write-Host $Text
}

function Write-INFO {
    param([string]$Text)
    Write-Host "  [....] " -NoNewline -ForegroundColor DarkGray
    Write-Host $Text
}

function Write-Log {
    param([string]$Text)
    Add-Content -Path $LOG_FILE -Value "[$(Get-Date -Format 'HH:mm:ss')] $Text" -ErrorAction SilentlyContinue
}

function Show-FixHint {
    param([string]$Problem, [string]$Fix)
    Write-Host ""
    Write-Host "  HOW TO FIX:" -ForegroundColor Yellow
    Write-Host "  Problem: $Problem" -ForegroundColor DarkYellow
    Write-Host "  Solution: $Fix" -ForegroundColor Cyan
    Write-Host ""
}

function Invoke-CommandSafely {
    param([string]$Command, [string]$Description, [switch]$CaptureOutput)
    Write-Log "Running: $Command"
    try {
        if ($CaptureOutput) {
            $result = Invoke-Expression $Command 2>&1
            Write-Log "Output: $result"
            return $result
        } else {
            Invoke-Expression $Command 2>&1 | ForEach-Object {
                Write-Log $_
                if ($VerbosePreference -eq 'Continue') { Write-Host "    $_" -ForegroundColor DarkGray }
            }
        }
    } catch {
        Write-Log "ERROR running '$Command': $_"
        throw
    }
}

function Test-PortAvailable {
    param([int]$Port)
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

function Get-RandomSecret {
    param([int]$Length = 32)
    $bytes = New-Object byte[] ($Length / 2)
    [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes)
    return [System.BitConverter]::ToString($bytes) -replace '-', ''
}

function Wait-ForHealthCheck {
    param(
        [string]$Url,
        [string]$ServiceName,
        [int]$TimeoutSeconds = 120,
        [int]$PollIntervalSeconds = 5
    )
    Write-INFO "Waiting for $ServiceName to become healthy..."
    $elapsed = 0
    $dots = ""
    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -in @(200, 201, 204)) {
                Write-OK "$ServiceName is healthy (${elapsed}s)"
                return $true
            }
        } catch {
            # Service not ready yet
        }
        $dots += "."
        Write-Host "    Waiting$dots ($elapsed/$TimeoutSeconds s)" -ForegroundColor DarkGray -NoNewline
        Write-Host "`r" -NoNewline
        Start-Sleep -Seconds $PollIntervalSeconds
        $elapsed += $PollIntervalSeconds
    }
    Write-WARN "$ServiceName did not respond within ${TimeoutSeconds}s (may still be starting)"
    return $false
}

# ============================================================
# STEP 1: Administrator Check
# ============================================================
function Test-Administrator {
    Write-Step -Number 1 -Text "Checking Administrator privileges"
    $currentUser = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-FAIL "This script must be run as Administrator!"
        Show-FixHint -Problem "Not running as Administrator" -Fix @"
Right-click PowerShell and select 'Run as Administrator', then run:
  cd '$SOURCE_PATH'
  .\SETUP_WINDOWS.ps1
"@
        exit 1
    }
    Write-OK "Running as Administrator"
}

# ============================================================
# STEP 2: Docker Desktop Check
# ============================================================
function Test-Docker {
    Write-Step -Number 2 -Text "Checking Docker Desktop"
    if ($SkipDockerCheck) {
        Write-WARN "Skipping Docker check (--SkipDockerCheck specified)"
        return
    }

    # Check if docker command exists
    $dockerCmd = Get-Command "docker" -ErrorAction SilentlyContinue
    if (-not $dockerCmd) {
        Write-FAIL "Docker Desktop is not installed!"
        Show-FixHint -Problem "Docker Desktop not found" -Fix @"
1. Download Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Install it (requires Windows 10/11 with WSL2 or Hyper-V)
3. Start Docker Desktop
4. Re-run this script
"@
        exit 1
    }

    # Check if docker daemon is running
    try {
        $dockerInfo = docker info 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Docker daemon not running"
        }
    } catch {
        Write-FAIL "Docker Desktop is installed but not running!"
        Show-FixHint -Problem "Docker daemon not running" -Fix @"
1. Open Docker Desktop from the Start menu or system tray
2. Wait for it to fully start (green indicator in taskbar)
3. Re-run this script
"@
        exit 1
    }

    # Check docker-compose
    $composeCmd = Get-Command "docker-compose" -ErrorAction SilentlyContinue
    if (-not $composeCmd) {
        # Try docker compose (v2 plugin)
        $composeV2 = docker compose version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-FAIL "docker-compose not found!"
            Show-FixHint -Problem "docker-compose not available" -Fix @"
Docker Compose is included with Docker Desktop.
Update Docker Desktop to the latest version: https://www.docker.com/products/docker-desktop/
"@
            exit 1
        }
        Write-OK "Docker Compose v2 detected"
    } else {
        Write-OK "docker-compose detected"
    }
    Write-OK "Docker Desktop is running"
}

# ============================================================
# STEP 3: Docker Resources Check
# ============================================================
function Test-DockerResources {
    Write-Step -Number 3 -Text "Checking Docker resource allocation"

    try {
        $dockerInfo = docker info --format "{{json .}}" 2>&1 | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($dockerInfo -and $dockerInfo.MemTotal) {
            $ramGB = [math]::Round($dockerInfo.MemTotal / 1GB, 1)
            if ($ramGB -lt 4) {
                Write-WARN "Docker has only ${ramGB}GB RAM. Recommended: 4GB+"
                Write-WARN "Increase Docker memory: Docker Desktop > Settings > Resources > Memory"
            } else {
                Write-OK "Docker RAM: ${ramGB}GB (sufficient)"
            }
        } else {
            Write-INFO "Could not read Docker memory info (non-critical)"
        }
    } catch {
        Write-INFO "Resource check skipped (non-critical)"
    }

    # Check available disk space
    $drive = Split-Path -Qualifier $InstallPath
    if (-not $drive) { $drive = "C:" }
    try {
        $disk = Get-PSDrive -Name ($drive.TrimEnd(':')) -ErrorAction SilentlyContinue
        if ($disk) {
            $freeGB = [math]::Round($disk.Free / 1GB, 1)
            if ($freeGB -lt 10) {
                Write-WARN "Low disk space: ${freeGB}GB free. Recommended: 10GB+"
            } else {
                Write-OK "Disk space: ${freeGB}GB free"
            }
        }
    } catch {
        Write-INFO "Disk space check skipped"
    }
}

# ============================================================
# STEP 4: Check Node.js
# ============================================================
function Test-NodeJS {
    Write-Step -Number 4 -Text "Checking Node.js (optional)"
    if ($SkipDependencies) {
        Write-INFO "Skipping Node.js check"
        return
    }

    $nodeCmd = Get-Command "node" -ErrorAction SilentlyContinue
    if (-not $nodeCmd) {
        Write-WARN "Node.js not found (optional — not required for Docker deployment)"
        Write-INFO "Install Node.js 18+ from: https://nodejs.org/en/download/"
        return
    }

    $nodeVersion = node --version 2>&1
    if ($nodeVersion -match 'v(\d+)') {
        $major = [int]$Matches[1]
        if ($major -ge 18) {
            Write-OK "Node.js $nodeVersion (>= 18)"
        } else {
            Write-WARN "Node.js $nodeVersion detected but 18+ recommended"
            Write-INFO "Upgrade: https://nodejs.org/en/download/"
        }
    }
}

# ============================================================
# STEP 5: Check Python
# ============================================================
function Test-Python {
    Write-Step -Number 5 -Text "Checking Python (optional)"
    if ($SkipDependencies) {
        Write-INFO "Skipping Python check"
        return
    }

    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue
    }

    if (-not $pythonCmd) {
        Write-WARN "Python not found (optional — not required for Docker deployment)"
        Write-INFO "Install Python 3.10+ from: https://www.python.org/downloads/"
        return
    }

    $pythonVersion = & $pythonCmd.Name --version 2>&1
    if ($pythonVersion -match '(\d+)\.(\d+)') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -eq 3 -and $minor -ge 10) {
            Write-OK "Python $pythonVersion (>= 3.10)"
        } else {
            Write-WARN "Python $pythonVersion found but 3.10+ recommended"
        }
    }
}

# ============================================================
# STEP 6: Check Git
# ============================================================
function Test-Git {
    Write-Step -Number 6 -Text "Checking Git"
    if ($SkipDependencies) {
        Write-INFO "Skipping Git check"
        return
    }

    $gitCmd = Get-Command "git" -ErrorAction SilentlyContinue
    if (-not $gitCmd) {
        Write-WARN "Git not found (optional for deployment)"
        Write-INFO "Install Git from: https://git-scm.com/download/win"
        return
    }

    $gitVersion = git --version 2>&1
    Write-OK "Git: $gitVersion"
}

# ============================================================
# STEP 7: Copy Files to Install Path
# ============================================================
function Install-Files {
    Write-Step -Number 7 -Text "Installing files to $InstallPath"

    # Check if source and destination are the same
    $sourceFull = (Resolve-Path $SOURCE_PATH -ErrorAction SilentlyContinue)?.Path
    $destFull   = (Resolve-Path $InstallPath -ErrorAction SilentlyContinue)?.Path

    if ($sourceFull -and $destFull -and ($sourceFull -eq $destFull)) {
        Write-OK "Already in install directory: $InstallPath"
        return
    }

    if (-not (Test-Path $InstallPath)) {
        Write-INFO "Creating directory: $InstallPath"
        New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    } elseif (-not $Force) {
        # Check if already installed
        if (Test-Path "$InstallPath\docker-compose.yml") {
            Write-OK "Files already exist in $InstallPath (use -Force to overwrite)"
            Set-Location $InstallPath
            return
        }
    }

    Write-INFO "Copying files from $SOURCE_PATH to $InstallPath..."

    # Exclude heavy or unnecessary directories
    $excludeDirs = @("node_modules", ".git", "__pycache__", ".pytest_cache", "*.pyc")
    
    try {
        # Use robocopy for efficient copy
        $robocopyArgs = @(
            $SOURCE_PATH,
            $InstallPath,
            "/E",           # Copy subdirectories including empty
            "/XD", "node_modules", ".git", "__pycache__", ".pytest_cache", "dist",
            "/XF", "*.pyc", "*.log",
            "/NFL",         # No file list
            "/NDL",         # No directory list
            "/NJH",         # No job header
            "/NJS"          # No job summary
        )
        $result = robocopy @robocopyArgs
        if ($LASTEXITCODE -gt 7) {
            throw "Robocopy failed with code $LASTEXITCODE"
        }
        Write-OK "Files copied to $InstallPath"
    } catch {
        # Fallback to PowerShell copy
        Write-INFO "Falling back to PowerShell copy..."
        Copy-Item -Path "$SOURCE_PATH\*" -Destination $InstallPath -Recurse -Force -ErrorAction Stop
        Write-OK "Files copied to $InstallPath"
    }

    Set-Location $InstallPath
}

# ============================================================
# STEP 8: Create .env File
# ============================================================
function Initialize-EnvFile {
    Write-Step -Number 8 -Text "Creating .env configuration file"
    
    Set-Location $InstallPath
    $envFile    = "$InstallPath\.env"
    $envExample = "$InstallPath\.env.example"

    if (Test-Path $envFile) {
        if (-not $Force) {
            Write-OK ".env file already exists (use -Force to regenerate)"
            return
        }
        Write-WARN "Overwriting existing .env file"
    }

    if (-not (Test-Path $envExample)) {
        Write-WARN ".env.example not found — creating minimal .env"
    }

    # Generate secure random secrets
    $pgPassword    = Get-RandomSecret -Length 24
    $redisPassword = Get-RandomSecret -Length 20
    $secretKey     = Get-RandomSecret -Length 64
    $jwtSecret     = Get-RandomSecret -Length 64
    $twinToken     = Get-RandomSecret -Length 32
    $grafanaPass   = Get-RandomSecret -Length 16

    $envContent = @"
# SintraPrime-Unified Environment Configuration
# Auto-generated by SETUP_WINDOWS.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# !!  KEEP THIS FILE PRIVATE — do not commit to git  !!

# === Database ===
POSTGRES_PASSWORD=$pgPassword
REDIS_PASSWORD=$redisPassword

# === Application Secrets ===
SECRET_KEY=$secretKey
JWT_SECRET=$jwtSecret

# === Grafana ===
GRAFANA_PASSWORD=$grafanaPass

# === MinIO ===
MINIO_PASSWORD=$(Get-RandomSecret -Length 20)

# === Twin Layer ===
TWIN_AUTH_TOKEN=$twinToken

# === AI API Keys (add your keys here) ===
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OPENAI_ORG_ID=

# === Slack Integration (optional) ===
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_APP_TOKEN=

# === Discord Integration (optional) ===
DISCORD_BOT_TOKEN=
DISCORD_GUILD_ID=

# === GitHub Integration (optional) ===
GITHUB_TOKEN=
GITHUB_WEBHOOK_SECRET=

# === GHL/CRM Integration (optional) ===
GHL_API_KEY=
GHL_LOCATION_ID=

# === Ports ===
API_PORT=8080
GRAFANA_PORT=3000
PROMETHEUS_PORT=9090
ELASTICSEARCH_PORT=9200

# === Log Level ===
LOG_LEVEL=INFO

# === Features ===
ENABLE_SUPERINTELLIGENCE=true
ENABLE_TWIN_TUI=true
ENABLE_AGENT_SWARMS=true
ENABLE_HIVE_MIND=true
ENABLE_VOICE=false
ENABLE_VLM=false
"@

    Set-Content -Path $envFile -Value $envContent -Encoding UTF8
    Write-OK ".env created with auto-generated secrets"
    Write-INFO "Secrets saved to: $envFile"
    Write-WARN "Add your API keys to .env before using AI features!"
}

# ============================================================
# STEP 9: Pull Docker Images
# ============================================================
function Invoke-DockerPull {
    Write-Step -Number 9 -Text "Pulling Docker images (this may take a few minutes)"
    
    Set-Location $InstallPath

    Write-INFO "Pulling base images from Docker Hub..."
    try {
        $pullCmd = "docker-compose pull --ignore-pull-failures 2>&1"
        $altCmd  = "docker compose pull --ignore-pull-failures 2>&1"
        
        $output = Invoke-Expression $pullCmd
        if ($LASTEXITCODE -ne 0) {
            $output = Invoke-Expression $altCmd
        }
        Write-OK "Docker images pulled"
    } catch {
        Write-WARN "Some images could not be pulled: $_"
        Write-INFO "Will try to build from source..."
    }
}

# ============================================================
# STEP 10: Build Custom Images
# ============================================================
function Invoke-DockerBuild {
    Write-Step -Number 10 -Text "Building custom Docker images"
    
    if ($SkipBuild) {
        Write-INFO "Skipping build step (-SkipBuild specified)"
        return
    }

    Set-Location $InstallPath

    Write-INFO "Building Python API and Node.js Airlock images..."
    try {
        $buildCmd = "docker-compose build --parallel 2>&1"
        $output = Invoke-Expression $buildCmd
        if ($LASTEXITCODE -ne 0) {
            $buildCmd = "docker compose build --parallel 2>&1"
            $output = Invoke-Expression $buildCmd
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Custom images built successfully"
        } else {
            Write-WARN "Build completed with warnings (exit code: $LASTEXITCODE)"
            Write-INFO "Services may still start from cached images"
        }
    } catch {
        Write-WARN "Build error: $_"
        Write-INFO "Attempting to start with available images..."
    }
}

# ============================================================
# STEP 11: Start All Services
# ============================================================
function Start-Services {
    Write-Step -Number 11 -Text "Starting all SintraPrime services"
    
    Set-Location $InstallPath

    Write-INFO "Running: docker-compose up -d"
    try {
        $upCmd = "docker-compose up -d 2>&1"
        $output = Invoke-Expression $upCmd
        if ($LASTEXITCODE -ne 0) {
            $upCmd = "docker compose up -d 2>&1"
            $output = Invoke-Expression $upCmd
        }

        if ($LASTEXITCODE -eq 0) {
            Write-OK "All services started"
        } else {
            Write-FAIL "docker-compose up failed!"
            Write-Host ""
            Write-Host "  Troubleshooting commands:" -ForegroundColor Yellow
            Write-Host "    docker-compose logs           # View all logs" -ForegroundColor Cyan
            Write-Host "    docker-compose logs api       # View API logs" -ForegroundColor Cyan
            Write-Host "    docker-compose ps             # Check service status" -ForegroundColor Cyan
            Write-Host ""
            Write-Log "docker-compose up output: $output"
            exit 1
        }
    } catch {
        Write-FAIL "Failed to start services: $_"
        exit 1
    }
}

# ============================================================
# STEP 12: Wait for Health Checks
# ============================================================
function Wait-ForServices {
    Write-Step -Number 12 -Text "Waiting for services to become healthy"
    
    Write-INFO "Giving containers 15 seconds to initialize..."
    Start-Sleep -Seconds 15

    # Check API health (most important)
    $apiHealthy = Wait-ForHealthCheck `
        -Url "http://localhost:8080/health" `
        -ServiceName "SintraPrime API" `
        -TimeoutSeconds 120 `
        -PollIntervalSeconds 5

    # Check Airlock
    $airlockHealthy = Wait-ForHealthCheck `
        -Url "http://localhost:3001/health" `
        -ServiceName "Airlock Server" `
        -TimeoutSeconds 90 `
        -PollIntervalSeconds 5

    # Check Grafana (non-blocking)
    $grafanaHealthy = Wait-ForHealthCheck `
        -Url "http://localhost:3000/api/health" `
        -ServiceName "Grafana" `
        -TimeoutSeconds 60 `
        -PollIntervalSeconds 5

    # Check Prometheus (non-blocking)
    $prometheusHealthy = Wait-ForHealthCheck `
        -Url "http://localhost:9090/-/healthy" `
        -ServiceName "Prometheus" `
        -TimeoutSeconds 60 `
        -PollIntervalSeconds 5

    if (-not $apiHealthy) {
        Write-WARN "API health check timed out. Run: docker-compose logs api"
    }
}

# ============================================================
# STEP 13: Check Port Conflicts
# ============================================================
function Test-PortConflicts {
    Write-Step -Number 13 -Text "Checking for port conflicts"
    
    $ports = @(
        @{ Port = 8080; Service = "SintraPrime API" }
        @{ Port = 3001; Service = "Airlock Server" }
        @{ Port = 3000; Service = "Grafana" }
        @{ Port = 9090; Service = "Prometheus" }
        @{ Port = 9200; Service = "Elasticsearch" }
        @{ Port = 5432; Service = "PostgreSQL" }
        @{ Port = 6379; Service = "Redis" }
        @{ Port = 80;   Service = "Nginx" }
    )

    $conflicts = @()
    foreach ($portInfo in $ports) {
        $inUse = -not (Test-PortAvailable -Port $portInfo.Port)
        if ($inUse) {
            # Check if it's our docker container
            try {
                $test = Invoke-WebRequest -Uri "http://localhost:$($portInfo.Port)/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
                if ($test) {
                    Write-OK "Port $($portInfo.Port) ($($portInfo.Service)) — running"
                }
            } catch {
                $conflicts += "$($portInfo.Port) ($($portInfo.Service))"
                Write-WARN "Port $($portInfo.Port) may be in use by another application"
            }
        } else {
            Write-OK "Port $($portInfo.Port) ($($portInfo.Service)) — available"
        }
    }

    if ($conflicts.Count -gt 0) {
        Write-Host ""
        Write-INFO "To change conflicting ports, edit .env file:"
        Write-INFO "  API_PORT=8081"
        Write-INFO "  GRAFANA_PORT=3001"
        Write-INFO "  PROMETHEUS_PORT=9091"
        Write-Host ""
    }
}

# ============================================================
# STEP 14: Open Browser
# ============================================================
function Open-BrowserUI {
    Write-Step -Number 14 -Text "Opening browser"
    
    $uiUrl = "http://localhost:3001"
    
    Write-INFO "Opening $uiUrl in your default browser..."
    try {
        Start-Process $uiUrl
        Write-OK "Browser opened"
    } catch {
        Write-INFO "Could not open browser automatically"
        Write-INFO "Manually open: $uiUrl"
    }
}

# ============================================================
# STEP 15: Print Success Banner
# ============================================================
function Show-SuccessBanner {
    Write-Step -Number 15 -Text "Setup complete!"

    Write-Host ""
    Write-Host "  ============================================================" -ForegroundColor Green
    Write-Host "   SintraPrime-Unified v2.0 — RUNNING " -ForegroundColor Green
    Write-Host "  ============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  SERVICE URLS:" -ForegroundColor Cyan
    Write-Host "  ┌─────────────────────────────────────────────────────────┐" -ForegroundColor DarkCyan
    Write-Host "  │  Main App (Airlock)   http://localhost:3001             │" -ForegroundColor White
    Write-Host "  │  API (Hive Mind)      http://localhost:8080             │" -ForegroundColor White
    Write-Host "  │  API Docs             http://localhost:8080/docs        │" -ForegroundColor White
    Write-Host "  │  Grafana Dashboard    http://localhost:3000             │" -ForegroundColor White
    Write-Host "  │  Prometheus Metrics   http://localhost:9090             │" -ForegroundColor White
    Write-Host "  │  Elasticsearch        http://localhost:9200             │" -ForegroundColor White
    Write-Host "  │  MinIO Console        http://localhost:9001             │" -ForegroundColor White
    Write-Host "  │  Twin Display (WS)    ws://localhost:8765               │" -ForegroundColor White
    Write-Host "  │  Nginx Proxy          http://localhost:80               │" -ForegroundColor White
    Write-Host "  └─────────────────────────────────────────────────────────┘" -ForegroundColor DarkCyan
    Write-Host ""
    Write-Host "  CREDENTIALS:" -ForegroundColor Cyan
    Write-Host "  ┌─────────────────────────────────────────────────────────┐" -ForegroundColor DarkCyan
    Write-Host "  │  Grafana:  admin / (see .env GRAFANA_PASSWORD)          │" -ForegroundColor White
    Write-Host "  │  MinIO:    minioadmin / (see .env MINIO_PASSWORD)       │" -ForegroundColor White
    Write-Host "  │  API Admin: admin / admin (change in production!)       │" -ForegroundColor White
    Write-Host "  └─────────────────────────────────────────────────────────┘" -ForegroundColor DarkCyan
    Write-Host ""
    Write-Host "  NEXT STEPS:" -ForegroundColor Cyan
    Write-Host "  1. Add your AI API keys to:   $InstallPath\.env" -ForegroundColor White
    Write-Host "  2. Restart after .env changes: docker-compose restart" -ForegroundColor White
    Write-Host "  3. View logs:                  docker-compose logs -f" -ForegroundColor White
    Write-Host "  4. Stop all services:          docker-compose down" -ForegroundColor White
    Write-Host "  5. Health check:               .\health_check.ps1" -ForegroundColor White
    Write-Host "  6. Quick reference:            Get-Content QUICK_REFERENCE.md" -ForegroundColor White
    Write-Host ""
    Write-Host "  INSTALL PATH:  $InstallPath" -ForegroundColor DarkGray
    Write-Host "  LOG FILE:      $LOG_FILE" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  ============================================================" -ForegroundColor Green
    Write-Host ""
}

# ============================================================
# MAIN EXECUTION
# ============================================================
function Main {
    # Print header
    Write-Banner -Text "$SCRIPT_NAME v$SCRIPT_VERSION" -Color Cyan
    Write-Host "  Log file: $LOG_FILE" -ForegroundColor DarkGray
    Write-Host ""

    Write-Log "=== SintraPrime-Unified Setup Started ==="
    Write-Log "Script Version: $SCRIPT_VERSION"
    Write-Log "Install Path: $InstallPath"
    Write-Log "Source Path: $SOURCE_PATH"
    Write-Log "PowerShell Version: $($PSVersionTable.PSVersion)"
    Write-Log "OS: $([System.Environment]::OSVersion.VersionString)"

    # Execute all steps
    Test-Administrator
    Test-Docker
    Test-DockerResources
    Test-NodeJS
    Test-Python
    Test-Git
    Install-Files
    Initialize-EnvFile
    Invoke-DockerPull
    Invoke-DockerBuild
    Start-Services
    Wait-ForServices
    Test-PortConflicts
    Open-BrowserUI
    Show-SuccessBanner

    Write-Log "=== Setup Completed Successfully ==="
}

# Run main function
try {
    Main
} catch {
    Write-Host ""
    Write-FAIL "Setup failed: $_"
    Write-Host ""
    Write-Host "  Check the log file for details: $LOG_FILE" -ForegroundColor Yellow
    Write-Host "  Run with -Verbose for more output" -ForegroundColor Yellow
    Write-Host ""
    Write-Log "=== Setup FAILED: $_ ==="
    exit 1
}
