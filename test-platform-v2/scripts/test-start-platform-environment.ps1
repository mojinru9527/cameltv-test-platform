[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function Assert-Equal($Expected, $Actual, [string]$Message) {
    if ($Expected -ne $Actual) {
        throw "ASSERTION FAILED: $Message (expected=$Expected, actual=$Actual)"
    }
}

function Assert-Throws([scriptblock]$Action, [string]$Pattern, [string]$Message) {
    $thrown = $false
    try { & $Action } catch {
        $thrown = $true
        if ($_.Exception.Message -notmatch $Pattern) {
            throw "ASSERTION FAILED: $Message (unexpected error: $($_.Exception.Message))"
        }
    }
    if (-not $thrown) { throw "ASSERTION FAILED: $Message (no error was thrown)" }
}

$scriptUnderTest = Join-Path $PSScriptRoot "start-platform-environment.ps1"
. $scriptUnderTest -LibraryOnly

$expectedBackend = 'F:\CamelTv-worktrees\current-task\test-platform-v2\backend'
Assert-True `
    (Test-ProcessBelongsToPath -CommandLine "python -m uvicorn --app-dir `"$expectedBackend`"" -ExpectedPath $expectedBackend) `
    "an exact app-dir must belong to the worktree"
Assert-True `
    (-not (Test-ProcessBelongsToPath -CommandLine "python -m uvicorn --app-dir `"$expectedBackend-foreign`"" -ExpectedPath $expectedBackend)) `
    "a sibling worktree sharing the path prefix must be rejected"

$script:listenerReadCount = 0
function Get-ListeningProcesses {
    param([int]$Port)
    $script:listenerReadCount++
    if ($script:listenerReadCount -eq 1) { return @() }
    return @([pscustomobject]@{
        ProcessId = 4242
        CommandLine = "python -m uvicorn --app-dir `"$expectedBackend`" --port $Port"
    })
}

$resolvedPid = Resolve-LocalListener `
    -Port 58026 `
    -ExpectedPath $expectedBackend `
    -Label "backend" `
    -StartProcess { [pscustomobject]@{ Id = 1111 } }
Assert-Equal 4242 $resolvedPid "the listener PID, not the venv forwarding PID, must be returned"

$manifest = [pscustomobject]@{
    pids = [pscustomobject]@{ backend = 1111; frontend = 3333 }
}
$listeners = @([pscustomobject]@{
    ProcessId = 4242
    CommandLine = "python -m uvicorn --app-dir `"$expectedBackend`" --port 58026"
})
$verifiedPid = Set-VerifiedManifestListenerPid `
    -Manifest $manifest `
    -Name "backend" `
    -Listeners $listeners `
    -Port 58026 `
    -ExpectedPath $expectedBackend `
    -Label "Backend"
Assert-Equal 4242 $verifiedPid "status must resolve the actual listener PID"
Assert-Equal 4242 $manifest.pids.backend "status must reconcile the in-memory manifest PID"

$foreignManifest = [pscustomobject]@{
    pids = [pscustomobject]@{ backend = 1111; frontend = 3333 }
}
$foreignListeners = @([pscustomobject]@{
    ProcessId = 9999
    CommandLine = 'python -m uvicorn --app-dir "F:\CamelTv-worktrees\another-task\test-platform-v2\backend" --port 58026'
})
Assert-Throws `
    { Set-VerifiedManifestListenerPid -Manifest $foreignManifest -Name "backend" -Listeners $foreignListeners -Port 58026 -ExpectedPath $expectedBackend -Label "Backend" } `
    "outside this worktree" `
    "manifest reconciliation must reject a foreign listener"
Assert-Equal 1111 $foreignManifest.pids.backend "a rejected foreign listener must not alter the manifest"

$productionWorkerProfile = @{
    PLATFORM_TARGET = "production"
    PLATFORM_FRONTEND_URL = "https://swiftbugs.cn"
    COMPOSE_PROJECT_NAME = "cameltv-tp-production"
    COMPOSE_PROFILES = "aitde-worker"
    FRONTEND_PORT = "80"
    BACKEND_PORT = "8000"
    ENVIRONMENT = "production"
    DATABASE_URL = "postgresql://cameltv:secret@postgres:5432/cameltv_production"
    AUTO_CREATE_TABLES = "false"
    COOKIE_SECURE = "true"
    ALLOWED_ORIGINS = "https://swiftbugs.cn"
    CSRF_ALLOWED_ORIGINS = "https://swiftbugs.cn"
    POSTGRES_DB = "cameltv_production"
    AITDE_V3_ENABLED = "true"
    TEMPORAL_ENABLED = "true"
    TEMPORAL_GRPC_ENDPOINT = "aitde-temporal:7233"
    AITDE_WORKER_API_TOKEN = "worker-token"
    AITDE_WORKER_KEY = "aitde-worker"
    AITDE_WORKER_HEARTBEAT_SECONDS = "60"
}
Assert-RuntimeProfile -Profile $productionWorkerProfile -RequestedTarget "production"

$missingWorkerToken = $productionWorkerProfile.Clone()
$missingWorkerToken["AITDE_WORKER_API_TOKEN"] = ""
Assert-Throws `
    { Assert-RuntimeProfile -Profile $missingWorkerToken -RequestedTarget "production" } `
    "requires non-empty AITDE_WORKER_API_TOKEN" `
    "the managed Worker must fail before Compose when its token is missing"

$disabledTemporal = $productionWorkerProfile.Clone()
$disabledTemporal["TEMPORAL_ENABLED"] = "false"
Assert-Throws `
    { Assert-RuntimeProfile -Profile $disabledTemporal -RequestedTarget "production" } `
    "requires AITDE_V3_ENABLED=true and TEMPORAL_ENABLED=true" `
    "the managed Worker must fail before Compose when Temporal is disabled"

$staleHeartbeat = $productionWorkerProfile.Clone()
$staleHeartbeat["AITDE_WORKER_HEARTBEAT_SECONDS"] = "180"
Assert-Throws `
    { Assert-RuntimeProfile -Profile $staleHeartbeat -RequestedTarget "production" } `
    "at least 1 and less than 180" `
    "the managed Worker heartbeat must stay inside the offline threshold"

Write-Host "PASS: runtime ownership and managed Worker production profile guards."
