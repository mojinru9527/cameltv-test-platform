# CI/CD 公共入口脚本
# 用法: .\scripts\ci-entrypoint.ps1 -Env test -Command "tp api run"
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("test", "prod")]
    [string]$Env,

    [Parameter(Mandatory=$true)]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host " CamelTv 测试平台 CI · 环境: $Env"        -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan

# 1. 激活虚拟环境
$venvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "[CI] 激活 virtualenv..." -ForegroundColor Green
    . $venvActivate
} else {
    Write-Host "[CI] virtualenv 不存在，跳过激活。" -ForegroundColor Yellow
}

# 2. 加载 .env
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Write-Host "[CI] 加载 .env..." -ForegroundColor Green
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)') {
            [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim())
        }
    }
}

# 3. prod 环境 vpn 校验
if ($Env -eq "prod") {
    Write-Host "[CI] 正式环境 — 校验 vpn07 连通性..." -ForegroundColor Yellow
    # vpn07_check 在 tp 内部做 TCP 连通检查
}

# 4. 环境探活
Write-Host "[CI] 环境探活..." -ForegroundColor Green
tp envcheck --env $Env
if ($LASTEXITCODE -ne 0) {
    Write-Host "[CI] 环境不通，终止流水线。" -ForegroundColor Red
    exit 1
}

# 5. 执行命令
Write-Host "[CI] 执行: $Command" -ForegroundColor Green
Invoke-Expression $Command
$exitCode = $LASTEXITCODE

Write-Host "========================================"  -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host " CI 通过 ✓" -ForegroundColor Green
} else {
    Write-Host " CI 失败 ✗ (exit=$exitCode)" -ForegroundColor Red
}
Write-Host "========================================"  -ForegroundColor Cyan
exit $exitCode
