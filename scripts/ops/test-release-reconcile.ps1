#requires -Version 5.1
<#
test-release-reconcile.ps1 — `release-reconcile.ps1` 的自检（桩驱动，不触网不碰生产）。

用法：pwsh scripts/ops/test-release-reconcile.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'release-reconcile.ps1')

$noop = { param([string]$Message) }
$noSleep = { param([int]$Seconds) }
$failures = 0

function Assert-Case {
    param([string]$Name, [bool]$Condition, [string]$Detail = '')
    if ($Condition) {
        Write-Host "  PASS  $Name" -ForegroundColor Green
    } else {
        Write-Host "  FAIL  $Name $Detail" -ForegroundColor Red
        $script:failures++
    }
}

Write-Host '== test-release-reconcile ==' -ForegroundColor Cyan

# 1. 请求中断但服务端已成功（2026-09-17 实际场景）
$states = [System.Collections.Generic.Queue[string]]::new()
$states.Enqueue('PROD_DEPLOYING'); $states.Enqueue('PROD_OBSERVING')
$r = Resolve-DeploymentOutcome -DeploymentId 'd1' -QueryState { param($id) $states.Dequeue() } `
    -DelaySeconds 0 -Sleep $noSleep -Log $noop
Assert-Case '中断但服务端已完成 → Succeeded=true' ($r.Reconciled -and $r.Succeeded -and $r.State -eq 'PROD_OBSERVING') $r.Reason

# 2. 服务端确认失败
$r = Resolve-DeploymentOutcome -DeploymentId 'd2' -QueryState { param($id) 'PROD_FAILED' } `
    -DelaySeconds 0 -Sleep $noSleep -Log $noop
Assert-Case '服务端失败 → Succeeded=false 且 Reconciled=true' ($r.Reconciled -and -not $r.Succeeded -and $r.State -eq 'PROD_FAILED')

# 3. 控制面不可达 → 不臆断
$r = Resolve-DeploymentOutcome -DeploymentId 'd3' -QueryState { param($id) throw 'unreachable' } `
    -Attempts 2 -DelaySeconds 0 -Sleep $noSleep -Log $noop
Assert-Case '查询不到状态 → Reconciled=false（交人工）' ((-not $r.Reconciled) -and (-not $r.Succeeded))

# 4. 未到终态（仍在部署）→ 不当成成功
$r = Resolve-DeploymentOutcome -DeploymentId 'd4' -QueryState { param($id) 'PROD_DEPLOYING' } `
    -Attempts 2 -DelaySeconds 0 -Sleep $noSleep -Log $noop
Assert-Case '仍在部署中 → Succeeded=false 且提示人工确认' ((-not $r.Succeeded) -and $r.State -eq 'PROD_DEPLOYING')

# 5. 异常后恢复可用（前两次抛错，第三次拿到状态）
$script:call = 0
$r = Resolve-DeploymentOutcome -DeploymentId 'd5' -QueryState {
    param($id) $script:call++; if ($script:call -lt 3) { throw 'flaky' } else { 'PRODUCTION_VERIFIED' }
} -Attempts 3 -DelaySeconds 0 -Sleep $noSleep -Log $noop
Assert-Case '查询抖动后恢复 → Succeeded=true' ($r.Succeeded -and $r.State -eq 'PRODUCTION_VERIFIED')

# 6. 回滚意图：PROD_ROLLED_BACK 视为成功
$r = Resolve-DeploymentOutcome -DeploymentId 'd6' -QueryState { param($id) 'PROD_ROLLED_BACK' } `
    -DelaySeconds 0 -Sleep $noSleep -Log $noop `
    -SuccessStates @('PROD_ROLLED_BACK') -FailureStates @('PROD_FAILED')
Assert-Case '回滚意图：PROD_ROLLED_BACK → Succeeded=true' ($r.Succeeded -and $r.State -eq 'PROD_ROLLED_BACK')

if ($failures -gt 0) {
    Write-Host "== FAILED ($failures) ==" -ForegroundColor Red
    exit 1
}
Write-Host '== ALL PASS ==' -ForegroundColor Green
