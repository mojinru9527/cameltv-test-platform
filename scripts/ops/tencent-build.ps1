#requires -Version 5.1
<#
tencent-build.ps1 — 腾讯云生产发布：本地构建镜像 + 上传 + (可选)服务器加载

这是发布平台的「构建」环节（网页无法执行，因服务器无法直连 GitHub/PyPI）。
用法（在仓库根目录执行）:

  # 1. 构建前后端镜像并导出 tar（本机必须已初始化 lanhu-mcp 子模块）
  pwsh scripts/ops/tencent-build.ps1 build -Tag release-20260823-0001

  # 2. 上传 tar 到服务器 /opt/cameltv-release/（发布按钮会 docker load）
  pwsh scripts/ops/tencent-build.ps1 upload -Tag release-20260823-0001

  # 3. 一键（构建+上传+提示到页面发布）
  pwsh scripts/ops/tencent-build.ps1 all -Tag release-20260823-0001

参数:
  -Tag            镜像 tag（release- 前缀 + 日期序列，如 release-20260823-0001）
  -Host           服务器地址（默认 111.230.155.116）
  -User           SSH 用户（默认 root）
  -KeyPath        SSH 密钥（默认 $HOME/.ssh/cameltv_tencent_lighthouse）
  -ReleaseDir     服务器发布目录（默认 /opt/cameltv-release）
  -IcpNumber      备案号（构建前端注入 footer，默认 粤ICP备2026121122号-1）
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("build", "upload", "all")]
    [string]$Command = "build",

    [Parameter(Mandatory)]
    [string]$Tag,

    [string]$HostName = "111.230.155.116",
    [string]$UserName = "root",
    [string]$KeyPath = "$HOME/.ssh/cameltv_tencent_lighthouse",
    [string]$ReleaseDir = "/opt/cameltv-release",
    [string]$IcpNumber = "粤ICP备2026121122号-1",
    [string]$OutputDir = "F:\CamelTv-safe-backup\release-artifacts"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# 校验 tag 安全性（只有字母数字和 -）
if ($Tag -notmatch "^[A-Za-z0-9-]+$") { throw "Tag 只能包含字母数字和连字符: $Tag" }

function Invoke-Step($msg) {
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Build-Images {
    param([string]$Tag)
    Invoke-Step "构建前端镜像 cameltv-tp-frontend:$Tag (ICP=$IcpNumber)"
    Push-Location "$repoRoot\test-platform-v2\frontend"
    try {
        docker build --build-arg "VITE_ICP_NUMBER=$IcpNumber" -t "cameltv-tp-frontend:$Tag" . 2>&1 | Select-Object -Last 3
        if ($LASTEXITCODE -ne 0) { throw "前端镜像构建失败" }
    } finally { Pop-Location }

    Invoke-Step "构建后端镜像 cameltv-tp-backend:$Tag"
    Push-Location $repoRoot
    try {
        docker build -t "cameltv-tp-backend:$Tag" -f test-platform-v2/backend/Dockerfile . 2>&1 | Select-Object -Last 3
        if ($LASTEXITCODE -ne 0) { throw "后端镜像构建失败" }
    } finally { Pop-Location }

    Invoke-Step "导出镜像 tar 到 $OutputDir"
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    docker save "cameltv-tp-backend:$Tag" -o "$OutputDir\$Tag-backend.tar"
    docker save "cameltv-tp-frontend:$Tag" -o "$OutputDir\$Tag-frontend.tar"
    Get-ChildItem $OutputDir -Filter "$Tag-*.tar" | Select-Object Name, @{N='MB';E={[math]::Round($_.Length/1MB,1)}}
}

function Upload-Artifacts {
    param([string]$Tag)
    Invoke-Step "上传镜像 tar 到 $UserName@$HostName:$ReleaseDir"
    $ssh = @{
        KeyPath = $KeyPath
        HostName = $HostName
        UserName = $UserName
    }
    # 创建发布目录
    ssh -i $KeyPath -o BatchMode=yes -o ConnectTimeout=15 "$UserName@$HostName" "mkdir -p $ReleaseDir" 2>&1 | Select-Object -First 2
    scp -i $KeyPath -o BatchMode=yes "$OutputDir\$Tag-backend.tar" "$UserName@$HostName`:$ReleaseDir/"
    scp -i $KeyPath -o BatchMode=yes "$OutputDir\$Tag-frontend.tar" "$UserName@$HostName`:$ReleaseDir/"
    Write-Host "上传完成。现在可在运维发布页面点击「发布」按钮（docker load + compose up）。" -ForegroundColor Green
}

switch ($Command) {
    "build" { Build-Images -Tag $Tag }
    "upload" { Upload-Artifacts -Tag $Tag }
    "all" {
        Build-Images -Tag $Tag
        Upload-Artifacts -Tag $Tag
    }
}
