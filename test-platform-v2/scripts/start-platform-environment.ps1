[CmdletBinding()]
param(
    [ValidateSet("local", "production")]
    [string]$Target = "local",

    [ValidateSet("start", "status")]
    [string]$Action = "start",

    [switch]$ConfirmProduction,

    [switch]$InitializeLocal,

    [switch]$LibraryOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$platformRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$profilePath = Join-Path $platformRoot "config\runtime\$Target.env"
$composePath = Join-Path $platformRoot "deploy\docker-compose.yml"
$backendRoot = Join-Path $platformRoot "backend"
$frontendRoot = Join-Path $platformRoot "frontend"
$runtimeDirectory = Join-Path ([System.IO.Path]::GetTempPath()) "cameltv-platform-$Target"
$manifestPath = Join-Path $runtimeDirectory "runtime-manifest.json"

function New-RandomProfileSecret {
    param([int]$ByteCount = 32)

    $bytes = [byte[]]::new($ByteCount)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function Initialize-LocalRuntimeProfile {
    if ($Target -ne "local") {
        throw "-InitializeLocal is only valid with -Target local."
    }
    if (Test-Path -LiteralPath $profilePath) {
        Write-Host "The ignored local runtime profile already exists; it was not overwritten."
        return
    }

    $examplePath = "$profilePath.example"
    if (-not (Test-Path -LiteralPath $examplePath -PathType Leaf)) {
        throw "The local runtime profile template is missing."
    }

    & git -C $platformRoot check-ignore --quiet "config/runtime/local.env"
    if ($LASTEXITCODE -ne 0) {
        throw "Refusing to create local.env because Git does not report it as ignored."
    }

    $generatedSecrets = @{
        SECRET_KEY = New-RandomProfileSecret -ByteCount 48
        ADMIN_PASSWORD = New-RandomProfileSecret -ByteCount 24
        TESTER_PASSWORD = New-RandomProfileSecret -ByteCount 24
    }
    $foundSecretKeys = @{}
    $profileLines = foreach ($rawLine in Get-Content -LiteralPath $examplePath -Encoding utf8) {
        if ($rawLine -match "^\s*(SECRET_KEY|ADMIN_PASSWORD|TESTER_PASSWORD)\s*=") {
            $key = $Matches[1]
            $foundSecretKeys[$key] = $true
            "$key=$($generatedSecrets[$key])"
        }
        else {
            $rawLine
        }
    }
    foreach ($key in $generatedSecrets.Keys) {
        if (-not $foundSecretKeys.ContainsKey($key)) {
            throw "The local runtime profile template is missing required key '$key'."
        }
    }

    Set-Content -LiteralPath $profilePath -Value $profileLines -Encoding utf8 -NoNewline:$false
    if ($IsWindows) {
        & icacls $profilePath /inheritance:r /grant:r "${env:USERNAME}:(R,W)" *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to restrict permissions on the generated local runtime profile."
        }
    }
    Write-Host "Created the ignored local runtime profile with independent generated credentials."
}

function Read-RuntimeProfile {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $relativeExample = "config/runtime/$Target.env.example"
        $relativeProfile = "config/runtime/$Target.env"
        throw "Runtime profile is missing. From test-platform-v2, run: Copy-Item '$relativeExample' '$relativeProfile', then set its ignored local secrets."
    }

    $result = @{}
    foreach ($rawLine in Get-Content -LiteralPath $Path -Encoding utf8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        $separator = $line.IndexOf("=")
        if ($separator -le 0) {
            throw "Runtime profile contains an invalid entry. Expected KEY=VALUE without printing profile values."
        }

        $key = $line.Substring(0, $separator).Trim()
        $value = $line.Substring($separator + 1).Trim()
        if ($key -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
            throw "Runtime profile contains an invalid key name."
        }
        if ($result.ContainsKey($key)) {
            throw "Runtime profile contains duplicate key '$key'."
        }
        $result[$key] = $value
    }

    return $result
}

function Assert-RequiredProfileKeys {
    param([Parameter(Mandatory)][hashtable]$Profile)

    $requiredKeys = @(
        "PLATFORM_TARGET",
        "PLATFORM_FRONTEND_URL",
        "COMPOSE_PROJECT_NAME",
        "FRONTEND_PORT",
        "BACKEND_PORT",
        "ENVIRONMENT",
        "DATABASE_URL",
        "AUTO_CREATE_TABLES",
        "COOKIE_SECURE"
    )

    foreach ($key in $requiredKeys) {
        if (-not $Profile.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($Profile[$key])) {
            throw "Runtime profile is missing required key '$key'."
        }
    }
}

function ConvertTo-ProfilePort {
    param(
        [Parameter(Mandatory)][hashtable]$Profile,
        [Parameter(Mandatory)][string]$Key
    )

    [int]$port = 0
    if (
        -not $Profile.ContainsKey($Key) -or
        -not [int]::TryParse($Profile[$Key], [ref]$port) -or
        $port -lt 1 -or
        $port -gt 65535
    ) {
        throw "Runtime profile key '$Key' must be an integer from 1 through 65535."
    }
    return $port
}

function Assert-RuntimeProfile {
    param(
        [Parameter(Mandatory)][hashtable]$Profile,
        [Parameter(Mandatory)][string]$RequestedTarget
    )

    Assert-RequiredProfileKeys -Profile $Profile

    if ($Profile["PLATFORM_TARGET"] -cne $RequestedTarget) {
        throw "Runtime profile PLATFORM_TARGET does not match requested target '$RequestedTarget'."
    }

    $frontendPort = ConvertTo-ProfilePort -Profile $Profile -Key "FRONTEND_PORT"
    $backendPort = ConvertTo-ProfilePort -Profile $Profile -Key "BACKEND_PORT"
    if ($frontendPort -eq $backendPort) {
        throw "FRONTEND_PORT and BACKEND_PORT must be distinct."
    }

    if ($Profile.ContainsKey("VITE_DEV_PORT")) {
        $vitePort = ConvertTo-ProfilePort -Profile $Profile -Key "VITE_DEV_PORT"
        if ($RequestedTarget -eq "local" -and $vitePort -ne $frontendPort) {
            throw "For local, VITE_DEV_PORT must equal FRONTEND_PORT."
        }
    }

    [uri]$frontendUri = $null
    if (-not [uri]::TryCreate($Profile["PLATFORM_FRONTEND_URL"], [System.UriKind]::Absolute, [ref]$frontendUri)) {
        throw "PLATFORM_FRONTEND_URL must be an absolute URL."
    }

    if ($RequestedTarget -eq "local") {
        foreach ($key in @("SECRET_KEY", "ADMIN_PASSWORD", "TESTER_PASSWORD")) {
            if (-not $Profile.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($Profile[$key])) {
                throw "The ignored local profile must set non-empty $key. Use -InitializeLocal for first-time setup."
            }
        }
        if ($Profile["ENVIRONMENT"] -cne "development") {
            throw "The local profile must set ENVIRONMENT=development."
        }
        if (-not $Profile["DATABASE_URL"].StartsWith("sqlite:///", [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "The local profile must use SQLite."
        }
        if ($Profile["COOKIE_SECURE"] -cne "false") {
            throw "The local profile must set COOKIE_SECURE=false."
        }
        if ($Profile["AUTO_CREATE_TABLES"] -cne "true") {
            throw "The local profile must set AUTO_CREATE_TABLES=true."
        }
        if ($frontendUri.Scheme -cne "http" -or -not $frontendUri.IsLoopback) {
            throw "The local profile must use an HTTP loopback PLATFORM_FRONTEND_URL."
        }
        if ($frontendUri.Port -ne $frontendPort) {
            throw "The local PLATFORM_FRONTEND_URL port must equal FRONTEND_PORT."
        }
        return
    }

    if ($Profile["ENVIRONMENT"] -cne "production") {
        throw "The production profile must set ENVIRONMENT=production."
    }
    if (-not $Profile["DATABASE_URL"].StartsWith("postgresql://", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "The production profile must use PostgreSQL."
    }
    if ($Profile["COOKIE_SECURE"] -cne "true") {
        throw "The production profile must set COOKIE_SECURE=true."
    }
    if ($Profile["AUTO_CREATE_TABLES"] -cne "false") {
        throw "The production profile must set AUTO_CREATE_TABLES=false."
    }
    if ($frontendUri.Scheme -cne "https") {
        throw "The production profile must use an HTTPS PLATFORM_FRONTEND_URL."
    }
    foreach ($key in @("ALLOWED_ORIGINS", "CSRF_ALLOWED_ORIGINS", "POSTGRES_DB")) {
        if (-not $Profile.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($Profile[$key])) {
            throw "The production profile must set non-empty $key."
        }
    }
    if (
        $Profile["ALLOWED_ORIGINS"] -cne $Profile["PLATFORM_FRONTEND_URL"] -or
        $Profile["CSRF_ALLOWED_ORIGINS"] -cne $Profile["PLATFORM_FRONTEND_URL"]
    ) {
        throw "Production origins must exactly match PLATFORM_FRONTEND_URL."
    }
    try {
        $databaseUri = [uri]$Profile["DATABASE_URL"]
        $databaseName = [uri]::UnescapeDataString($databaseUri.AbsolutePath.TrimStart("/"))
    }
    catch {
        throw "The production DATABASE_URL is invalid."
    }
    if ($databaseName -cne $Profile["POSTGRES_DB"]) {
        throw "The production DATABASE_URL database must match POSTGRES_DB."
    }
}

function Assert-NoPlaceholderValues {
    param([Parameter(Mandatory)][hashtable]$Profile)

    foreach ($key in $Profile.Keys) {
        if ($Profile[$key].IndexOf("change-me", [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            throw "Runtime profile key '$key' still contains a change-me placeholder."
        }
    }
    if (
        $Profile["PLATFORM_FRONTEND_URL"].IndexOf(
            "example.com",
            [System.StringComparison]::OrdinalIgnoreCase
        ) -ge 0
    ) {
        throw "PLATFORM_FRONTEND_URL still contains the example hostname."
    }
}

function Get-DatabaseIdentity {
    param([Parameter(Mandatory)][string]$DatabaseUrl)

    if ($DatabaseUrl.StartsWith("sqlite:///", [System.StringComparison]::OrdinalIgnoreCase)) {
        $databasePath = $DatabaseUrl.Substring("sqlite:///".Length)
        return @{
            backend = "sqlite"
            name = [System.IO.Path]::GetFileName($databasePath)
        }
    }

    try {
        $databaseUri = [uri]$DatabaseUrl
        $databaseName = [uri]::UnescapeDataString($databaseUri.AbsolutePath.TrimStart("/"))
    }
    catch {
        throw "DATABASE_URL is not a valid PostgreSQL URL."
    }

    if ([string]::IsNullOrWhiteSpace($databaseName)) {
        throw "DATABASE_URL must include a database name."
    }
    return @{
        backend = "postgresql"
        name = $databaseName
    }
}

function Get-GitSha {
    $sha = & git -C $platformRoot rev-parse HEAD 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $sha) {
        return "unknown"
    }
    return ([string]($sha -join "")).Trim()
}

function Write-RuntimeManifest {
    param(
        [Parameter(Mandatory)][hashtable]$Profile,
        [Parameter(Mandatory)][hashtable]$Database,
        [hashtable]$ProcessIds = @{}
    )

    New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
    $backendUrl = if ($Target -eq "local") {
        "http://127.0.0.1:$($Profile["BACKEND_PORT"])"
    }
    else {
        "$($Profile["PLATFORM_FRONTEND_URL"].TrimEnd("/"))/api/v1"
    }

    [ordered]@{
        target = $Target
        frontendUrl = $Profile["PLATFORM_FRONTEND_URL"]
        backendUrl = $backendUrl
        database = [ordered]@{
            backend = $Database["backend"]
            name = $Database["name"]
        }
        ports = [ordered]@{
            backend = [int]$Profile["BACKEND_PORT"]
            frontend = [int]$Profile["FRONTEND_PORT"]
        }
        pids = $ProcessIds
        gitSha = Get-GitSha
        recordedAtUtc = [DateTime]::UtcNow.ToString("o")
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding utf8
}

function Get-ListeningProcesses {
    param([Parameter(Mandatory)][int]$Port)

    $connections = @(
        Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
            Sort-Object OwningProcess -Unique
    )
    foreach ($connection in $connections) {
        $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($connection.OwningProcess)" -ErrorAction SilentlyContinue
        [pscustomobject]@{
            ProcessId = [int]$connection.OwningProcess
            CommandLine = if ($processInfo) { [string]$processInfo.CommandLine } else { "" }
        }
    }
}

function Test-ProcessBelongsToPath {
    param(
        [Parameter(Mandatory)][string]$CommandLine,
        [Parameter(Mandatory)][string]$ExpectedPath
    )

    $normalizedCommand = $CommandLine.Replace("/", "\")
    $normalizedPath = $ExpectedPath.Replace("/", "\").TrimEnd("\")
    $searchFrom = 0
    while ($searchFrom -lt $normalizedCommand.Length) {
        $matchIndex = $normalizedCommand.IndexOf(
            $normalizedPath,
            $searchFrom,
            [System.StringComparison]::OrdinalIgnoreCase
        )
        if ($matchIndex -lt 0) {
            return $false
        }

        $beforeValid = $matchIndex -eq 0
        if (-not $beforeValid) {
            $before = $normalizedCommand[$matchIndex - 1]
            $beforeValid = [char]::IsWhiteSpace($before) -or $before -in @('"', "'", '=')
        }

        $afterIndex = $matchIndex + $normalizedPath.Length
        $afterValid = $afterIndex -eq $normalizedCommand.Length
        if (-not $afterValid) {
            $after = $normalizedCommand[$afterIndex]
            $afterValid = [char]::IsWhiteSpace($after) -or $after -in @('"', "'", '\')
        }

        if ($beforeValid -and $afterValid) {
            return $true
        }
        $searchFrom = $matchIndex + 1
    }
    return $false
}

function Get-VerifiedListenerProcessId {
    param(
        [Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Listeners,
        [Parameter(Mandatory)][int]$Port,
        [Parameter(Mandatory)][string]$ExpectedPath,
        [Parameter(Mandatory)][string]$Label
    )

    $listenerList = @($Listeners)
    if ($listenerList.Count -eq 0) {
        return $null
    }
    if ($listenerList.Count -ne 1) {
        $listenerPids = ($listenerList.ProcessId -join ", ")
        throw "$Label port $Port has multiple listener processes (PID: $listenerPids). Stop them before starting this profile."
    }

    $listener = $listenerList[0]
    if (-not (Test-ProcessBelongsToPath -CommandLine $listener.CommandLine -ExpectedPath $ExpectedPath)) {
        throw "$Label port $Port is occupied by a process outside this worktree (PID: $($listener.ProcessId)). Stop it or change the ignored local profile."
    }
    return [int]$listener.ProcessId
}

function Set-VerifiedManifestListenerPid {
    param(
        [Parameter(Mandatory)][psobject]$Manifest,
        [Parameter(Mandatory)][ValidateSet("backend", "frontend")][string]$Name,
        [Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Listeners,
        [Parameter(Mandatory)][int]$Port,
        [Parameter(Mandatory)][string]$ExpectedPath,
        [Parameter(Mandatory)][string]$Label
    )

    $listenerPid = Get-VerifiedListenerProcessId `
        -Listeners $Listeners `
        -Port $Port `
        -ExpectedPath $ExpectedPath `
        -Label $Label
    if ($null -eq $listenerPid) {
        return $null
    }

    if (-not $Manifest.PSObject.Properties["pids"] -or $null -eq $Manifest.pids) {
        $Manifest | Add-Member -MemberType NoteProperty -Name "pids" -Value ([pscustomobject]@{}) -Force
    }
    $Manifest.pids | Add-Member -MemberType NoteProperty -Name $Name -Value $listenerPid -Force
    return $listenerPid
}

function Resolve-LocalListener {
    param(
        [Parameter(Mandatory)][int]$Port,
        [Parameter(Mandatory)][string]$ExpectedPath,
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][scriptblock]$StartProcess
    )

    $listenerPid = Get-VerifiedListenerProcessId `
        -Listeners @(Get-ListeningProcesses -Port $Port) `
        -Port $Port `
        -ExpectedPath $ExpectedPath `
        -Label $Label
    if ($null -ne $listenerPid) {
        $reusedPid = [int]$listenerPid
        Write-Host "Reusing $Label from this worktree (PID $reusedPid)."
        return $reusedPid
    }

    $startedProcess = & $StartProcess
    Write-Host "Started $Label (PID $($startedProcess.Id))."
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    while ([DateTime]::UtcNow -lt $deadline) {
        $listenerPid = Get-VerifiedListenerProcessId `
            -Listeners @(Get-ListeningProcesses -Port $Port) `
            -Port $Port `
            -ExpectedPath $ExpectedPath `
            -Label $Label
        if ($null -ne $listenerPid) {
            if ([int]$listenerPid -ne [int]$startedProcess.Id) {
                Write-Host "Resolved $Label listener PID $listenerPid from launcher PID $($startedProcess.Id)."
            }
            return [int]$listenerPid
        }
        Start-Sleep -Milliseconds 200
    }
    throw "$Label did not bind port $Port within 60 seconds. Logs: $runtimeDirectory"
}

function Assert-LocalListenerOwnership {
    param(
        [Parameter(Mandatory)][int]$Port,
        [Parameter(Mandatory)][string]$ExpectedPath,
        [Parameter(Mandatory)][string]$Label
    )

    $null = Get-VerifiedListenerProcessId `
        -Listeners @(Get-ListeningProcesses -Port $Port) `
        -Port $Port `
        -ExpectedPath $ExpectedPath `
        -Label $Label
}

function Assert-LocalReuseManifest {
    param(
        [Parameter(Mandatory)][hashtable]$Profile,
        [Parameter(Mandatory)][hashtable]$Database,
        [switch]$RequireRunning
    )

    $backendPort = ConvertTo-ProfilePort -Profile $Profile -Key "BACKEND_PORT"
    $frontendPort = ConvertTo-ProfilePort -Profile $Profile -Key "FRONTEND_PORT"
    $backendListeners = @(Get-ListeningProcesses -Port $backendPort)
    $frontendListeners = @(Get-ListeningProcesses -Port $frontendPort)
    if ($backendListeners.Count -eq 0 -and $frontendListeners.Count -eq 0) {
        if ($RequireRunning) {
            throw "The backend and frontend listeners are stopped."
        }
        return
    }
    if ($RequireRunning -and ($backendListeners.Count -ne 1 -or $frontendListeners.Count -ne 1)) {
        throw "A complete backend/frontend listener pair is not running."
    }
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Existing local listeners have no matching runtime manifest. Stop the old processes before starting this profile."
    }

    $expectedBackendUrl = "http://127.0.0.1:$backendPort"
    try {
        $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8 | ConvertFrom-Json
        $manifestMatches = (
            $manifest.target -ceq "local" -and
            $manifest.frontendUrl -ceq $Profile["PLATFORM_FRONTEND_URL"] -and
            $manifest.backendUrl -ceq $expectedBackendUrl -and
            $manifest.database.backend -ceq $Database["backend"] -and
            $manifest.database.name -ceq $Database["name"] -and
            [int]$manifest.ports.backend -eq $backendPort -and
            [int]$manifest.ports.frontend -eq $frontendPort -and
            $manifest.gitSha -ceq (Get-GitSha)
        )
    }
    catch {
        throw "Existing local listeners have an unreadable or incomplete runtime manifest. Stop the old processes before starting this profile."
    }
    if (-not $manifestMatches) {
        throw "Existing local listeners do not match the requested profile target, URL, database, ports, or Git SHA. Stop the old processes before starting this profile."
    }

    $null = Set-VerifiedManifestListenerPid `
        -Manifest $manifest `
        -Name "backend" `
        -Listeners $backendListeners `
        -Port $backendPort `
        -ExpectedPath $backendRoot `
        -Label "Backend"
    $null = Set-VerifiedManifestListenerPid `
        -Manifest $manifest `
        -Name "frontend" `
        -Listeners $frontendListeners `
        -Port $frontendPort `
        -ExpectedPath $frontendRoot `
        -Label "Frontend"

    return $manifest
}

function Test-HttpEndpoint {
    param([Parameter(Mandatory)][string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 3 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Wait-ForHttpEndpoint {
    param(
        [Parameter(Mandatory)][string]$Url,
        [Parameter(Mandatory)][string]$Label,
        [int]$TimeoutSeconds = 60
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-HttpEndpoint -Url $Url) {
            Write-Host "$Label is healthy."
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "$Label did not become healthy within $TimeoutSeconds seconds. Logs: $runtimeDirectory"
}

function Show-LocalStatus {
    param(
        [Parameter(Mandatory)][hashtable]$Profile,
        [Parameter(Mandatory)][hashtable]$Database
    )

    $backendPort = ConvertTo-ProfilePort -Profile $Profile -Key "BACKEND_PORT"
    $frontendPort = ConvertTo-ProfilePort -Profile $Profile -Key "FRONTEND_PORT"
    $backendUrl = "http://127.0.0.1:$backendPort/health"
    $frontendUrl = "$($Profile["PLATFORM_FRONTEND_URL"].TrimEnd("/"))/login"
    $proxyUrl = "$($Profile["PLATFORM_FRONTEND_URL"].TrimEnd("/"))/api/v1/open/health"

    $backendListeners = @(Get-ListeningProcesses -Port $backendPort)
    $frontendListeners = @(Get-ListeningProcesses -Port $frontendPort)
    try {
        $manifest = Assert-LocalReuseManifest `
            -Profile $Profile `
            -Database $Database `
            -RequireRunning
    }
    catch {
        throw "Local runtime status is stale/unverified: $($_.Exception.Message)"
    }
    $backendOwned = $backendListeners.Count -gt 0 -and @(
        $backendListeners | Where-Object {
            Test-ProcessBelongsToPath -CommandLine $_.CommandLine -ExpectedPath $backendRoot
        }
    ).Count -eq $backendListeners.Count
    $frontendOwned = $frontendListeners.Count -gt 0 -and @(
        $frontendListeners | Where-Object {
            Test-ProcessBelongsToPath -CommandLine $_.CommandLine -ExpectedPath $frontendRoot
        }
    ).Count -eq $frontendListeners.Count

    Write-Host "Target: local"
    Write-Host "Access: $($Profile["PLATFORM_FRONTEND_URL"])"
    Write-Host "Database: $($Database["backend"])/$($Database["name"])"
    Write-Host "Runtime manifest: verified"
    Write-Host "Manifest target: $($manifest.target)"
    Write-Host "Manifest frontend URL: $($manifest.frontendUrl)"
    Write-Host "Manifest backend URL: $($manifest.backendUrl)"
    Write-Host "Manifest database: $($manifest.database.backend)/$($manifest.database.name)"
    Write-Host "Manifest ports: backend=$($manifest.ports.backend), frontend=$($manifest.ports.frontend)"
    Write-Host "Manifest Git SHA: $($manifest.gitSha)"
    Write-Host "Manifest PIDs: backend=$($manifest.pids.backend), frontend=$($manifest.pids.frontend)"
    Write-Host "Backend listener: $(if ($backendOwned) { "this worktree" } elseif ($backendListeners.Count) { "foreign process" } else { "stopped" })"
    Write-Host "Frontend listener: $(if ($frontendOwned) { "this worktree" } elseif ($frontendListeners.Count) { "foreign process" } else { "stopped" })"
    Write-Host "Backend health: $(if (Test-HttpEndpoint -Url $backendUrl) { "healthy" } else { "unavailable" })"
    Write-Host "Frontend login: $(if (Test-HttpEndpoint -Url $frontendUrl) { "healthy" } else { "unavailable" })"
    Write-Host "Proxied health: $(if (Test-HttpEndpoint -Url $proxyUrl) { "healthy" } else { "unavailable" })"
}

function Start-LocalEnvironment {
    param(
        [Parameter(Mandatory)][hashtable]$Profile,
        [Parameter(Mandatory)][hashtable]$Database
    )

    $backendPort = ConvertTo-ProfilePort -Profile $Profile -Key "BACKEND_PORT"
    $frontendPort = ConvertTo-ProfilePort -Profile $Profile -Key "FRONTEND_PORT"
    $viteEntryPoint = Join-Path $frontendRoot "node_modules\vite\bin\vite.js"
    if (-not (Test-Path -LiteralPath $viteEntryPoint -PathType Leaf)) {
        throw "Frontend dependencies are missing. Run npm install in test-platform-v2/frontend."
    }

    $pythonCommand = @(Get-Command python -CommandType Application -ErrorAction Stop)[0]
    $nodeCommand = @(Get-Command node -CommandType Application -ErrorAction Stop)[0]
    New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
    Assert-LocalListenerOwnership -Port $backendPort -ExpectedPath $backendRoot -Label "Backend"
    Assert-LocalListenerOwnership -Port $frontendPort -ExpectedPath $frontendRoot -Label "Frontend"
    $null = Assert-LocalReuseManifest -Profile $Profile -Database $Database

    $previousEnvironment = @{}
    try {
        foreach ($key in $Profile.Keys) {
            $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
            [Environment]::SetEnvironmentVariable($key, $Profile[$key], "Process")
        }

        $backendPid = Resolve-LocalListener `
            -Port $backendPort `
            -ExpectedPath $backendRoot `
            -Label "backend" `
            -StartProcess {
                Start-Process `
                    -FilePath $pythonCommand.Source `
                    -ArgumentList @(
                        "-m",
                        "uvicorn",
                        "app.main:app",
                        "--app-dir",
                        "`"$backendRoot`"",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "$backendPort"
                    ) `
                    -WorkingDirectory $backendRoot `
                    -WindowStyle Hidden `
                    -RedirectStandardOutput (Join-Path $runtimeDirectory "backend.stdout.log") `
                    -RedirectStandardError (Join-Path $runtimeDirectory "backend.stderr.log") `
                    -PassThru
            }

        $frontendPid = Resolve-LocalListener `
            -Port $frontendPort `
            -ExpectedPath $frontendRoot `
            -Label "frontend" `
            -StartProcess {
                Start-Process `
                    -FilePath $nodeCommand.Source `
                    -ArgumentList @(
                        "`"$viteEntryPoint`"",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "$frontendPort",
                        "--strictPort"
                    ) `
                    -WorkingDirectory $frontendRoot `
                    -WindowStyle Hidden `
                    -RedirectStandardOutput (Join-Path $runtimeDirectory "frontend.stdout.log") `
                    -RedirectStandardError (Join-Path $runtimeDirectory "frontend.stderr.log") `
                    -PassThru
            }
    }
    finally {
        foreach ($key in $Profile.Keys) {
            [Environment]::SetEnvironmentVariable($key, $previousEnvironment[$key], "Process")
        }
    }

    $frontendBaseUrl = $Profile["PLATFORM_FRONTEND_URL"].TrimEnd("/")
    Wait-ForHttpEndpoint -Url "http://127.0.0.1:$backendPort/health" -Label "Backend"
    Wait-ForHttpEndpoint -Url "$frontendBaseUrl/login" -Label "Frontend login"
    Wait-ForHttpEndpoint -Url "$frontendBaseUrl/api/v1/open/health" -Label "Proxied API"

    Write-RuntimeManifest -Profile $Profile -Database $Database -ProcessIds @{
        backend = $backendPid
        frontend = $frontendPid
    }
    Write-Host "Local platform is ready at $($Profile["PLATFORM_FRONTEND_URL"])."
    Write-Host "Database: $($Database["backend"])/$($Database["name"])"
    Write-Host "Runtime manifest: $manifestPath"
}

function Invoke-SharedCompose {
    param(
        [Parameter(Mandatory)][hashtable]$Profile,
        [Parameter(Mandatory)][hashtable]$Database,
        [Parameter(Mandatory)][ValidateSet("start", "status")][string]$RequestedAction
    )

    $baseArguments = @(
        "compose",
        "--project-name",
        $Profile["COMPOSE_PROJECT_NAME"],
        "--env-file",
        $profilePath,
        "-f",
        $composePath
    )
    if ($RequestedAction -eq "status") {
        & docker @baseArguments ps
    }
    else {
        & docker @baseArguments up -d --build
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose $RequestedAction failed for target '$Target'."
    }

    if ($RequestedAction -eq "start") {
        Write-RuntimeManifest -Profile $Profile -Database $Database
        Write-Host "$Target platform start requested at $($Profile["PLATFORM_FRONTEND_URL"])."
        Write-Host "Database: $($Database["backend"])/$($Database["name"])"
        Write-Host "Runtime manifest: $manifestPath"
    }
}

if ($LibraryOnly) {
    return
}

if ($InitializeLocal) {
    Initialize-LocalRuntimeProfile
}

$profile = Read-RuntimeProfile -Path $profilePath
Assert-RuntimeProfile -Profile $profile -RequestedTarget $Target
$databaseIdentity = Get-DatabaseIdentity -DatabaseUrl $profile["DATABASE_URL"]

if ($Target -eq "production" -and $Action -eq "start" -and -not $ConfirmProduction) {
    throw "Production start requires the explicit -ConfirmProduction switch."
}
if ($Target -ne "local" -and $Action -eq "start") {
    Assert-NoPlaceholderValues -Profile $profile
}

if ($Target -eq "local") {
    if ($Action -eq "status") {
        Show-LocalStatus -Profile $profile -Database $databaseIdentity
    }
    else {
        Start-LocalEnvironment -Profile $profile -Database $databaseIdentity
    }
}
else {
    Invoke-SharedCompose -Profile $profile -Database $databaseIdentity -RequestedAction $Action
}
