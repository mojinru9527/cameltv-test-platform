[CmdletBinding()]
param(
    [string]$PythonVersion = "3.12.10",
    [string]$TargetDir = (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312"),
    [string]$BackendPath,
    [switch]$RebuildVenv
)

$ErrorActionPreference = "Stop"

function Test-PythonHealthy {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $out = @(& $Path -c "import fastapi, sqlalchemy, pydantic; print('deps ok')" 2>&1)
    return ($LASTEXITCODE -eq 0 -and ($out -join ' ') -match 'deps ok')
}

$pythonExe = Join-Path $TargetDir "python.exe"
Write-Host "== setup-dev-python =="
Write-Host "target   : $TargetDir"

if (Test-PythonHealthy -Path $pythonExe) {
    Write-Host "OK: python.exe + 依赖已可用，无需修复"
    exit 0
}

if (-not (Test-Path -LiteralPath $TargetDir)) {
    Write-Host "目标目录不存在，将全新安装 Python $PythonVersion (per-user)"
}
elseif (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Host "检测到 python.exe 缺失（目录存在），执行原位修复"
}
else {
    Write-Host "python.exe 存在但依赖不可用，将覆盖安装后重装依赖"
}

$installer = Join-Path $env:TEMP ("python-" + $PythonVersion + "-amd64.exe")
if (-not (Test-Path -LiteralPath $installer)) {
    $url = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
    Write-Host "下载官方安装器: $url"
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
}

Write-Host "静默安装（per-user，TargetDir 不变，不写系统 PATH）..."
$args = @(
    "/quiet",
    "InstallAllUsers=0",
    "TargetDir=$TargetDir",
    "PrependPath=0",
    "Include_launcher=0",
    "Include_test=0",
    "Include_doc=0",
    "Include_tcltk=0"
)
$proc = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru -WindowStyle Hidden
if ($proc.ExitCode -ne 0) {
    throw "Python 安装器退出码 $($proc.ExitCode)"
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Host "安装器因产品已注册而跳过（已知坑），改用官方 embeddable 包原位补回解释器 DLL..."
    $zip = Join-Path $env:TEMP ("python-" + $PythonVersion + "-embed-amd64.zip")
    if (-not (Test-Path -LiteralPath $zip)) {
        Invoke-WebRequest -Uri ("https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip") -OutFile $zip -UseBasicParsing
    }
    $extract = Join-Path $env:TEMP ("pyembed-" + $PythonVersion)
    if (Test-Path -LiteralPath $extract) { [IO.Directory]::Delete($extract, $true) }
    Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
    foreach ($file in @("python.exe", "pythonw.exe", "python312.dll", "python3.dll", "vcruntime140.dll", "vcruntime140_1.dll")) {
        $src = Join-Path $extract $file
        if (Test-Path -LiteralPath $src) { Copy-Item -LiteralPath $src -Destination (Join-Path $TargetDir $file) -Force }
    }
}

if (-not (Test-PythonHealthy -Path $pythonExe)) {
    throw "安装后 python.exe 仍不可用或依赖缺失: $pythonExe"
}
Write-Host "OK: python.exe 已恢复，依赖可导入"

if (-not $BackendPath) {
    $repo = & git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -eq 0) { $BackendPath = Join-Path $repo "test-platform-v2/backend" }
}
if ($BackendPath -and (Test-Path -LiteralPath (Join-Path $BackendPath "requirements.txt"))) {
    $venv = Join-Path $BackendPath ".venv"
    $venvPy = Join-Path $venv "Scripts\python.exe"
    if (-not (Test-PythonHealthy -Path $venvPy)) {
        if ($RebuildVenv) {
            Write-Host "重建后端 venv: $venv"
            if (Test-Path -LiteralPath $venv) { [IO.Directory]::Delete($venv, $true) }
            & $pythonExe -m venv $venv
            & (Join-Path $venv "Scripts\python.exe") -m pip install --upgrade pip --quiet
            & (Join-Path $venv "Scripts\python.exe") -m pip install -r (Join-Path $BackendPath "requirements.txt") --quiet
        }
        else {
            Write-Host "后端 .venv 不可用，可用 -RebuildVenv 重建（会自动 pip install requirements）"
        }
    }
}

if ($BackendPath -and (Test-PythonHealthy -Path (Join-Path $BackendPath ".venv\Scripts\python.exe"))) {
    Write-Host "OK: 后端 .venv 已可用"
}

Write-Host "DONE"
exit 0
