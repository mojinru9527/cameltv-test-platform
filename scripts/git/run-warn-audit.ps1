[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [string]$BaselinePath,
    [string]$BatchLabel = "",
    [switch]$NoTrendAppend
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-GitRoot {
    param([string]$Path)
    $out = @(& git -C $Path rev-parse --show-toplevel 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "Not a git repository: $Path" }
    return $out[0].Trim()
}

$root = Get-GitRoot -Path $RepositoryPath
if (-not $BaselinePath) { $BaselinePath = Join-Path $root "docs/agent-team/warn-baseline.json" }
$inventory = Join-Path $root "docs/agent-team/warn-inventory.md"

$scanScript = Join-Path $root "scripts/git/scan-common-bugs.ps1"
$scanOut = @(& $scanScript -RepositoryPath $root -BaselinePath $BaselinePath 6>&1)
$scanExit = $LASTEXITCODE

Write-Host "== run-warn-audit =="
$scanOut | Write-Host

# 解析扫描结果
$warnTotal = 0
$hardTotal = 0
$newCats = 0
$newFiles = 0
foreach ($line in $scanOut) {
    if ($line -match '^HARD findings\s*:\s*(\d+)') { $hardTotal = [int]$Matches[1] }
    if ($line -match '^WARN findings\s*:\s*(\d+)') { $warnTotal = [int]$Matches[1] }
    if ($line -match 'new warn categories:\s*(\d+)') { $newCats = [int]$Matches[1] }
    if ($line -match '/ new files:\s*(\d+)') { $newFiles = [int]$Matches[1] }
}

if ($scanExit -eq 1) {
    Write-Host "AUDIT_RESULT=FAIL (HARD=$hardTotal)"
    exit 1
}

# 追加趋势表（幂等：同一天只追加一次）
if (-not $NoTrendAppend -and (Test-Path -LiteralPath $inventory)) {
    $today = (Get-Date).ToString("yyyy-MM-dd")
    $content = Get-Content -Raw -LiteralPath $inventory
    if ($content -match "(?m)^\|\s*$today\s*\|.*自动审计\s*\|") {
        Write-Host "TREND_APPEND=skipped (今天已有记录)"
    }
    else {
        $lines = $content -split "`n"
        $insertAt = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match '^\|\s*\d{4}-\d{2}-\d{2}\s*\|') { $insertAt = $i }
        }
        if ($insertAt -lt 0) { $insertAt = $lines.Count - 1 }
        $row = "| $today | $BatchLabel | $warnTotal | $newCats | $newFiles | 自动审计 |"
        $newLines = New-Object System.Collections.Generic.List[string]
        for ($i = 0; $i -le $insertAt; $i++) { $newLines.Add($lines[$i]) }
        $newLines.Add($row)
        for ($i = $insertAt + 1; $i -lt $lines.Count; $i++) { $newLines.Add($lines[$i]) }
        ($newLines -join "`n") | Set-Content -Encoding UTF8 -LiteralPath $inventory
        Write-Host "TREND_APPEND=ok ($today, WARN=$warnTotal, newCats=$newCats)"
    }
}
elseif (-not (Test-Path -LiteralPath $inventory)) {
    Write-Host "TREND_APPEND=skipped (inventory 不存在)"
}

if ($newCats -gt 0 -or $newFiles -gt 0) {
    Write-Host "AUDIT_RESULT=NEW_WARN (需人工归因复核)"
    exit 2
}
Write-Host "AUDIT_RESULT=OK (WARN=$warnTotal, HARD=$hardTotal, delta 0)"
exit 0
