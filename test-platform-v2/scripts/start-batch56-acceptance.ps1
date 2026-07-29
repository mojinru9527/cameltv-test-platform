[CmdletBinding()]
param(
    [switch]$RevealLocalCredentials,
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$platformRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $platformRoot "backend"
$frontendRoot = Join-Path $platformRoot "frontend"
$runtimeRoot = Join-Path $env:TEMP "batch56-local-runtime"
$containerName = "cameltv-batch56-postgres"
$postgresPort = 55456

function Get-ContainerEnvironmentValue {
    param(
        [Parameter(Mandatory)] [string]$Container,
        [Parameter(Mandatory)] [string]$Name
    )

    $lines = @(& docker inspect --format "{{range .Config.Env}}{{println .}}{{end}}" $Container)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to inspect acceptance PostgreSQL container."
    }
    $entry = @($lines | Where-Object { $_.StartsWith("$Name=") } | Select-Object -First 1)
    if ($entry.Count -ne 1) {
        throw "Container environment entry '$Name' is missing."
    }
    return $entry[0].Substring($Name.Length + 1)
}

function Get-DerivedSecret {
    param(
        [Parameter(Mandatory)] [string]$Seed,
        [Parameter(Mandatory)] [string]$Purpose
    )

    $bytes = [Text.Encoding]::UTF8.GetBytes("${Seed}:${Purpose}")
    $hash = [Security.Cryptography.SHA256]::HashData($bytes)
    return [Convert]::ToHexString($hash).ToLowerInvariant()
}

function Wait-HttpReady {
    param(
        [Parameter(Mandatory)] [string]$Uri,
        [Parameter(Mandatory)] [scriptblock]$IsReady,
        [int]$Attempts = 45
    )

    for ($attempt = 0; $attempt -lt $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 2
            if (& $IsReady $response) {
                return
            }
        }
        catch {
            # The process may still be starting.
        }
        Start-Sleep -Seconds 1
    }
    throw "Timed out waiting for $Uri"
}

function Assert-PortIsFree {
    param(
        [Parameter(Mandatory)] [int]$Port,
        [Parameter(Mandatory)] [string]$Service
    )

    $listeners = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    )
    if ($listeners.Count -gt 0) {
        $owners = ($listeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
        throw (
            "$Service port $Port is already owned by PID(s) $owners. " +
            "Refusing to reuse an unverified process; stop it and rerun this script."
        )
    }
}

function Get-ListenerProcess {
    param(
        [Parameter(Mandatory)] [int]$Port,
        [Parameter(Mandatory)] [string]$ExpectedCommandFragment
    )

    $listeners = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    )
    if ($listeners.Count -ne 1) {
        throw "Expected exactly one listener on port $Port, found $($listeners.Count)."
    }

    $processId = $listeners[0].OwningProcess
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $processId"
    if (
        $null -eq $processInfo -or
        -not $processInfo.CommandLine.Contains($ExpectedCommandFragment)
    ) {
        throw "Listener on port $Port is not bound to the expected Batch 56 worktree."
    }
    return Get-Process -Id $processId
}

New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
$platformStatus = @(& git -C $platformRoot status --porcelain=v1 -- .)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect the Batch 56 platform worktree."
}
$workingTreeClean = $platformStatus.Count -eq 0
if (-not $workingTreeClean -and -not $AllowDirty) {
    throw (
        "The test-platform-v2 worktree has uncommitted changes. " +
        "Commit the exact acceptance source or rerun explicitly with -AllowDirty."
    )
}
Assert-PortIsFree -Port 8000 -Service "Backend"
Assert-PortIsFree -Port 5173 -Service "Frontend"

& docker info --format "{{.ServerVersion}}" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop must be running for the Batch 56 PostgreSQL gate."
}

$existingContainer = @(
    & docker ps -a --filter "name=^/${containerName}$" --format "{{.Names}}"
)
if ($existingContainer.Count -eq 0) {
    $postgresPassword = [Convert]::ToHexString(
        [Security.Cryptography.RandomNumberGenerator]::GetBytes(24)
    ).ToLowerInvariant()
    & docker run -d `
        --name $containerName `
        --label "cameltv.batch=56" `
        --label "cameltv.worktree=codex-batch-56-full-platform-production-acceptance" `
        -e "POSTGRES_USER=cameltv" `
        -e "POSTGRES_PASSWORD=$postgresPassword" `
        -e "POSTGRES_DB=cameltv_batch56" `
        -p "127.0.0.1:${postgresPort}:5432" `
        -v "cameltv-batch56-pg-data:/var/lib/postgresql/data" `
        "postgres:16-alpine" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the Batch 56 PostgreSQL container."
    }
}
else {
    & docker start $containerName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to start the Batch 56 PostgreSQL container."
    }
}

$postgresReady = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    & docker exec $containerName pg_isready -U cameltv -d cameltv_batch56 *> $null
    if ($LASTEXITCODE -eq 0) {
        $postgresReady = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $postgresReady) {
    throw "Batch 56 PostgreSQL did not become ready."
}

$postgresPassword = Get-ContainerEnvironmentValue `
    -Container $containerName `
    -Name "POSTGRES_PASSWORD"
$adminPassword = "B56a!" + (
    Get-DerivedSecret -Seed $postgresPassword -Purpose "admin"
).Substring(0, 24)
$testerPassword = "B56t!" + (
    Get-DerivedSecret -Seed $postgresPassword -Purpose "tester"
).Substring(0, 24)
$jwtSecret = Get-DerivedSecret -Seed $postgresPassword -Purpose "jwt"

$env:DATABASE_URL = (
    "postgresql://cameltv:${postgresPassword}@127.0.0.1:${postgresPort}/cameltv_batch56"
)
$env:AUTO_CREATE_TABLES = "false"
$env:ENVIRONMENT = "development"
$env:SECRET_KEY = $jwtSecret
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = $adminPassword
$env:TESTER_USERNAME = "tester"
$env:TESTER_PASSWORD = $testerPassword
$env:ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
$env:CSRF_ALLOWED_ORIGINS = $env:ALLOWED_ORIGINS
$env:COOKIE_SECURE = "false"
$env:AI_ENABLED = "false"
$env:SYNC_ENABLED = "false"
$env:KNOWLEDGE_INGEST_PRODUCTION_DATA = "false"

Push-Location $backendRoot
try {
    & python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic upgrade failed."
    }
}
finally {
    Pop-Location
}

$backendLauncher = Start-Process `
    -FilePath "python" `
    -ArgumentList @(
        "-m", "uvicorn", "app.main:app",
        "--app-dir", $backendRoot,
        "--host", "127.0.0.1",
        "--port", "8000"
    ) `
    -WorkingDirectory $runtimeRoot `
    -WindowStyle Hidden `
    -PassThru

Wait-HttpReady `
    -Uri "http://127.0.0.1:8000/health" `
    -IsReady { param($response) $response.StatusCode -eq 200 }
$backendProcess = Get-ListenerProcess `
    -Port 8000 `
    -ExpectedCommandFragment $backendRoot

Push-Location $frontendRoot
try {
    & npm ci
    if ($LASTEXITCODE -ne 0) {
        throw "npm ci failed."
    }
}
finally {
    Pop-Location
}

$viteEntry = Join-Path $frontendRoot "node_modules/vite/bin/vite.js"
$frontendLauncher = Start-Process `
    -FilePath "node" `
    -ArgumentList @(
        $viteEntry,
        "--host", "0.0.0.0",
        "--port", "5173",
        "--strictPort"
    ) `
    -WorkingDirectory $frontendRoot `
    -WindowStyle Hidden `
    -PassThru

Wait-HttpReady `
    -Uri "http://127.0.0.1:5173/login" `
    -IsReady { param($response) $response.StatusCode -eq 200 }
Wait-HttpReady `
    -Uri "http://127.0.0.1:5173/api/v1/open/health" `
    -IsReady {
        param($response)
        if ($response.StatusCode -ne 200) {
            return $false
        }
        try {
            return ($response.Content | ConvertFrom-Json).code -eq 0
        }
        catch {
            return $false
        }
    }
$frontendProcess = Get-ListenerProcess `
    -Port 5173 `
    -ExpectedCommandFragment $frontendRoot

$codeSha = (& git -C $platformRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to identify the Batch 56 code revision."
}
$runtimeManifestPath = Join-Path $runtimeRoot "runtime-manifest.json"
[ordered]@{
    batch = 56
    code_sha = $codeSha
    working_tree_clean = $workingTreeClean
    platform_root = $platformRoot
    database = "postgresql://cameltv@127.0.0.1:${postgresPort}/cameltv_batch56"
    backend_pid = $backendProcess.Id
    frontend_pid = $frontendProcess.Id
} | ConvertTo-Json | Set-Content -LiteralPath $runtimeManifestPath -Encoding UTF8

$credentialsPath = Join-Path $runtimeRoot "local-credentials.json"
[ordered]@{
    scope = "Batch 56 local acceptance only"
    frontend = "http://localhost:5173/"
    admin_username = "admin"
    admin_password = $adminPassword
    tester_username = "tester"
    tester_password = $testerPassword
} | ConvertTo-Json | Set-Content -LiteralPath $credentialsPath -Encoding UTF8

if ($IsWindows) {
    & icacls $credentialsPath /inheritance:r /grant:r "${env:USERNAME}:(R,W)" *> $null
    & icacls $runtimeManifestPath /inheritance:r /grant:r "${env:USERNAME}:(R,W)" *> $null
}

$result = [pscustomobject]@{
    Frontend = "http://localhost:5173/"
    Backend = "http://127.0.0.1:8000"
    Database = "PostgreSQL 16 / cameltv_batch56 / port $postgresPort"
    BackendProcess = $backendProcess.Id
    FrontendProcess = $frontendProcess.Id
    RuntimeData = $runtimeRoot
    RuntimeManifest = $runtimeManifestPath
    CredentialsFile = $credentialsPath
}
$result | Format-List

if ($RevealLocalCredentials) {
    [pscustomobject]@{
        AdminUsername = "admin"
        AdminPassword = $adminPassword
        TesterUsername = "tester"
        TesterPassword = $testerPassword
    } | Format-List
}
