#requires -Version 5.1
<#
verify-reused-image.ps1 — C249-5：沿用旧镜像 / 打补丁镜像前的核对

背景（Batch 248 runner 热修事故）：runner target 本机不可构建时，发布改用"复用已验证
镜像 / 打补丁镜像"。镜像里的转发面（RUNNER_ENDPOINTS）或 alembic/versions 一旦与当前
配置不一致，会出现"容器能起、任务全挂 / 迁移不可用"的隐形故障。

本脚本把核对做成一条命令：在目标镜像里跑 deploy/release-console/image_contract.py，
对比**当前仓库**声明的转发面，并检查必需路径（alembic/versions 等）。

用法（仓库根目录）:
  # 本地镜像
  pwsh scripts/ops/verify-reused-image.ps1 -Image cameltv-tp-runner:release-20260917-0007 -Part runner
  # 服务器上的镜像（走 ssh）
  pwsh scripts/ops/verify-reused-image.ps1 -Image cameltv-tp-backend:release-20260917-0007 -Part backend `
      -SshHost 111.230.155.116 -KeyPath F:\CamelTv-safe-backup\release-platform-key

退出码：0 = 可沿用；1 = 核对不通过（缺路径/缺转发面），**不得沿用**。
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Image,
    [Parameter(Mandatory)][ValidateSet('backend', 'runner', 'api', 'ai-gateway')][string]$Part,
    [string]$RepoRoot = '',
    [string]$AppRoot = '/app',
    [string]$SshHost = '',
    [string]$SshUser = 'root',
    [string]$KeyPath = '',
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }
$contractPath = Join-Path $RepoRoot 'test-platform-v2\backend\app\core\execution_dispatch.py'
$modulePath = Join-Path $RepoRoot 'deploy\release-console\image_contract.py'
foreach ($required in @($contractPath, $modulePath)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "缺少前置文件: $required" }
}

$repoSource = [IO.File]::ReadAllText($contractPath)
$moduleB64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $modulePath)))
$payloadJson = @{ root = $AppRoot; part = $Part; repo_source = $repoSource } | ConvertTo-Json -Compress
$payloadB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($payloadJson))

# 自包含探测脚本（经 stdin 送进容器，避免 PowerShell 原生参数二次引号问题）
$probe = @"
import base64, json
ns = {'__name__': 'image_contract_probe'}
exec(base64.b64decode('$moduleB64'), ns)
payload = json.loads(base64.b64decode('$payloadB64').decode('utf-8'))
facts = ns['collect_image_facts'](payload['root'], payload['part'])
report = ns['verify_image'](root=payload['root'], part=payload['part'],
                            repo_source=payload['repo_source'], **facts)
print(json.dumps(report))
"@

if ($SshHost) {
    $sshArgs = @('-o', 'BatchMode=yes')
    if ($KeyPath) { $sshArgs += @('-i', $KeyPath) }
    $sshArgs += @("${SshUser}@${SshHost}", "docker run -i --rm --entrypoint python $Image -")
    $raw = $probe | & ssh @sshArgs 2>&1
} else {
    $raw = $probe | & docker run -i --rm --entrypoint python $Image - 2>&1
}
$text = ($raw | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw "镜像内探测失败(rc=$LASTEXITCODE): $text" }

$report = $text | ConvertFrom-Json
if ($Json) {
    $text
} else {
    Write-Host "== verify-reused-image ==" -ForegroundColor Cyan
    Write-Host "image : $Image"
    Write-Host "part  : $($report.part) (root=$($report.root))"
    Write-Host "转发面: $(@($report.image_endpoint_modules).Count) 个模块"
    if ($report.missing_paths.Count -gt 0) { Write-Host "缺少路径: $($report.missing_paths -join ', ')" -ForegroundColor Red }
    if ($report.missing_endpoints) {
        foreach ($name in $report.missing_endpoints.PSObject.Properties.Name) {
            Write-Host "缺少转发面: $name -> $($report.missing_endpoints.$name -join ', ')" -ForegroundColor Red
        }
    }
    if ($report.contract_error) { Write-Host "转发面解析失败: $($report.contract_error)" -ForegroundColor Red }
    if ($report.ok) { Write-Host "OK：可沿用（路径齐全 + 转发面覆盖当前仓库契约）" -ForegroundColor Green }
    else { Write-Host "BLOCK：不得沿用该镜像" -ForegroundColor Red }
}

if (-not $report.ok) { exit 1 }
