#!/usr/bin/env pwsh
<#
.SYNOPSIS
    TA-001.5 / batch-277 — AIQE §0 P0-1..5 fail-closed readiness guard.

.DESCRIPTION
    M0 Gate 的机械守卫：只有 P0-1..5 全部拿到可复核证据时才返回 0。

    - P0-1 / P0-2 / P0-3 / P0-4：读取 work-logs/p0-evidence/*.json
      （status=pass + checked_at 在 MaxEvidenceAgeDays 内）
    - P0-2：额外静态扫描 Alembic upgrade()：禁止 op.drop_table，
            且 `DROP TABLE` 必须带 `IF EXISTS`（13 号 §0 P0-2）
    - P0-4：额外静态扫描控制面 Dockerfile：不得安装 Playwright/Chromium
    - P0-5：静态扫描后端 app/tests/scripts：ai_gateway|AiJob|AiShadowRun|AiGatewayCache
            命中必须为 0，且 Alembic 必须单 head（历史 migration 不计入业务代码）

    任何一条缺失/过期/不通过 => 退出码 1（CI fail-closed），并输出失败原因。

.PARAMETER SelfTest
    用临时仓库骨架 + 临时证据验证守卫行为（全绿 => 0，缺一条 => 1），不触碰真实仓库。

.EXAMPLE
    pwsh scripts/ci/check-p0-ready.ps1
    pwsh scripts/ci/check-p0-ready.ps1 -SelfTest
#>
[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [string]$EvidenceRoot,
    [int]$MaxEvidenceAgeDays = 30,
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-RepoRoot([string]$Path) {
    $out = @(& git -C $Path rev-parse --show-toplevel 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "Not a git repository: $Path" }
    return $out[0].Trim()
}

function New-Result([string]$Id, [string]$Name, [bool]$Pass, [string]$Detail) {
    [pscustomobject]@{ Id = $Id; Name = $Name; Pass = $Pass; Detail = $Detail }
}

function Test-Evidence {
    param([string]$Root, [string]$File)
    $path = Join-Path $Root $File
    if (-not (Test-Path -LiteralPath $path)) {
        return @{ Pass = $false; Detail = "证据缺失: $File" }
    }
    try {
        $doc = Get-Content -Raw -LiteralPath $path | ConvertFrom-Json
    }
    catch {
        return @{ Pass = $false; Detail = "证据无法解析为 JSON: $File" }
    }
    if ([string]$doc.status -ne "pass") {
        return @{ Pass = $false; Detail = "status=$($doc.status)（需 pass）" }
    }
    if (-not $doc.PSObject.Properties["checked_at"]) {
        return @{ Pass = $false; Detail = "缺 checked_at" }
    }
    try { $checked = [datetimeoffset]::Parse([string]$doc.checked_at) }
    catch { return @{ Pass = $false; Detail = "checked_at 无法解析" } }
    $ageDays = ([datetimeoffset]::UtcNow - $checked).TotalDays
    if ($ageDays -gt $MaxEvidenceAgeDays) {
        return @{ Pass = $false; Detail = ("证据过期 {0:N1} 天（上限 {1}）" -f $ageDays, $MaxEvidenceAgeDays) }
    }
    $ev = @(@($doc.evidence) | Where-Object { $_ })
    return @{ Pass = $true; Detail = ("checked_at={0:yyyy-MM-dd} evidence={1} 项" -f $checked, $ev.Count) }
}

function Test-NoUnsafeDrop {
    param([string]$VersionsDir)
    $bad = @()
    if (-not (Test-Path -LiteralPath $VersionsDir)) {
        return @{ Pass = $false; Detail = "alembic/versions 不存在" }
    }
    foreach ($file in Get-ChildItem -LiteralPath $VersionsDir -Filter *.py -File) {
        $text = Get-Content -Raw -LiteralPath $file.FullName
        $m = [regex]::Match($text, "(?s)def upgrade\(\)(.*?)def downgrade\(\)")
        if (-not $m.Success) { continue }
        $upgrade = $m.Groups[1].Value
        if ($upgrade -match "op\.drop_table\(") {
            $bad += "$($file.Name): op.drop_table() in upgrade()"
        }
        foreach ($hit in [regex]::Matches($upgrade, "DROP TABLE[^""']*", "IgnoreCase")) {
            if ($hit.Value -notmatch "IF EXISTS") {
                $bad += "$($file.Name): '$($hit.Value.Trim())' 缺 IF EXISTS"
            }
        }
    }
    return @{ Pass = ($bad.Count -eq 0); Detail = if ($bad.Count) { $bad -join "; " } else { "upgrade() 内无裸 DROP" } }
}

function Get-AlembicHeads {
    param([string]$HelperPath, [string]$VersionsDir)
    if (-not (Test-Path -LiteralPath $HelperPath)) {
        return @{ Heads = @(); Error = "缺少 heads 检测脚本 $HelperPath" }
    }
    $out = @(& python $HelperPath $VersionsDir 2>&1)
    if ($LASTEXITCODE -ne 0) {
        return @{ Heads = @(); Error = (($out | Out-String).Trim()) }
    }
    $heads = @($out | Where-Object { "$_".Trim() })
    return @{ Heads = $heads; Error = $null }
}

function Test-ControlPlaneNoBrowser {
    param([string]$BackendDir)
    $dockerfile = Join-Path $BackendDir "Dockerfile"
    if (-not (Test-Path -LiteralPath $dockerfile)) {
        return @{ Pass = $false; Detail = "未找到控制面 Dockerfile" }
    }
    $text = Get-Content -Raw -LiteralPath $dockerfile
    $hits = @([regex]::Matches($text, "(?im)^.*(playwright\s+install|install\s+.*chromium).*$"))
    return @{ Pass = ($hits.Count -eq 0); Detail = if ($hits.Count) { "Dockerfile 仍安装浏览器: $($hits[0].Value.Trim())" } else { "控制面 Dockerfile 无浏览器安装" } }
}

function Test-AiGatewayResidue {
    param([string]$BackendDir)
    $pattern = "ai_gateway|AiJob|AiShadowRun|AiGatewayCache"
    $targets = @(
        (Join-Path $BackendDir "app"),
        (Join-Path $BackendDir "tests"),
        (Join-Path $BackendDir "scripts")
    ) | Where-Object { Test-Path -LiteralPath $_ }
    $hits = @()
    foreach ($dir in $targets) {
        $hits += @(Get-ChildItem -LiteralPath $dir -Recurse -Filter *.py -File |
            Select-String -Pattern $pattern |
            ForEach-Object { "$($_.Path):$($_.LineNumber)" })
    }
    return @{ Pass = ($hits.Count -eq 0); Detail = if ($hits.Count) { "$($hits.Count) 处残留: $($hits[0])" } else { "后端代码 0 残留" } }
}

function Invoke-Checks {
    param([string]$EvidenceDir, [string]$BackendDir, [string]$VersionsDir, [string]$HelperPath)
    $results = [System.Collections.Generic.List[object]]::new()

    $p1 = Test-Evidence -Root $EvidenceDir -File "P0-1-ai-key-rotation.json"
    $results.Add((New-Result "P0-1" "生产 4 个 AI Key 轮换 + 真实调用" $p1.Pass $p1.Detail))

    $p2drop = Test-NoUnsafeDrop -VersionsDir $VersionsDir
    $p2ev = Test-Evidence -Root $EvidenceDir -File "P0-2-backup-restore.json"
    $results.Add((New-Result "P0-2" "备份恢复演练 + DROP 守卫 + downgrade 可执行" ($p2drop.Pass -and $p2ev.Pass) ("$($p2ev.Detail); $($p2drop.Detail)")))

    $p3 = Test-Evidence -Root $EvidenceDir -File "P0-3-disk-watermark.json"
    $results.Add((New-Result "P0-3" "磁盘水位 <=80% 维持 48h + 告警收条" $p3.Pass $p3.Detail))

    $p4static = Test-ControlPlaneNoBrowser -BackendDir $BackendDir
    $p4ev = Test-Evidence -Root $EvidenceDir -File "P0-4-control-plane-no-browser.json"
    $results.Add((New-Result "P0-4" "/uitest 剥离控制面浏览器 + 走 node" ($p4static.Pass -and $p4ev.Pass) ("$($p4ev.Detail); $($p4static.Detail)")))

    $p5 = Test-AiGatewayResidue -BackendDir $BackendDir
    $heads = Get-AlembicHeads -HelperPath $HelperPath -VersionsDir $VersionsDir
    $single = $heads.Heads.Count -eq 1
    $headsDetail = if ($heads.Error) { "alembic heads 检测失败: $($heads.Error)" } else { "alembic heads=$($heads.Heads.Count)" }
    $results.Add((New-Result "P0-5" "ai_gateway/AiJob/AiShadowRun/AiGatewayCache 清零 + 单 head" ($p5.Pass -and $single) ("$($p5.Detail); $headsDetail")))

    return $results
}

function Write-Results($results) {
    $results | Format-Table -AutoSize Id, Name, Pass, Detail | Out-String -Width 240 | Write-Host
    $failed = @($results | Where-Object { -not $_.Pass })
    if ($failed.Count -gt 0) {
        Write-Host ("GATE_RESULT=FAIL ({0}/5 未通过: {1})" -f $failed.Count, (($failed | ForEach-Object { $_.Id }) -join ",")) -ForegroundColor Red
        return 1
    }
    Write-Host "GATE_RESULT=PASS (P0-1..5 全部拿到可复核证据)" -ForegroundColor Green
    return 0
}

function New-SelfTestFixture {
    param([string]$Root)
    $backend = Join-Path $Root "test-platform-v2/backend"
    foreach ($dir in @("app", "tests", "scripts", "alembic/versions")) {
        New-Item -ItemType Directory -Path (Join-Path $backend $dir) -Force | Out-Null
    }
    Set-Content -LiteralPath (Join-Path $backend "Dockerfile") -Encoding UTF8 -Value "FROM python:3.12-slim`nRUN pip install -r requirements.txt`n"
    $migration = @'
revision = "0001_selftest"
down_revision = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
'@
    Set-Content -LiteralPath (Join-Path $backend "alembic/versions/0001_selftest.py") -Encoding UTF8 -Value $migration
    $evidence = Join-Path $Root "evidence"
    New-Item -ItemType Directory -Path $evidence -Force | Out-Null
    foreach ($name in @("P0-1-ai-key-rotation.json", "P0-2-backup-restore.json", "P0-3-disk-watermark.json", "P0-4-control-plane-no-browser.json")) {
        @{ status = "pass"; checked_at = (Get-Date).ToUniversalTime().ToString("o"); evidence = @("selftest") } |
            ConvertTo-Json -Depth 3 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence $name)
    }
    return @{ Backend = $backend; Versions = (Join-Path $backend "alembic/versions"); Evidence = $evidence }
}

$helper = Join-Path $PSScriptRoot "alembic_heads.py"

if ($SelfTest) {
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("p0-selftest-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $fx = New-SelfTestFixture -Root $tmp
    Write-Host "== SelfTest: 全绿（期望 PASS） =="
    $passCode = Write-Results (Invoke-Checks -EvidenceDir $fx.Evidence -BackendDir $fx.Backend -VersionsDir $fx.Versions -HelperPath $helper)
    Write-Host "== SelfTest: 删除 P0-3 证据（期望 FAIL） =="
    Remove-Item -LiteralPath (Join-Path $fx.Evidence "P0-3-disk-watermark.json") -Force
    $failCode = Write-Results (Invoke-Checks -EvidenceDir $fx.Evidence -BackendDir $fx.Backend -VersionsDir $fx.Versions -HelperPath $helper)
    Remove-Item -LiteralPath $tmp -Recurse -Force
    if ($passCode -eq 0 -and $failCode -eq 1) {
        Write-Host "SELFTEST=PASS" -ForegroundColor Green
        exit 0
    }
    Write-Host "SELFTEST=FAIL (期望 PASS=0/FAIL=1，实际 PASS=$passCode/FAIL=$failCode)" -ForegroundColor Red
    exit 1
}

$root = Get-RepoRoot $RepositoryPath
if (-not $EvidenceRoot) { $EvidenceRoot = Join-Path $root "work-logs/p0-evidence" }
$backend = Join-Path $root "test-platform-v2/backend"
$versions = Join-Path $backend "alembic/versions"
$code = Write-Results (Invoke-Checks -EvidenceDir $EvidenceRoot -BackendDir $backend -VersionsDir $versions -HelperPath $helper)
exit $code
