# AITDE V3.4 — 自签 mTLS 证书（CA + Temporal server + worker client），Windows
#
# 生成到 .\certs\（git-ignored）。开启 Temporal mTLS 时把路径填入 .env。
# 依赖: openssl（Git Bash / WSL / Chocolatey openssl 均可）。
# 用法: pwsh -File scripts\gen-certs.ps1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $PSScriptRoot
$certDir = Join-Path $root "certs"
New-Item -ItemType Directory -Force -Path $certDir | Out-Null
$days = 3650
$cn = "cameltv-aitde"

Write-Host "[gen-certs] cert dir: $certDir"

function Invoke-Openssl([string[]]$argsList) {
    & openssl @argsList
    if ($LASTEXITCODE -ne 0) { throw "openssl $($argsList -join ' ') failed" }
}

# ── CA ──
Invoke-Openssl @("req","-x509","-newkey","rsa:2048","-nodes","-days","$days",
    "-keyout",(Join-Path $certDir "ca.key"),"-out",(Join-Path $certDir "ca.crt"),
    "-subj","/CN=$cn-CA")

# ── Temporal server ──
Invoke-Openssl @("genrsa","-out",(Join-Path $certDir "temporal.key"),"2048")
Invoke-Openssl @("req","-new","-key",(Join-Path $certDir "temporal.key"),
    "-out",(Join-Path $certDir "temporal.csr"),"-subj","/CN=temporal")
$san = "subjectAltName=DNS:localhost,DNS:temporal,IP:127.0.0.1"
$extFile = Join-Path $certDir "temporal.ext"
Set-Content -Path $extFile -Value $san -Encoding ascii
Invoke-Openssl @("x509","-req","-in",(Join-Path $certDir "temporal.csr"),
    "-CA",(Join-Path $certDir "ca.crt"),"-CAkey",(Join-Path $certDir "ca.key"),
    "-CAcreateserial","-days","$days","-out",(Join-Path $certDir "temporal.crt"),
    "-extfile",$extFile)

# ── Worker client ──
Invoke-Openssl @("genrsa","-out",(Join-Path $certDir "worker.key"),"2048")
Invoke-Openssl @("req","-new","-key",(Join-Path $certDir "worker.key"),
    "-out",(Join-Path $certDir "worker.csr"),"-subj","/CN=worker")
Invoke-Openssl @("x509","-req","-in",(Join-Path $certDir "worker.csr"),
    "-CA",(Join-Path $certDir "ca.crt"),"-CAkey",(Join-Path $certDir "ca.key"),
    "-CAcreateserial","-days","$days","-out",(Join-Path $certDir "worker.crt"))

Remove-Item -Force (Join-Path $certDir "temporal.csr"),(Join-Path $certDir "worker.csr"),
    (Join-Path $certDir "temporal.ext"),(Join-Path $certDir "ca.srl") -ErrorAction SilentlyContinue

Write-Host "[gen-certs] done:"
Get-ChildItem $certDir | Select-Object -ExpandProperty Name | ForEach-Object { "  $_" }
Write-Host ""
Write-Host "配置到 .env:"
Write-Host "  TEMPORAL_TLS_ENABLED=true"
Write-Host "  TEMPORAL_TLS_CA_PATH=$(Join-Path $certDir 'ca.crt')"
Write-Host "  TEMPORAL_TLS_CERT_PATH=$(Join-Path $certDir 'worker.crt')"
Write-Host "  TEMPORAL_TLS_KEY_PATH=$(Join-Path $certDir 'worker.key')"
Write-Host "（对 Temporal server 使用 $certDir\temporal.crt / temporal.key）"
