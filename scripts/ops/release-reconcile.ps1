<#
release-reconcile.ps1 — C252-1：发布/回滚请求在网络中断时的**状态核对**。

背景（2026-09-17 实测）：`release.ps1 -Publish` 的 publish 请求在客户端侧抛
"An error occurred while sending the request."，脚本直接 `throw "发布失败"`；
但服务端**已完整执行成功**（容器重建 healthy、事件到 PROD_OBSERVING、
随后 /verify 返回 production verified）。运维会误以为失败，可能重复发布或误回滚。

本模块只做一件事：请求异常后，按 deployment id 查控制面状态，判断"到底成没成"。
纯函数 + 可注入查询/等待，便于 `test-release-reconcile.ps1` 用桩验证。
#>
Set-StrictMode -Version Latest

# 出现在这些状态说明服务端已经跑起来/跑完（不需要重新发布）
$script:ReconciledSuccessStates = @('PROD_OBSERVING', 'PRODUCTION_VERIFIED')
# 这些状态说明服务端确实失败了（可以安全地按失败处理）
$script:ReconciledFailureStates = @('PROD_FAILED', 'PROD_ROLLED_BACK', 'TEST_FAILED', 'TEST_ROLLED_BACK', 'CANCELLED')

function Resolve-DeploymentOutcome {
    <#
    .SYNOPSIS
        请求异常后按 deployment id 核对真实状态。
    .PARAMETER QueryState
        返回当前状态的脚本块（如 { param($id) (Invoke-Api 'GET' "/api/deployments/$id").state }）。
    .OUTPUTS
        [pscustomobject] Reconciled / Succeeded / State / Attempts / Reason
    #>
    param(
        [Parameter(Mandatory)][string]$DeploymentId,
        [Parameter(Mandatory)][scriptblock]$QueryState,
        [int]$Attempts = 3,
        [int]$DelaySeconds = 5,
        [scriptblock]$Sleep = { param([int]$Seconds) Start-Sleep -Seconds $Seconds },
        [scriptblock]$Log = { param([string]$Message) Write-Host $Message },
        [string[]]$SuccessStates = @('PROD_OBSERVING', 'PRODUCTION_VERIFIED'),
        [string[]]$FailureStates = @('PROD_FAILED', 'PROD_ROLLED_BACK', 'TEST_FAILED', 'TEST_ROLLED_BACK', 'CANCELLED')
    )

    $state = $null
    for ($i = 1; $i -le [Math]::Max(1, $Attempts); $i++) {
        try {
            $state = [string](& $QueryState $DeploymentId)
        } catch {
            $state = $null
        }
        if ($state) {
            if ($SuccessStates -contains $state -or $FailureStates -contains $state) { break }
            if ($i -lt $Attempts) {
                & $Log "  核对中（$i/$Attempts）：当前状态 $state，等待 $DelaySeconds s 后重试…"
                & $Sleep $DelaySeconds
            }
        } elseif ($i -lt $Attempts) {
            & $Sleep $DelaySeconds
        }
    }

    if (-not $state) {
        return [pscustomobject]@{
            Reconciled = $false; Succeeded = $false; State = ''; Attempts = $Attempts
            Reason = '无法查询发布状态（控制面不可达）——请人工到控制台确认后再决定是否重发'
        }
    }
    if ($SuccessStates -contains $state) {
        return [pscustomobject]@{
            Reconciled = $true; Succeeded = $true; State = $state; Attempts = $Attempts
            Reason = "服务端已完成（状态 $state）：请求只是中断，不要重发"
        }
    }
    if ($FailureStates -contains $state) {
        return [pscustomobject]@{
            Reconciled = $true; Succeeded = $false; State = $state; Attempts = $Attempts
            Reason = "服务端确认失败（状态 $state）"
        }
    }
    return [pscustomobject]@{
        Reconciled = $true; Succeeded = $false; State = $state; Attempts = $Attempts
        Reason = "状态仍为 $state（未到终态）：发布可能仍在进行，请到控制台确认后再操作"
    }
}
