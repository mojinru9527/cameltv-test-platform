<#
.SYNOPSIS
  AIQE 升级：把生产 backend 切到指定镜像 tag 并触发迁移/健康检查。默认 DryRun。
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ImageTag,
    [switch]$Execute,
    [string]$ComposeDir = "/opt/cameltv-tp/test-platform-v2",
    [string]$HealthUrl = "https://swiftbugs.cn/api/v1/open/health"
)

$ErrorActionPreference = "Stop"
$commands = @(
    "docker tag cameltv-tp-backend:$ImageTag cameltv-tp-backend:main",
    "cd $ComposeDir",
    "docker compose -p cameltv-tp-production --env-file config/runtime/production.env -f deploy/docker-compose.yml -f deploy/docker-compose.override.yml up -d --no-deps backend",
    "docker exec cameltv-tp-production-backend-1 alembic current",
    "curl -s -o /dev/null -w '%{http_code}' $HealthUrl"
)

if (-not $Execute) {
    Write-Host "AIQE_UPGRADE=DRYRUN tag=$ImageTag"
    $commands | ForEach-Object { Write-Host "  $_" }
    Write-Host "追加 -Execute 才会实际执行。"
    exit 0
}

foreach ($command in $commands) {
    Write-Host "+ $command"
    if ($command -like "cd *") {
        Set-Location ($command.Substring(3))
    }
    elseif ($command -like "curl *") {
        $code = & bash -lc $command
        if ($code -ne "200") { throw "健康检查失败: $code" }
    }
    else {
        & bash -lc $command
        if ($LASTEXITCODE -ne 0) { throw "命令失败: $command" }
    }
}
Write-Host "AIQE_UPGRADE=DONE tag=$ImageTag"
exit 0
