#Requires -Version 5.1
<#
.SYNOPSIS
    SintraPrime-Unified Health Check Script

.DESCRIPTION
    Checks all SintraPrime services and displays a color-coded status table.
    - Green  = Healthy / Running
    - Yellow = Starting / Degraded
    - Red    = Down / Unreachable

.EXAMPLE
    .\health_check.ps1
    .\health_check.ps1 -Watch        # Auto-refresh every 10 seconds
    .\health_check.ps1 -Json         # Output JSON (for automation)

.PARAMETER Watch
    Continuously monitor services (Ctrl+C to stop)

.PARAMETER RefreshSeconds
    Refresh interval when -Watch is used (default: 10)

.PARAMETER Json
    Output results as JSON

.PARAMETER Timeout
    HTTP request timeout in seconds (default: 5)
#>

param(
    [switch]$Watch,
    [int]$RefreshSeconds = 10,
    [switch]$Json,
    [int]$Timeout = 5
)

# ============================================================
# SERVICE DEFINITIONS
# ============================================================
$Services = @(
    @{
        Name        = "SintraPrime API"
        Container   = "sintraprime-api"
        HealthUrl   = "http://localhost:8080/health"
        Port        = 8080
        DocsUrl     = "http://localhost:8080/docs"
        Type        = "http"
    },
    @{
        Name        = "Airlock Server"
        Container   = "sintraprime-airlock"
        HealthUrl   = "http://localhost:3001/health"
        Port        = 3001
        DocsUrl     = "http://localhost:3001"
        Type        = "http"
    },
    @{
        Name        = "PostgreSQL"
        Container   = "sintraprime-postgres"
        HealthUrl   = ""
        Port        = 5432
        DocsUrl     = ""
        Type        = "docker"
    },
    @{
        Name        = "Redis"
        Container   = "sintraprime-redis"
        HealthUrl   = ""
        Port        = 6379
        DocsUrl     = ""
        Type        = "docker"
    },
    @{
        Name        = "Elasticsearch"
        Container   = "sintraprime-elasticsearch"
        HealthUrl   = "http://localhost:9200/_cluster/health"
        Port        = 9200
        DocsUrl     = "http://localhost:9200"
        Type        = "http"
    },
    @{
        Name        = "Grafana"
        Container   = "sintraprime-grafana"
        HealthUrl   = "http://localhost:3000/api/health"
        Port        = 3000
        DocsUrl     = "http://localhost:3000"
        Type        = "http"
    },
    @{
        Name        = "Prometheus"
        Container   = "sintraprime-prometheus"
        HealthUrl   = "http://localhost:9090/-/healthy"
        Port        = 9090
        DocsUrl     = "http://localhost:9090"
        Type        = "http"
    },
    @{
        Name        = "MinIO"
        Container   = "sintraprime-minio"
        HealthUrl   = "http://localhost:9000/minio/health/live"
        Port        = 9000
        DocsUrl     = "http://localhost:9001"
        Type        = "http"
    },
    @{
        Name        = "Twin Display"
        Container   = "sintraprime-twin-display"
        HealthUrl   = ""
        Port        = 8765
        DocsUrl     = ""
        Type        = "tcp"
    },
    @{
        Name        = "Nginx Proxy"
        Container   = "sintraprime-nginx"
        HealthUrl   = "http://localhost:80"
        Port        = 80
        DocsUrl     = "http://localhost"
        Type        = "http"
    }
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================
function Get-ContainerStatus {
    param([string]$ContainerName)
    try {
        $status = docker inspect --format '{{.State.Status}}' $ContainerName 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $status.Trim()
        }
    } catch {}
    return "not-found"
}

function Get-ContainerHealth {
    param([string]$ContainerName)
    try {
        $health = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' $ContainerName 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $health.Trim()
        }
    } catch {}
    return "unknown"
}

function Test-HttpEndpoint {
    param([string]$Url, [int]$TimeoutSec = 5)
    if (-not $Url) { return @{ Success = $false; StatusCode = 0; ResponseTime = 0 } }
    $start = Get-Date
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
        $elapsed = [int]((Get-Date) - $start).TotalMilliseconds
        return @{
            Success      = ($response.StatusCode -in @(200, 201, 204))
            StatusCode   = $response.StatusCode
            ResponseTime = $elapsed
        }
    } catch [System.Net.WebException] {
        $elapsed = [int]((Get-Date) - $start).TotalMilliseconds
        $code = 0
        if ($_.Exception.Response) {
            $code = [int]$_.Exception.Response.StatusCode
        }
        return @{ Success = ($code -in @(200, 201, 204, 301, 302)); StatusCode = $code; ResponseTime = $elapsed }
    } catch {
        return @{ Success = $false; StatusCode = 0; ResponseTime = 0 }
    }
}

function Test-TcpPort {
    param([int]$Port, [int]$TimeoutMs = 2000)
    try {
        $tcp = [System.Net.Sockets.TcpClient]::new()
        $task = $tcp.ConnectAsync("localhost", $Port)
        $completed = $task.Wait($TimeoutMs)
        $tcp.Close()
        return $completed -and -not $task.IsFaulted
    } catch {
        return $false
    }
}

function Get-StatusIcon {
    param([string]$Status)
    switch ($Status) {
        "healthy"   { return "[OK] " }
        "running"   { return "[OK] " }
        "starting"  { return "[..] " }
        "warning"   { return "[!!] " }
        "unhealthy" { return "[XX] " }
        "down"      { return "[--] " }
        default     { return "[??] " }
    }
}

function Get-StatusColor {
    param([string]$Status)
    switch ($Status) {
        "healthy"   { return "Green"  }
        "running"   { return "Green"  }
        "starting"  { return "Yellow" }
        "warning"   { return "Yellow" }
        "unhealthy" { return "Red"    }
        "down"      { return "Red"    }
        default     { return "Gray"   }
    }
}

function Get-ServiceStatus {
    param($Service)
    
    $containerStatus = Get-ContainerStatus -ContainerName $Service.Container
    $containerHealth = Get-ContainerHealth -ContainerName $Service.Container
    
    $result = @{
        Name          = $Service.Name
        Container     = $Service.Container
        Port          = $Service.Port
        ContainerStatus = $containerStatus
        ContainerHealth = $containerHealth
        HttpStatus    = $null
        ResponseTime  = $null
        OverallStatus = "down"
        URL           = $Service.DocsUrl
    }

    if ($containerStatus -ne "running") {
        $result.OverallStatus = if ($containerStatus -eq "not-found") { "down" } else { $containerStatus }
        return $result
    }

    # Container is running — check connectivity
    switch ($Service.Type) {
        "http" {
            if ($Service.HealthUrl) {
                $http = Test-HttpEndpoint -Url $Service.HealthUrl -TimeoutSec $Timeout
                $result.HttpStatus   = $http.StatusCode
                $result.ResponseTime = $http.ResponseTime
                
                if ($http.Success) {
                    $result.OverallStatus = if ($containerHealth -eq "unhealthy") { "warning" } else { "healthy" }
                } elseif ($containerHealth -eq "starting") {
                    $result.OverallStatus = "starting"
                } else {
                    $result.OverallStatus = "unhealthy"
                }
            } else {
                $result.OverallStatus = if ($containerHealth -in @("healthy", "no-healthcheck")) { "running" } else { "starting" }
            }
        }
        "tcp" {
            $open = Test-TcpPort -Port $Service.Port
            $result.OverallStatus = if ($open) { "healthy" } else { "starting" }
        }
        "docker" {
            # For postgres/redis, trust docker health check
            $result.OverallStatus = switch ($containerHealth) {
                "healthy"   { "healthy" }
                "unhealthy" { "unhealthy" }
                "starting"  { "starting" }
                default     { "running" }
            }
        }
    }
    
    return $result
}

# ============================================================
# DISPLAY FUNCTIONS
# ============================================================
function Show-StatusTable {
    param($Results)
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    Clear-Host
    Write-Host ""
    Write-Host "  SintraPrime-Unified Health Status" -ForegroundColor Cyan
    Write-Host "  Updated: $timestamp" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  ┌──────────────────────┬────────────┬──────────┬──────────────┬──────┐" -ForegroundColor DarkCyan
    Write-Host "  │  Service             │  Status    │  Port    │  Response    │  URL │" -ForegroundColor DarkCyan
    Write-Host "  ├──────────────────────┼────────────┼──────────┼──────────────┼──────┤" -ForegroundColor DarkCyan

    $allHealthy   = $true
    $healthyCount = 0
    $totalCount   = $Results.Count

    foreach ($r in $Results) {
        $icon       = Get-StatusIcon -Status $r.OverallStatus
        $color      = Get-StatusColor -Status $r.OverallStatus
        $name       = $r.Name.PadRight(20)
        $status     = $r.OverallStatus.PadRight(10)
        $port       = (":" + $r.Port).PadRight(8)
        $respTime   = if ($r.ResponseTime) { "${$r.ResponseTime}ms".PadRight(12) } else { "N/A         " }
        $hasUrl     = if ($r.URL) { "open" } else { "    " }

        Write-Host "  │ " -NoNewline -ForegroundColor DarkCyan
        Write-Host "$icon" -NoNewline -ForegroundColor $color
        Write-Host "$name" -NoNewline -ForegroundColor White
        Write-Host "│ " -NoNewline -ForegroundColor DarkCyan
        Write-Host "$status" -NoNewline -ForegroundColor $color
        Write-Host "│ $port│ " -NoNewline -ForegroundColor DarkCyan
        Write-Host "$respTime" -NoNewline -ForegroundColor DarkGray
        Write-Host "│ $hasUrl │" -ForegroundColor DarkCyan

        if ($r.OverallStatus -in @("healthy", "running")) { $healthyCount++ }
        else { $allHealthy = $false }
    }

    Write-Host "  └──────────────────────┴────────────┴──────────┴──────────────┴──────┘" -ForegroundColor DarkCyan
    Write-Host ""

    # Summary
    $summaryColor = if ($allHealthy) { "Green" } elseif ($healthyCount -gt 0) { "Yellow" } else { "Red" }
    Write-Host "  Summary: $healthyCount/$totalCount services healthy" -ForegroundColor $summaryColor
    Write-Host ""

    # Quick commands
    Write-Host "  Quick Commands:" -ForegroundColor DarkGray
    Write-Host "    docker-compose logs -f api         # Stream API logs" -ForegroundColor DarkGray
    Write-Host "    docker-compose restart api         # Restart API" -ForegroundColor DarkGray
    Write-Host "    docker-compose down                # Stop everything" -ForegroundColor DarkGray
    Write-Host "    docker-compose up -d               # Start everything" -ForegroundColor DarkGray
    Write-Host ""

    if ($Watch) {
        Write-Host "  Refreshing every ${RefreshSeconds}s — Press Ctrl+C to stop" -ForegroundColor DarkGray
    }

    return $allHealthy
}

# ============================================================
# JSON OUTPUT
# ============================================================
function Show-JsonOutput {
    param($Results)
    
    $output = @{
        timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
        services  = $Results
        summary   = @{
            total   = $Results.Count
            healthy = ($Results | Where-Object { $_.OverallStatus -in @("healthy", "running") }).Count
        }
    }
    
    $output | ConvertTo-Json -Depth 5
}

# ============================================================
# MAIN
# ============================================================
function Main {
    do {
        $results = foreach ($service in $Services) {
            Get-ServiceStatus -Service $service
        }

        if ($Json) {
            Show-JsonOutput -Results $results
        } else {
            $allHealthy = Show-StatusTable -Results $results
        }

        if ($Watch) {
            Start-Sleep -Seconds $RefreshSeconds
        }
    } while ($Watch)
}

Main
