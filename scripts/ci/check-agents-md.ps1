# AIQE AGENTS.md 守卫：确保 Codex 新 session 能读到 AIQE 关键入口与门禁。
[CmdletBinding()]
param(
    [string]$RepositoryPath = "."
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $RepositoryPath).Path
$path = Join-Path $root "AGENTS.md"
if (-not (Test-Path -LiteralPath $path)) {
    Write-Host "AGENTS_GUARD=FAIL 缺少 AGENTS.md"
    exit 1
}
$text = Get-Content -Raw -LiteralPath $path

$required = @(
    "## 5.5 AIQE 专项规范",
    "docs/aiqe/ops.md",
    "docs/aiqe/rollback.md",
    "scripts/mcp-server/README.md",
    "check-oracle-layer.ps1",
    "check-aiqe-skills.ps1"
)
$missing = @($required | Where-Object { -not $text.Contains($_) })

if ($missing.Count -gt 0) {
    Write-Host "AGENTS_GUARD=FAIL 缺少: $($missing -join ', ')"
    exit 1
}
Write-Host "AGENTS_GUARD=PASS"
exit 0
