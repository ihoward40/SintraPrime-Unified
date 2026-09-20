[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Low")]
param(
    [Parameter(Mandatory = $false)]
    [string]$VaultRoot = (Join-Path $PSScriptRoot "..\..\hermes-vault"),

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^tenant_[A-Za-z0-9][A-Za-z0-9._-]{2,127}$')]
    [string]$TenantId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-DirectoryIfMissing {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
            throw "Expected directory but found a non-directory path: $Path"
        }
        return
    }

    if ($PSCmdlet.ShouldProcess($Path, "Create directory")) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function New-FileIfMissing {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Content
    )

    if (Test-Path -LiteralPath $Path) {
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            throw "Expected file but found a non-file path: $Path"
        }
        return
    }

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-DirectoryIfMissing -Path $parent
    }

    if ($PSCmdlet.ShouldProcess($Path, "Create file")) {
        Set-Content -LiteralPath $Path -Value $Content -Encoding utf8NoBOM -NoNewline
    }
}

$resolvedRoot = [System.IO.Path]::GetFullPath($VaultRoot)
if (Test-Path -LiteralPath $resolvedRoot -PathType Leaf) {
    throw "VaultRoot resolves to an existing file: $resolvedRoot"
}

New-DirectoryIfMissing -Path $resolvedRoot

$globalDirectories = @(
    "schema",
    "templates",
    "parser-cache"
)

foreach ($directory in $globalDirectories) {
    New-DirectoryIfMissing -Path (Join-Path $resolvedRoot $directory)
}

if ($TenantId) {
    $tenantRoot = Join-Path $resolvedRoot (Join-Path "tenants" $TenantId)
    $tenantDirectories = @(
        "raw/inbox",
        "raw/processed",
        "raw/rejected",
        "wiki/clients",
        "wiki/matters",
        "wiki/projects",
        "wiki/decisions",
        "wiki/people",
        "wiki/organizations",
        "wiki/law",
        "wiki/procedures",
        "wiki/content",
        "receipts/ingest",
        "receipts/query",
        "receipts/lint",
        "receipts/quarantine",
        "receipts/resolution",
        "receipts/access",
        "indexes",
        "quarantine"
    )

    foreach ($directory in $tenantDirectories) {
        New-DirectoryIfMissing -Path (Join-Path $tenantRoot $directory)
    }

    $indexFiles = @(
        "indexes/source-index.jsonl",
        "indexes/entity-index.jsonl",
        "indexes/contradiction-index.jsonl"
    )

    foreach ($relativePath in $indexFiles) {
        New-FileIfMissing -Path (Join-Path $tenantRoot $relativePath) -Content ""
    }
}

$readme = @'
# Hermes Governed Memory Vault

This directory is managed by the Hermes governed-memory subsystem.

- `tenants/<tenant_id>/raw/` is write-once source-of-truth material.
- `tenants/<tenant_id>/wiki/` contains versioned, source-linked notes.
- `schema/` defines note, receipt, and governance requirements.
- `receipts/` are tenant-local, append-only operation evidence.
- `indexes/` and `parser-cache/` are rebuildable and are not authoritative.
- `quarantine/` contains ambiguous, malformed, or policy-blocked material.

Required operations: ingest, query, lint.

The initializer never overwrites existing files. Use `-WhatIf` for a dry run.
'@

$gitIgnore = @'
# Local transient data
.tmp/
.cache/
*.lock
*.bak
*.partial

# Secrets and credentials
.env
.env.*
*.pem
*.key
credentials.json

# Local model/parser caches
models/
parser-cache/

# OS/editor noise
.DS_Store
Thumbs.db
'@

New-FileIfMissing -Path (Join-Path $resolvedRoot "README.md") -Content $readme
New-FileIfMissing -Path (Join-Path $resolvedRoot ".gitignore") -Content $gitIgnore
New-FileIfMissing -Path (Join-Path $resolvedRoot ".vault-version") -Content "hermes-governed-memory-vault-v1`n"

$result = [ordered]@{
    vault_root = $resolvedRoot
    tenant_id = if ($TenantId) { $TenantId } else { $null }
    mode = if ($WhatIfPreference) { "what-if" } else { "applied" }
    overwritten_files = 0
}

$result | ConvertTo-Json -Compress | Write-Output
