# SintraPrime-Unified Windows Health Check Script
# Monitors the health of all deployed services
# Usage: PowerShell -ExecutionPolicy Bypass -File health-check.ps1

param(
    [int]$IntervalSeconds = 30,
    [switch]$Continuous = $false,
    [switch]$Verbose = $false
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$HealthCheckLog = "$ProjectRoot\health-checks.log"

# Health check endpoints and configurations
$HealthEndpoints = @(
    @{
        Name = 'Hive Mind API'
        Type = 'HTTP'
        Endpoint = 'http://localhost:8080/health'
        Port = 8080
        Timeout = 5
        Weight = 'Critical'
    },
    @{
        Name = 'Airlock Server'
        Type = 'HTTP'
        Endpoint = 'http://localhost:3001/health'
        Port = 3001
        Timeout = 5
        Weight = 'Critical'
    },
    @{
        Name = 'PostgreSQL'
        Type = 'Port'
        Port = 5432
        Timeout = 5
        Weight = 'Critical'
    },
    @{
        Name = 'Redis'
        Type = 'Port'
        Port = 6379
        Timeout = 5
        Weight = 'Critical'
    },
    @{
        Name = 'Elasticsearch'
        Type = 'HTTP'
        Endpoint = 'http://localhost:9200/_cluster/health'
        Port = 9200
        Timeout = 5
        Weight = 'Important'
    },
    @{
        Name = 'Grafana'
        Type = 'HTTP'
        Endpoint = 'http://localhost:3000/api/health'
        Port = 3000
        Timeout = 5
        Weight = 'Important'
    },
    @{
        Name = 'Prometheus'
        Type = 'HTTP'
        Endpoint = 'http://localhost:9090/-/healthy'
        Port = 9090
        Timeout = 5
        Weight = 'Important'
    },
    @{
        Name = 'MinIO'
        Type = 'HTTP'
        Endpoint = 'http://localhost:9000/minio/health/live'
        Port = 9000
        Timeout = 5
        Weight = 'Optional'
    }
)

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = 'Info',
        [switch]$ToFile = $true
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    $colors = @{
        'Success' = 'Green'
        'Error' = 'Red'
        'Warning' = 'Yellow'
        'Info' = 'Cyan'
        'Critical' = 'Red'
    }
    
    $symbols = @{
        'Success' = '✓'
        'Error' = '✗'
        'Warning' = '⚠'
        'Info' = 'ℹ'
        'Critical' = '●'
    }
    
    $logLine = "[$timestamp] [$Level] $Message"
    
    if ($ToFile) {
        Add-Content -Path $HealthCheckLog -Value $logLine
    }
    
    Write-Host "$($symbols[$Level]) $Message" -ForegroundColor $colors[$Level]
}

function Test-HttpEndpoint {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 5
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSeconds -ErrorAction SilentlyContinue
        return @{
            Success = $response.StatusCode -eq 200
            StatusCode = $response.StatusCode
            ResponseTime = $response.BaseResponse.ResponseTime
        }
    }
    catch {
        return @{
            Success = $false
            Error = $_.Exception.Message
        }
    }
}

function Test-PortConnection {
    param(
        [int]$Port,
        [int]$TimeoutSeconds = 5
    )
    
    try {
        $tcpConnection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($tcpConnection) {
            return @{
                Success = $true
                Port = $Port
                State = $tcpConnection.State
            }
        }
        return @{Success = $false}
    }
    catch {
        return @{Success = $false}
    }
}

function Check-ServiceHealth {
    param([PSObject]$Service)
    
    $name = $Service.Name
    $type = $Service.Type
    
    if ($type -eq 'HTTP') {
        $result = Test-HttpEndpoint -Url $Service.Endpoint -TimeoutSeconds $Service.Timeout
        if ($result.Success) {
            return @{
                Service = $name
                Status = 'Healthy'
                StatusCode = $result.StatusCode
                Weight = $Service.Weight
            }
        }
        else {
            return @{
                Service = $name
                Status = 'Unhealthy'
                Error = $result.Error
                Weight = $Service.Weight
            }
        }
    }
    elseif ($type -eq 'Port') {
        $result = Test-PortConnection -Port $Service.Port -TimeoutSeconds $Service.Timeout
        if ($result.Success) {
            return @{
                Service = $name
                Status = 'Healthy'
                Port = $Service.Port
                Weight = $Service.Weight
            }
        }
        else {
            return @{
                Service = $name
                Status = 'Unhealthy'
                Port = $Service.Port
                Weight = $Service.Weight
            }
        }
    }
}

function Show-HealthStatus {
    param([PSObject[]]$Results)
    
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║        SintraPrime-Unified Service Health Report            ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    Write-Host "`nStatus: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Yellow
    Write-Host "`nCritical Services:" -ForegroundColor Magenta
    foreach ($result in ($Results | Where-Object {$_.Weight -eq 'Critical'})) {
        $symbol = if ($result.Status -eq 'Healthy') {'✓'} else {'✗'}
        $color = if ($result.Status -eq 'Healthy') {'Green'} else {'Red'}
        Write-Host "  $symbol $($result.Service): $($result.Status)" -ForegroundColor $color
    }
    
    Write-Host "`nImportant Services:" -ForegroundColor Magenta
    foreach ($result in ($Results | Where-Object {$_.Weight -eq 'Important'})) {
        $symbol = if ($result.Status -eq 'Healthy') {'✓'} else {'⚠'} 
        $color = if ($result.Status -eq 'Healthy') {'Green'} else {'Yellow'}
        Write-Host "  $symbol $($result.Service): $($result.Status)" -ForegroundColor $color
    }
    
    Write-Host "`nOptional Services:" -ForegroundColor Magenta
    foreach ($result in ($Results | Where-Object {$_.Weight -eq 'Optional'})) {
        $symbol = if ($result.Status -eq 'Healthy') {'✓'} else {'○'} 
        $color = if ($result.Status -eq 'Healthy') {'Green'} else {'Gray'}
        Write-Host "  $symbol $($result.Service): $($result.Status)" -ForegroundColor $color
    }
    
    # Summary
    $criticalIssues = ($Results | Where-Object {$_.Weight -eq 'Critical' -and $_.Status -eq 'Unhealthy'}).Count
    $warningCount = ($Results | Where-Object {$_.Weight -eq 'Important' -and $_.Status -eq 'Unhealthy'}).Count
    
    Write-Host "`nSummary:" -ForegroundColor Cyan
    if ($criticalIssues -eq 0) {
        Write-Host "  ✓ All critical services are healthy" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ $criticalIssues critical service(s) are unhealthy" -ForegroundColor Red
    }
    
    if ($warningCount -gt 0) {
        Write-Host "  ⚠ $warningCount important service(s) have issues" -ForegroundColor Yellow
    }
    
    Write-Host ""
}

function Show-DetailedReport {
    param([PSObject[]]$Results)
    
    Write-Host "`nDetailed Report:" -ForegroundColor Cyan
    
    foreach ($result in $Results) {
        Write-Host "`n  Service: $($result.Service)" -ForegroundColor Yellow
        Write-Host "    Status: $($result.Status)" -ForegroundColor (if ($result.Status -eq 'Healthy') {'Green'} else {'Red'})
        
        if ($result.StatusCode) {
            Write-Host "    HTTP Status: $($result.StatusCode)" -ForegroundColor Gray
        }
        if ($result.Port) {
            Write-Host "    Port: $($result.Port)" -ForegroundColor Gray
        }
        if ($result.Error) {
            Write-Host "    Error: $($result.Error)" -ForegroundColor Red
        }
        if ($result.ResponseTime) {
            Write-Host "    Response Time: $($result.ResponseTime) ms" -ForegroundColor Gray
        }
    }
}

function Main {
    Write-Log "Health check started" -Level 'Info'
    
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║   SintraPrime-Unified Health Check Tool                     ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    if ($Continuous) {
        Write-Host "`nRunning continuous health checks every $IntervalSeconds seconds..." -ForegroundColor Cyan
        Write-Host "Press Ctrl+C to exit`n" -ForegroundColor Gray
        
        while ($true) {
            $results = @()
            foreach ($endpoint in $HealthEndpoints) {
                $result = Check-ServiceHealth -Service $endpoint
                $results += $result
            }
            
            Clear-Host
            Show-HealthStatus -Results $results
            
            if ($Verbose) {
                Show-DetailedReport -Results $results
            }
            
            Start-Sleep -Seconds $IntervalSeconds
        }
    }
    else {
        $results = @()
        foreach ($endpoint in $HealthEndpoints) {
            $result = Check-ServiceHealth -Service $endpoint
            $results += $result
        }
        
        Show-HealthStatus -Results $results
        
        if ($Verbose) {
            Show-DetailedReport -Results $results
        }
        
        Write-Log "Health check completed" -Level 'Info'
        
        $criticalIssues = ($results | Where-Object {$_.Weight -eq 'Critical' -and $_.Status -eq 'Unhealthy'}).Count
        if ($criticalIssues -gt 0) {
            exit 1
        }
    }
}

Main
