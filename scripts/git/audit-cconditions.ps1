[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [string]$WorklogsPath,
    [switch]$RequireLatestBatch
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
$trackerPath = Join-Path $root "C-CONDITIONS.md"
if (-not (Test-Path -LiteralPath $trackerPath)) {
    Write-Error "C-CONDITIONS.md not found at $trackerPath"
    exit 1
}

$worklogDirs = @()
if ($WorklogsPath) {
    if (Test-Path -LiteralPath $WorklogsPath) { $worklogDirs += $WorklogsPath }
    else { Write-Error "WorklogsPath not found: $WorklogsPath"; exit 1 }
}
else {
    $worklogDirs += @(
        (Join-Path $root "test-platform-v2/work-logs"),
        (Join-Path $root "work-logs")
    ) | Where-Object { Test-Path -LiteralPath $_ }
}
if ($worklogDirs.Count -eq 0) {
    Write-Error "No work-logs directory found under $root"
    exit 1
}

$hardErrors = @()
$warnings = @()

# 检查 1: 状态机规则头
$tracker = Get-Content -Raw -LiteralPath $trackerPath
if ($tracker -notmatch "Open（待处理）" -or $tracker -notmatch "Closed（已关闭" -or $tracker -notmatch "Deferred（延期") {
    $hardErrors += "C-CONDITIONS.md 缺少 Batch 75 状态机规则头（Open/Closed/Deferred）"
}

# 检查 2 + 3: 条件 ID 一致性
$verdictFiles = @($worklogDirs | ForEach-Object {
    Get-ChildItem -LiteralPath $_ -Recurse -Filter "batch-*-leader-verdict.md" -File -ErrorAction SilentlyContinue
})
$verdictIds = New-Object System.Collections.Generic.HashSet[string]
$trackerIdList = New-Object System.Collections.Generic.List[string]
$trackerIds = New-Object System.Collections.Generic.HashSet[string]

$idPattern = '(?:TPv2-B\d+-)?(?:C|G|CP)\d+[-_][A-Za-z]?\d+(?:[-_][A-Za-z]?\d+)*'
# 区间简写（batch-18/e verdict 用 "C1-C3"/"C5-C8" 表示连续条件区间，非真实条件 ID）
$proseRangeTokens = @('C1-C3', 'C5-C8')
$allowedNext = [System.Collections.Generic.HashSet[char]]::new()
foreach ($c in @(':', '：', '|', '*', '（', '(', ' ', '、', ',', '，', ';', '；')) {
    [void]$allowedNext.Add([char]$c)
}
function ConvertTo-NormalizedId([string]$value) {
    $v = $value.ToUpperInvariant().Trim()
    if ($v.StartsWith("BATCH-")) { $v = $v.Substring(6) }
    return $v
}
function Get-ConditionIds([string]$text) {
    $ids = New-Object System.Collections.Generic.HashSet[string]
    foreach ($match in [regex]::Matches($text, $idPattern)) {
        if ($proseRangeTokens -contains $match.Value) { continue }
        $nextIdx = $match.Index + $match.Length
        if ($nextIdx -lt $text.Length -and -not $allowedNext.Contains($text[$nextIdx])) { continue }
        [void]$ids.Add((ConvertTo-NormalizedId $match.Value))
    }
    return $ids
}
foreach ($id in (Get-ConditionIds -Text $tracker)) {
    $trackerIdList.Add($id)
    [void]$trackerIds.Add($id)
}
foreach ($file in $verdictFiles) {
    $content = Get-Content -Raw -LiteralPath $file.FullName
    foreach ($id in (Get-ConditionIds -Text $content)) { [void]$verdictIds.Add($id) }
}

foreach ($id in ($verdictIds | Sort-Object)) {
    if (-not $trackerIds.Contains($id)) {
        $hardErrors += "孤儿条件: $id 出现在 leader-verdict 但不在 C-CONDITIONS.md"
    }
}

# 检查 4: Closed 必须带证据
$closedCount = 0
$closedMissingEvidence = 0
$evidencePattern = 'PR|commit|#\d+|http|已关闭|Closed|close'
foreach ($line in ($tracker -split "`n")) {
    if ($line -match 'Closed|✅ Closed') {
        $closedCount++
        if ($line -notmatch $evidencePattern) {
            $closedMissingEvidence++
            $warnings += "Closed 行缺证据: $($line.Trim().Substring(0, [Math]::Min(80, $line.Trim().Length)))"
        }
    }
}

# 检查 6: 最后更新日期 vs 最新 leader-verdict 日期
$trackerDateMatch = [regex]::Match($tracker, '最后更新[^\d]*(\d{4}-\d{2}-\d{2})')
$trackerDate = if ($trackerDateMatch.Success) { [datetime]$trackerDateMatch.Groups[1].Value } else { $null }
$newestVerdictDate = $null
foreach ($file in $verdictFiles) {
    $head = Get-Content -LiteralPath $file.FullName -TotalCount 5
    $dateMatch = [regex]::Match(($head -join " "), 'Date:\s*(\d{4}-\d{2}-\d{2})')
    if ($dateMatch.Success) {
        $d = [datetime]$dateMatch.Groups[1].Value
        if (-not $newestVerdictDate -or $d -gt $newestVerdictDate) { $newestVerdictDate = $d }
    }
}
if ($trackerDate -and $newestVerdictDate -and $trackerDate -lt $newestVerdictDate) {
    $msg = "C-CONDITIONS 最后更新 $($trackerDate.ToString('yyyy-MM-dd')) 早于最新 verdict $($newestVerdictDate.ToString('yyyy-MM-dd'))"
    if ($RequireLatestBatch) { $hardErrors += $msg } else { $warnings += $msg }
}

# 检查 7 (C90-1): 统计口径 —— 按文件实际解析 Open/Closed/Deferred 计数，禁止手工漂移
function Get-ConditionStats {
    param([string]$TrackerText)
    $openRows = @{}; $closedRows = @{}; $deferredRows = @{}
    $section = ""
    $inDeferredSection = $false
    foreach ($ln in ($TrackerText -split "`n")) {
        if ($ln -match '^## Open') { $section = "open"; continue }
        if ($ln -match '^## In Progress') { $section = "inprogress"; continue }
        if ($ln -match '^## Closed') { $section = "closed"; continue }
        if ($ln -match '^## 历史引用归档') { $section = "archive"; continue }
        if ($ln -match '^### ') {
            $inDeferredSection = ($section -eq "open" -and $ln -match 'Deferred')
            continue
        }
        if ($section -notin @("open", "closed") -or $ln -notmatch '^\|') { continue }
        $cells = @($ln.Trim('|') -split '\|' | ForEach-Object { $_.Trim() })
        if ($cells.Count -lt 1 -or $cells[0] -eq "" -or $cells[0] -eq "ID" -or $cells[0] -eq "—" -or $cells[0] -match '^-+$') { continue }
        $id = $cells[0]
        if ($section -eq "open") {
            $openRows[$id] = $ln
            if ($inDeferredSection) { $deferredRows[$id] = $ln }
        } else {
            $closedRows[$id] = $ln
        }
    }
    $realOpen = @($openRows.Keys | Where-Object {
        $row = $openRows[$_]
        $row -notmatch 'CLOSED|✅ Closed|~~' -and -not $closedRows.ContainsKey($_)
    })
    return [pscustomobject]@{
        OpenRows  = $openRows.Count
        RealOpen  = $realOpen.Count
        Deferred  = $deferredRows.Count
        Closed    = $closedRows.Count
    }
}
$stats = Get-ConditionStats -TrackerText $tracker

# 输出
Write-Host "== audit-cconditions =="
Write-Host "tracker      : $trackerPath"
Write-Host "worklogs     : $($worklogDirs -join '; ')"
Write-Host "verdicts     : $($verdictFiles.Count) files"
Write-Host "condition ids: $($trackerIds.Count) in tracker, $($verdictIds.Count) referenced in verdicts"
Write-Host "closed rows  : $closedCount (missing evidence: $closedMissingEvidence)"
Write-Host "stats        : Open=$($stats.RealOpen) (rows=$($stats.OpenRows), deferred=$($stats.Deferred)) Closed=$($stats.Closed)"
Write-Host "hard errors  : $($hardErrors.Count)"
foreach ($e in $hardErrors) { Write-Host "  [ERROR] $e" }
Write-Host "warnings     : $($warnings.Count)"
foreach ($w in $warnings) { Write-Verbose $w }

if ($hardErrors.Count -gt 0) { exit 1 }
if ($warnings.Count -gt 0) { exit 2 }
exit 0
