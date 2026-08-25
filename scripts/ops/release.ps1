#requires -Version 5.1
<#
release.ps1 — 腾讯云一键发布（自动化：build → digest → 提交 → 上传 → 发布）

用法（仓库根目录执行）:
  # 全流程（构建+提取digest+提交登记+上传+验证+发布+确认上线）
  pwsh scripts/ops/release.ps1 -Tag release-20260823-0003 -Publish

  # 只构建+提交登记（不发布，线下检查后网页点发布）
  pwsh scripts/ops/release.ps1 -Tag release-20260823-0003

  # 只回滚
  pwsh scripts/ops/release.ps1 rollback -Tag main

  # 只备份
  pwsh scripts/ops/release.ps1 backup

参数:
  -Tag        镜像 tag（release- 前缀；rollback 时填目标镜像如 main）
  -Publish    构建提交流程后立即发布（默认不发布）
  -Token      release-console 令牌（首次输入后保存到 ~\.cameltv-release-console\token.json）
  -BaseUrl    release-console API（默认 https://release.swiftbugs.cn）
  -Host       服务器地址（默认 111.230.155.116）
  -User       SSH 用户（默认 root）
  -KeyPath    SSH 密钥（默认 ./release-platform-key 或 ~/.ssh/cameltv_tencent_lighthouse）
  -IcpNumber  备案号
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("release", "rollback", "backup")]
    [string]$Command = "release",
    [string]$Tag = "",
    [switch]$Publish,
    [string]$Token = "",
    [string]$BaseUrl = "https://release.swiftbugs.cn",
    [string]$HostName = "111.230.155.116",
    [string]$UserName = "root",
    [string]$KeyPath = "",
    [string]$IcpNumber = "粤ICP备2026121122号-1",
    [string]$OutputDir = "F:\CamelTv-safe-backup\release-artifacts",
    [string]$ReleaseDir = "/opt/cameltv-release"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# ── Token 管理（首次输入，之后存本地）─────────────────────────────
$tokenStore = "$HOME\.cameltv-release-console\token.json"
if (-not $Token -and (Test-Path $tokenStore)) {
    $Token = (Get-Content $tokenStore -Raw | ConvertFrom-Json).token
}
if ($Command -ne "backup" -and -not $Token) {
    $Token = Read-Host "请输入 RELEASE_CONSOLE_TOKEN（回车保存到本地，之后免输入）"
    New-Item -ItemType Directory -Force -Path (Split-Path $tokenStore) | Out-Null
    @{ token = $Token } | ConvertTo-Json | Set-Content $tokenStore -Encoding UTF8
}

# ── SSH 密钥（发布密钥优先）──────────────────────────────────────
if (-not $KeyPath) {
    $candidates = @("F:\CamelTv-safe-backup\release-platform-key", "$HOME\.ssh\cameltv_tencent_lighthouse")
    $KeyPath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

# ── 辅助 ────────────────────────────────────────────────────────
function Invoke-Api([string]$method, [string]$path, $body = $null) {
    $headers = @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }
    $params = @{ Uri = "$BaseUrl$path"; Method = $method; Headers = $headers; UseBasicParsing = $true; TimeoutSec = 900 }
    if ($body) { $params.Body = ($body | ConvertTo-Json -Depth 6) }
    try {
        $r = Invoke-RestMethod @params
        if ($r.code -ne 0 -and $r.code -ne $null) { Write-Host "API 异常: $($r.msg)" -ForegroundColor Red; return $null }
        return $r
    } catch {
        Write-Host "API 失败: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function Get-Digest([string]$image) {
    $id = docker image inspect $image --format "{{index .RepoDigests 0}}" 2>$null
    if ($id -and $id -match "sha256:([0-9a-f]{64})") { return $Matches[1] }
    $id2 = docker image inspect $image --format "{{.Id}}" 2>$null
    if ($id2 -match "sha256:([0-9a-f]{64})") { return $Matches[1] }
    throw "无法获取镜像 $image digest"
}

# ── 发布流程 ────────────────────────────────────────────────────
function Invoke-Release {
    if (-not $Tag) { throw "-Tag 必填（如 release-20260823-0003）" }
    $gitSha = (git -C $repoRoot rev-parse HEAD).Trim()
    Write-Host "==> Git SHA: $gitSha" -ForegroundColor Cyan

    # 1. 构建镜像
    Write-Host "==> 构建前端 cameltv-tp-frontend:$Tag (ICP=$IcpNumber)" -ForegroundColor Cyan
    Push-Location "$repoRoot\test-platform-v2\frontend"
    try { docker build --build-arg "VITE_ICP_NUMBER=$IcpNumber" -t "cameltv-tp-frontend:$Tag" . 2>&1 | Select-Object -Last 2 } finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { throw "前端构建失败" }

    Write-Host "==> 构建后端 cameltv-tp-backend:$Tag" -ForegroundColor Cyan
    Push-Location $repoRoot
    try { docker build -t "cameltv-tp-backend:$Tag" -f test-platform-v2/backend/Dockerfile . 2>&1 | Select-Object -Last 2 } finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { throw "后端构建失败" }

    # 2. 自动提取 digest
    $feDigest = Get-Digest "cameltv-tp-frontend:$Tag"
    $beDigest = Get-Digest "cameltv-tp-backend:$Tag"
    Write-Host "==> 前端 digest: $feDigest" -ForegroundColor Green
    Write-Host "==> 后端 digest: $beDigest" -ForegroundColor Green

    # 3. 生成 manifest + 提交登记
    $releaseId = $Tag -replace "[^a-z0-9-]", "-"
    $zero64 = "0" * 64
    $manifest = @{
        schema_version = "1.0"
        release_id = $releaseId
        git_sha = $gitSha
        frontend = @{ image = "cameltv-tp-frontend"; digest = "sha256:$feDigest"; sbom_sha256 = $zero64 }
        backend = @{ image = "cameltv-tp-backend"; digest = "sha256:$beDigest"; sbom_sha256 = $zero64; openapi_sha256 = $zero64 }
        database = @{ alembic_heads = @("see-verified-head"); target_revision = "see-verified-head"; rollback_mode = "application-rollback-or-forward-fix" }
        config_schema = "platform-runtime/v1"
        secret_refs = @("secret://production/cameltv/platform@v1")
        qa_evidence = @("artifact://release-platform/qa-e2e")
    } | ConvertTo-Json -Depth 6

    Write-Host "==> 提交登记 $releaseId" -ForegroundColor Cyan
    $submit = Invoke-Api "POST" "/api/deployments" @{
        release_id = $releaseId; image_tag = $Tag; manifest_json = $manifest
    }
    if (-not $submit -or -not $submit.deployment_id) { throw "提交登记失败" }
    $deploymentId = $submit.deployment_id
    Write-Host "==> 登记成功 id=$deploymentId（状态 DRAFT）" -ForegroundColor Green

    # 4. 导出 + 上传 tar
    Write-Host "==> 导出并上传镜像" -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    # containerd 存储（io.containerd.snapshotter.v1）下 docker save 可能产出
    # 残缺 OCI tar（缺 index.json/manifest.json → 服务器 load 报
    # "unrecognized image format"，2026-08-25 演练实测），改用 buildx
    # type=docker 导出（含 manifest.json 的经典 docker 归档，服务器可 load）。
    docker buildx build --builder desktop-linux -t "cameltv-tp-backend:$Tag" -f test-platform-v2/backend/Dockerfile --output=type=docker,dest="$OutputDir\$Tag-backend.tar" . 2>&1 | Select-Object -Last 2
    if ($LASTEXITCODE -ne 0) { throw "后端镜像导出失败" }
    Push-Location "$repoRoot\test-platform-v2\frontend"
    try { docker buildx build --builder desktop-linux --build-arg "VITE_ICP_NUMBER=$IcpNumber" -t "cameltv-tp-frontend:$Tag" --output=type=docker,dest="$OutputDir\$Tag-frontend.tar" . 2>&1 | Select-Object -Last 2 } finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { throw "前端镜像导出失败" }
    ssh -i $KeyPath -o BatchMode=yes "${UserName}@${HostName}" "mkdir -p $ReleaseDir" 2>&1 | Out-Null
    scp -i $KeyPath -o BatchMode=yes "$OutputDir\$Tag-backend.tar" "${UserName}@${HostName}:$ReleaseDir/"
    scp -i $KeyPath -o BatchMode=yes "$OutputDir\$Tag-frontend.tar" "${UserName}@${HostName}:$ReleaseDir/"

    # 5. 发布（可选）
    if ($Publish) {
        Write-Host "==> 验证 manifest $deploymentId" -ForegroundColor Cyan
        $val = Invoke-Api "POST" "/api/deployments/$deploymentId/validate" $null
        if (-not $val) { throw "验证失败（manifest 校验未通过，请到网页检查）" }
        Write-Host "==> 发布 $deploymentId" -ForegroundColor Cyan
        $pub = Invoke-Api "POST" "/api/deployments/$deploymentId/publish" @{ image_tag = $Tag }
        if (-not $pub) { throw "发布失败" }
        Write-Host "==> 发布成功: $($pub.summary)" -ForegroundColor Green
        Write-Host "==> 确认上线（线上健康检查）" -ForegroundColor Cyan
        $ver = Invoke-Api "POST" "/api/deployments/$deploymentId/verify" $null
        if ($ver) { Write-Host "==> 上线确认: $($ver.summary)" -ForegroundColor Green }
        else { Write-Host "==> 上线确认未通过，请到网页 https://release.swiftbugs.cn 手动「确认上线」" -ForegroundColor Yellow }
    } else {
        Write-Host "==> 构建+提交完成。去网页 https://release.swiftbugs.cn 点「发布」即可（状态 VALIDATED 后）" -ForegroundColor Yellow
    }
}

function Invoke-Rollback {
    if (-not $Tag) { throw "rollback 需 -Tag（目标镜像如 main）" }
    $list = Invoke-Api "GET" "/api/deployments"
    if (-not $list) { return }
    $deploy = @($list) | Select-Object -First 1
    if (-not $deploy) { Write-Host "无发布记录" -ForegroundColor Yellow; return }
    $rb = Invoke-Api "POST" "/api/deployments/$($deploy.id)/rollback" @{ image_tag = $Tag }
    if ($rb) { Write-Host "==> 回滚成功: $($rb.summary)" -ForegroundColor Green }
}

function Invoke-Backup {
    $list = Invoke-Api "GET" "/api/deployments"
    if (-not $list) { return }
    $deploy = @($list) | Select-Object -First 1
    if (-not $deploy) {
        Write-Host "无发布记录，无法备份（需先发布）" -ForegroundColor Yellow
        return
    }
    $bk = Invoke-Api "POST" "/api/deployments/$($deploy.id)/backup" $null
    if ($bk) { Write-Host "==> 备份成功: $($bk.summary)" -ForegroundColor Green }
}

switch ($Command) {
    "release" { Invoke-Release }
    "rollback" { Invoke-Rollback }
    "backup" { Invoke-Backup }
}
