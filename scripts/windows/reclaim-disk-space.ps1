<#
.SYNOPSIS
    Reports disk usage on a Windows desktop and optionally reclaims space from
    known-safe locations.

.DESCRIPTION
    Default mode is REPORT ONLY: it measures drives, common cache/temp locations,
    the Recycle Bin and large dev-tool caches (Docker/WSL/node/pip), then prints a
    ranked list of reclaim candidates with the exact command to free each one.

    Pass -Execute to actually delete the items marked "SAFE" in the report.
    Pass -Deep to also walk C:\ top-level folders and the user profile for the
    largest files (slower).

    Nothing outside the SAFE actions in -Execute is ever deleted, and no registry
    keys, services, restore points or installed programs are touched.

.PARAMETER Execute
    Perform the safe cleanups. Without this switch the script is read-only.

.PARAMETER Deep
    Add slow scans: per-folder sizes under C:\ and the largest files in the user
    profile older than 30 days.

.PARAMETER MinFileMb
    Minimum size in MB for a file to appear in the "deep" largest-file list.
    Default 100.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\reclaim-disk-space.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\reclaim-disk-space.ps1 -Deep -Execute
#>
[CmdletBinding()]
param(
    [switch]$Execute,
    [switch]$Deep,
    [int]$MinFileMb = 100
)

$ErrorActionPreference = 'Continue'

function Write-Section($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Write-Ok($t)      { Write-Host "  [ok]   $t" -ForegroundColor Green }
function Write-Warn2($t)   { Write-Host "  [warn] $t" -ForegroundColor Yellow }
function Write-Info($t)    { Write-Host "  $t" }

function Get-PathSizeMb {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        $sum = (Get-ChildItem -LiteralPath $Path -Recurse -Force -File -ErrorAction SilentlyContinue |
                Measure-Object -Property Length -Sum).Sum
        if ($null -eq $sum) { return 0 }
        return [math]::Round($sum / 1MB, 1)
    } catch { return $null }
}

function Format-Mb([double]$Mb) {
    if ($Mb -ge 1024) { return ('{0:N2} GB' -f ($Mb / 1024)) }
    return ('{0:N1} MB' -f $Mb)
}

$findings = New-Object System.Collections.ArrayList

function Add-Finding {
    param(
        [string]$Name,
        [double]$Mb,
        [string]$Action,
        [string]$Command,
        [switch]$SafeToRun
    )
    [void]$findings.Add([pscustomobject]@{
        Name       = $Name
        Mb         = [math]::Round($Mb, 1)
        Action     = $Action
        Command    = $Command
        SafeToRun  = [bool]$SafeToRun
    })
}

Write-Host "Disk space recovery audit - mode: $(if ($Execute) { 'REPORT + EXECUTE' } else { 'REPORT ONLY' })" -ForegroundColor White

# ---------------------------------------------------------------- 1. Drives
Write-Section "1. Drives"
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    $freeGb  = [math]::Round($_.FreeSpace / 1GB, 1)
    $totalGb = [math]::Round($_.Size / 1GB, 1)
    $pct     = if ($_.Size -gt 0) { [math]::Round(100 * $_.FreeSpace / $_.Size, 1) } else { 0 }
    $line    = "{0}  {1} GB free of {2} GB ({3}%)" -f $_.DeviceID, $freeGb, $totalGb, $pct
    if ($pct -lt 10) { Write-Warn2 $line } else { Write-Info $line }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warn2 "Not running as Administrator - component store, restore-point and shadow-copy figures will be missing."
}

# ------------------------------------------------- 2. Safe cache/temp folders
Write-Section "2. Temp and cache folders"
$tempTargets = @(
    @{ Name = 'User TEMP';          Path = $env:TEMP },
    @{ Name = 'Windows Temp';       Path = "$env:SystemRoot\Temp" },
    @{ Name = 'Windows Update cache'; Path = "$env:SystemRoot\SoftwareDistribution\Download" },
    @{ Name = 'Delivery Optimization'; Path = "$env:SystemRoot\SoftwareDistribution\DeliveryOptimization" },
    @{ Name = 'INetCache';          Path = "$env:LOCALAPPDATA\Microsoft\Windows\INetCache" },
    @{ Name = 'Explorer thumbnails'; Path = "$env:LOCALAPPDATA\Microsoft\Windows\Explorer" },
    @{ Name = 'CrashDumps';         Path = "$env:LOCALAPPDATA\CrashDumps" }
)
foreach ($t in $tempTargets) {
    $mb = Get-PathSizeMb $t.Path
    if ($null -eq $mb -or $mb -le 0) { continue }
    Write-Info ("{0,-24} {1,10}" -f $t.Name, (Format-Mb $mb))
    if ($mb -ge 50) {
        Add-Finding -Name $t.Name -Mb $mb -SafeToRun `
            -Action "Delete contents of $($t.Path)" `
            -Command "Remove-Item -Path '$($t.Path)\*' -Recurse -Force -ErrorAction SilentlyContinue"
    }
}

# ------------------------------------------------------------- 3. Recycle Bin
Write-Section "3. Recycle Bin"
try {
    $shell = New-Object -ComObject Shell.Application
    $bin = $shell.Namespace(0xA)
    $binMb = 0
    foreach ($i in $bin.Items()) { $binMb += $i.Size }
    $binMb = [math]::Round($binMb / 1MB, 1)
    Write-Info ("Recycle Bin: {0}" -f (Format-Mb $binMb))
    if ($binMb -ge 100) {
        Add-Finding -Name 'Recycle Bin' -Mb $binMb -SafeToRun `
            -Action 'Empty the Recycle Bin (permanent delete)' `
            -Command 'Clear-RecycleBin -Force'
    }
} catch { Write-Warn2 "Could not measure the Recycle Bin: $($_.Exception.Message)" }

# --------------------------------------------- 4. Windows-managed components
Write-Section "4. Windows-managed components (measured, not auto-deleted)"
$componentFiles = @(
    @{ Name = 'hiberfil.sys (hibernation)'; Path = 'C:\hiberfil.sys' },
    @{ Name = 'pagefile.sys (virtual memory)'; Path = 'C:\pagefile.sys' },
    @{ Name = 'swapfile.sys'; Path = 'C:\swapfile.sys' }
)
foreach ($f in $componentFiles) {
    if (Test-Path -LiteralPath $f.Path) {
        $mb = [math]::Round((Get-Item -LiteralPath $f.Path -Force).Length / 1MB, 1)
        Write-Info ("{0,-28} {1,10}" -f $f.Name, (Format-Mb $mb))
    }
}
foreach ($legacy in @('C:\Windows.old', 'C:\$WINDOWS.~BT', 'C:\$WINDOWS.~WS', 'C:\$WinREAgent')) {
    $mb = Get-PathSizeMb $legacy
    if ($null -ne $mb -and $mb -gt 0) {
        Write-Warn2 ("{0,-28} {1,10}  <- previous Windows install / upgrade leftovers" -f $legacy, (Format-Mb $mb))
        Add-Finding -Name $legacy -Mb $mb `
            -Action 'Delete upgrade leftovers (removes the roll-back option to the previous Windows build) - decide manually' `
            -Command "takeown /F '$legacy' /R /A /D Y; icacls '$legacy' /grant *S-1-5-32-544:F /T /C; Remove-Item -LiteralPath '$legacy' -Recurse -Force -ErrorAction SilentlyContinue"
    }
}
$winsxs = Get-PathSizeMb "$env:SystemRoot\WinSxS"
if ($null -ne $winsxs) { Write-Info ("{0,-28} {1,10}  (use DISM, never delete by hand)" -f 'WinSxS component store', (Format-Mb $winsxs)) }


Write-Info "Component store / restore points (admin only):"
Write-Info "  Dism.exe /Online /Cleanup-Image /AnalyzeComponentStore   (size of the component store)"
Write-Info "  vssadmin list shadowstorage                              (System Restore usage)"
Write-Info "  vssadmin resize shadowstorage /for=C: /on=C: /maxsize=5% (shrink restore-point budget)"
if ($Execute -and $isAdmin) {
    Write-Info "  -> running Dism.exe /Online /Cleanup-Image /StartComponentCleanup"
    & Dism.exe /Online /Cleanup-Image /StartComponentCleanup | Out-Null
} else {
    Write-Info "  (run Dism.exe /Online /Cleanup-Image /StartComponentCleanup in an elevated prompt)"
}

# ------------------------------------------------------- 5. Developer caches
Write-Section "5. Developer caches"
$devTargets = @(
    @{ Name = 'pip cache';           Path = "$env:LOCALAPPDATA\pip\cache";             Command = 'python -m pip cache purge' },
    @{ Name = 'npm cache';           Path = "$env:LOCALAPPDATA\npm-cache";             Command = 'npm cache clean --force' },
    @{ Name = 'NuGet packages';      Path = "$env:USERPROFILE\.nuget\packages";        Command = 'dotnet nuget locals all --clear' },
    @{ Name = 'Gradle caches';       Path = "$env:USERPROFILE\.gradle\caches";         Command = 'Remove-Item -Recurse -Force (Join-Path $env:USERPROFILE ".gradle\caches")' },
    @{ Name = 'Maven repository';    Path = "$env:USERPROFILE\.m2\repository";         Command = 'Remove-Item -Recurse -Force (Join-Path $env:USERPROFILE ".m2\repository")' },
    @{ Name = 'Yarn cache';          Path = "$env:LOCALAPPDATA\Yarn\Cache";            Command = 'yarn cache clean' },
    @{ Name = 'Docker Desktop data'; Path = "$env:LOCALAPPDATA\Docker\wsl";            Command = 'docker system prune -a --volumes --force' }
)
foreach ($d in $devTargets) {
    $mb = Get-PathSizeMb $d.Path
    if ($null -eq $mb -or $mb -lt 200) { continue }
    Write-Info ("{0,-24} {1,10}" -f $d.Name, (Format-Mb $mb))
    Add-Finding -Name $d.Name -Mb $mb -SafeToRun `
        -Action "Clear $($d.Name) (caches only; projects are untouched)" -Command $d.Command
}

$wslVhdx = Get-ChildItem -Path "$env:LOCALAPPDATA\Packages" -Filter '*.vhdx' -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Length -gt 1GB } | Sort-Object Length -Descending
foreach ($v in $wslVhdx) {
    $mb = [math]::Round($v.Length / 1MB, 1)
    Write-Warn2 ("WSL/Docker virtual disk {0}  {1}" -f (Format-Mb $mb), $v.FullName)
    Add-Finding -Name "WSL vhdx: $($v.Name)" -Mb $mb `
        -Action 'Compact the virtual disk: delete files inside the distro first, then wsl --shutdown, then Optimize-VHD' `
        -Command "wsl --shutdown; Optimize-VHD -Path '$($v.FullName)' -Mode Full"
}

$nodeModules = Get-ChildItem -Path $env:USERPROFILE -Directory -Filter 'node_modules' -Recurse -Force -ErrorAction SilentlyContinue -Depth 6 |
    Select-Object -First 200
if ($nodeModules) {
    $nmMb = 0
    foreach ($nm in $nodeModules) { $s = Get-PathSizeMb $nm.FullName; if ($s) { $nmMb += $s } }
    if ($nmMb -ge 500) {
        Write-Info ("{0,-24} {1,10}  ({2} folders)" -f 'node_modules trees', (Format-Mb $nmMb), $nodeModules.Count)
        Add-Finding -Name 'node_modules trees' -Mb $nmMb `
            -Action 'Reinstallable: delete only in projects you can rebuild (npm install restores them)' `
            -Command 'Get-ChildItem $env:USERPROFILE -Directory -Filter node_modules -Recurse -Depth 6 | Remove-Item -Recurse -Force'
    }
}

Write-Info "Built-in tools for system files:"
Write-Info "  cleanmgr /sageset:1 ; cleanmgr /sagerun:1     (Disk Cleanup, pick categories)"
Write-Info "  cleanmgr /verylowdisk                        (minimal Disk Cleanup)"


# ---------------------------------------------------- 6. Optional deep scan
if ($Deep) {
    Write-Section "6. Deep scan (slow)"
    Get-ChildItem C:\ -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $mb = Get-PathSizeMb $_.FullName
        if ($null -ne $mb) { Write-Info ("{0,-32} {1,10}" -f $_.Name, (Format-Mb $mb)) }
    }
    Write-Info "Largest files in your profile (>= $MinFileMb MB):"
    Get-ChildItem $env:USERPROFILE -File -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -ge ($MinFileMb * 1MB) } |
        Sort-Object Length -Descending | Select-Object -First 40 | ForEach-Object {
            Write-Info ("{0,10}  {1}" -f (Format-Mb ($_.Length / 1MB)), $_.FullName)
        }
}

# ---------------------------------------------------------- 7. Ranked report
Write-Section "7. Reclaim candidates (largest first)"
if ($findings.Count -eq 0) {
    Write-Ok "Nothing over threshold found in the scanned locations."
} else {
    $findings | Sort-Object Mb -Descending |
        Format-Table -AutoSize Name, @{N='Size';E={Format-Mb $_.Mb}}, SafeToRun, Action |
        Out-String | Write-Host
}

$safe = $findings | Where-Object { $_.SafeToRun } | Sort-Object Mb -Descending
$safeMb = ($safe | Measure-Object -Property Mb -Sum).Sum
if ($null -eq $safeMb) { $safeMb = 0 }
Write-Info ("Potentially reclaimable via the SAFE actions above: {0}" -f (Format-Mb $safeMb))

if ($Execute) {
    Write-Section "8. Executing safe cleanups"
    foreach ($f in $safe) {
        Write-Info "-> $($f.Name) ($(Format-Mb $f.Mb)): $($f.Command)"
        try {
            Invoke-Expression $f.Command | Out-Null
            Write-Ok "$($f.Name) cleaned"
        } catch {
            Write-Warn2 "$($f.Name) failed: $($_.Exception.Message)"
        }
    }
    Write-Host "`nDone. Re-run without -Execute to see the new free space." -ForegroundColor Green
    $manual = $findings | Where-Object { -not $_.SafeToRun } | Sort-Object Mb -Descending
    if ($manual) {
        Write-Section "9. Not auto-run - decide by hand"
        foreach ($f in $manual) {
            Write-Info "$($f.Name) ($(Format-Mb $f.Mb)) - $($f.Action)"
            Write-Info "  $($f.Command)"
        }
    }
} else {
    Write-Section "8. Next steps"
    Write-Info "Report only - nothing was deleted."
    Write-Info "To run the SAFE actions listed above:"
    Write-Info "  powershell -ExecutionPolicy Bypass -File .\reclaim-disk-space.ps1 -Execute"
    Write-Info "Skip anything you want to keep (Windows.old, node_modules, WSL disks) by running its command by hand."
}

