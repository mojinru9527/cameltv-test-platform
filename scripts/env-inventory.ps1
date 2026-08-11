#requires -Version 5.1
<#
.SYNOPSIS
  环境变量清单与必填校验（C152-1）。只读，不修改任何 env 文件。
.EXAMPLE
  pwsh scripts/env-inventory.ps1
#>
[CmdletBinding()]
param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$entries = @(
    @{ Label = "backend/.env";          Path = "test-platform-v2/backend/.env";          Required = @("DATABASE_URL", "SECRET_KEY") },
    @{ Label = "backend/.env.example";  Path = "test-platform-v2/backend/.env.example";  Required = @("DATABASE_URL") },
    @{ Label = "frontend/.env.example"; Path = "test-platform-v2/frontend/.env.example"; Required = @() },
    @{ Label = "deploy/.env.example";   Path = "test-platform-v2/deploy/.env.example";   Required = @() },
    @{ Label = "config/runtime/local.env"; Path = "test-platform-v2/config/runtime/local.env"; Required = @("DATABASE_URL", "SECRET_KEY", "ADMIN_PASSWORD") }
)

Write-Host "== env-inventory =="
$missingFiles = 0
$missingKeys = 0
foreach ($entry in $entries) {
    $full = Join-Path $Root $entry.Path
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        Write-Host ("[MISSING FILE] " + $entry.Path)
        $missingFiles++
        continue
    }
    $content = Get-Content -LiteralPath $full -Raw -ErrorAction SilentlyContinue
    foreach ($key in $entry.Required) {
        if ($content -notmatch "(?m)^\s*$([regex]::Escape($key))\s*=") {
            Write-Host ("[MISSING KEY ] " + $entry.Path + " -> " + $key)
            $missingKeys++
        }
    }
    Write-Host ("[OK] " + $entry.Path)
}
Write-Host ("summary: files=" + (5 - $missingFiles) + "/5, missingKeys=" + $missingKeys)
if ($missingFiles -gt 0 -or $missingKeys -gt 0) {
    Write-Host "note: .env / .env.local / config/runtime 为本地生成文件，未生成属正常（首次启动用 -InitializeLocal）。"
    exit 0
}
