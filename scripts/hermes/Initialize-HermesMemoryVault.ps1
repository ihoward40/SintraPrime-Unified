[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $false)]
    [string]$VaultRoot = (Join-Path $PSScriptRoot "..\..\hermes-vault")
)

$ErrorActionPreference = "Stop"

$directories = @(
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
    "schema",
    "receipts/ingest",
    "receipts/query",
    "receipts/lint",
    "indexes",
    "quarantine",
    "templates"
)

foreach ($directory in $directories) {
    $path = Join-Path $VaultRoot $directory
    if (-not (Test-Path -LiteralPath $path)) {
        if ($PSCmdlet.ShouldProcess($path, "Create directory")) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }
}

$readme = @'
# Hermes Governed Memory Vault

This directory is managed by the Hermes governed-memory subsystem.

- `raw/` is source-of-truth material and must never be edited by agents.
- `wiki/` contains agent-maintained, source-linked notes.
- `schema/` defines note and governance requirements.
- `receipts/` contains append-only operation evidence.
- `indexes/` contains rebuildable machine indexes.
- `quarantine/` contains ambiguous or policy-blocked material.

Required operations: ingest, query, lint.
'@

$readmePath = Join-Path $VaultRoot "README.md"
if (-not (Test-Path -LiteralPath $readmePath)) {
    Set-Content -LiteralPath $readmePath -Value $readme -Encoding utf8NoBOM
}

$indexFiles = @(
    "indexes/source-index.jsonl",
    "indexes/entity-index.jsonl",
    "indexes/contradiction-index.jsonl"
)

foreach ($relativePath in $indexFiles) {
    $path = Join-Path $VaultRoot $relativePath
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType File -Path $path -Force | Out-Null
    }
}

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
'@

$gitIgnorePath = Join-Path $VaultRoot ".gitignore"
if (-not (Test-Path -LiteralPath $gitIgnorePath)) {
    Set-Content -LiteralPath $gitIgnorePath -Value $gitIgnore -Encoding utf8NoBOM
}

Write-Host "Hermes governed memory vault initialized at: $VaultRoot"
