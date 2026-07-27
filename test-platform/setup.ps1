# ============================================================
# 体育平台测试平台 — 一键搭建（Windows PowerShell）
# 用法:  在 test-platform/ 目录下执行  ./setup.ps1
# ============================================================
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "==> 1/5 创建独立 venv (test-platform/.venv)" -ForegroundColor Cyan
$Py = "C:\Users\26029\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }   # 回退到 PATH 中的 python
& $Py -m venv .venv

$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host "==> 2/5 升级 pip 并安装依赖" -ForegroundColor Cyan
& $VenvPy -m pip install --upgrade pip
& $VenvPy -m pip install -r requirements.txt

Write-Host "==> 3/5 以可编辑方式安装本平台 (提供 tp 命令)" -ForegroundColor Cyan
& $VenvPy -m pip install -e .

Write-Host "==> 4/5 安装 Playwright Chromium" -ForegroundColor Cyan
& $VenvPy -m playwright install chromium

Write-Host "==> 5/5 准备 .env" -ForegroundColor Cyan
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "    已生成 .env，请填写凭据" -ForegroundColor Yellow }

Write-Host ""
Write-Host "============== 安装完成 ==============" -ForegroundColor Green
Write-Host "激活 venv:  .\.venv\Scripts\Activate.ps1"
Write-Host "自检:       tp config show --site camel1 --env prod"
Write-Host ""
Write-Host "仍需手动完成的外部依赖:" -ForegroundColor Yellow
Write-Host "  1) Docker Desktop —— Mock Server(WireMock) 需要。安装后  docker pull wiremock/wiremock"
Write-Host "  2) mitmproxy CA 证书 —— 抓 camel1.to 的 HTTPS 必需:"
Write-Host "       先跑一次  tp capture --site camel1 --env prod  会启动 mitmproxy,"
Write-Host "       浏览器访问 http://mitm.it 下载并安装对应平台证书到'受信任的根证书颁发机构'。"
Write-Host "  3) 填写 .env 中各站点/环境的凭据与 UPSTREAM_PROXY(访问站点的上游代理地址)。"
