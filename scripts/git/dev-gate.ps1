[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$SkipRuff,
    [switch]$SkipTypecheck,
    [switch]$SkipLint,
    [switch]$SkipGuard
)

<#
.SYNOPSIS
    测试平台 代码开发校验门禁（本地一键版）：串起 G0–G2 的机械强制项。

.DESCRIPTION
    对应 docs/code-development-gate.md 的第 7.1 节。按顺序执行并聚合 HARD 结果，
    让「不合格代码」在 commit/push 前就被拦下，减少返工。

    执行顺序：
      G0 scan-common-bugs.ps1     提交卫生（调试遗留/硬编码密钥/静默吞异常）
      G1 ruff F821                后端未定义符号
      G1 npm run typecheck        前端类型
      G1 npm run lint             前端风格
      G2 route-layer guard tests  后端路由层禁 ORM + 路径集基线

    退出码：
      0 全部通过
      1 存在 HARD / 未定义符号 / 类型错误 / 守卫测试失败
      2 存在 WARN（scan-common-bugs 非硬失败）—— 需人工复核

.EXAMPLE
    pwsh scripts/git/dev-gate.ps1 -RepositoryPath (Get-Location).Path
    # 仅前端：
    pwsh scripts/git/dev-gate.ps1 -SkipBackend
#>

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-GitRoot {
    param([string]$Path)
    $out = @(& git -C $Path rev-parse --show-toplevel 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "Not a git repository: $Path" }
    return $out[0].Trim()
}

$root = Get-GitRoot -Path $RepositoryPath
$backend = Join-Path $root "test-platform-v2/backend"
$frontend = Join-Path $root "test-platform-v2/frontend"
$scanScript = Join-Path $root "scripts/git/scan-common-bugs.ps1"

$failed = $false
$warnFound = $false

Write-Host "== 代码开发校验门禁（G0-G2） =="
Write-Host "repo = $root"

# ── G0 提交卫生 ───────────────────────────────────────
if (Test-Path -LiteralPath $scanScript) {
    Write-Host "`n[G0] scan-common-bugs ..."
    $scanOut = @(& $scanScript -RepositoryPath $root 6>&1)
    $scanExit = $LASTEXITCODE
    $scanOut | Write-Host
    if ($scanExit -eq 1) { $failed = $true; Write-Host "  -> HARD findings found (Block)" }
    elseif ($scanExit -eq 2) { $warnFound = $true; Write-Host "  -> WARN findings found (需复核)" }
    Write-Host "  -> exit=$scanExit"
}
else {
    Write-Host "`n[G0] scan-common-bugs SKIPPED (script missing)"
}

# ── G1 后端 F821 ─────────────────────────────────────
if (-not $SkipBackend -and -not $SkipRuff -and (Test-Path -LiteralPath $backend)) {
    Write-Host "`n[G1] ruff F821 ..."
    Push-Location $backend
    try {
        $out = @(& ruff check app/ --select F821 --output-format=concise 2>&1)
        $code = $LASTEXITCODE
        $out | Write-Host
        if ($code -ne 0) { $failed = $true; Write-Host "  -> F821 found (Block)" }
        Write-Host "  -> exit=$code"
    }
    finally { Pop-Location }
}
else { Write-Host "`n[G1] ruff F821 SKIPPED (-SkipBackend/-SkipRuff or dir missing)" }

# ── G1 前端 typecheck + lint ──────────────────────────
if (-not $SkipFrontend -and (Test-Path -LiteralPath (Join-Path $frontend "package.json"))) {
    if (-not $SkipTypecheck) {
        Write-Host "`n[G1] npm run typecheck ..."
        Push-Location $frontend
        try {
            $out = @(& npm run typecheck 2>&1)
            $code = $LASTEXITCODE
            $out | Select-Object -Last 40 | Write-Host
            if ($code -ne 0) { $failed = $true; Write-Host "  -> typecheck FAILED (Block)" }
            Write-Host "  -> exit=$code"
        }
        finally { Pop-Location }
    }
    else { Write-Host "`n[G1] typecheck SKIPPED (-SkipTypecheck)" }

    if (-not $SkipLint) {
        Write-Host "`n[G1] npm run lint ..."
        Push-Location $frontend
        try {
            $out = @(& npm run lint 2>&1)
            $code = $LASTEXITCODE
            $out | Select-Object -Last 40 | Write-Host
            if ($code -ne 0) { $failed = $true; Write-Host "  -> lint FAILED (Block)" }
            Write-Host "  -> exit=$code"
        }
        finally { Pop-Location }
    }
    else { Write-Host "`n[G1] lint SKIPPED (-SkipLint)" }
}
else { Write-Host "`n[G1] frontend SKIPPED (-SkipFrontend or package.json missing)" }

# ── G2 后端守卫测试（路由禁 ORM + 路径集基线） ─────────
if (-not $SkipBackend -and -not $SkipGuard -and (Test-Path -LiteralPath $backend)) {
    Write-Host "`n[G2] route-layer guard tests ..."
    Push-Location $backend
    try {
        $targets = @(
            "tests/test_route_layer_orm_ban.py",
            "tests/test_route_inventory.py"
        )
        $present = @($targets | Where-Object { Test-Path -LiteralPath $_ })
        if ($present.Count -eq 0) {
            Write-Host "  -> guard tests not found (目录差异); 视为通过，需确认分类器/守卫存在"
        }
        else {
            $out = @(& (Get-Command python -ErrorAction SilentlyContinue).Source -m pytest -q @present 2>&1)
            $code = $LASTEXITCODE
            $out | Select-Object -Last 60 | Write-Host
            if ($code -ne 0) { $failed = $true; Write-Host "  -> guard FAILED (Block)" }
            Write-Host "  -> exit=$code"
        }
    }
    finally { Pop-Location }
}
else { Write-Host "`n[G2] guard tests SKIPPED (-SkipBackend/-SkipGuard or dir missing)" }

# ── 汇总 ─────────────────────────────────────────────
Write-Host "`n== 门禁汇总 =="
if ($failed) {
    Write-Host "GATE_RESULT=FAIL (存在 HARD/类型/守卫失败项 -> 请修复后重跑)"
    exit 1
}
if ($warnFound) {
    Write-Host "GATE_RESULT=PASS_WITH_WARN (机械项通过; 存在 WARN -> 人工复核)"
    exit 2
}
Write-Host "GATE_RESULT=PASS (G0-G2 机械门禁全部通过; 请继续走 G3 评审 + CI 全量)"
exit 0
